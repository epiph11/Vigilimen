#!/usr/bin/env python3
"""
FF-06 — the safety function is independent of the control function.

This is the fitness function behind the programme's central safety claim, and
behind Sprint 3's definition of done:

    "Interlock trips with every container except the PLC stopped."
    "Safety function operates with the control network severed."

Every case models an adversary who has WON on the control side — who owns the
control PLC, can forge any command, and can hold RUN asserted for as long as
they like. The question each case asks is the only one that matters:

    can the belt turn?

    python3 scripts/ff06_safety_independence.py
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plant" / "sim"))

from interlock_model import (  # noqa: E402
    Contactor,
    ControlFunction,
    Conveyor,
    Inputs,
    SafetyFunction,
)

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, condition: bool, why: str) -> None:
    results.append((PASS if condition else FAIL, name, why))


def running_conveyor() -> Conveyor:
    """A conveyor that has been reset and started, and is running."""
    c = Conveyor()
    i = Inputs(safety_reset_pressed=True)
    c.scan(i)                                    # clear the initial trip
    i = Inputs(start_pressed=True, zero_speed=False)
    c.scan(i)
    i = Inputs(zero_speed=False)
    assert c.scan(i), "fixture failure: conveyor did not start"
    return c


# ===========================================================================
# 1. The baseline. Without this, every test below passes trivially.
# ===========================================================================

c = running_conveyor()
check(
    "baseline — the belt runs when nothing is demanded",
    c.scan(Inputs(zero_speed=False)) is True,
    "a safety function that stops everything always is not independent, it is broken. "
    "Every case below is meaningless unless the belt can run at all.",
)

# ===========================================================================
# 2. Independence — the control side has lost
# ===========================================================================

c = running_conveyor()
c.control = None  # the control PLC is powered down / crashed / unreachable
check(
    "e-stop trips with the control PLC ABSENT",
    c.motor_would_run_if_commanded(Inputs(estop_ch_a=False, estop_ch_b=False)) is False,
    "the DoD case: the interlock trips with every container except the PLC stopped",
)

c = running_conveyor()
check(
    "e-stop trips while the control function is holding RUN",
    c.scan(Inputs(estop_ch_a=False, estop_ch_b=False, start_pressed=True, zero_speed=False)) is False,
    "models an adversary with the control PLC, commanding RUN through the demand",
)

c = running_conveyor()
c.control = ControlFunction()
c.control.run_request = True
check(
    "the control function cannot INHIBIT a trip",
    c.motor_would_run_if_commanded(Inputs(estop_ch_a=False, estop_ch_b=False)) is False,
    "there is no path from the control function into the safety logic. If this ever "
    "fails, someone has added an interlock bypass and it is a design defect, not a bug",
)

c = running_conveyor()
check(
    "safety holds with the control NETWORK severed",
    c.motor_would_run_if_commanded(Inputs(pullcord_ch_a=False, pullcord_ch_b=False)) is False,
    "the second DoD case. The safety controller has its own I/O and needs no network at all",
)

# ===========================================================================
# 3. Fail-safe wiring — a broken wire is a demand
# ===========================================================================

c = running_conveyor()
check(
    "a broken e-stop wire reads as a demand",
    c.motor_would_run_if_commanded(Inputs(estop_ch_a=False, estop_ch_b=False)) is False,
    "True = healthy is the convention. De-energise-to-trip means loss of wire, loss of "
    "power and a real demand all produce the same outcome",
)

c = Conveyor()
check(
    "a cold start is not a safe start",
    c.motor_would_run_if_commanded(Inputs()) is False,
    "the safety function boots TRIPPED. A controller that powers up permissive has "
    "decided the plant is safe without having looked at it",
)

# ===========================================================================
# 4. Dual channel — a discrepancy is a fault, not a vote
# ===========================================================================

c = running_conveyor()
single = Inputs(estop_ch_a=False, estop_ch_b=True, zero_speed=False)
immediately = c.motor_would_run_if_commanded(single, dt_ms=100)
check(
    "one e-stop channel open trips on the channel that IS demanded",
    immediately is False,
    "a demand on either channel is a demand. The discrepancy timer is about the "
    "device's health, not about whether to stop",
)

c = running_conveyor()
# Model a welded contact: channel A stuck HEALTHY while channel B is demanded,
# then B recovers. The discrepancy persisted — the device is not trustworthy.
s = SafetyFunction(tripped=False)
for _ in range(6):
    s.scan(Inputs(estop_ch_a=True, estop_ch_b=False), dt_ms=100)
after = s.scan(Inputs(estop_ch_a=True, estop_ch_b=True), dt_ms=100)
check(
    "a sustained channel discrepancy latches a device fault",
    after is Contactor.DROPPED and s.tripped,
    "one channel healthy and one not means a broken wire or a welded contact. Either "
    "way the device can no longer be trusted to demand a stop WHEN IT IS NEEDED, which "
    "is a different and worse failure than a spurious trip",
)

# ===========================================================================
# 5. Latching — clearing the demand is not permission to restart
# ===========================================================================

c = running_conveyor()
c.scan(Inputs(estop_ch_a=False, estop_ch_b=False))       # trip
still = c.scan(Inputs(zero_speed=False, start_pressed=True))  # demand cleared, start pressed
check(
    "clearing the demand does NOT restart the belt",
    still is False,
    "somebody pressed that e-stop and is now standing at the belt. Automatic restart "
    "on demand-clear is how they get hurt by it starting behind them",
)

c = running_conveyor()
c.scan(Inputs(estop_ch_a=False, estop_ch_b=False))
c.scan(Inputs(safety_reset_pressed=True))
restarted = c.scan(Inputs(start_pressed=True, zero_speed=False))
check(
    "after a manual reset AND a start, the belt runs again",
    restarted is True,
    "reset must actually work, or operations will bypass it — and a bypassed safety "
    "function is worse than an inconvenient one",
)

# ===========================================================================
# 6. Scope — machine protection belongs to CONTROL, not to safety
# ===========================================================================

c = running_conveyor()
hot = Inputs(bearing_temp_c=99.0, zero_speed=False, start_pressed=True)
check(
    "bearing overtemperature stops the belt via the CONTROL function",
    c.scan(hot) is False,
    "machine protection, correctly placed on the control side",
)

c = running_conveyor()
check(
    "bearing overtemperature does NOT trip the safety function",
    c.motor_would_run_if_commanded(Inputs(bearing_temp_c=99.0)) is True,
    "the safety function protects PEOPLE. Loading it with machine protection adds "
    "demands that have nothing to do with anyone's safety, and every added demand is "
    "another way for it to trip spuriously — which is how it ends up bypassed",
)

# ===========================================================================

failures = [r for r in results if r[0] == FAIL]
width = max(len(n) for _, n, _ in results)

print("FF-06 — safety function independence\n")
for status, name, why in results:
    print(f"  {status}  {name.ljust(width)}")
    if status == FAIL:
        print(f"        why this case exists: {why}")

print(f"\n{len(results)} cases, {len(failures)} failed")

if failures:
    print("\nFF-06 FAIL — the safety function is not independent of the control function.")
    print("This is the TRITON shape. Do not proceed to S4 until it passes.")
    sys.exit(1)

print("""
FF-06 pass.

What this proves: the safety LOGIC is independent of the control logic.
What it does not prove: that the plant is. That needs the witnessed test —
run the conveyor, de-energise the control PLC, press the e-stop, watch the
contactor drop. It is SAT-11's shape from the hydro assessment, and no
amount of Python replaces standing there while it happens.""")
