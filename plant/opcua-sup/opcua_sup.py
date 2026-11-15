#!/usr/bin/env python3
"""
opcua-sup - the read-only supervisory OPC UA server (ADR-023, point 3; physical OT-OPC-01).

    python3 plant/opcua-sup/opcua_sup.py --port 14841 --upstream opc.tcp://127.0.0.1:14840/vigilimen/conv001/

WHAT IT IS
  A mirror of the gateway's MEASUREMENTS, served from Zone 2. Everything that only
  reads (the collector, the SCADA read view, and later the edge) reads this server
  instead of the gateway. It is an OPC UA client of the gateway (flow F8, through
  fw-cell) and an OPC UA server for its readers (flows F1, F3).

WHAT IT DELIBERATELY IS NOT
  It has NO command node and NO fault node: no StartCommand, no StopCommand, no
  Fault*. Read-only is therefore a property of the ADDRESS SPACE, not of a role.
  There is nothing to authorise, so there is no role model here to get wrong
  (ADR-017 describes the two attempts that went wrong in the gateway).

TWO RULES THAT MATTER FOR A HISTORIAN
  1. The SOURCE timestamp and the StatusCode are copied from the gateway, never
     re-stamped. The collector stores the plant's time, not the mirror's.
  2. If the gateway cannot be reached, every node's status becomes Bad (BadNoCommunication)
     with the time of the failure (measured 15 Nov 2026: readers then see value None). A stale
     value must never look fresh. The collector stores quality 0 and keeps the alarm engine
     away from it (collector.py: only Good values feed the engine).

ADDRESS SPACE ORDER
  The seven measurements come first and keep the gateway's NodeIds (ns=2;i=6..12), so
  the SCADA bindings for them do not move. Plc* status follows (i=13..15 here, not
  20..22 as on the gateway). Nothing the SCADA binds sits after them.

NOT YET DONE (ADR-023 point 7): the secure channel (Sign and Encrypt, application
certificates, per-identity roles). This server uses the lab's NoSecurity policy with
named accounts, like the gateway. Recorded as a lab concession, not as the design.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from datetime import datetime, timezone

from asyncua import Client, Server, ua
from asyncua.server.user_managers import UserManager
from asyncua.server.users import User, UserRole

URI = "urn:vigilimen:plant:conv001"
PATH = ("Enterprise", "PilbaraSite", "ProcessingArea", "ConveyingCell", "CONV001")

# Creation order matters (see the header). Initial values are what a reader sees
# before the first upstream read; the status is Bad until then.
MIRRORED: list[tuple[str, object]] = [
    ("Running", False), ("SafetyTripped", True), ("BeltSpeed_mps", 0.0), ("Load_tph", 0.0),
    ("BearingTemp_C", 28.0), ("Vibration_mms", 0.0), ("MotorCurrent_A", 0.0),
    ("PlcLinkOK", False), ("PlcState", 0), ("PlcAlarmWord", 0),
]


class SupUserManager(UserManager):
    """Named accounts only. Anonymous is refused. Attribution, not authorisation:
    no account can write because no node is writable."""

    ACCOUNTS = {
        "historian": ("h1st0r1an-demo", UserRole.User),
        "scada":     ("sc4da-demo", UserRole.User),
    }

    def get_user(self, iserver, username=None, password=None, certificate=None):
        if username is None:
            return None
        entry = self.ACCOUNTS.get(username)
        if entry is None or password != entry[0]:
            return None
        return User(role=entry[1], name=username)


async def build(server: Server) -> dict:
    idx = await server.register_namespace(URI)
    node = server.nodes.objects
    for name in PATH:
        node = await node.add_object(idx, name)
    nodes = {}
    for name, initial in MIRRORED:
        # add_variable and NOTHING ELSE: no set_writable(). Default access is read-only.
        nodes[name] = await node.add_variable(idx, name, initial)
    return nodes


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def mark_bad(nodes: dict) -> None:
    """Say the value is not current (readers see a Bad status, and a None value)."""
    bad = ua.StatusCode(ua.StatusCodes.BadNoCommunication)
    for n in nodes.values():
        cur = await n.read_data_value(raise_on_bad_status=False)    # it may already be Bad
        await n.write_value(ua.DataValue(cur.Value, bad, SourceTimestamp=_now()))


async def mirror(nodes: dict, url: str, user: str, password: str, period_s: float) -> None:
    """Read the gateway's measurements and republish them, DataValue and all."""
    await mark_bad(nodes)                               # Bad until the first good read
    while True:
        try:
            client = Client(url, timeout=4)
            client.set_user(user)                       # before connect(), as in collector.py
            client.set_password(password)
            await client.connect()
            try:
                ns = await client.get_namespace_index(URI)
                root = client.nodes.objects
                for name in PATH:
                    root = await root.get_child(f"{ns}:{name}")
                src = {name: await root.get_child(f"{ns}:{name}") for name, _ in MIRRORED}
                print(f"opcua-sup: mirroring {len(src)} nodes from {url}", flush=True)
                while True:
                    dvs = await asyncio.gather(*(n.read_data_value(raise_on_bad_status=False) for n in src.values()))
                    for name, dv in zip(src, dvs):
                        await nodes[name].write_value(dv)
                    await asyncio.sleep(period_s)
            finally:
                try:
                    await client.disconnect()
                except Exception:                       # noqa: BLE001
                    pass
        except asyncio.CancelledError:
            raise
        except Exception as e:                          # noqa: BLE001
            print(f"opcua-sup: upstream {type(e).__name__}: {e}; values marked Bad, retry in 2 s", flush=True)
            await mark_bad(nodes)
            await asyncio.sleep(2.0)


async def run(port: int, url: str, user: str, password: str, period_s: float) -> None:
    logging.getLogger("asyncua").setLevel(logging.ERROR)
    server = Server(user_manager=SupUserManager())
    await server.init()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{port}/vigilimen/conv001/")
    server.set_server_name("VIGILIMEN CONV-001 (supervisory, read-only)")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    server.set_security_IDs(["Username"])
    nodes = await build(server)
    async with server:
        print(f"opcua-sup on opc.tcp://0.0.0.0:{port}/vigilimen/conv001/ - read-only, no command or fault node", flush=True)
        await mirror(nodes, url, user, password, period_s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=4840)
    ap.add_argument("--upstream", default=os.environ.get("VIGILIMEN_UPSTREAM_URL", "opc.tcp://fw-cell:4840/vigilimen/conv001/"))
    ap.add_argument("--user", default=os.environ.get("VIGILIMEN_UPSTREAM_USER", "opcua-sup"))
    ap.add_argument("--period", type=float, default=float(os.environ.get("VIGILIMEN_MIRROR_PERIOD_S", "0.5")))
    a = ap.parse_args()
    pw = os.environ.get("VIGILIMEN_UPSTREAM_PASSWORD", "sup-m1rr0r-demo")
    try:
        asyncio.run(run(a.port, a.upstream, a.user, pw, a.period))
    except KeyboardInterrupt:
        pass
