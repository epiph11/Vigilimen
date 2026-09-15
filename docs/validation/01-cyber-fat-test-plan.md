# Cyber Security Factory Acceptance Test Plan

**Kanangra Creek Hydro Station — 20 MW run-of-river generating station**
**Ref:** KCH-CYB-FAT-001 · **Revision:** 0.1 — DRAFT · **Date:** 14 September 2026
**Specification under test:** KCH-CYB-CRS-001 rev 0.2
**Prepared by:** Epiphane Zaré

> ⚠ **Fictional facility.** Kanangra Creek is a worked example. This plan demonstrates method against a specification, not a delivered system.

---

## 1. What a cyber FAT is, and what it is not

A Factory Acceptance Test proves that **the system as built meets the specification, in a controlled environment, before it reaches the site.**

That last clause is the whole point. The FAT is the **last cheap place to find a defect**. A shared account discovered in the factory is a configuration change; the same account discovered at SAT is a site visit; discovered after energisation it is a change request against a running generator with production at stake and a commercial argument about who pays. The cost of a defect rises by roughly an order of magnitude at each of those boundaries, and a cyber FAT exists to move findings to the left of them.

**A cyber FAT is not a penetration test.** It is a *conformance* test: each case maps to a numbered requirement, and the result is pass, fail, or conditional-with-punch-item. Exploratory testing is valuable and has its place, but it cannot be the acceptance basis, because a test with no defined pass criterion cannot be failed and therefore cannot be passed.

### 1.1 The rule that decides whether this plan is worth running

> **Test that the control cannot be bypassed, not that the control exists.**

A test that confirms a feature is present proves the integrator read the specification. A test that attempts the thing the requirement forbids proves the requirement is *enforced*. Every case in this plan that carries a **negative step** is doing the second job, and those are the steps that find defects.

Examples of the difference, drawn from this plan:

| Weak test | The test in this plan |
|---|---|
| "Confirm each operator has an account" | Attempt to log in with the vendor's commissioning account. It must fail |
| "Confirm session recording is enabled" | Open a session, disable recording as the vendor user, re-open. Recording must persist and the attempt must be logged |
| "Confirm the write allow-list is configured" | Write to a tag that is not on the list, from a host that is. It must be refused, and refused *at the controller*, not merely absent from the HMI |
| "Confirm the rate limit is set" | Command maximum closure rate with the limit removed from governor logic. Closure time must not change |

---

## 2. Entry criteria

The FAT does not start until all of these hold. **An integrator who asks to begin without them is asking to spend the window debugging the test environment rather than testing the system.**

| # | Entry criterion | Evidence |
|---|---|---|
| E-1 | CRS rev 0.2 issued and under change control | Issue record |
| E-2 | Design review complete; all design-review hold points closed (CRS-020, CRS-046, CRS-048) | Design review minutes |
| E-3 | As-built network diagram and conduit register submitted | Matches CRS Annexure A, or deviations raised |
| E-4 | Component SL-C declarations received for every component (CRS-051) | Supplier statements |
| E-5 | The system under test is **configuration-complete** — not a demonstration rig | Integrator statement + spot check |
| E-6 | Test accounts provisioned at the privilege levels each case requires, including **a deliberately low-privilege account** | Account list |
| E-7 | This plan issued to the integrator **at least 10 working days beforehand** | Transmittal |
| E-8 | Witness nominated and available for the full window | Schedule |

> **On E-7.** Issuing the test plan in advance is not a weakness. A supplier who prepares for the test is a supplier who fixes the defects before you arrive, which is exactly the outcome you want and exactly what the FAT is for. Surprise testing produces a better story and a worse plant.

> **On E-5.** The most common failure of a cyber FAT is testing a rig that is not the delivered system — a laptop standing in for the jump host, a simulator standing in for the relay, security features "to be enabled at site". Every one of those makes the test result void. **If it will not be shipped, it must not be tested.**

---

## 3. Witnessing discipline

| Role | Responsibility |
|---|---|
| **Integrator test lead** | Executes each step |
| **Asset owner witness** | Observes execution, confirms the result, signs the record. **Does not execute** |
| **Recorder** | Captures evidence as it is produced, not afterwards |

**The integrator does not execute their own test unwitnessed and submit the result.** That is a document review dressed as a test. The point of witnessing is not distrust — it is that the person who built the system knows which sequence works, and will unconsciously take it.

