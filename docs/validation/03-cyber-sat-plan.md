# Cyber Security Site Acceptance Test Plan

**Kanangra Creek Hydro Station — 20 MW run-of-river generating station**
**Ref:** KCH-CYB-SAT-001 · **Revision:** 0.1 — DRAFT · **Date:** 14 September 2026
**Specification under test:** KCH-CYB-CRS-001 rev 0.2 · **Follows:** KCH-CYB-FAT-001 rev 0.1
**Prepared by:** Epiphane Zaré

> ⚠ **Fictional facility.** A worked example against a specification, not a delivered system.

---

## 1. The rule this plan is built on

> **A SAT plan that repeats the FAT plan is a defect in the SAT plan.**

The factory already proved the system meets the specification in a controlled environment. Running those cases again at site consumes the one scarce resource on a live plant — access to the machine — and proves nothing new.

**SAT exists for exactly what the factory could not represent.** Every case in §4 traces back to a *"cannot prove"* line in the FAT plan, and the traceability is given explicitly in §3 so a reviewer can check that nothing was carried over out of habit and nothing was dropped.

Five things change between the factory and the site, and they are the entire content of this plan:

| | What changes |
|---|---|
| **The network is real** | Real switches, real cable runs, real VLANs, real broadcast traffic, real redundancy that will one day fail over |
| **The internet is real** | The jump host is reached from outside, through the real firewall, against the real identity provider |
| **Physical access is real** | Doors, cabinets, ports, a structure 4.2 km upstream behind a padlock |
| **The paths are long** | Logs must survive a WAN. Alarms must reach a control centre that is not in the next room |
| **The plant exists** | There is water, a penstock, a generator, and a configuration worth restoring |

---

## 2. Entry criteria

| # | Criterion |
|---|---|
| E-1 | FAT complete, **all FAT hold points passed** |
| E-2 | FAT punch items dispositioned and **re-decided at the shipment boundary**, not rolled |
| E-3 | Installation complete; as-built network diagram and port schedule submitted |
| E-4 | Conduit register updated to as-built and submitted against CRS Annexure A |
| E-5 | Site safety induction complete; permit-to-work arrangements agreed |
| E-6 | **A-01 verification scheduled within this window.** See §5 |
| E-7 | Rollback position agreed and tested for every case that touches a live system |

> **On E-7.** At FAT, a failed test costs a reboot. At SAT it can cost a trip. Every case below states what it touches and how it is backed out, and the ones that touch a generating unit are scheduled into an outage rather than negotiated on the day.

---

## 3. Traceability — what the factory could not prove

| FAT could not prove | SAT case |
|---|---|
| Anything about the site network | SAT-01, SAT-04 |
| Firewall rule set against real traffic | SAT-02 |
| Real-world remote access | SAT-03 |
| Physical port population and blocking | SAT-04 |
| Logging paths end to end over the real WAN | SAT-05 |
| Alarm delivery to the portfolio control centre | SAT-06 |
| Recovery of the **site's** configuration | SAT-07 |
| Physical access assumptions (A-02, A-03) | SAT-08 |
| The intake — every assumption about it | SAT-08, SAT-10 |
| Handover in maintainable form | SAT-09 |
| Independence of protection with real water | SAT-11 |

---

## 4. Test cases

**N** marks a negative step.

### SAT-01 · Segmentation enforced against real traffic
**Verifies** CRS-017, CRS-034 · **Treats** R-12, R-26 · **HOLD POINT** · *Touches: zone boundaries. Backed out by rule restore*

1. Confirm the implemented rule set matches the as-built conduit register, flow by flow.
2. From Z-04, attempt each flow to Z-02 that the register does not list. **N**
3. From Z-03, attempt to reach Z-02 other than via the registered permissive flows. **N**
4. From a corporate-IT host, attempt to reach any control zone directly. **N**
5. Force a redundancy failover on the firewall pair, and repeat steps 2 and 4 **during and after** the switchover.

**Pass:** every unregistered flow refused, including during failover. **Step 5 is the one that finds the defect** — rule state that does not survive a failover is a rule set that opens itself at the exact moment the plant is already having a bad day.

### SAT-02 · Firewall-to-register reconciliation
**Verifies** CRS-042, GC-4 · **Treats** R-30 · **HOLD POINT** · *Touches: nothing. Read-only*

1. Run the automated reconciliation between the implemented rule set and the conduit register.
2. Review every divergence.
3. Confirm divergences alarm rather than merely appearing in a report nobody opens.

**Pass:** reconciliation runs, divergences are zero or documented and dispositioned. **Any live flow absent from the register is a GC-4 breach and a defect, whether or not it is exploitable.**

