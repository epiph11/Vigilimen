# ADR-021 — Vendor remote access is a brokered, recorded, time-boxed session, not a VPN

**Status:** Proposed (draft of 26 October 2026, nothing built) · **Deciders:** E. Zaré
**Related:** ADR-005 (unidirectional boundary, four conditions for a write path) · ADR-008 · ADR-017 · ADR-018 · ADR-020 · `docs/architecture/dmz-target.md` · **Sprint:** 5 (gate M1)

> The delivery plan calls this decision "brokered remote access over VPN" and numbers it ADR-013. In the repository ADR-013 is the Modbus link; this is ADR-021 (`docs/adr/NUMBERING.md`).
> Draft. Choices marked **(to confirm)** are proposals.

---

## Context

Remote access by a vendor is the most frequent control gap in real OT estates. Oldsmar was not a sophisticated attack: shared remote-access credentials and an operator who happened to be watching. In 62443 terms the vendor path is a conduit, usually the one with the highest target security level, because it crosses the most boundaries. Phishing-resistant MFA on it is a CIRMP obligation (s8B).

ADR-005 allows an IT-to-OT path only if it is a registered conduit, terminates in the DMZ, is validated at the receiving end, and cannot reach a protective function. ADR-017 says no OPC UA account can be limited to read access today, so a vendor session to the gateway could write `StartCommand`.

## Decision

1. **A VPN is rejected.** A VPN grants network access; this grants a session to one asset over one protocol.
2. **`jump` is an OpenSSH host in the DMZ.** The vendor connects from outside (the host's loopback in the lab) to it and to nothing else. *(to confirm: OpenSSH over Apache Guacamole, Teleport or a commercial PAM; chosen because every property below can be configured as code and tested in compose. The alternatives were not evaluated here, and their licences and features must be checked before choosing otherwise.)*
3. **Named, time-boxed access by short-lived SSH certificates.** One principal per individual, no shared account. The operator approves a request with a script that signs a certificate valid for a fixed number of minutes. Expiry is automatic. The approval and its time are logged. No approval, no certificate, no session.
4. **The session is an interactive shell on `jump`, recorded.** The shell offers only the client for the one permitted protocol. A recorder wraps the session and writes to a volume the vendor account cannot write. **If the recorder cannot write, the login ends**: fail closed. A plain TCP port forward is not used, because its content cannot be recorded.
5. **One asset, one protocol, enforced by topology first.** Each brokered asset has its own internal network (`net_remote_<asset>`) holding only `jump` and that asset. `jump` has no other path into OT. The asset's own authorisation then limits what the session may do.
6. **First target: the historian, PostgreSQL 5432, through a read-only database role.** Unlike OPC UA (ADR-017), a database role can really be read-only, so ADR-005's conditions can be met. A target that can start the conveyor (the gateway, the PLC) is **not** offered until the engineering workstation exists and a write path satisfies ADR-005. *(to confirm, Q1)*
7. **Termination.** The operator can end a session at any time with a script that kills it and revokes its certificate. A reconnection with the revoked certificate is refused.
8. **Phishing-resistant factor.** The policy is configured: the certificate is bound to a hardware-backed key that requires user verification. *(to confirm: the exact OpenSSH options and the minimum version.)* **The lab cannot prove the strength of a hardware factor.** It proves the policy and the recording, which is what the S5 cadrage already says.

## Reasoning

**Why certificates and not accounts with keys in `authorized_keys`.** Expiry, a principal name and constraints travel with the certificate, so "time-boxed" and "named" are properties of the credential, not of a clean-up job someone must remember.

**Why topology before configuration.** An allow-list inside `jump` can be edited or misconfigured; a network that holds only `jump` and one asset cannot reach anything else, whatever `jump` is told. Docker cannot filter by port per network, so the protocol limit comes from the one listener on the asset plus its role.

## Consequences

**Positive.** Each property of the gate (approval, recording, termination) maps to a test with a negative step. The conduit is registered with its own identifier.

**Negative.** One extra network per brokered asset, and the historian becomes a multi-homed service. The DMZ is not internal in the lab, so `jump` has an Internet route a real DMZ would deny (Docker constraint, see `dmz-target.md`). Interactive recording captures what the vendor types and sees, not bytes of a forwarded protocol.

**Limits to state in the gate report.** No hardware factor is tested. The vendor, the operator and the code have the same author. The lab network is not a firewall.

## Tests (one FF, three cases, each with a negative step; number given when the script is written, FF-30 proposed)

| Case | Positive | Negative |
|---|---|---|
| Open only on approval | An approved vendor opens a session to the historian | No approval, or an expired certificate: refused |
| Recorded | The session produces a recording | Recorder unavailable: login refused |
| Terminable | The operator ends a live session | The revoked certificate cannot reconnect; `jump` cannot reach any other asset |

Plus FF-22 (topology: `jump` on `net_dmz` and one access segment only; each access segment has exactly two members) and FF-04.

## Open questions (block acceptance)

- **Q1.** Historian as the first target (proposed) or another asset? Anything that can write to the plant waits for the engineering workstation and a path that satisfies ADR-005.
- **Q2.** Who is the operator in the lab (a host script run by E. Zaré), and where do approval logs go?
- **Q3.** Session length by default (30 min proposed) and the maximum.
- **Q4.** Is a hardware security key available to test the positive path of the factor, or is the policy shown by configuration only?

---

*VIGILIMEN-ADR-021 · Sprint 5 · draft*
