# IEC 62443-3-2 Risk Assessment — Kanangra Creek Hydro Station

A worked cyber security risk assessment of a 20 MW run-of-river hydroelectric generating station, following **IEC 62443-3-2** and producing the full ZCR 1–7 artifact set.

> ⚠ **The facility is fictional.** It is modelled on the architecture of a real small run-of-river station but describes no actual asset. Every operating assumption is declared as an assumption, not a finding.

---

## Why this exists

IEC 62443-3-2 is the part of the series that most OT security work is actually about: partitioning a system into zones and conduits, assigning each a target security level from consequence, and consolidating the result into a **Cybersecurity Requirements Specification** that a system integrator can be contracted against.

The CRS is the deliverable that makes 62443 real, because it is the only one that is *contractual* — it flows into 62443-2-4 obligations on the integrator and 4-2 capability requirements on components.

---

## Documents

| # | Document | ZCR | Status |
|---|---|---|---|
| 01 | [System under Consideration](01-suc-description.md) | ZCR 1 | Draft |
| 02 | [Initial risk assessment](02-initial-risk-assessment.md) | ZCR 2 | Draft |
| 03 | [Zone and conduit partition](03-zone-conduit-partition.md) | ZCR 3 | Draft |
| 04 | [Tolerable risk criteria](04-tolerable-risk-criteria.md) | ZCR 4 | Draft rev 0.2 — life-safety override widened |
| 05 | [Detailed risk assessment](05-detailed-risk-assessment.xlsx) (xlsx) | ZCR 5 | Draft |
| 06 | [Zone and conduit drawing](06-zone-conduit-drawing.html) (html) | ZCR 6 | Draft — KCH-CYB-ZC-001 rev 0.2 |
| 07 | Zone characteristics register | ZCR 6 | Consolidated into **10, Annexure A** |
| 08 | Operating environment assumptions | ZCR 6 | Consolidated into **10, Annexure B** |
| 09 | Threat environment | ZCR 6 | Consolidated into **10, Annexure C** |
| 10 | **[Cybersecurity Requirements Specification](10-cybersecurity-requirements-specification.md)** | ZCR 6 | Draft — KCH-CYB-CRS-001 rev 0.2 |
| 11 | Regulatory requirements | ZCR 6 | Consolidated into **10, Annexure D** |
| 12 | **[Asset owner approval record](12-asset-owner-approval-record.md)** | ZCR 7 | Draft — KCH-CYB-APP-001 rev 0.1 |

Documents 07 to 09 and 11 were written as standalone deliverables in the original plan and have been folded into the CRS as annexures instead. They are all *inputs the CRS depends on* — a characteristic, an assumption, a threat, a statutory obligation only matters here because a requirement rests on it. Splitting them out produced four documents nobody would read and a specification that pointed at them. Folded in, each annexure row is reachable from the requirement that cites it.

---

## The partition at a glance

| Zone | SL-T | Worst consequence |
|---|---|---|
| Z-01 Protection and trip | **3** | 5 — unprotected equipment, fire, fatality |
| Z-02 Unit control | **3** *(4 if A-01 false)* | 5 — overspeed, water hammer |
| Z-03 Station auxiliaries | 2 | 4 — cascade to machine damage |
| Z-04 Supervisory control | 2 | 4 — loss of view and generation |
| Z-05a Engineering | **3** | 5 — unrecoverable outage |
| Z-05b Plant information | 2 | 3 — disclosure |
| Z-06 Intake and weir | **3** | 5 — third-party flooding |
| Z-07 Transient and externally connected | **3** | inherited |
| Z-08 Site DMZ | **3** | inherited |

Thirteen conduits, seven at SL-T 3. The highest-consequence conduit is **C-09, vendor remote access**, because its consequence is the maximum of everything it can reach.

**Z-05 was split at ZCR 5.** It had been rated SL-T 3 because of one asset — the engineering workstation — leaving the historian carrying a target it had not earned. Z-05b now reaches its target *by being correctly drawn rather than by being bought*: its SL gap is zero at no capital cost. That is the cheapest control in the assessment, and it is an argument for spending time on the partition rather than on the firewall.

---

## What ZCR 5 found

40 risks across 9 zones and 13 conduits, mapped to **MITRE ATT&CK for ICS v19.2**.

Eleven risks are Extreme after existing controls, and **not one of them is in Z-01, Z-02, Z-03 or Z-04.** Nothing at the machine, the protection, the auxiliaries or the control room reaches Extreme. Every one of the eleven sits at an **edge**:

- **The intake** — five of the eleven. An unstaffed structure 4.2 km upstream behind a padlock carries 45% of the Extreme population. **R-22, the highest residual risk in the assessment, has no network treatment available at all.**
- **Vendor remote access** — two. Shared credentials, no just-in-time approval, no session recording. The Oldsmar shape.
- **Recovery, media and the DMZ** — four. Backups on the same domain as the host that would encrypt them; no pre-connection scanning; a firewall rule set never reconciled against the conduit register.

