# ADR-007 — Federated identity only. No static cloud credential exists.

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré
**Related:** ADR-001 (three clouds), ADR-004 (cost by construction)

---

## Context

CI must reach three clouds. The default answer is to store an access key, a client secret and a service account JSON in the repository's secrets, and every one of those is a long-lived credential with the blast radius of the role behind it.

Long-lived credentials in CI have a specific failure mode: they do not leak dramatically, they **accumulate**. Rotation is deferred because rotation breaks builds, the key outlives the person who created it, and nobody can say which of four keys the pipeline actually uses.

---

## Decision

**Every cloud authentication is federated via OIDC, with no static credential stored anywhere.**

| Cloud | Mechanism |
|---|---|
| AWS | GitHub OIDC provider → IAM role, assumed with a 1-hour session |
| Azure | Workload identity federation → app registration, no client secret |
| GCP | Workload Identity Federation → service account impersonation, no key file |

The trust policy on each side is scoped to **this repository and a named branch or environment**. A fork cannot assume the role; nor can a workflow on a branch outside the trust condition.

Role ARNs, tenant ids and provider paths are stored as `vars`, **not** `secrets`. There is nothing secret about an identifier, and storing it as a secret only makes it harder to review — which quietly trains everyone to treat the secrets list as noise.

**FF-03 fails the build** on any static credential shape in the tree, and — more usefully — on any workflow that authenticates to a cloud **without requesting an OIDC token**. The absence of a secret is not proof that federation is configured; a workflow that silently lost `id-token: write` would fall back to whatever is in the environment, and that is the case worth catching.

---

## Why not a policy engine for this, and for FF-13

Conftest and Rego are the industry answer for policy-as-code, and this programme uses a tested Python check instead. The reason is worth recording rather than left to look like ignorance.

**A policy you cannot run locally is a policy you cannot test.** The deny-list in FF-13 carries eleven test cases, several of which exist because they are ways the check could pass when it should not — a replacement that reads as `["delete","create"]`, an `allow_when` attribute that is simply absent. Those cases were written first and two of them failed before the implementation was right.

Rego would not have made the rules better; it would have made them harder to prove. **When the Terraform pipeline is real and conftest runs in CI against a genuine plan, this is revisited** — and the migration is cheap precisely because the rules live in `deny-list.yml` as data rather than in the checker as code.

---

## Consequences

**Positive.** No credential to rotate, leak or inherit. Sessions last one hour and are scoped to one repository. Revocation is a trust-policy edit, not a key hunt. The claim "there are no static credentials in this programme" is enforced rather than asserted.

**Negative.** Three federation configurations to set up, each with its own vocabulary for the same idea, and each failing in its own unhelpful way on a mistyped subject claim. **This is genuinely the fiddliest part of Sprint 1**, and the failure mode is a trust condition that is too broad rather than too narrow — which is invisible until someone tests it.

**Therefore:** the trust policies are themselves reviewed as an artifact, and `verify_empty.sh` runs after every evidence window so a role that was over-scoped shows up as something left behind rather than as nothing at all.

---

*MINED-ADR-007 · Sprint 1*
