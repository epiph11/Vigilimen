# ZCR 2 — Initial cyber security risk assessment

**SUC:** Kanangra Creek Hydro Station · **Document:** 02 of 12 · **Status:** DRAFT · **Date:** 14 Sept 2026

---

## 1. Method, and what this document is *not*

ZCR 2 is the **high-level, consequence-driven** assessment. It asks one question of each function in the SUC:

> If a capable adversary had full control of this function, what is the **worst credible** outcome?

Three deliberate constraints follow from that:

- **Pre-mitigation.** Existing countermeasures are ignored. This is the unmitigated case, and its purpose is to justify the partition in ZCR 3 — you cannot draw zones from consequence if you have already discounted the consequence.
- **No likelihood.** Likelihood belongs to ZCR 5. Introducing it here produces a partition shaped by how hard an attack *feels* rather than by what it would cost, and that is how safety-critical zones end up merged with convenience systems.
- **Worst *credible*, not worst conceivable.** A scenario requiring simultaneous defeat of independent mechanical protection and physical presence and the civil structure is not credible. A scenario requiring only a skilled actor with an IACS-specific toolkit is.

The output is a consequence rating per function against the categories in document 04, and it is the input to the partition.

---

## 2. Consequence categories

Per the tolerable-risk criteria in document 04. Summarised here for readability.

| Level | Safety | Environment | Availability | Financial | Regulatory |
|---|---|---|---|---|---|
| **5 Catastrophic** | Fatality | Uncontained release with lasting harm, or downstream flooding | > 6 months outage | > $10M | Licence revocation, prosecution |
| **4 Major** | Permanent disability | Reportable breach with remediation | 1–6 months | $1–10M | Enforceable undertaking, mandatory report |
| **3 Moderate** | Lost-time injury | Reportable, remediable | 1–4 weeks | $100k–1M | Reportable incident |
| **2 Minor** | Medical treatment | Contained, internally reportable | 1–7 days | $10–100k | Internal only |
| **1 Negligible** | First aid | None | < 1 day | < $10k | None |

---

## 3. Consequence scenarios

Each is a *worst credible* outcome assuming adversary control of the stated function, with no countermeasures.

### S-01 — Overspeed to mechanical destruction
**Function:** Governor + unit control + protection
**Scenario:** An adversary with control of the governor opens wicket gates while the unit is disconnected from the grid, or blocks closure on load rejection. The unit accelerates toward runaway speed. The generator rotor and turbine runner are not designed for sustained runaway. Fragments leave the machine.
**Worst credible outcome:** Fatality or permanent disability if personnel are in the powerhouse. Total destruction of the turbine-generator — replacement lead time for a Francis runner and rotor rewind is measured in **many months**. Penstock and civil damage possible.
**Ratings:** Safety **5** · Availability **5** · Financial **5** · Environment 2 · Regulatory 4
**Depends on assumption A-01.** If the hardwired overspeed trip is genuinely independent of every programmable device, this scenario requires defeating it separately — which is precisely why A-01 must be confirmed rather than believed. If A-01 is false, this is the single scenario that drives the whole assessment.

### S-02 — Water hammer through rapid gate closure
**Function:** Governor, main inlet valve, intake gate
**Scenario:** Commanded rapid closure of the wicket gates or main inlet valve against full flow. The pressure transient propagates up the penstock. Penstock rupture releases the full conduit volume into the powerhouse and the valley floor.
**Worst credible outcome:** Fatality. Uncontrolled water release with downstream consequence. Civil reconstruction.
**Ratings:** Safety **5** · Environment **4** · Availability **5** · Financial **5** · Regulatory **5**
This scenario is why closure-rate limits must be enforced in a place an adversary with governor access cannot reach. Where that limit lives is a design question the CRS must answer explicitly.

