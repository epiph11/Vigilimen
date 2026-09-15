# ZCR 4 — Tolerable risk criteria

**SUC:** Kanangra Creek Hydro Station · **Document:** 04 of 12 · **Status:** DRAFT — **requires asset owner approval before ZCR 5 begins** · **Date:** 14 Sept 2026

---

## 1. Why this document must be approved first

> **Agree the criteria before the assessment, or the assessment is unfalsifiable.**

If tolerable risk is decided after the detailed assessment, the threshold drifts toward wherever the findings happen to land. Every risk turns out to be acceptable, because acceptability was defined by what was found. This document therefore has to be signed before document 05 starts, and it is the reason ZCR 4 sits where it does in the standard rather than at the end.

It is also the document that makes the assessment *the asset owner's*. The assessor supplies method; only the owner can say what the organisation is willing to tolerate. A consultant who sets the risk appetite has taken a decision that was not theirs.

---

## 2. Consequence scale

Five levels, five categories. A scenario takes the **highest** rating across categories — consequences do not average.

| | **Safety** | **Environment** | **Availability** | **Financial** | **Regulatory / reputation** |
|---|---|---|---|---|---|
| **5 · Catastrophic** | Fatality, or multiple permanent disabilities | Uncontained release with lasting harm; uncontrolled water release affecting third parties | > 6 months outage | > $10M | Licence revocation; prosecution; ministerial intervention |
| **4 · Major** | Permanent disability; multiple lost-time injuries | Reportable breach requiring remediation; environmental flow breach | 1–6 months | $1–10M | Enforceable undertaking; mandatory regulatory report; sustained adverse coverage |
| **3 · Moderate** | Lost-time injury | Reportable, remediable within the licence | 1–4 weeks | $100k–1M | Reportable incident; local coverage |
| **2 · Minor** | Medical treatment, no lost time | Contained; internally reportable | 1–7 days | $10–100k | Internal reporting only |
| **1 · Negligible** | First aid | None | < 1 day | < $10k | None |

### Notes on the scale

**Safety leads, and the ordering is not decorative.** In an OT assessment the priority is safety, then availability, then integrity, then confidentiality — the inversion of the IT ordering. Where a scenario rates 5 on safety and 2 on availability, it is a 5. The temptation to let a familiar availability number dominate an unfamiliar safety number is the most common distortion in a first OT risk assessment.

**Environment includes third-party water release.** For a hydro asset this is not a sub-case of availability. Downstream flooding is a consequence class of its own with its own regulator.

**Regulatory includes the SOCI reporting trigger.** A scenario taking operational technology offline is a *significant impact on availability* and carries a **12-hour** report to ASD, not 72. Any scenario rating 4 or 5 on availability should be assumed to carry that obligation, and the incident response plan must be able to meet it.

---

## 3. Likelihood scale

Likelihood is assessed at ZCR 5, not here — but the scale is fixed now so it cannot be adjusted to suit findings later.

| | Descriptor | Guidance |
|---|---|---|
| **5 · Almost certain** | Expected within 12 months | Techniques are commodity; the path is exposed and requires no specialist knowledge |
| **4 · Likely** | Expected within 1–3 years | Known techniques, moderate effort, path reachable from outside |
| **3 · Possible** | Expected within 3–10 years | Requires IACS-specific knowledge or insider access; documented in the wild |
| **2 · Unlikely** | Expected within 10–25 years | Requires sustained effort, specialist tooling and target-specific knowledge |
| **1 · Rare** | Not expected | Requires extended resources against this specific asset |

**Likelihood here is threat-informed, not actuarial.** There is no dataset of hydro station compromises from which to derive frequencies, and pretending otherwise produces false precision. The anchors are attacker capability and path exposure, which is also what makes the scale commensurable with the SL definitions in document 03 — SL 3 corresponds roughly to a likelihood-3 actor.

The threat input is **MITRE ATT&CK for ICS**, with the canonical cases as calibration points: Stuxnet, Industroyer and Industroyer2, TRITON, PIPEDREAM, Colonial Pipeline and Oldsmar.

---

## 4. Risk matrix

Risk = likelihood × consequence, banded.

| | **C1** | **C2** | **C3** | **C4** | **C5** |
|---|---|---|---|---|---|
| **L5** | M | H | **E** | **E** | **E** |
| **L4** | L | M | H | **E** | **E** |
| **L3** | L | M | H | H | **E** |
| **L2** | L | L | M | H | H |
| **L1** | L | L | L | M | H |

**L** Low · **M** Medium · **H** High · **E** Extreme

---

## 5. Risk acceptance criteria

**This is the section requiring signature.**

