# Protocol register

**Ref:** MD360-ARC-005 · **Rev:** 1.0 · **Date:** 14 September 2026 (AEST) · **Sprint:** 3

The protocols spoken in the simulated plant, and — the only column that matters — **what each one authenticates.**

---

## The register

| Protocol | Where | Port | Authenticates the sender? | Integrity? | Confidentiality? |
|---|---|---|---|---|---|
| **Modbus TCP** | SCADA ↔ PLC-CONV-001 | 502 | **No. Nothing at all** | No | No |
| **S7comm** | Engineering ↔ PLC (S7-1200/1500 profile) | 102 | Proprietary, weak. Access levels are a device setting, not a protocol property | No | No |
| **DNP3** *(without Secure Authentication)* | Remote outstation ↔ SCADA | 20000 | **No** | CRC only — detects corruption, not an adversary | No |
| **DNP3-SA** | where the device supports it | 20000 | Yes — challenge-response | Yes | No |
| **OPC UA** | PLC ↔ historian ↔ northbound | 4840 | **Yes** — X.509 certificates, user tokens | Yes, signed | Yes, encrypted |
| **MQTT / Sparkplug B** | edge → cloud | 8883 | TLS client certificate | TLS | TLS |

---

## What that table means

**Modbus and DNP3 without Secure Authentication have no authentication whatsoever.** Not weak authentication. None. There is no credential, no session, no identity in the protocol at all. **Anyone who can reach port 502 can write any register**, and the device will act on it exactly as it acts on the SCADA system, because to the device the two are indistinguishable.

This is not a bug and it is not going to be patched. Modbus was published in 1979 for a serial link between two boxes in one cabinet. It was never wrong; the network arrived afterwards.

**S7comm is the middle case and is often overstated in both directions.** It has proprietary protections and access levels, but those are device configuration rather than protocol guarantees, and they have been broken repeatedly. Treat it as unauthenticated and be pleasantly surprised.

**OPC UA is the outlier that does it properly** — certificates, signing, encryption, user tokens. That is why it is the northbound protocol here and why it is not the one talking to the controller: the controller does not speak it, which is the ordinary situation on real plant.

---

## The consequence that runs through the whole programme

> **In OT, the segmentation *is* the authentication.**

If a protocol cannot tell you who is talking, the only remaining control is *who can reach the port at all*. That single sentence explains a great deal that otherwise looks like paranoia:

- why **FR5 — restricted data flow** carries far more weight in IEC 62443 than confidentiality does
- why a conduit is a first-class object with its own target security level, rather than "a firewall rule"
- why **CRS-011** in the hydro assessment requires the write allow-list to be enforced **at the controller**, not in the HMI's tag database — an allow-list the adversary can route around is decoration
- why the ADR-005 one-way boundary is worth its capability cost
- why **active scanning can crash legacy PLCs**: a device with no concept of an unauthenticated stranger has no concept of a malformed one either. Passive monitoring first, always; active polling only under change control with engineering sign-off

---

## Where this bites in the simulated plant

`PLC-CONV-001` reads `Start_PB`, `Bearing_Temp` and `Zero_Speed` over Modbus and S7comm. **Every one of those is writable by anyone with network reach**, which means:

- an adversary can start the conveyor
- an adversary can report a false bearing temperature and suppress the machine-protection trip
- an adversary can report `Zero_Speed` false and make a stopped belt look like it is running

None of those is fixable in the PLC program. All three are fixable at the conduit, and that is where S5, S6 and S7 put them.

**What an adversary cannot do from the network, at any point:** prevent `SIS-CONV-001` from dropping the contactor. The safety function has no network input of any kind — no remote reset, no SCADA write, no bypass bit. Its independence is the one property in this plant that does not depend on the segmentation holding.

---

## Demonstrated, not asserted

Two runnable pairs make this register's central claim checkable rather than quoted. Both have been executed.

| Run | What it shows |
|---|---|
| `plant/gateway/modbus_server.py` + `attack_demo.py` | Three unauthenticated attacks succeed — start the belt, spoof the bearing to 99 °C and defeat machine protection, restore and restart leaving nothing in the process data. The fourth fails: the safety function holds through an e-stop while RUN is held asserted |
| `plant/gateway/opcua_server.py` + `opcua_contrast.py` | The same opening move is refused at the door. A measurement cannot be written even by a named account |

**The Modbus implementation is written from the MBAP frame rather than pulled from a library**, and that was the right call for a reason beyond dependencies: holding the frame in one file makes the claim impossible to argue with. There is no identity field. Not optional, not disabled — absent.

**And the OPC UA server produced its own finding.** Its first version mapped the engineer account to asyncua's Admin role, and the contrast demo caught Admin writing `SafetyTripped` — a measurement of the safety controller. A second attempt, a custom permission ruleset, denied *every* write including legitimate ones, because the write list sits on `body.Parameters` rather than `body`. **A rule that refuses everything looks secure and is simply broken**, and it was caught only because the demo asserts that a permitted write *succeeds* as well as that a forbidden one fails.

What ships enforces read/write per node, and the two accounts differ in **attribution rather than authorisation**. That is stated in the server rather than hidden, because a role model which silently bypasses node permissions gives you less than the diagram suggests.

---

## Verification note

Port numbers and the authentication properties above are standard and stable. **The S7comm characterisation is the one to re-check** against the specific firmware of any device actually deployed — Siemens has changed access-level behaviour across firmware generations, and "weak" is a summary rather than a finding.

---

*MD360-ARC-005 rev 1.0 · Sprint 3 · Feeds ZCR 1 and ZCR 3 at S7*