### SAT-03 · Remote access from the real world
**Verifies** CRS-007, CRS-038, CRS-039, CRS-043, CRS-044, CRS-045 · **Treats** R-28, R-31, R-32 · **HOLD POINT** · *Touches: jump host. Backed out by session termination*

1. Open an approved vendor session **from outside the site**, over the real internet, through the real firewall, with the real identity provider.
2. Repeat FAT-07 steps 2–4 from this position: second asset, second protocol, network-layer route. **N**
3. **N** — attempt to reach any Z-01 management interface by any remote path. *CRS-007 requires presence in the relay room; this step must fail from every direction.*
4. Confirm the session recording is written to its store outside Z-08 and is retrievable.
5. Confirm the authentication events — success **and** failure — reach the central log over the real WAN.
6. Let the time box expire; confirm auto-revocation from outside.

**Pass:** steps 2 and 3 fail; steps 4, 5 and 6 succeed. **Step 3 is the non-negotiable one.** CRS-007 is the requirement most likely to have been quietly relaxed between factory and site, because it is the one a vendor most wants relaxed.

### SAT-04 · Physical ports and port security
**Verifies** CRS-035 · **Treats** R-26, R-39 · **HOLD POINT** · *Touches: switch ports. Backed out by re-enable*

1. Count live unused ports on every control-zone switch. Compare with the as-built.
2. **N** — connect an unauthorised device to a live unused port.
3. **N** — connect an unauthorised device to an enabled port; confirm port security or 802.1X refuses it.
4. Confirm physical blockers are fitted to disabled ports.
5. Confirm each refusal generates an event that reaches the supervisory zone.

**Pass:** live unused port count is zero; unauthorised devices refused and logged. **The count in step 1 is the finding.** As-built port schedules are optimistic almost without exception, because ports get enabled during commissioning and nobody writes it down.

### SAT-05 · Logging survives the real path
**Verifies** CRS-002, CRS-010, CRS-044, CRS-047 · *Touches: nothing beyond generating events*

1. Generate one event of each monitored class at the plant.
2. Confirm each arrives at the central log, and record the latency.
3. **N** — sever the WAN path for a defined interval, generate events, restore the path.
4. Confirm the events generated during the outage are buffered and delivered on restoration, or that their loss is alarmed.

**Pass:** events arrive; **loss during outage is either prevented or detected.** Silent loss is the failure mode — a logging chain that quietly drops events during a WAN outage is at its least reliable precisely when an adversary would most want it to be.

### SAT-06 · Alarms reach the control centre
**Verifies** CRS-004 · **Treats** R-02 · *Touches: protection element out-of-service. Outage required*

1. Place a protective element out of service.
2. Confirm the alarm at the supervisory zone **and** at the portfolio control centre.
3. Confirm the alarm is standing, not momentary.
4. Confirm the control centre operator on shift can state what the alarm means and what to do. **Ask them.**

**Pass:** both destinations, standing alarm, and step 4 answered. **Step 4 is not a formality.** The station is normally unattended; an alarm that reaches a screen nobody can interpret has the delivery characteristics of a control and none of the effect.

### SAT-07 · Restoration of the site configuration
**Verifies** CRS-023, CRS-024 · **Treats** R-18 · **HOLD POINT** · *Touches: spare hardware only. No live system*

1. Confirm the backup store is off-site, outside the plant authentication domain, and **not writable from the engineering workstation** (attempt a write — **N**).
2. Restore controller logic, relay settings and SCADA configuration to known-good on spare or isolated hardware.
3. **Record elapsed time. That number is the measured recovery time.**
4. Verify the restored configuration functions, rather than merely loading.

**Pass:** restoration succeeds and is verified. **Step 3 has no pass criterion, and that is deliberate** — the measurement is the deliverable. If it materially exceeds the assumption behind consequence scenario S-09, that is an observation against the *risk assessment*, not a defect against the integrator, and it triggers a reassessment under approval record §8.

### SAT-08 · Physical access assumptions
**Verifies** CRS-031, CRS-032 · **Treats** R-22 · **HOLD POINT** · *Touches: nothing*

1. **A-02** — confirm powerhouse access is controlled **and logged**. Inspect the log. **N** — attempt entry on a revoked credential.
2. **A-03** — travel to the intake, 4.2 km upstream. Record what actually stands between a person and the gate controller.
3. Confirm intrusion detection and camera coverage at the intake operate, and that the alarm reaches somebody who would act.
4. Confirm gate commands are validated at the receiving end rather than trusted from the sender.

**Pass:** A-02 confirmed; A-03 characterised as found; detection operational end to end.

> **A-03 was assumed adverse — that the intake is *not* effectively access-controlled.** If step 2 finds it better than assumed, R-22 drops and five Extreme risks move. If it finds it worse, nothing changes, because the assessment already assumed the worse case. **This is the value of assuming adverse: the site visit can only improve the picture.**

