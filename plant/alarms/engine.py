#!/usr/bin/env python3
"""
Alarm state model for CONV-001, following ISA-18.2.

WHY A STATE MACHINE AND NOT A BOOLEAN
-------------------------------------
"Is the alarm on" is the wrong question, and building on it produces the
alarm system every operator has learned to ignore. The real questions are
whether anyone has SEEN it, whether it has CLEARED, and whether someone
made it stop showing — and those are three different things that a boolean
cannot hold.

The state that matters most is RTN_UNACK: the condition has returned to
normal, and nobody ever acknowledged it. A boolean alarm erases that
transition entirely. It is also, routinely, the most interesting line in a
post-incident review — the plant told somebody, and the record shows nobody
was there.

STATES
    NORMAL        no condition, nothing outstanding
    UNACK         in alarm, not acknowledged
    ACKED         in alarm, acknowledged — still a problem
    RTN_UNACK     returned to normal, never acknowledged
    SHELVED       operator hid it temporarily. Expires by itself.
    SUPPRESSED    design hid it — a known consequence of another alarm
    OOS           out of service. Maintenance, and it does not come back alone.

Verified by scripts/ff07_alarm_state_model.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class State(str, Enum):
    NORMAL = "NORMAL"
    UNACK = "UNACK"
    ACKED = "ACKED"
    RTN_UNACK = "RTN_UNACK"
    SHELVED = "SHELVED"
    SUPPRESSED = "SUPPRESSED"
    OOS = "OOS"


class Priority(int, Enum):
    """ISA-18.2 wants priority to reflect CONSEQUENCE and TIME TO RESPOND.

    Four levels, not ten. A scale with ten levels is a scale on which
    everything becomes a 3, because nobody can defend the difference
    between 4 and 5 at two in the morning.
    """
    DIAGNOSTIC = 1     # tell the engineer, not the operator
    LOW = 2            # act this shift
    HIGH = 3           # act now
    URGENT = 4         # act now, and the consequence is safety or environment


def utcnow() -> datetime:
    """UTC. Always. Rendering to Brisbane is a presentation concern (ADR-010)."""
    return datetime.now(timezone.utc)


@dataclass
class Event:
    ts: datetime
    tag_id: str
    condition: str
    from_state: State
    to_state: State
    priority: Priority
    actor: str | None = None
    note: str | None = None


@dataclass
class Alarm:
    """One condition on one tag. A tag with HI and HI_HI has two of these."""

    tag_id: str
    condition: str                 # HI_HI · HI · LO · LO_LO · DISCREPANCY
    limit: float | None
    priority: Priority
    deadband: float = 0.0
    on_delay_s: float = 0.0

    state: State = State.NORMAL
    in_condition: bool = False
    shelved_until: datetime | None = None
    _pending_since: datetime | None = None

    def _compare(self, value: float) -> bool:
        if self.limit is None:
            return False
        if self.condition.startswith("HI"):
            # Deband applies on the way OUT only. Symmetric deadband delays
            # the alarm as well as the clear, which delays the operator.
            return value >= self.limit if not self.in_condition else value >= self.limit - self.deadband
        return value <= self.limit if not self.in_condition else value <= self.limit + self.deadband


# ---------------------------------------------------------------------------

@dataclass
class AlarmEngine:
    alarms: dict[tuple[str, str], Alarm] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)

    # ---- registration ----------------------------------------------------

    def add(self, a: Alarm) -> Alarm:
        self.alarms[(a.tag_id, a.condition)] = a
        return a

    def get(self, tag_id: str, condition: str) -> Alarm:
        return self.alarms[(tag_id, condition)]

    def _emit(self, a: Alarm, frm: State, to: State,
              actor: str | None = None, note: str | None = None,
              now: datetime | None = None) -> None:
        if frm == to:
            return
        a.state = to
        self.events.append(Event(now or utcnow(), a.tag_id, a.condition,
                                 frm, to, a.priority, actor, note))

    # ---- the process drives this ------------------------------------------

    def evaluate(self, tag_id: str, value: float, now: datetime | None = None) -> None:
        now = now or utcnow()
        for (t, _), a in self.alarms.items():
            if t != tag_id:
                continue
            self._evaluate_one(a, value, now)

    def _evaluate_one(self, a: Alarm, value: float, now: datetime) -> None:
        raw = a._compare(value)

        # On-delay. A transient excursion is not an alarm — it is noise, and
        # sending it to an operator is how a console reaches 200 alarms an
        # hour and stops being read.
        if raw and not a.in_condition:
            if a.on_delay_s:
                if a._pending_since is None:
                    a._pending_since = now
                if (now - a._pending_since).total_seconds() < a.on_delay_s:
                    return
            a._pending_since = None
            a.in_condition = True
            self._on_condition_start(a, now)
            return

        if not raw:
            a._pending_since = None
            if a.in_condition:
                a.in_condition = False
                self._on_condition_clear(a, now)

    def _on_condition_start(self, a: Alarm, now: datetime) -> None:
        if a.state in (State.SUPPRESSED, State.OOS):
            return                                   # by design. No event.
        if a.state is State.SHELVED:
            if a.shelved_until and now < a.shelved_until:
                return
            self._emit(a, State.SHELVED, State.NORMAL, note="shelf expired", now=now)
        self._emit(a, a.state, State.UNACK, now=now)

    def _on_condition_clear(self, a: Alarm, now: datetime) -> None:
        if a.state in (State.SUPPRESSED, State.OOS, State.SHELVED):
            return
        if a.state is State.UNACK:
            # THE TRANSITION THAT MATTERS. It cleared and nobody ever saw it.
            self._emit(a, State.UNACK, State.RTN_UNACK, now=now)
        elif a.state is State.ACKED:
            self._emit(a, State.ACKED, State.NORMAL, now=now)

    # ---- an operator drives these -----------------------------------------

    def acknowledge(self, tag_id: str, condition: str, actor: str,
                    now: datetime | None = None) -> None:
        a = self.get(tag_id, condition)
        now = now or utcnow()
        if a.state is State.UNACK:
            self._emit(a, State.UNACK, State.ACKED, actor=actor, now=now)
        elif a.state is State.RTN_UNACK:
            self._emit(a, State.RTN_UNACK, State.NORMAL, actor=actor, now=now)
        # Acknowledging a NORMAL alarm is a no-op, not an error. Operators
        # press acknowledge-all; refusing it would train them to ignore
        # errors from the alarm system itself.

    def shelve(self, tag_id: str, condition: str, actor: str,
               minutes: int, now: datetime | None = None) -> None:
        """Hide an alarm temporarily. ALWAYS with an expiry.

        Unlimited shelving is suppression wearing an operator's name, and it
        is how a plant arrives at an alarm that has been off for four years
        with nobody able to say who turned it off or why.
        """
        if minutes <= 0 or minutes > 8 * 60:
            raise ValueError("shelve duration must be 1..480 minutes — "
                             "an unbounded shelf is suppression without the paperwork")
        a = self.get(tag_id, condition)
        now = now or utcnow()
        a.shelved_until = now + timedelta(minutes=minutes)
        self._emit(a, a.state, State.SHELVED, actor=actor,
                   note=f"{minutes} min", now=now)

    def unshelve_expired(self, now: datetime | None = None) -> None:
        now = now or utcnow()
        for a in self.alarms.values():
            if a.state is State.SHELVED and a.shelved_until and now >= a.shelved_until:
                self._emit(a, State.SHELVED, State.UNACK if a.in_condition else State.NORMAL,
                           note="shelf expired", now=now)
                a.shelved_until = None

    def suppress(self, tag_id: str, condition: str, reason: str,
                 now: datetime | None = None) -> None:
        """Hide by DESIGN, not by an operator.

        The legitimate case is a known consequence: the belt stopped, so
        every downstream low-flow alarm is arithmetic rather than news.
        Suppression must name the cause, which is why `reason` is required
        and is written into the history.
        """
        a = self.get(tag_id, condition)
        self._emit(a, a.state, State.SUPPRESSED, note=reason, now=now)

    def out_of_service(self, tag_id: str, condition: str, actor: str,
                       now: datetime | None = None) -> None:
        a = self.get(tag_id, condition)
        self._emit(a, a.state, State.OOS, actor=actor, now=now)

    def return_to_service(self, tag_id: str, condition: str, actor: str,
                          now: datetime | None = None) -> None:
        a = self.get(tag_id, condition)
        self._emit(a, a.state, State.UNACK if a.in_condition else State.NORMAL,
                   actor=actor, now=now)

    # ---- what the operator sees -------------------------------------------

    def active(self) -> list[Alarm]:
        """Highest priority first, and SHELVED / SUPPRESSED / OOS excluded.

        Excluded from the LIST, never from the HISTORY. An alarm nobody can
        see must still be an alarm somebody can audit.
        """
        visible = [a for a in self.alarms.values()
                   if a.state in (State.UNACK, State.ACKED, State.RTN_UNACK)]
        return sorted(visible, key=lambda a: (-a.priority, a.state is not State.UNACK))

    def hidden(self) -> list[Alarm]:
        """Everything a human decided, or a design decided, not to show.

        This list is the one worth reviewing weekly. It is where an alarm
        goes to be forgotten.
        """
        return [a for a in self.alarms.values()
                if a.state in (State.SHELVED, State.SUPPRESSED, State.OOS)]


# ---------------------------------------------------------------------------

def build_conv001() -> AlarmEngine:
    """CONV-001's alarm set. Limits match plant/historian/schema.sql."""
    e = AlarmEngine()
    e.add(Alarm("CONV001.BearingTemp_C", "HI",    85.0, Priority.HIGH,   deadband=2.0, on_delay_s=10))
    e.add(Alarm("CONV001.BearingTemp_C", "HI_HI", 95.0, Priority.URGENT, deadband=2.0))
    e.add(Alarm("CONV001.Vibration_mms", "HI",     4.5, Priority.LOW,    deadband=0.3, on_delay_s=30))
    e.add(Alarm("CONV001.Vibration_mms", "HI_HI",  7.1, Priority.HIGH,   deadband=0.3, on_delay_s=5))
    e.add(Alarm("CONV001.Current_A",     "HI",    38.0, Priority.LOW,    deadband=1.0, on_delay_s=5))
    e.add(Alarm("CONV001.Current_A",     "HI_HI", 42.0, Priority.HIGH,   deadband=1.0))
    e.add(Alarm("CONV001.Speed_mps",     "LO",     2.0, Priority.LOW,    deadband=0.1, on_delay_s=15))
    e.add(Alarm("CONV001.Speed_mps",     "LO_LO",  0.1, Priority.HIGH,   deadband=0.05))
    return e
