# RAID Log

**Ref:** LIMEN-GOV-002 · **Rev:** 1.0 · **Date:** 14 September 2026
**Seeded by:** first risk-storming pass (Sprint 0)

Risks · Assumptions · Issues · Dependencies. Reviewed at the end of every cycle, and re-scored at every gate.

---

## How this log is scored

**Likelihood × impact, 1–5 each.** Score is the product; the band is what drives action.

| Score | Band | Action |
|---|---|---|
| 15–25 | **High** | Named response, owner, and a date. Reviewed every cycle |
| 8–12 | Medium | Response identified. Reviewed at each gate |
| 1–6 | Low | Monitored. Reviewed at cycle boundaries only |

**A programme risk log with no High entries is a log that has not been filled in honestly.** Three below are High, and none of them is a technical risk.

---

## Risks

| # | Risk | L | I | Score | Response | Review |
|---|---|---|---|---|---|---|
| R-01 | **Scope inflation.** Three clouds, an OT plant and a full assurance programme is ambitious for one engineer at 23 h/week | 4 | 5 | **20** | MoSCoW cut lines fixed *at sprint planning*, not renegotiated at the deadline. Must-have is ≤ 60% of each sprint's hours | Every cycle |
| R-02 | **Indefinite polishing.** With no client and no deadline, the real failure mode is an assessment still being improved in March | 4 | 4 | **16** | Gates are pass/fail with dates. A document past its gate is frozen unless a reassessment trigger fires | Every cycle |
| R-03 | **Learning curve underestimated** in Phase B and C — Zeek, ICSNPP, the 62443 vocabulary, designing a FAT test that would catch something | 4 | 4 | **16** | C2, C3 and C4 deliberately under-loaded against 70 h capacity. Spend headroom on depth, never on pulling work forward | M1, M2 |
| R-04 | **Documentation over-engineering.** The Sprint 0 top risk, and the one most likely to be indulged | 3 | 3 | 9 | Hard cut line: governance documents ≤ 2 pages. Assessment artifacts exempt — they are the deliverable | Every cycle |
| R-05 | **Cloud spend escapes the ceiling** | 2 | 5 | 10 | Structural, not behavioural: platforms that cannot bill, local persistent spine, `if: always()` teardown, FF-13 deny-list. See ADR-004 | Monthly |
| R-06 | **The heavy week is lost to the roster.** 56 of 70 hours sit in one week | 3 | 4 | 12 | Slip the cycle, never compress the next. Two consecutive losses triggers re-planning, not heroics | Every cycle |
| R-07 | **Oracle Always Free capacity unavailable** in ap-sydney-1 — "out of host capacity" is the normal response, not an error | 4 | 2 | 8 | Scripted retry. Fallback is fully local; the cost model already assumes this | S1 |
| R-08 | **A regulatory position dates.** SOCI definitions rules have been amended repeatedly since 2018 | 3 | 3 | 9 | ADR-006 is a reassessment trigger wherever relied upon, not a standing fact. Re-checked at M3 | M3 |
| R-09 | **Lab hardware failure.** The persistent spine is local, so a failed disk is a lost lab | 2 | 4 | 8 | The lab's own backup discipline becomes load-bearing — and testing it is itself a portfolio artifact | S1 |
| R-10 | **The 62443 work outpaces the cloud work**, leaving a portfolio strong in assurance and thin elsewhere | 3 | 2 | 6 | Accepted. M3 is the employment gate; breadth after it is secondary by design | M3 |

---

## Assumptions

**Assumptions are load-bearing. If one is false, whatever rests on it is wrong** — which is why each carries its consequence rather than just its status.

| # | Assumption | If false |
|---|---|---|
| A-01 | Standards Australia Reader Room covers AS IEC 62443 (terms say "selected standards"; library guidance says the whole catalogue) | **The highest-leverage unknown in the plan.** The standard text becomes inaccessible without paying, and the SR x.y mapping in the CRS cannot be completed |
| A-02 | An Australian can register for the CISA virtual learning portal | Free ICS training path closes; substitute with ISAGCA and vendor material |
| A-03 | 23.3 h/week average is sustainable for ten months | The programme is re-planned at 30 sprints, not compressed |
| A-04 | The simulated plant's protocols are realistic enough for the visibility work at S6 to see traffic worth parsing | S6's value drops sharply, and ADR-003's fidelity limitation widens |
| A-05 | Free tiers persist for the programme's duration | Cost model is re-run. The local-first design is what limits the blast radius |

---

## Issues

*(An issue is a risk that has occurred. None open at Sprint 0.)*

| # | Issue | Raised | Owner | Status |
|---|---|---|---|---|
| — | — | — | — | — |

---

## Dependencies

| # | Depends on | Needed by | Status |
|---|---|---|---|
| D-01 | Standards Australia Reader Room token (3/year, 24 h each, Australian mobile required) | S7 · already consumed once for the hydro assessment | **Open — verify A-01 first** |
| D-02 | Oracle Cloud Always Free tenancy in ap-sydney-1 | S1 | Open |
| D-03 | GitHub Actions OIDC trust configured in all three clouds | S1 | Open |
| D-04 | MITRE ATT&CK for ICS current content version | S8 | Rolling — **technique IDs are version-sensitive and must be verified against the live matrix, never recalled** |
| D-05 | AESCSF v2 (2023 Core) practice set | S2, S11 | Open |

> **D-04 is written that way because it has already gone wrong once.** Technique IDs recalled from memory during the hydro assessment were obsolete — T0855, T0856, T0803, T0804, T0857, T0839 and T0891 are superseded in the current matrix. Verified against the live source before use, and the correction is recorded in the workbook.

---

*LIMEN-GOV-002 rev 1.0 · Sprint 0 · Gate M0*
