"""FF-38 - the DMZ broker really behaves as ADR-020 and the hardening table say (LIVE part of FF-36 / FF-37).

Runs INSIDE a container on net_dmz (tools\\validate-broker.ps1 starts it), with the lab certificates mounted at
/pki/<identity>/ (ca.pem, client.pem, client.key). It speaks MQTT 3.1.1 itself over Python's ssl module, from the
wire format, so that what it reports is the broker's behaviour and not a client library's defaults.

    --phase main                       the refusals, the ACL and the limits
    --phase revocation --identity edge-old --expect accepted|refused|report

A refusal is only evidence when a positive control passes in the same run: a client that connects fine is what
makes "the same client refused" mean something.

What it does NOT prove: that the broker stays up under a flood (that is FF-29), anything about the WAN, or how
Mosquitto behaves in versions other than the one the compose pins.
"""

from __future__ import annotations

import argparse
import warnings
import socket
import ssl
import sys
import tempfile
import time
from pathlib import Path

for cand in ("/opt/vigilimen", str(Path(__file__).resolve().parent.parent / "plant" / "pki")):
    sys.path.insert(0, cand)

warnings.filterwarnings("ignore", category=DeprecationWarning)
HOST, PORT = "broker", 8883
PKI = Path("/pki")
ROOT_TOPIC = "vigilimen/v1/"
T_OK = ROOT_TOPIC + "lab/CONV-001/ff38"

fails = 0


def report(status: str, name: str, detail: str = "") -> None:
    global fails
    if status == "FAIL":
        fails += 1
    print(f"  {status}  {name}" + (f"   [{detail}]" if detail else ""), flush=True)


# ---------------------------------------------------------------------------
# A minimal MQTT 3.1.1 client (QoS 0 only)
# ---------------------------------------------------------------------------
def _varlen(n: int) -> bytes:
    out = b""
    while True:
        b, n = n % 128, n // 128
        out += bytes([b | (128 if n else 0)])
        if not n:
            return out


def _utf(s: str) -> bytes:
    b = s.encode()
    return len(b).to_bytes(2, "big") + b


