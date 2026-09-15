# Asset Owner Approval Record

**Kanangra Creek Hydro Station — 20 MW run-of-river generating station**
**Document:** 12 of 12 · **ZCR 7** · **Ref:** KCH-CYB-APP-001 · **Revision:** 0.1 — DRAFT
**Date:** 14 September 2026 · **Assessor:** Epiphane Zaré
**Status:** Unsigned

> ⚠ **Fictional facility.** Kanangra Creek is a worked example modelled on a real small run-of-river architecture. It describes no actual asset.

---

## 1. What ZCR 7 is for

ZCR 7 is the step where the assessment stops being the assessor's and becomes the **asset owner's**.

That is not a formality. Everything before this document is method: a consultant can partition a system, rate consequence, score likelihood and write requirements without ever holding accountability for any of it. Only the asset owner can say *this is the risk we carry, and this is what we will spend to carry less of it*. An assessment that is never signed is an opinion in a folder.

Three things happen here and nowhere else:

| | What it establishes |
|---|---|
| **Acceptance** | Residual risk is formally carried, at the authority level the tolerable risk criteria require |
| **Ownership** | The assumptions become the owner's to verify, not the assessor's to caveat |
| **Mandate** | The CRS becomes issuable — a tender document rather than a draft |

**Approval is not agreement that the plant is secure.** It is agreement that the risk is now described accurately enough to act on, and that the described treatment is what the organisation intends to do.

---

## 2. The documents being approved

| # | Document | Rev | Approved as |
|---|---|---|---|
| 01 | System under Consideration | 0.1 | Scope and boundary statement |
| 02 | Initial risk assessment | 0.1 | Consequence scenarios S-01…S-10 |
| 03 | Zone and conduit partition | 0.2 | The partition — 9 zones, 13 conduits, SL-T per element |
| 04 | Tolerable risk criteria | **0.2** | **The organisation's risk appetite.** See §4 |
| 05 | Detailed risk assessment | 0.2 | 40 risks, residual bands, SL gap, attack path, priority score |
| 06 | Zone and conduit drawing KCH-CYB-ZC-001 | 0.2 | The controlled drawing |
| 10 | Cybersecurity Requirements Specification KCH-CYB-CRS-001 | 0.2 | **The contractual deliverable.** Annexures A–D consolidate documents 07, 08, 09 and 11 |

Documents 07, 08, 09 and 11 are not issued separately and are approved in their consolidated form as Annexures A to D of document 10.

---

## 3. Assessment decisions requiring ratification

Five judgements were made during the assessment that change the result. Each is defensible and each has a defensible alternative. **Approving this record ratifies them; declining any one of them reopens the work it governs.**

### D-1 · Consequence is rated at what a risk directly achieves

Seven risks originally inherited safety consequence 5 from what they *enabled* rather than what they *achieved*. Six were renoted to their direct consequence, and the escalation chains moved to the attack-path sheet of document 05.

**Effect:** the Extreme band fell from 17 to 11. **Alternative:** rate enablers at inherited consequence, and let the ordering of the treatment plan carry the prioritisation instead. Both are practised. *What is not defensible is doing either without saying which.*

**Reopens if declined:** documents 05 and 10, and the acceptance schedule in §5.

### D-2 · Z-05 is split

Z-05 was rated SL-T 3 because of one asset. It is now **Z-05a Engineering (SL-T 3)** and **Z-05b Plant information (SL-T 2)**, joined by conduit C-13.

**Effect:** Z-05b's SL gap closes to zero by separation alone — at no capital cost. **Alternative:** keep one zone and accept that the historian carries a target it has not earned.

**Reopens if declined:** documents 03, 05, 06 and 10 §4.5.

### D-3 · The life-safety override is widened

The override in document 04 §5 was written against the *Safety category*. The environment-5 band in the same document describes uncontrolled water release affecting third parties, which is a drowning mechanism. Five intake risks sat outside an override plainly meant to catch them.

**Effect:** the override population rises from 11 to 16 risks. **Alternative:** none that is defensible — this was a drafting error, not a judgement.

