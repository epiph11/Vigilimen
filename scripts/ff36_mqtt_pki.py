"""FF-36 - the MQTT lab CA is what ADR-020 says it is (S5).

Generates the lab PKI (plant/pki/mqttpki.py) into a temporary folder and checks it, then proves the checks
can fail: 16 deliberate mutations, each of which must be caught by the check that is meant to catch it.
No Docker, no network. Needs the `cryptography` package (the pki-init image already has it).

    python scripts\\ff36_mqtt_pki.py              baseline checks + mutation self-test
    python scripts\\ff36_mqtt_pki.py --static     baseline checks only

Not covered here (needs the broker, built later): that Mosquitto actually refuses the revoked client, and
whether it re-reads the CRL without a restart. That is the live part of FF-36, still to write.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plant" / "pki"))
try:
    import mqttpki as M
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization as ser
    from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID, NameOID
except ImportError as e:                                      # pragma: no cover
    sys.exit(f"FF-36 needs the 'cryptography' package: {e}. Try: python -m pip install cryptography")

POSIX = os.name == "posix"
SERVICES = ["broker", "edge", "consumer", "edge-old"]


def _cert(p: Path):
    return x509.load_pem_x509_certificate(p.read_bytes())


def _cn(c) -> str:
    return c.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value


def _dns(c) -> set[str]:
    return set(c.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value.get_values_for_type(x509.DNSName))


def _eku(c) -> set:
    return set(c.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value)


def _leaf_path(root: Path, svc: str) -> Path:
    return root / svc / ("server.pem" if svc == "broker" else "client.pem")


def _key_path(root: Path, svc: str) -> Path:
    return root / svc / ("server.key" if svc == "broker" else "client.key")


def _pub(x):
    return x.public_bytes(ser.Encoding.DER, ser.PublicFormat.SubjectPublicKeyInfo)


def checks(root: Path) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        out.append((name, bool(ok), detail))

    def guard(name, fn):
        try:
            ok, detail = fn()
        except Exception as e:                                # a broken file is a failed check, not a crash
            ok, detail = False, f"{type(e).__name__}: {e}"
        add(name, ok, detail)

    ca_pem = root / "_ca" / "ca.pem"
    ca = _cert(ca_pem)
    present = [s for s in SERVICES if (root / s).is_dir()]

    # --- the CA itself
    def ca_is_ca():
        bc = ca.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
        ku = ca.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
        ok = bc.critical and bc.value.ca and ku.key_cert_sign and ku.crl_sign
        return ok, f"ca={bc.value.ca} critical={bc.critical} keyCertSign={ku.key_cert_sign} cRLSign={ku.crl_sign}"
    guard("the CA is a CA (critical, keyCertSign, cRLSign)", ca_is_ca)

    def ca_pathlen():
        bc = ca.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS).value
        return bc.path_length == 0, f"path length {bc.path_length} (0: it cannot sign another CA)"
    guard("the CA path length is 0", ca_pathlen)

    def same_ca_everywhere():
        bad = [s for s in present if (root / s / "ca.pem").read_bytes() != ca_pem.read_bytes()]
        return not bad, f"different ca.pem in: {bad}" if bad else "every service holds the same ca.pem"
    guard("every service folder holds the same CA certificate", same_ca_everywhere)

    # --- each leaf
    for s in present:
        c = _cert(_leaf_path(root, s))
        is_server = s == "broker"

        def signed(c=c):
            c.verify_directly_issued_by(ca)
            return True, "signature and issuer name verified"
        guard(f"{s}: signed by the lab CA", signed)

        def cn(c=c, s=s):
            return _cn(c) == s, f"CN={_cn(c)!r}"
        guard(f"{s}: CN equals the identity (the ACL key)", cn)

        def eku(c=c, is_server=is_server):
            want = {ExtendedKeyUsageOID.SERVER_AUTH} if is_server else {ExtendedKeyUsageOID.CLIENT_AUTH}
            got = {o._name for o in _eku(c)}
            return _eku(c) == want, f"EKU {sorted(got)}"
        guard(f"{s}: EKU is {'serverAuth' if is_server else 'clientAuth'} only", eku)

        def san(c=c, s=s, is_server=is_server):
            want = {"broker", "localhost"} if is_server else {s}
            return want <= _dns(c), f"SAN DNS {sorted(_dns(c))}"
        guard(f"{s}: host name in the SAN", san)

        def validity(c=c):
            now = dt.datetime.now(dt.timezone.utc)
            span = (c.not_valid_after_utc - c.not_valid_before_utc).days
            ok = c.not_valid_before_utc <= now <= c.not_valid_after_utc and span <= 400
            return ok, f"valid {c.not_valid_before_utc:%Y-%m-%d} to {c.not_valid_after_utc:%Y-%m-%d} ({span} days)"
        guard(f"{s}: within validity and at most 400 days", validity)

        def keymatch(c=c, s=s):
            k = ser.load_pem_private_key(_key_path(root, s).read_bytes(), None)
            return _pub(k.public_key()) == _pub(c.public_key()), "the key in the folder matches the certificate"
        guard(f"{s}: the private key matches the certificate", keymatch)

    # --- keys sit only where they belong
    def keys_only_where_expected():
        expected = {(root / s / ("server.key" if s == "broker" else "client.key")).resolve() for s in present}
        found = set()
        for p in root.rglob("*"):
            if p.is_file() and "_ca" not in p.relative_to(root).parts and b"PRIVATE KEY" in p.read_bytes()[:200]:
                found.add(p.resolve())
        extra, missing = found - expected, expected - found
        return not extra and not missing, f"unexpected key files: {sorted(x.name for x in extra)}" if extra else "one key per service, nothing else"
    guard("private keys exist only as each service's own key (no CA key, no other service's key)", keys_only_where_expected)

    def keymodes():
        if not POSIX:
            return True, "skipped: not a POSIX file system (checked in the container)"
        bad = [str(p.relative_to(root)) for p in root.rglob("*.key") if p.stat().st_mode & 0o077]
        return not bad, f"too open: {bad}" if bad else "all .key files are 0600"
    guard("private keys are readable by their owner only", keymodes)

    # --- the CRL
    crl_path = root / "broker" / "crl.pem"

    def crl_present():
        return crl_path.exists() and not any((root / s / "crl.pem").exists() for s in present if s != "broker"), "crl.pem only in the broker folder"
    guard("CRL present, and only the broker holds it", crl_present)

    def crl_load():
        return x509.load_pem_x509_crl(crl_path.read_bytes())

    def crl_sig():
        crl = crl_load()
        ok = crl.is_signature_valid(ca.public_key()) and crl.issuer == ca.subject
        return ok, f"next update {crl.next_update_utc:%Y-%m-%d}"
    guard("the CRL is signed by the lab CA and is not expired", lambda: (lambda r: (r[0] and crl_load().next_update_utc > dt.datetime.now(dt.timezone.utc), r[1]))(crl_sig()))

    def crl_has():
        crl = crl_load()
        want = [_cert(_leaf_path(root, i)).serial_number for i in M.REVOKED if i in present]
        miss = [i for i in M.REVOKED if i in present and crl.get_revoked_certificate_by_serial_number(_cert(_leaf_path(root, i)).serial_number) is None]
        return bool(want) and not miss, f"revoked identities missing from the CRL: {miss}" if miss else "the revoked identity is listed"
    guard("the CRL lists the revoked identity", crl_has)

    def crl_only():
        crl = crl_load()
        wrong = [s for s in present if s not in M.REVOKED and crl.get_revoked_certificate_by_serial_number(_cert(_leaf_path(root, s)).serial_number) is not None]
        return not wrong, f"valid identities wrongly listed: {wrong}" if wrong else "no valid identity is listed"
    guard("the CRL lists no valid identity", crl_only)

    # --- an independent verifier (OpenSSL), when it is installed
    def openssl_check():
        exe = shutil.which("openssl")
        if not exe:
            return True, "skipped: openssl not found on PATH"
        res = []
        for s in present:
            r = subprocess.run([exe, "verify", "-CAfile", str(ca_pem), "-crl_check", "-CRLfile", str(crl_path), str(_leaf_path(root, s))],
                               capture_output=True, text=True)
            ok_cert = r.returncode == 0
            res.append((s, ok_cert, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else ""))
        bad = [f"{s}: {m}" for s, ok_cert, m in res if ok_cert == (s in M.REVOKED)]
        return not bad, "; ".join(bad) if bad else "openssl accepts every valid identity and rejects the revoked one"
    guard("independent verifier (openssl): valid accepted, revoked refused", openssl_check)
    return out


# ---------------------------------------------------------------------------
# Mutations: each damages a fresh copy of the tree and names the check that must notice.
# ---------------------------------------------------------------------------
def _ca_parts(root: Path):
    ca = _cert(root / "_ca" / "ca.pem")
    key = ser.load_pem_private_key((root / "_ca" / "ca.key").read_bytes(), None)
    return ca, key


def _put_leaf(root: Path, svc: str, cert, key) -> None:
    _leaf_path(root, svc).write_bytes(M.pem(cert))
    _key_path(root, svc).write_bytes(M.key_pem(key))


def _put_ca_everywhere(root: Path, cert) -> None:
    (root / "_ca" / "ca.pem").write_bytes(M.pem(cert))
    for s in SERVICES:
        if (root / s).is_dir():
            (root / s / "ca.pem").write_bytes(M.pem(cert))


def m_rogue_ca(root):
    ca, _ = _ca_parts(root)
    rogue, rkey = M.make_ca(name=M.CA_NAME)
    c, k = M.make_leaf(rogue, rkey, "broker", True, ["broker", "localhost"])
    _put_leaf(root, "broker", c, k)


def m_broker_eku(root):
    ca, ck = _ca_parts(root)
    c, k = M.make_leaf(ca, ck, "broker", True, ["broker", "localhost"], eku=[ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH])
    _put_leaf(root, "broker", c, k)


def m_client_eku_server(root):
    ca, ck = _ca_parts(root)
    c, k = M.make_leaf(ca, ck, "edge", False, ["edge"], eku=[ExtendedKeyUsageOID.SERVER_AUTH])
    _put_leaf(root, "edge", c, k)


def m_broker_san(root):
    ca, ck = _ca_parts(root)
    c, k = M.make_leaf(ca, ck, "broker", True, ["localhost"])
    _put_leaf(root, "broker", c, k)


def m_crl_empty(root):
    ca, ck = _ca_parts(root)
    (root / "broker" / "crl.pem").write_bytes(M.crl_pem(M.make_crl(ca, ck, [])))


def m_crl_too_much(root):
    ca, ck = _ca_parts(root)
    serials = [_cert(_leaf_path(root, s)).serial_number for s in ("edge-old", "edge")]
    (root / "broker" / "crl.pem").write_bytes(M.crl_pem(M.make_crl(ca, ck, serials)))


def m_crl_wrong_signer(root):
    ca, _ = _ca_parts(root)
    rogue, rkey = M.make_ca()
    serial = _cert(_leaf_path(root, "edge-old")).serial_number
    (root / "broker" / "crl.pem").write_bytes(M.crl_pem(M.make_crl(ca, rkey, [serial])))


def m_crl_missing(root):
    (root / "broker" / "crl.pem").unlink()


def m_ca_not_ca(root):
    ca, ck = _ca_parts(root)
    bad, _ = M.make_ca(key=ck, is_ca=False)
    _put_ca_everywhere(root, bad)


def m_ca_pathlen(root):
    ca, ck = _ca_parts(root)
    bad, _ = M.make_ca(key=ck, path_length=None)
    _put_ca_everywhere(root, bad)


def m_ca_key_leak(root):
    shutil.copy2(root / "_ca" / "ca.key", root / "broker" / "ca.key")


def m_client_key_leak(root):
    shutil.copy2(root / "edge" / "client.key", root / "consumer" / "edge.key")


def m_expired(root):
    ca, ck = _ca_parts(root)
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=800)
    c, k = M.make_leaf(ca, ck, "edge", False, ["edge"], days=30, not_before=old)
    _put_leaf(root, "edge", c, k)


def m_long_lived(root):
    ca, ck = _ca_parts(root)
    c, k = M.make_leaf(ca, ck, "edge", False, ["edge"], days=1800)
    _put_leaf(root, "edge", c, k)


def m_cn_mismatch(root):
    ca, ck = _ca_parts(root)
    c, k = M.make_leaf(ca, ck, "edge", False, ["edge"])         # an 'edge' certificate in the consumer folder
    _put_leaf(root, "consumer", c, k)


def m_key_mode(root):
    os.chmod(root / "edge" / "client.key", 0o644)


MUTATIONS = [
    (m_rogue_ca, "broker: signed by the lab CA", "a broker certificate signed by another CA"),
    (m_broker_eku, "broker: EKU is serverAuth only", "the broker certificate is also valid as a client"),
    (m_client_eku_server, "edge: EKU is clientAuth only", "a client certificate that says serverAuth"),
    (m_broker_san, "broker: host name in the SAN", "the broker name missing from the SAN"),
    (m_crl_empty, "the CRL lists the revoked identity", "an empty CRL: the revoked client would be accepted"),
    (m_crl_too_much, "the CRL lists no valid identity", "a CRL that also revokes a valid client"),
    (m_crl_wrong_signer, "the CRL is signed by the lab CA", "a CRL signed by another key"),
    (m_crl_missing, "CRL present", "no CRL file for the broker"),
    (m_ca_not_ca, "the CA is a CA", "the CA certificate without the CA flag"),
    (m_ca_pathlen, "the CA path length is 0", "a CA that could sign another CA"),
    (m_ca_key_leak, "private keys exist only as", "the CA private key copied into the broker folder"),
    (m_client_key_leak, "private keys exist only as", "the edge key copied into the consumer folder"),
    (m_expired, "edge: within validity", "an expired client certificate"),
    (m_long_lived, "edge: within validity", "a 5-year client certificate"),
    (m_cn_mismatch, "consumer: CN equals the identity", "an 'edge' certificate in the consumer folder"),
    (m_key_mode, "private keys are readable by their owner only", "a client key readable by everyone (POSIX only)"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", action="store_true", help="baseline checks only, no mutation self-test")
    a = ap.parse_args()
    failed = 0
    print("FF-36 - MQTT lab CA")

    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "pki-mqtt"
        M.init(base, tester=True)
        print("\nBaseline (the tree pki-init would write, with the revocation tester):")
        res = checks(base)
        for name, ok, detail in res:
            print(f"  {'PASS' if ok else 'FAIL'}  {name}   [{detail}]")
            failed += 0 if ok else 1

        prod = Path(td) / "prod"
        M.init(prod, tester=False)
        crl = x509.load_pem_x509_crl((prod / "broker" / "crl.pem").read_bytes())
        ok = not (prod / "edge-old").exists() and len(list(crl)) == 0
        print(f"  {'PASS' if ok else 'FAIL'}  without --tester there is no revocation tester and the CRL is empty   [edge-old folder: {(prod / 'edge-old').exists()}, revoked: {len(list(crl))}]")
        failed += 0 if ok else 1

        rerun = Path(td) / "rerun"
        M.init(rerun, tester=True)
        first = (rerun / "edge" / "client.pem").read_bytes()
        M.init(rerun, tester=True)
        ok = (rerun / "edge" / "client.pem").read_bytes() == first
        print(f"  {'PASS' if ok else 'FAIL'}  a second run keeps the same identities (stable until the volume is removed)")
        failed += 0 if ok else 1

        caught = 0
        if not a.static and failed == 0:
            print("\nMutation self-test (each damage must be caught by the named check):")
            for fn, check_name, what in MUTATIONS:
                if fn is m_key_mode and not POSIX:
                    print(f"  SKIP  {what}")
                    continue
                work = Path(td) / f"m-{fn.__name__}"
                shutil.copytree(base, work)
                fn(work)
                bad = [n for n, ok, _ in checks(work) if not ok]
                hit = any(check_name in n for n in bad)
                print(f"  {'CAUGHT' if hit else 'MISSED'}  {what}   [{check_name!r}]")
                if hit:
                    caught += 1
                else:
                    failed += 1
                    print(f"           failing checks were: {bad}")
            print(f"\n{caught} mutations caught of {len(MUTATIONS)}")

    print(f"\nFF-36 {'FAIL' if failed else 'pass'} ({failed} problem(s)).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
