# ZCR 3 — Zone and conduit partition

**SUC:** Kanangra Creek Hydro Station · **Document:** 03 of 12 · **Status:** DRAFT · **Date:** 14 Sept 2026

---

## 1. The partitioning rule

> **Zones are drawn from consequence, not from network topology and not from Purdue level.**

This is the single most misapplied idea in 62443. A zone is *a grouping of assets sharing common security requirements*. A zone may span Purdue levels; a Purdue level will usually contain several zones. Drawing the partition by redrawing the network diagram produces zones that match the switches you already have, which is a description of the past rather than a requirement on the future.

IEC 62443-3-2 additionally **requires** separation of four categories, regardless of what consequence analysis alone would suggest:

| Required separation | Where it applies here |
|---|---|
| Business / IT assets | Z-08, outside the SUC boundary |
| **Safety-related assets** | **Z-01 — protection and trip** |
| **Wireless devices** | **Z-06 — intake, over licensed radio** |
| **Temporarily or externally connected devices** | **Z-07 — transient engineering, and conduits C-09/C-10** |

Three of the four are load-bearing in this partition. That is not a coincidence: they are the separations most often skipped.

---

## 2. Zones

Eight zones. Each carries a proposed **SL-T** — a *target* security level, expressed as the attacker capability the zone must withstand, derived from the consequence ratings in document 02.

> **SL is defined by attacker capability, not control count.**
> **SL 1** casual or coincidental · **SL 2** intentional, simple means, low resources, generic skills · **SL 3** intentional, sophisticated means, moderate resources, **IACS-specific skills** · **SL 4** as SL 3 with extended resources and high motivation — nation-state.

### Z-01 · Protection and trip

| | |
|---|---|
| **Assets** | Generator, transformer and line protection relays; hardwired overspeed trip; trip circuits; process bus |
| **Purdue** | 1 (spans into 0 via trip circuits) |
| **Drives from** | S-04 (consequence 5), S-01 (consequence 5) |
| **Proposed SL-T** | **3** |
| **Rationale** | Defeating protection requires IACS-specific skill — relay configuration tooling, protection engineering knowledge, and awareness of which setting group matters. That is the definition of SL 3. It is not SL 4: this is a 20 MW station, not a systemically significant asset, and SL 4 implies nation-state resourcing against *this* target specifically. |
| **Hard constraint** | **No security control may be placed in the trip path.** A control that can fail closed on a protective function has made the plant less safe, not more. Any control protecting this zone acts on its *management* interfaces, never on its protective action. This constraint is non-negotiable and belongs verbatim in the CRS. |

### Z-02 · Unit control

| | |
|---|---|
| **Assets** | Digital governor, unit control PLC, AVR, synchronising equipment, main inlet valve control |
| **Purdue** | 1 |
| **Drives from** | S-01 (5), S-02 (5) |
| **Proposed SL-T** | **3** |
| **Rationale** | Causing overspeed or water hammer requires understanding turbine control — gate sequencing, closure rates, load rejection behaviour. Generic IT skill does not produce S-01 or S-02; IACS-specific skill does. |
| **Conditional** | **If assumption A-01 is false** — if the overspeed trip depends on any programmable device in this zone — **SL-T rises to 4**, because the last independent barrier would then be inside the zone being attacked. Confirm A-01 by inspection before accepting SL-T 3. |

### Z-03 · Station auxiliaries

| | |
|---|---|
| **Assets** | Auxiliaries PLC: cooling water, lubrication oil, drainage and dewatering, compressed air, HVAC |
| **Purdue** | 1 |
| **Drives from** | S-08 (4) |
| **Proposed SL-T** | **2** |
| **Rationale** | The cascade to machine damage is real, but it is slow and observable, and it does not require turbine-control knowledge. Separated from Z-02 because a 4 does not belong in the same zone as a 5 — but separated *from the general plant network* too, because the reflex to treat auxiliaries as non-critical is exactly what S-08 exploits. |
| **Note** | This is the zone most likely to be challenged as over-engineered, and the one where the challenge should be resisted. |

### Z-04 · Supervisory control

