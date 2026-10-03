# ADR-001 — Three clouds, split by verb rather than by preference

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré

---

## Context

The programme spans industrial telemetry, enterprise work management and analytics. Each could be built on any of the three major clouds. Multicloud is usually an accident — an acquisition, a procurement decision, a team that liked something — and it usually costs more than it returns.

Choosing it deliberately requires a reason that survives the question *"why not just pick one?"*

---

## Decision

**Three clouds, each assigned a verb, with the boundary drawn where the data changes meaning.**

| Cloud | Verb | What it owns |
|---|---|---|
| **AWS** | **senses** | Industrial ingestion, asset models, time-series, the operational data lake |
| **Azure** | **acts** | Work management, the enterprise domain model, APIs, the technician experience |
| **GCP** | **learns** | The warehouse, cross-site data products, machine learning |

The split is not by workload size or by cost. It is by **what happens to the data**: a sensor reading becomes a measurement in AWS, becomes a work order in Azure, becomes a pattern in GCP. Each transition is a genuine change of meaning, and a boundary drawn at a change of meaning is a boundary that stays put.

---

## Alternatives

**Single cloud.** Simpler, cheaper in egress, one identity model, one skill set. Rejected for this programme specifically: the portfolio has to demonstrate multicloud competence, and a single-cloud build demonstrates one cloud. *This is a portfolio reason, and it is stated as one.* **On a real project with a real client, single cloud would be the correct default and this ADR would read the other way.**

**Two clouds.** Would work. Rejected because the third boundary — analytics — is the one where the strongest case for a different provider exists, and collapsing it would leave the multicloud claim resting on a single split.

---

## Consequences

**Positive.** Each boundary is justified by a change in the data's meaning rather than by convenience. Identity federation, cross-cloud OIDC and the integration layer become real problems with real solutions rather than diagrams. The walking skeleton at M5 has something genuine to connect.

**Negative.** Three identity models, three IaC dialects, three cost surfaces, three sets of service limits. Egress between them is a cost and a latency. Debugging crosses providers.

**Mitigation.** One Terraform codebase with three providers; OIDC federation with **zero static credentials anywhere** (ADR-007, S1); a single naming and tagging standard enforced by policy-as-code.

**The cost consequence is bounded by design, not by care.** The persistent spine is local; each cloud is entered only inside a scripted apply → evidence → destroy window (ADR-004).

---

*LIMEN-ADR-001 · Sprint 0 · Gate M0*