The finding is worth stating plainly because it is counter-intuitive: **the risk is not where the turbine is. It is where the plant meets everything that is not the plant.**

Three of the eleven are **contractual rather than technical** — vendor obligations, access discipline, a restore-tested off-site backup. They close with a purchase order and a tested procedure, not an appliance. That is why the CRS matters more than the firewall.

### The calibration, and what fixing it did and did not achieve

The register first flagged **39 of 40 risks for treatment**, with 17 carrying safety consequence 5. That is a finding about the register as much as about the plant: a register that prioritises everything prioritises nothing.

Most of those 5s were **inherited from what a risk enabled rather than what it achieved**. Seven risks were renoted to the consequence they reach directly, without traversing a further zone boundary or defeating a further control, and the escalation chains moved to an **attack path sheet** where they stay visible. The Extreme band fell from 17 to 11.

**The treatment count did not move, and the workbook says so.** It is still 39 of 40, because the acceptance criteria require treatment at High as well as Extreme. What changed is the ranking underneath it: a priority score now orders the treatment plan, and R-22 — the intake — comes out top on the arithmetic rather than on the narrative. *'If everything needs treatment, what do I fund first'* has an answer that does not depend on the reader's patience.

Calibrating also **found a defect in the criteria themselves**. The life-safety override was written against the *Safety category*, while the criteria's own environment-5 band describes uncontrolled water release affecting third parties — a drowning mechanism. Five intake risks sat outside an override plainly meant to catch them. Document 04 was corrected to rev 0.2. The general lesson is worth more than the fix: **an override written against a category name rather than against a mechanism will miss it.**

**All of this rests on one unverified fact.** Six of the seven renotings hold only because the hardwired overspeed trip is independent of every programmable device (assumption A-01). If it is not, they return to consequence 5 and the Extreme band returns to 17. The register is conditional on one witnessed test, and it says which one.

---

## The drawing

Document 06 is the one page a reader should be able to take in at a glance: nine zones and thirteen conduits, each carrying its target security level, laid across the Purdue levels **without aligning to them**. That misalignment is the argument — Z-05a sits a level above Z-04 and is rated a level higher, because the engineering workstation can reprogram the machine while the HMI can only ask it politely. The split states it a second way: Z-05a and Z-05b sit at the *same* Purdue level, in the same equipment room, and carry different targets.

Two amber markers carry the ZCR 5 findings onto the drawing: the intake RTU, and the vendor remote access conduit. The intake is drawn with a geographic break and its distance annotated, because 4.2 km behind a padlock is a security property, not a civil one.

---

## Three things this assessment argues

**Zones come from consequence, not from topology.** Z-05a (engineering) is rated *above* Z-04 (supervisory), inverting the Purdue ordering, because the engineering workstation can reprogram the machine while the HMI can only ask it politely. Purdue describes function; it does not describe consequence — and neither does a rack.

**Nothing is rated SL-T 4, and that is a defensible judgement rather than an omission.** SL 4 implies extended resources directed at *this* asset. A 20 MW station that is not systemically significant does not obviously attract that, and **an SL-T you cannot fund is worse than an honest SL-T 3** — it produces a paper requirement instead of a control. The contrary argument is set out in document 03 §5 so a reviewer can take it up.

**No security control may sit inside a protective function.** A control that can fail closed on a protection or safety function has made the plant less safe, not more. This is carried as a hard constraint from the partition into the risk acceptance criteria, and it is the direct lesson of TRITON.

---

## Method and sources

Method follows IEC 62443-3-2 ZCR 1–7. Threat input is **MITRE ATT&CK for ICS**. Regulatory context is the **SOCI Act 2018** as amended by the **Enhanced CIRMP Rules 2026**, and **AESCSF v2 (2023 Core)**.

Where a regulatory characterisation could not be verified against a primary source it is flagged inline rather than asserted.

One of those flags has since been resolved, and it resolved **against** the assessment's original assumption. A generation asset is a *critical electricity asset* where it is connected to a wholesale market and either has an installed capacity of **at least 30 MW** or its operator holds a **system restart ancillary services** contract. **Kanangra Creek is 20 MW and does not cross that threshold on its own.** Annexure D of the CRS was rewritten from an assertion of CIRMP applicability into a four-branch test the asset owner must answer.

That correction is worth more to this document than the confirmation would have been. *Critical infrastructure* is routinely read as *every power station*; the threshold is public, and it is 30 MW.

---

## Fidelity

This assessment is a desk exercise against a fictional facility. It demonstrates method, not field experience. What it does not and cannot demonstrate is participation in a real FAT, SAT or commissioning phase, and it is not offered as a substitute for that.

---

*Assessor: Epiphane Zaré · September 2026*
