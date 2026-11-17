<#
The PLC link and alarm persistence, in Docker (ADR-013, ADR-019). Run AFTER validate-4e.ps1 passed.

    cd plant
    powershell -ExecutionPolicy Bypass -File tools\validate-plcio.ps1

Does: local FFs -> migrate the historian -> bring the stack up in its default mode (PLC link on, alarm persistence on) ->
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
$compose = @('-f', 'docker-compose.yml')   # the PLC link and persistence are the compose defaults since 26 Oct 2026
# ADR-023: FF-26 commands go through fw-cell, which admits only scada as the F9 source. For the scripted run
# the collector plays the operator (docker-compose.ff26.yml); the design is restored at the end.
$composeTest = @('-f', 'docker-compose.yml', '-f', 'docker-compose.ff26.yml')

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
    foreach ($ff in 'ff07_alarm_state_model', 'ff21_safety_st_static', 'ff22_compose_topology', 'ff23_plc_io_map', 'ff24_gateway_plc_link', 'ff25_alarm_persistence', 'ff31_cell_door', 'ff33_opcua_sup_readonly') {
        python "$root\scripts\$ff.py" | Out-Null
        if ($LASTEXITCODE -ne 0) { Stop-Here "$ff failed locally" }
        Write-Host "  PASS  $ff"
    }
    python "$root\scripts\ff35_secure_channel.py" --static-only | Out-Null
    if ($LASTEXITCODE -ne 0) { Stop-Here "ff35_secure_channel (static) failed locally" }
    Write-Host "  PASS  ff35_secure_channel (static)"
}

Write-Host "`n== 2. migrate the historian (idempotent; the schema only runs on an EMPTY volume) =="
docker compose @compose up -d historian
Start-Sleep -Seconds 8
Get-Content "$root\plant\historian\migrations\001_alarm_state.sql" | docker exec -i vigilimen-historian psql -U vigilimen -d vigilimen -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { Stop-Here "migration failed" }
docker exec vigilimen-historian psql -U vigilimen -d vigilimen -c "\d alarm_state"

Write-Host "`n== 3. build + up WITH the PLC link and persistence =="
docker compose @compose build pki-init gateway fw-cell opcua-sup collector scada
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
# The dashboard saying 'Running' is NOT proof (16 Nov 2026: Start PLC pressed more than once left the runtime
# with no Modbus listener while the page still said Running). The proof is port 502 answering, from the gateway.
$modbusUp = $false
foreach ($i in 1..10) {
    docker exec vigilimen-gateway python3 -c "import socket; s=socket.create_connection(('plc-control',502),3); s.close()" 2>$null
    if ($LASTEXITCODE -eq 0) { $modbusUp = $true; break }
    Start-Sleep -Seconds 3
}
if (-not $modbusUp) {
    Stop-Here "plc-control is not listening on Modbus port 502 although the dashboard may say Running. In OpenPLC press Stop PLC, wait 5 s, press Start PLC ONCE, leave the page alone, then run this script again."
}
Write-Host "  PASS  plc-control answers on Modbus port 502"
docker compose @compose restart gateway | Out-Null
# After the gateway restart, wait for its own 'linked' line (not a fixed sleep).
$t0 = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$linked = $false
foreach ($i in 1..30) {
    $l = docker logs --since $t0 vigilimen-gateway 2>&1 | Select-String 'plc-link: linked to'
    if ($l) { $linked = $true; break }
    Start-Sleep -Seconds 4
}
docker compose @compose logs gateway --tail 15
if (-not $linked) { Stop-Here "the gateway did not log 'plc-link: linked' within 2 minutes after its restart (port 502 was answering before it)" }
Write-Host "  PASS  gateway linked to the PLC after its restart"

Write-Host "`n== 5. FF-26 with the PLC in the loop (START now waits for the 10 s horn) =="
Write-Host "  (F9 source switched to the collector for the scripted run; FUXA cannot command until step 9)"
docker compose @composeTest up -d fw-cell | Out-Null
Start-Sleep -Seconds 12
$rc = Ff26 @('--phase', 'alarm', '--expect-link', 'modbus')
if ($rc -ne 0) {
    # Evidence first: what each hop of the chain was doing, with timestamps (the 16 Nov failure left none).
    foreach ($c in 'vigilimen-gateway', 'vigilimen-opcua-sup', 'vigilimen-fw-cell') {
        Write-Host "--- $c (last 15 lines, timestamped)"
        docker logs -t --tail 15 $c 2>&1 | ForEach-Object { Write-Host $_ }
    }
    Stop-Here "FF-26 alarm phase failed"
}
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

Write-Host "`n== 9. restore the design: F9 source back to scada =="
docker compose @compose up -d fw-cell | Out-Null

Stop-Transcript | Out-Null
if ($iso -ne 0) { Write-Host "ISOLATION FAILED. Log: $log"; exit 1 }
Write-Host "PLC link, persistence and isolation all proven in Docker. Log: $log"
