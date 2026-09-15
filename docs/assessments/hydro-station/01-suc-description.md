# ZCR 1 — System under Consideration

**Assessment:** IEC 62443-3-2 cyber security risk assessment
**SUC:** Kanangra Creek Hydro Station — 20 MW run-of-river generating station
**Document:** 01 of 12 · **Status:** DRAFT for asset owner review · **Date:** 14 Sept 2026
**Author:** Epiphane Zaré

> ⚠ **This is a fictional facility** built as a worked example. It is modelled on the architecture of a real small run-of-river station but describes no actual asset. Every operating assumption in §6 is an assumption, not a finding.

---

## 1. Purpose

IEC 62443-3-2 requires the System under Consideration to be defined before anything else, because **where the SUC stops is where accountability stops**. A boundary that is vague in this document becomes a zone that nobody owns in the partition, and a requirement nobody is contracted to meet in the CRS.

This document establishes the boundary and enumerates every access point crossing it. Nothing else in the assessment is valid if this is wrong.

---

## 2. Facility overview

| Attribute | Value |
|---|---|
| Type | Run-of-river hydroelectric generating station |
| Installed capacity | 20 MW, single Francis turbine-generator unit |
| Operating mode | Normally unattended, remotely supervised from a portfolio control centre |
| Staffing | Roving operator, ~2 site visits per week; maintenance crews as scheduled |
| Connection | 132 kV transmission via on-site step-up transformer and switchyard |
| Market role | Registered generator providing operational telemetry to the market operator |
| Intake | Weir and intake structure **4.2 km upstream**, unstaffed, telemetry over licensed radio |

### ⚠ Verify before external use

Two regulatory characterisations in this document are **assumed, not verified**, and both change the assessment materially:

1. **Whether this station meets the SOCI Act *critical electricity asset* threshold.** The asset-class test applies at defined capacity and connection thresholds; a 20 MW station may qualify on its own, or only as part of an operator's aggregate portfolio. Verify against the SOCI asset-class definitions before asserting CIRMP applicability.
2. **The market registration category and its telemetry obligations.** Whether this unit is scheduled, semi-scheduled or non-scheduled determines what data must flow to the market operator, how fast, and with what availability obligation — which directly sets the SL-T of conduit **C7**.

Both are flagged again in §7.

---

## 3. SUC boundary

### In scope

Everything within the following, whether or not it is networked:

- The **powerhouse**: turbine, generator, exciter, governor, unit control system, protection relays, station auxiliaries, local HMI, and the powerhouse LAN
- The **switchyard** control and protection, up to and including the 132 kV circuit breaker control and protection interfaces
- The **intake and weir** instrumentation, gate actuation and its telemetry link
- The **plant information layer**: station historian, engineering workstation, local time source
- The **site DMZ** and every device within it
- All **conduits** crossing the SUC boundary, including the controls applied to them

### Out of scope

- The **corporate IT network** and enterprise services (identity, email, ERP). The SUC terminates at the DMZ's northbound interface.
- The **portfolio control centre** as a system. Its *connection* to this station is in scope as a conduit; its internal architecture is a separate SUC.
- The **market operator's** systems. In scope only as the far end of conduit C7.
- The **transmission network** beyond the station's connection point.
- **Physical dam structural integrity** and civil works, except where a cyber event can influence them through gate control or level telemetry — which it can, and §5 of document 02 treats that as a primary consequence.

### Boundary statement

> The SUC comprises all industrial automation and control systems, instrumentation, protection and supporting information systems located at the Kanangra Creek powerhouse, switchyard and upstream intake, together with the site demilitarised zone, and every communication path crossing the outer boundary of that set.

---

## 4. Asset inventory (summary)

Full register is maintained separately. This is the assessment-relevant view.

### Level 0 — Process and equipment

Francis turbine and wicket gates · synchronous generator · brushless exciter · main inlet valve · intake gates and trash rack · spillway gate · penstock · step-up transformer · 132 kV circuit breaker and disconnectors · station service transformer · cooling water and lubrication oil systems · drainage and dewatering pumps · compressed air · fire detection and suppression

### Level 1 — Control and protection

