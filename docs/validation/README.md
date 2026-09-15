# Cyber Security Validation — Kanangra Creek Hydro Station

The FAT, punch list, SAT and cutover artifacts that carry the **Cybersecurity Requirements Specification** from a signed document into a plant that can be accepted.

> ⚠ **The facility is fictional.** A worked example modelled on a real small run-of-river architecture, describing no actual asset.

---

## Why this set exists separately from the assessment

The [IEC 62443-3-2 assessment](../assessments/hydro-station/README.md) ends at ZCR 7 with a signed CRS. That is where most 62443 work stops, and it is also where most of it quietly fails, because **a requirement with no verification method cannot be accepted** — and a requirement with a verification method but no test plan is accepted on the word of the party who built it.

These four documents close that gap:

| # | Document | Ref | What it settles |
|---|---|---|---|
| 01 | [Cyber FAT test plan](01-cyber-fat-test-plan.md) | KCH-CYB-FAT-001 | Does the system meet the specification, in the factory, where a defect is still cheap? |
| 02 | [Punch list](02-punch-list.xlsx) (xlsx) | KCH-CYB-PUNCH-001 | What is carried forward, by whom, until when, and with what standing in its place? |
| 03 | [Cyber SAT plan](03-cyber-sat-plan.md) | KCH-CYB-SAT-001 | Does it still hold on the real network, from the real internet, with real water? |
| 04 | [Commissioning cutover runbook](04-commissioning-cutover-runbook.md) | KCH-CYB-COM-001 | How does construction access get removed before the unit generates? |

---

## The four ideas these documents are built on

**Test that the control cannot be bypassed, not that the control exists.** A test confirming a feature is present proves the integrator read the specification. A test attempting the thing the requirement forbids proves the requirement is *enforced*. Every case marked **N** in the plans is doing the second job, and those are the steps that find defects — writing to a tag from a raw protocol client rather than through the HMI; removing the software rate limit and timing the closure anyway; asking the vendor user to delete their own session recording.

**A hold point cannot become a punch item.** A hold point is a requirement whose failure stops shipment or energisation. The moment hold points start appearing on the punch list, the list has become the mechanism by which the specification is abandoned, and every signature after it is worth less.

**A SAT plan that repeats the FAT plan is a defect in the SAT plan.** Every SAT case here traces to a *"cannot prove"* line in the FAT plan, and the traceability is written out so a reviewer can check that nothing was carried over from habit. SAT exists for what the factory could not represent: the real network, the real internet, real physical access, long paths, and water in the penstock.

**Construction state is not a lesser version of operational state.** Broad engineering access, open vendor accounts, widened firewall rules and suppressed alarms are all legitimate while a plant is being built and all defects the moment it generates. Cutover is the controlled removal of that scaffolding — an event with a time, a checklist and a signature. A plant that never formally cuts over runs on commissioning access indefinitely, which is the most common finding in a first assessment of an existing asset. Not a sophisticated attack path: a commissioning account nobody removed.

---

## The one hour the whole programme depends on

**SAT-11.** De-energise the governor, put the unit control PLC in STOP, run the unit up, and see whether the hardwired overspeed trip operates anyway.

That test resolves **assumption A-01**, and six risks in the register — R-12, R-17, R-26, R-35, R-38, R-39 — are rated at direct consequence 4 rather than 5 only because that trip is assumed to stand behind them. If it does not:

- those six return to consequence 5
- the Extreme band returns from 11 to 17
- Z-02's target security level rises to **SL 4**
- the CRS is reissued at a higher target, and the programme moves from acceptance back into design

A certificate does not discharge it. The claim is about independence, and independence is shown by removing the thing it is independent of. **Schedule it early in the SAT window** — finding out on the last day costs a mobilisation.

---

## Fidelity

These plans demonstrate method. They are written against a specification for a fictional facility and have not been executed.

**What they do not and cannot demonstrate is participation in a real FAT, SAT, commissioning or operational cutover** — the pressure of a window that closes at six, the commercial argument about whether a finding is a defect or a variation, the judgement call at two in the morning about whether an unexplained alarm is worth aborting for. They are not offered as a substitute for that.

---

*Author: Epiphane Zaré · September 2026*
