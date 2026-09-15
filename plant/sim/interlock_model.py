#!/usr/bin/env python3
"""
Reference model of CONV-001's control and safety functions.

WHY THIS FILE EXISTS
--------------------
The real logic ships as Structured Text for OpenPLC:

    plant/plc-control/conveyor.st     the control function
    plant/plc-safety/safety.st        the safety function

Structured Text cannot be executed in CI without the runtime, and a safety
claim that is only asserted in prose is not a safety claim. This module is a
line-for-line model of the same two programs, so FF-06 can execute the
INDEPENDENCE argument on every commit.

WHAT THIS DOES NOT PROVE
------------------------
That the ST matches this model. Two implementations of one idea drift, and
the drift is invisible until something fails. Three mitigations, in order of
strength:

  1. The model and the ST are edited in the same commit. The PR template
     asks; nothing enforces it.
  2. At S4 the ST runs against the same test vectors this model does.
  3. The only test that settles it is the witnessed one: run the conveyor,
     de-energise the control PLC, press the e-stop, watch the contactor
     drop. That is SAT-11's shape, and no amount of Python replaces it.

This file is therefore evidence that the LOGIC is independent. It is not
evidence that the PLANT is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Contactor(Enum):
    """The motor contactor. Energised runs the belt; de-energised stops it.

    It is de-energise-to-trip on purpose: loss of power, loss of wire and
    loss of the safety controller all produce the same outcome as a demand.
    A trip mechanism that needs power to trip has a failure mode that looks
    exactly like normal operation.
    """
    ENERGISED = "energised"
    DROPPED = "dropped"


@dataclass
class Inputs:
    """Field inputs. Dual-channel devices are read as two independent signals.

    Safety convention throughout: True = healthy / not demanded.
    A broken wire reads False, which is a demand. Fail-safe is a wiring
    decision before it is a logic decision.
    """
    estop_ch_a: bool = True
    estop_ch_b: bool = True
    pullcord_ch_a: bool = True
    pullcord_ch_b: bool = True
    belt_drift_ok: bool = True
    guard_closed: bool = True

    # Process values, read by the control function only.
    zero_speed: bool = True
    bearing_temp_c: float = 40.0
    motor_current_a: float = 0.0

    # Operator intent, control function only.
    start_pressed: bool = False
    stop_pressed: bool = False
    safety_reset_pressed: bool = False


# ---------------------------------------------------------------------------
# The safety function — SIS-CONV-001
# ---------------------------------------------------------------------------

@dataclass
class SafetyFunction:
    """Independent safety controller.

    Its output is a hardwired drop of the motor contactor coil. It takes NO
    input from the control function, is on a separate zone, and has its own
    I/O. The control function cannot inhibit, bypass, delay or acknowledge a
    trip — there is no path by which it could, which is the point.
    """

    tripped: bool = True          # starts tripped; a cold start is not a safe start
    trip_reason: str = "initial state — never energised"
    discrepancy_timer_ms: int = 0
    DISCREPANCY_LIMIT_MS: int = 500

    def scan(self, i: Inputs, dt_ms: int = 100) -> Contactor:
        """One scan of the safety logic. Returns the contactor state."""

        # --- dual-channel evaluation ---------------------------------------
        estop_demanded = not (i.estop_ch_a and i.estop_ch_b)
        cord_demanded = not (i.pullcord_ch_a and i.pullcord_ch_b)

        # A discrepancy between channels is a FAULT, not a vote. One channel
        # healthy and one not means a broken wire or a welded contact, and
        # either way the device can no longer be trusted to demand a stop
        # when it is needed. Discrepancy persisting past the limit trips.
        estop_discrepant = i.estop_ch_a != i.estop_ch_b
        cord_discrepant = i.pullcord_ch_a != i.pullcord_ch_b

        if estop_discrepant or cord_discrepant:
            self.discrepancy_timer_ms += dt_ms
        else:
            self.discrepancy_timer_ms = 0

        discrepancy_fault = self.discrepancy_timer_ms >= self.DISCREPANCY_LIMIT_MS

        # --- trip conditions ------------------------------------------------
        for demanded, reason in (
            (estop_demanded, "emergency stop"),
            (cord_demanded, "pull-cord"),
            (not i.belt_drift_ok, "belt drift"),
            (not i.guard_closed, "guard open"),
            (discrepancy_fault, "channel discrepancy — device fault"),
        ):
            if demanded:
                self.tripped = True
                self.trip_reason = reason
                return Contactor.DROPPED

        # --- reset ----------------------------------------------------------
        # A trip latches. Clearing the demand does NOT restart the belt:
        # someone must press reset, having looked at why it tripped. Automatic
        # restart on demand-clear is how a person who pressed an e-stop and
        # walked to the belt gets hurt by it starting again behind them.
        if self.tripped:
            if i.safety_reset_pressed:
                self.tripped = False
                self.trip_reason = ""
                return Contactor.ENERGISED
            return Contactor.DROPPED

        return Contactor.ENERGISED


# ---------------------------------------------------------------------------
# The control function — PLC-CONV-001
# ---------------------------------------------------------------------------

class ControlState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAULT = "fault"


@dataclass
class ControlFunction:
    """Ordinary conveyor control. Sequencing, interlocks, process alarms.

    It requests the motor to run. It cannot force it: its run request is
    ANDed with the safety contactor downstream, in hardware.
    """

    state: ControlState = ControlState.STOPPED
    run_request: bool = False
    alarms: list[str] = field(default_factory=list)

    BEARING_ALARM_C: float = 85.0
    BEARING_TRIP_C: float = 95.0

    def scan(self, i: Inputs) -> bool:
        """One scan. Returns the control function's RUN REQUEST only."""
        self.alarms = []

        if i.bearing_temp_c >= self.BEARING_ALARM_C:
            self.alarms.append(f"bearing temperature {i.bearing_temp_c:.1f} C")

        # A process trip on bearing temperature. Note that this is a CONTROL
        # action, not a safety one: it protects the machine, not a person,
        # and it therefore lives here rather than in the safety function.
        # Putting machine protection into the safety controller inflates the
        # safety function with demands that have nothing to do with people,
        # and every added demand is another way for it to fail spuriously.
        if i.bearing_temp_c >= self.BEARING_TRIP_C:
            self.state = ControlState.FAULT
            self.run_request = False
            self.alarms.append("bearing overtemperature trip")
            return False

        if i.stop_pressed:
            self.state = ControlState.STOPPING
            self.run_request = False
            return False

        if self.state in (ControlState.STOPPED, ControlState.STOPPING) and i.start_pressed:
            self.state = ControlState.STARTING
            self.run_request = True
            return True

        if self.state == ControlState.STARTING:
            self.state = ControlState.RUNNING if not i.zero_speed else ControlState.STARTING
            self.run_request = True
            return True

        if self.state == ControlState.RUNNING:
            self.run_request = True
            return True

        self.run_request = False
        return False


