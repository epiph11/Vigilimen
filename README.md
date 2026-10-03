# Vigilimen

An IT/OT convergence programme for a mining operation, built as an engineered system: a simulated plant on vendor-realistic industrial protocols, a full IEC 62443 assurance programme over it, and a three-cloud data and work-management architecture on top.

One engineer. Thirty sprints. A hard budget of **US$333**.

> **Nothing here is a production system and no facility described is real.** Every operating assumption is declared as an assumption rather than reported as a finding.

---

## Where to start

| If you want | Read |
|---|---|
| Why this exists and what it is for | [`docs/charter.md`](docs/charter.md) |
| What the architecture optimises for, and what that costs | [`docs/architecture/characteristics.md`](docs/architecture/characteristics.md) |
| Why the decisions were made the way they were | [`docs/adr/`](docs/adr/) |
| **Whether Australian critical-infrastructure law actually applies to a mine** | [`docs/adr/0006-regulatory-applicability.md`](docs/adr/0006-regulatory-applicability.md) |
| **Why an OT estate cannot reach Essential Eight ML2** | [`docs/compliance/e8-ml2-self-assessment.xlsx`](docs/compliance/e8-ml2-self-assessment.xlsx) |
| What an adversary could do at each trust boundary | [`docs/architecture/threat-model-v1.md`](docs/architecture/threat-model-v1.md) |
| The framework the programme is actually assessed against | [`docs/compliance/aescsf-orientation.md`](docs/compliance/aescsf-orientation.md) |
| **What each industrial protocol actually authenticates** (mostly: nothing) | [`docs/architecture/protocol-register.md`](docs/architecture/protocol-register.md) |
| The safety function, and the test that proves it is independent | [`plant/plc-safety/safety.st`](plant/plc-safety/safety.st) · [`scripts/ff06_safety_independence.py`](scripts/ff06_safety_independence.py) |
| **The worked IEC 62443-3-2 assessment** — ZCR 1–7, nine documents | [`docs/assessments/hydro-station/`](docs/assessments/hydro-station/) |
| **The FAT, SAT and cutover plans derived from it** | [`docs/validation/`](docs/validation/) |

---

## Decision record

| ADR | Decision | Status |
|---|---|---|
| [001](docs/adr/0001-multicloud-split.md) | Three clouds, split by verb — AWS senses, Azure acts, GCP learns | Accepted |
| [002](docs/adr/0002-modular-monolith.md) | Modular monolith for the enterprise plane, boundaries enforced in CI | Accepted |
| [003](docs/adr/0003-simulated-plant.md) | A simulated plant is the System under Consideration | Accepted |
| [004](docs/adr/0004-zero-idle-by-construction.md) | Cost control by construction, not by discipline | Accepted |
| [005](docs/adr/0005-ot-boundary-unidirectional.md) | The OT boundary is unidirectional by default | Accepted |
| [006](docs/adr/0006-regulatory-applicability.md) | **Mining is not a SOCI sector.** What applies, what does not, and why build to it anyway | Accepted |
| [007](docs/adr/0007-oidc-only-credentials.md) | Federated identity only — no static cloud credential exists | Accepted |
| [008](docs/adr/0008-entra-as-identity-authority.md) | Entra ID is the identity authority for all three clouds; authorisation stays local | Accepted |
| [009](docs/adr/0009-compliance-framework-selection.md) | **Nominate AESCSF at SP-2.** Map IEC 62443 underneath. Essential Eight is a declared partial lens | Accepted |
| [010](docs/adr/0010-programme-time-is-brisbane.md) | Machine time is UTC; human time is Australia/Brisbane, which has no daylight saving | Accepted |
| [011](docs/adr/0011-safety-function-separation.md) | **The safety function is a separate controller** — own runtime, own I/O, own zone, no network input at all | Accepted |
| [012](docs/adr/0012-fuxa-scada.md) | FUXA for SCADA — **a licence decision, not a feature comparison** | Accepted |

---

## The three things this programme argues

**Zones come from consequence, not from network topology.** A partition drawn by redrawing the network diagram produces zones that match the switches you already have — which is a description of the past. The engineering workstation outranks the HMI because it can reprogram the machine while the HMI can only ask it politely.

