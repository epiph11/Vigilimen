# ADR-011 — The safety function is a separate controller, from Sprint 3

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré
**Related:** LIMEN-ARC-001 (safety as a driving characteristic) · **Sprint:** 3
*(The delivery plan numbered this ADR-010; that number was taken by the programme time convention. Renumbered here.)*

---

## Context

The simulated conveyor needs an emergency stop, a pull-cord and a guard interlock. The cheap implementation is a few rungs inside `PLC-CONV-001` alongside the sequencing, and on a simulated plant nobody is hurt by that choice.

**It is still the wrong choice**, because every downstream artifact — the ZCR 3 partition at S7, the CRS, the FAT hold points — assesses *this* system. A plant with no real safety separation produces an assessment with nothing to separate, and the resulting portfolio demonstrates the vocabulary rather than the practice.

---

## Decision

**Two controllers, from the first sprint the plant exists.**

| | `PLC-CONV-001` | `SIS-CONV-001` |
|---|---|---|
| Protects | The machine | People |
| Runtime | Own | **Separate** |
| I/O | Own | **Separate, dual-channel field devices** |
| Zone | Control | **Its own, from day one** |
| Network | Modbus, S7comm, OPC UA | **None. No input from anywhere** |
| Output | Run *request* | Drops the contactor coil, hardwired |

The two outputs are wired **in series** to the motor contactor:

```
motor turns  =  safety contactor energised  AND  control run request
```

That series connection is a physical property, not a line of logic in either program. The asymmetry it produces is the whole decision:

- the control function **can** stop the belt — by dropping its own request
- the control function **cannot** start the belt against a trip
- the safety function stops the belt with the control PLC **absent, powered down, disconnected, or actively commanding RUN**

---

## The rule this exists to make true

> **No security control may sit inside a protective function.**

A control that can fail closed on a safety function has made the plant less safe, not more. Security controls protecting `SIS-CONV-001` act on its **management interfaces**, on **physical access**, and on **detection** — never on the protective action.

This is the direct lesson of TRITON, where a safety instrumented system was itself the target, and it is carried unchanged into the risk criteria and into the CRS. It is a hard constraint at every layer of this programme, and ADR-011 is where the plant is built so that it can be true.

### What is deliberately absent from the safety controller

No bearing temperature, no motor current, no vibration, no overload. Those are machine protection and they live in the control PLC.

**This is a scoping decision, not an oversight.** Every demand added to a safety function is another way for it to trip spuriously — and a safety function that trips for reasons operations do not respect is one that will eventually be bypassed by people who need the plant to run. **Keeping it narrow is what keeps it trusted**, and a trusted safety function is the only kind that protects anybody.

---

## How this is enforced rather than asserted

**FF-06** (`scripts/ff06_safety_independence.py`) runs on every commit. Thirteen cases, each modelling an adversary who has already *won* on the control side — owns the PLC, forges any command, holds RUN asserted — and asking the only question that matters: *can the belt turn?*

It covers the two Sprint 3 definition-of-done cases directly: the interlock trips with the control PLC absent, and the safety function operates with the control network severed. It also covers the failures that make a safety function useless without making it look broken — a permissive cold start, auto-restart when a demand clears, a channel discrepancy treated as a vote instead of a fault.

**The check has been shown to fail.** Four mutations of the model were introduced deliberately and each was caught: a control-side inhibit, a permissive boot, auto-restart on demand-clear, and machine protection migrated into the safety function. A fitness function that has never failed is a green tick.

---

## Consequences

**Positive.** S7 has a real safety zone to partition. The TRITON constraint is demonstrable rather than quoted. The plant's own definition of done is machine-checked.

**Negative.** Two runtimes, two I/O maps, two programs to keep aligned — and **the reference model in `plant/sim/interlock_model.py` can drift from the Structured Text**, which is the real risk this decision creates. Three mitigations, honestly ranked: the two are edited in one commit (convention, unenforced); at S4 the ST runs against the same vectors; and the only thing that settles it is the witnessed test.

**What FF-06 does not prove.** That the ST matches the model, and that the *plant* is independent rather than the *logic*. Settling that means running the conveyor, de-energising the control PLC, pressing the e-stop and watching the contactor drop — which is SAT-11's shape from the hydro assessment, and no amount of Python replaces standing there while it happens.

---

*LIMEN-ADR-011 · Sprint 3*