| | |
|---|---|
| **Assets** | SCADA server pair, control room HMI, alarm annunciator, station bus switches, GPS/NTP time source |
| **Purdue** | 2 |
| **Drives from** | S-07 (3, escalating), S-05 (4) |
| **Proposed SL-T** | **2** |
| **Rationale** | Direct consequence is loss of view and loss of generation, not destruction. But this zone is the **principal lateral path** to Z-02 — it holds the operator's credentials, the tooling and the routes. Its SL-T is set by its own consequence; its *control requirements* are shaped by what lies beyond it, which the conduits express. |
| **Note** | The GPS/NTP source sits here and feeds Z-01. A spoofed time source degrades protection forensics and some protection schemes — a small asset with a consequence disproportionate to its cost, and worth calling out in the CRS. |

### Z-05a · Engineering

| | |
|---|---|
| **Assets** | **Engineering workstation** with governor/PLC/relay toolchains, configuration backup store, patch and AV staging |
| **Purdue** | 3 |
| **Drives from** | S-09 (5) |
| **Proposed SL-T** | **3** |
| **Rationale** | **This zone is rated higher than the supervisory zone above it, and that is deliberate.** The engineering workstation holds the tooling that can reprogram Z-01 and Z-02; the backup store determines whether a bad day is a bad week or a bad year. Purdue level is not consequence. The engineering workstation is the pivot in Stuxnet, in TRITON, and in most real intrusions — treating it as ordinary plant IT is the standard mistake this partition exists to avoid. |

### Z-05b · Plant information

| | |
|---|---|
| **Assets** | Station historian, documentation store, reporting and trend clients |
| **Purdue** | 3 |
| **Drives from** | S-09 (3 — disclosure, not destruction) |
| **Proposed SL-T** | **2** |
| **Rationale** | Read-mostly. Its worst direct consequence is disclosure of settings and diagrams (R-20, consequence 3); it holds no tooling that can write to a controller. Rating it 3 would impose the engineering zone's requirements on people whose job is to look at trends. |
| **Note** | Its *enabling* value is high — exfiltrated settings and diagrams are what make R-05 and R-19 achievable. That contribution is carried on the ZCR 5 attack-path sheet, not inflated into this zone's SL-T. |

> **Decision, 14 September 2026 — the split of Z-05.** ZCR 3 left this open for ZCR 5 to decide on the real network facts. It is now decided: **split**.
>
> The trigger is the standard one. Z-05 was rated SL-T 3 **because of one asset**. Everything else in it was carrying a target it did not earn, which costs three times over — in requirements, in hardening, and in friction for users who only read trends. When a single asset drives a whole zone's SL-T, that is the textbook condition for splitting it.
>
> The argument against was recorded honestly at ZCR 3 and has not gone away: a zone of one or two assets sharing a cabinet, a switch and an administrator is an administrative fiction. The answer is that the split is **logical, not civil** — same room, same rack, separated by a conduit (**C-13**) and by administrative separation of the toolchain from the historian. That is achievable on a small station, and the ZCR 5 SL gap sheet records the result: **Z-05b's gap closes to zero by separation alone, at no capital cost.** A zone that reaches its target by being correctly drawn is the cheapest control in the assessment.
>
> Consequential changes: register risks R-18, R-19, R-21 → Z-05a; R-20 → Z-05b at SL-T 2. Conduits C-04 and C-05 re-terminate. New conduit C-13.

### Z-06 · Intake and weir

| | |
|---|---|
| **Assets** | Intake RTU, gate actuation, level instrumentation, trash rack differential, spillway gate control, radio terminal |
| **Purdue** | 1–2, geographically remote |
| **Drives from** | S-03 (5) |
| **Proposed SL-T** | **3** |
| **Rationale** | Three separation triggers coincide: high consequence, **wireless** (mandatory separation), and **physical access effectively uncontrolled** (AP-12, assumption A-03). The consequence is third-party flooding and environmental breach, which is not recoverable by restarting anything. |
| **Design implication** | Because physical access cannot be assumed, controls must survive an adversary standing at the RTU. That points to cryptographic authentication on the link and to command validation *at the receiving end* rather than trust in the sender — and it means the conduit, not the endpoint, carries most of the security burden. |