**Note for the record:** it was found by the priority scoring, not by review. The general lesson is worth carrying into the owner's other assessments: *an override written against a category name rather than against a mechanism will miss it.*

### D-4 · Nothing is rated SL-T 4

SL 4 implies extended resources directed at *this* asset. A 20 MW station that is not systemically significant does not obviously attract that, and **an SL-T that cannot be funded is worse than an honest SL-T 3** — it produces a paper requirement instead of a control.

**Alternative:** the contrary argument is real and set out in document 03 §5 — TRITON demonstrated nation-state interest in safety systems. **If the asset owner's own threat assessment says otherwise, this changes and the CRS changes with it.** This is a threat-appetite question, and it belongs to the owner.

### D-5 · SOCI applicability is a test, not an assertion

A generation asset is a *critical electricity asset* where it is connected to a wholesale market and either has an installed capacity of at least **30 MW** or its operator holds a **system restart ancillary services** contract. Kanangra Creek is 20 MW and does not cross that threshold on its own.

CIRMP obligations reach this station only via routes D-1 to D-3 of Annexure D §13.1, **which only the asset owner can answer.**

**If the answer is that the station sits outside the regime, this specification does not weaken.** Every requirement derives from consequence, not from statute. What changes is the enforcement route: contractual rather than regulatory.

---

## 4. Ratification of the tolerable risk criteria

Document 04 was approved before ZCR 5 began, as the standard requires — criteria agreed after an assessment drift toward wherever the findings happen to land. It has since moved to rev 0.2 under decision D-3.

**Re-confirm at signature:**

1. The financial bands in §2 match the operator's materiality thresholds
2. The acceptance authorities in §5 match the operator's delegation framework
3. The two overriding constraints in §5 are accepted as written, **including the widened life-safety override**
4. The scale is compatible with the enterprise risk framework (assumption T-04)

> **T-04 carries more weight than it looks.** A cyber risk assessment on a bespoke scale cannot be aggregated into the enterprise risk register, which means it cannot reach the board, which means Extreme risks have no route to the only authority permitted to accept them. **Align the scale or the governance path breaks**, and an unaligned assessment produces signatures that are not valid ones.

---

## 5. Residual risk acceptance schedule

Profile after existing countermeasures, against the rev 0.2 criteria:

| Band | Count | Share | Acceptance authority | Timeframe |
|---|---|---|---|---|
| **Extreme** | **11** | 28% | **Board or equivalent** — *cannot* be accepted at site or asset-manager level | Interim control 30 days; treatment plan 90 days |
| **High** | 28 | 70% | Asset owner executive | Treatment within 12 months |
| **Medium** | 1 | 2% | Asset manager | Reviewed annually |
| **Low** | 0 | — | — | — |

**Sixteen risks carry the life-safety override** and are treated regardless of band: R-01, R-02, R-03, R-04, R-05, R-06, R-19, R-21, R-22, R-23, R-24, R-25, R-28, R-31, R-32, R-33.

### 5.1 The Extreme risks, individually

These require board-level acceptance and cannot be delegated. Ordered by priority score — consequence × residual likelihood — which is what the treatment plan is sequenced on.

| Rank | Risk | Where | Score | What it is |
|---|---|---|---|---|
| 1 | **R-22** | Z-06 intake | **20** | Uncontrolled physical access to the gate controller, 4.2 km from the powerhouse. **No network treatment exists for this risk at all** |
| 2 | R-23 | Z-06 radio | 15 | Unauthenticated protocol over a link whose far end is physically exposed |
| 3 | R-24 | Z-06 instrumentation | 15 | Level measurement that gate logic trusts without corroboration |
| 4 | R-25 | Z-06 cellular backup | 15 | A second path into the intake that exists for maintenance convenience |
| 5 | R-33 | C-06 conduit | 15 | The conduit carrying gate commands over that radio |
| 6 | R-31 | C-09 vendor access | 15 | Supply chain — no 62443-2-4 obligations flowed to the OEMs |
| 7 | R-32 | C-09 vendor access | 15 | Shared vendor credentials, no just-in-time approval, no session recording. The Oldsmar shape |
| 8 | R-18 | Z-05a recovery | 15 | Backups on the same domain, reachable from the host that would be encrypted, never restore-tested |
| 9 | R-27 | Z-07 removable media | 15 | No pre-connection scanning, no dedicated site laptops |
| 10 | R-29 | Z-08 DMZ services | 15 | Internet-reachable services in the brokering layer |
| 11 | R-30 | Z-08 firewall | 15 | Rule set never reconciled against the conduit register |

