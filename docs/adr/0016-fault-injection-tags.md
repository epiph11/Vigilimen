# ADR-016 — Fault injection is part of the gateway's address space

**Status:** Accepted · **Date:** 25 October 2026 · **Deciders:** E. Zaré
**Related:** ADR-003 · ADR-017 (accounts) · acceptance test 4e · **Sprint:** 4

---

## Context

Acceptance test 4e says a vibration spike must raise an alarm within 2 seconds. A simulator that only ever produces healthy values cannot be asked to spike. S8 needs a baseline an attacker can be shown to have altered, and S13 needs a degradation signal. All three want values that can be pushed on demand.

## Decision

**Five writable tags on the gateway** (`FaultBearingWear`, `FaultBeltSlip`, `FaultMisalignment`, `FaultIdlerSeizure`, `FaultVibrationSpike`, node ids `ns=2;i=15..19`), read by the plant cycle and fed to the physics.

- **Appended, never inserted.** asyncua numbers nodes in creation order and FUXA binds `ns=2;i=N`. Inserting earlier would silently re-point every binding.
- **Clamped.** Bearing, slip, misalignment and seizure to 0..1, the spike to 0..10 mm/s; NaN and non-numbers become 0. A bad write cannot produce NaN physics.
- **A stimulus, not a failure mode.** The spike moves vibration and nothing physically coupled to it, so it tests the alarm path without pretending a bearing failed.

## Reasoning

**Why in the gateway and not a side channel.** The injection must pass through the same OPC UA path an operator or attacker uses, or 4e proves nothing about the path. A test hook that bypasses it would be a second implementation of the thing under test.

**Why FF-26 and not just a unit test.** The 25 October trap was an image built before these tags existed: FUXA showed them with no value and the buttons did nothing. Only a run against the *built* image notices that.

## Consequences

**Positive.** 4e is reproducible and timed. The same five tags drive S8 and S13.

**Negative, and a finding.** These are plant-model inputs in a namespace that otherwise models a plant. A real server would not have them. Worse, **any authenticated session can write them, including `historian`** (ADR-017), and **nothing records who wrote one**: a falsified fault is indistinguishable from an injected one by design. That is the S24 detection problem in miniature, so it is recorded here and not fixed.

**Reaching machine protection.** Slip plus a seized idler push current over 42 A, so the PLC trips on overload (FF-24 asserts it). The 95 °C trip is hard to provoke: in the physics, full bearing wear alone levels off near 85 °C, and 95 °C needs wear **and** a seized idler, then about 50 minutes of simulated running (measured), during which the overload trip can fire first. FF-24 therefore tests the 95 °C trip by setting the temperature directly. That is a property of the model, not of the program.

**Revisit when:** S8 needs the writes attributed, or a `VIGILIMEN_FAULT_INJECTION=off` switch is wanted for a run that must be unfalsifiable.

---

*VIGILIMEN-ADR-016 · Sprint 4*
