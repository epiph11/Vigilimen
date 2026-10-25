# Station 5 — evaluation of the IEC 62443-3-2 assessment

**Scope:** `docs/assessments/hydro-station/` (Kanangra Creek, a **fictional** 20 MW station) · **Date:** 25 October 2026 · **Reviewer:** Claude, with the author

Method: read all documents, then **recompute** the register's headline numbers from its inputs (`scripts/s5_recompute_register.py`), then check claims against each other and against the one external source that could be checked. What was *not* done is stated at the end.

---

## What holds

| Claim | Recomputed |
|---|---|
| 40 risks | 40 |
| 11 Extreme after existing controls | **11** (23 Extreme unmitigated) |
| None of the 11 in Z-01 to Z-04 | **True** |
| Grouping: intake 5, vendor access 2, recovery/media/DMZ 4 | **True**: intake R-22..25 + R-33 (5), vendor R-31, R-32 (2), R-18 backups + R-27 media + R-29, R-30 DMZ (4) |
| 39 of 40 flagged for treatment | **39** (23 plain, 16 by the life-safety override), 1 "justify and monitor" |
| R-22 ranks first on the priority score | **20**, then R-18, R-23, R-24, R-25 at 15 |
| The override covers 16 risks | **16** (11 safety, 5 environment) |
| MITRE technique IDs in the register | Spot-checked **T1692 Unauthorized Message**: real, ATT&CK ICS, created April 2026, supersedes T0855 and T0856. Not an error |

The formula bug the walkthrough describes (an override written against a *category name* rather than a *mechanism*) is fixed in the workbook as it stands: `OR(I="Safety", I="Environment")`.

---

## Findings

**F1 — the workbook has no cached values.** Every formula cell (bands, treatment flag, priority, whole Summary sheet) is empty to anything that does not recalculate: a repository web view, a previewer, a script. Excel fills them on open. *Fix:* open and save once in Excel or LibreOffice. *Why it matters:* a reviewer who previews the file sees an assessment with no results.

**F2 — "seven renotings" versus six.** README and the Summary note both say seven risks were renoted and "six of the seven" depend on A-01. The Summary lists **six** IDs (R-12, R-17, R-26, R-35, R-38, R-39) and says R-20 "was already rated directly and is unchanged". The arithmetic works only if R-20 is the seventh and was not actually renoted. *Fix:* say six renoted, six conditional on A-01, R-20 unchanged.

**F3 — four of thirteen conduits have no risk row.** The register scores C-02, 04, 06, 07, 08, 09, 10, 11, 12. **C-01** (protection signalling and the hardwired trip), **C-03**, **C-05** and **C-13** have none. C-01 is probably covered at zone level by R-03 (GOOSE injection, Z-01), but that is an inference. **C-13**, the conduit *created* by the Z-05 split that the README calls "the cheapest control", has no risk of its own. A partition whose newest conduit is unscored has not finished ZCR 5.

**F4 — stale text in document 01.** §2 still says the SOCI threshold characterisation is "assumed, not verified" and "verify before external use", while the README says it has been resolved and CRS Annexure D states the 30 MW test. Document 01 was not updated. Separately, **ADR-006 itself flags the 30 MW figure as taken from secondary commentary and "to be re-checked against the primary rules"**. This review did not re-check it against the primary rules, so the README's word "resolved" is stronger than the evidence in the repository.

**F5 — R-18 is not at an edge in the sense the structural finding implies.** It sits in **Z-05a (engineering)**, the zone rated above supervisory because it can reprogram the machine. The finding "none of the 11 is in the zones containing the turbine" is true. "Every one sits at an edge" needs R-18 to be read as a *backup-store* risk rather than an engineering-workstation risk, and the register puts both in one row.

**F6 — the walkthrough's Station 5 is out of date.** It says "nine documents" and points at `Vigilimen\assessments\`. There are **eight** documents (07 to 09 and 11 are folded into 10), and the folder is `docs\assessments\hydro-station\`. Corrected in walkthrough rev 1.2.

**F7 — the assessed system is not the running one.** The SUC is a hydro station. The plant in Docker is a mining conveyor, and **no 62443-3-2 pass has been done on CONV-001.** The nearest link is ADR-011 against A-01 (hardwired overspeed trip independent of programmable devices), which is the same argument as the contactor in series. A short SUC and partition for CONV-001 would let the Modbus link (ADR-013) be registered as a conduit with a target SL.

---

## Proposed mapping for CONV-001, for the author to accept or reject

| Docker network | Zone | Proposed SL-T | Reason |
|---|---|---|---|
| `net_safety` | Safety | 3 | Consequence: injury. Nothing else may reach it |
| `net_control` | Control | 3 | Can start the belt; no authentication on Modbus |
| `net_supervisory` | Supervisory | 2 | Loses view, not safety |

Conduits to register: **gateway to PLC (Modbus, ADR-013)**, SCADA to gateway (OPC UA with passwords, `NoSecurity`, ADR-017/018), collector to gateway. The safety zone has **no conduit**, which is the point of FF-22.

---

## Not done

Primary-source verification of the SOCI threshold and the Enhanced CIRMP Rules 2026; ATT&CK IDs beyond T1692; a re-derivation of any consequence rating or likelihood (they are inputs, and judgements); the CRS requirement-by-requirement; the drawing (06) beyond its description. The self-test questions in the walkthrough are the author's to answer in the log.