### 5.2 What the shape of that list says

**Not one Extreme risk is in Z-01, Z-02, Z-03 or Z-04.** After recalibration, nothing at the machine, the protection, the auxiliaries or the control room reaches Extreme.

Every one of the eleven is at an **edge**: the remote structure, the vendor, the boundary, the media, the backup. That is the finding the board should take away, and it is counter-intuitive enough to be worth stating plainly — **the risk is not where the turbine is. It is where the plant meets everything that is not the plant.**

Two consequences follow directly:

- **Five of the eleven are at the intake.** A single site — unstaffed, 4.2 km upstream, behind a padlock — carries 45% of the Extreme population. Treatment there is physical and detective before it is ever network, and the cheapest movement available in this whole assessment is at that structure rather than in the powerhouse.
- **Three of the eleven are contractual rather than technical** — R-31 and R-32 (vendor obligations and access discipline) and R-18 (a restore-tested off-site backup). They are closed by a purchase order and a tested procedure, not by an appliance. **This is why the CRS matters more than the firewall.**

### 5.3 Calibration note, carried forward honestly

**39 of the 40 risks require treatment.** Decision D-1 reduced the Extreme band but did not change that number, because the criteria require treatment at High as well as Extreme, and a normally unattended station whose countermeasures are periodic and detective against threats that act in minutes genuinely sits there before treatment.

The prioritisation therefore does not come from the band. It comes from the **priority score** and from the **treatment plan sequence**, and the board should read those rather than the band counts. A register that prioritises everything prioritises nothing; the answer here is the ordering, and the ordering is explicit.

---

## 6. Conditions on this approval

Approval is granted **subject to** the following. Each is a fact the assessor could not establish and the owner can.

### 6.1 A-01 — the condition the assessment stands on

**The hardwired overspeed trip is assumed to operate independently of every programmable device in the SUC.** It has not been verified.

Six risks — R-12, R-17, R-26, R-35, R-38, R-39 — are rated at direct consequence 4 rather than 5 **precisely because this trip stands behind them.**

**If A-01 is false:**

| | Consequence |
|---|---|
| Those six risks | Return to consequence 5 |
| Extreme band | Returns from 11 to 17 |
| Z-02 target security level | Rises to **SL 4** |
| This specification | Must be reissued |

**Verification method:** witness an overspeed trip test with the governor de-energised and the unit control PLC in STOP, recording trip speed and resulting gate closure. A certificate, a datasheet or a vendor statement does not discharge this — the claim is about independence, and independence is shown by removing the thing it is independent of.

**This is the single highest-value hour available anywhere in the programme.** One witnessed test either confirms the shape of the entire register or changes it fundamentally, and it costs a morning.

### 6.2 Other conditions

| # | Condition | Effect if false |
|---|---|---|
| C-1 | A-02 — powerhouse physical access is controlled and logged | Z-07 and C-10 treatment assumptions fail; the transient-connection model loses its only control |
| C-2 | A-04 — no wireless exists inside the powerhouse | A new zone is required and the partition is reopened |
| C-3 | A-07 — market dispatch is advisory, not actuating | C-07 sits inside the control loop; its SL-T rises |
| C-4 | The intake RTU supports DNP3 Secure Authentication | C-06's SL-T 3 is aspirational rather than achievable, and the finding moves to procurement |
| C-5 | Annexure D §13.1 — which route, if any, brings the station inside the CIRMP regime | Determines whether obligations are regulatory or contractual, and whether the 12-hour reporting duty attaches |
| C-6 | Market registration category — scheduled, semi-scheduled or non-scheduled | Sets C-07's telemetry obligations and its SL-T |

