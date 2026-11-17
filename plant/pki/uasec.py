"""OPC UA secure channel for the lab (ADR-023, point 7).

What it gives:  Basic256Sha256 / Sign and Encrypt on every OPC UA endpoint, application
certificates that must be on the server's trust list, and the existing user accounts carried
INSIDE the encrypted channel (so no more "Sending plain-text password").

What it is NOT: a PKI. Every certificate is self-signed and the trust list is a directory of
exact certificates (an allow-list). There is no CA, no CRL, no rotation, no HSM. Production
needs a certificate authority with revocation (IEC 62443-3-3 SR 1.8 / 1.9); this proves the
mechanism and the refusals, not the operations.

Layout, one folder per service (mounted read-only at /pki, so a service sees ONLY its own keys):

    identities/<id>.der  <id>.key  <id>.pem  <id>-key.pem   certificates and keys it can act as
    trust/<id>.der                                          clients this server accepts
    peers/<id>.der                                          servers this client will talk to

Fail closed: a server without a PKI folder, or with an empty trust list, refuses to start / refuses
everybody. There is no "no security" fallback switch, on purpose.

    python3 uasec.py init /pki [--tester]       (the pki-init container)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# The plan: who holds which key, who trusts whom. This IS the access-control list.
# ---------------------------------------------------------------------------
HOLDS = {                              # service folder -> identities it holds (certificate + key)
    "gateway":   ["gateway", "gateway-local"],
    "opcua-sup": ["opcua-sup", "opcua-sup-local"],
    "collector": ["collector"],
    "scada":     ["scada"],          # ONE identity: FUXA is one container with one client certificate (ADR-023, point 7)
}
TRUSTS = {                             # server folder -> client identities it accepts
    "gateway":   ["opcua-sup", "scada", "gateway-local"],
    "opcua-sup": ["collector", "scada", "opcua-sup-local"],
}
PEERS = {                              # client folder -> server certificates it will connect to
    "gateway":   ["gateway"],                      # its own health check, over localhost
    "opcua-sup": ["gateway", "opcua-sup"],         # mirrors the gateway; own health check
    "collector": ["opcua-sup"],
    "scada":     ["opcua-sup", "gateway"],      # FUXA does NOT use these: it accepts any server certificate. For test scripts only.
}
UIDS = {"gateway": 10001, "collector": 10002, "opcua-sup": 10003, "scada": 0}
# FUXA (node-opcua) names itself urn:<hostname>:NodeOPCUA-Client by default. The certificate carries both names, so the
# server's check "the client's URI is in its certificate" passes whichever one FUXA announces.
EXTRA_URIS = {"scada": ["urn:scada:NodeOPCUA-Client"]}
SERVER_NAMES = {"gateway": ["gateway", "fw-cell", "localhost"], "opcua-sup": ["opcua-sup", "localhost"]}


def app_uri(identity: str) -> str:
    return f"urn:vigilimen:{identity}"


# ---------------------------------------------------------------------------
# Generation (pki-init)
# ---------------------------------------------------------------------------
def _make(identity: str):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, identity)])
    now = dt.datetime.now(dt.timezone.utc)
    dns = [x509.DNSName(n) for n in SERVER_NAMES.get(identity, [identity, "localhost"])]
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(u) for u in [app_uri(identity), *EXTRA_URIS.get(identity, [])]] + dns), False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=True,
                                         data_encipherment=True, key_agreement=False, key_cert_sign=True,
                                         crl_sign=False, encipher_only=False, decipher_only=False), True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]), False)
            .sign(key, hashes.SHA256()))
    return cert, key


def _write(path: Path, data: bytes, mode: int) -> None:
    path.write_bytes(data)
    os.chmod(path, mode)


def _store(master: Path, identity: str) -> None:
    """Create the identity once; keep it across runs (the certificate is stable until the volume is removed)."""
    from cryptography.hazmat.primitives import serialization as s

    if (master / f"{identity}.der").exists() and (master / f"{identity}.key").exists():
        return
    cert, key = _make(identity)
    _write(master / f"{identity}.der", cert.public_bytes(s.Encoding.DER), 0o644)
    _write(master / f"{identity}.pem", cert.public_bytes(s.Encoding.PEM), 0o644)
    _write(master / f"{identity}.key", key.private_bytes(s.Encoding.DER, s.PrivateFormat.PKCS8, s.NoEncryption()), 0o600)
    _write(master / f"{identity}-key.pem", key.private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption()), 0o600)


def init(root: Path, tester: bool = False) -> None:
    holds = {k: list(v) for k, v in HOLDS.items()}
    trusts = {k: list(v) for k, v in TRUSTS.items()}
    peers = {k: list(v) for k, v in PEERS.items()}
    if tester:                         # FF-26/28 only: the collector container plays operator
        holds["collector"].append("tester")
        for s in trusts.values():
            s.append("tester")
        peers["collector"] += ["gateway"]

    master = root / "_master"          # never mounted into any service
    master.mkdir(parents=True, exist_ok=True)
    os.chmod(master, 0o700)
    for ids in holds.values():
        for i in ids:
            _store(master, i)

    for svc in HOLDS:
        base = root / svc
        # Rebuilt every run, so a stale trust entry cannot survive. The FOLDERS are kept and only their files
        # replaced: a running container's subpath mount points at the folder, and deleting it would strand it.
        for d in ("identities", "trust", "peers"):
            (base / d).mkdir(parents=True, exist_ok=True)
            for old in (base / d).iterdir():
                old.unlink()
        for i in holds[svc]:
            for ext in (".der", ".pem", ".key", "-key.pem"):
                shutil.copy2(master / f"{i}{ext}", base / "identities" / f"{i}{ext}")
        for i in trusts.get(svc, []):
            shutil.copy2(master / f"{i}.der", base / "trust" / f"{i}.der")
        for i in peers.get(svc, []):
            for ext in (".der", ".pem"):
                shutil.copy2(master / f"{i}{ext}", base / "peers" / f"{i}{ext}")
        uid = UIDS[svc]
        for p in [base, *base.rglob("*")]:
            try:
                os.chown(p, uid, uid)
            except OSError:                            # local, non-root runs: ownership is irrelevant
                pass
        print(f"pki: {svc}: holds {holds[svc]}, trusts {trusts.get(svc, [])}, peers {peers.get(svc, [])}", flush=True)


# ---------------------------------------------------------------------------
# Use (servers and clients)
# ---------------------------------------------------------------------------
def pki_dir() -> Path:
    return Path(os.environ.get("VIGILIMEN_PKI_DIR", "/pki"))


def _need(path: Path) -> Path:
    if not path.exists():
        raise SystemExit(f"uasec: {path} is missing. The secure channel has no off switch: run the pki-init service "
                         f"(docker compose up -d) or generate a lab PKI with 'python3 uasec.py init <dir>'.")
    return path


class _PerNodeRuleset:
    """Authorisation stays PER NODE (ADR-017); this ruleset only refuses anonymous.

    asyncua attaches its SimpleRoleRuleset to every SECURED policy (and to none for NoSecurity), and that ruleset lets
    only Admin write. Turning the secure channel on therefore silently made both accounts read-only: FF-26 found it on
    16 Nov (BadUserAccessDenied on a write that had worked unsecured). The node's own access level still decides who
    can write what, and adding or deleting nodes stays Admin-only inside asyncua's address space."""

    def check_validity(self, user, action_type_id, body):
        from asyncua.server.users import UserRole
        return user is not None and user.role != UserRole.Anonymous