| Band | Treatment | Authority to accept | Timeframe |
|---|---|---|---|
| **Extreme** | **Not tolerable under any circumstances.** Must be treated to High or below. Where treatment is not immediately achievable, an interim control plus a documented time-bound derogation is required, reviewed monthly. | Board or equivalent governing body — *cannot* be accepted at site or asset-manager level | Interim control within 30 days; treatment plan within 90 |
| **High** | Not tolerable without treatment. Treatment plan required with named owner and date. | Asset owner executive | Treatment within 12 months |
| **Medium** | Tolerable with documented justification and monitoring. Treat where reasonably practicable. | Asset manager | Reviewed annually |
| **Low** | Tolerable. Monitor through routine review. | Site | Reviewed at each assessment cycle |

### Two constraints that override the matrix

**A credible path to fatality is never accepted on likelihood grounds alone.** Any scenario with a credible path to fatality requires treatment regardless of where it falls in the matrix. A low-likelihood fatality is still a fatality, and "unlikely" is not a control. This mirrors the *so far as is reasonably practicable* duty that sits over the whole facility under work health and safety law, and it is the point at which cyber risk assessment and safety obligation meet.

The override is triggered by **consequence 5 in the Safety category, and by consequence 5 in the Environment category where the mechanism is uncontrolled water release affecting third parties.**

> **Correction, 14 September 2026 — rev 0.2.** As first drafted this override named only the Safety category. That was a drafting error, and it was exposed by the ZCR 5 priority scoring rather than by review: the environment-5 band in §2 above describes "uncontrolled water release affecting third parties", which is a drowning mechanism, and five risks in the register — R-22, R-23, R-24, R-25, R-33, all at the intake and weir — sat outside an override that was plainly meant to catch them. Reading the override as **life-safety** rather than **safety-category** brings the covered population from 11 risks to 16.
>
> The general lesson is worth keeping: *a consequence scale can describe a fatality in a category that is not called Safety.* An override written against a category name rather than against a mechanism will miss it. This is why the ZCR 5 workbook applies the override by formula and not by judgement — the formula is auditable, and it failed visibly.

**No treatment may be applied inside a protective function.** Where a control would reduce risk by inserting itself into the trip path of a protection or safety function, it is rejected on principle, however large the risk reduction. A control that can fail closed on a protective function has made the plant less safe. Alternative treatment must act on management interfaces, on access, or on detection — never on the protective action itself. *(Carried from document 03, Z-01.)*

---

## 6. Residual risk and the SL-A gap

Two distinct things are tracked at ZCR 5, and conflating them is a common error:

**Residual risk** — risk remaining after existing and planned countermeasures, assessed against the criteria above. It is a *risk* statement.

**The SL-A gap** — the difference between the **SL-T** assigned in document 03 and the **SL-A** actually achieved in situ. It is a *capability* statement.

The operating loop is: **assess SL-A against SL-T; the delta is the remediation backlog.** And the third term matters — **SL-C**, what a component is *capable* of, as declared by its vendor. A capable device badly configured achieves less than it could; an incapable device cannot achieve SL-T at all no matter how well configured, and that finding belongs in procurement rather than in engineering.

One trap worth stating explicitly because it is a standard interview probe: **maturity level and security level have no relationship to each other.** ML describes how institutionalised a *process* is (62443-2-1 and -2-4); SL describes what attacker capability a *system* withstands. An organisation at ML 3 can operate a zone at SL 1.

---

## 7. Assumptions governing these criteria

| # | Assumption |
|---|---|
| T-01 | Financial bands reflect the operator's materiality thresholds, not the station's revenue |
| T-02 | Availability bands assume single-unit outage; portfolio-level correlated outage is out of scope |
| T-03 | Safety bands apply to personnel on site and to third parties downstream |
| T-04 | The asset owner's existing enterprise risk framework uses a compatible 5×5 structure — **if it does not, these criteria must be re-expressed in the house scale rather than run in parallel** |

T-04 matters more than it looks. A cyber risk assessment on a bespoke scale cannot be aggregated into the enterprise risk register, which means it cannot reach the board, which means Extreme risks have no route to the only authority permitted to accept them. **Align the scale or the governance path breaks.**

---

## 8. Approval

ZCR 7 requires asset owner approval of the assessment. These criteria require approval *before* ZCR 5 begins.

| Role | Name | Signature | Date |
|---|---|---|---|
| Asset owner representative | | | |
| Operations manager | | | |
| Risk / HSE representative | | | |
| Assessor | Epiphane Zaré | | 14 Sept 2026 |

**Items requiring explicit confirmation at signature:**

1. The financial bands in §2 match the operator's materiality thresholds
2. The acceptance authorities in §5 match the operator's delegation framework
3. The two overriding constraints in §5 are accepted as written
4. The scale is compatible with the enterprise risk framework (T-04)

---

## 9. Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 14 Sept 2026 | Initial draft for review |
| 0.2 | 14 Sept 2026 | §5 override widened from *safety category* to *life-safety mechanism*, covering environment-5 uncontrolled water release. Raised by ZCR 5 priority scoring. |
