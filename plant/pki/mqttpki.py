"""Lab mini-CA for MQTT (ADR-020 point 2, S5). Separate from the OPC UA lab PKI (uasec.py).

What it gives:  a certificate authority that signs one certificate per MQTT party (broker, edge, consumer),
and a CRL, so the broker can verify every client by CHAIN and refuse a revoked one. The broker derives the
client's identity from the certificate CN (Mosquitto: use_identity_as_username), and the ACL is keyed on it.

What it is NOT: production PKI. One online CA key, no intermediate, no HSM, no OCSP, no rotation, 30-day CRL
that nobody republishes. Production needs an offline root, an issuing CA, short-lived certificates and
automated revocation (IEC 62443-3-3 SR 1.8 / 1.9). This proves the mechanism and the refusal.

Why it is separate from uasec.py: OPC UA trusts exact self-signed certificates (an allow-list). MQTT trusts a
CA, so a certificate the CA signed is accepted unless revoked. Two trust models must not share a volume, or a
certificate for one protocol could be presented to the other.

Layout under <root> (the `pki-mqtt` volume). Each service folder is mounted read-only at its own path:

    _ca/ca.key  ca.pem  serial-state          CA private key. NEVER mounted into any service.
    broker/    ca.pem  server.pem  server.key  crl.pem
    edge/      ca.pem  client.pem  client.key
    consumer/  ca.pem  client.pem  client.key
    edge-old/  ca.pem  client.pem  client.key   only with --tester: the identity that gets revoked (FF-36)

Names: the certificate CN is the identity and the ACL key. Servers carry their DNS names in the SAN (so
verification by host name works, unlike the OPC UA lab certificates).

    python3 mqttpki.py init /pki-mqtt [--tester]
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sys
from pathlib import Path

CA_NAME = "vigilimen-mqtt-lab-ca"
CA_DAYS = 3650
LEAF_DAYS = 365
CRL_DAYS = 30

SERVER = {"broker": ["broker", "localhost"]}        # server identity -> DNS names in the SAN
CLIENTS = ["edge", "consumer"]                       # client identities (one certificate each)
TESTER_CLIENTS = ["edge-old"]                        # --tester only; revoked by init
REVOKED = ["edge-old"]                               # who goes on the CRL
UIDS = {"broker": 1883, "edge": 10004, "consumer": 10005, "edge-old": 10006}   # broker uid to confirm at build


def _utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def new_key():
    from cryptography.hazmat.primitives.asymmetric import ec
    return ec.generate_private_key(ec.SECP256R1())


def make_ca(key=None, name: str = CA_NAME, is_ca: bool = True, path_length: int | None = 0, days: int = CA_DAYS):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.x509.oid import NameOID

    key = key or new_key()
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = _utc()
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=days))
            .add_extension(x509.BasicConstraints(ca=is_ca, path_length=path_length if is_ca else None), True)
            .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=True,
                                         crl_sign=True, encipher_only=False, decipher_only=False), True)
            .sign(key, hashes.SHA256()))
    return cert, key


def make_leaf(ca_cert, ca_key, cn: str, server: bool, dns: list[str] | None = None, days: int = LEAF_DAYS,
              eku: list | None = None, key=None, not_before: dt.datetime | None = None):
    """A leaf certificate. server=True -> serverAuth, else clientAuth. `eku` overrides (used by FF-36 mutations)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    key = key or new_key()
    now = _utc()
    names = dns if dns is not None else ([cn, "localhost"] if server else [cn])
    usage = eku if eku is not None else [ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]
    nb = not_before or (now - dt.timedelta(days=1))
    cert = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)]))
            .issuer_name(ca_cert.subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(nb).not_valid_after(nb + dt.timedelta(days=days + 1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(n) for n in names]), False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                         crl_sign=False, encipher_only=False, decipher_only=False), True)
            .add_extension(x509.ExtendedKeyUsage(usage), False)
            .sign(ca_key, hashes.SHA256()))
    return cert, key


def make_crl(ca_cert, ca_key, revoked_serials: list[int], days: int = CRL_DAYS):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    now = _utc()
    b = (x509.CertificateRevocationListBuilder().issuer_name(ca_cert.subject)
         .last_update(now - dt.timedelta(hours=1)).next_update(now + dt.timedelta(days=days)))
    for s in revoked_serials:
        b = b.add_revoked_certificate(x509.RevokedCertificateBuilder().serial_number(s).revocation_date(now).build())
    return b.sign(ca_key, hashes.SHA256())


