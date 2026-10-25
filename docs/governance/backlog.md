# Backlog — epics and MoSCoW cut lines

**Ref:** VIGILIMEN-GOV-003 · **Rev:** 1.0 · **Date:** 14 September 2026

---

## How the cut line works

MoSCoW fails when Must-have is set to everything anyone wants. The rule that makes it work:

> **Must-have is capped at 60% of the sprint's hours. The remaining 40% is where the estimate is allowed to be wrong.**

A sprint whose Must-have list fills the available time has no slack, so the first surprise consumes a Should-have that was never negotiated. Capping it means the cut is decided at planning, by someone with time to think, rather than at the deadline by someone who is tired.

**The cut line is set at sprint planning and is not renegotiated at the deadline.** That is the whole discipline. Moving it later is how a programme discovers in month eight that it has been running at 100% Must-have since month two.

---

## Epics

| # | Epic | Sprints | Gate |
|---|---|---|---|
| E-1 | Governance and regulatory frame | S0–S2 | M0 |
| E-2 | The OT world — plant, protocols, protective function | S3–S5 | M1 |
| **E-3** | **OT security assurance** | **S6–S11** | **M2, M3** |
| E-4 | Industrial data plane | S12–S14 | M4 |
| E-5 | Enterprise work management | S15–S18 | M5 |
| E-6 | Machine intelligence | S19–S21 | M6 |
| E-7 | Enterprise experience | S22–S23 | M7 |
| E-8 | Production hardening and the OT SOC | S24–S27 | M8 |
| E-9 | Showcase | S28–S29 | M9 |

**E-3 is the flagship and carries six of thirty sprints.** Every other epic exists to give it something real to assure — a plant that can be attacked, a boundary that can be crossed, a supply chain that can be specified. An assurance programme over nothing is a template.

---

## Sprint 0 — the cut applied

20 hours. Must-have capped at 12.

| Item | MoSCoW | h |
|---|---|---|
| Programme charter | **Must** | 2 |
| Architecture characteristics worksheet + rationale | **Must** | 3 |
| ADR-001…005 | **Must** | 4 |
| **ADR-006 — regulatory applicability** | **Must** | 2 |
| RAID log seeded by risk storming | **Must** | 1 |
| Monorepo scaffold, PR template with ADR checkbox | Should | 2 |
| C4 Level-1 system context, OT arrow unidirectional | Should | 2 |
| Backlog: epics and cut lines | Should | 1 |
| Wardley map for build-vs-buy | Could | 2 |
| Branch protection and CI skeleton | Could | 1 |
| *A CONTRIBUTING guide, an issue template, a docs site* | **Won't** | — |

**Must = 12 h of 20. The cap holds.**

> **The Won't row is not filler.** The Sprint 0 top risk is documentation over-engineering, and the natural response to a governance sprint is to produce more governance. Writing down what is deliberately not being built is the control — and a docs site for a repository one person reads is the exact shape that risk takes.

---

## Standing cut lines

Applied at every sprint unless an ADR overrides.

| Cut | Rule |
|---|---|
| **Documentation** | Governance documents ≤ 2 pages. Assessment and specification artifacts are exempt — they are the deliverable, not the overhead |
| **Cloud** | No persistent cloud resource. Anything billable lives inside a scripted apply → evidence → destroy window (ADR-004) |
| **Scope** | One site, one plant, one user. Multi-site and multi-tenant are Won't for the whole programme |
| **Tooling** | Prefer a permissively licensed tool over a better one with a restrictive licence, where the restriction would ever need discussing |
| **Demos** | One recording per sprint, ≤ 5 minutes, produced in the sprint it documents. A demo recorded later is a demo of a memory |

---

## Definition of done — every sprint

1. Artifacts merged by PR, with the ADR checkbox answered
2. Any new fitness function running in CI and **capable of failing the build**
3. No new persistent cloud resource
4. RAID log updated — including risks that **closed**, which is the half that gets forgotten
5. Demo recorded
6. Tracker updated with actual hours against planned

**Item 6 is what makes the plan honest.** A plan never compared against actuals is a wish, and the comparison is only useful if the number recorded is the one that happened.

---

*VIGILIMEN-GOV-003 rev 1.0 · Sprint 0 · Gate M0*
