#!/usr/bin/env python3
"""
FF-33 - opcua-sup exposes nothing writable, whoever asks (ADR-023, point 3; OPC-03).

ADR-017 found that on the gateway every logged-in account can write StartCommand, StopCommand
and the Fault* tags, because write permission is a property of the NODE and both accounts
hold the same role. ADR-023's answer is not a better role: it is a server that has no such
node. This check proves the property from both sides.

  STATIC  reads plant/opcua-sup/opcua_sup.py: no set_writable, no command or fault names,
          the mirrored set is exactly the ten expected measurements and status tags.
          Self-tested with mutations of the source text.
  LIVE    (when a URL is given) opens a session as every account and as nobody:
            - anonymous is refused;
            - the address space contains exactly the expected names;
            - a write to EVERY node is refused for EVERY account;
            - a READ with every account succeeds (a check that only proves refusals can pass
              against a server that is simply broken; the OPC UA contrast demo learned this).

    python3 scripts/ff33_opcua_sup_readonly.py
    python3 scripts/ff33_opcua_sup_readonly.py --url opc.tcp://127.0.0.1:14841/vigilimen/conv001/

In Docker (the server is on an internal network, so run it from inside the stack):
    docker cp scripts\\ff33_opcua_sup_readonly.py vigilimen-collector:/tmp/ff33.py
    docker exec vigilimen-collector python3 /tmp/ff33.py --url opc.tcp://opcua-sup:4840/vigilimen/conv001/
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "plant" / "opcua-sup" / "opcua_sup.py"
EXPECTED = ["Running", "SafetyTripped", "BeltSpeed_mps", "Load_tph", "BearingTemp_C", "Vibration_mms",
            "MotorCurrent_A", "PlcLinkOK", "PlcState", "PlcAlarmWord"]
ACCOUNTS = {"historian": "h1st0r1an-demo", "scada": "sc4da-demo"}
PASS, FAIL = "PASS", "FAIL"
URI = "urn:vigilimen:plant:conv001"
PATH = ("Enterprise", "PilbaraSite", "ProcessingArea", "ConveyingCell", "CONV001")


def code_of(text: str) -> str:
    """The program without its comments and docstrings, so prose cannot cause or hide a finding."""
    text = re.sub(r'""".*?"""', "", text, flags=re.S)
    return "\n".join(re.sub(r"#.*", "", ln) for ln in text.splitlines())


def static(text: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []

    def check(n: str, ok: bool, why: str) -> None:
        out.append((PASS if ok else FAIL, n, why))

    code = code_of(text)
    check("no node is made writable", "set_writable" not in code and "AccessLevel" not in code and "UserAccessLevel" not in code,
          "a writable node is a command path; read-only must be the default, not a flag")
    check("no command or fault name appears in the program",
          not re.search(r"StartCommand|StopCommand|Fault[A-Z]", code),
          "if the name is in the program, someone intends to serve it")
    m = re.search(r"MIRRORED[^=]*=\s*\[(.*?)\n\]", code, flags=re.S)
    names = re.findall(r'\("(\w+)"', m.group(1)) if m else []
    check("the mirrored set is exactly the ten expected nodes, in order", names == EXPECTED,
          f"found {names}. Order matters: the SCADA binds ns=2;i=6..12 to the first seven")
    check("the server does not call the gateway's write API (no write to the upstream)",
          not re.search(r"upstream.*write_value|src\[[^\]]*\]\.write", code),
          "the mirror reads; a write to the gateway would make opcua-sup a command path")
    return out


def static_mutations(text: str):
    def m(label, a, b, must):
        assert a in text, a
        return label, text.replace(a, b, 1), must
    return [
        m("a node made writable", "nodes[name] = await node.add_variable(idx, name, initial)",
          "nodes[name] = await node.add_variable(idx, name, initial); await nodes[name].set_writable()",
          "no node is made writable"),
        m("StartCommand added", '("PlcAlarmWord", 0),\n]', '("PlcAlarmWord", 0), ("StartCommand", False),\n]',
          "no command or fault name appears in the program"),
        m("a fault tag added", '("PlcAlarmWord", 0),\n]', '("PlcAlarmWord", 0), ("FaultBeltSlip", 0.0),\n]',
          "no command or fault name appears in the program"),
        m("a measurement dropped", '("Load_tph", 0.0),', '', "the mirrored set is exactly the ten expected nodes, in order"),
        m("a write to the upstream", "await nodes[name].write_value(dv)",
          "await nodes[name].write_value(dv); await src[name].write_value(dv)",
          "the server does not call the gateway's write API (no write to the upstream)"),
    ]


async def live(url: str) -> list[tuple[str, str, str]]:
    from asyncua import Client
    out: list[tuple[str, str, str]] = []

    def check(n: str, ok: bool, why: str) -> None:
        out.append((PASS if ok else FAIL, n, why))

    anon = Client(url, timeout=4)
    try:
        await anon.connect(); await anon.disconnect(); refused = False
    except Exception:                                        # noqa: BLE001
        refused = True
    check("anonymous sessions are refused", refused, "an endpoint that accepts anonymous is open to every container on the network")

    for user, pw in ACCOUNTS.items():
        c = Client(url, timeout=4)
        c.set_user(user); c.set_password(pw)
        try:
            await c.connect()
        except Exception as e:                               # noqa: BLE001
            check(f"[{user}] can open a session", False, f"{type(e).__name__}: {e}")
            continue
        try:
            ns = await c.get_namespace_index(URI)
            node = c.nodes.objects
            for p in PATH:
                node = await node.get_child(f"{ns}:{p}")
            kids = await node.get_children()
            names = [(await k.read_browse_name()).Name for k in kids]
            check(f"[{user}] sees exactly the ten expected nodes", names == EXPECTED, f"saw {names}")
            readable = True
            for k in kids:
                try:
                    await k.read_data_value(raise_on_bad_status=False)
                except Exception:                            # noqa: BLE001
                    readable = False
            check(f"[{user}] can READ every node (the permitted action works)", readable,
                  "a server that refuses everything looks secure and is broken")
            accepted = []
            for k, n in zip(kids, names):
                try:
                    dv = await k.read_data_value(raise_on_bad_status=False)
                    await k.write_value(dv.Value)
                    accepted.append(n)
                except Exception:                            # noqa: BLE001
                    pass
            check(f"[{user}] is refused a write to EVERY node", not accepted,
                  f"writes ACCEPTED on {accepted}. opcua-sup must have no writable node")
        finally:
            await c.disconnect()
    return out


def report(title: str, rows) -> int:
    print(title)
    width = max(len(n) for _, n, _ in rows)
    for s, n, why in rows:
        print(f"  {s}  {n.ljust(width)}")
        if s == FAIL:
            print(f"        why this case exists: {why}")
    return sum(1 for r in rows if r[0] == FAIL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="run the LIVE part against this opcua-sup endpoint")
    a = ap.parse_args()
    text = SRC.read_text(encoding="utf-8")

    failed = report("FF-33 - opcua-sup is read-only\n\n  STATIC (plant/opcua-sup/opcua_sup.py)", static(text))
    print("\n  self-test - each mutation of the source must be caught:")
    unseen = 0
    for label, mutated, must in static_mutations(text):
        caught = any(s == FAIL and n == must for s, n, _ in static(mutated))
        print(f"  {PASS if caught else FAIL}  caught: {label}")
        unseen += 0 if caught else 1

    live_failed = 0
    if a.url:
        print(f"\n  LIVE ({a.url})")
        live_failed = report("", asyncio.run(live(a.url)))
    else:
        print("\n  LIVE skipped (no --url). Static only: this does not prove the running server.")

    if failed or unseen or live_failed:
        print("\nFF-33 FAIL")
        return 1
    print("\nFF-33 pass" + ("" if a.url else " (STATIC only)") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