class Mqtt:
    def __init__(self, sock: ssl.SSLSocket):
        self.s = sock

    def _read(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed by the broker")
            buf += chunk
        return buf

    def packet(self, timeout: float):
        """-> (type, flags, payload) or None on timeout; ConnectionError when the broker closes."""
        self.s.settimeout(timeout)
        try:
            h = self._read(1)[0]
        except (socket.timeout, TimeoutError):
            return None
        mult, n = 1, 0
        while True:
            b = self._read(1)[0]
            n += (b & 127) * mult
            mult *= 128
            if not b & 128:
                break
        self.s.settimeout(5)
        return h >> 4, h & 15, self._read(n)

    def connect(self, client_id: str) -> int:
        body = _utf("MQTT") + bytes([4, 0x02]) + (30).to_bytes(2, "big") + _utf(client_id)
        self.s.sendall(bytes([0x10]) + _varlen(len(body)) + body)
        p = self.packet(5)
        if p is None or p[0] != 2:
            raise ConnectionError(f"no CONNACK (got {p})")
        return p[2][1]

    def subscribe(self, topic: str) -> int:
        body = (1).to_bytes(2, "big") + _utf(topic) + bytes([0])
        self.s.sendall(bytes([0x82]) + _varlen(len(body)) + body)
        p = self.packet(5)
        if p is None or p[0] != 9:
            raise ConnectionError(f"no SUBACK (got {p})")
        return p[2][2]

    def publish(self, topic: str, payload: bytes, retain: bool = False) -> None:
        body = _utf(topic) + payload
        self.s.sendall(bytes([0x30 | (1 if retain else 0)]) + _varlen(len(body)) + body)

    def messages(self, seconds: float) -> list[tuple[str, bytes]]:
        """Collect PUBLISH packets for `seconds`. ConnectionError if the broker closes the connection."""
        out, end = [], time.time() + seconds
        while time.time() < end:
            p = self.packet(max(0.05, end - time.time()))
            if p is None:
                continue
            if p[0] == 3:
                tl = int.from_bytes(p[2][:2], "big")
                out.append((p[2][2:2 + tl].decode(), p[2][2 + tl:]))
        return out

    def close(self) -> None:
        try:
            self.s.close()
        except OSError:
            pass


def context(identity: str | None = None, cert: tuple[str, str] | None = None, minv=None, maxv=None) -> ssl.SSLContext:
    ca = next(PKI.glob("*/ca.pem"))
    c = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    c.load_verify_locations(str(ca))
    c.check_hostname = True
    if identity:
        c.load_cert_chain(str(PKI / identity / "client.pem"), str(PKI / identity / "client.key"))
    elif cert:
        c.load_cert_chain(*cert)
    if minv is not None:
        c.minimum_version = minv
    if maxv is not None:
        c.maximum_version = maxv
    return c


def session(ctx: ssl.SSLContext, client_id: str, server_hostname: str = HOST):
    """-> (Mqtt, tls_version) once CONNACK accepted. Raises on any refusal."""
    raw = socket.create_connection((HOST, PORT), timeout=5)
    try:
        tls = ctx.wrap_socket(raw, server_hostname=server_hostname)
        m = Mqtt(tls)
        rc = m.connect(client_id)
    except Exception:
        raw.close()
        raise
    if rc != 0:
        m.close()
        raise ConnectionError(f"CONNACK refused, code {rc}")
    return m, tls.version()


def attempt(ctx: ssl.SSLContext, client_id: str, server_hostname: str = HOST):
    try:
        m, v = session(ctx, client_id, server_hostname)
        return True, m, v
    except Exception as e:                                           # a refusal, in whatever form
        return False, None, f"{type(e).__name__}: {str(e)[:110]}"


# ---------------------------------------------------------------------------
def phase_main() -> None:
    print("FF-38 - DMZ broker, live (main)\n")

    print("Positive controls (without these, the refusals below prove nothing):")
    ok, edge_probe, v = attempt(context("edge"), "ff38-edge-probe")
    report("PASS" if ok else "FAIL", "the edge connects with its certificate over TLS", f"negotiated {v}")
    if not ok:
        print("\nFF-38 cannot go on: the positive control failed. Read the broker log first (docker compose logs broker).")
        sys.exit(1)
    edge_probe.close()
    ok, cons_probe, v = attempt(context("consumer"), "ff38-cons-probe")
    report("PASS" if ok else "FAIL", "the consumer connects with its certificate over TLS", f"negotiated {v}")
    if ok:
        cons_probe.close()
    ok, m, v = attempt(context("edge", minv=ssl.TLSVersion.TLSv1_2, maxv=ssl.TLSVersion.TLSv1_2), "ff38-tls12")
    report("PASS" if ok else "FAIL", "TLS 1.2 is accepted", v)
    if ok:
        m.close()
    ok, m, v = attempt(context("edge", minv=ssl.TLSVersion.TLSv1_3), "ff38-tls13")
    report("PASS" if ok else "FAIL", "TLS 1.3 is accepted", v)
    if ok:
        m.close()

    print("\nRefusals:")
    ok, m, why = attempt(context(None), "ff38-nocert")
    report("PASS" if not ok else "FAIL", "a client with NO certificate is refused", why if not ok else "it was accepted")
    if ok:
        m.close()

    import mqttpki as M
    rogue, rkey = M.make_ca()
    leaf, lkey = M.make_leaf(rogue, rkey, "edge", False)
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "c.pem").write_bytes(M.pem(leaf))
        (Path(td) / "k.pem").write_bytes(M.key_pem(lkey))
        ok, m, why = attempt(context(None, cert=(str(Path(td) / "c.pem"), str(Path(td) / "k.pem"))), "ff38-rogue")
    report("PASS" if not ok else "FAIL", "a certificate with the right name ('edge') signed by ANOTHER CA is refused", why if not ok else "it was accepted")
    if ok:
        m.close()

    ok, m, why = attempt(context("edge"), "ff38-badname", server_hostname="not-the-broker")
    report("PASS" if not ok else "FAIL", "the client verifies the broker's name (a wrong name is refused by the client)", why if not ok else "it was accepted")
    if ok:
        m.close()

    try:
        c = context("edge", minv=ssl.TLSVersion.TLSv1_1, maxv=ssl.TLSVersion.TLSv1_1)
        c.set_ciphers("ALL:@SECLEVEL=0")
        ok, m, why = attempt(c, "ff38-tls11")
        if ok:
            m.close()
            report("FAIL", "TLS 1.1 is refused", "it was accepted")
        elif "NO_PROTOCOLS_AVAILABLE" in why or "NO_CIPHERS_AVAILABLE" in why or "UNSUPPORTED_PROTOCOL" in why:
            report("SKIP", "TLS 1.1 is refused", f"this client cannot offer TLS 1.1 at all, so nothing was tested: {why}")
        else:
            report("PASS", "TLS 1.1 is refused", why)
    except (ValueError, ssl.SSLError) as e:
        report("SKIP", "TLS 1.1 is refused", f"this client cannot offer TLS 1.1 at all, so nothing was tested: {e}")

    print("\nACL and limits (QoS 0, MQTT 3.1.1):")
    ok1, cons, _ = attempt(context("consumer"), "ff38-cons-sub")
    ok2, edge_sub, _ = attempt(context("edge"), "ff38-edge-sub")
    ok3, edge_pub, _ = attempt(context("edge"), "ff38-edge-pub")
    ok4, cons_pub, _ = attempt(context("consumer"), "ff38-cons-pub")
    if not (ok1 and ok2 and ok3 and ok4):
        report("FAIL", "four sessions for the ACL checks", "one of them could not connect")
        return
    rc_c = cons.subscribe(ROOT_TOPIC + "#")
    rc_e = edge_sub.subscribe(ROOT_TOPIC + "#")
    report("PASS" if rc_c in (0, 1, 2) else "FAIL", "the consumer's subscription to vigilimen/v1/# is granted", f"SUBACK {rc_c:#04x}")
    report("PASS" if rc_e == 0x80 else "INFO", "the edge's subscription is refused in the SUBACK (0x80)", f"SUBACK {rc_e:#04x}; the delivery check below is the one that decides")

    edge_pub.publish(T_OK, b'{"schema":"1","probe":"ff38"}')
    got_c = [t for t, _ in cons.messages(3)]
    got_e = [t for t, _ in edge_sub.messages(0.5)]
    report("PASS" if T_OK in got_c else "FAIL", "POSITIVE CONTROL: what the edge publishes reaches the consumer", f"consumer received {got_c}")
    report("PASS" if not got_e else "FAIL", "the edge receives NOTHING, although it subscribed and the same message was delivered to the consumer", f"edge received {got_e}")

    cons_pub.publish(ROOT_TOPIC + "lab/CONV-001/forged", b"forged")
    got = [t for t, _ in cons.messages(3)]
    report("PASS" if not got else "FAIL", "the consumer cannot publish (nobody receives what it sends, its own subscription included)", f"received {got}")

    edge_pub.publish(ROOT_TOPIC + "lab/CONV-001/retained", b"keep me", retain=True)
    cons.messages(1.5)
    ok, late, _ = attempt(context("consumer"), "ff38-cons-late")
    if ok:
        late.subscribe(ROOT_TOPIC + "#")
        got = [t for t, _ in late.messages(2)]
        report("PASS" if not got else "FAIL", "retained telemetry is switched off (a consumer that arrives late gets nothing)", f"late consumer received {got}")
        late.close()

    try:
        edge_pub.publish(ROOT_TOPIC + "lab/CONV-001/big", b"x" * 6000)
        edge_pub.messages(2)
        still_open = True
    except (ConnectionError, OSError, ssl.SSLError):
        still_open = False
    got = [t for t, _ in cons.messages(1)]
    report("PASS" if (not still_open and not any(t.endswith("/big") for t in got)) else "FAIL",
           "a 6000-byte message (limit 4096) is not delivered and the broker closes the sender's connection",
           f"sender connection still open: {still_open}; delivered: {[t for t in got if t.endswith('/big')]}")

    for x in (cons, edge_sub, edge_pub, cons_pub):
        x.close()


