# ADR-008 — Entra ID is the identity authority for all three clouds

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré
**Related:** ADR-001 (three clouds) · ADR-007 (federation, no static credentials) · **Sprint:** 2

---

## Context

Three clouds means three native identity systems. Left alone, each grows its own users, its own groups and its own offboarding problem — and the offboarding problem is the one that matters: an account that exists in only one of three places is an account nobody remembers to remove.

ADR-007 settled how *machines* authenticate: federated OIDC, no stored credentials. This settles how *people* do.

---

## Decision

**Entra ID is the single identity authority.** AWS and GCP federate to it and hold no independent human identities.

| | How |
|---|---|
| AWS | Entra → IAM Identity Center via SAML; permission sets mapped from Entra groups |
| GCP | Entra → Cloud Identity via SAML; groups synchronised |
| Azure | Native |

**Authorisation stays local.** Entra says *who you are*; each cloud says *what you may do*. Pushing fine-grained cloud permissions into directory groups produces a directory nobody can read and a permissions model nobody can audit — the group name stops describing the person and starts describing a policy document.

### The baseline that comes with it

- MFA on every account, phishing-resistant for anything privileged
- Conditional access: block legacy authentication, require compliant or managed device for administrative roles
- Privileged roles are **eligible, not standing** — activated on request, time-boxed, logged
- Break-glass accounts excluded from conditional access, stored offline, monitored for any use at all

> **The break-glass exclusion is the one to be deliberate about.** An account exempt from conditional access is by definition the weakest account in the tenant, and it exists because a conditional access misconfiguration can otherwise lock every administrator out of the tenant that would fix it. The control is not the exclusion — it is that *any* authentication by that account raises an alert, every time, with no threshold.

---

## Why not per-cloud identity

It is simpler on day one and it fails at exactly one moment: when someone leaves. Three directories means three offboarding steps, and the third one is done by memory. **A single authority makes revocation one action**, which is the only property of an identity system that matters under pressure.

The counter-argument is real and is recorded: a single authority is a single point of failure, and an Entra outage locks all three clouds at once. That is mitigated by break-glass and accepted, because the alternative failure — an orphaned account in a cloud nobody audits — is silent, and silent failures are worse than loud ones.

---

## Consequences

**Positive.** One place to grant, one place to revoke, one audit trail for human access. Conditional access applies uniformly rather than three times with three dialects.

**Negative.** Entra becomes load-bearing for the whole programme, and its own configuration is now the highest-value target in it. SAML federation to AWS and GCP is fiddly and fails in unhelpful ways — the failure mode is an assertion attribute mismatch that reads as a generic authentication error.

**Relationship to ADR-007.** These are deliberately separate mechanisms. Human access goes through Entra; machine access goes through OIDC federation directly from the workflow and **does not touch Entra at all**. Routing CI through a human identity provider is how service accounts acquire mailboxes, MFA prompts and a person's name on an audit line — and how a build starts failing because someone's password expired.

---

*MINED-ADR-008 · Sprint 2*
