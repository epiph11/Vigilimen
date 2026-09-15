# Architecture Characteristics Worksheet

**Ref:** MD360-ARC-001 · **Rev:** 1.0 · **Date:** 14 September 2026
**Method:** Mark Richards / Neal Ford — *Fundamentals of Software Architecture*

---

## How this worksheet is used

Architecture characteristics are the *-ilities* a system must exhibit. The method has one rule that makes it useful:

> **Never choose more than three driving characteristics.**

Not because a system cannot exhibit more, but because a driving characteristic is one you will **sacrifice another characteristic for**. A list of seven priorities is a list of none, and it produces an architecture that is mediocre at everything because nothing was ever traded away.

The discipline is to write down what you gave up. Section 4 is the part of this worksheet that does the work.

---

## 1. Candidates considered

| Characteristic | Relevance | Driver? |
|---|---|---|
| **Safety** | A control action can injure someone. This is not a software concern borrowed from elsewhere — it is the reason the plant floor has different rules | **Driving** |
| **Security** | Critical-infrastructure-adjacent OT. The whole assurance programme sits here | **Driving** |
| **Availability** | A stopped plant is lost production. In OT the ordering is safety → availability → integrity → confidentiality | **Driving** |
| Data integrity | A wrong sensor value is worse than a missing one, because it is acted upon | Supporting |
| Evolvability | A 30-sprint programme across three clouds will change shape | Supporting |
| Observability | Cannot secure or operate what cannot be seen | Supporting |
| Testability | Fitness functions need something to run against | Supporting |
| Interoperability | Industrial protocols, three clouds, vendor tooling | Supporting |
| Cost efficiency | A hard US$333 constraint | Constraint, not characteristic |
| Scalability | One site, one plant, one user | **Explicitly not a driver** |
| Elasticity | No demand spikes exist to absorb | **Explicitly not a driver** |
| Performance | Sub-second is not required anywhere in this system | **Explicitly not a driver** |

---

## 2. The three drivers

### Safety
Any function whose failure can injure a person is architecturally separate from any function that can be reached from a network. **No security control may sit in the trip path of a protective function** — a control that can fail closed on a protection or safety function has made the plant less safe, not more. This is carried as a hard constraint everywhere, and it is the direct lesson of TRITON.

### Security
The system is designed to withstand an adversary with IACS-specific skills and moderate resources — **SL 3** in IEC 62443 terms, at the zones where consequence justifies it. Security level is defined by attacker capability, not by control count.

### Availability
Continuity of operation outranks confidentiality throughout. Where a security control and continuity conflict, the conflict is **escalated, never resolved unilaterally in favour of the control**. Controls fail in the direction that preserves safe operation.

---

## 3. Why scalability and performance were rejected

They are the characteristics a cloud architect reaches for by habit, and neither is a driver here.

**Scalability** is the ability to handle more load. There is one plant, one site and one user. Designing for horizontal scale would produce a distributed architecture whose complexity buys nothing, and the cost of that complexity would be paid in evolvability — the characteristic that actually matters over thirty sprints.

**Performance** matters at the millisecond scale inside the control loop, and the control loop is not in this system. Everything in scope tolerates seconds. Optimising it would trade away simplicity for a property nobody can perceive.

**Stating a non-driver is as much of a decision as stating a driver**, and it is the one that gets omitted. An architecture with no rejected characteristics was not designed; it was accumulated.

---

## 4. What each driver costs

This is the section that makes the worksheet real. Every driver is paid for.

| Driver | What it costs |
|---|---|
| **Safety** | Duplicated hardware paths that a purely software design would consolidate. Protective functions that cannot be monitored by anything that could also disable them. Slower change: a modification inside a protective function requires a witnessed test, not a deployment |
| **Security** | Segmentation the data flow does not otherwise need. Brokered access where a VPN would be simpler and cheaper. Named individual accounts and just-in-time approval where a shared credential would be faster for the people doing the work — and the friction is real, not theoretical |
| **Availability** | Redundancy that costs money and adds failure modes of its own. Change windows measured in outages rather than sprints. Patches that wait for vendor validation, which is the correct answer and an uncomfortable one |

### The trade-offs made explicitly

| We chose | Over | Because |
|---|---|---|
| Safety | Availability | A trip is recoverable; an injury is not. The hardwired protection stays outside every programmable path even though that guarantees nuisance trips |
| Availability | Confidentiality | Data disclosure is a bad day. A stopped plant is lost production and a safety event during restart |
| Security | Convenience | Brokered session access rather than network access, even though it is slower for the vendor on a Sunday night |
| Evolvability | Performance | Modular monolith rather than microservices — see ADR-002 |
| Cost | Operational convenience | Local-first infrastructure with cloud touched only inside a scripted window — see ADR-004 |

---

## 5. How these are enforced

A characteristic that is only written down is an aspiration. Each driver has machinery behind it, and the fitness functions arrive with the sprint that can first run them.

| Driver | Enforced by |
|---|---|
| Safety | Zone separation of protective functions; a CI check that no security control is defined inside a protection path; witnessed independence test at SAT |
| Security | SL-T assigned per zone at S7; SL-A reassessed against it annually — **the delta is the remediation backlog, and that loop is the point of assigning SL-T at all**; ATT&CK for ICS coverage measured at S8 |
| Availability | Chaos game-days at S26; the three-month independence proof; measured recovery time from an actual restoration, not an assumed one |

---

## 6. Review

Characteristics are re-examined at **M1, M3 and M5**. A driver that has not cost anything by its review point was not a driver — it was a preference, and it should be demoted so the list keeps its meaning.

---

*MD360-ARC-001 rev 1.0 · Sprint 0 · Gate M0*