async def secure_server(server, identity: str, pki: Path | None = None) -> None:
    """Sign and Encrypt only; clients must present a certificate on the trust list."""
    from asyncua import ua
    from asyncua.crypto.truststore import TrustStore
    from asyncua.crypto.validator import CertificateValidator, CertificateValidatorOptions

    pki = pki or pki_dir()
    cert = _need(pki / "identities" / f"{identity}.der")
    key = _need(pki / "identities" / f"{identity}.key")
    trust = _need(pki / "trust")
    await server.set_application_uri(app_uri(identity))
    await server.load_certificate(str(cert))
    await server.load_private_key(str(key))
    server.set_security_policy([ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt], permission_ruleset=_PerNodeRuleset())
    store = TrustStore([trust], [])
    await store.load()
    opts = CertificateValidatorOptions.TRUSTED_VALIDATION | CertificateValidatorOptions.PEER_CLIENT
    validator = CertificateValidator(opts, store)

    async def validate(cert, app_description):
        await store.load_trust()               # read the trust folder at every session: removing a file revokes at once
        await validator.validate(cert, app_description)

    server.set_certificate_validator(validate)
    n = len(list(trust.glob("*.der")))
    print(f"uasec: {identity}: Basic256Sha256 SignAndEncrypt, {n} client certificate(s) trusted", flush=True)


async def secure_client(client, identity: str, peer: str, pki: Path | None = None) -> None:
    """Present `identity`; accept only the pinned certificate of `peer`. Call before connect()."""
    from asyncua import ua
    from asyncua.crypto.security_policies import SecurityPolicyBasic256Sha256
    from asyncua.crypto.truststore import TrustStore
    from asyncua.crypto.validator import CertificateValidator, CertificateValidatorOptions

    pki = pki or pki_dir()
    client.application_uri = app_uri(identity)
    await client.set_security(
        SecurityPolicyBasic256Sha256,
        certificate=str(_need(pki / "identities" / f"{identity}.der")),
        private_key=str(_need(pki / "identities" / f"{identity}.key")),
        server_certificate=str(_need(pki / "peers" / f"{peer}.der")),
        mode=ua.MessageSecurityMode.SignAndEncrypt)
    store = TrustStore([_need(pki / "peers")], [])
    await store.load()
    opts = CertificateValidatorOptions.TRUSTED_VALIDATION | CertificateValidatorOptions.PEER_SERVER
    client.certificate_validator = CertificateValidator(opts, store).validate


async def make_client(url: str, identity: str, peer: str, user: str, password: str, timeout: float = 4,
                      pki: Path | None = None):
    """A configured, NOT yet connected, asyncua Client (set_user/set_password go before connect())."""
    from asyncua import Client

    c = Client(url, timeout=timeout)
    await secure_client(c, identity, peer, pki)
    c.set_user(user)
    c.set_password(password)
    return c


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("root")
    p.add_argument("--tester", action="store_true", default=os.environ.get("VIGILIMEN_PKI_TESTER") == "1")
    a = ap.parse_args()
    init(Path(a.root), a.tester)
    sys.exit(0)