**Evidence is captured at the moment of execution.** A screenshot produced the following week is a screenshot of something else.

**Three rules that stop a FAT degrading into a demonstration:**

1. **The witness chooses the values.** Where a test has a parameter — which tag, which account, which port — the witness picks it at execution time, from a set the plan defines. Otherwise the integrator tests the path that works.
2. **A step that is skipped is a fail, not a gap.** "We'll cover that at SAT" is a punch item with an owner and a date, recorded as such.
3. **Partial passes do not exist at hold points.** A hold point is pass or fail. Everything else may be conditional.

---

## 4. Test cases

**Notation.** Each case carries the CRS requirement it verifies, the risk it ultimately treats, and its hold-point status. **N** marks a negative step — the step that attempts what the requirement forbids.

---

### Group A — Identity and authentication

#### FAT-01 · Individual accounts on protection relay management
**Verifies** CRS-001 · **Treats** R-01 · **HOLD POINT**

| | |
|---|---|
| **Preconditions** | Relay delivered in its shipping configuration. No changes made for the test |
| **Steps** | 1. Enumerate all accounts present in the running configuration and export the list.<br>2. Confirm each named account maps to a named individual or a named role with an accountable holder.<br>3. **N** — attempt authentication using the manufacturer's published default credentials for this model and firmware.<br>4. **N** — attempt authentication using the integrator's commissioning account.<br>5. **N** — attempt authentication using any account named in the list that the witness cannot map to a person |
| **Pass criteria** | Every account maps to an accountable holder. **Steps 3, 4 and 5 all fail to authenticate.** Each failure is logged |
| **Evidence** | Account export; authentication logs showing four failures with timestamps and source |
| **Cannot prove** | That the account set will still be this set after commissioning. Re-verified at SAT and at handover |

> **Step 4 finds more defects than step 3.** Default credentials are checked by everyone; the commissioning account nobody remembered to remove is the one that survives to operations, and it is usually the most privileged account on the device.

#### FAT-02 · Individual accounts on the governor programming interface
**Verifies** CRS-008 · **Treats** R-05 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. Enumerate accounts on the governor programming interface.<br>2. Perform a logic download as a named engineering user.<br>3. Inspect the resulting log entry.<br>4. **N** — attempt a download using a shared or generic engineering account.<br>5. **N** — attempt a download with an account that has no engineering role |
| **Pass criteria** | The log for step 3 records **account, host, timestamp and a hash of the downloaded logic** — all four. Steps 4 and 5 fail and are logged |
| **Evidence** | Log extract; screenshot of the hash recorded against the download |
| **Cannot prove** | That the hash is compared against anything. That is CRS-013, tested at FAT-14 |

> **The hash is the requirement.** A log entry saying "logic downloaded by J. Smith at 14:22" tells you a download happened. A log entry carrying the hash tells you *which logic*, which is the only version of that record with forensic value.

#### FAT-03 · Individual operator accounts
**Verifies** CRS-018 · **Treats** R-17 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. Enumerate SCADA and HMI accounts.<br>2. **N** — attempt login with any account whose name suggests shared use (`operator`, `control`, `shift`, `scada`).<br>3. Confirm an operator action taken from the HMI attributes to a named individual in the event log |
| **Pass criteria** | No shared account authenticates. Operator actions attribute to individuals |
| **Cannot prove** | That operators will not share a credential in practice. That is an operational control, and the SAT tests the *technical* preconditions for it — session timeout and lockout |

#### FAT-04 · Vendor named accounts and phishing-resistant MFA
**Verifies** CRS-043, CRS-044 · **Treats** R-32 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. Confirm each vendor identity is a named individual, not a per-company account.<br>2. Authenticate successfully with the phishing-resistant factor and confirm the central log entry.<br>3. **N** — attempt authentication with the password factor alone.<br>4. **N** — attempt authentication with a one-time code delivered by SMS or email, if any such fallback exists.<br>5. **N** — attempt authentication with a deliberately wrong factor and confirm the **failure** appears in the central log |
| **Pass criteria** | Steps 3 and 4 fail. Step 4 finding no fallback mechanism at all is the strongest pass. **Both success and failure are logged centrally** |
| **Evidence** | Central log extract showing one success and two failures |
| **Cannot prove** | That the central log is reachable from site over the real WAN. SAT |

