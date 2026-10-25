<#
Acceptance test 4e on the EMBEDDED model (no PLC link, no alarm persistence): the baseline the PLC mode is compared against.

The compose default is the PLC link since 26 Oct 2026, so this script opts out for itself (VIGILIMEN_PLC_LINK=off and
VIGILIMEN_ALARM_PERSIST=off, set for this process only). The containers stay in the embedded mode afterwards; to go back:
    Remove-Item Env:VIGILIMEN_PLC_LINK -ErrorAction SilentlyContinue ; docker compose up -d   (in a new PowerShell window)

    cd plant
    powershell -ExecutionPolicy Bypass -File tools\validate-4e.ps1

Does, in order: local fitness functions -> build gateway + collector -> up -> wait for
health -> FF-26 (STOP, clear, START, Spike +8, timed alarm row, Clear all faults) ->
last alarm_event rows -> the FUXA checklist you do by hand.

IF ANYTHING FAILS: stop. Open docs\runs\NOTES.md and write SYMPTOM, CAUSE, FIX
(in that order, before you change a line). The transcript of this run is in
docs\runs\4e-<timestamp>.log. A programme that records what its own checks caught is
worth more than one that shows a green tick of unknown provenance.
#>
$ErrorActionPreference = 'Continue'
$env:VIGILIMEN_PLC_LINK = 'off'
$env:VIGILIMEN_ALARM_PERSIST = 'off'
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location "$root\plant"
$logDir = "$root\docs\runs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = "$logDir\4e-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Transcript -Path $log | Out-Null

function Stop-Here($why) {
    Write-Host ""
    Write-Host "STOPPED: $why"
    Write-Host "Write SYMPTOM / CAUSE / FIX in docs\runs\NOTES.md BEFORE changing anything. Log: $log"
    Stop-Transcript | Out-Null
    exit 1
}

Write-Host "== 1. local fitness functions =="
if (Get-Command python -ErrorAction SilentlyContinue) {
    foreach ($ff in 'ff07_alarm_state_model', 'ff21_safety_st_static', 'ff22_compose_topology', 'ff23_plc_io_map', 'ff24_gateway_plc_link', 'ff25_alarm_persistence') {
        python "$root\scripts\$ff.py" | Out-Null
        if ($LASTEXITCODE -ne 0) { Stop-Here "$ff failed locally. Run it to see why: python scripts\$ff.py" }
        Write-Host "  PASS  $ff"
    }
} else { Write-Host "  (python not on PATH: skipped)" }

Write-Host "`n== 2. build gateway + collector =="
docker compose build gateway collector
if ($LASTEXITCODE -ne 0) { Stop-Here "docker compose build failed (read the first error above, not the last)" }

Write-Host "`n== 3. up =="
docker compose up -d
if ($LASTEXITCODE -ne 0) { Stop-Here "docker compose up failed" }
docker compose ps

Write-Host "`n== 4. wait for health (gateway opens a real authenticated OPC UA session) =="
$healthy = $false
foreach ($i in 1..45) {
    $g = (docker inspect -f '{{.State.Health.Status}}' vigilimen-gateway).Trim()
    $h = (docker inspect -f '{{.State.Health.Status}}' vigilimen-historian).Trim()
    Write-Host "  gateway=$g historian=$h"
    if ($g -eq 'healthy' -and $h -eq 'healthy') { $healthy = $true; break }
    Start-Sleep -Seconds 4
}
if (-not $healthy) { Stop-Here "gateway or historian not healthy after 3 minutes: docker compose logs gateway --tail 40" }

Write-Host "`n== 5. the gateway built from THIS tree has the Fault* nodes (the 25/10 trap: an old image has none) =="
docker compose logs gateway --tail 5
Start-Sleep -Seconds 5

Write-Host "`n== 6. FF-26: START, Spike +8, timed alarm row, Clear all faults =="
docker cp "$root\scripts\ff26_stack_e2e.py" vigilimen-collector:/tmp/ff26.py
docker exec -e VIGILIMEN_OPCUA_USER=engineer -e VIGILIMEN_OPCUA_PASSWORD=eng1neer-demo vigilimen-collector python /tmp/ff26.py --phase all --expect-link off
$ff26 = $LASTEXITCODE

Write-Host "`n== 7. last alarm_event rows =="
docker exec vigilimen-historian psql -U vigilimen -d vigilimen -c "SELECT event_id, ts, condition, from_state, to_state FROM alarm_event ORDER BY event_id DESC LIMIT 6;"

Write-Host @"

== 8. FUXA, by hand (this part cannot be scripted) ==
  a. http://localhost:1881 -> gear (top right) -> Project -> Import
     plant\scada\project\vigilimen-conv001.fuxa.json   (REPLACES the whole project)
  b. Connections -> CONV-001: user engineer, password eng1neer-demo, if it shows disconnected.
  c. START: Running lamp green, belt speed rises to 2.5 m/s (immediately: no PLC in the loop yet).
  d. 'Spike vibration +8': vibration lamp red within 2 s. Then re-run step 7 above for the row.
  e. 'Clear all faults': the lamp clears and the row goes UNACK -> RTN_UNACK.
Write down anything that differs from c-e. Do not fix it first.
"@

Stop-Transcript | Out-Null
if ($ff26 -ne 0) { Write-Host "FF-26 FAILED. Log: $log"; exit 1 }
Write-Host "Automated part of 4e passed. Now do step 8 by hand. Log: $log"
