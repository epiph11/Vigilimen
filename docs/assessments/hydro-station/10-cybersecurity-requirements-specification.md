# Cybersecurity Requirements Specification

**Kanangra Creek Hydro Station — 20 MW run-of-river generating station**
**Document:** 10 of 12 · **ZCR 6** · **Ref:** KCH-CYB-CRS-001 · **Revision:** 0.2 — DRAFT
**Date:** 14 September 2026 · **Assessor:** Epiphane Zaré
**Status:** Unapproved. Requires asset owner approval (ZCR 7) before issue to tender.

> ⚠ **Fictional facility.** Kanangra Creek is a worked example modelled on a real small run-of-river architecture. It describes no actual asset.

---

## 1. Purpose and standing

This specification consolidates the output of the IEC 62443-3-2 risk assessment into requirements that can be **contracted against**. It is the deliverable that makes 62443 real: everything upstream of it describes risk, and this document converts that description into obligations a system integrator and a product supplier can price, deliver and be held to.

It flows in three directions:

| Direction | Standard | What it becomes |
|---|---|---|
| To the **system integrator** | IEC 62443-**2-4** | Security programme obligations on the SI for this project |
| To the **product suppliers** | IEC 62443-**4-1** and **4-2** | Secure development obligations, and component capability (SL-C) requirements |
| To the **asset owner** | IEC 62443-**2-1** | Operational obligations that survive handover |

**Nothing in this document is a recommendation.** Where a requirement is not achievable it must be raised as a formal deviation before contract award, not discovered at acceptance.

### 1.1 Documents this specification consolidates

| Source | ZCR | What it contributes |
|---|---|---|
| 01 — System under Consideration | 1 | Scope, boundary, access points |
| 02 — Initial risk assessment | 2 | Consequence scenarios S-01…S-10 |
| 03 — Zone and conduit partition | 3 | Zones, conduits, SL-T assignment |
| 04 — Tolerable risk criteria | 4 | Risk acceptance and the two overrides (rev 0.2 — life-safety override widened) |
| 05 — Detailed risk assessment | 5 | Risks R-01…R-40, residual bands, SL gap, attack path |
| 06 — Zone and conduit drawing | 6 | KCH-CYB-ZC-001 rev 0.2 |

Documents 07 (characteristics register), 08 (operating assumptions), 09 (threat environment) and 11 (regulatory requirements) are **consolidated into the annexures of this specification** rather than issued separately. A tenderer receives one requirements document, not five.

---

## 2. How to read a requirement

Every requirement carries five things, and a requirement missing any of them is not yet a requirement:

```
CRS-018   Applies to: Z-02 · Delivers: SL-T 3 · Treats: R-05, R-19 · FR3 System Integrity
          Verify: FAT — hold point
```

| Field | Meaning |
|---|---|
| **Applies to** | The zone or conduit. A requirement with no zone is a wish |
| **Delivers** | The target security level this requirement contributes to |
| **Treats** | The risk IDs from document 05. Requirements that treat nothing are cut |
| **FR** | The IEC 62443-3-3 foundational requirement served — FR1 identification and authentication control, FR2 use control, FR3 system integrity, FR4 data confidentiality, FR5 restricted data flow, FR6 timely response to events, FR7 resource availability |
| **Verify** | Design review · document review · **FAT** · **SAT** · commissioning. A requirement with no verification method cannot be accepted |

**Hold point** marks a requirement whose failure stops shipment or stops energisation. Everything else may be accepted conditionally against a punch list.

> ⚠ **Open action before issue.** Requirements below are project-numbered and tagged to the foundational requirement they serve. **Mapping each to its specific IEC 62443-3-3 System Requirement number (SR x.y) is outstanding** and must be completed against the standard text before this document goes to tender. Tagging to FR is sufficient to specify and to test; SR numbering is what lets a supplier's SL-C claim be compared line for line.

---

## 3. Governing constraints

These four sit above every requirement in this document. A design that satisfies every numbered requirement and breaches one of these is rejected.

### GC-1 — No security control in a protective function

No control required, supplied or configured under this specification may be placed in the trip path of a protection or safety function in Z-01. A control that can fail closed on a protective function has made the plant less safe, not more.

Controls protecting Z-01 act on its **management interfaces**, on **access**, and on **detection** — never on the protective action itself. This is the direct lesson of TRITON and it is not negotiable at any price.

### GC-2 — Independent last-resort protection

The hardwired overspeed trip shall remain independent of every programmable device in the SUC, shall require no network, power or software from any zone other than its own, and shall be demonstrated to operate with all programmable systems in a failed state.

**Verification method.** GC-2 is demonstrated by witnessing an overspeed trip test with **the governor de-energised and the unit control PLC in STOP**, recording the trip speed and the resulting gate closure. A certificate, a datasheet or a vendor statement does not discharge this — the claim is about independence, and independence is shown by removing the thing it is independent of.