# ---------------------------------------------------------------------------
# The plant — how the two are wired together
# ---------------------------------------------------------------------------

@dataclass
class Conveyor:
    """CONV-001.

    The motor runs only when BOTH the safety contactor is energised AND the
    control function requests it. That AND is a physical series connection
    between the safety relay output and the control PLC's motor output — not
    a line of logic in either controller.

    The asymmetry is the whole design:
      - the control function can STOP the belt (drop its own request)
      - the control function CANNOT START the belt against a safety trip
      - the safety function can stop the belt with the control PLC absent,
        powered down, disconnected, or actively commanding RUN
    """

    safety: SafetyFunction = field(default_factory=SafetyFunction)
    control: ControlFunction | None = field(default_factory=ControlFunction)

    def scan(self, i: Inputs, dt_ms: int = 100) -> bool:
        """Returns True if the motor is turning."""
        contactor = self.safety.scan(i, dt_ms)

        # `control is None` models the control PLC being absent: powered
        # down, crashed, or on a severed network. Its run request is then
        # simply not present, which is the same as not requesting.
        run_request = self.control.scan(i) if self.control is not None else False

        return contactor is Contactor.ENERGISED and run_request

    def motor_would_run_if_commanded(self, i: Inputs, dt_ms: int = 100) -> bool:
        """Could a RUN command from anywhere turn the motor right now?

        Models an adversary in full control of the control function — one who
        can write any output, forge any command, and hold the run request
        asserted indefinitely. If this returns False, the safety function is
        holding the belt regardless of what the control side does.
        """
        return self.safety.scan(i, dt_ms) is Contactor.ENERGISED
