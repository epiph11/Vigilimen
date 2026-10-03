#!/usr/bin/env python3
"""
The same four moves as attack_demo.py, against OPC UA instead of Modbus.

    # terminal 1
    python3 plant/gateway/opcua_server.py --port 14840
    # terminal 2
    python3 plant/gateway/opcua_contrast.py --port 14840

On Modbus, three of four succeeded. Here the first one does not get past
the door, and the difference is structural rather than configuration:
there is a place in the session to put an identity, so there is something
to check.

Read this next to `attack_demo.py`. The pair is the argument.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from asyncua import Client, ua

OK, BAD = "✓", "✗"
URI = "urn:limen:plant:conv001"


def banner(n: int, title: str) -> None:
    print(f"\n{'=' * 74}\n  {n}. {title}\n{'=' * 74}")


async def node(c: Client, name: str):
    idx = await c.get_namespace_index(URI)
    return await c.nodes.root.get_child(
        ["0:Objects", f"{idx}:Enterprise", f"{idx}:PilbaraSite",
         f"{idx}:ProcessingArea", f"{idx}:ConveyingCell", f"{idx}:CONV001", f"{idx}:{name}"]
    )


async def main(host: str, port: int) -> int:
    logging.getLogger("asyncua").setLevel(logging.CRITICAL)
    url = f"opc.tcp://{host}:{port}/limen/conv001/"
    failures = 0

    # ---------------------------------------------------------------------
    banner(1, "Connect with no credential, as the Modbus demo did")

    # A refusal and an absent server look identical from the client unless
    # you check. The first version of this script reported PASS because the
    # server had crashed on an import — a test that succeeds when the system
    # under test is missing is worse than no test.
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(host, port), 3)
        w.close()
    except Exception:
        print(f"     {BAD} nothing is listening on {host}:{port} — start the server first.")
        print("       (A refusal and an absent server look the same from here. They")
        print("        are not the same, so this is checked before anything else.)")
        return 2
    print(f"     · the server is listening on {host}:{port}")

    try:
        async with Client(url=url) as c:
            await (await node(c, "Running")).get_value()
        print(f"     {BAD} the anonymous session was ACCEPTED — that is a finding, not a pass")
        failures += 1
    except Exception as e:
        print(f"     {OK} refused by the server: {type(e).__name__}")
        print("       The session carries a user token field. Leaving it empty is")
        print("       a thing the server can notice, because there is a field to")
        print("       be empty. On Modbus there is no field to leave empty.")

    # ---------------------------------------------------------------------
    banner(2, "Connect as the historian — a real account, read-only")
    c = Client(url=url)
    c.set_user("historian")
    c.set_password("h1st0r1an-demo")
    # set_user BEFORE connect. Inside `async with`, __aenter__ has already
    # connected anonymously and the credential arrives too late — which the
    # server correctly rejects.
    await c.connect()
    if True:
        try:
            running = await (await node(c, "Running")).get_value()
            temp = await (await node(c, "BearingTemp_C")).get_value()
            print(f"     {OK} connected. Running={running}  BearingTemp={temp:.1f} C")

            try:
                await (await node(c, "BearingTemp_C")).write_value(99.0)
                print(f"     {BAD} the historian WROTE a measurement — that should not be possible")
                failures += 1
            except ua.UaStatusCodeError as e:
                print(f"     {OK} writing a measurement refused: {type(e).__name__}")
                print("       BearingTemp_C is read-only as a PROPERTY OF THE NODE, and the")
                print("       server enforces it. Scenario 2 of the Modbus demo — spoof the")
                print("       bearing to 99 C and defeat machine protection — cannot start here.")
        finally:
            await c.disconnect()

    # ---------------------------------------------------------------------
    banner(3, "Connect as the engineer — writes a setpoint, cannot write a measurement")
    c = Client(url=url)
    c.set_user("engineer")
    c.set_password("eng1neer-demo")
    await c.connect()
    if True:
        try:
            await (await node(c, "StartCommand")).write_value(True)
            await asyncio.sleep(2)
            running = await (await node(c, "Running")).get_value()
            print(f"     {OK} start command written by a NAMED account. Running={running}")
            print("       The command still works — identity is not a wall, it is an")
            print("       attribution. Every write above is traceable to 'engineer',")
            print("       which is the thing scenario 3 of the Modbus demo could erase.")

            try:
                await (await node(c, "SafetyTripped")).write_value(False)
                print(f"     {BAD} the safety status was WRITABLE")
                failures += 1
            except ua.UaStatusCodeError:
                print(f"     {OK} SafetyTripped refused even for the engineer — it is a")
                print("       MEASUREMENT of the safety controller, not a control on it.")
                print("       The safety function has no network input at all (ADR-011);")
                print("       a writable SafetyTripped would let a client make a tripped")
                print("       plant look healthy — the Modbus demo's scenario 3 reappearing")
                print("       on the protocol that was supposed to prevent it.")
        finally:
            await c.disconnect()

    # ---------------------------------------------------------------------
    print(f"""
{'=' * 74}
  WHAT THE PAIR DEMONSTRATES
{'=' * 74}

  Modbus            OPC UA
  ----------------  ------------------------------------------------------
  no identity       user token in the session — anonymous refused
  every address     read-only is a property of the node, enforced
    writable
  no attribution    every write traceable to a named account
  nothing to log    a session to log

  AND YET THE CONTROLLER IS NO SAFER.

  This server sits NORTHBOUND of PLC-CONV-001, which still speaks Modbus
  on port 502 to anyone who can reach it. That is the ordinary shape on
  real plant, and it is the reason a 62443 partition puts most of the
  burden on the CONDUIT rather than on the endpoint: good security at the
  northbound boundary does not reach down to protect the fieldbus.

  What OPC UA changes is what a historian, a SCADA system and an analytics
  plane can be trusted to do. What it does not change is that the adversary
  with network reach to the controller does not need to talk to this server
  at all.
""")

    if failures:
        print(f"  {BAD} {failures} scenario(s) behaved unexpectedly.\n")
        return 1
    print("  All three scenarios behaved as documented.\n")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=14840)
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.host, a.port)))
