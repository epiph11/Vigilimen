# ADR-004 — Cost control by construction, not by discipline

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré
**Supersedes:** the v1.0 teardown-discipline approach

---

## Context

The programme has a hard ceiling of **US$333** across ten months, against a naive build cost of roughly **US$3,700**.

The obvious answer is to stop resources when they are not in use. That answer was adopted in v1.0 and then rejected, because it depends on a human remembering — and the failure mode of cost discipline is not laziness, it is a busy week. One forgotten NAT gateway, one managed Kafka cluster left running over a roster break, and the ceiling is gone with no way to recover it.

> **Any cost control that requires the operator to do something is a cost control that will eventually not happen.**

---

## Decision

**Remove the human from the loop entirely.** Three mechanisms, in order of preference.

### 1. Platforms that cannot bill

Preferred wherever they suffice. A platform with **no card on file and no overage path** cannot produce a surprise. Cloudflare's free tier is the model: it stops rather than charges. Oracle Cloud Always Free carries the persistent Linux workload, and the lab's own continuous activity defeats the idle-reclamation policy as a side effect of doing its job.

### 2. The persistent spine is local

Everything that must run continuously — the simulated plant, the historian, network visibility, the OT SOC — runs on local and always-free infrastructure. **History accumulates in TimescaleDB, not in a managed cloud service billed by the hour.** This is the single largest saving in the model, and it is structural: there is nothing to forget to turn off.

### 3. Real cloud is entered only inside a scripted window

Where a sprint must demonstrate a genuine managed service, it runs as one GitHub Actions job:

```
workflow_dispatch → OIDC → terraform apply → capture evidence → terraform destroy
                                                    ↓
                                    cloud-nuke in  if: always()
```

The destroy is **not conditional on success**. A failed apply, a cancelled run, a timeout — every path reaches teardown, because the teardown sits in `if: always()` and a sweeper runs behind it. The evidence — screenshots, logs, exported configuration — is what persists in the repo. The infrastructure does not.

**FF-13** fails the build if a Terraform plan proposes anything on the never-create list: Front Door, APIM Developer tier and above, Managed HSM, Fabric capacity, SageMaker real-time endpoints, Kinesis streams. Those are the resources that bill by existing rather than by being used, and the deny-list is the only control that catches them before the money is spent.

---

## Consequences

**Positive.** US$3,708 → **US$13–333**. Zero idle spend by construction. No monthly reconciliation ritual. A forgotten resource cannot survive a workflow run.

**Negative.** Local infrastructure is the author's to operate — a failed disk is a lost lab, so the lab's own backup discipline becomes load-bearing. Cloud demonstrations are shorter and must be scripted in advance, which costs preparation time and forbids casual exploration. **Some things genuinely cannot be demonstrated this way**, and where that is true the artifact says so rather than faking it.

**The non-cloud cost dominated anyway.** ISA IC32 at US$2,160 exceeds the entire cloud budget fourteen times over. It is deferred until an employer funds it, with a free substitute path: Standards Australia Reader Room tokens, ISAGCA whitepapers, the CISA virtual learning portal. Getting the cloud bill to zero while paying two thousand dollars for a certificate would have been optimising the wrong number.

---

*VIGILIMEN-ADR-004 · Sprint 0 · Gate M0*
