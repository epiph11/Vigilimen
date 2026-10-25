#!/usr/bin/env python3
"""
One gateway scan, with no OPC UA in it.

opcua_server.py used to hold this loop inline. It lives here so that the same
code can be driven by a test (FF-24) without asyncua, a socket to a browser,
or half a second of real time per step.

TWO MODES, ONE CONTRACT
-----------------------
link = None     "embedded": interlock_model.py plays BOTH controllers. This is
                the behaviour acceptance test 4e was written against, and it
                stays the default until the PLC link is validated in Docker.
link = PlcLink  "plc": PLC-CONV-001 (conveyor.st) is the control function.
                The Python SafetyFunction still stands in for SIS-CONV-001's
                hardwired contactor, because the SIS has no network path to
                reach (ADR-014). The motor turns only if

                    contactor energised  AND  PLC run request

                which is the series connection of ADR-011, as one line of code
                in the simulator and as copper on a real plant.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sim"))
sys.path.insert(0, str(HERE))

from conveyor_physics import Conveyor as Physics                       # noqa: E402
from interlock_model import Conveyor as Logic, Inputs, Contactor      # noqa: E402
from plc_link import PlcInputs, PlcLink                                # noqa: E402

FAULT_LIMITS = {
    "FaultBearingWear": 1.0,
    "FaultBeltSlip": 1.0,
    "FaultMisalignment": 1.0,
    "FaultIdlerSeizure": 1.0,
    "FaultVibrationSpike": 10.0,
}


def clamp_fault(raw, hi: float) -> float:
    """A bad write must not produce NaN physics."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if v != v:
        return 0.0
    return min(hi, max(0.0, v))


class PlantCycle:
    def __init__(self, link: PlcLink | None = None, dt_s: float = 0.5) -> None:
        self.link = link
        self.dt_s = dt_s
        self.physics = Physics()
        self.logic = Logic()
        self.last_plc = None          # last good PlcOutputs, for the OPC UA tags
        # The panel reset is pressed ONCE, on the first scan after start, to take the safety function out
        # of its cold-start trip. It used to be held for ever, which was harmless while reset acted on the
        # level and wrong once it acts on the edge (ADR-011): a held button must not be able to restart
        # the belt after a trip. Nothing in the simulation re-arms after a trip yet; that needs a reset tag.
        self._reset_pending = True

    def step(self, start: bool, stop: bool, faults: dict) -> dict:
        p, lg = self.physics, self.logic
        reset_now, self._reset_pending = self._reset_pending, False
        i = Inputs(
            start_pressed=bool(start),
            stop_pressed=bool(stop),
            safety_reset_pressed=reset_now,     # one press on the first scan; see __init__
            zero_speed=p.zero_speed,
            bearing_temp_c=p.bearing_temp_c,
            motor_current_a=p.motor_current_a,
        )
        p.deg.bearing_wear = clamp_fault(faults.get("FaultBearingWear"), 1.0)
        p.deg.belt_slip = clamp_fault(faults.get("FaultBeltSlip"), 1.0)
        p.deg.misalignment = clamp_fault(faults.get("FaultMisalignment"), 1.0)
        p.deg.idler_seizure = clamp_fault(faults.get("FaultIdlerSeizure"), 1.0)
        p.deg.vibration_spike_mms = clamp_fault(faults.get("FaultVibrationSpike"), 10.0)

        plc_ok, plc_state, plc_word = False, 0, 0
        if self.link is None:
            running = lg.scan(i)
        else:
            contactor = lg.safety.scan(i, int(self.dt_s * 1000))
            out = self.link.exchange(PlcInputs(
                start=i.start_pressed, stop=i.stop_pressed,
                zero_speed=i.zero_speed,
                bearing_temp_c=i.bearing_temp_c,
                motor_current_a=i.motor_current_a,
                belt_speed_mps=p.belt_speed_mps,
            ))
            # No usable PLC = no run request (fail-safe, plc_link.py point 1).
            run_request = out.motor_run if out is not None else False
            running = contactor is Contactor.ENERGISED and run_request
            if out is not None:
                plc_ok, plc_state, plc_word = True, out.state, out.alarm_word
                self.last_plc = out

        p.running = running
        t = p.step(self.dt_s)
        return {
            "Running": running,
            "SafetyTripped": lg.safety.tripped,
            "BeltSpeed_mps": t["CONV001.Speed_mps"],
            "Load_tph": t["CONV001.Load_tph"],
            "BearingTemp_C": t["CONV001.BearingTemp_C"],
            "Vibration_mms": t["CONV001.Vibration_mms"],
            "MotorCurrent_A": t["CONV001.Current_A"],
            "PlcLinkOK": plc_ok,
            "PlcState": plc_state,
            "PlcAlarmWord": plc_word,
        }