| Asset | Function | Vendor class | Protocols |
|---|---|---|---|
| Digital governor | Speed and load control, wicket gate positioning | Turbine OEM | Proprietary + Modbus TCP |
| Unit control PLC | Start/stop sequencing, synchronisation, interlocks | Major automation vendor | Modbus TCP, OPC UA |
| Generator protection relay | Differential, overspeed, loss of field, overcurrent | Protection OEM | IEC 61850 MMS + GOOSE |
| Transformer protection relay | Differential, Buchholz, thermal | Protection OEM | IEC 61850 |
| Line protection relay | Distance, overcurrent, breaker fail | Protection OEM | IEC 61850 |
| Automatic voltage regulator | Excitation control | Exciter OEM | Proprietary serial |
| Auxiliaries PLC | Cooling, lube oil, drainage, air, HVAC | Major automation vendor | Modbus TCP |
| Intake RTU | Gate position, headwater/tailwater level, trash rack differential | RTU vendor | DNP3 over radio |
| **Hardwired overspeed trip** | Mechanical/electrical trip, independent of all of the above | — | **None — hardwired** |

### Level 2 — Supervisory

Station SCADA server (redundant pair) · powerhouse control room HMI · local alarm annunciator · GPS/NTP time source · station Ethernet switches (station bus and process bus)

### Level 3 — Plant information

Station historian · engineering workstation (governor, PLC and relay configuration toolchains) · local file share for configuration backups · patch/AV staging server

### Level 3.5 — DMZ

Data replication node (historian northbound) · remote access jump host · protocol gateway for control-centre and market-operator telemetry · DMZ firewall pair

---

## 5. Access points crossing the SUC boundary

**This list is the single most important output of ZCR 1.** Every entry becomes a conduit in ZCR 3, and every conduit acquires an SL-T. An access point omitted here is a control nobody specifies and nobody tests.

| # | Access point | Direction | Medium | Purpose | Normally active? |
|---|---|---|---|---|---|
| **AP-01** | Portfolio control centre supervisory link | Bidirectional | Fibre WAN, operator-owned | Remote supervision, setpoint and start/stop dispatch | **Yes, continuous** |
| **AP-02** | Market operator telemetry | Outbound (+ inbound dispatch) | Dedicated market network | Operational telemetry, dispatch signalling | **Yes, continuous** |
| **AP-03** | Corporate IT network | Bidirectional, DMZ-terminated | Fibre WAN | Historian replication north, identity, patch distribution | **Yes, continuous** |
| **AP-04** | Vendor remote access — governor OEM | Inbound | Internet → DMZ jump host | Diagnostics, firmware, tuning | On request |
| **AP-05** | Vendor remote access — protection OEM | Inbound | Internet → DMZ jump host | Relay setting review, firmware | On request |
| **AP-06** | Vendor remote access — SCADA integrator | Inbound | Internet → DMZ jump host | Configuration, graphics, alarm changes | On request |
| **AP-07** | Intake telemetry radio link | Bidirectional | Licensed point-to-point radio, 4.2 km | Level, gate position, gate command | **Yes, continuous** |
| **AP-08** | Cellular backup for intake | Bidirectional | Public cellular, APN | Failover for AP-07 | Standby |
| **AP-09** | Engineering laptops (maintenance crews) | Inbound, transient | Physical connection in powerhouse | Commissioning, fault-finding, config changes | Transient |
| **AP-10** | Removable media | Inbound, transient | USB | Firmware, configuration backup restore | Transient |
| **AP-11** | Physical access — powerhouse | Inbound | Doors, access control | Operations and maintenance | Controlled |
| **AP-12** | Physical access — intake structure | Inbound | **Fence and padlock only** | Maintenance | **Uncontrolled in practice** |
| **AP-13** | Fire and security systems interface | Outbound | Separate monitored line | Alarm to monitoring centre | Continuous |
| **AP-14** | Time synchronisation | Inbound | GPS antenna | Protection and sequence-of-event timestamping | Continuous |

### Three access points that deserve attention now

**AP-12, physical access to the intake.** Four kilometres from the powerhouse, behind a fence and a padlock, containing an RTU that commands a gate. Per 62443-3-2 ZCR 3 this is both a wireless zone and an externally-accessible zone, and both flags point the same way. It is the cheapest way into this facility and it does not require a network at all.

