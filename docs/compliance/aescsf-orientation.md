# AESCSF — orientation

**Ref:** VIGILIMEN-CMP-002 · **Rev:** 1.0 · **Date:** 14 September 2026 (AEST)
**Why this exists:** ADR-009 nominates AESCSF 2023 Framework Core at SP-2. This is the one page that makes the framework usable before the assessment starts at S11.

---

## What it is

The **Australian Energy Sector Cyber Security Framework**, maintained by AEMO. It descends from the US **C2M2** with **NIST CSF** structure folded in, then calibrated for Australian energy — which is why choosing it does not forfeit C2M2 (ADR-009).

It is on the CIRMP approved-framework table. **IEC 62443 is not**, which is the whole reason this document exists rather than an ISA one.

---

## The two axes, and why confusing them ruins a report

This is the distinction the framework is most often got wrong on, and it is a standard interview probe.

| | **Maturity Indicator Level** | **Security Profile** |
|---|---|---|
| Range | MIL 0–3 | SP-1, SP-2, SP-3 |
| Assessed | **Independently, per domain** | **Collectively, across all domains** |
| Describes | How *institutionalised* a practice is — performed, documented, managed, measured | Which *set of practices* is in scope |
| Practice count | — | SP-1 ≈ 109 · **SP-2 ≈ 239** · SP-3 ≈ 312 |
| Answers | "How reliably do we do this?" | "How much are we expected to do?" |

**MIL is depth. SP is breadth.** An organisation can be MIL 3 in Risk Management and MIL 1 in Supply Chain, because MILs are per-domain — and that unevenness is information, not an error to average away.

> **Two traps worth holding separately.**
>
> **MIL is not SL.** Maturity level and IEC 62443 *security level* have no relationship whatsoever. ML describes how institutionalised a process is; SL describes what attacker capability a system withstands. An organisation at MIL 3 can operate a zone at SL 1, and often does — mature processes reliably delivering a weak architecture.
>
> **MIL is not a score to maximise.** MIL 3 across every domain is neither required nor sensible. SP-2 defines what is expected; pushing a domain past it spends effort that another domain needs more.

---

## The eleven domains

| | Domain | What it asks |
|---|---|---|
| **RM** | Risk Management | Is there a cyber risk programme, and does it reach the board? |
| **ACM** | Asset, Change and Configuration Management | Do you know what you have, and does it change under control? |
| **IAM** | Identity and Access Management | Who can do what, and how is that revoked? |
| **TVM** | Threat and Vulnerability Management | Do you know what is coming, and what you are exposed to? |
| **SA** | Situational Awareness | Can you see the estate, and would you notice? |
| **IR** | Information Sharing and Communications | Do you receive and contribute threat information? |
| **ER** | Event and Incident Response, Continuity of Operations | Can you respond, and keep operating? |
| **SCM** | Supply Chain and External Dependencies | Are your suppliers a risk you have assessed? |
| **WM** | Workforce Management | Are the people vetted, trained and accountable? |
| **CPM** | Cybersecurity Program Management | Is there a programme, funded and governed? |
| **AM** | Australian Privacy Management | Are privacy obligations met? |

**AM is the Australian addition** and is the visible sign that this is not simply a re-badged C2M2.

### Where this programme's existing work already lands

| Artifact | Domain |
|---|---|
| The 62443-3-2 assessment and CRS | RM, ACM, TVM |
| The zone and conduit partition | ACM, SA |
| Brokered vendor access, ADR-007, ADR-008 | IAM, SCM |
| The FAT / SAT / cutover set | ACM, SCM, WM |
| Malcolm, Zeek, the OT SOC (S6, S24) | SA, TVM |
| Incident response and tabletop (S11) | ER, IR |

Six of eleven domains already have evidence before the assessment begins. **SCM is the domain the 62443-2-4 procurement work feeds**, and it is the one most organisations score worst on.

---

## The 42 anti-patterns

The part of AESCSF that nothing else has, and the reason to prefer it in a room full of people who have read ISO 27001.

They are scored **present or not present** — not by maturity — and they describe **how organisations actually fail** rather than what they should do. A control checklist asks "do you have X?". An anti-pattern asks "are you doing the thing that makes X useless?", which is a far better question and a much harder one to answer flatteringly.

Examples of the shape (illustrative, not quoted from the framework):

- A risk register that exists and is never read by anyone who can fund a treatment
- Asset inventory maintained by a spreadsheet that one person updates from memory
- Vendor access granted permanently because the approval process is slower than the outage
- Backups that run reliably and have never been restored

**Every one of those is a finding this programme has already produced independently** — the treatment-ordering problem in the ZCR 5 register, the standing vendor access in the hydro assessment, the untested restoration in both halves of the Essential Eight scorecard. That convergence is the argument for the anti-patterns: they find what a maturity score hides.

---

## What the assessment at S11 must produce

1. **MIL per domain** — eleven ratings, assessed independently, with the unevenness preserved rather than smoothed
2. **SP-2 practice coverage** — 239 practices, in scope or justified out
3. **Anti-pattern scoring** — 42, present or not present
4. **The 62443 mapping** — which CRS requirement evidences which AESCSF practice. *This is the artifact that makes ADR-009's "map 62443 underneath" real rather than a claim*
5. **The honest gaps**, including the Essential Eight mitigations the OT estate cannot reach

> **Verification note.** The domain list, the MIL/SP structure and the 42 anti-patterns are recorded here from secondary knowledge of AESCSF v2 (2023 Core). **The practice counts and the domain abbreviations must be confirmed against AEMO's published framework before any of this is used externally.** The structure is what matters for orientation; the numbers are what will be wrong if anything is.

---

*VIGILIMEN-CMP-002 rev 1.0 · Sprint 2 · Assessment proper at S11*