def pem(cert) -> bytes:
    from cryptography.hazmat.primitives import serialization as s
    return cert.public_bytes(s.Encoding.PEM)


def key_pem(key) -> bytes:
    from cryptography.hazmat.primitives import serialization as s
    return key.private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption())


def crl_pem(crl) -> bytes:
    from cryptography.hazmat.primitives import serialization as s
    return crl.public_bytes(s.Encoding.PEM)


def _write(path: Path, data: bytes, mode: int) -> None:
    path.write_bytes(data)
    os.chmod(path, mode)


def _load_or_create_ca(ca_dir: Path):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization as s

    cert_p, key_p = ca_dir / "ca.pem", ca_dir / "ca.key"
    if cert_p.exists() and key_p.exists():
        return x509.load_pem_x509_certificate(cert_p.read_bytes()), s.load_pem_private_key(key_p.read_bytes(), None)
    cert, key = make_ca()
    _write(cert_p, pem(cert), 0o644)
    _write(key_p, key_pem(key), 0o600)
    return cert, key


def _load_leaf(master: Path, ident: str):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization as s
    c, k = master / f"{ident}.pem", master / f"{ident}.key"
    if c.exists() and k.exists():
        return x509.load_pem_x509_certificate(c.read_bytes()), s.load_pem_private_key(k.read_bytes(), None)
    return None


def init(root: Path, tester: bool = False) -> None:
    ca_dir = root / "_ca"
    ca_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(ca_dir, 0o700)
    ca_cert, ca_key = _load_or_create_ca(ca_dir)

    master = ca_dir / "issued"                       # all issued leaves, inside _ca (never mounted)
    master.mkdir(exist_ok=True)
    os.chmod(master, 0o700)
    clients = CLIENTS + (TESTER_CLIENTS if tester else [])
    leaves = {}
    for ident, dns in SERVER.items():
        got = _load_leaf(master, ident)
        if got is None:
            got = make_leaf(ca_cert, ca_key, ident, True, dns)
            _write(master / f"{ident}.pem", pem(got[0]), 0o644)
            _write(master / f"{ident}.key", key_pem(got[1]), 0o600)
        leaves[ident] = got
    for ident in clients:
        got = _load_leaf(master, ident)
        if got is None:
            got = make_leaf(ca_cert, ca_key, ident, False)
            _write(master / f"{ident}.pem", pem(got[0]), 0o644)
            _write(master / f"{ident}.key", key_pem(got[1]), 0o600)
        leaves[ident] = got

    crl = make_crl(ca_cert, ca_key, [leaves[i][0].serial_number for i in REVOKED if i in leaves])

    def fresh(folder: Path) -> Path:
        # Folders are kept and only their files replaced: a running container's subpath mount points at the folder.
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.iterdir():
            old.unlink()
        return folder

    b = fresh(root / "broker")
    shutil.copy2(ca_dir / "ca.pem", b / "ca.pem")
    _write(b / "server.pem", pem(leaves["broker"][0]), 0o644)
    _write(b / "server.key", key_pem(leaves["broker"][1]), 0o600)
    _write(b / "crl.pem", crl_pem(crl), 0o644)
    for ident in clients:
        d = fresh(root / ident)
        shutil.copy2(ca_dir / "ca.pem", d / "ca.pem")
        _write(d / "client.pem", pem(leaves[ident][0]), 0o644)
        _write(d / "client.key", key_pem(leaves[ident][1]), 0o600)

    for ident in ["broker", *clients]:
        uid = UIDS.get(ident, 0)
        for p in [root / ident, *(root / ident).rglob("*")]:
            try:
                os.chown(p, uid, uid)
            except OSError:                          # local, non-root runs: ownership is irrelevant
                pass
        print(f"mqttpki: {ident}: {sorted(x.name for x in (root / ident).iterdir())}", flush=True)
    print(f"mqttpki: CRL lists {len([i for i in REVOKED if i in leaves])} revoked certificate(s)", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("root")
    p.add_argument("--tester", action="store_true", default=os.environ.get("VIGILIMEN_PKI_TESTER") == "1")
    a = ap.parse_args()
    init(Path(a.root), a.tester)
    sys.exit(0)
