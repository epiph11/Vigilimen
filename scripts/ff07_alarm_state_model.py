#!/usr/bin/env python3
"""
FF-07 — the alarm state model behaves as ISA-18.2 describes.

Sprint 4's definition of done says alarms must exist as a MANIPULABLE
SURFACE. Manipulable means an adversary can shelve, suppress or take an
alarm out of service — so every one of those paths has to be correct and
auditable before S8 tries to abuse them.

Each case below is a way an alarm system fails while still looking like it
works.

    python3 scripts/ff07_alarm_state_model.py
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plant" / "alarms"))

from engine import (  # noqa: E402
    Priority,
    State,
    build_conv001,
    utcnow,
)

results: list[tuple[bool, str, str]] = []


def check(name: str, cond: bool, why: str) -> None:
    results.append((cond, name, why))


T0 = utcnow()


def at(sec: float):
    return T0 + timedelta(seconds=sec)


# ===========================================================================
# 1. The basic cycle
# ===========================================================================

e = build_conv001()
e.evaluate("CONV001.BearingTemp_C", 90.0, at(0))
e.evaluate("CONV001.BearingTemp_C", 90.0, at(11))     # past the 10 s on-delay
check("HI raises after the on-delay",
      e.get("CONV001.BearingTemp_C", "HI").state is State.UNACK,
      "a transient excursion is noise; a sustained one is an alarm")

e.acknowledge("CONV001.BearingTemp_C", "HI", "operator.chen", at(20))
check("acknowledge moves UNACK to ACKED",
      e.get("CONV001.BearingTemp_C", "HI").state is State.ACKED,
      "acknowledged means SEEN, not FIXED — the condition is still true")

e.evaluate("CONV001.BearingTemp_C", 80.0, at(40))
check("clearing an ACKED alarm returns it to NORMAL",
      e.get("CONV001.BearingTemp_C", "HI").state is State.NORMAL,
      "seen, then cleared — nothing outstanding")

# ===========================================================================
# 2. The transition that matters
# ===========================================================================

e = build_conv001()
e.evaluate("CONV001.BearingTemp_C", 90.0, at(0))
e.evaluate("CONV001.BearingTemp_C", 90.0, at(11))
e.evaluate("CONV001.BearingTemp_C", 80.0, at(30))     # cleared, never acked
a = e.get("CONV001.BearingTemp_C", "HI")
check("an unacknowledged alarm that clears becomes RTN_UNACK",
      a.state is State.RTN_UNACK,
      "THE state a boolean alarm erases. The plant told somebody and the "
      "record shows nobody was there — routinely the most interesting line "
      "in a post-incident review")

check("RTN_UNACK still appears on the operator's list",
      a in e.active(),
      "it cleared, but it has not been seen. Dropping it off the list is "
      "how the event disappears")

e.acknowledge("CONV001.BearingTemp_C", "HI", "operator.chen", at(60))
check("acknowledging RTN_UNACK finally closes it",
      e.get("CONV001.BearingTemp_C", "HI").state is State.NORMAL,
      "the acknowledgement is the record that a human saw it")

# ===========================================================================
# 3. Deadband — asymmetric on purpose
# ===========================================================================

e = build_conv001()
e.evaluate("CONV001.BearingTemp_C", 95.5, at(0))      # HI_HI, no on-delay
check("HI_HI raises immediately, with no on-delay",
      e.get("CONV001.BearingTemp_C", "HI_HI").state is State.UNACK,
      "urgent alarms do not wait. The on-delay is for nuisance, not for safety")

e.evaluate("CONV001.BearingTemp_C", 94.0, at(5))      # inside the 2.0 deadband
check("a value inside the deadband does NOT clear the alarm",
      e.get("CONV001.BearingTemp_C", "HI_HI").in_condition is True,
      "without deadband a value hovering at the limit chatters — on, off, on, "
      "off — and a chattering alarm is how a console becomes unreadable")

e.evaluate("CONV001.BearingTemp_C", 92.0, at(9))      # below limit - deadband
check("a value past the deadband does clear it",
      e.get("CONV001.BearingTemp_C", "HI_HI").in_condition is False,
      "the deadband delays the CLEAR, never the RAISE")

# ===========================================================================
# 4. Shelving — the operator's escape hatch, bounded
# ===========================================================================

e = build_conv001()
e.evaluate("CONV001.Vibration_mms", 5.0, at(0))
e.evaluate("CONV001.Vibration_mms", 5.0, at(31))
e.shelve("CONV001.Vibration_mms", "HI", "operator.chen", minutes=30, now=at(40))
check("shelving hides the alarm from the active list",
      e.get("CONV001.Vibration_mms", "HI") not in e.active(),
      "the operator has a real reason and a real need to quieten a console")

check("a shelved alarm still appears in the hidden list",
      e.get("CONV001.Vibration_mms", "HI") in e.hidden(),
      "hidden from the LIST, never from the AUDIT. The weekly review of this "
      "list is where an alarm goes to be found again")

try:
    e.shelve("CONV001.Current_A", "HI", "operator.chen", minutes=0)
    unbounded_rejected = False
except ValueError:
    unbounded_rejected = True
check("a zero or unbounded shelf is refused",
      unbounded_rejected,
      "unlimited shelving is suppression wearing an operator's name — how a "
      "plant ends up with an alarm off for four years and nobody able to say why")

e.unshelve_expired(now=at(40 + 31 * 60))
check("the shelf expires by itself and the alarm comes back",
      e.get("CONV001.Vibration_mms", "HI").state is State.UNACK,
      "expiry must not depend on anyone remembering")

# ===========================================================================
# 5. Suppression and out-of-service — and the record they leave
# ===========================================================================

e = build_conv001()
e.suppress("CONV001.Speed_mps", "LO", "belt stopped — downstream low-flow is arithmetic", now=at(0))
e.evaluate("CONV001.Speed_mps", 0.5, at(5))
check("a suppressed alarm raises no event at all",
      e.get("CONV001.Speed_mps", "LO").state is State.SUPPRESSED,
      "suppression by design is legitimate: a known consequence of another "
      "alarm is not news")

suppress_events = [ev for ev in e.events if ev.to_state is State.SUPPRESSED]
check("suppression records its reason",
      bool(suppress_events) and bool(suppress_events[0].note),
      "a suppression that does not name its cause is indistinguishable from "
      "an alarm somebody turned off")

e = build_conv001()
e.out_of_service("CONV001.Current_A", "HI", "tech.okonkwo", at(0))
# Two evaluations, because Current_A HI carries a 5 s on-delay. The first
# version of this case called evaluate once and then asserted the alarm
# re-raised on return to service — it had never entered the condition at
# all, so the test was asserting something it had not set up. The engine
# was right and the test was wrong, which is the more common of the two.
e.evaluate("CONV001.Current_A", 45.0, at(5))
e.evaluate("CONV001.Current_A", 45.0, at(11))
check("an out-of-service alarm stays silent under a real excursion",
      e.get("CONV001.Current_A", "HI").state is State.OOS,
      "maintenance is working on the transmitter. This is correct and it is "
      "also the most dangerous state in the model")

e.return_to_service("CONV001.Current_A", "HI", "tech.okonkwo", at(600))
check("returning to service re-raises if the condition is still true",
      e.get("CONV001.Current_A", "HI").state is State.UNACK,
      "the excursion did not stop while the alarm was off. Returning to "
      "NORMAL here would lose it silently")

# ===========================================================================
# 6. Every state change is attributable
# ===========================================================================

e = build_conv001()
e.evaluate("CONV001.BearingTemp_C", 96.0, at(0))
e.acknowledge("CONV001.BearingTemp_C", "HI_HI", "operator.chen", at(10))
e.shelve("CONV001.BearingTemp_C", "HI_HI", "operator.chen", minutes=15, now=at(20))

human_events = [ev for ev in e.events if ev.to_state in (State.ACKED, State.SHELVED)]
check("every human-driven transition names an actor",
      bool(human_events) and all(ev.actor for ev in human_events),
      "after an incident the question is rarely 'did the alarm fire' — the log "
      "shows that. It is 'who shelved it, and when', and nothing answers that "
      "unless somebody designed a column for it")

check("the history keeps the transition, not just the current state",
      len(e.events) >= 3 and e.events[0].to_state is State.UNACK,
      "a table of current states cannot answer a question about the past")

# ===========================================================================
# 7. Priority ordering
# ===========================================================================

e = build_conv001()
e.evaluate("CONV001.Vibration_mms", 5.0, at(0))
e.evaluate("CONV001.Vibration_mms", 5.0, at(31))      # LOW
e.evaluate("CONV001.BearingTemp_C", 96.0, at(31))     # URGENT
top = e.active()[0]
check("the urgent alarm sorts above the low one",
      top.priority is Priority.URGENT,
      "an operator reads from the top. A list sorted by time puts a bearing "
      "about to seize underneath a vibration trend")

# ===========================================================================

fails = [r for r in results if not r[0]]
width = max(len(n) for _, n, _ in results)
print("FF-07 — alarm state model (ISA-18.2)\n")
for ok, name, why in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}")
    if not ok:
        print(f"        why this case exists: {why}")
print(f"\n{len(results)} cases, {len(fails)} failed")

if fails:
    print("\nFF-07 FAIL — the alarm surface does not behave as ISA-18.2 describes.")
    sys.exit(1)

print("""
FF-07 pass.

The alarm surface is manipulable BY DESIGN — shelve, suppress and
out-of-service all work, and all three leave a record naming who did it.
That is what makes it worth attacking at S8: an alarm system with no way
to silence an alarm is not realistic, and one that silences without a
record is not auditable.""")