*(This is operating assumption A-01. If the delivered design does not satisfy GC-2, Z-02's target security level rises to SL 4 and this specification must be reissued.)*

> **Why A-01 is the most load-bearing assumption in the assessment.** After the ZCR 5 recalibration of 14 September 2026, **six risks — R-12, R-17, R-26, R-35, R-38, R-39 — are rated at direct consequence 4 rather than 5 precisely because this trip stands behind them.** If A-01 is false, all six return to consequence 5, the Extreme band returns from 11 to 17, and Z-02 rises to SL-T 4. The register is conditional on one witnessed test. That is not a weakness in the assessment; it is the assessment saying which single fact it is standing on.

### GC-3 — Availability precedence

Where a security control and continuity of generation conflict, the conflict is escalated to the asset owner, never resolved by the integrator in favour of the control. Security controls shall fail in the direction that preserves safe operation.

### GC-4 — No undocumented path

Every communication path in the delivered system shall appear in the conduit register at Annexure A. A path that exists and is not registered is a defect, regardless of whether it is exploitable.

---

## 4. Zone requirements

### 4.1 Z-01 — Protection and trip · SL-T 3

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-001** | Protection relay management interfaces shall authenticate each user individually. Shared, default and vendor-generic accounts shall not be present in the delivered configuration. | FR1 | R-01 | FAT — **hold point** |
| **CRS-002** | Every change to a protection setting group shall generate an event transmitted to the supervisory zone within 10 seconds, identifying the changed group, the originating account and the originating host. | FR6 | R-01 | FAT — **hold point** |
| **CRS-003** | The delivered relay configuration shall be supplied as a signed or hash-verified baseline, and a documented procedure shall exist to verify the running configuration against that baseline without taking the relay out of service. | FR3 | R-01, R-04 | Document review + SAT |
| **CRS-004** | Out-of-service state of any protective element shall be alarmed to the supervisory zone and to the portfolio control centre. Local indication alone is not sufficient for a normally unattended station. | FR6 | R-02 | FAT — **hold point** |
| **CRS-005** | Relay firmware shall be cryptographically verified by the device before installation. Where the device does not support verification, the supplier shall declare this as a capability gap under CRS-051. | FR3 | R-04 | Document review |
| **CRS-006** | The process bus carrying GOOSE shall be physically separate from the station bus — separate switching hardware, not VLAN separation alone. | FR5 | R-03 | Design review + SAT |
| **CRS-007** | No remote access path shall reach Z-01 management interfaces. Configuration change shall require presence in the relay room. | FR2 | R-01, R-31 | Design review + SAT — **hold point** |

> **Note on Z-01.** Requirement CRS-007 is the most commercially contentious in this specification, because it removes the vendor's ability to adjust settings remotely. It is retained deliberately: the consequence of protection defeat is a fatality scenario (S-04), and the convenience of remote setting change does not buy that back. An integrator wishing to challenge it should propose a supervised alternative, not a relaxation.

### 4.2 Z-02 — Unit control · SL-T 3

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-008** | The governor programming interface shall authenticate each user individually and shall log every logic download with account, host, timestamp and a hash of the downloaded logic. | FR1, FR6 | R-05 | FAT — **hold point** |
| **CRS-009** | Wicket gate and main inlet valve closure rates shall be limited by a **hydraulic restriction in the servomotor circuit** — a calibrated orifice or needle valve bounding oil flow, with the cushioning stroke at end of travel — sized so that the fastest achievable closure remains within the penstock's design surge pressure with the governor commanding maximum rate. The pressure relief or synchronous bypass valve shall be commissioned as the companion device. **Any rate limit implemented in governor logic is a secondary operational convenience and shall be declared as such; it shall not be offered as the mechanism satisfying this requirement.** The enforcing mechanism, its sizing calculation and the resulting minimum closure time shall be identified in the delivered documentation. | FR3, FR7 | R-06, R-38, R-39 | Design review + FAT — **hold point** |
| **CRS-010** | Controller operating mode changes (RUN / PROGRAM / STOP) shall be alarmed to the supervisory zone within 10 seconds and shall be recorded with the originating account. | FR6 | R-07 | FAT — **hold point** |
| **CRS-011** | The unit control PLC shall accept command and setpoint writes only from an explicitly configured allow-list of source addresses, and only for an explicitly configured allow-list of tags. Unrestricted write access to the controller from the supervisory VLAN shall not be delivered. | FR1, FR2, FR5 | R-08, R-38 | FAT — **hold point** |
| **CRS-012** | Command frequency on C-02 shall be rate-limited at the boundary, with the limit documented and the exceeded-rate condition alarmed. | FR7 | R-38 | FAT |
| **CRS-013** | Controller logic shall be supplied with a golden-copy hash, and a procedure shall exist to compare running logic against it. | FR3 | R-05, R-19 | Document review |
| **CRS-014** | Excitation control interfaces shall not be reachable from any zone other than Z-02. | FR5 | R-09 | Design review + SAT |

### 4.3 Z-03 — Station auxiliaries · SL-T 2

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-015** | Auxiliary setpoints shall be baselined at handover, and any change to a baselined setpoint shall raise an event to the supervisory zone. Alarming on process value alone is insufficient — the slow-drift scenario stays inside alarm tolerance by design. | FR6 | R-10 | FAT |
| **CRS-016** | Pump and fan **inhibit** states shall be monitored and alarmed, not only run states. | FR6 | R-11 | FAT |
| **CRS-017** | Conduit C-03 shall carry only the defined permissive and status exchange between Z-03 and Z-02. General traffic between the zones shall be denied by default. | FR5 | R-12 | Design review + SAT — **hold point** |

### 4.4 Z-04 — Supervisory control · SL-T 2

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-018** | Each operator shall hold an individual account. Shared operator accounts shall not be delivered. | FR1 | R-17 | FAT — **hold point** |
| **CRS-019** | Alarm configuration changes — thresholds, suppression, shelving — shall be logged to a store outside Z-04, and threshold widening shall raise an event. | FR6 | R-14 | FAT |
| **CRS-020** | The SCADA redundant pair shall not share a single switch stack or a single power supply path. | FR7 | R-15 | Design review — **hold point** |
| **CRS-021** | The station shall be operable under local manual control with all external conduits severed, and this capability shall be demonstrated. | FR7 | R-15 | SAT — **hold point** |
| **CRS-022** | Time synchronisation shall be drawn from at least two independent sources, with a divergence alarm. A single unauthenticated GPS input shall not be the sole reference for protection timestamping. | FR3, FR6 | R-16, R-40 | Design review + SAT |

### 4.5 Z-05a — Engineering · SL-T 3

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-023** | Configuration backups shall be replicated to a store that is **off-site, outside the plant authentication domain, and not writable from the engineering workstation**. | FR7 | R-18 | Design review + SAT — **hold point** |
| **CRS-024** | A full restoration of controller logic, relay settings and SCADA configuration from backup to a known-good state shall be **demonstrated**, and the elapsed time recorded as the measured recovery time. An untested backup is not a backup. | FR7 | R-18 | SAT — **hold point** |
| **CRS-025** | Project files for controllers and relays shall be integrity-protected, and a golden-copy comparison shall be performed and recorded before every download to a live device. | FR3 | R-19 | Document review + FAT |
| **CRS-026** | Engineering toolchains for protection, governor and PLC shall not all reside on a single host without separation of duty. The delivered design shall state which separation is applied. | FR2 | R-21 | Design review |
| **CRS-028** | Removable media ports on the engineering workstation shall be controlled by policy enforced technically, not administratively. | FR2 | R-27 | FAT |

### 4.5a Z-05b — Plant information · SL-T 2

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-027** | Engineering documentation, network diagrams and relay settings held in the plant information store shall be encrypted at rest and access-restricted to named engineers. | FR4 | R-20 | Document review |
| **CRS-027a** | The historian and documentation store shall hold **no executable engineering toolchain and no credential with write authority to any controller**. Compliance shall be demonstrated by inventory at SAT, not asserted. | FR2, FR5 | R-20 | SAT — **hold point** |
| **CRS-027b** | Conduit **C-13** shall be one-way in intent, engineering → plant information. Any requirement for the reverse direction shall be raised as a deviation and justified individually. | FR5 | R-19, R-20 | Design review |

> **Note on the split of Z-05.** ZCR 3 left open whether the engineering workstation should separate from the historian. It is decided: **split**. Z-05 was rated SL-T 3 because of one asset, and everything else in it was carrying a target it had not earned — which costs in requirements, in hardening, and in friction for people whose job is to read trends. When one asset drives a whole zone's SL-T, that is the condition for splitting it.
>
> The split is **logical, not civil**: same equipment room, same rack, separated by conduit C-13 and by administrative separation of the toolchain from the store. It is the cheapest control in this specification, because **Z-05b reaches its target by being correctly drawn rather than by being bought**. The ZCR 5 SL gap sheet records its gap as zero.
>
> **Z-05a is specified above Z-04 and that inversion is intentional.** The engineering workstation can reprogram the machine; the HMI can only ask it politely. Purdue level describes function, not consequence — and the split states it twice, because Z-05a and Z-05b sit at the *same* Purdue level and carry different targets.

### 4.6 Z-06 — Intake and weir · SL-T 3

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-029** | Gate movement commands shall be **validated at the receiving end** against independently sensed conditions. A single falsified input shall not be sufficient to move a gate. | FR3 | R-22, R-24, R-33 | Design review + SAT — **hold point** |
| **CRS-030** | Headwater and tailwater level shall be derived from at least two independent instruments, with a divergence alarm to the supervisory zone. | FR3, FR6 | R-24 | Design review + SAT |
| **CRS-031** | The intake enclosure shall carry a tamper detection device reporting to the supervisory zone and to the portfolio control centre. | FR6 | R-22 | SAT — **hold point** |
| **CRS-032** | Intake structure access shall be monitored — camera or intrusion detection — with alarm to a monitored centre. | FR6 | R-22 | SAT |
| **CRS-033** | The standby cellular path shall not be permanently connected. It shall be brought up on demand and shall authenticate by per-device certificate. | FR1, FR5 | R-25 | Design review + FAT |

> **Note on Z-06.** Physical access to the intake is an **assumed adverse condition** (assumption A-03), not a defeated control. Requirements here are therefore written to survive an adversary standing at the terminal. That is why CRS-029 places validation at the receiving end rather than trust in the sender, and it is the single most important design idea in this specification.

### 4.7 Z-07 — Transient and externally connected · SL-T 3

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-034** | Site-controlled engineering laptops shall be provided for use in control zones. Contractor-owned devices shall not connect directly to Z-01, Z-02, Z-03 or Z-06. | FR1, FR5 | R-26 | Design review + SAT — **hold point** |
| **CRS-035** | Control-zone switch ports shall enforce port security or 802.1X. Unused ports shall be administratively disabled and physically blocked. | FR5 | R-26, R-39 | FAT + SAT — **hold point** |
| **CRS-036** | A media sanitisation station shall be provided, and transfer of firmware or configuration into control zones shall pass through it. | FR3 | R-27 | SAT |
| **CRS-037** | A connection log shall record every transient device connection to a control zone: device, purpose, operator authorising, date and duration. | FR6 | R-39 | Document review |

### 4.8 Z-08 — Site DMZ · SL-T 3

| ID | Requirement | FR | Treats | Verify |
|---|---|---|---|---|
| **CRS-038** | The remote access jump host shall record every session in full, with the recording retained for a period defined by the asset owner and stored outside Z-08. | FR6 | R-28 | FAT — **hold point** |
| **CRS-039** | A session on the jump host shall be scoped to **one target asset and one protocol**. Network-level access to a zone or VLAN shall not be granted. | FR2, FR5 | R-28, R-32 | FAT — **hold point** |
| **CRS-040** | An operator shall be able to terminate any active remote session immediately, from the control room and from the portfolio control centre. | FR2 | R-28 | FAT |
| **CRS-041** | DMZ host patching shall be decoupled from the plant outage window. Where a patch cannot be applied, a documented compensating control shall be applied at the boundary. | FR3 | R-29 | Document review |
| **CRS-042** | Implemented firewall flows shall be compared automatically against the conduit register at Annexure A at least weekly, and any divergence raised as a finding. | FR5, FR6 | R-30 | SAT — **hold point** |

---

## 5. Conduit requirements

| ID | Requirement | Conduit | FR | Treats | Verify |
|---|---|---|---|---|---|
| **CRS-043** | Vendor remote access shall use **per-individual named accounts**. Shared per-vendor accounts shall not be created. | C-09 | FR1 | R-32 | FAT — **hold point** |
| **CRS-044** | Vendor remote access shall require **phishing-resistant multi-factor authentication**, with successful *and unsuccessful* authentication attempts logged centrally. | C-09 | FR1, FR6 | R-32 | FAT — **hold point** |
| **CRS-045** | A vendor session shall be opened only against an approved work order, shall be time-boxed, shall auto-revoke on expiry, and shall require **an operator to enable it**. Standing access shall not be configured. | C-09 | FR2 | R-31, R-32 | FAT — **hold point** |
| **CRS-046** | The intake conduit shall use cryptographic authentication of messages. Where the delivered RTU does not support authenticated DNP3, the supplier shall declare the gap under CRS-051 and the asset owner shall decide between replacement and compensating control. | C-06 | FR1, FR3 | R-23, R-33 | Design review — **hold point** |
| **CRS-047** | Market operator telemetry shall be integrity-checked at the gateway. The gateway shall not forward values it has not validated against source. | C-07 | FR3 | R-34 | FAT |
| **CRS-048** | The corporate boundary shall carry no inbound trust for identity or patch distribution into the SUC without brokering at Z-08. | C-11 | FR5 | R-36 | Design review — **hold point** |
| **CRS-049** | The historian collection path shall be one-way in implementation, not only in intent. A unidirectional gateway shall be evaluated and the decision recorded. | C-04 | FR5 | R-37 | Design review |
| **CRS-050** | Every conduit shall be documented with its endpoints, protocol, port, direction, and the controls applied. The delivered as-built register shall match Annexure A. | all | FR5 | R-30 | SAT — **hold point** |

---

## 6. Component capability requirements — IEC 62443-4-2

The supplier shall declare, per component, the **capability security level (SL-C)** achieved against each foundational requirement.

| ID | Requirement | Verify |
|---|---|---|
| **CRS-051** | For each component supplied into a zone with SL-T 3, the supplier shall declare SL-C per FR. **Where SL-C is below the zone's SL-T, the gap shall be declared before contract award, not at acceptance.** | Document review — **hold point** |
| **CRS-052** | Components shall support individual user authentication, or the supplier shall declare the limitation and propose a compensating control. | Document review |
| **CRS-053** | Components shall support export of security-relevant events to an external collector. | Document review + FAT |
| **CRS-054** | Components shall permit disabling of unused services and ports, and the delivered configuration shall have them disabled. | FAT — **hold point** |
| **CRS-055** | No component shall be delivered with default or hardcoded credentials in the running configuration. | FAT — **hold point** |
| **CRS-056** | The supplier shall provide a **software bill of materials** for each component, in a machine-readable format, updated at each firmware release. | Document review |

> **SL-C, SL-T and SL-A.** SL-T is what the zone needs. SL-C is what the component can do, as declared by its supplier. SL-A is what is actually achieved once installed and configured. A component with SL-C 3 badly configured achieves less; a component with SL-C 1 **cannot** reach SL-T 3 however well configured — and that finding belongs in procurement, not in engineering. The operating loop after handover is: assess SL-A against SL-T, and the delta is the remediation backlog.

---

## 7. Integrator obligations — IEC 62443-2-4

| ID | Requirement | Verify |
|---|---|---|
| **CRS-057** | The integrator shall operate a documented security programme covering this project, and shall state the maturity level claimed for each 62443-2-4 practice area. | Document review — **hold point** |
| **CRS-058** | The integrator shall nominate a named individual accountable for cybersecurity delivery on this project, with contact details maintained for the contract duration. | Document review |
| **CRS-059** | Personnel with access to the SUC shall be identified, and their suitability assessed to the standard the asset owner specifies for critical workers. | Document review |
| **CRS-060** | The integrator shall notify the asset owner of any security incident affecting its own environment that could affect the delivered system, within 24 hours of becoming aware. | Contract |
| **CRS-061** | All configuration, logic, settings and documentation shall be handed over in editable source form, with no dependency on integrator-proprietary tooling for the asset owner to maintain the system. | Document review — **hold point** |
| **CRS-062** | The integrator shall deliver an as-built zone and conduit drawing at handover, reconciled against KCH-CYB-ZC-001. | SAT — **hold point** |

> **Note.** CRS-061 is the requirement most likely to be negotiated away and the one least worth conceding. A system the asset owner cannot maintain without the integrator is a system whose security posture is the integrator's to decide.

---

## 8. Product supplier obligations — IEC 62443-4-1

| ID | Requirement | Verify |
|---|---|---|
| **CRS-063** | The supplier shall evidence a secure development lifecycle covering threat modelling, secure coding, security testing and defect management. | Document review |
| **CRS-064** | The supplier shall operate a published vulnerability disclosure process and shall notify the asset owner of vulnerabilities affecting supplied components. | Contract — **hold point** |
| **CRS-065** | The supplier shall commit to a security patch support period, stated in years, and shall give not less than 24 months' notice of end of security support. | Contract — **hold point** |
| **CRS-066** | The supplier shall state, per component, whether firmware is cryptographically signed and verified by the device. | Document review |

---

## 9. Evidence and acceptance

### 9.1 The hold points

A hold point is a requirement whose failure **stops shipment or stops energisation**. It is not negotiable at the point of test; it is escalated. **Forty requirements in this specification carry hold points**, concentrated in three places: authentication and account hygiene, the independence of protective functions, and the recoverability of the system.

> **Count corrected at rev 0.2.** Rev 0.1 stated twenty-six. That was a miscount, found by counting the tables rather than trusting the summary line — which is the same discipline the specification demands of the integrator, and it applies to the assessor first. Forty hold points on seventy-two requirements is a high proportion and an integrator will say so; the answer is that a hold point marks a requirement whose failure stops shipment or energisation, and on a normally unattended station with a fatality scenario behind three of its zones, that is where the line falls. Any hold point an integrator wishes to downgrade to punch-list should be argued individually at §15.1, not in aggregate.

### 9.2 What is verified where

| Phase | What it proves | What it cannot prove |
|---|---|---|
| **Design review** | The architecture satisfies the requirement in principle | That it was built that way |
| **Document review** | The obligation is committed and evidenced | That it is practised |
| **FAT** | The **system** meets the specification in a controlled environment | Anything about the site |
| **SAT** | The **installation** meets it in the real one | — |
| **Commissioning** | Transition to operational state is clean | — |

**A SAT plan that repeats the FAT plan is a defect in the SAT plan.** SAT exists for what the factory could not represent: network integration, remote access from the real internet, segmentation enforced against real traffic, live logging paths, and the independence demonstrations that need the real plant.

### 9.3 Commissioning transition

| ID | Requirement | Verify |
|---|---|---|
| **CRS-067** | All factory and commissioning credentials shall be rotated before energisation, and the rotation evidenced. | Commissioning — **hold point** |
| **CRS-068** | All commissioning and temporary accounts shall be removed before handover, with a closing account inventory produced. | Commissioning — **hold point** |
| **CRS-069** | Firewall policy shall transition from log-only to enforcing before handover, after a full operating cycle in log-only, with the ruleset reviewed against observed traffic. | Commissioning — **hold point** |
| **CRS-070** | The as-built conduit register shall be reconciled and signed at handover. | Commissioning — **hold point** |

---

## 10. Annexure A — Zone and conduit characteristics register

*(Consolidates document 07.)*

### Zones

| Zone | Name | Purdue | Principal assets | Physical boundary | Conduits | Worst consequence | SL-T | Owner |
|---|---|---|---|---|---|---|---|---|
| Z-01 | Protection and trip | 1 | Generator, transformer and line protection relays; hardwired overspeed trip; trip circuits; process bus | Relay room | C-01 | 5 | **3** | *TBC* |
| Z-02 | Unit control | 1 | Digital governor, unit control PLC, AVR, synchronising, main inlet valve control | Control cabinets, powerhouse | C-01, C-02, C-03 | 5 | **3** *(4 if A-01 false)* | *TBC* |
| Z-03 | Station auxiliaries | 1 | Auxiliaries PLC: cooling, lube oil, drainage, air, HVAC | Auxiliary cabinets | C-03 | 4 | 2 | *TBC* |
| Z-04 | Supervisory control | 2 | SCADA server pair, control room HMI, alarm annunciator, station bus, time source | Control room | C-02, C-04, C-06, C-12 | 4 | 2 | *TBC* |
| Z-05a | Engineering | 3 | Engineering workstation, governor/PLC/relay toolchains, configuration backup store, patch staging | Equipment room | C-13 | 5 | **3** | *TBC* |
| Z-05b | Plant information | 3 | Station historian, documentation store, reporting and trend clients | Equipment room | C-04, C-05, C-13 | 3 | 2 | *TBC* |
| Z-06 | Intake and weir | 1–2 | Intake RTU, gate actuation, level instrumentation, spillway control, radio terminal | Intake structure, 4.2 km upstream | C-06 | 5 | **3** | *TBC* |
| Z-07 | Transient and externally connected | any | Maintenance laptops, removable media, vendor devices, test equipment | **No permanent boundary** | C-10 | inherited | **3** | *TBC* |
| Z-08 | Site DMZ | 3.5 | Historian replication node, jump host, protocol gateway, firewall pair | Equipment room | C-05, C-07, C-08, C-09, C-11 | inherited | **3** | *TBC* |

### Conduits

| ID | Endpoints | Protocol | Direction | SL-T | Governing requirements |
|---|---|---|---|---|---|
| C-01 | Z-01 ↔ Z-02 | IEC 61850 GOOSE + hardwired | bidirectional | **3** | CRS-006, GC-1, GC-2 |
| C-02 | Z-04 ↔ Z-02 | Modbus TCP / OPC UA | bidirectional | **3** | CRS-011, CRS-012 |
| C-03 | Z-03 ↔ Z-02 | Modbus TCP | bidirectional | 2 | CRS-017 |
| C-04 | Z-04 ↔ Z-05b | OPC UA / collector | one-way in intent | 2 | CRS-049 |
| C-05 | Z-05b ↔ Z-08 | Replication | northbound | 2 | CRS-050 |
| C-06 | Z-06 ↔ Z-04 | DNP3 over licensed radio | bidirectional | **3** | CRS-029, CRS-046 |
| C-07 | Z-08 ↔ market operator | Market network | bidirectional | **3** | CRS-047 |
| C-08 | Z-08 ↔ control centre | Operator WAN | bidirectional | **3** | CRS-050 |
| C-09 | Vendors → Z-08 → targets | Brokered session | inbound | **3** | CRS-038…CRS-045 |
| C-10 | Z-07 → any zone | Physical, USB | inbound | **3** | CRS-034…CRS-037 |
| C-11 | Z-08 ↔ corporate IT | Operator WAN | bidirectional | 2 | CRS-048 |
| C-13 | Z-05a ↔ Z-05b | File transfer / historian query | one-way in intent, engineering → plant information | **3** | CRS-027a, CRS-027b |
| C-12 | GPS → Z-04 | RF | inbound | 2 | CRS-022 |

---

## 11. Annexure B — Operating environment assumptions

*(Consolidates document 08. Full text and consequences at document 01 §6.)*

**Assumptions are load-bearing. If one is false, the SL-T derived from it is wrong.** Each shall be confirmed by the asset owner at ZCR 7, and each shall be re-confirmed at SAT.

| # | Assumption | Status |
|---|---|---|
| A-01 | The hardwired overspeed trip operates independently of every programmable device | **To be confirmed by witnessed overspeed test with the governor de-energised.** Drives GC-2, Z-02's SL-T, and the direct-consequence rating of R-12, R-17, R-26, R-35, R-38, R-39. **The single most load-bearing assumption in the assessment** |
| A-02 | Powerhouse physical access is controlled and logged | To be confirmed |
| A-03 | The intake structure is **not** effectively access-controlled | **Assumed adverse.** Drives CRS-029, CRS-031, CRS-032 |
| A-04 | No wireless exists inside the powerhouse | To be confirmed. If false, a new zone is required |
| A-05 | Relay setting groups change only locally or over an authenticated session | To be confirmed |
| A-06 | The control centre cannot command the governor directly | To be confirmed |
| A-07 | Market dispatch is advisory, not actuating | **To be confirmed.** Drives C-07's SL-T |
| A-08 | Vendor access is brokered, never network-level VPN | Enforced by CRS-039 |
| A-09 | Configuration backups exist, are current, and are restore-tested | **Assumed false.** Drives CRS-023, CRS-024 |
| A-10 | The station can operate with all external links severed | **To be demonstrated** under CRS-021 |

---

## 12. Annexure C — Threat environment

*(Consolidates document 09.)*

Threat input is **MITRE ATT&CK for ICS, content version v19.2**, verified 14 September 2026. Forty-three techniques are mapped across the forty risks in document 05.

The threat actor capability this specification is written against is **SL 3 — intentional violation using sophisticated means, moderate resources, IACS-specific skills and moderate motivation.** No zone is specified at SL 4; the reasoning, and the contrary argument, are at document 03 §5.

**Reference cases informing the requirements:**

| Case | What it informs |
|---|---|
| **TRITON / TRISIS** | GC-1 and the separation of Z-01. The target was the safety system itself |
| **Stuxnet** | CRS-025, CRS-027, CRS-036 — the engineering workstation as pivot, and removable media as the path |
| **Industroyer / Industroyer2** | CRS-006, CRS-011 — protocol-native attacks on grid control |
| **Oldsmar** | CRS-043, CRS-044, CRS-045 — shared credentials on a remote path. The failure was architectural, not technical |
| **Colonial Pipeline** | CRS-021, CRS-048 — IT compromise forcing an OT shutdown |
| **PIPEDREAM / INCONTROLLER** | CRS-051 — a toolkit built for ICS, which raises the bar on component capability |

> ⚠ ATT&CK technique IDs are version-sensitive. Several were restructured before v19.2 — T0855, T0856, T0803, T0804, T0857, T0839 and T0891 appear in older material and are superseded by T1691–T1695. Re-verify at each assessment refresh and record the version verified against.

---

## 13. Annexure D — Regulatory requirements

*(Consolidates document 11.)*

### 13.1 Does the SOCI Act apply to this station? — the test, not an assertion

Earlier revisions of this assessment assumed CIRMP applicability. **That assumption does not survive the threshold.**

A generation asset is a **critical electricity asset** where it is connected to a wholesale electricity market **and** either:

- it has an **installed capacity of at least 30 MW**, or
- its operator holds a contract to provide **system restart ancillary services (SRAS)** in that State or Territory.

**Kanangra Creek is 20 MW. It does not cross the capacity threshold on its own.** CIRMP obligations reach this station only if one of the following is true, and the asset owner must answer which:

| # | Route to applicability | Who answers |
|---|---|---|
| D-1 | The operator holds an SRAS contract covering this station | Asset owner — commercial |
| D-2 | The station forms part of a **larger registered generation asset** whose aggregate capacity crosses 30 MW | Asset owner — market registration |
| D-3 | Another asset in the operator's portfolio carries the CIRMP, and this station is brought inside it by the operator's own risk management programme rather than by statute | Asset owner — governance |
| D-4 | None of the above — **the station is outside the CIRMP regime**, and the requirements below are adopted voluntarily as good practice | Default position |

**If D-4 is the answer, this specification does not weaken.** Every requirement in it is derived from consequence through ZCR 2–5, not from a statute. What changes is the *enforcement route*: the obligations become contractual rather than regulatory, the 12-hour reporting obligation does not attach, and the asset owner cannot point to a regulator when the integrator asks why.

> **Why this is stated as a test rather than resolved.** It is a fact about the operator, not about the plant, and the assessor does not have it. Asserting applicability would have been the easier and more impressive-looking choice, and it is the error made routinely in this market — *critical infrastructure* is read as *every power station*. The threshold is public and it is 30 MW. Verify against the SOCI Definitions Rules as the primary source before external use; the figure and conditions here come from secondary legal commentary.

### 13.2 Instruments

| Instrument | Bearing on this specification | Status |
|---|---|---|
| **SOCI Act 2018 + Enhanced CIRMP Rules 2026** | **If** §13.1 resolves to D-1, D-2 or D-3: **s8B** phishing-resistant MFA with central logging (CRS-044); **s8C** segregation, inventory, restoration and **three months of independent operation** (CRS-021, CRS-023, CRS-024, CRS-048); **s10A** supply chain and FOCI assessment (§7, §8); **s11A** physical security including the physical consequences of cyber events (CRS-031, CRS-032) | ⚠ **Conditional — see §13.1.** Not assumed |
| **AESCSF v2 (2023 Core)** | Approved CIRMP framework at Security Profile 2 for enhanced asset classes | Applicable if nominated |
| **AS IEC 62443** | The method used by this specification | Voluntary; **appears in neither CIRMP approved-framework table** and is mapped underneath a nominated framework |
| **ASD Essential Eight** | ML2 under the enhanced rules | Enterprise-oriented; maps poorly onto Levels 0–2, and this specification says so rather than forcing it |
| Market operator rules | Telemetry and dispatch obligations on C-07 | ⚠ **Category to be verified.** At 20 MW run-of-river, *non-scheduled* is the working assumption, which would lighten telemetry obligations and **lower C-07's SL-T**. Not verified; not relied on |
| Dam safety and environmental licence | Spillway and environmental flow obligations reachable through gate control | Applicable — drives CRS-029, CRS-030 |

**Incident reporting.** *Conditional on §13.1.* Where the station is inside the CIRMP regime, a cyber incident taking operational technology offline is a *significant impact on availability* and carries a **12-hour** report to ASD (via ReportCyber, not the CISC), not 72. The delivered system shall support the evidence collection that report requires **whether or not the obligation attaches** — the evidence is needed for the asset owner's own investigation either way, and building it in later costs more than building it in now.

---

## 14. Traceability

Every requirement traces to a risk; every risk traces to a consequence scenario; every consequence scenario traces to a zone. A requirement that traces to nothing has been cut.

| Consequence scenario | Risks | Requirements |
|---|---|---|
| S-01 Overspeed to mechanical destruction | R-05, R-09, R-12, R-17, R-19, R-21, R-26, R-38, R-39 | CRS-008…014, CRS-025, CRS-026, CRS-034, CRS-035 |
| S-02 Water hammer | R-06 | CRS-009 |
| S-03 Spillway and intake misoperation | R-22, R-23, R-24, R-25, R-33 | CRS-029…033, CRS-046 |
| S-04 Protection defeat | R-01, R-02, R-03, R-04 | CRS-001…007, GC-1 |
| S-05 Loss of generation | R-07, R-08, R-15, R-35, R-36 | CRS-010, CRS-011, CRS-020, CRS-021, CRS-048 |
| S-06 False market telemetry | R-34 | CRS-047 |
| S-07 Loss of view | R-13, R-14, R-16, R-37, R-40 | CRS-019, CRS-022, CRS-049 |
| S-08 Auxiliary manipulation | R-10, R-11 | CRS-015, CRS-016 |
| S-09 Loss of configuration and recovery | R-18, R-20, R-27 | CRS-023, CRS-024, CRS-027, CRS-028, CRS-036 |
| S-10 Persistent vendor access | R-28, R-29, R-30, R-31, R-32 | CRS-038…045, CRS-057…062 |

---

## 15. Deviations and approval

### 15.1 Deviation process

A requirement that cannot be met shall be raised as a **formal deviation before contract award**, stating: the requirement, why it cannot be met, the residual risk that results, the compensating control proposed, and the residual risk after that control. Deviations are accepted by the authority the risk band requires under document 04 §5 — **Extreme residual risk cannot be accepted below board level.**

A requirement discovered to be unmet at FAT or SAT is a **defect**, not a deviation.

### 15.2 Approval

| Role | Name | Signature | Date |
|---|---|---|---|
| Asset owner representative | | | |
| Operations manager | | | |
| Engineering manager | | | |
| Risk / HSE representative | | | |
| Assessor | Epiphane Zaré | | 14 Sept 2026 |

**Confirm at signature:** the four governing constraints in §3 as written; the assumptions in Annexure B, particularly A-01, A-07 and A-10; the hold points in §9.1; the regulatory characterisations in Annexure D; and that CRS-007 and CRS-061 are accepted as non-negotiable.

---

## 16. Revision history

| Rev | Date | Change |
|---|---|---|
| 0.1 | 14 Sept 2026 | Initial draft for asset owner review |
| 0.2 | 14 Sept 2026 | Five arbitrations applied. **Z-05 split** into Z-05a Engineering (SL-T 3) and Z-05b Plant information (SL-T 2); conduit C-13 created; CRS-027a and CRS-027b added. **CRS-009** now names the hydraulic servomotor restriction as the enforcing mechanism and forbids a logic rate limit being offered in its place. **GC-2 / A-01** given an explicit verification method and its dependency on the ZCR 5 recalibration stated. **Annexure D §13.1** rewritten as a conditional applicability test — the 30 MW / SRAS threshold means a 20 MW station does not cross it on its own. ZCR 4 life-safety override widened, following the ZCR 5 priority scoring. |

---

*72 requirements · 4 governing constraints · 40 hold points · 9 zones · 13 conduits · IEC 62443-3-2 ZCR 6 · KCH-CYB-CRS-001 rev 0.2*