**No security control may sit inside a protective function.** A control that can fail closed on a protection or safety function has made the plant less safe, not more. This is a hard constraint, carried from the architecture characteristics into the risk criteria into the requirements specification, and it is the direct lesson of TRITON.

**Cost control that depends on remembering will eventually not happen.** The persistent spine is local; real cloud is entered only inside a scripted apply → evidence → destroy window whose teardown runs in `if: always()`. US$3,708 naive becomes US$13–333 structural.

---

## Contributing

Every structural decision becomes an ADR before the code that implements it. The PR template asks whether one is needed, and the answer "no" is acceptable — the answer "I'll add it later" is not.

**Governance documents are capped at two pages.** The top risk at inception was over-engineering the docs, and the cut line is how it is managed.

---

## Fitness functions

An architecture characteristic that is only written down is an aspiration. These fail builds.

| | Enforces | State |
|---|---|---|
| **FF-01** | Governance docs ≤ 2 pages; an ADR is one decision | Running — **caught ADR-006 on its first run at 94 lines against an 80-line cap** |
| **FF-02** | Terraform formatted and valid | Two stacks now exist. **Not yet run — see the note below** |
| **FF-03** | No static credential shape in the tree, and every cloud login requests an OIDC token | Running |
| **FF-06** | **The safety function is independent of the control function** (ADR-011) | Running — 13 cases, each modelling an adversary who already owns the control PLC. Verified against four deliberate mutations |
| **FF-07** | **The alarm surface behaves as ISA-18.2 describes** — shelve, suppress and out-of-service all work, and all leave an actor | Running — 20 cases. Caught its own test: an assertion whose setup had never run |
| **FF-05** | Naming and tagging — **the tag is the teardown mechanism**, so a missing one means a resource that survives the window and bills | Running — caught a real gap on its first run, and the gap turned out to be in the check |
| **FF-13** | The never-create deny-list (ADR-004) | Running — 13 rules, 11 test cases |
| **FF-14** | Federation trust stays scoped to this repository (ADR-007) | Running — 9 checks across three clouds, each verified against a deliberately broken copy |

`python3 scripts/ff06_safety_independence.py` · `python3 scripts/ff07_alarm_state_model.py` · `python3 scripts/test_ff13.py` · `bash scripts/ff01_doc_cut_line.sh` · `bash scripts/ff03_no_static_credentials.sh` · `bash scripts/ff05_naming_and_tagging.sh` · `bash scripts/ff14_federation_scope.sh`

---

> ⚠ **FF-02 has not actually executed.** The Terraform binary could not be installed in the environment these stacks were authored in, so `fmt -check` and `validate` have not run against them. Formatting was hand-aligned to fmt's rules and braces were balance-checked, which is not the same thing. **The first CI run is expected to find something**, and the honest position is to say so rather than to present unexecuted checks as passing.

---

## Status

Sprint 0 complete at gate **M0**. **Sprints 1 and 2 complete** — identity, compliance frame, threat model, and six fitness functions. Remaining before any of it is *proven*: a first real evidence-window run, and the Entra→AWS/GCP federation, both of which need cloud accounts.

Phase A is closed. **S3 complete.** **S4 in progress** — the compose stack now *builds*: both Dockerfiles and the OPC UA → TimescaleDB collector exist, and `depends_on` waits on health rather than on existence. Outstanding: the FUXA mimic (built through the browser — FUXA has no headless import) and the engineering workstation VM.

> **The gateway does not yet read the OpenPLC runtime over Modbus.** It serves the in-process simulation, and `LIMEN_MODBUS_HOST` is set in compose and unused. That is S5 work and it is named in `plant/gateway/Dockerfile` rather than left to be discovered.

### What this repository deliberately does not contain

The programme's own management artifacts — the sprint plan, the cost model, the
progress tracker and the author's working notes — are kept outside it. They describe
how the work is being scheduled and paid for, which is a different subject from the
engineering, and mixing the two makes both harder to read.

What is here is the system and the assurance case over it. Everything in the table
above can be read, run or falsified without reference to anything that is not in this
repository.

---

**Licence:** MIT — see [`LICENSE`](LICENSE), which also records the licences of the
container images this project composes and why FUXA was chosen over a more capable
alternative ([ADR-012](docs/adr/0012-fuxa-scada.md)).
