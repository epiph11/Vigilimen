# ADR-005 — The OT boundary is unidirectional by default

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré

---

## Context

The industrial data plane needs plant telemetry in the cloud. The enterprise plane will eventually want to send something back — a schedule, a setpoint, a work order acknowledgement. The moment it does, the boundary becomes bidirectional, and every argument for segmentation weakens.

This decision is taken **at inception rather than when the first write request appears**, because by then there will be a delivery date attached to it.

---

## Decision

**Data flows OT → IT. Control does not flow IT → OT.**

The arrow on the C4 Level-1 context diagram is drawn one-way and labelled, and it stays that way unless this ADR is superseded by a decision that names what changed.

Where a genuine write path is later required, it is subject to four conditions, all of them:

1. It is a **conduit in the 62443 sense**, registered, with its own target security level, and it appears in the conduit register — an unregistered path is a defect regardless of whether it is exploitable
2. It terminates in the **DMZ**, never into a control zone
3. The receiving controller **validates the command at the receiving end** rather than trusting the sender, and enforces an allow-list of writable tags **in the controller**, not in the HMI's tag database
4. It **cannot reach a protective function**, by design rather than by configuration

---

## Reasoning

**Colonial Pipeline is the business-continuity argument.** The OT was not compromised; the IT was, and the operator shut the pipeline down anyway because it could not establish what the boundary had let through. A boundary you cannot reason about becomes a boundary you shut down.

**The technical argument is that industrial protocols have no authentication.** Modbus and DNP3 without Secure Authentication have none at all — anyone who can reach the port can write. OPC UA is the outlier. In FR terms the segmentation *is* the authentication, which is why FR5 restricted data flow carries so much weight in OT and so little in enterprise IT.

**The architectural argument is that a default decides the next fifty decisions.** Once a bidirectional path exists, every subsequent "we just need one more field" is an incremental request against an established pattern. One-way by default means each write is a decision with a named owner, which is the outcome the four conditions above are really for.

---

## Consequences

**Positive.** The boundary is reasonable about. Scheduling and work management consume plant state without authority over it. The conduit register stays meaningful because there is a default to deviate *from*.

**Negative.** Some features become harder. Remote setpoint adjustment from the enterprise plane is not available, and closed-loop optimisation — the kind an ML model would want — cannot actuate. **That is a real capability cost and it is accepted deliberately**, not worked around.

**What this costs at S19–S21.** The machine learning plane advises; it does not act. A predictive maintenance model raises a work order, and a person decides. That is a weaker demo and a better architecture, and where the two conflict the architecture wins.

---

*VIGILIMEN-ADR-005 · Sprint 0 · Gate M0*
