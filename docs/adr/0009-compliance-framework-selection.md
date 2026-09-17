# ADR-009 — Nominate AESCSF. Map IEC 62443 underneath it.

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré
**Related:** ADR-006 (regulatory applicability) · **Sprint:** 2

---

## Context

ADR-006 established that this programme builds to the CIRMP control set **voluntarily**. Voluntary or not, the control set has a shape: an operator nominates one framework from an approved table and evidences against it. **IEC 62443 appears in neither table** — the enhanced table lists ISO/IEC 27001:2023, ASD Essential Eight at ML2, NIST CSF 2.0, C2M2 v2.1 at MIL2, and the AESCSF 2023 Framework Core at SP-2, so an operator wanting to use 62443 maps it *underneath* a listed framework or argues equivalence in writing.

The choice of which framework carries the evidence is not a formality: the nomination decides what S10 and S11 actually build.

---

## Decision

**Nominate AESCSF 2023 Framework Core at Security Profile 2. Map IEC 62443 beneath it. Run Essential Eight ML2 as a second, declared, partial lens.**

---

## Why AESCSF

**It is sector-native and OT-aware.** AEMO built it for Australian energy — the sector this programme's assets actually sit in, being the electricity, water and rail assets a miner owns at its edges (ADR-006) — and its practice set assumes control systems, vendors and field assets rather than an office estate with some machinery attached. It also inherits C2M2's structure with the sector calibration already done, so choosing it does not forfeit C2M2.

**The 42 anti-patterns are the part nobody else has.** Scored present or not present, they describe how organisations actually fail rather than what they should do, which makes them far more diagnostic than a control checklist — and distinctive enough to name unprompted.

### The distinction that must not be got wrong

**Maturity Indicator Levels (MIL 1–3)** are assessed **independently per domain** and describe how *institutionalised* a practice is. **Security Profiles (SP 1–3)** are cumulative groupings applied **collectively across all domains** — SP-1 is 109 practices, SP-2 is 239, SP-3 is 312. MIL is per-domain depth; SP is a scope applied across the whole. Confusing them is a standard interview probe and it is how an assessment report becomes unusable.

**A further trap, carried from the hydro assessment:** maturity level and *security level* have no relationship to each other at all. ML describes how institutionalised a process is; SL describes what attacker capability a system withstands. An organisation at ML 3 can operate a zone at SL 1.

---

## Why not the others

| Rejected | Reason |
|---|---|
| **ISO/IEC 27001:2023** | An ISMS standard — certifiable, respected, and largely silent on what makes a control system different. It would produce a management system and no OT findings |
| **NIST CSF 2.0** | An excellent *mapping spine* and a poor *nomination*. It is deliberately outcome-level, so evidencing against it means choosing an underlying control set anyway — one framework's worth of work for two frameworks' worth of paperwork |
| **C2M2 v2.1** | Good, and AESCSF already contains its structure with the sector calibration added |
| **ASD Essential Eight ML2** | See below. Not rejected — demoted |

---

## Essential Eight, honestly

The enhanced rules name Essential Eight ML2, so it is assessed. **It is not the nomination, and the reason is worth writing down rather than glossing.**

The Essential Eight is **Application control · Patch applications · Configure Microsoft Office macro settings · User application hardening · Restrict administrative privileges · Patch operating systems · Multi-factor authentication · Regular backups.**

Read that list against a Purdue Level 1 control network:

- **Office macro settings** describe an attack surface that does not exist on a PLC.
- **Patch operating systems** and **patch applications** assume a cadence measured in weeks. OT patching waits for vendor validation, an outage window measured in months, and equipment whose warranty is void if you patch it. The honest answer is compensating controls and virtual patching at the network layer — which the Essential Eight has no vocabulary for.
- **Application control** and **user application hardening** are meaningful on the engineering workstation and meaningless below it.
- **MFA**, **restrict administrative privileges** and **regular backups** transfer well, and the hydro assessment's worst finding was a backup problem.

Three of eight transfer cleanly, two partially, three barely. **The mapping is reported as partial, with non-applicable mitigations marked and justified**, rather than scored against a plant they were not designed for. The worked scorecard is at `docs/compliance/e8-ml2-self-assessment.xlsx`, and its finding is blunt: **the OT estate cannot reach ML2 at all**, because the patch cadence requirement and vendor-validated OT patching are not in tension — they are incompatible.

> ASD's own guidance frames the model as designed principally for internet-connected Windows networks, and points elsewhere for cloud, enterprise mobility and operational technology. *That characterisation is from secondary sources and should be checked against ASD's exact wording before external use* — it matters, because it is the difference between "we chose not to apply it" and "ASD says it does not apply".

**Forcing a clean Essential Eight score over an OT estate produces a number that is wrong in a way nobody can see.** Declaring the partial mapping produces a number that is smaller and true, and the second is the one that survives an auditor.

---

## Consequences

**Positive.** The nomination is defensible, the 62443 work is not wasted — it becomes the technical evidence beneath AESCSF's practices — and the Essential Eight gap is documented as a scoping decision rather than discovered as a failure.

**Negative.** Two frameworks to maintain, and AESCSF is the less widely recognised of the pair outside Australian energy. A reader from general IT security will know Essential Eight and not AESCSF, so every report needs a sentence of orientation.

**Revisit if** the asset moves sector, or if a future CIRMP table admits IEC 62443 directly — which would make this whole ADR unnecessary and is the outcome to hope for.

---

*VIGILIMEN-ADR-009 · Sprint 2*