### SAT-09 · Handover in maintainable form
**Verifies** CRS-061 · **HOLD POINT** *(document review, executed at SAT)*

1. Receive all configuration, logic, settings and documentation in **editable source form**.
2. **N** — have an asset owner engineer, with no integrator-proprietary licence, open and modify one file of each type.

**Pass:** step 2 succeeds for every type. **A dependency discovered here is a commercial problem, and it is the last moment at which the asset owner still has leverage.** After handover the price of the toolchain is whatever the OEM says it is.

### SAT-10 · Intake conduit capability
**Verifies** CRS-029, CRS-046 · **Treats** R-23, R-33 · *Touches: intake link. Outage window*

1. Confirm whether the intake RTU supports DNP3 Secure Authentication **in the delivered firmware**, not in the datasheet.
2. If yes: enable it, verify authenticated operation, and **N** — replay a captured gate command; it must be rejected.
3. If no: record as a capability gap under CRS-051 and confirm the compensating controls in the CRS are in place.

**Pass:** either authenticated operation demonstrated, or the gap is **declared with its compensating control operating**. This closes open condition C-4 of the approval record either way.

### SAT-11 · Independence of protection, with water
**Verifies** GC-2, A-01, CRS-009 · **HOLD POINT** · *Touches: the machine. Outage and permit required*

**This case is executed jointly with mechanical and protection commissioning. It is a cyber test only in the sense that the whole risk register depends on it.**

1. De-energise the governor; place the unit control PLC in STOP.
2. Run the unit up and demonstrate that the **hardwired overspeed trip operates**, recording trip speed.
3. Record the resulting gate closure and compare against the CRS-009 sizing calculation.
4. Confirm the pressure relief / synchronous bypass device operates as commissioned.
5. Record penstock pressure through the closure.

**Pass:** the trip operates with all programmable systems dead, and closure time matches the calculation.

> **See §5. This is the most consequential hour in the whole validation programme.**

---

## 5. A-01 — the condition the assessment stands on

**A-01 is the assumption that the hardwired overspeed trip operates independently of every programmable device.** It has never been verified, and SAT-11 is where it is.

Six risks — R-12, R-17, R-26, R-35, R-38, R-39 — are rated at direct consequence 4 rather than 5 **because this trip stands behind them.**

| If SAT-11 fails | Consequence |
|---|---|
| Those six risks | Return to consequence 5 |
| Extreme band | Returns from 11 to 17 |
| Z-02 target security level | Rises to **SL 4** |
| KCH-CYB-CRS-001 | Must be reissued at a higher target |
| This programme | Is no longer in acceptance; it is in redesign |

**A certificate does not discharge SAT-11.** The claim is about independence, and independence is shown by removing the thing it is independent of. A vendor statement that the trip is hardwired describes an intent; de-energising the governor and watching the machine trip anyway describes the plant.

**Schedule SAT-11 early in the SAT window, not late.** If it fails, everything downstream of it changes, and finding that out on the last day of the window costs a mobilisation.

---

## 6. Exit criteria

| # | Criterion |
|---|---|
| X-1 | Every SAT hold point passed |
| X-2 | **SAT-11 executed and A-01 resolved**, either way |
| X-3 | Punch list re-dispositioned at the energisation boundary — every open item re-decided, none rolled |
| X-4 | As-built conduit register reconciled and signed (CRS-070) |
| X-5 | Measured recovery time recorded and compared against the S-09 assumption |
| X-6 | Commissioning runbook issued (KCH-CYB-COM-001) with SAT findings folded in |
| X-7 | Reassessment triggers from approval record §8 reviewed — **has anything found at SAT tripped one?** |

---

## 7. What SAT still cannot prove

| | Why not |
|---|---|
| **Operational discipline** | Credential sharing, unregistered cables, standing vendor sessions, emergency rules never withdrawn. These are 62443-2-1 obligations and they begin decaying at handover |
| **Detection against a real adversary** | SAT proves a control refuses a test. It does not prove it refuses someone who wants in |
| **That the partition will still be true in a year** | It is a statement about a configuration. The reassessment triggers exist because configurations move |
| **That anyone will read the alarms at 03:00** | SAT-06 step 4 asks the question. It cannot answer it for the next ten years |

---

## 8. Approval

| Role | Name | Signature | Date |
|---|---|---|---|
| Asset owner witness | | | |
| Integrator test lead | | | |
| Operations manager | | | |
| Engineering manager (SAT-11) | | | |
| Plan author | Epiphane Zaré | | 14 Sept 2026 |

---

*11 test cases · every one traced to a FAT "cannot prove" · KCH-CYB-SAT-001 · Fictional facility, worked example*
