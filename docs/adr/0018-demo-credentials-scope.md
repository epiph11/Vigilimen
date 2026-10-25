# ADR-018 — Demo credentials in the plant, and what ADR-007 does and does not cover

**Status:** Accepted · **Date:** 25 October 2026 · **Deciders:** E. Zaré
**Related:** ADR-007 (federated identity) · ADR-008 · ADR-017 · FF-03 · FF-22 · **Sprint:** 4

---

## Context

ADR-007 says no static credential exists. The README repeats it. Yet the plant carries passwords in plain text: two OPC UA accounts in `opcua_server.py` and `docker-compose.yml`, the historian's database password in the compose file, and the default `openplc` / `openplc` login on both PLC UIs. Read literally, the repository contradicts its own ADR.

## Decision

**ADR-007 governs credentials that reach a cloud account. This ADR governs credentials inside the local simulated plant, and they are a different class with different rules.**

A plant demo credential is acceptable only if **all** of these hold:

1. **It protects a simulation.** No value of any kind: no real data, and nothing it reaches is shared with anything real.
2. **It cannot be reached from outside the host.** Every published port is on `127.0.0.1` and both OT networks are `internal` (FF-22).
3. **It is not a reused secret.** No real password, no cloud key, nothing that appears elsewhere.
4. **It is visibly a demo.** The values say so (`...-demo`, `...-local-only`), and each file that holds one says why.
5. **It is listed.** The register below is the only place a new one is added.

| Credential | Where | Why acceptable | What replaces it on a real site |
|---|---|---|---|
| OPC UA `historian`, `engineer` | `opcua_server.py`, `docker-compose.yml`, FUXA device | Loopback, simulated plant | Federation to the identity authority (ADR-008) |
| Historian DB password | `docker-compose.yml` | Loopback, no data of value | Secret from the identity authority |
| OpenPLC `openplc` / `openplc` | OpenPLC's default | UI is on an internal network, reachable only through a temporary relay | Changed on first boot, role-based |

## Reasoning

**Pretending the exception does not exist is the worse option.** A portfolio that says "no static credentials" while shipping three is a portfolio whose author did not read their own ADR, and the contradiction is what a reviewer finds first.

**FF-03 already tolerates them,** because it looks for cloud-credential *shapes* and these are not that. The tolerance is now a decision instead of an accident.

## Consequences

**Positive.** ADR-007's claim stays strong and true for what it covers. The plant's exception has conditions, and conditions can fail a build.

**Negative.** Condition 4 is convention; nothing enforces that a *new* demo password looks like one. Condition 2 is enforced (FF-22); conditions 1 and 3 are not.

**Gap, named.** The OPC UA channel is `NoSecurity`: the password crosses the Docker network in clear. That is acceptable on a loopback-only simulation and is exactly what S6 network monitoring should be shown seeing.

**Wording change.** README and ADR-007 now say *no static credential reaches a cloud account*, and point here for the plant.

---

*VIGILIMEN-ADR-018 · Sprint 4*