### S-03 — Spillway and intake gate misoperation
**Function:** Intake RTU, spillway gate control, level telemetry
**Scenario:** Gates are commanded open during high inflow, or held closed when they should pass flow; *or* level telemetry is falsified so that operators and automation act on a false picture. The falsification variant is the more dangerous one, because every human and automated response is then wrong by design.
**Worst credible outcome:** Downstream flooding affecting third parties. Environmental flow breach. Dam safety licence consequences.
**Ratings:** Safety **4** · Environment **5** · Availability 3 · Financial 4 · Regulatory **5**
The intake is behind a padlock four kilometres away (AP-12) and reachable over radio (AP-07). **High consequence, weak physical control, wireless path** — the combination that ZCR 3 exists to isolate.

### S-04 — Protection defeat, then fault
**Function:** Generator, transformer and line protection relays
**Scenario:** Protection settings are altered or trip outputs blocked. The equipment then runs unprotected. A subsequent internal fault — which protection exists precisely to clear in milliseconds — is not cleared. Generator winding or transformer destruction, with fire.
**Worst credible outcome:** Fire in the powerhouse. Transformer replacement, lead time in months. Possible fatality.
**Ratings:** Safety **4** · Availability **5** · Financial **5** · Environment 3 (oil) · Regulatory 4
**This is the TRITON pattern**: the target is not the process, it is the system that protects the process. It is also the scenario that justifies giving protection its own zone with the highest SL-T in the plant, and it is the reason no security control may ever sit in the trip path.

### S-05 — Loss of generation
**Function:** Any of unit control, supervisory, or the external links
**Scenario:** Adversary trips and holds the unit offline, or denies the control path so it cannot be restarted remotely.
**Worst credible outcome:** Extended forced outage. Under the SOCI Act this is the textbook *significant impact on availability* — **operational technology offline or unavailable** — which is the trigger for the **12-hour** critical-incident report, not the 72-hour one.
**Ratings:** Availability **4** · Financial 3 · Regulatory **4** · Safety 1 · Environment 1
Worth noting plainly: loss of generation is the consequence operators instinctively rate first, and it is *not* the worst thing in this list. S-01 through S-04 all outrank it. An assessment that ranks availability above safety has inverted the OT priority it claims to hold.

### S-06 — False telemetry to the market operator
**Function:** Protocol gateway, AP-02
**Scenario:** Telemetry reported to the market operator is falsified — availability, output or capability misrepresented — or dispatch signalling is manipulated.
**Worst credible outcome:** Contribution to a grid-level misoperation; market and regulatory consequence for the operator. A single 20 MW unit is not systemically significant alone, which caps this at Major rather than Catastrophic — **but the same technique applied across a fleet is, and that is the honest framing.**
**Ratings:** Regulatory **4** · Financial 3 · Availability 2 · Safety 1
**Depends on assumption A-07.** If dispatch is a direct actuator rather than advisory, the safety and availability ratings rise and an external party is inside the control loop.

### S-07 — Loss of view
**Function:** SCADA, HMI, historian, alarm annunciator
**Scenario:** The operator's picture is denied or falsified while the process continues. Alarms are suppressed.
**Worst credible outcome:** An unattended station running blind. Consequence is *derivative* — it converts an otherwise-detectable developing fault into an undetected one, so its true rating is the rating of whatever it conceals.
**Ratings:** Availability 3 · Safety **3, escalating** · Financial 3
Alarm suppression is an ICS technique with its own ATT&CK entry for a reason. It is rarely the objective; it is what makes the objective survivable for the attacker.

### S-08 — Auxiliary system manipulation
**Function:** Auxiliaries PLC — cooling water, lubrication oil, drainage
**Scenario:** Cooling or lubrication is degraded slowly enough that protection thresholds are approached but alarms are within tolerance, or drainage pumps are disabled and the powerhouse floods.
**Worst credible outcome:** Bearing failure and consequential machine damage. Powerhouse flooding reaching electrical equipment.
**Ratings:** Availability **4** · Financial 4 · Safety 3 · Environment 2
Auxiliaries are routinely treated as low-criticality because no single one matters. The cascade does. This is the scenario most often missed in a first partition.