### Z-07 · Transient and externally connected

| | |
|---|---|
| **Assets** | Maintenance engineering laptops, removable media, vendor-supplied devices, temporary test equipment |
| **Purdue** | Any — that is the point |
| **Drives from** | S-09, S-10, and the 62443-3-2 mandatory separation |
| **Proposed SL-T** | **3** |
| **Rationale** | A zone that has no permanent membership. Devices enter it when they arrive on site and leave when they go. It exists because the alternative — treating a laptop that was on a hotel network yesterday as a member of Z-02 today — is how air gaps are crossed. Rated at the consequence of the zones it can reach. |

### Z-08 · Site DMZ

| | |
|---|---|
| **Assets** | Historian replication node, remote access jump host, protocol gateway (control centre and market operator), DMZ firewall pair |
| **Purdue** | 3.5 |
| **Drives from** | S-10 (5), S-06 (4) |
| **Proposed SL-T** | **3** |
| **Rationale** | Every external path terminates here and nothing crosses it unbrokered. Its consequence is inherited from everything behind it. The jump host in particular is the single most valuable asset in the SUC to an external adversary, because it is the one designed to be reachable. |

---

## 3. Conduits

A conduit is a communication path between zones **plus the controls on it**. A conduit is itself a zone type and carries its own SL-T — commonly **higher** than the zones it joins, because it crosses a boundary that exists for a reason.

| ID | From ↔ To | Medium / protocol | Purpose | SL-T | Note |
|---|---|---|---|---|---|
| **C-01** | Z-01 ↔ Z-02 | IEC 61850 GOOSE + hardwired trip | Protection signalling and trip | **3** | The hardwired element must remain outside any programmable control |
| **C-02** | Z-02 ↔ Z-04 | Modbus TCP / OPC UA | Supervision, setpoints, start/stop | **3** | Rated to the higher endpoint. The primary lateral path to the machine |
| **C-03** | Z-03 ↔ Z-02 | Modbus TCP | Auxiliary status and permissives | 2 | |
| **C-04** | Z-04 ↔ Z-05b | OPC UA / historian collector | Historisation | 2 | Should be one-way in intent; candidate for a data diode |
| **C-05** | Z-05b ↔ Z-08 | Historian replication | Northbound data | 2 | |
| **C-06** | Z-06 ↔ Z-04 | **DNP3 over licensed radio** | Level, gate position, gate command | **3** | Wireless, physically exposed at the far end, commands a gate. See §4 |
| **C-07** | Z-08 ↔ market operator | Market network protocol | Telemetry and dispatch | **3** | SL-T **conditional on assumption A-07** — if dispatch actuates rather than advises, this conduit is inside the control loop |
| **C-08** | Z-08 ↔ portfolio control centre | Operator WAN | Remote supervision and dispatch | **3** | |
| **C-09** | **Vendor remote access** → Z-08 → targets | Internet → brokered session | OEM diagnostics and configuration | **3** | **The highest-consequence conduit in the plant.** See §4 |
| **C-10** | Z-07 → any zone | Physical connection, USB | Maintenance and commissioning | **3** | Has no network control at all. It is how Stuxnet crossed an air gap |
| **C-11** | Z-08 ↔ corporate IT | Operator WAN | Identity, patching, replication | 2 | The SUC boundary. Nothing crosses unbrokered |
| **C-12** | GPS → Z-04 | RF | Time synchronisation | 2 | Unauthenticated by nature; treat as untrusted input |
| **C-13** | Z-05a ↔ Z-05b | File transfer / historian query | Engineering reads plant data; documentation lands in the store | **3** | Created by the Z-05 split. Rated to the higher endpoint. **One-way in intent, engineering → plant information** — the reverse direction is how exfiltrated settings would leave, and how a compromised historian would reach the toolchain |

---

## 4. The two conduits that carry the assessment

### C-09 — vendor remote access

In 62443 terms this is a conduit, and it is almost always the one with the **highest SL-T in the plant**, because it crosses the most zone boundaries and because its consequence is the maximum of everything it can reach.