---

## 7. What this approval does not do

Stated plainly, because approval records are routinely over-read:

- **It does not certify the plant as secure.** It accepts a description of risk and a plan.
- **It does not establish achieved security level.** SL-A is measured, not approved. The SL gap sheet of document 05 records estimates that require verification in situ.
- **It does not discharge the requirements of the CRS.** Those are discharged at FAT, SAT and commissioning, against the hold points in document 10 §9.
- **It does not substitute for the operational obligations of IEC 62443-2-1.** A partition approved and then never maintained decays from the day of handover — every undocumented cable, every emergency firewall rule, every vendor account left open after a call-out.
- **It does not resolve the conditions in §6.** Those remain open, and the risks that depend on them remain conditional.

---

## 8. Review and reassessment triggers

The assessment is re-run, not merely re-read, when any of these occurs:

| Trigger | Why |
|---|---|
| **A-01 is found false** | The register's consequence ratings change materially |
| Any change to a zone's assets, or any new communication path | The partition is a statement about a configuration; change the configuration and the statement expires |
| A cyber incident at this station, or at a comparable asset in the operator's fleet | Likelihood anchors are threat-informed; a real event is data |
| Change of system integrator, or of a principal OEM | The 2-4 and 4-1 obligations are supplier-specific |
| Material change in the threat environment — a new ATT&CK for ICS technique affecting this architecture, or a sector advisory | The threat input, Annexure C, is the input that dates fastest |
| Change to the SOCI asset-class definitions or the CIRMP rules | Annexure D §13.1 is a test against a statutory threshold; the threshold can move |
| **At most 3 years** | Beyond that the assumptions are archaeology |

---

## 9. Approval

**By signing, each party confirms they have read §3 (decisions), §5 (residual risk), §6 (conditions) and §7 (what this does not do).**

| Role | Responsible for | Name | Signature | Date |
|---|---|---|---|---|
| **Board / governing body representative** | **Acceptance of the 11 Extreme risks in §5.1 — this cannot be delegated** | | | |
| Asset owner executive | Acceptance of the 28 High risks; ratification of decisions D-1 to D-5 | | | |
| Operations manager | Conditions §6.1 and §6.2; operational obligations surviving handover | | | |
| Engineering manager | Verification of A-01; the partition; the CRS as issuable | | | |
| Risk / HSE representative | Tolerable risk criteria rev 0.2 and the widened life-safety override | | | |
| Assessor | Method, and the accuracy of the record | Epiphane Zaré | | 14 Sept 2026 |

### 9.1 If the board declines to accept an Extreme risk

That is the correct outcome, not a failure of the assessment. The criteria in document 04 §5 state that Extreme is **not tolerable under any circumstances** and must be treated to High or below. Where treatment is not immediately achievable, the path is an **interim control plus a documented, time-bound derogation reviewed monthly** — never an acceptance.

A board that accepts eleven Extreme risks unchanged has not used this document. A board that funds the intake and the vendor obligations, and holds a derogation on the rest, has.

---

## 10. Assessor's statement

This assessment follows IEC 62443-3-2, ZCR 1 to 7. The method is the standard's; the judgements are mine and are marked as such at §3.

Where a fact could not be established it is declared as an assumption with its consequence stated, rather than asserted. Where a regulatory characterisation could not be verified against a primary source it is flagged rather than claimed — and one such flag, on SOCI applicability, resolved **against** the assessment's original position and has been corrected.

**What this work does not demonstrate, and is not offered as:** participation in a real FAT, SAT, commissioning or operational cutover. It is a desk exercise against a fictional facility. It demonstrates method.

---

## 11. Revision history

| Rev | Date | Change |
|---|---|---|
| 0.1 | 14 Sept 2026 | Initial draft for asset owner signature |

---

*IEC 62443-3-2 ZCR 7 · KCH-CYB-APP-001 · Kanangra Creek Hydro Station · Fictional facility, worked example*