**AP-14, the GPS time source.** Protection schemes and sequence-of-event records depend on it. GPS spoofing is neither theoretical nor expensive. A protection scheme with corrupted time is a protection scheme whose post-event forensics cannot be trusted — and in some schemes, one that misoperates.

**AP-10, removable media.** It is the access point that has no network control at all, and it is how Stuxnet crossed an air gap. It gets a conduit in ZCR 3 like any other.

---

## 6. Operating environment assumptions

**Assumptions are load-bearing.** If one of these is false, the SL-T derived from it is wrong. Each is stated so it can be falsified by inspection, and each must be confirmed by the asset owner at ZCR 7.

| # | Assumption | If false, the effect is |
|---|---|---|
| A-01 | The hardwired overspeed trip operates independently of every programmable device in the SUC | Catastrophic — the last-resort mechanical protection becomes software-dependent, and the unit control zone's SL-T rises to 4 |
| A-02 | Powerhouse physical access is controlled and logged | The transient access points AP-09/AP-10 lose their primary compensating control |
| A-03 | The intake structure is *not* effectively access-controlled | Already assumed adverse — no relief available, drives the intake zone design |
| A-04 | No wireless exists inside the powerhouse | If false, a new zone is required and the partition changes |
| A-05 | The protection relays' settings groups can only be changed locally or over an authenticated session | If false, remote setting change becomes a credible path to defeating protection |
| A-06 | The control centre link (AP-01) cannot command the governor directly, only the unit control PLC | If false, the control centre becomes part of the unit control zone rather than a conduit peer |
| A-07 | Market operator dispatch (AP-02) is advisory to a human or to the unit PLC, not a direct actuator | If false, C7's SL-T rises and an external party sits inside the control loop |
| A-08 | Vendor remote access is brokered through the DMZ jump host, never a network-level VPN into the plant | If false, AP-04/05/06 collapse into a single high-consequence path |
| A-09 | Configuration backups exist, are current, and have been restore-tested | Recovery time assumptions in the consequence analysis are unfounded |
| A-10 | The station can operate under local manual control with all external links severed | The CIRMP s8C operational-independence position is unsupported |

---

## 7. Regulatory and policy context

| Instrument | Relevance | Status |
|---|---|---|
| **SOCI Act 2018 + Enhanced CIRMP Rules 2026** | If this is a critical electricity asset, the CIRMP obligations apply — including **s8C network segregation supporting three months of independent operation** | ⚠ **Applicability to be verified** — see §2 |
| **AESCSF v2 (2023 Core)** | The energy-sector framework; SP-2 is the enhanced CIRMP level | Applicable if the operator nominates it |
| **AS IEC 62443** series | The method used by this assessment | Voluntary; sits *underneath* a nominated CIRMP framework, and appears in neither approved-framework table |
| **ASD Essential Eight** | ML2 under the enhanced rules | Enterprise-oriented; maps poorly onto Level 0–2. Say so rather than forcing it |
| **Market operator rules** | Telemetry and dispatch obligations on AP-02 | ⚠ **Category to be verified** — see §2 |
| **Dam safety and environmental licence** | Spillway and environmental flow obligations reachable through gate control and level telemetry | Applicable |

The important observation for the CRS: **none of the five frameworks approved under the CIRMP Rules is OT-native.** Essential Eight is a Windows-centric enterprise control set, ISO 27001 is a management system, NIST CSF is outcomes. AESCSF and C2M2 are the only two written with energy OT in mind. This assessment therefore uses 62443 as the method and maps its output onto whichever framework the operator has nominated — which is the normal practice and should be stated plainly rather than glossed.

---

## 8. What the asset owner must decide

ZCR 7 requires asset owner approval. These are the decisions that cannot be made by the assessor:

1. **Confirm or reject each assumption in §6**, particularly A-01, A-07 and A-10.
2. **Confirm the SOCI and market-registration characterisations** in §2.
3. **Confirm the out-of-scope list in §3.** Specifically: is the portfolio control centre genuinely a separate SUC with its own assessment, or is this station being assessed in isolation because no such assessment exists?
4. **Confirm AP-12 is as weak as assumed.** If the intake is better protected than stated, the partition changes.
5. **Nominate the CIRMP framework** so the CRS can map to it.

---

## 9. Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 14 Sept 2026 | Initial draft for review |