The design distinction that matters: **a VPN grants network access; brokering grants session access to one asset over one protocol.** The first is a hole through every zone boundary it traverses; the second is a mediated conversation. A vendor with a VPN into the plant is a member of every zone that VPN can route to, whatever the network diagram claims.

Required properties, which flow into the CRS:

- Terminates in Z-08. **Never into a control zone.**
- Per-individual named accounts. Never a shared vendor login.
- **Phishing-resistant MFA** — now a CIRMP **s8B** obligation, with central logging of successful *and* unsuccessful authentication.
- Just-in-time, time-boxed, tied to an approved work order, with **an operator on site enabling the session**.
- Full session recording, with the ability to terminate mid-session.
- Least privilege to **one asset and one protocol**, not to a VLAN.

### C-06 — the intake radio link

DNP3 over licensed radio, to an RTU behind a padlock four kilometres away, that commands a gate whose misoperation floods third parties.

The uncomfortable property: **the adversary can be standing at the far end.** Physical presence at the intake is not a defeated control, it is an assumed condition (A-03). So the conduit cannot rely on the endpoint being trustworthy. What follows is that command *validation* must happen at the receiving end — gate movement constrained by independently-sensed conditions rather than by the instruction alone — and that the link itself needs cryptographic authentication, which plain DNP3 does not provide. **DNP3 Secure Authentication exists; whether this RTU supports it is a vendor capability question, and it is exactly the kind of question the CRS should force a supplier to answer with an SL-C claim.**

---

## 5. Partition summary

| Zone | SL-T | Highest consequence |
|---|---|---|
| Z-01 Protection and trip | **3** | 5 |
| Z-02 Unit control | **3** *(4 if A-01 false)* | 5 |
| Z-03 Station auxiliaries | 2 | 4 |
| Z-04 Supervisory control | 2 | 4 |
| Z-05a Engineering | **3** | 5 |
| Z-05b Plant information | 2 | 3 |
| Z-06 Intake and weir | **3** | 5 |
| Z-07 Transient and externally connected | **3** | inherited |
| Z-08 Site DMZ | **3** | inherited |

Nine zones. Seven of thirteen conduits are SL-T 3.

### Two observations a reviewer should test

**Z-05a is rated above Z-04, inverting Purdue.** That is the intended result of drawing zones from consequence. If a reviewer objects that a Level 3 zone cannot outrank a Level 2 zone, the answer is that Purdue describes function, not consequence, and the engineering workstation can reprogram the machine while the HMI can only ask it politely. The split of Z-05 sharpens this rather than softening it: the zone that outranks Purdue is now *only* the tooling, and the historian sitting at the same Purdue level is rated 2.

**Nothing is SL-T 4.** That is a judgement, and it should be contested. The argument for SL-T 4 on Z-01 and Z-02 is that TRITON demonstrated nation-state interest in safety systems and that hydro assets sit in a targeted sector. The argument against — and the one taken here — is that SL 4 implies extended resources directed at *this* asset, that a 20 MW non-systemically-significant station does not obviously attract that, and that **an SL-T you cannot fund is worse than an honest SL-T 3**, because it produces a paper requirement rather than a control. If the asset owner's threat assessment says otherwise, this changes and the CRS changes with it.

---

## 6. What ZCR 5 must resolve

The detailed assessment inherits three unresolved items from this partition:

1. **Confirm A-01 by inspection.** It is the difference between SL-T 3 and SL-T 4 on Z-02. **Still open** — and ZCR 5 has made it larger rather than smaller: six risks are rated at direct consequence 4 *only because* the independent trip stands behind them. Verification method is now specified: witness an overspeed test with the governor de-energised. Until that is done the register is conditional.
2. ~~Decide whether the engineering workstation splits out of Z-05~~ — **resolved 14 Sept 2026: split into Z-05a and Z-05b.** See §2.
3. **Establish whether the intake RTU supports DNP3 Secure Authentication** — an SL-C question that determines whether C-06's SL-T 3 is achievable or aspirational. **Still open.**

---

## 7. Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 14 Sept 2026 | Initial draft for review |
