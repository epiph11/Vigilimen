#!/usr/bin/env python3
"""
Test vectors for the safety function: what the PYTHON MODEL says each scan should do.

ADR-014 admits that safety.st has never been driven by an input, so the model
(plant/sim/interlock_model.py, which FF-06 proves things about) and the program
(plant/plc-safety/safety.st, which FF-21 reads) have never been compared by
EXECUTION. This writes the model's side: a CSV of scans, each with the seven
inputs, the scan length, and the outputs the model produces.

    python scripts/safety_vectors.py safety_vectors.csv      (writes UTF-8 with LF; do NOT use `>` in
    Windows PowerShell 5.1, which writes UTF-16)

Columns: scenario, step, dt_ms, estop_a, estop_b, cord_a, cord_b, drift_ok, guard_closed,
         reset, model_contactor, model_tripped, spec_contactor, spec_tripped

TWO EXPECTATIONS, ON PURPOSE. The model is only an oracle if it is right. The requirement (ADR-011)
is the authority. Where the two differ, the SPEC column says what ADR-011 requires and the model
column says what the model does; the replay reports disagreement with each separately, and a program
that matches the model but not the spec is the worse outcome, not the better one. SPEC_OVERRIDES
lists every place they differ, with the reason, so nobody has to rediscover it.

The other side (running safety.st through MatIEC's generated C) needs the OpenPLC image
and lives in plant/tools/replay-safety.ps1. Anywhere the two disagree, one of them is wrong,
and the disagreement is the finding. Known candidate, from reading both: the MODEL resets on
the reset LEVEL, the PROGRAM only on a rising EDGE (ADR-011 says edge).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plant" / "sim"))
from interlock_model import Contactor, Inputs, SafetyFunction  # noqa: E402

H = dict(estop_a=1, estop_b=1, cord_a=1, cord_b=1, drift_ok=1, guard_closed=1, reset=0)


def s(dt=100, **kw):
    d = dict(H); d.update(kw); d["dt"] = dt; return d


SCENARIOS = {
    "boot_tripped_no_reset": [s(), s(), s()],
    "boot_then_reset_pulse": [s(), s(reset=1), s(reset=0), s()],
    "estop_drops": [s(reset=1), s(reset=0), s(estop_a=0, estop_b=0), s(estop_a=0, estop_b=0)],
    "demand_clears_no_restart": [s(reset=1), s(reset=0), s(estop_a=0, estop_b=0), s(), s(), s()],
    "reset_after_clear": [s(reset=1), s(reset=0), s(estop_a=0, estop_b=0), s(), s(reset=1), s(reset=0), s()],
    "reset_pulse_while_demanded": [s(reset=1), s(reset=0), s(estop_a=0, estop_b=0), s(estop_a=0, estop_b=0, reset=1), s(estop_a=0, estop_b=0, reset=0)],
    "pullcord_one_channel_fault_short": [s(reset=1), s(reset=0), s(cord_a=0, dt=100), s(cord_a=0, dt=100)],
    "pullcord_discrepancy_to_fault": [s(reset=1), s(reset=0)] + [s(cord_a=0, dt=100) for _ in range(8)],
    "belt_drift_trips": [s(reset=1), s(reset=0), s(drift_ok=0), s(drift_ok=1), s(drift_ok=1)],
    "guard_open_trips": [s(reset=1), s(reset=0), s(guard_closed=0), s(guard_closed=1), s()],
    "reset_refused_while_guard_open": [s(reset=1), s(reset=0), s(guard_closed=0), s(guard_closed=0, reset=1), s(guard_closed=0, reset=0)],
    # The candidate divergence: reset HELD high across a trip.
    "reset_held_across_trip": [s(reset=1), s(reset=1), s(reset=1, estop_a=0, estop_b=0), s(reset=1), s(reset=1)],
}


# (scenario, step) -> (contactor, tripped) required by ADR-011 where the MODEL does something else.
SPEC_OVERRIDES = {
    # ADR-011: reset is a rising EDGE, so a held or jammed button cannot restart the belt when a demand
    # clears. The model resets on the LEVEL of safety_reset_pressed and re-energises here.
    ("reset_held_across_trip", 3): (0, 1),
    ("reset_held_across_trip", 4): (0, 1),
}


def main() -> None:
    lines = ["scenario,step,dt_ms,estop_a,estop_b,cord_a,cord_b,drift_ok,guard_closed,reset,model_contactor,model_tripped,spec_contactor,spec_tripped"]
    for name, steps in SCENARIOS.items():
        sf = SafetyFunction()
        for n, st in enumerate(steps):
            i = Inputs(estop_ch_a=bool(st["estop_a"]), estop_ch_b=bool(st["estop_b"]),
                       pullcord_ch_a=bool(st["cord_a"]), pullcord_ch_b=bool(st["cord_b"]),
                       belt_drift_ok=bool(st["drift_ok"]), guard_closed=bool(st["guard_closed"]),
                       safety_reset_pressed=bool(st["reset"]))
            c = sf.scan(i, st["dt"])
            mc, mt = int(c is Contactor.ENERGISED), int(sf.tripped)
            sc, stt = SPEC_OVERRIDES.get((name, n), (mc, mt))
            lines.append(f"{name},{n},{st['dt']},{st['estop_a']},{st['estop_b']},{st['cord_a']},{st['cord_b']},"
                         f"{st['drift_ok']},{st['guard_closed']},{st['reset']},{mc},{mt},{sc},{stt}")
    text = "\n".join(lines) + "\n"
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text, encoding="utf-8", newline="")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
