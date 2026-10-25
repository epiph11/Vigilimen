# Proposed commits (nothing has been committed, nothing pushed)

Run from the repo root in PowerShell. Check each step before the next one. **Never `git add -A`**: it
would also stage anything new you create. FF-03 fails on your local `my-notes.md` (a literal key,
line 66); that file is gitignored and stays out, but fix the line.

Before starting: `git status --short`. The index already holds the staged rename hunks (41 files).

## 1. The rename, as it is already staged

```powershell
git diff --cached --stat        # expect 41 files: limen- to vigilimen- (plus FF-03 skipping pilotage/)
git commit -m "Finish the limen- to vigilimen- rename (docs, infra, plant, scripts)"
```

## 2. FF-21 (it was never tracked, and CI already calls it)

```powershell
git add -- scripts/ff21_safety_st_static.py
git commit -m "FF-21: the safety program on disk matches the independence argument" -m "FF-06 tests the Python model and never opens safety.st. FF-21 reads the program: 10 properties, 8 mutations."
```

## 3. 4e: fault injection physics, health check, generators, FUXA project

```powershell
git add -- plant/sim/conveyor_physics.py plant/gateway/healthcheck.py plant/plc-upload/build.py plant/plc-upload/safety_upload.st plant/scada/project/build_project.py plant/scada/project/vigilimen-conv001.fuxa.json .gitignore
git commit -m "4e: vibration-spike stimulus, authenticated health check, FUXA project and PLC upload generators" -m ".gitignore now lets the FUXA generator and its import file through, and ignores docs/runs/*.log."
```

## 4. Alarm state persistence (ADR-019)

```powershell
git add -- plant/alarms/engine.py plant/alarms/store.py plant/historian/schema.sql plant/historian/migrations plant/historian/Dockerfile plant/historian/collector.py scripts/ff25_alarm_persistence.py docs/adr/0019-alarm-state-persistence.md
git commit -m "Persist alarm state in the historian; enforce append-only alarm_event (ADR-019)" -m "State is saved in the same transaction as the events. A failed commit no longer loses events. Off by default (VIGILIMEN_ALARM_PERSIST). collector.py also carries the 4e alarm feed. Needs migrations/001_alarm_state.sql on an existing volume."
```

## 5. Gateway to PLC over Modbus, opt-in (ADR-013, ADR-014)

```powershell
git add -- plant/gateway/modbus.py plant/gateway/plc_io_map.py plant/gateway/plc_link.py plant/gateway/plant_cycle.py plant/gateway/opcua_server.py plant/gateway/Dockerfile plant/plc-control/conveyor.st plant/plc-upload/conveyor_upload.st plant/docker-compose.yml plant/docker-compose.plcio.yml plant/tools scripts/ff22_compose_topology.py scripts/ff23_plc_io_map.py scripts/ff24_gateway_plc_link.py scripts/ff26_stack_e2e.py docs/adr/0013-gateway-plc-modbus-link.md docs/adr/0014-sis-unlinked-contactor-modelled.md
git commit -m "Gateway drives PLC-CONV-001 over Modbus, opt-in; SIS stays unlinked (ADR-013, ADR-014)" -m "Off by default; docker-compose.plcio.yml enables it. FF-22/23/24 pass locally against a FAKE PLC; FF-26 (Docker) has not run and conveyor.st has not been compiled by MatIEC. ADR-013 is Proposed. opcua_server.py also carries the 4e fault tags. VIGILIMEN_MODBUS_HOST now names a service, not a hostname."
```

## 6. Decisions and scope notes

```powershell
git add -- docs/adr/0015-openplc-v3-end-of-life.md docs/adr/0016-fault-injection-tags.md docs/adr/0017-opcua-accounts-attribution-not-authorisation.md docs/adr/0018-demo-credentials-scope.md docs/adr/0007-oidc-only-credentials.md README.md
git commit -m "ADR-015 to 018; ADR-007 scoped to cloud credentials; README lists FF-21 to FF-26"
```

## 7. CI

```powershell
git add -- .github/workflows/ci.yml
git commit -m "CI: run FF-22 to FF-25 (FF-26 needs Docker and is not run here)"
```

## 8. Station 5 evaluation, run notes, state document

```powershell
git add -- docs/assessments/hydro-station/EVALUATION-station5.md scripts/s5_recompute_register.py docs/runs/NOTES.md docs/runs/COMMITS.md docs/VIGILIMEN-etat-des-lieux.md docs/img
git commit -m "Station 5 evaluation, validation run notes, state-of-play document"
```

## After

```powershell
git status --short      # expect nothing but ignored files
git log --oneline -9
# Push only when you decide to:  git push
```

Commits 4 and 5 should be checked against CI before merging: FF-22 needs `pip install pyyaml` (the workflow does it).
