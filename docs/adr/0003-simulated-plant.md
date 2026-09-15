# ADR-003 — A simulated plant is the System under Consideration

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré

---

## Context

An OT security programme needs an OT system. The options are real hardware, a vendor simulator, or an open-source simulated plant.

---

## Decision

**A simulated plant** — OpenPLC for the controllers, FUXA for the SCADA and HMI, Node-RED for gateway logic, Mosquitto and Modbus/DNP3 for the protocols, TimescaleDB for historisation — modelling a conveyor, a crusher, dewatering, and **a protective function that is architecturally separate from the control function.**

---

## Reasoning

**Real hardware costs the budget and buys less than it appears to.** A single used PLC, a managed industrial switch and a panel would exceed US$333 several times over, and the thing it would demonstrate — that the author can wire a panel — is not what an assurance role is testing for.

**A simulated plant can be attacked.** This is the decisive property. The programme needs to run ATT&CK for ICS techniques against controllers, break them, and rebuild them in an afternoon. Doing that to real hardware is either impossible or expensive, and doing it to a vendor's cloud simulator violates their terms.

**FUXA over Ignition Maker Edition** on licensing grounds. FUXA is MIT-licensed with no restriction on how the result is shown. Ignition Maker is free but non-commercial, and a portfolio shown to prospective employers sits close enough to a commercial purpose that the question would have to be asked. Choosing the permissive tool avoids a conversation that adds nothing.

---

## The honest limitation, stated once so it need not be re-litigated

**A simulated plant does not have the failure modes of a real one.** No electrical noise, no marginal terminations, no firmware quirk that only appears at 40 °C, no vendor's undocumented behaviour under load. The protocols are real; the physics is not.

That limitation is recorded in the fidelity statement of every artifact the plant produces. **It is stated as a property of the work rather than defended**, which is the only treatment that survives a reviewer who has worked on real plant.

---

## Consequences

**Positive.** US$0 hardware. Destructible and rebuildable. Runs on the local spine, which is what makes the cost model hold. Vendor-realistic protocols mean the network visibility work at S6 sees traffic worth parsing.

**Negative.** The fidelity limitation above. Some findings — timing-sensitive protocol behaviour, device-specific weaknesses — cannot be reproduced.

**Mitigation.** Where a claim depends on real device behaviour, it is marked as an assumption rather than a finding. This is the same discipline the 62443 assessment applies to its own operating assumptions, and it is applied here for the same reason.

---

*MD360-ADR-003 · Sprint 0 · Gate M0*
