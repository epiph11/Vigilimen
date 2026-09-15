# Cyber Security Commissioning and Cutover Runbook

**Kanangra Creek Hydro Station — 20 MW run-of-river generating station**
**Ref:** KCH-CYB-COM-001 · **Revision:** 0.1 — DRAFT · **Date:** 14 September 2026
**Follows:** KCH-CYB-SAT-001 rev 0.1 · **Specification:** KCH-CYB-CRS-001 rev 0.2
**Prepared by:** Epiphane Zaré

> ⚠ **Fictional facility.** A worked example against a specification, not a delivered system.

---

## 1. What cutover is, and why it is the dangerous part

SAT proved the installation meets the specification. Cutover is the transition from **a system being built** to **a system being operated** — and it is the phase where more security posture is lost than in any other, because every mechanism that made construction possible is still in place and nothing yet forces its removal.

During construction the plant necessarily runs with:

- broad engineering access, because engineers are building it
- vendor accounts open, because vendors are on site
- firewall rules widened for commissioning tools
- test accounts, default configurations, temporary paths
- alarms suppressed so that a plant under test does not scream continuously

**Every one of those is legitimate during construction and a defect the moment the unit is generating.** Cutover is the controlled removal of the scaffolding. A plant that is never formally cut over runs on commissioning access indefinitely, and this is the single most common finding in a first assessment of an existing asset — not a sophisticated attack path, but a commissioning account from 2014 that still works.

> **The governing idea: construction state is not a lesser version of operational state. It is a different state, with different access, and the transition between them must be an event with a time, a checklist and a signature — not a drift.**

---

## 2. Prerequisites

| # | Prerequisite |
|---|---|
| P-1 | SAT complete, all SAT hold points passed |
| P-2 | **SAT-11 executed; A-01 resolved.** If A-01 failed, **stop** — this runbook does not apply to a system whose target security level has changed |
| P-3 | Punch list re-dispositioned at the energisation boundary |
| P-4 | As-built conduit register signed (CRS-070) |
| P-5 | Operations staff trained on the alarms they will receive (CRS-068) |
| P-6 | Incident response plan issued and the reporting path tested (CRS-069) |
| P-7 | Rollback position agreed for every step in §4 |

---

## 3. The cutover window

| | |
|---|---|
| **Duration** | One shift, plus a 72-hour observation period |
| **Authority to proceed** | Operations manager |
| **Authority to abort** | **Anyone present.** No justification required at the time; recorded afterwards |
| **Preconditions** | Unit off line or at a stable operating point agreed in advance. Engineering support available for the full window and for the observation period |

> **On the abort authority.** A cutover is a sequence of irreversible-feeling removals under time pressure, which is precisely the condition under which people continue past something they have noticed. Making abort free at the moment and accountable afterwards inverts that, and costs one shift at worst.

---

## 4. The sequence

**Each step: execute, verify, record. A step that cannot be verified is not complete, and the sequence does not continue past it.**

### Stage 1 — Freeze

| # | Step | Verify | Rollback |
|---|---|---|---|
| 1.1 | Declare configuration freeze. All changes from this point require change control | Freeze notice issued and acknowledged by all parties on site | — |
| 1.2 | Capture a full configuration baseline of every component | Baseline stored in the off-site backup store; hash recorded | — |
| 1.3 | Verify the baseline restores (spot check, one component of each type) | Restoration succeeds on isolated hardware | — |

> **1.3 exists because a baseline nobody has restored is a hypothesis.** It is also the last convenient moment to discover that the backup format is unreadable.

### Stage 2 — Withdraw construction access

| # | Step | Verify | Rollback |
|---|---|---|---|
| 2.1 | Disable every commissioning and temporary account. **Disable, do not delete** — deletion destroys the audit trail | Enumerate accounts; every remaining account maps to a named operational holder | Re-enable named account |
| 2.2 | Withdraw integrator standing access. Future access is via the CRS-045 just-in-time path only | **N** — integrator attempts to connect as before. Must fail | Re-grant, time-boxed, recorded |
| 2.3 | Remove temporary firewall rules opened for commissioning | Rule set reconciles clean against the conduit register (CRS-042) | Restore the specific rule, tagged and dated |
| 2.4 | Rotate every credential that was known to a construction party | Rotation record; authentication with the old credential fails | — |
| 2.5 | Remove commissioning tooling from control-zone hosts | Host inventory matches the delivered software list | — |

> **2.3 is where the permanent "temporary" rule is born.** The countermeasure is in the verification column: reconcile against the register, not against memory. A rule that is legitimate survives reconciliation because it is registered; a rule that survives because nobody looked is the one that is still there in 2034.

> **2.4 is routinely skipped** on the reasoning that the construction party is trusted. The requirement is not about trust — it is that a credential known to a party who is no longer accountable for the system is a credential with no owner. The vendor's laptop went home with the vendor.

### Stage 3 — Enable the operational security posture

