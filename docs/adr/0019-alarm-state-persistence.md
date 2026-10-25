# ADR-019 — Alarm state is stored in the historian, in the same transaction as its events

**Status:** Accepted — validated in Docker on 25 October 2026 (FF-26) · **Date:** 25 October 2026 · **Deciders:** E. Zaré
**Related:** ADR-010 · FF-07 · FF-25 · acceptance test 4e · **Sprint:** 4

---

## Context

The ISA-18.2 engine lived in the collector's memory. Restart the collector while an operator had **acknowledged** an alarm that was still true, and the next sample raised it again as a new `NORMAL→UNACK`: the acknowledgement was lost and one incident appeared twice in a history that is supposed to be a record.

A second defect sat beside it. `pending()` advanced its mark *before* the insert, so a failed insert lost the events permanently.

## Decision

**Persist the engine's state** (`state`, `in_condition`, `shelved_until`, `pending_since`) in a new `alarm_state` table, **written in the same transaction as the sample rows and the events that explain it**, loaded once per process at start, and saved only when it changes. The collector advances its event mark only after the commit.

- **Off by default** (`VIGILIMEN_ALARM_PERSIST`), on in `docker-compose.plcio.yml`, so the existing volume and acceptance test 4e are untouched.
- **Limits and delays are not stored.** They come from `build_conv001()`. A stored row must never override today's alarm limits.
- **Restoring emits no events.** The transitions are already in the history.
- **A missing table says how to fix itself.** `schema.sql` runs only on an *empty* volume, so an existing one needs `migrations/001_alarm_state.sql` once. The collector prints the command rather than crash-looping.
- `alarm_event` becomes **append-only in fact**: a trigger refuses UPDATE, DELETE and TRUNCATE. It had been append-only in a comment.

## Reasoning

**Why not replay `alarm_event`.** A shelf has an expiry and the on-delay has a clock; neither is a transition, and neither survives in an old event. Replay also has to stay correct across releases that change an alarm definition, and costs a start-up scan over a history that has no retention policy by design.

**Why the same transaction.** After a crash the state and its events are both there or both absent: never an `UNACK` with no raise in the history, and never a raise with no state behind it.

## Consequences

**Positive.** A restart is invisible to the record (FF-25, 19 cases, including the control case that reproduces the old bug).

**Negative.** One more table, and a migration step the schema cannot do for an existing volume. A state row can be stale if the collector dies between two commits; that costs at most one sample's worth of state, never a lost event.

**The trigger is not a security control.** The table owner, which is the collector's own role, can drop it. It stops an accidental `UPDATE` and a careless `DELETE`. Separate roles to write and to administer are an S8 item.

**Proven in Docker, 25 October.** The migration applied, a collector restart in the middle of an alarm raised the incident once (`alarm_state` still held it), and the trigger refused an `UPDATE` on `alarm_event`. Not exercised: `DELETE`, `TRUNCATE` (deliberately: a missing trigger would destroy the history), and a restart while an alarm is `SHELVED`.

---

*VIGILIMEN-ADR-019 · Sprint 4*
