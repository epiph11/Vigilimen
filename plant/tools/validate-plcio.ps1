<#
The PLC link and alarm persistence, in Docker (ADR-013, ADR-019). Run AFTER validate-4e.ps1 passed.

    cd plant
    powershell -ExecutionPolicy Bypass -File tools\validate-plcio.ps1

Does: local FFs -> migrate the historian -> bring the stack up WITH docker-compose.plcio.yml ->
you load conveyor_upload.st into PLC-CONV-001 and Start PLC (once) -> FF-26 with the PLC in
the loop -> `docker restart vigilimen-collector` in the middle of an alarm -> FF-26 again
(no second raise, state kept) -> Clear -> isolation proof.

IF ANYTHING FAILS: stop, and write SYMPTOM / CAUSE / FIX in docs\runs\NOTES.md before changing it.
Most likely first failures, so you recognise them:
  * conveyor_upload.st does not COMPILE (MatIEC rejects located variables or a type): paste the
    compiler output into NOTES.md. FF-23 cannot catch this, only OpenPLC can.
  * plc-link says 'program signature 0': the program is not loaded, or the PLC is not started.
  * plc-link says 'read-back mismatch': OpenPLC maps an address differently from plc_io_map.py.
#>
$ErrorActionPreference = 'Continue'
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location "$root\plant"
$logDir = "$root\docs\runs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = "$logDir\plcio-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Transcript -Path $log | Out-Null
$compose = @('-f', 'docker-compose.yml', '-f', 'docker-compose.plcio.yml')

function Stop-Here($why) {
    Write-Host ""
    Write-Host "STOPPED: $why"
    Write-Host "Write SYMPTOM / CAUSE / FIX in docs\runs\NOTES.md BEFORE changing anything. Log: $log"
    Stop-Transcript | Out-Null
    exit 1
}
function Ff26($phaseArgs) {
    docker cp "$root\scripts\ff26_stack_e2e.py" vigilimen-collector:/tmp/ff26.py | Out-Null
    $out = docker exec -e VIGILIMEN_OPCUA_USER=engineer -e VIGILIMEN_OPCUA_PASSWORD=eng1neer-demo vigilimen-collector python /tmp/ff26.py @phaseArgs
    $out | ForEach-Object { Write-Host $_ }
    $script:lastOut = $out -join "`n"
    return $LASTEXITCODE
}

Write-Host "== 1. local fitness functions =="
if (Get-Command python -ErrorAction SilentlyContinue) {
    foreach ($ff in 'ff07_alarm_state_model', 'ff21_safety_st_static', 'ff22_compose_topology', 'ff23_plc_io_map', 'ff24_gateway_plc_link', 'ff25_alarm_persistence') {
        python "$root\scripts\$ff.py" | Out-Null
        if ($LASTEXITCODE -ne 0) { Stop-Here "$ff failed locally" }
        Write-Host "  PASS  $ff"
    }
}

Write-Host "`n== 2. migrate the historian (idempotent; the schema only runs on an EMPTY volume) =="
docker compose @compose up -d historian
Start-Sleep -Seconds 8
Get-Content "$root\plant\historian\migrations\001_alarm_state.sql" | docker exec -i vigilimen-historian psql -U vigilimen -d vigilimen -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { Stop-Here "migration failed" }
docker exec vigilimen-historian psql -U vigilimen -d vigilimen -c "\d alarm_state"

Write-Host "`n== 3. build + up WITH the PLC link and persistence =="
docker compose @compose build gateway collector
if ($LASTEXITCODE -ne 0) { Stop-Here "build failed" }
docker compose @compose up -d
docker compose @compose ps

Write-Host @"

== 4. load the program into PLC-CONV-001, by hand, ONCE ==
  powershell -ExecutionPolicy Bypass -File tools\plc-ui-relay.ps1 -Action start -Target control
  http://127.0.0.1:8081  (openplc / openplc)  ->  Programs -> Upload Program
  upload  plant\plc-upload\conveyor_upload.st   (NOT plc-control\conveyor.st: it has no CONFIGURATION block)
  name it, Launch program, wait for COMPILATION to finish: it must say success, not just 'done'
  -> Start PLC.   (Settings -> 'Start in run mode' keeps it started across restarts.)
"@
Read-Host "Press Enter when the PLC dashboard says 'Running'"
docker compose @compose restart gateway | Out-Null
Start-Sleep -Seconds 12
docker compose @compose logs gateway --tail 15

Write-Host "`n== 5. FF-26 with the PLC in the loop (START now waits for the 10 s horn) =="
$rc = Ff26 @('--phase', 'alarm', '--expect-link', 'modbus')
if ($rc -ne 0) { Stop-Here "FF-26 alarm phase failed" }
$since = 0
if ($lastOut -match 'since-event-id (\d+)') { $since = [int]$Matches[1] }

Write-Host "`n== 6. restart the collector in the middle of the alarm (ADR-019) =="
docker restart vigilimen-collector | Out-Null
Start-Sleep -Seconds 6
docker compose @compose logs collector --tail 6
$rc = Ff26 @('--phase', 'after-restart', '--since-event-id', "$since")
if ($rc -ne 0) { Stop-Here "after-restart failed: the incident was raised twice or alarm_state is empty" }

Write-Host "`n== 7. clear =="
$rc = Ff26 @('--phase', 'clear', '--expect-link', 'modbus', '--expect-append-only')
if ($rc -ne 0) { Stop-Here "clear phase failed" }

Write-Host "`n== 8. isolation, live =="
powershell -ExecutionPolicy Bypass -File "$root\plant\tools\prove-isolation.ps1"
$iso = $LASTEXITCODE

Stop-Transcript | Out-Null
if ($iso -ne 0) { Write-Host "ISOLATION FAILED. Log: $log"; exit 1 }
Write-Host "PLC link, persistence and isolation all proven in Docker. Log: $log"
