#!/usr/bin/env python3
"""
CONV-001 — conveyor physics simulator.

Produces the process values the control function reads: belt speed, load,
bearing temperature, vibration and motor current. Degradation is INJECTABLE,
because the point of this simulator is not to model a conveyor accurately —
it is to produce a signal that S13's predictive maintenance model can learn
and that S8's attack scenarios can falsify.

    python3 plant/sim/conveyor_physics.py --demo

WHAT THIS IS FOR, IN ORDER
  S4   values to historise and alarm on
  S8   a baseline an attacker can be shown to have altered
  S13  a degradation signal a model can be trained against
  S24  a detection surface where a falsified value is distinguishable
       from a real one — which is the hard part

WHAT THIS IS NOT
  Accurate. Bearing thermal mass, belt tension and drive efficiency here are
  plausible rather than derived. ADR-003 records the limitation once so it
  need not be re-litigated: the protocols are real, the physics is not.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass, field


AMBIENT_C = 28.0          # Pilbara-ish. Ambient matters: a 40 C day moves
                          # every bearing alarm threshold whether or not
                          # anything is actually wrong.
BELT_SPEED_MPS = 2.5
DESIGN_LOAD_TPH = 850.0
NO_LOAD_CURRENT_A = 8.0
FULL_LOAD_CURRENT_A = 38.0


@dataclass
class Degradation:
    """Injectable faults. Each is a real conveyor failure mode.

    They are separate because they are DISTINGUISHABLE in the data, and
    that distinguishability is what S13 has to learn and what S8 has to
    defeat. A single 'health 0..1' scalar would make both exercises trivial
    and meaningless.
    """

    bearing_wear: float = 0.0      # 0..1 — heat and vibration rise together
    belt_slip: float = 0.0         # 0..1 — current up, speed down
    misalignment: float = 0.0      # 0..1 — vibration up, speed steady
    idler_seizure: float = 0.0     # 0..1 — current up, localised heat

    def any_active(self) -> bool:
        return any(v > 0 for v in (self.bearing_wear, self.belt_slip,
                                   self.misalignment, self.idler_seizure))


@dataclass
class Conveyor:
    running: bool = False
    load_tph: float = 0.0
    bearing_temp_c: float = AMBIENT_C
    t: float = 0.0
    deg: Degradation = field(default_factory=Degradation)
    rng: random.Random = field(default_factory=lambda: random.Random(20260914))

    # --- derived process values -------------------------------------------

    @property
    def belt_speed_mps(self) -> float:
        if not self.running:
            return 0.0
        return BELT_SPEED_MPS * (1.0 - 0.18 * self.deg.belt_slip)

    @property
    def motor_current_a(self) -> float:
        if not self.running:
            return 0.0
        load_frac = min(self.load_tph / DESIGN_LOAD_TPH, 1.3)
        base = NO_LOAD_CURRENT_A + (FULL_LOAD_CURRENT_A - NO_LOAD_CURRENT_A) * load_frac
        base *= 1.0 + 0.22 * self.deg.belt_slip      # slipping belt draws more
        base *= 1.0 + 0.30 * self.deg.idler_seizure  # a seized idler is a brake
        base *= 1.0 + 0.05 * self.deg.bearing_wear
        return base + self.rng.gauss(0, 0.25)

    @property
    def vibration_mms(self) -> float:
        """RMS velocity, mm/s. ISO 10816 territory: ~2.8 good, ~7 alarm."""
        if not self.running:
            return 0.0
        v = 1.6
        v += 5.5 * self.deg.bearing_wear ** 1.5   # accelerates, not linear
        v += 4.0 * self.deg.misalignment
        v += 2.0 * self.deg.idler_seizure
        v += 0.4 * (self.load_tph / DESIGN_LOAD_TPH)
        return max(0.0, v + self.rng.gauss(0, 0.12))

    @property
    def zero_speed(self) -> bool:
        return self.belt_speed_mps < 0.1

    # --- the one value with memory ----------------------------------------

    def _step_bearing(self, dt_s: float) -> None:
        """First-order thermal lag toward a load- and wear-dependent target.

        Temperature is the only value here that CANNOT be spoofed for a
        single sample without leaving a trace, because it has a time
        constant. A bearing that jumps 20 C in one scan is not a bearing;
        it is a write. That is the S24 detection idea in one sentence, and
        it is the reason this is modelled with memory rather than computed
        fresh each step.
        """
        if not self.running:
            target = AMBIENT_C
            tau = 900.0
        else:
            rise = 26.0 * (self.load_tph / DESIGN_LOAD_TPH)
            rise += 34.0 * self.deg.bearing_wear
            rise += 12.0 * self.deg.idler_seizure
            target = AMBIENT_C + rise
            tau = 420.0

        self.bearing_temp_c += (target - self.bearing_temp_c) * (dt_s / tau)
        self.bearing_temp_c += self.rng.gauss(0, 0.04)

    # --- tick ---------------------------------------------------------------

    def step(self, dt_s: float = 1.0) -> dict:
        self.t += dt_s
        if self.running:
            # Feed rate wanders the way a real one does.
            wander = 0.10 * DESIGN_LOAD_TPH * math.sin(self.t / 220.0)
            self.load_tph = max(0.0, 0.78 * DESIGN_LOAD_TPH + wander + self.rng.gauss(0, 12))
        else:
            self.load_tph = 0.0

        self._step_bearing(dt_s)
        return self.tags()

    def tags(self) -> dict:
        """ISA-95 style tag names — the shape S4's historian will use."""
        return {
            "CONV001.Run":           self.running,
            "CONV001.Speed_mps":     round(self.belt_speed_mps, 3),
            "CONV001.Load_tph":      round(self.load_tph, 1),
            "CONV001.BearingTemp_C": round(self.bearing_temp_c, 2),
            "CONV001.Vibration_mms": round(self.vibration_mms, 3),
            "CONV001.Current_A":     round(self.motor_current_a, 2),
            "CONV001.ZeroSpeed":     self.zero_speed,
        }