| # | Step | Verify | Rollback |
|---|---|---|---|
| 3.1 | Un-suppress all security and protection alarms suppressed for commissioning | Suppression list is empty. **Compare against the list captured at the start of commissioning** — if no such list exists, that is itself the finding | Re-suppress individually, with a reason |
| 3.2 | Enable session recording and central logging in operational configuration | Generate one event of each class; confirm arrival at the central log | — |
| 3.3 | Enable the automated firewall-to-register reconciliation on its operational schedule | First scheduled run completes and reports | — |
| 3.4 | Place golden-copy baselines under change control | Comparison procedure runs clean against every controller | — |
| 3.5 | Hand the backup and restoration procedure to operations, with the measured recovery time from SAT-07 | Operations acknowledges the **measured** time, not the assumed one | — |

> **3.1 depends on a list that had to be made months earlier.** If suppressions were not recorded as they were applied, there is no way to know what is still suppressed, and the honest disposition is to un-suppress everything and work through the resulting noise. That is expensive and it is the correct answer.

### Stage 4 — Transfer of custody

| # | Step | Verify |
|---|---|---|
| 4.1 | Formal handover of configuration, logic, settings and documentation in editable source form (CRS-061) | Asset owner engineer opens and modifies one file of each type, **without an integrator licence** |
| 4.2 | Transfer of the account register to operations | Operations holds and can administer every account |
| 4.3 | Transfer of the conduit register and drawing KCH-CYB-ZC-001 as controlled documents | Registered in the document management system |
| 4.4 | Confirm the 62443-2-1 operational obligations are assigned to named roles | Assignment record |
| 4.5 | Sign the transfer of custody | Signature of operations manager and engineering manager |

> **4.4 is the one that decides whether any of this survives.** Every control delivered here decays without an owner: accounts accumulate, cables go unregistered, vendor sessions stay open after a call-out, and emergency rules are never withdrawn. **The partition is true on the day it is signed and progressively less true every day after, unless somebody's job description says otherwise.**

### Stage 5 — Observation

| # | Step | Duration |
|---|---|---|
| 5.1 | Monitor for alarms caused by the cutover itself — an un-suppressed alarm that should have stayed suppressed, a withdrawn rule that was load-bearing | 72 hours |
| 5.2 | Confirm no operational process was silently depending on a withdrawn access path | 72 hours |
| 5.3 | Confirm logging, recording and reconciliation continue to function unattended | 72 hours |
| 5.4 | Close the cutover record | End of window |

> **5.2 is the step that catches the real consequence of Stage 2.** Something always depended on the broad access — a nightly export, a vendor's monitoring poll, a report that ran as the commissioning account. The right outcome is that it breaks visibly within 72 hours while the people who can fix it are still on site, rather than silently at the first quarter-end.

---

## 5. Abort criteria

**Stop the cutover and restore the previous state if any of these occurs.** The plant returns to construction state, which is a known state.

| # | Trigger |
|---|---|
| A-1 | Any step cannot be verified |
| A-2 | Any step cannot be rolled back as documented |
| A-3 | An alarm or trip occurs that is not understood within the window |
| A-4 | Withdrawing an access path breaks an operational process that cannot be restored another way |
| A-5 | The configuration baseline cannot be restored at step 1.3 |
| A-6 | Anyone present calls it |

> **Aborting is not a failure of the cutover.** The failure mode is completing a cutover that left the plant in a state nobody can describe — which is what happens when a team pushes through A-3 at two in the morning because the window closes at six.

---

## 6. The first year

Cutover is the beginning of the operational obligations, not the end of the project. These are 62443-2-1, they belong to the asset owner, and they are what the whole programme is finally worth.

| When | What | Why |
|---|---|---|
| Weekly | Firewall-to-register reconciliation reviewed | Divergence is the earliest signal of an undocumented path |
| Monthly | Account register reviewed; dormant accounts disabled | Accounts accumulate; nobody is ever asked to remove one |
| Monthly | Vendor session log reviewed against work orders | A session with no work order is the finding |
| Quarterly | Golden-copy comparison on every controller | Detects change that no log recorded |
| **Annually** | **Restoration test with measured recovery time** | An untested backup is not a backup — and the measured time drifts as the system grows |
| Annually | Physical port count reconciled against the schedule | Ports get enabled and not recorded |
| Annually | SL-A reassessed against SL-T; the delta is the remediation backlog | **This is the operating loop.** It is the whole point of assigning SL-T in the first place |
| On trigger | Full reassessment per approval record §8 | Change, incident, new supplier, new threat, or 3 years |

---

## 7. Cutover record

| | |
|---|---|
| Date and window | |
| Unit state at start | |
| Steps completed | |
| Steps aborted, with reason | |
| Punch items raised | |
| Observation period findings | |

| Role | Name | Signature | Date |
|---|---|---|---|
| Operations manager — authority to proceed | | | |
| Engineering manager — transfer of custody | | | |
| Integrator test lead | | | |
| Asset owner witness | | | |

---

## 8. Revision history

| Rev | Date | Change |
|---|---|---|
| 0.1 | 14 Sept 2026 | Initial draft against CRS rev 0.2 and SAT plan rev 0.1 |

---

*5 stages · 6 abort criteria · 8 first-year obligations · KCH-CYB-COM-001 · Fictional facility, worked example*
