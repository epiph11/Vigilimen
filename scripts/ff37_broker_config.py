"""FF-37 - the DMZ broker configuration says what ADR-020 says (static part).

Reads plant/broker/mosquitto.conf and plant/broker/acl and checks them, then proves the checks can fail with
deliberate mutations, each of which must be caught by the check meant to catch it. No Docker, no broker.

    python scripts\\ff37_broker_config.py              baseline + mutation self-test
    python scripts\\ff37_broker_config.py --static     baseline only

Not covered here (needs the broker running, later): that Mosquitto really refuses the edge's subscription,
refuses a revoked certificate, refuses TLS 1.1, and what it does with the CRL without a restart.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plant" / "pki"))
import mqttpki as M                                                    # noqa: E402

CONF = ROOT / "plant" / "broker" / "mosquitto.conf"
ACL = ROOT / "plant" / "broker" / "acl"
TOPIC_ROOT = "vigilimen/v1/"
BROKER_FILES = {"ca.pem", "server.pem", "server.key", "crl.pem"}         # what mqttpki.py writes into broker/


def parse_conf(text: str) -> list[tuple[str, str]]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            k, _, v = line.partition(" ")
            out.append((k, v.strip()))
    return out


def parse_acl(text: str):
    """-> (top_level_lines, {user: [(access, topic)]}, pattern_lines)"""
    top, users, patterns, cur = [], {}, [], None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.partition(" ")
        if k == "user":
            cur = v.strip()
            users.setdefault(cur, [])
        elif k in ("pattern",):
            patterns.append(line)
        elif k == "topic":
            parts = v.split(None, 1)
            if len(parts) == 2 and parts[0] in ("read", "write", "readwrite", "deny"):
                access, topic = parts
            else:
                access, topic = "readwrite", v            # Mosquitto: no keyword means read and write
            (users[cur] if cur else top).append((access, topic.strip()))
        else:
            top.append((k, v))
    return top, users, patterns


def checks(conf_text: str, acl_text: str) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []

    def add(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    c = parse_conf(conf_text)
    vals = lambda k: [v for kk, v in c if kk == k]                       # noqa: E731
    one = lambda k: (vals(k) or [None])[-1]                              # noqa: E731

    listeners = vals("listener")
    add("exactly one listener, on 8883", [x.split()[0] for x in listeners] == ["8883"], f"listeners: {listeners}")
    add("no plain-text port (1883) anywhere in the file", "1883" not in re.findall(r"\b1883\b", " ".join(f"{k} {v}" for k, v in c if k in ('listener', 'port', 'bind_address'))) and "port" not in [k for k, _ in c], "")
    add("protocol is mqtt (no websockets)", vals("protocol") == ["mqtt"], f"protocol: {vals('protocol')}")
    add("per-listener settings are on (the listener's own ACL and anonymous rules apply)", one("per_listener_settings") == "true", f"value: {one('per_listener_settings')}")
    add("anonymous access is refused", one("allow_anonymous") == "false", f"allow_anonymous: {one('allow_anonymous')}")
    add("a client certificate is required (mutual TLS)", one("require_certificate") == "true", f"require_certificate: {one('require_certificate')}")
    add("the identity is the certificate CN", one("use_identity_as_username") == "true", f"use_identity_as_username: {one('use_identity_as_username')}")
    add("no password file and no pre-shared key", not (vals("password_file") or vals("psk_file") or vals("psk_hint")), "")
    tv = vals("tls_version")
    add("TLS version: none set (1.2 and 1.3), or 1.2 or 1.3 explicitly; never 1.1 or lower", all(v in ("tlsv1.2", "tlsv1.3") for v in tv), f"tls_version: {tv}")
    certs = {"cafile": "ca.pem", "certfile": "server.pem", "keyfile": "server.key", "crlfile": "crl.pem"}
    for k, fname in certs.items():
        add(f"{k} is set to the file mqttpki.py writes ({fname})", one(k) is not None and one(k).endswith("/" + fname) and fname in BROKER_FILES, f"{k}: {one(k)}")
    add("the ACL file is set", bool(one("acl_file")), f"acl_file: {one('acl_file')}")
    add("message size limit is set and at most 65536 bytes", one("message_size_limit") is not None and int(one("message_size_limit")) <= 65536, f"message_size_limit: {one('message_size_limit')}")
    add("connections are capped (at most 20)", one("max_connections") is not None and 0 < int(one("max_connections")) <= 20, f"max_connections: {one('max_connections')}")
    add("queues and in-flight messages are bounded", one("max_queued_messages") is not None and 0 < int(one("max_queued_messages")) <= 10000 and one("max_inflight_messages") is not None and 0 < int(one("max_inflight_messages")) <= 100,
        f"max_queued: {one('max_queued_messages')}, max_inflight: {one('max_inflight_messages')}")
    add("retained telemetry is switched off", one("retain_available") == "false", f"retain_available: {one('retain_available')}")

    top, users, patterns = parse_acl(acl_text)
    add("ACL: no top-level topic lines and no `pattern` lines (they would apply to everybody)", not top and not patterns, f"top: {top}, pattern: {patterns}")
    add("ACL: exactly the users edge and consumer", set(users) == {"edge", "consumer"}, f"users: {sorted(users)}")
    add("ACL: every user is a client certificate identity mqttpki.py issues", set(users) <= set(M.CLIENTS), f"users: {sorted(users)}; certificates: {M.CLIENTS}")
    add("ACL: the revocation tester identity has no rights", not (set(users) & set(M.TESTER_CLIENTS)), "")
    e = users.get("edge", [])
    add("ACL: the edge can only WRITE (it has no subscription at all)", bool(e) and all(a == "write" for a, _ in e), f"edge: {e}")
    k = users.get("consumer", [])
    add("ACL: the consumer can only READ (it cannot publish)", bool(k) and all(a == "read" for a, _ in k), f"consumer: {k}")
    alltopics = [t for v in users.values() for _, t in v]
    add(f"ACL: every topic is under {TOPIC_ROOT} (no bare '#', no $SYS)", all(t.startswith(TOPIC_ROOT) for t in alltopics), f"topics: {alltopics}")
    return out


# ---------------------------------------------------------------------------
# Mutations: (name, edit to conf or acl, the check that must fail)
# ---------------------------------------------------------------------------
def c_sub(old, new):
    return lambda conf, acl: (conf.replace(old, new), acl)


def a_sub(old, new):
    return lambda conf, acl: (conf, acl.replace(old, new))


MUTATIONS = [
    ("a plain-text listener on 1883 is added", lambda conf, acl: (conf + "\nlistener 1883\n", acl), "exactly one listener, on 8883"),
    ("a websockets listener is added", lambda conf, acl: (conf + "\nlistener 9001\nprotocol websockets\n", acl), "exactly one listener, on 8883"),
    ("a `port 1883` line is added", lambda conf, acl: (conf + "\nport 1883\n", acl), "no plain-text port (1883)"),
    ("anonymous access allowed", c_sub("allow_anonymous false", "allow_anonymous true"), "anonymous access is refused"),
    ("client certificate no longer required", c_sub("require_certificate true", "require_certificate false"), "a client certificate is required"),
    ("identity no longer taken from the certificate", c_sub("use_identity_as_username true", "use_identity_as_username false"), "the identity is the certificate CN"),
    ("a password file is added", lambda conf, acl: (conf + "\npassword_file /mosquitto/config/passwd\n", acl), "no password file"),
    ("TLS 1.1 allowed", lambda conf, acl: (conf + "\ntls_version tlsv1.1\n", acl), "TLS version"),
    ("the CRL line is removed", c_sub("crlfile /mosquitto/certs/crl.pem\n", ""), "crlfile is set to the file"),
    ("the CA file points at a file mqttpki.py does not write", c_sub("/mosquitto/certs/ca.pem", "/mosquitto/certs/rootca.pem"), "cafile is set to the file"),
    ("the ACL file line is removed", c_sub("acl_file /mosquitto/config/acl\n", ""), "the ACL file is set"),
    ("per-listener settings turned off", c_sub("per_listener_settings true", "per_listener_settings false"), "per-listener settings are on"),
    ("message size limit removed", c_sub("message_size_limit 4096\n", ""), "message size limit is set"),
    ("message size limit 10 MB", c_sub("message_size_limit 4096", "message_size_limit 10485760"), "message size limit is set"),
    ("connections uncapped (0)", c_sub("max_connections 10", "max_connections 0"), "connections are capped"),
    ("queue limit removed", c_sub("max_queued_messages 1000\n", ""), "queues and in-flight messages are bounded"),
    ("retained messages allowed", c_sub("retain_available false", "retain_available true"), "retained telemetry is switched off"),
    ("the edge may also read", a_sub("topic write vigilimen/v1/#", "topic readwrite vigilimen/v1/#"), "the edge can only WRITE"),
    ("the edge gets a read line as well", a_sub("topic write vigilimen/v1/#\n", "topic write vigilimen/v1/#\ntopic read vigilimen/v1/#\n"), "the edge can only WRITE"),
    ("the consumer may also write", a_sub("topic read vigilimen/v1/#", "topic readwrite vigilimen/v1/#"), "the consumer can only READ"),
    ("a `pattern` line for everybody", lambda conf, acl: (conf, acl + "\npattern readwrite vigilimen/v1/%u/#\n"), "no top-level topic lines"),
    ("a top-level topic line (anonymous rights)", lambda conf, acl: (conf, "topic read vigilimen/v1/#\n" + acl), "no top-level topic lines"),
    ("a third user, the revocation tester, given rights", lambda conf, acl: (conf, acl + "\nuser edge-old\ntopic write vigilimen/v1/#\n"), "the revocation tester identity has no rights"),
    ("a user with no certificate behind it", lambda conf, acl: (conf, acl + "\nuser admin\ntopic read vigilimen/v1/#\n"), "every user is a client certificate identity"),
    ("the consumer reads everything ('#')", a_sub("topic read vigilimen/v1/#", "topic read #"), "every topic is under"),
    ("the consumer reads $SYS", a_sub("topic read vigilimen/v1/#", "topic read $SYS/#"), "every topic is under"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", action="store_true")
    a = ap.parse_args()
    conf, acl = CONF.read_text(), ACL.read_text()
    failed = 0
    print("FF-37 - DMZ broker configuration")
    print("\nBaseline (plant/broker/mosquitto.conf and acl):")
    for name, ok, detail in checks(conf, acl):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail and not ok else ""))
        failed += 0 if ok else 1
    if not a.static and failed == 0:
        print("\nMutation self-test (each damage must be caught by the named check):")
        caught = 0
        for what, fn, check_name in MUTATIONS:
            c2, a2 = fn(conf, acl)
            if (c2, a2) == (conf, acl):
                failed += 1
                print(f"  BROKEN  {what}: the mutation changed nothing (its anchor text is not in the file)")
                continue
            bad = [n for n, ok, _ in checks(c2, a2) if not ok]
            hit = any(check_name in n for n in bad)
            print(f"  {'CAUGHT' if hit else 'MISSED'}  {what}   [{check_name!r}]")
            if hit:
                caught += 1
            else:
                failed += 1
                print(f"           failing checks were: {bad}")
        print(f"\n{caught} mutations caught of {len(MUTATIONS)}")
    print(f"\nFF-37 {'FAIL' if failed else 'pass'} ({failed} problem(s)).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