def demo() -> None:
    """Run a shift, inject a bearing fault at the two-hour mark, watch it grow."""
    c = Conveyor()
    c.running = True

    print(f"{'hh:mm':>7}  {'temp C':>7} {'vib mm/s':>9} {'amps':>6} {'t/h':>6}   state")
    print("  " + "-" * 62)

    for minute in range(0, 481, 20):
        for _ in range(20):
            c.step(60.0)

        # Bearing wear appears at t+2h and grows. It is deliberately gradual:
        # a fault that arrives fully formed teaches a model nothing, and an
        # attacker who wants to hide inside the noise has to be gradual too.
        if minute >= 120:
            c.deg.bearing_wear = min(1.0, (minute - 120) / 420.0)

        tg = c.tags()
        temp = tg["CONV001.BearingTemp_C"]
        state = ("TRIP  >= 95" if temp >= 95 else
                 "alarm >= 85" if temp >= 85 else
                 "")
        print(f"  {minute // 60:02d}:{minute % 60:02d}  "
              f"{temp:7.2f} {tg['CONV001.Vibration_mms']:9.2f} "
              f"{tg['CONV001.Current_A']:6.2f} {tg['CONV001.Load_tph']:6.0f}   {state}")

    print("\n  Vibration leads temperature — it rises with the square of wear while")
    print("  temperature lags behind a 7-minute thermal constant. That ordering is")
    print("  the predictive signal at S13, and it is also what an attacker has to")
    print("  reproduce to forge a plausible bearing.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="CONV-001 physics simulator")
    ap.add_argument("--demo", action="store_true", help="run an 8-hour shift with an injected bearing fault")
    a = ap.parse_args()
    if a.demo:
        demo()
    else:
        c = Conveyor(); c.running = True
        for _ in range(60):
            c.step()
        for k, v in c.tags().items():
            print(f"  {k:26} {v}")
