# Environment strategy

**Ref:** LIMEN-ARC-003 · **Rev:** 1.0 · **Date:** 14 September 2026

---

## There are three environments, and only one of them is in a cloud

| Environment | Where | Lifetime | What it is for |
|---|---|---|---|
| **`local`** | The author's machine and Oracle Always Free | **Permanent** | The simulated plant, the historian, network visibility, the OT SOC. Everything that must keep running |
| **`ci`** | GitHub Actions runners | Minutes | Fitness functions, `terraform validate`, policy checks. Touches no cloud account |
| **`evidence`** | Real AWS, Azure or GCP | **One workflow run** | Demonstrating a genuine managed service, capturing proof, and then ceasing to exist |

This is the usual dev/test/prod ladder turned on its side, and the reason is ADR-004: **the persistent environment is the cheap one, and the expensive one is not persistent.** A conventional ladder would have three long-lived cloud environments and a budget three times over.

---

## What `evidence` means

An evidence environment is not a short-lived dev environment. It is **a demonstration that produces a document.**

```
dispatch → OIDC → plan → FF-13 → apply → capture → destroy → sweep → verify
```

What persists is `evidence/<cloud>/<timestamp>/` — the plan, the state as applied, the outputs, and a record naming the run, the commit and what it was proving. The infrastructure does not persist, and the record says so explicitly so that a reader of the repository is never misled about what is running.

**Nothing depends on an evidence environment.** No other stack reads its outputs, no demo points at its endpoints, and no document links to a live URL in it. A dependency on something that exists for forty minutes is a dependency that is broken by definition, and building one is how a "temporary" environment becomes permanent.

---

## Promotion

There is no promotion path, and that is the decision rather than an omission.

Code does not move from `evidence` to anywhere; `evidence` exists to prove that code works against the real service, and then the code is what is kept. **The artifact of a cloud demonstration is a document, not a deployment.**

The one thing that does promote is the **module**: a Terraform module proven inside an evidence window is tagged and reused, and the evidence record is the reason it can be trusted.

---

## State

| Environment | State backend |
|---|---|
| `local` | Local file, committed nowhere, backed up with the lab |
| `ci` | None — `terraform init -backend=false`, validation only |
| `evidence` | Remote per cloud: S3 + DynamoDB lock · Azure Storage · GCS |

**Remote state is the one persistent cloud resource the programme allows**, and it is deliberate. A state bucket costs cents per month, and the alternative — no remote state — means a cancelled workflow run orphans infrastructure with no record of what it created. **The cheapest possible teardown is one that knows what to tear down.**

State buckets are therefore *not* on the FF-13 deny-list, and this paragraph is why.

---

## Naming and tagging

Everything created in an evidence window carries `limen-ephemeral=true`, applied through the provider's `default_tags` rather than per resource, so it cannot be forgotten. The sweep and the verification both key off that tag.

```
limen-<cloud>-<stack>-<resource>        e.g. limen-aws-telemetry-ingest-bucket
```

Region is `ap-southeast-2` / `australiaeast` / `australia-southeast1` throughout. Data residency is not a requirement of this programme, but it is a requirement of the sector it models, and modelling it costs nothing.

---

## Time

**Machines write UTC. People read `Australia/Brisbane`, labelled AEST.** ADR-010.

Brisbane is UTC+10 all year and has no daylight saving, so a cron schedule means the same thing in June as in December — a schedule written in a DST zone silently moves twice a year, and a job near midnight crosses a date boundary when it does.

| | Zone | Example |
|---|---|---|
| Stored — logs, evidence records, state, filenames | **UTC**, ISO 8601 with an explicit `Z` | `2026-09-14T04:22:07Z` |
| Displayed — dashboards, reports, the tracker | **Australia/Brisbane**, labelled | `14 Sep 2026 14:22 AEST` |

Conversion happens at the presentation layer and nowhere else. **No stored value is ever in local time.**

> **Region is not timezone.** All three clouds stay in Sydney, because region is chosen for latency, service availability and data residency — none of which has anything to do with what a clock displays. Conflating the two is how this decision gets reversed by accident.

---

*LIMEN-ARC-003 rev 1.0 · Sprint 1*