> **Step 4 is the one to insist on.** A "phishing-resistant" deployment with an SMS fallback is a phishing-susceptible deployment with extra steps, and the fallback is usually configured for convenience during commissioning and never removed. This is the specific technical control named in SOCI s8B where the CIRMP regime applies — and it is worth having whether or not it applies, which is the position taken in CRS Annexure D.

#### FAT-05 · No default or hardcoded credentials, any component
**Verifies** CRS-055 · **Treats** multiple · **HOLD POINT**

| | |
|---|---|
| **Steps** | For every component in the delivered system — the witness selects the order:<br>1. **N** — attempt the manufacturer's documented default credentials.<br>2. Confirm any account that cannot be removed or renamed has been declared under CRS-051 as a capability gap |
| **Pass criteria** | No default authenticates. Every irremovable account is **declared, not discovered** |
| **Evidence** | Per-component result table signed by the witness |

> **An undeclared hardcoded account is a worse finding than a declared one**, and the difference matters commercially. A declared gap is a known risk the owner can treat by compensating control. An undeclared one means the supplier either did not know their own product or chose not to say — and both put every other declaration in the tender under question.

---

### Group B — Authorisation and scope

#### FAT-06 · Controller write allow-list
**Verifies** CRS-011 · **Treats** R-08, R-38 · **HOLD POINT**

| | |
|---|---|
| **Preconditions** | Allow-list configured as delivered. Test client available on the supervisory VLAN |
| **Steps** | 1. From an allowed source, write to an allowed tag. Confirm success.<br>2. **N** — from an allowed source, write to a tag **not** on the list.<br>3. **N** — from a source **not** on the list, write to an allowed tag.<br>4. **N** — repeat step 2 using a raw protocol client, bypassing the HMI entirely |
| **Pass criteria** | Steps 2, 3 and 4 are **refused at the controller**. Each refusal generates an event |
| **Evidence** | Protocol capture showing request and refusal; controller event log |
| **Cannot prove** | Behaviour under the real site traffic profile. SAT |

> **Step 4 is the case that finds the real defect.** Allow-lists are frequently implemented in the HMI's tag database rather than in the controller — which looks identical in every test that goes through the HMI, and provides no protection whatsoever against the threat the requirement exists for. The adversary does not use your HMI.

#### FAT-07 · Session scope on the jump host
**Verifies** CRS-039 · **Treats** R-28, R-32 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. Open an approved session to one target asset on one protocol. Confirm it works.<br>2. **N** — from inside that session, attempt to reach a second asset in the same zone.<br>3. **N** — from inside that session, attempt a second protocol to the same asset.<br>4. **N** — attempt to establish any network-layer route, tunnel or port forward from the session to the zone |
| **Pass criteria** | Steps 2, 3 and 4 all fail. **No network-layer path exists from the session to anything but the single approved target and protocol** |
| **Evidence** | Session recording; network capture at the zone boundary showing no traffic beyond the approved flow |
| **Cannot prove** | That the same holds when the session originates from the real internet. SAT |

> **This is the Oldsmar test.** The distinction between *access to a system* and *access to a network* is the entire difference between a controlled vendor connection and a VPN with a nicer login page, and it is the distinction most "secure remote access" products blur in their marketing.

#### FAT-08 · Just-in-time vendor access
**Verifies** CRS-045 · **Treats** R-31, R-32 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. **N** — attempt to open a vendor session with no work order. It must be refused.<br>2. Open a session against an approved work order, with operator enablement. Confirm success.<br>3. Allow the time box to expire with the session open. Confirm **auto-revocation**.<br>4. **N** — attempt to re-open the revoked session without new operator enablement.<br>5. Inspect the access configuration for any standing entitlement |
| **Pass criteria** | Steps 1 and 4 refused. Step 3 revokes without operator intervention. **No standing access is configured** |
| **Evidence** | Access log; recording of the revocation; entitlement export |

> **Step 3 must be observed, not asserted.** Expiry that requires someone to notice is not expiry, and "the session times out" frequently means "the console shows a timeout while the underlying tunnel persists".

#### FAT-09 · Unused services and ports disabled as delivered
**Verifies** CRS-054 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. For each component the witness selects, enumerate listening services and open ports as delivered.<br>2. Compare against the documented required set.<br>3. Confirm each surplus service can be disabled and **is** disabled in the shipping configuration |
| **Pass criteria** | Running configuration matches the documented required set. Surplus services are absent, not merely disableable |
| **Evidence** | Port scan output; configuration export; the required-set document |

