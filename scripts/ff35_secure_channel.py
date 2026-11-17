#!/usr/bin/env python3
"""
FF-35 - the OPC UA secure channel is enforced, not just offered (ADR-023, point 7; OPC-04).

Before: NoSecurity, so every run printed "Sending plain-text password" and any container on the
network could read the traffic or pose as a client. After: Sign and Encrypt only, the client must
present an application certificate that is on the server's trust list, the server's certificate is
pinned by the client, and the user account travels inside the encrypted channel.

  STATIC  plant/gateway/opcua_server.py, plant/opcua-sup/opcua_sup.py, plant/pki/uasec.py:
          no NoSecurity policy, both servers call secure_server, every client goes through
          make_client, uasec has no environment switch that turns security off.
          Self-tested with mutations of the source text.
  LIVE    against a running server, as a trusted identity and as everything else:
            - the endpoints on offer are Basic256Sha256 / SignAndEncrypt and nothing else;
            - POSITIVE CONTROL: the trusted identity with a good account opens a session and reads
              (a check that only proves refusals passes against a server that is simply broken);
            - a certificate that is not on the trust list is refused (BadCertificateUntrusted);
            - a trusted certificate with a wrong password, or anonymous, is refused;
            - a client with no security at all is refused;
            - a client pinned to a different server's certificate refuses this server;
            - no "plain-text password" warning is logged by the client.
          Locally (default) it generates a lab PKI, starts the gateway and opcua-sup and also proves
          revocation: remove a certificate from the trust folder and the same client is refused at
          once; put it back and it is accepted.

    python3 scripts/ff35_secure_channel.py                         # static + local live (no Docker)
    python3 scripts/ff35_secure_channel.py --static-only

In Docker (from inside the stack; /tmp/uasec.py is the module the images carry):
    docker cp scripts\\ff35_secure_channel.py vigilimen-collector:/tmp/ff35.py
    docker cp plant\\pki\\uasec.py vigilimen-collector:/tmp/uasec.py
    docker exec vigilimen-collector python3 /tmp/ff35.py --url opc.tcp://opcua-sup:4840/vigilimen/conv001/ --identity collector --peer opcua-sup --user historian --password h1st0r1an-demo
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANT = ROOT / "plant"
sys.path.insert(0, str(PLANT / "pki"))
sys.path.insert(0, str(Path(__file__).resolve().parent))      # /tmp/uasec.py inside a container

PASS, FAIL = "PASS", "FAIL"
URI = "urn:vigilimen:plant:conv001"
PATH = ("Enterprise", "PilbaraSite", "ProcessingArea", "ConveyingCell", "CONV001")


def code_of(text: str) -> str:
    text = re.sub(r'""".*?"""', "", text, flags=re.S)
    return "\n".join(re.sub(r"#.*", "", ln) for ln in text.splitlines())


# ---------------------------------------------------------------------------
# STATIC
# ---------------------------------------------------------------------------
FILES = {
    "gateway": PLANT / "gateway" / "opcua_server.py",
    "sup": PLANT / "opcua-sup" / "opcua_sup.py",
    "uasec": PLANT / "pki" / "uasec.py",
    "collector": PLANT / "historian" / "collector.py",
    "gw_hc": PLANT / "gateway" / "healthcheck.py",
    "sup_hc": PLANT / "opcua-sup" / "healthcheck.py",
    "df_gateway": PLANT / "gateway" / "Dockerfile",
    "df_sup": PLANT / "opcua-sup" / "Dockerfile",
    "df_collector": PLANT / "historian" / "Dockerfile",
    "df_scada": PLANT / "scada" / "Dockerfile",
}


def static(src: dict[str, str]) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []

    def check(n: str, ok: bool, why: str) -> None:
        out.append((PASS if ok else FAIL, n, why))

    code = {k: (v if k.startswith("df_") else code_of(v)) for k, v in src.items()}
    for k in ("gateway", "sup", "uasec"):
        check(f"{k}: the NoSecurity policy is never offered", "NoSecurity" not in code[k],
              "one NoSecurity endpoint beside the secure one is the endpoint every client will pick")
    for k in ("gateway", "sup"):
        check(f"{k}: the server is secured through uasec.secure_server", "uasec.secure_server(" in code[k],
              "a server that sets its own policy can drift from the trust-list rule")
    check("uasec: only Basic256Sha256 SignAndEncrypt is configured",
          "SecurityPolicyType.Basic256Sha256_SignAndEncrypt" in code["uasec"]
          and len(re.findall(r"SecurityPolicyType\.", code["uasec"])) == 1,
          "a second policy in the list is a downgrade path")
    check("uasec: the client certificate must be TRUSTED (trust list enforced)",
          "TRUSTED_VALIDATION" in code["uasec"] and "PEER_CLIENT" in code["uasec"] and "set_certificate_validator" in code["uasec"],
          "the first spike connected with an untrusted certificate because the validator was never attached")
    check("uasec: the trust folder is re-read at every session (revocation without restart)",
          "load_trust()" in code["uasec"], "a trust list read once at start cannot revoke anything")
    check("uasec: the server certificate is pinned and validated by the client",
          "server_certificate=" in code["uasec"] and "PEER_SERVER" in code["uasec"],
          "without it a client encrypts to whoever answers, so an impostor server reads the password")
    check("uasec: authorisation stays per node (a permission ruleset is passed, asyncua's secured default is read-only for User)",
          "permission_ruleset=_PerNodeRuleset()" in code["uasec"],
          "found by FF-26 on 16 Nov: with the secure channel on, every write by every account was refused"),
    check("uasec: no environment switch can turn security off",
          not re.search(r"environ[^\n]*(SECURITY|INSECURE|NOSEC|PLAIN|DISABLE)", code["uasec"], re.I),
          "a documented off switch is a downgrade attack waiting for a typo in a compose file")
    check("uasec: a missing PKI folder stops the service (fail closed)", "SystemExit" in code["uasec"],
          "falling back to no security when the certificates are missing hides exactly this failure")
    for k, n in (("collector", "the collector"), ("sup", "opcua-sup's upstream client"),
                 ("gw_hc", "the gateway health check"), ("sup_hc", "the opcua-sup health check")):
        check(f"{n} connects through uasec.make_client", "uasec.make_client(" in code[k] and "Client(" not in code[k].replace("make_client(", ""),
              "a plain asyncua Client() has no security and would be refused: or worse, would need NoSecurity back")
    for k in ("df_gateway", "df_sup", "df_collector", "df_scada"):
        bad = [ln for ln in src[k].splitlines()
               if re.match(r"\s*(FROM|RUN|COPY|ADD|ENV|CMD|ENTRYPOINT|WORKDIR|USER|EXPOSE|HEALTHCHECK|ARG)\b[^#\\]*\s#", ln)]
        check(f"{k[3:]} Dockerfile: no '#' after an instruction (Docker reads it as arguments)", not bad,
              f"{bad[:1]}. The 16 Nov build failed on '\"/secure\": not found' because a comment trailed a COPY")
    for k, n in (("df_gateway", "the gateway image"), ("df_sup", "the opcua-sup image"), ("df_collector", "the collector image")):
        check(f"{n} carries uasec.py", "pki/uasec.py" in src[k], "a service that imports uasec without the file cannot start")
    return out


def static_mutations(src: dict[str, str]):
    def m(label, key, a, b, must):
        assert a in src[key], (key, a)
        s = dict(src)
        s[key] = src[key].replace(a, b, 1)
        return label, s, must
    return [
        m("NoSecurity added to the gateway", "gateway", "await uasec.secure_server(",
          "server.set_security_policy([ua.SecurityPolicyType.NoSecurity]); await uasec.secure_server(",
          "gateway: the NoSecurity policy is never offered"),
        m("opcua-sup sets its own policy", "sup", "await uasec.secure_server(server, \"opcua-sup\")", "pass",
          "sup: the server is secured through uasec.secure_server"),
        m("trust validator detached", "uasec", "server.set_certificate_validator(validate)", "pass",
          "uasec: the client certificate must be TRUSTED (trust list enforced)"),
        m("trust list read once", "uasec", "await store.load_trust()", "pass",
          "uasec: the trust folder is re-read at every session (revocation without restart)"),
        m("server certificate not pinned", "uasec", "server_certificate=", "x=",
          "uasec: the server certificate is pinned and validated by the client"),
        m("default permission ruleset back", "uasec", ", permission_ruleset=_PerNodeRuleset())", ")",
          "uasec: authorisation stays per node (a permission ruleset is passed, asyncua's secured default is read-only for User)"),
        m("an off switch", "uasec", "pki = pki or pki_dir()\n    cert = _need(",
          "pki = pki or pki_dir()\n    if os.environ.get('VIGILIMEN_UA_INSECURE'): return\n    cert = _need(",
          "uasec: no environment switch can turn security off"),
        m("comment after a COPY", "df_gateway", "COPY pki/uasec.py /opt/vigilimen/gateway/uasec.py",
          "COPY pki/uasec.py /opt/vigilimen/gateway/uasec.py   # secure channel",
          "gateway Dockerfile: no '#' after an instruction (Docker reads it as arguments)"),
        m("collector back to a plain client", "collector",
          "await uasec.make_client(OPCUA_URL, \"collector\", \"opcua-sup\", OPCUA_USER, OPCUA_PASSWORD, timeout=4)",
          "Client(OPCUA_URL)", "the collector connects through uasec.make_client"),
    ]


# ---------------------------------------------------------------------------
# LIVE
# ---------------------------------------------------------------------------
class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


async def _read_one(c) -> str:
    """Open a session and read one node. Returns a short text, raises on any failure."""
    await c.connect()
    try:
        ns = await c.get_namespace_index(URI)
        n = c.nodes.objects
        for p in PATH:
            n = await n.get_child(f"{ns}:{p}")
        dv = await (await n.get_child(f"{ns}:Running")).read_data_value(raise_on_bad_status=False)
        return f"read Running -> {dv.Value.Value!r}"
    finally:
        try:
            await c.disconnect()
        except Exception:                                   # noqa: BLE001
            pass


async def _try(c) -> tuple[bool, str]:
    try:
        return True, await asyncio.wait_for(_read_one(c), 20)
    except BaseException as e:                              # noqa: BLE001  (a refusal can be any exception type)
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        return False, f"{type(e).__name__}: {str(e)[:140]}"


async def live(url: str, pki: Path, identity: str, peer: str, user: str, password: str,
               other_peer: str | None, label: str, revoke_dir: Path | None = None, writable: bool = False) -> list[tuple[str, str, str]]:
    import uasec
    from asyncua import Client, ua

    out: list[tuple[str, str, str]] = []

    def check(n: str, ok: bool, why: str) -> None:
        out.append((PASS if ok else FAIL, f"{label}: {n}", why))

    # 1. endpoints on offer (discovery is allowed on any channel; what it lists is what a client can choose)
    try:
        eps = await Client(url, timeout=6).connect_and_get_server_endpoints()
        modes = {(e.SecurityPolicyUri.rsplit("#", 1)[-1], e.SecurityMode.name) for e in eps}
        check("the only endpoint on offer is Basic256Sha256 / SignAndEncrypt",
              modes == {("Basic256Sha256", "SignAndEncrypt")}, f"offered: {sorted(modes)}")
    except Exception as e:                                  # noqa: BLE001
        check("the only endpoint on offer is Basic256Sha256 / SignAndEncrypt", False, f"could not list endpoints: {e}")

    # 2. positive control, with the plain-text warning captured
    cap = _Capture()
    root = logging.getLogger()
    root.addHandler(cap)
    old = root.level
    root.setLevel(logging.DEBUG)
    c = await uasec.make_client(url, identity, peer, user, password, timeout=8, pki=pki)
    ok, why = await _try(c)
    root.removeHandler(cap)
    root.setLevel(old)
    check(f"POSITIVE CONTROL: {identity} + {user} opens a session and reads", ok, why)
    plain = [m for m in cap.messages if "plain-text" in m.lower() or "plain text" in m.lower()]
    check("no 'plain-text password' warning: the account travels inside the encrypted channel", ok and not plain,
          f"warnings: {plain[:1]}")
    if not ok:                                              # every refusal below would pass against a broken server
        check("refusal checks skipped: the positive control failed, so they would prove nothing", False,
              "fix the positive control first")
        return out

    # 2b. authorisation survives the secure channel (the bug FF-26 found: every write refused on a secured policy)
    if writable:
        c = await uasec.make_client(url, identity, peer, user, password, timeout=8, pki=pki)
        await c.connect()
        try:
            ns = await c.get_namespace_index(URI)
            n = c.nodes.objects
            for p in PATH:
                n = await n.get_child(f"{ns}:{p}")
            start = await n.get_child(f"{ns}:StartCommand")
            cur = await start.read_value()
            try:
                await start.write_value(cur)               # write the value back: no change to the plant
                w_ok, w_why = True, f"wrote StartCommand={cur!r} back"
            except Exception as e:                          # noqa: BLE001
                w_ok, w_why = False, f"{type(e).__name__}: {str(e)[:100]}"
            meas = await n.get_child(f"{ns}:BeltSpeed_mps")
            try:
                await meas.write_value(await meas.read_value())
                m_ok = True
            except Exception:                               # noqa: BLE001
                m_ok = False
        finally:
            await c.disconnect()
        check(f"a PERMITTED write works over the secure channel ({user} writes StartCommand)", w_ok, w_why)
        check(f"a write to a MEASUREMENT is still refused ({user}, BeltSpeed_mps)", not m_ok,
              "the node is writable: authorisation per node was lost")

    # 3. a certificate nobody trusts
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        for d in ("identities", "peers"):
            (t / d).mkdir()
        master = t / "m"
        master.mkdir()
        uasec._store(master, "evil-client")
        for ext in (".der", ".key"):
            shutil.copy(master / f"evil-client{ext}", t / "identities" / f"evil-client{ext}")
        shutil.copy(pki / "peers" / f"{peer}.der", t / "peers" / f"{peer}.der")
        c = await uasec.make_client(url, "evil-client", peer, user, password, timeout=8, pki=t)
        ok3, why3 = await _try(c)
    check("a certificate that is not on the trust list is refused (BadCertificateUntrusted)",
          (not ok3) and "BadCertificateUntrusted" in why3, f"{'connected!' if ok3 else why3}")

    # 4. trusted certificate, wrong password / anonymous
    c = await uasec.make_client(url, identity, peer, user, "not-the-password", timeout=8, pki=pki)
    ok4, why4 = await _try(c)
    check("trusted certificate, wrong password: refused", not ok4, "connected with a wrong password!" if ok4 else why4)
    c = Client(url, timeout=8)
    await uasec.secure_client(c, identity, peer, pki)       # no set_user: anonymous
    ok5, why5 = await _try(c)
    check("trusted certificate, anonymous: refused", not ok5, "connected anonymously!" if ok5 else why5)

    # 5. no security at all
    c = Client(url, timeout=8)
    c.set_user(user)
    c.set_password(password)
    ok6, why6 = await _try(c)
    check("no security (a plain client): refused", not ok6, "connected in the clear!" if ok6 else why6)

    # 6. server authentication: pinned to another server's certificate
    if other_peer:
        c = await uasec.make_client(url, identity, other_peer, user, password, timeout=8, pki=pki)
        ok7, why7 = await _try(c)
        check(f"a client pinned to {other_peer}'s certificate refuses this server", not ok7,
              "connected to the wrong server!" if ok7 else why7)

    # 7. revocation, local only
    if revoke_dir is not None:
        f = revoke_dir / f"{identity}.der"
        saved = f.read_bytes()
        f.unlink()
        c = await uasec.make_client(url, identity, peer, user, password, timeout=8, pki=pki)
        ok8, why8 = await _try(c)
        f.write_bytes(saved)
        c = await uasec.make_client(url, identity, peer, user, password, timeout=8, pki=pki)
        ok9, why9 = await _try(c)
        check(f"revocation: {identity} removed from the trust folder is refused with no restart", not ok8,
              "still accepted after removal!" if ok8 else why8)
        check(f"revocation: put back, it is accepted again (the refusal was the trust list, not a broken server)", ok9, why9)
    return out


def _wait_port(port: int, secs: float = 30) -> bool:
    end = time.time() + secs
    while time.time() < end:
        try:
            socket.create_connection(("127.0.0.1", port), 0.5).close()
            return True
        except OSError:
            time.sleep(0.3)
    return False


async def local_live() -> list[tuple[str, str, str]]:
    import uasec

    out: list[tuple[str, str, str]] = []
    with tempfile.TemporaryDirectory() as td:
        pki = Path(td) / "pki"
        uasec.init(pki)
        procs = []
        try:
            gw_port, sup_port = 14850, 14851
            env = dict(os.environ, PYTHONUNBUFFERED="1", VIGILIMEN_PLC_LINK="off", VIGILIMEN_PKI_DIR=str(pki / "gateway"))
            procs.append(subprocess.Popen([sys.executable, str(PLANT / "gateway" / "opcua_server.py"), "--port", str(gw_port)],
                                          env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            env2 = dict(os.environ, PYTHONUNBUFFERED="1", VIGILIMEN_PKI_DIR=str(pki / "opcua-sup"))
            procs.append(subprocess.Popen([sys.executable, str(PLANT / "opcua-sup" / "opcua_sup.py"), "--port", str(sup_port),
                                           "--upstream", f"opc.tcp://127.0.0.1:{gw_port}/vigilimen/conv001/"],
                                          env=env2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            if not (_wait_port(gw_port) and _wait_port(sup_port)):
                return [(FAIL, "local servers start", "the gateway or opcua-sup did not open its port in 30 s")]
            await asyncio.sleep(2)
            out += await live(f"opc.tcp://127.0.0.1:{gw_port}/vigilimen/conv001/", pki / "scada", "scada", "gateway",
                              "engineer", "eng1neer-demo", "opcua-sup", "gateway", revoke_dir=pki / "gateway" / "trust", writable=True)
            out += await live(f"opc.tcp://127.0.0.1:{sup_port}/vigilimen/conv001/", pki / "collector", "collector", "opcua-sup",
                              "historian", "h1st0r1an-demo", None, "opcua-sup", revoke_dir=pki / "opcua-sup" / "trust")
            # cross-check: the collector (a read identity) is trusted by opcua-sup but must NOT be accepted by the gateway
            import uasec as u
            x = Path(td) / "collector-vs-gateway"
            for d in ("identities", "peers"):
                (x / d).mkdir(parents=True)
            for ext in (".der", ".key"):
                shutil.copy(pki / "collector" / "identities" / f"collector{ext}", x / "identities" / f"collector{ext}")
            shutil.copy(pki / "gateway" / "identities" / "gateway.der", x / "peers" / "gateway.der")
            c = await u.make_client(f"opc.tcp://127.0.0.1:{gw_port}/vigilimen/conv001/", "collector", "gateway",
                                    "engineer", "eng1neer-demo", timeout=8, pki=x)
            ok, why = await _try(c)
            out.append((PASS if not ok and "BadCertificateUntrusted" in why else FAIL,
                        "gateway: the collector (a read identity) is not on the gateway's trust list: refused",
                        "connected!" if ok else why))
        finally:
            for p in procs:
                p.terminate()
            for p in procs:
                try:
                    p.wait(5)
                except Exception:                           # noqa: BLE001
                    p.kill()
    return out


def report(title: str, rows) -> int:
    print(title)
    if not rows:
        return 0
    width = max(len(n) for _, n, _ in rows)
    for s, n, why in rows:
        print(f"  {s}  {n.ljust(width)}")
        if s == FAIL or os.environ.get("FF35_VERBOSE"):
            print(f"        {why}")
    return sum(1 for r in rows if r[0] == FAIL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="LIVE against this endpoint (inside the stack)")
    ap.add_argument("--identity", default="collector")
    ap.add_argument("--peer", default="opcua-sup")
    ap.add_argument("--other-peer", default=None, help="another server whose certificate this client also holds")
    ap.add_argument("--user", default="historian")
    ap.add_argument("--password", default="h1st0r1an-demo")
    ap.add_argument("--writable", action="store_true", help="also prove a permitted write works and a measurement write is refused (the gateway)")
    ap.add_argument("--static-only", action="store_true")
    ap.add_argument("--live-only", action="store_true")
    a = ap.parse_args()
    failed = unseen = lf = 0

    if not a.live_only:
        src = {k: p.read_text(encoding="utf-8") for k, p in FILES.items()}
        failed = report("FF-35 - the OPC UA secure channel is enforced\n\n  STATIC", static(src))
        print("\n  self-test - each mutation of the source must be caught:")
        for label, mutated, must in static_mutations(src):
            caught = any(s == FAIL and n == must for s, n, _ in static(mutated))
            print(f"  {PASS if caught else FAIL}  caught: {label}")
            unseen += 0 if caught else 1
    else:
        print("FF-35 - the OPC UA secure channel is enforced (LIVE only)")

    if a.url:
        print(f"\n  LIVE ({a.url})")
        rows = asyncio.run(live(a.url, Path(os.environ.get("VIGILIMEN_PKI_DIR", "/pki")), a.identity, a.peer,
                                a.user, a.password, a.other_peer, a.peer, writable=a.writable))
        lf = report("", rows)
    elif not a.static_only:
        print("\n  LIVE, local: lab PKI generated in a temporary folder, gateway and opcua-sup started on loopback")
        lf = report("", asyncio.run(local_live()))
    else:
        print("\n  LIVE skipped. This does not prove the running server.")

    if failed or unseen or lf:
        print("\nFF-35 FAIL")
        return 1
    print("\nFF-35 pass" + (" (STATIC only)" if a.static_only else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
