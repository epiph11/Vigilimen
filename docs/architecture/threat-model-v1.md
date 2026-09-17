# STRIDE Threat Model v1

**Ref:** VIGILIMEN-ARC-004 · **Rev:** 1.0 · **Date:** 14 September 2026 (AEST)
**Scope:** the C4 Level-1 context, VIGILIMEN-ARC-002 · **Sprint:** 2

---

## 1. What this model is, and what it is not

STRIDE is applied to the **Level-1 context** — the trust boundaries between the system, its people, the plant and the external parties. It is deliberately coarse. A Level-1 model that tries to enumerate component vulnerabilities produces a hundred rows nobody reads and misses the two boundaries that matter.

**This is not the 62443 risk assessment.** That is ZCR 1–7, it works from consequence rather than from threat category, and it produces target security levels. The two answer different questions and both are needed:

| | Question | Output |
|---|---|---|
| **STRIDE here** | What could an adversary *do* at each trust boundary? | A threat list with mitigations |
| **62443-3-2 at S7** | What is the *consequence* if they succeed, and what capability must we withstand? | Zones, conduits, SL-T, a CRS |

STRIDE finds the threat; 62443 decides what it is worth spending to stop. Running STRIDE alone produces a list with no priority, which is the failure mode of most threat models.

---

## 2. Trust boundaries in scope

Four, taken straight off the context drawing. A boundary that is not on the drawing is not modelled, and that is a statement about the drawing rather than about the system.

| # | Boundary | Direction permitted |
|---|---|---|
| **TB-1** | Plant OT ↔ Vigilimen | **Data up only.** No control path down (ADR-005) |
| **TB-2** | Vendor OEMs ↔ Plant OT | Brokered session, one asset, one protocol |
| **TB-3** | Corporate identity ↔ Vigilimen | Authentication assertions in |
| **TB-4** | Between the three cloud planes | Data forward through defined integrations |

---

## 3. The model

**S**poofing · **T**ampering · **R**epudiation · **I**nformation disclosure · **D**enial of service · **E**levation of privilege

### TB-1 — Plant OT ↔ Vigilimen

| | Threat | Mitigation | Carried to |
|---|---|---|---|
| **S** | A rogue device publishes telemetry as CONV-001 | Per-device certificate; the IoT policy scopes `Connect` to this client id and `Publish` to this device's topic only | S12 |
| **T** | Telemetry altered in transit, so condition-based maintenance acts on false state | TLS on the ingest path; sequence and timestamp continuity checked at ingest — **a gap in a time series is a signal, not an absence** | S12, S13 |
| **R** | A setpoint change cannot be attributed | Out of scope at TB-1 **by construction**: no setpoint change crosses this boundary (ADR-005) |  |
| **I** | Process data reveals production rates, outage windows and plant layout | Landing bucket private and encrypted; access by named role. Treated as commercially sensitive rather than as telemetry | S12 |
| **D** | Telemetry flood exhausts ingest quota or budget | Per-device publish rate limit; ingest quota alarmed. **The budget is the denial-of-service surface here**, not the compute | S12, FF-13 |
| **E** | Compromised ingest role reaches other cloud resources | Ingest role scoped to one bucket and one action. No `iam:*`, no wildcard resource | S12 |

> **The strongest control on this boundary is the absence of a return path.** Half of what STRIDE would normally find here — command spoofing, command tampering, command repudiation — simply does not arise, because the device cannot subscribe and the boundary carries no control. That is ADR-005 paying for itself, and it is why the decision was taken at inception rather than when the first write request appeared.

### TB-2 — Vendor OEMs ↔ Plant OT

**The highest-consequence boundary in the system.** In the worked hydro assessment its equivalent, conduit C-09, is the highest-consequence conduit in the plant, because its consequence is the maximum of everything it can reach.