### S-09 — Loss of configuration and inability to recover
**Function:** Engineering workstation, configuration backups, historian
**Scenario:** Controller logic, relay settings and SCADA configuration are corrupted or encrypted, together with the backups — which live on the same site, on the same domain, reachable from the same workstation.
**Worst credible outcome:** The station cannot be restored to a known-good state. Recovery becomes a vendor re-engineering exercise. Outage measured in months rather than days.
**Ratings:** Availability **5** · Financial **4** · Regulatory 3
This is the scenario that turns a recoverable incident into an unrecoverable one, and it is the direct link to CIRMP **s8C** — *be able to recover and restore critical systems* and *maintain availability during restoration*. It is also the scenario where the engineering workstation shows its real importance.

### S-10 — Persistent access through the vendor path
**Function:** AP-04/05/06, DMZ jump host
**Scenario:** A vendor's own environment is compromised and the trusted inbound path is used to reach the plant. The access is legitimate, credentialed, and looks exactly like maintenance.
**Worst credible outcome:** An enabler for any of S-01 to S-09, with the additional property that it is **the hardest to detect**, because it is indistinguishable from authorised work.
**Ratings:** Rated as the maximum of whatever it enables — therefore **5**
Oldsmar was not sophisticated: shared credentials and an operator who happened to be watching the screen. The failure was architectural, not technical. Supply-chain compromise of an OEM is the sophisticated version of the same architectural failure.

---

## 4. Consequence summary

Highest rating across all categories, pre-mitigation.

| Scenario | Function | Worst | Primary driver |
|---|---|---|---|
| S-01 | Governor / unit control | **5** | Safety, total machine loss |
| S-02 | Governor / inlet valve | **5** | Safety, environment, civil |
| S-03 | Intake and spillway | **5** | Environment, third-party flooding |
| S-04 | Protection relays | **5** | Safety, unprotected equipment |
| S-09 | Engineering + backups | **5** | Unrecoverable outage |
| S-10 | Vendor remote access | **5** | Enables all of the above, undetectably |
| S-08 | Auxiliaries | **4** | Cascade to machine damage |
| S-05 | Loss of generation | **4** | Availability, 12-hour SOCI report |
| S-06 | Market telemetry | **4** | Regulatory, fleet-scale technique |
| S-07 | Loss of view | **3→** | Derivative; escalates what it hides |

---

## 5. What this determines about the partition

The initial assessment does not produce zones — it produces the **constraints** the partition must satisfy. Five fall out of the above and carry into ZCR 3:

1. **Protection must be its own zone.** S-04 targets protection *as the objective*, not as an obstacle. A zone that contains both the thing being protected and the thing protecting it cannot express that.
2. **The intake must be its own zone.** High consequence (S-03), weak physical control (AP-12), wireless path (AP-07) and geographic separation. Three of 62443-3-2's explicit separation triggers apply at once.
3. **Auxiliaries cannot simply be merged into unit control.** S-08 is a 4, which is higher than most first partitions assume — but it is also not a 5, so it does not belong in the same zone as the governor either.
4. **Vendor remote access is a conduit, and it is the highest-SL-T conduit in the plant.** S-10 inherits the maximum consequence of everything it reaches, because that is what an access path *is*.
5. **Engineering and backup are high-consequence, not administrative.** S-09 rates 5. A partition that puts the engineering workstation in a general-purpose plant-information zone with the historian has understated it.

---

## 6. Open questions for the asset owner

- **A-01 must be confirmed by inspection, not by documentation.** If the overspeed trip depends on a programmable device, S-01 becomes the dominant scenario and the unit control zone requires SL-T 4.
- **Where is the gate closure-rate limit enforced?** (S-02.) If it lives in the governor's software, an adversary with governor access has it too.
- **Are configuration backups off-site and restore-tested?** (S-09.) If not, the availability rating stands at 5 and no compensating control reduces it.
- **Is market dispatch advisory or actuating?** (S-06, assumption A-07.)
- **Has any vendor's remote session ever been reviewed after the fact?** (S-10.) If the answer is no, the detection assumption is unfounded.

---

## 7. Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 14 Sept 2026 | Initial draft for review |
