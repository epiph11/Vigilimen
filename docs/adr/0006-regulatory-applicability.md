# ADR-006 — Which regulations actually apply to a mining operation

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré
**Supersedes:** none · **Related:** ADR-009 (compliance framework selection, S2)

---

## Context

"Mining is critical infrastructure" is said constantly and is **wrong as a statement of Australian law**. Getting it wrong in either direction is expensive: claim SOCI applies and you build a compliance programme nobody requires; claim it does not and you miss the obligations that genuinely attach.

This ADR fixes the position for the whole programme, because the compliance frame decides what S2, S10 and S11 are actually building.

---

## The finding

**The SOCI Act 2018 covers eleven sectors.** Mining is not one of them.

> Communications · Financial services and markets · Data storage or processing · Defence industry · Higher education and research · Energy · Food and grocery · Healthcare and medical · Space technology · Transport · Water and sewerage

There is no mining asset class and no critical-minerals asset class. A mine is not a critical infrastructure asset because it is a mine.

**Mining groups are nonetheless captured — at their edges.** A large miner typically owns or operates assets that *are* listed:

| Caught — the listed assets a miner may own | Not caught |
|---|---|
| Generation feeding the grid (≥ 30 MW, or an SRAS contract) · a dedicated rail line and rolling stock · a port or terminal · a water or sewerage utility serving a township · a gas or liquid fuel pipeline — each subject to its own threshold | **The pit, the processing plant, the conveyors, the crushers** |

**The safety-critical OT inside the mine is governed by work health and safety mining law, not by SOCI.** That is a different regulator, a different duty, and a genuinely different standard of proof — the WHS duty is *so far as is reasonably practicable*, which is more demanding in some respects than any cyber rule and has no cyber-specific language at all.

---

## Decision

**This programme adopts the following position, and every downstream artifact inherits it.**

1. The simulated mine site is **not** a SOCI critical infrastructure asset. No CIRMP obligation attaches to it by virtue of being a mine.
2. Where the programme models an asset that *is* listed — the worked hydro station assessment is one — **applicability is established by a written test against the threshold, never assumed.**
3. Safety-critical OT inside the mine is treated under the **WHS duty**, and cyber risk to a protective function is framed as a safety risk, because that is what it is.
4. The programme nonetheless builds to the CIRMP control set **voluntarily**, and says plainly that it is voluntary.

### Why build to it voluntarily

Three reasons, and the third is the honest one. **It is where the sector is going** — miners already run electricity, rail and port assets carrying CIRMP obligations, and no operator runs two security programmes, so regulated obligations propagate inward by policy long before they propagate by statute. **The controls are correct on their own terms** — phishing-resistant MFA, central logging of successful *and* unsuccessful authentication, asset inventory, restoration capability, three months of independent operation, supply chain and FOCI assessment; none becomes a bad idea because a statute does not compel it. **And it is a portfolio programme, where the regulated frame is the one worth being able to demonstrate** — stating that plainly rather than dressing it as necessity is the point, because a compliance position that cannot say why it exists collapses under the first question.

---

## The framework table point

**IEC 62443 appears in neither CIRMP approved-framework table.** This is the detail that separates someone who has read the rules from someone who has read a blog post about them.

The enhanced table lists ISO/IEC 27001:2023, ASD Essential Eight at **ML2**, NIST CSF **2.0**, C2M2 **v2.1 at MIL2**, and the AESCSF **2023 Core at SP-2** — every one raised a level from the baseline table. An operator wishing to use 62443 **maps it underneath whichever listed framework it nominates, or argues equivalence in writing.**

---

## Consequences

**Positive.** The programme's compliance claims are defensible under challenge. ADR-009 at S2 selects a *listed* framework and maps 62443 beneath it, rather than nominating 62443 and being wrong. The distinction between statutory obligation and voluntary adoption is visible in every artifact, which is what makes the artifacts usable as evidence of judgement rather than of effort.

**Negative.** More work than asserting applicability. Each modelled asset now needs its own threshold test, and at least one of those tests has already returned "outside the regime" — the 20 MW hydro station in the worked assessment — which required rewriting an annexure that was already finished.

**Accepted risk.** Thresholds move. The SOCI definitions rules have been amended repeatedly since 2018, and this position has a shelf life. It is therefore a **reassessment trigger** wherever it is relied upon, not a standing fact.

---

## Verification

**Eleven sectors, mining not among them** — CISC, *Security of Critical Infrastructure Act 2018*, verified 14 Sept 2026.
**Critical electricity threshold, 30 MW or an SRAS contract** — secondary legal commentary on the SOCI Definitions Rules, 14 Sept 2026, **to be re-checked against the primary rules before external use.**
**Enhanced CIRMP framework table** — Enhanced CIRMP Rules 2026, carried from the hydro assessment, Annexure D.

**The middle line is deliberately left marked.** A verification note that records *how well* something was verified is worth more than one that records only that it was.

---

*LIMEN-ADR-006 · Sprint 0 · Gate M0*
