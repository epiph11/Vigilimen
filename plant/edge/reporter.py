"""What the edge publishes, and when (ADR-020 point 5; values: docs/sprints/S5-cadrage.md, Q3).

The gateway side is read at 1 Hz. For each tag the reporter answers one question per sample: publish it, and as what?

  baseline    a periodic repeat (one value per tag every 10 s): it keeps the stream alive and bounds the replay
  exception   a change that must not wait: the value moved by at least the tag's deadband since it was last
              PUBLISHED, it crossed an alarm threshold, its quality changed, or (booleans) it changed at all
  None        nothing to say

The first sample of a tag is published at once. An unknown tag is an error, not silence: a tag that is missing from
the table would otherwise vanish from the stream without anyone noticing.

Deadbands and thresholds are the alarm engine's own numbers (plant/alarms/engine.py), the author's and the
simulator's, NOT a process engineer's: the M1 report must say so. Known limit: there is no hysteresis, so a value
that oscillates around a threshold publishes at every crossing (at most one message per second per tag).
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

BASELINE_S = 10.0


@dataclass(frozen=True)
class Spec:
    deadband: float | None                  # None: a boolean, any change is an exception
    thresholds: tuple[float, ...] = ()


TAGS: dict[str, Spec] = {
    "BearingTemp_C": Spec(2.0, (85.0, 95.0)),
    "Vibration_mms": Spec(0.3, (4.5, 7.1)),
    "Current_A": Spec(1.0, (38.0, 42.0)),
    "Speed_mps": Spec(0.1, (0.1, 2.0)),
    "Load_tph": Spec(36.0, (950.0, 1100.0)),
    "Running": Spec(None),
    "SafetyTripped": Spec(None),
}


class UnknownTag(KeyError):
    pass


class Reporter:
    def __init__(self, tags: dict[str, Spec] | None = None, baseline_s: float = BASELINE_S):
        self.tags = TAGS if tags is None else tags
        self.baseline_s = baseline_s
        self._last: dict[str, tuple] = {}        # tag -> (value, time, quality, zone) AT THE LAST PUBLICATION

    # -- hooks FF-39 can break on purpose -----------------------------------------------------------------
    def _spec(self, tag: str) -> Spec:
        try:
            return self.tags[tag]
        except KeyError:
            raise UnknownTag(f"{tag!r} is not in the reporter's table: add it (with a deadband) or remove it from the read list")

    def _beyond(self, delta: float, deadband: float) -> bool:
        return delta >= deadband

    def _zone(self, spec: Spec, value) -> int | None:
        return None if value is None or spec.deadband is None else bisect_right(spec.thresholds, value)

    def _quality_changed(self, quality: int, last_quality: int) -> bool:
        return quality != last_quality

    def _baseline_due(self, now: float, last_time: float) -> bool:
        return now - last_time >= self.baseline_s

    # -- API ----------------------------------------------------------------------------------------------
    def decide(self, tag: str, value, quality: int, now: float) -> str | None:
        spec = self._spec(tag)
        zone = self._zone(spec, value)
        last = self._last.get(tag)
        kind = self._kind(spec, last, value, quality, zone, now)
        if kind is not None:
            self._last[tag] = (value, now, quality, zone)
        return kind

    def _kind(self, spec, last, value, quality, zone, now):
        if last is None:
            return "baseline"
        l_value, l_time, l_quality, l_zone = last
        if self._quality_changed(quality, l_quality):
            return "exception"
        if spec.deadband is None:
            if value != l_value:
                return "exception"
        elif value is not None and l_value is not None:
            if self._beyond(abs(value - l_value), spec.deadband) or zone != l_zone:
                return "exception"
        if self._baseline_due(now, l_time):
            return "baseline"
        return None