> **"Can be disabled" and "is disabled" are different acceptance states**, and the specification requires the second. A component that ships with its web server, its discovery protocol and its diagnostic port live has met a capability requirement and failed a delivery requirement.

---

### Group C — Integrity and the independence of protective functions

#### FAT-10 · Closure-rate limit is outside programmable logic
**Verifies** CRS-009, GC-1 · **Treats** R-06, R-38, R-39 · **HOLD POINT**

| | |
|---|---|
| **Preconditions** | Hydraulic servomotor circuit as built, with the restriction fitted. Sizing calculation submitted |
| **Steps** | 1. Review the sizing calculation and the stated minimum closure time.<br>2. Command a full closure at the governor's normal rate. Record elapsed time.<br>3. **N** — remove or raise any rate limit configured in governor logic, then command maximum closure rate. Record elapsed time.<br>4. Compare. Confirm the pressure relief / synchronous bypass device operates as commissioned |
| **Pass criteria** | **Closure time in step 3 does not differ materially from step 2.** The limit is hydraulic, not logical. Measured minimum closure time matches the sizing calculation |
| **Evidence** | Timed traces from both runs; the sizing calculation; relief valve commissioning record |
| **Cannot prove** | Penstock surge behaviour with real water in the pipe. That is a hydraulic commissioning test, witnessed jointly |

> **This case is the reason the requirement was rewritten.** An adversary who owns the governor owns any limit written inside it. Water hammer is a problem of Allievi, and Allievi does not read firmware. The test is deliberately constructed so that a software-only implementation **cannot** pass it.

#### FAT-11 · Controller mode change is alarmed
**Verifies** CRS-010 · **Treats** R-07 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. Change the controller from RUN to PROGRAM. Start a stopwatch.<br>2. Observe the supervisory zone alarm. Record elapsed time.<br>3. Confirm the event carries the originating account.<br>4. Return to RUN; confirm the restoration is also recorded.<br>5. **N** — attempt the mode change by a second means (front panel, key switch, engineering tool) and confirm **each** path alarms |
| **Pass criteria** | Alarm within **10 seconds by every available path**. Originating account recorded |
| **Evidence** | Timed video or synchronised logs; alarm list extract |

> **Step 5 is where this fails in practice.** Mode change is commonly alarmed when made through the engineering tool and silent when made at the front panel — which inverts the intent, because the front panel is the path that implies someone is standing at the cabinet unannounced.

#### FAT-12 · Protection setting change generates an event
**Verifies** CRS-002 · **Treats** R-01 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. Change the active protection setting group. Start a stopwatch.<br>2. Observe the event at the supervisory zone. Record elapsed time.<br>3. Confirm the event identifies **changed group, originating account and originating host** — all three.<br>4. **N** — change a setting value within a group without changing the active group. Confirm this is also detected |
| **Pass criteria** | Event within 10 seconds carrying all three fields. Step 4 detected |
| **Evidence** | Timed log extract |

> **Step 4 tests the requirement's intent rather than its letter.** Monitoring *group selection* while ignoring *values within a group* leaves the more precise attack completely unobserved, and a literal reading of the requirement would let that pass.

#### FAT-13 · Protection out-of-service is alarmed remotely
**Verifies** CRS-004 · **Treats** R-02 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. Place a protective element out of service.<br>2. Confirm alarm at the supervisory zone **and** at the portfolio control centre — both, not either.<br>3. Confirm the alarm persists while the element is out, rather than annunciating once.<br>4. Restore; confirm the restoration is recorded |
| **Pass criteria** | Both destinations alarm. The alarm is standing, not momentary |

> **The station is normally unattended.** Local indication of a disabled protection is indication to nobody. A momentary alarm at 03:00 on an unstaffed site has the same operational value as no alarm at all.

#### FAT-14 · Golden-copy comparison is possible
**Verifies** CRS-013, CRS-025 · **Treats** R-05, R-19

| | |
|---|---|
| **Steps** | 1. Execute the documented comparison procedure against unmodified running logic. Confirm it reports no difference.<br>2. **N** — introduce a single, trivial, functionally inert change to the running logic. Re-run the comparison |
| **Pass criteria** | **Step 2 detects the change.** A procedure that cannot detect a trivial change cannot detect a deliberate one |
| **Evidence** | Both comparison reports |

