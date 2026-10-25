# ADR-017 — The OPC UA accounts differ in attribution, not authorisation

**Status:** Accepted — as a known gap, to be attacked in S8 · **Date:** 25 October 2026 · **Deciders:** E. Zaré
**Related:** ADR-008 (identity authority) · ADR-012 · ADR-016 · risk R-14 · **Sprint:** 4

---

## Context

The gateway has two named accounts and refuses anonymous sessions. The collector uses `historian` and its header claimed that account *"holds no write access to any node"*. FUXA uses `engineer`, which needs to write `StartCommand` and `StopCommand`.

## Decision

**Record what is true: both accounts hold `UserRole.User`, and write permission is a property of the *node* (`set_writable()`), not of the account.** Every authenticated session can write every writable node.

| Node | Writable by `historian`? | By `engineer`? |
|---|---|---|
| `StartCommand`, `StopCommand` | **Yes** | Yes |
| `Fault*` (five) | **Yes** | Yes |
| measurements, `Plc*` status | No (read-only nodes) | No |

The two accounts therefore differ in **who the audit trail would blame**, which is attribution, and not in **what they may do**, which is authorisation.

## Reasoning

**How it got here.** The first design mapped `engineer` to asyncua's Admin role; Admin bypasses per-node access levels and could write `SafetyTripped`. The second added a custom permission ruleset and denied *every* write, including the legitimate ones, because the write list sits on `body.Parameters` and not on `body`; it was caught only because the contrast demo asserts that a *permitted* write succeeds. What shipped is the version that works and says less.

**Why it is not fixed now.** A per-account node allow-list belongs in the identity authority (ADR-008), not in a role enum inside one server. Writing one into the demo server would produce a fix that looks like the real thing and is not.

## Consequences

**Positive.** The claim is now accurate, and the contrast demo still checks both directions.

**Negative, and the point.** A compromised collector can start the conveyor and inject faults. The collector's own file claimed otherwise and has been corrected. **The HMI holds a credential that can start the conveyor** (R-14), and so does the historian's client. Both are S8's targets, deliberately left in place.

**Detection value.** Because nothing distinguishes the two accounts' actions, an S24 detector has to work from *behaviour*: the collector has never written a node, so its first write is the signal.

**Options when this is fixed, cheapest first:** a second OPC UA server instance that exposes only measurements to the historian; a node-level ruleset with a test that asserts both a permitted write succeeds and a forbidden one fails; or federation to the identity authority.

---

*VIGILIMEN-ADR-017 · Sprint 4*