| | Threat | Mitigation | Carried to |
|---|---|---|---|
| **S** | A shared vendor credential is used by someone other than the named engineer | Per-individual named accounts; phishing-resistant MFA with no fallback path | S5, S10 |
| **T** | Controller logic modified during a support session | Golden-copy comparison before and after every session; logic download hashed and logged | S5, S9 |
| **R** | The vendor denies making a change | **Full session recording, stored outside the DMZ and not deletable by the recorded party** | S5 |
| **I** | Vendor tooling exfiltrates configuration for reuse elsewhere | Session scoped to one asset and one protocol; no file transfer path out | S5 |
| **D** | A vendor session is opened during a production-critical window | Just-in-time approval with an operator in the loop; time-boxed with auto-revocation | S5 |
| **E** | Session pivots to a second asset or to network-layer access | **No network-layer route exists from the session.** This is the control; everything else is detection | S5 |

> **This is the Oldsmar shape.** Shared credentials on a remote access tool, no session recording, no approval step. The failure there was architectural, not technical — which is why five of the six mitigations above are contractual or procedural rather than products.

### TB-3 — Corporate identity ↔ Vigilimen

| | Threat | Mitigation | Carried to |
|---|---|---|---|
| **S** | Forged SAML assertion grants cloud access | Signature validation; assertion issuer and audience pinned; clock skew bounded | S2 |
| **T** | Group membership altered to grant privilege | Privileged group changes alarmed; **eligible-not-standing roles**, so membership alone grants nothing | S2, ADR-008 |
| **R** | A privileged action cannot be tied to a person | Entra sign-in and audit logs centralised; every cloud role assumption traces to an Entra identity | S2 |
| **I** | Directory enumeration reveals the organisation's shape | Not a primary concern at this scale; noted rather than mitigated |  |
| **D** | Entra outage locks all three clouds simultaneously | **Accepted, with break-glass.** ADR-008 records this as the cost of a single authority | ADR-008 |
| **E** | Break-glass account abused | Excluded from conditional access by necessity, therefore **alerted on every single use with no threshold**, stored offline | S2 |

### TB-4 — Between the cloud planes

| | Threat | Mitigation | Carried to |
|---|---|---|---|
| **S** | One plane impersonates another to the third | Workload identity per plane; no shared service principal | S18 |
| **T** | Work order altered between Azure and the historian | Integration messages signed or transported over an authenticated channel; idempotency keys | S18 |
| **R** | An automated action has no originator | Every automated action carries the workflow run id that produced it — the evidence record already establishes this pattern | S18 |
| **I** | Analytics copy carries data whose sensitivity was set in another plane | Classification travels with the data rather than with the store | S20 |
| **D** | A retry storm between planes exhausts a quota | Backoff, dead-letter, and a quota alarm. **BigQuery custom quota is set on day one at S20**, not after the first bill |  S20 |
| **E** | A cross-plane role is broader than its one integration needs | One role per integration; FF-14 checks federation scope statically |  FF-14 |

---

## 4. What this model refuses to do

**It does not rate likelihood.** Likelihood belongs to the 62443 detailed assessment at ZCR 5, where it is threat-informed and anchored against attacker capability. Assigning a number here would produce a second, competing risk register — and two registers that disagree is worse than one that is incomplete.

**It does not cover Levels 0–2 internals.** The C4 Level-1 boundary stops at the plant. Inside it is the 62443 partition's job, and duplicating that here would create two descriptions of the same system that drift apart at the first change.

**It does not treat confidentiality as the lead.** Information disclosure appears in every row and leads none of them, which is the OT ordering: safety, then availability, then integrity, then confidentiality. **The inversion from IT is structural rather than attitudinal** — a stopped plant is a safety event during restart, and a disclosed production figure is a bad afternoon.

---

## 5. Review

Re-run at **M1**, when the OT world exists and TB-1 and TB-2 stop being drawings; and at **M3**, against the completed 62443 assessment, to check that the two models still agree about which boundary matters most. **If they disagree, one of them is wrong and the disagreement is the finding.**

---

*VIGILIMEN-ARC-004 rev 1.0 · Sprint 2*
