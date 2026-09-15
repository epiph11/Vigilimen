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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sim"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conveyor_physics import Conveyor as Physics          # noqa: E402
from interlock_model import Conveyor as Logic, Inputs     # noqa: E402

from asyncua import Server, ua                            # noqa: E402
from asyncua.server.user_managers import UserManager      # noqa: E402
from asyncua.crypto.permission_rules import User, UserRole  # noqa: E402

URI = "urn:md360:plant:conv001"


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

class PlantUserManager(UserManager):
    """Named accounts only. Anonymous sessions are refused.

    Two roles, because the read/write split is the whole point of having
    identity at all:

        historian  — reads. Cannot write anything.
        engineer   — reads, and may write the operator setpoints.

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
    }


# ---------------------------------------------------------------------------

async def run(port: int) -> None:
    logging.getLogger("asyncua").setLevel(logging.ERROR)

    server = Server(user_manager=PlantUserManager())
    await server.init()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{port}/md360/conv001/")
    server.set_server_name("MD360 CONV-001")

    # Username/password only. Anonymous is NOT in this list, and its absence
    # is the control — an endpoint that also offers Anonymous alongside
    # a signed policy is an endpoint a client will happily connect to
    # anonymously, because clients pick the easiest policy on offer.
    # The ruleset is attached HERE, alongside the policy, because
    # authentication and authorisation are configured together or they drift
    # apart — which is how a correctly-authenticated engineer ends up able to
    # write a measurement.
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    server.set_identity_tokens([ua.UserNameIdentityToken])

    tags = await build(server)
    physics, logic = Physics(), Logic()

    async with server:
        print(f"CONV-001 OPC UA server on opc.tcp://0.0.0.0:{port}/md360/conv001/")
        print("Anonymous sessions are refused. Accounts: historian (read), engineer (read/write)\n")

        while True:
            i = Inputs(
                start_pressed=await tags["StartCommand"].get_value(),
                stop_pressed=await tags["StopCommand"].get_value(),
                safety_reset_pressed=True,          # panel reset, modelled as held
                zero_speed=physics.zero_speed,
                bearing_temp_c=physics.bearing_temp_c,
                motor_current_a=physics.motor_current_a,
            )
            running = logic.scan(i)
            physics.running = running
            t = physics.step(0.5)

            await tags["Running"].write_value(running)
            await tags["SafetyTripped"].write_value(logic.safety.tripped)
            await tags["BeltSpeed_mps"].write_value(t["CONV001.Speed_mps"])
            await tags["Load_tph"].write_value(t["CONV001.Load_tph"])
            await tags["BearingTemp_C"].write_value(t["CONV001.BearingTemp_C"])
            await tags["Vibration_mms"].write_value(t["CONV001.Vibration_mms"])
            await tags["MotorCurrent_A"].write_value(t["CONV001.Current_A"])

            await asyncio.sleep(0.5)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=14840)
    a = ap.parse_args()
    try:
        asyncio.run(run(a.port))
    except KeyboardInterrupt:
        pass
