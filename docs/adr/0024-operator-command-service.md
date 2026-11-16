# ADR-024 — Operator commands go through a command service that authorises, audits and tracks them

**Status:** Proposed (drafted 16 November 2026, nothing built) · **Deciders:** E. Zaré
**Related:** ADR-005 (unidirectional boundary, four conditions for a write path) · ADR-008 (identity authority) · ADR-017 (accounts are attribution, not authorisation) · ADR-023 (cell firewall, F9) · risk R-14 · `docs/architecture/dmz-target.md` §7 · **Sprint:** 8 (not S5)

> Draft. Choices marked **(to confirm)** are proposals. The open questions at the end block acceptance. Nothing here changes S5: F9 stays as ADR-023 describes it.

---

## Context

The operator command path (F9) today is FUXA's own OPC UA client writing `StartCommand`, `StopCommand` and the `Fault*` tags through `fw-cell` to the gateway, with the shared account `engineer`. `fw-cell` filters by source address and port, not by node or value.

Four properties are missing, and they are different problems:

| Property | State today |
|---|---|
| Who: the person is known to OT | No. OT sees the shared account (ADR-017, R-14) |
| May they: authorisation per command and role | No. Any authenticated session may write every writable node |
| What happened: audit | No record of command, person, time, result. `fw-cell` counts flows only |
| Did it work: command state | No. The level is written; the result is read from the lamps |

## Decision (proposed)

1. **A command service sits between the HMI and `fw-cell`.** It is the only F9 source; `scada` is no longer allowed through `fw-cell`.
2. **It authenticates the operator** through the identity authority of ADR-008 *(to confirm: how the HMI passes the identity; not tested)*.
3. **It authorises by role and command** from a committed table. Fault-injection tags are not offered in any production profile.
4. **It validates** the command (allow-list, preconditions, rate limit) and writes the OPC UA node itself with a service account.
5. **It records every command, accepted or refused,** in an append-only table in the historian (person, command, time, outcome), with the same trigger approach as `alarm_event`.
6. **It tracks command state**: requested, accepted, executed, refused, timed out, with the feedback tags as evidence of execution.
7. **Audit and state are not stored in the SCADA.** A compromisable component cannot hold the evidence about itself.

## Alternatives

- **A. Leave F9 as is** (HMI writes with a shared account). Cheapest, and what S5 does. Repudiation (R-14) stays open.
- **B. OPC UA roles on the server** (ADR-023 point 7, secure channel with per-identity roles). No new container. *Not verified:* whether the OPC UA library supports permissions per node and per role. Needs a short test before choosing.
- **C. Gateway-side write log** (account, node, value). Cheap and useful as evidence, but the account is still shared, so it does not answer "who".

## Consequences

**Positive.** A compromised HMI can no longer write by itself. Each of the four properties maps to a test with a negative step.

**Negative.** One more container and one more place to fail. FUXA would call the service over a different interface than its native OPC UA write; *whether FUXA can do this cleanly (scripts or an HTTP device) is not checked.* More work in a sprint that is already loaded.

**Limits to state in the gate report.** The lab has one author for the operator, the service and the tests. Identity strength cannot be proven in a Docker lab.

## Open questions (block acceptance)

- **Q1.** Command service (this ADR) or OPC UA roles (alternative B)? Decide after the role test.
- **Q2.** Can FUXA call the service? Test before any commitment.
- **Q3.** Which identity does the operator present, and where does the lab get it?
- **Q4.** Command allow-list and preconditions (start while the horn runs, stop while tripped): source them from the PLC logic, not from this ADR.

---

*VIGILIMEN-ADR-024 · Sprint 8 · proposed*
