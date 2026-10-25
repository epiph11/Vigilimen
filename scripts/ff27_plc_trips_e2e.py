#!/usr/bin/env python3
"""
FF-27 — conveyor.st's machine-protection trips, in the REAL OpenPLC (needs Docker, PLC link on).

FF-24 tested the 42 A and 95 degC trips against a Python PORT of conveyor.st. A port
proves the port. This drives the real program, through the real stack:

  1. START: the PLC runs its 10 s horn and the belt reaches speed (PlcState 3);
  2. 42 A: FaultBeltSlip + FaultIdlerSeizure push the motor current over 42 A through
     the physics, the PLC trips to FAULT (PlcState 5) and the belt stops;
  3. a FAULT is not cleared by START, only by STOP with the belt stopped (a fault
     needs an operator, not a timer);
  4. 95 degC: the bearing cannot reach 95 degC through the physics in any useful time
     (about 50 min with wear AND a seized idler, and the overload trips first), so the
     test WRITES the temperature register on the PLC directly over Modbus, once, and
     lets the gateway's next cycle overwrite it. That is also the S8 point in one line:
     Modbus has no identity, so anything on net_control can trip the machine with one
     frame. The trip is the program's own (BEARING_TRIP = 95.0), not a setpoint of mine.

Runs INSIDE the gateway container (it has asyncua and gateway/modbus.py):

    docker cp scripts\\ff27_plc_trips_e2e.py vigilimen-gateway:/tmp/ff27.py
    docker exec -e VIGILIMEN_OPCUA_PASSWORD=eng1neer-demo vigilimen-gateway python3 /tmp/ff27.py

Needs the plcio override and the program loaded (plant/tools/validate-plcio.ps1 does both).
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

for p in ("/opt/vigilimen/gateway", str(Path(__file__).resolve().parent.parent / "plant" / "gateway")):
    if Path(p).is_dir():
        sys.path.insert(0, p)

from asyncua import Client          # noqa: E402
from modbus import Client as Modbus  # noqa: E402

URL = os.environ.get("VIGILIMEN_OPCUA_URL", "opc.tcp://127.0.0.1:4840/vigilimen/conv001/")
USER = os.environ.get("VIGILIMEN_OPCUA_USER", "engineer")
PASSWORD = os.environ.get("VIGILIMEN_OPCUA_PASSWORD", "")
PLC_HOST = os.environ.get("VIGILIMEN_MODBUS_HOST", "plc-control")
HR_BEARING_TEMP_X10 = 100            # plc_io_map: %QW100
FAULTS = ["FaultBearingWear", "FaultBeltSlip", "FaultMisalignment", "FaultIdlerSeizure", "FaultVibrationSpike"]
results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((bool(ok), name, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""), flush=True)


async def nodes(c: Client) -> dict:
    ns = await c.get_namespace_index("urn:vigilimen:plant:conv001")
    r = c.nodes.objects
    for n in ("Enterprise", "PilbaraSite", "ProcessingArea", "ConveyingCell", "CONV001"):
        r = await r.get_child(f"{ns}:{n}")
    names = ["Running", "BeltSpeed_mps", "MotorCurrent_A", "BearingTemp_C", "StartCommand", "StopCommand",
             "PlcLinkOK", "PlcState"] + FAULTS
    return {n: await r.get_child(f"{ns}:{n}") for n in names}


async def until(pred, timeout_s: float, every_s: float = 0.2):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if await pred():
            return time.monotonic() - t0
        await asyncio.sleep(every_s)
    return None


async def main() -> int:
    if not PASSWORD:
        print("set VIGILIMEN_OPCUA_PASSWORD (docker exec -e ...)", file=sys.stderr)
        return 2
    print("FF-27 — conveyor.st trips in the real OpenPLC")
    c = Client(URL, timeout=10)
    c.set_user(USER)
    c.set_password(PASSWORD)
    await c.connect()
    try:
        n = await nodes(c)
        state = lambda: n["PlcState"].get_value()                       # noqa: E731

        async def is_state(v):
            return int(await state()) == v

        async def running():
            return bool(await n["Running"].get_value())

        async def stopped():
            return not await running()

        async def press_start():
            await n["StopCommand"].write_value(False)
            await n["StartCommand"].write_value(True)

        async def press_stop():
            await n["StartCommand"].write_value(False)
            await n["StopCommand"].write_value(True)

        async def clear_faults():
            for f in FAULTS:
                await n[f].write_value(0.0)

        async def reach_idle(label):
            await clear_faults()
            await press_stop()
            t = await until(lambda: is_state(0), 90)
            check(f"{label}: PLC back to STOPPED (state 0)", t is not None, f"{t:.1f} s" if t else "timed out")
            return t is not None

        check("PLC link up (PlcLinkOK)", bool(await n["PlcLinkOK"].get_value()),
              "run validate-plcio.ps1 first: the override and the program must be in place")
        if not results[-1][0]:
            return 1
        if not await reach_idle("setup"):
            return 1

        # ---- 1. START
        await press_start()
        t = await until(lambda: is_state(3), 40)
        check("START: PLC reaches RUNNING (state 3) after its horn", t is not None and t >= 9.0, f"{t:.1f} s" if t else "timed out")
        check("belt at speed", await until(lambda: _gt(n["BeltSpeed_mps"], 2.1), 10) is not None)
        await asyncio.sleep(2.0)

        # ---- 2. overload trip, through the physics
        await n["FaultBeltSlip"].write_value(1.0)
        await n["FaultIdlerSeizure"].write_value(1.0)
        t = await until(lambda: is_state(5), 30)
        check("slip + seized idler: current over 42 A, PLC trips to FAULT (state 5)", t is not None,
              f"{t:.1f} s" if t else "no trip in 30 s")
        t2 = await until(stopped, 10)
        check("...and the belt stops", t2 is not None)
        await clear_faults()

        # ---- 3. START does not clear a FAULT
        await press_start()
        await asyncio.sleep(4.0)
        check("START does NOT clear a FAULT (still state 5, belt stopped)",
              int(await state()) == 5 and not await running(),
              "a fault needs an operator pressing STOP, not a timer or a second START")
        await press_stop()
        t = await until(lambda: is_state(0), 90)
        check("STOP with the belt stopped and the machine cool clears it (state 0)", t is not None,
              f"{t:.1f} s" if t else "timed out (is the bearing under 85 degC and the current under 1 A?)")

        # ---- 4. 95 degC trip, by a direct Modbus write
        await press_start()
        t = await until(lambda: is_state(3), 40)
        check("START again: RUNNING", t is not None)
        m = Modbus(PLC_HOST, 502)
        ok = m.connect(3.0)
        check("direct Modbus connection to the PLC (no credential asked for)", ok)
        if ok:
            for _ in range(3):                                   # the gateway rewrites it every 0.5 s
                m.write_register(HR_BEARING_TEMP_X10, 960)       # 96.0 degC
                await asyncio.sleep(0.1)
            m.close()
            t = await until(lambda: is_state(5), 5)
            check("one forged frame (bearing = 96.0 degC): the PLC trips to FAULT", t is not None,
                  f"{t:.2f} s" if t else "no trip. BEARING_TRIP in the loaded program?")
            t2 = await until(stopped, 10)
            check("...and the belt stops", t2 is not None)
        await press_stop()
        t = await until(lambda: is_state(0), 90)
        check("recovered to STOPPED (state 0)", t is not None, f"{t:.1f} s" if t else "timed out")
    finally:
        try:
            await clear_faults()
            await press_stop()
        finally:
            await c.disconnect()

    failed = [r for r in results if not r[0]]
    print(f"\n{len(results)} checks, {len(failed)} failed")
    print("FF-27 pass." if not failed else "FF-27 FAIL: write symptom, cause, fix in docs/runs/NOTES.md BEFORE changing anything.")
    return 1 if failed else 0


async def _gt(node, x):
    return float(await node.get_value()) > x


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
