# ADR-010 — Machine time is UTC. Human time is Australia/Brisbane.

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré
**Related:** ADR-004 (evidence windows), ADR-001 (three clouds)
*(ADR-008 and ADR-009 are reserved for Sprint 2 — identity authority and compliance framework selection.)*

---

## Context

A programme spanning three clouds, a simulated plant, a CI pipeline and a roster cadence produces timestamps from a dozen places. Left unstated, each source picks its own zone, and the first time anyone correlates a plant alarm against a CI run they discover the two are an hour apart — and cannot tell whether that is a clock problem, a timezone problem, or a real delay.

Australia makes this worse than most places. **New South Wales, Victoria, South Australia and Tasmania observe daylight saving; Queensland, Western Australia and the Northern Territory do not.** A national operator therefore has sites whose offset relationship to each other *changes twice a year*.

---

## Decision

**Two rules, and the separation between them is the decision.**

1. **Everything a machine writes is UTC**, ISO 8601, with an explicit `Z`. Log lines, evidence records, database columns, filenames, cron schedules, Terraform state.
2. **Everything a human reads is rendered in `Australia/Brisbane`**, labelled `AEST`. Dashboards, reports, the programme tracker, alarm displays, the cadence calendar.

Conversion happens at the presentation layer and nowhere else. **No stored value is ever in local time.**

---

## Why Brisbane rather than Sydney

Brisbane is **AEST, UTC+10, all year. It has no daylight saving.**

That is the whole argument, and it is an engineering argument rather than a geographic one:

- **A cron schedule written in a DST zone silently moves twice a year.** A job set for 02:30 either runs twice or not at all on the changeover night, and a job near midnight crosses a date boundary — so a "daily" report quietly covers 23 hours, then 25. In Brisbane, the offset is a constant, and a schedule means the same thing in June as in December.
- **Offsets that never move are offsets nobody has to reason about.** UTC+10 with no exceptions is a rule a reader can apply in their head at 3 a.m. during an incident, which is exactly when timestamp arithmetic goes wrong.
- **The plant does not observe daylight saving either.** Process historians, PLC clocks and protection relays are conventionally run on a fixed offset or on UTC precisely because a one-hour jump in a time series is indistinguishable from an hour of missing data. Aligning the programme's display zone with a fixed-offset zone removes a class of reconciliation problem at the boundary.

**Sydney was the alternative and it loses on the third point alone.** A control-room display on AEDT against a historian on a fixed offset produces a one-hour discrepancy for five months of the year, and someone rediscovers it every October.

---

## Why not UTC for humans too

It is the tidier answer and it is rejected for one reason: **people do not operate a plant in UTC.** A shift starts at 06:00 because that is when people arrive, and a report that says a conveyor tripped at 20:14Z requires every reader to do arithmetic before they can picture the shift it happened on. Arithmetic under pressure is where errors come from.

---

## Consequences

**Region is not timezone, and this ADR does not move any region.** The clouds stay at `ap-southeast-2`, `australiaeast` and `australia-southeast1` — all Sydney — because region is chosen for latency, service availability and data residency, and none of those has anything to do with what a clock displays. **Conflating the two is the most common way this decision gets reversed by accident**, so it is written here explicitly.

**Every rendering layer needs the conversion.** `TZ=Australia/Brisbane` in the display path, an explicit zone in every chart axis, and `AEST` in the label — a bare "14:32" with no zone is the bug this ADR exists to prevent.

**Evidence records carry both.** The workflow writes UTC as the value and Brisbane as the reading, on the same line, because an evidence record is read by a person and audited by a machine.

**Accepted cost.** Readers in Sydney or Melbourne are an hour out from the programme's display zone for five months of the year. That is a real inconvenience, and it is smaller than the alternative, because it is *visible* — a label that says AEST when the reader is on AEDT prompts the conversion, whereas a floating offset does not prompt anything at all.

---

*LIMEN-ADR-010 · Sprint 1*
