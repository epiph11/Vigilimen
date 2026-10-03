# ADR-002 — A modular monolith for the enterprise plane, not microservices

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré

---

## Context

The Azure enterprise plane carries work management, the asset domain, scheduling and the technician experience. The default shape for a system like this in 2026 is microservices, and the default is frequently wrong.

Microservices buy **independent deployability** and **independent scalability**. They are paid for in distributed transactions, network failure modes, eventual consistency, operational surface and debugging that crosses process boundaries.

---

## Decision

**A modular monolith with bounded contexts enforced at build time**, deployed as a single unit.

Contexts — Asset, Work, Scheduling, Personnel — communicate through explicit published interfaces. A fitness function in CI **fails the build** if one context imports another's internals. The module boundaries are therefore real, not conventional.

---

## Reasoning

Look at what microservices are actually for, against what this system actually has:

| What microservices buy | Does this system need it? |
|---|---|
| Independent deployability across teams | **One engineer.** There is no team boundary to align to a service boundary |
| Independent scalability per service | **One site, one user.** Scalability was explicitly rejected as a driver (LIMEN-ARC-001 §3) |
| Fault isolation | Real. Achievable in-process at this size, and cheaper |
| Technology heterogeneity | Not needed. One language serves the whole plane |

Conway's law works in both directions: a service topology that does not match a team topology creates coordination cost without the autonomy that pays for it. **With one engineer, every service boundary is pure overhead.**

---

## The part that matters

**The module boundaries are drawn so that extraction is possible later.** If Work Management ever needs independent deployment, it comes out as a service because its boundary was already a real one.

This is the point Fowler and Richards both make and that gets ignored: *you cannot decompose a system whose boundaries were never enforced.* A monolith with disciplined internal boundaries can become microservices. A distributed system with confused boundaries can only become a distributed mess. **Starting monolithic is not the conservative choice — it is the choice that keeps the other one available.**

---

## Consequences

**Positive.** One deployment, one debugger, one transaction scope. Boundaries enforced by machinery rather than by review. Extraction remains possible.

**Negative.** A single scaling unit and a single failure domain. The temptation to reach across a boundary "just this once" is constant, which is precisely why the check is in CI and not in a code review checklist.

**Revisit if:** a context genuinely needs an independent release cadence or an independent scaling profile. Neither condition exists in this programme, and if one appears it is a finding worth writing down rather than a reason to have started differently.

---

*LIMEN-ADR-002 · Sprint 0 · Gate M0*