def phase_revocation(identity: str, expect: str) -> None:
    print(f"FF-38 - DMZ broker, live (revocation: {identity}, expect {expect})\n")
    ok, ctrl, v = attempt(context("edge"), "ff38-rev-control")
    report("PASS" if ok else "FAIL", "POSITIVE CONTROL: a valid client (edge) connects in the same run", v)
    if ok:
        ctrl.close()
    ok, m, why = attempt(context(identity), "ff38-rev-" + identity)
    if ok:
        m.close()
    if expect == "accepted":
        report("PASS" if ok else "FAIL", f"{identity} (valid certificate, not revoked) connects", "accepted" if ok else why)
    elif expect == "refused":
        report("PASS" if not ok else "FAIL", f"{identity} (revoked, broker restarted) is refused", why if not ok else "it was accepted")
    else:
        print(f"  FINDING  {identity} after the CRL changed, WITHOUT restarting the broker: " + ("STILL ACCEPTED (the CRL is not re-read until a restart)" if ok else f"REFUSED (the CRL is re-read: {why})"), flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["main", "revocation"], required=True)
    ap.add_argument("--identity", default="edge-old")
    ap.add_argument("--expect", choices=["accepted", "refused", "report"], default="report")
    a = ap.parse_args()
    if a.phase == "main":
        phase_main()
    else:
        phase_revocation(a.identity, a.expect)
    print(f"\n{fails} failed.")
    print("FF-38 " + ("FAIL" if fails else "pass") + f" ({a.phase}).")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