> **Step 2 is the whole test.** A comparison run only against an unmodified baseline proves that the tool executes. It is also the standard way this requirement gets signed off without ever being verified.

---

### Group D — Detection and recording

#### FAT-15 · Session recording is complete and tamper-resistant
**Verifies** CRS-038 · **Treats** R-28 · **HOLD POINT**

| | |
|---|---|
| **Steps** | 1. Open a session, perform a series of actions the witness specifies, close it.<br>2. Replay the recording. Confirm every specified action is visible.<br>3. Confirm the recording is stored **outside Z-08**.<br>4. **N** — as the vendor user, attempt to disable recording, delete the recording, or open a session with recording suppressed.<br>5. Confirm each attempt in step 4 is refused **and logged** |
| **Pass criteria** | Recording complete and stored outside Z-08. Step 4 refused and logged |
| **Evidence** | Playback witnessed; storage location confirmed; log of the tamper attempts |

> **A recording the recorded party can delete is a convenience feature, not a control.** Step 4 is what separates the two, and it is skipped in almost every acceptance test of a remote access product.

#### FAT-16 · Port security on control-zone switches
**Verifies** CRS-035 · **Treats** R-26, R-39 · **HOLD POINT** *(FAT portion; completed at SAT)*

| | |
|---|---|
| **Steps** | 1. Confirm unused ports are administratively disabled in the delivered configuration.<br>2. **N** — connect an unauthorised device to a disabled port. Confirm no link, no address, no traffic.<br>3. **N** — connect an unauthorised device to an **enabled** port. Confirm port security or 802.1X refuses it.<br>4. Confirm each refusal generates an event |
| **Pass criteria** | Steps 2 and 3 refused and logged |
| **Cannot prove** | Physical port blocking, and the real port population. **SAT**, where the count of live unused ports is frequently the finding |

---

## 5. Exit criteria

| # | Exit criterion |
|---|---|
| X-1 | **Every FAT hold point passed.** No hold point may be closed by punch item |
| X-2 | Every non-hold-point case passed, or carried as a punch item with owner, date and agreed interim position |
| X-3 | Punch list signed by both parties (format: KCH-CYB-PUNCH-001) |
| X-4 | Evidence pack assembled and transmitted — logs, captures, configuration exports, timed traces |
| X-5 | Deviations raised under CRS §15.1 and dispositioned. **A requirement found unmet at FAT is a defect, not a deviation** |
| X-6 | SAT plan updated with everything this FAT could not prove |

> **X-6 is the step that is always skipped, and it is the one that makes the FAT worth running.** Each "cannot prove" note in §4 is an input to the SAT plan. A SAT plan that repeats the FAT plan is a defect in the SAT plan: SAT exists for exactly what the factory could not represent.

---

## 6. What a cyber FAT cannot prove

Stated at the front of the report, not buried, because acceptance documents are read for what they claim and a plant is operated on what they omit.

| | Why not |
|---|---|
| **Anything about the site** | Different network, different physical access, different people, different cable runs |
| **Real-world remote access** | The factory jump host is not reached from the real internet, through the real firewall, with the real identity provider |
| **Segmentation under real traffic** | A rule set that holds against test traffic may not hold against production protocol behaviour, broadcast storms or a failed redundancy switchover |
| **Logging paths end to end** | Central logging in the factory is a local collector. Whether events survive the real WAN is a SAT question |
| **Recovery** | Restoration is tested at SAT (CRS-024), because the thing being recovered is the site's configuration, not the factory's |
| **Anything about operations** | Credential sharing, unregistered cables, standing vendor sessions, emergency firewall rules never withdrawn. These are 62443-2-1 obligations and they decay from the day of handover |
| **The independence of protection with real water** | Hydraulic behaviour needs a penstock |

---

## 7. Approval

| Role | Name | Signature | Date |
|---|---|---|---|
| Asset owner witness | | | |
| Integrator test lead | | | |
| Engineering manager | | | |
| Plan author | Epiphane Zaré | | 14 Sept 2026 |

---

## 8. Revision history

| Rev | Date | Change |
|---|---|---|
| 0.1 | 14 Sept 2026 | Initial draft against CRS rev 0.2 |

---

*16 test cases · 16 CRS hold points verified at FAT · KCH-CYB-FAT-001 · Fictional facility, worked example*
