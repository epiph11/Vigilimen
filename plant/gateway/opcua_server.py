#!/usr/bin/env python3
"""
CONV-001 — OPC UA server, with an ISA-95 address space.

    python3 plant/gateway/opcua_server.py --port 14840

WHY THIS EXISTS ALONGSIDE THE MODBUS SERVER
-------------------------------------------
The protocol register claims OPC UA is "the outlier that does it properly".
This server and `opcua_contrast.py` turn that claim into something you can
watch happen: the same conveyor, the same values, and a client that gets
refused at the door instead of writing whatever it likes.

Two differences from the Modbus server, and both are structural rather
than configuration:

  1. THERE IS A PLACE TO PUT AN IDENTITY. OPC UA carries user tokens and
     certificates in the session. Modbus has no field at all — see the MBAP
     frame at the top of modbus.py.

  2. WRITE PERMISSION IS A PROPERTY OF THE NODE. A variable can be
     genuinely read-only, and the server enforces it. On Modbus "read-only"
     exists only in documentation, and documentation is not a control.

WHAT DOES NOT CHANGE
--------------------
The controller still speaks Modbus. This server sits NORTHBOUND of it, and
that is the ordinary situation on real plant: OPC UA between the gateway
and the historian, unauthenticated fieldbus below. Good northbound security
does not reach down to protect the controller — which is exactly why the
conduit, not the endpoint, carries most of the burden in the 62443
partition.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sim"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from plant_cycle import PlantCycle, FAULT_LIMITS         # noqa: E402
from plc_link import PlcLink                              # noqa: E402

from asyncua import Server, ua                            # noqa: E402
from asyncua.server.user_managers import UserManager      # noqa: E402
from asyncua.server.users import User, UserRole  # noqa: E402

URI = "urn:vigilimen:plant:conv001"


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

class PlantUserManager(UserManager):
    """Named accounts only. Anonymous sessions are refused.

    Two roles, because the read/write split is the whole point of having
    identity at all:

        historian  — intended to read.   engineer — intended to write setpoints.

    INTENDED, not enforced: both hold UserRole.User, and write permission is a
    property of the NODE. `historian` CAN write StartCommand, StopCommand and the
    Fault* tags. See ADR-017 and the finding below.

    A single account with full rights would authenticate perfectly and
    protect nothing, which is the shape most OPC UA deployments actually
    ship in.
    """

    # Both User, deliberately. Admin bypasses per-node access levels in
    # asyncua, which would let the engineer write a measurement — see the
    # note below the class.
    ACCOUNTS = {
        "historian": ("h1st0r1an-demo", UserRole.User),
        "engineer":  ("eng1neer-demo", UserRole.User),
    }

    def get_user(self, iserver, username=None, password=None, certificate=None):
        if username is None:
            return None                      # anonymous — refused
        entry = self.ACCOUNTS.get(username)
        if entry is None or password != entry[0]:
            return None                      # unknown or wrong password
        return User(role=entry[1], name=username)


# Demo credentials in source, deliberately and visibly. FF-03 tolerates them
# because they are inside ACCOUNTS on a simulated plant; a real deployment
# federates to the identity authority (ADR-008) and holds no password here
# at all. The point being demonstrated is that an identity EXISTS to check,
# not how it is stored.


# ---------------------------------------------------------------------------
# Authorisation — and an honest finding about it
# ---------------------------------------------------------------------------
#
# FIRST ATTEMPT, AND WHY IT WAS ABANDONED.
#
# The first version mapped 'engineer' to asyncua's Admin role, and the
# contrast demo immediately caught that Admin could write SafetyTripped —
# a MEASUREMENT of the safety controller. The role model was bypassing the
# per-node access level entirely.
#
# The second version added a custom PermissionRuleset to deny writes to
# measurements. It denied every write including the legitimate ones, because
# the write list sits on body.Parameters rather than on body — a rule that
# refuses everything looks secure and is simply broken, and it was caught
# only because the demo asserts that a PERMITTED write succeeds.
#
# WHAT IS SHIPPED INSTEAD, AND THE LESSON IN IT.
#
# Both accounts hold UserRole.User, and the read/write split is enforced
# per node by set_writable(). That is the mechanism that actually works
# here, and it means:
#
#     the two accounts differ in ATTRIBUTION, not in authorisation.
#
# Which is worth stating rather than hiding. A role model that silently
# bypasses node permissions gives you less than the diagram suggests, and
# discovering that took two broken attempts and a demo that checks both
# directions. Real authorisation in this programme comes from the identity
# authority (ADR-008), not from a role enum inside one server.


# ---------------------------------------------------------------------------
# Address space — ISA-95
# ---------------------------------------------------------------------------

async def build(server: Server) -> dict:
    """Enterprise → Site → Area → Work cell → Equipment → tags.

    The hierarchy is not decoration. It is what lets a tag be addressed by
    what it IS rather than by where it happens to be wired, and it is the
    model S13's asset structure will mirror. A flat tag list is how you get
    `CONV001_TEMP_2` and nobody remembering which bearing that was.
    """
    idx = await server.register_namespace(URI)
    objects = server.nodes.objects

    ent = await objects.add_object(idx, "Enterprise")
    site = await ent.add_object(idx, "PilbaraSite")
    area = await site.add_object(idx, "ProcessingArea")
    cell = await area.add_object(idx, "ConveyingCell")
    eq = await cell.add_object(idx, "CONV001")

    async def ro(name: str, val):
        """Read-only measurement. The server enforces this."""
        v = await eq.add_variable(idx, name, val)
        return v

    async def rw(name: str, val):
        """Writable setpoint. Requires an authenticated session."""
        v = await eq.add_variable(idx, name, val)
        await v.set_writable()
        return v

    return {
        "Running":        await ro("Running", False),
        "SafetyTripped":  await ro("SafetyTripped", True),
        "BeltSpeed_mps":  await ro("BeltSpeed_mps", 0.0),
        "Load_tph":       await ro("Load_tph", 0.0),
        "BearingTemp_C":  await ro("BearingTemp_C", 28.0),
        "Vibration_mms":  await ro("Vibration_mms", 0.0),
        "MotorCurrent_A": await ro("MotorCurrent_A", 0.0),
        "StartCommand":   await rw("StartCommand", False),
        "StopCommand":    await rw("StopCommand", False),
        # ---- FAULT INJECTION (S4 acceptance 4e, S8, S13) -------------------
        # APPENDED AFTER the nine tags above on purpose: asyncua numbers nodes
        # in creation order, and FUXA addresses them as ns=2;i=N. Inserting
        # earlier would silently re-point every SCADA binding (these are i=15..19).
        # These are simulation inputs, not plant tags: a real server would not
        # have them, and ADR-003 says why this one does. NOTE the finding: any
        # authenticated session can write them (roles differ in attribution,
        # not authorisation - see above), including `historian`.
        "FaultBearingWear":    await rw("FaultBearingWear", 0.0),
        "FaultBeltSlip":       await rw("FaultBeltSlip", 0.0),
        "FaultMisalignment":   await rw("FaultMisalignment", 0.0),
        "FaultIdlerSeizure":   await rw("FaultIdlerSeizure", 0.0),
        "FaultVibrationSpike": await rw("FaultVibrationSpike", 0.0),
        # ---- PLC LINK STATUS (ADR-013) — appended again: i=20..22 --------------
        # Read-only. In embedded mode (no PLC link) they read False / 0 / 0.
        "PlcLinkOK":      await ro("PlcLinkOK", False),
        "PlcState":       await ro("PlcState", 0),
        "PlcAlarmWord":   await ro("PlcAlarmWord", 0),
    }


# ---------------------------------------------------------------------------

async def run(port: int) -> None:
    logging.getLogger("asyncua").setLevel(logging.ERROR)

    server = Server(user_manager=PlantUserManager())
    await server.init()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{port}/vigilimen/conv001/")
    server.set_server_name("VIGILIMEN CONV-001")

    # Username/password only. Anonymous is NOT in this list, and its absence
    # is the control — an endpoint that also offers Anonymous alongside
    # a signed policy is an endpoint a client will happily connect to
    # anonymously, because clients pick the easiest policy on offer.
    # The ruleset is attached HERE, alongside the policy, because
    # authentication and authorisation are configured together or they drift
    # apart — which is how a correctly-authenticated engineer ends up able to
    # write a measurement.
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    server.set_security_IDs(["Username"])

    tags = await build(server)

    # PLC link: OFF by default. "modbus" makes PLC-CONV-001 the control function
    # (ADR-013). The default stays "off" until the link is validated in Docker,
    # so acceptance test 4e keeps meaning what it meant when it was written.
    mode = os.environ.get("VIGILIMEN_PLC_LINK", "off").strip().lower()
    if mode not in ("off", "modbus"):
        raise SystemExit(f"VIGILIMEN_PLC_LINK must be 'off' or 'modbus', got {mode!r}")
    link = None
    if mode == "modbus":
        link = PlcLink(os.environ.get("VIGILIMEN_MODBUS_HOST", "plc-control"),
                       int(os.environ.get("VIGILIMEN_MODBUS_PORT", "502")))
    cycle = PlantCycle(link, dt_s=0.5)

    async with server:
        print(f"CONV-001 OPC UA server on opc.tcp://0.0.0.0:{port}/vigilimen/conv001/")
        print("Anonymous sessions are refused. Accounts: historian (read), engineer (read/write)")
        print(f"Control function: {'PLC-CONV-001 over Modbus (' + link.host + ':' + str(link.port) + ')' if link else 'embedded Python model (no PLC link)'}\n")

        while True:
            start = await tags["StartCommand"].get_value()
            stop = await tags["StopCommand"].get_value()
            # Fault injection: raw values here, clamped inside PlantCycle.
            faults = {name: await tags[name].get_value() for name in FAULT_LIMITS}

            # The scan does blocking socket I/O in PLC mode, so it runs in a
            # worker thread: a slow or absent PLC must not freeze OPC UA.
            snap = await asyncio.to_thread(cycle.step, start, stop, faults)

            for name, value in snap.items():
                await tags[name].write_value(value)

            await asyncio.sleep(0.5)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=14840)
    a = ap.parse_args()
    try:
        asyncio.run(run(a.port))
    except KeyboardInterrupt:
        pass
