# Programme Charter — MineDigital

**Ref:** MINED-GOV-001 · **Rev:** 1.0 · **Date:** 14 September 2026 · **Owner:** Epiphane Zaré

---

## Why this exists

A mining operation runs two worlds that do not speak to each other. The plant floor measures, moves and protects; the enterprise plans, procures and reports. Between them sits a gap that gets crossed by spreadsheets, phone calls and a radio.

MineDigital closes that gap **as an engineered system rather than an integration project**, on the terms the plant floor sets rather than the terms the enterprise would prefer: safety first, then availability, then integrity, then confidentiality.

It is built as a portfolio: one engineer, a real cadence, no client. That is a constraint on scale, not on rigour — the artifacts are the ones a real programme would produce, and they are defended the way a real programme would have to defend them.

---

## Scope

**In.** A simulated mining plant — conveyor, crusher, dewatering, and their protective functions — on vendor-realistic industrial protocols. OT network visibility. An IEC 62443-3-2 assurance programme over it. An industrial data plane on AWS, an enterprise work-management plane on Azure, an analytics and machine-learning plane on GCP. An OT security operations capability spanning both worlds.

**Out, and deliberately.**

| Out of scope | Why |
|---|---|
| Real OT hardware | A simulated plant can be attacked, broken and rebuilt. Real hardware cannot, and would consume the budget |
| Production data of any kind | There is no client. Synthetic data is not a limitation here, it is the correct choice |
| Vendor-specific certification paths | ISA IC32 at US$2,160 exceeds the entire cloud budget fourteen times over. Deferred until an employer funds it |
| A mobile application | Adds surface, proves nothing this programme does not already prove |
| Multi-site / multi-tenant | One site, modelled honestly, beats three modelled thinly |

---

## Success criteria

The programme succeeds if all four hold. Three of four is a partial result and should be reported as one.

| # | Criterion | Measured by |
|---|---|---|
| S-1 | The OT security dossier is defensible to a practitioner, not merely complete | A 62443-literate reviewer can contest a position and find the counter-argument already written down |
| S-2 | Every architectural decision has a written rationale and a stated consequence | ≥ 30 ADRs merged; no undocumented structural decision |
| S-3 | Architectural intent is enforced by machinery, not by memory | ≥ 16 fitness functions running in CI and failing builds |
| S-4 | Total programme spend stays under **US$333** | Monthly cost report; US$0 in non-evidence months |

**S-4 is a design constraint, not a budget line.** A programme that needs discipline to stay cheap will not stay cheap. Cost control is structural: platforms that cannot bill, persistent workload local, real cloud touched only inside a scripted apply-evidence-destroy window.

---

## Governance

| | |
|---|---|
| **Cadence** | 3-week roster cycle: 56 h in week 1, 7 h in each of weeks 2–3. **70 h per cycle, 23.3 h/week average** |
| **Heavy week** | Building, deploying, debugging, attacking, testing, and the first draft of every large document — anything that can fail unexpectedly |
| **Light fortnight** | Incremental completion only. One ADR, one batch of register rows, one section. **One hour a day cannot do flow work** |
| **Slip rule** | A lost heavy week is a lost cycle. Slip the cycle; never compress the next. Two consecutive losses triggers re-planning |
| **Decision record** | Every structural decision becomes an ADR in Nygard format, merged by PR |
| **Gates** | M0–M9. A gate is passed or it is not; there is no partial gate |

---

## The ten gates

| Gate | At | When | What it establishes |
|---|---|---|---|
| M0 | S0 | late Oct 26 | Governance exists |
| M1 | S5 | early Dec 26 | The OT world is alive; vendor access is controlled |
| M2 | S6 | early Dec 26 | The plant is visible |
| **M3** | **S11** | **early Feb 27** | **The OT security dossier — the employment gate** |
| M4 | S14 | late Feb 27 | Telemetry lands in AWS |
| M5 | S18 | mid Apr 27 | The walking skeleton connects all three planes |
| M6 | S21 | early May 27 | Machine intelligence |
| M7 | S23 | early May 27 | Enterprise experience |
| M8 | S27 | mid Jun 27 | Production-hardened |
| M9 | S29 | mid Jun 27 | Showcase |

**M3 carries different weight from the others.** It is the point at which the programme has produced something that changes what the author can be hired to do. Everything after it is portfolio breadth; everything up to it is the argument.

---

## Top programme risks at inception

Seeded from the first risk-storming pass. Full register: `governance/raid-log.md`.

| # | Risk | Response |
|---|---|---|
| R-01 | Scope inflation — three clouds is already ambitious for one engineer | MoSCoW cut lines per sprint, applied at planning not at the deadline |
| R-02 | Documentation over-engineering | **Cut line: every governance document ≤ 2 pages.** Assessment artifacts are exempt; charters are not |
| R-03 | Learning curve underestimated in Phase B and C | C2, C3, C4 deliberately under-loaded against capacity |
| R-04 | Cloud spend escapes | Structural, not behavioural — see S-4 |
| R-05 | The heavy week is lost to the roster | Slip rule; two losses triggers re-planning |

---

## What this charter is not

It is not a commitment to anyone. There is no client, no sponsor and no delivery date anybody is waiting on. **That makes the gates the only thing preventing indefinite polishing**, which is the real failure mode of a solo portfolio programme — not abandonment, but an assessment that is still being improved in March.

---

*MINED-GOV-001 rev 1.0 · Sprint 0 · Gate M0*
