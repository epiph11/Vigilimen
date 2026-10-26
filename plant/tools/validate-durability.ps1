<#
FF-28 in Docker: the alarm history survives DELETE / TRUNCATE attempts and a collector restart DURING a shelf.

    cd plant
    powershell -ExecutionPolicy Bypass -File tools\validate-durability.ps1

Runs in the EMBEDDED model with alarm persistence ON (set for this process only): no PLC program to load by hand,
and persistence is the thing under test. Afterwards the containers stay in that mode; to go back to the default
(PLC mode), open a new PowerShell window and:  docker compose up -d --build

Does: local FFs -> up (embedded + persistence) -> migrate -> wait for health -> FF-26 alarm phase (leaves the
Vibration spike ON) -> FF-28 tamper -> FF-28 shelve (1 minute) -> docker restart vigilimen-collector -> FF-28
after-restart -> FF-28 expiry (waits for the shelf to end, about 1 minute) -> FF-26 clear.
The whole run is about 3 minutes. The restart must happen inside the 1-minute shelf: if the script says
"TOO SLOW", just run it again.

With -Extended, three more scenarios run afterwards (about 6 more minutes), each from a live alarm:
  A  restart of the collector AFTER the shelf expired      -> exactly one SHELVED->UNACK
  B  the condition clears DURING the shelf, restart in the middle, then expiry -> SHELVED->NORMAL, never UNACK
  C  alarm ACKNOWLEDGED, then shelved, restart, expiry      -> comes back UNACK (the acknowledgement is not kept)
    powershell -ExecutionPolicy Bypass -File tools\validate-durability.ps1 -Extended

IF ANYTHING FAILS: stop, and write SYMPTOM / CAUSE / FIX in docs\runs\NOTES.md before changing a line.
A surprising result: suspect the instrument first (this script, FF-28, the self-test), not the collector.
#>
param([switch]$Extended)
$ErrorActionPreference = 'Continue'
$env:VIGILIMEN_PLC_LINK = 'off'
# VIGILIMEN_ALARM_PERSIST is set AFTER step 1: ff25 asserts that persistence is OFF by default,
# so it fails if the variable is already 'on' (NOTES.md, 26/10 03:15).
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location "$root\plant"
$logDir = "$root\docs\runs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = "$logDir\durability-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Transcript -Path $log | Out-Null

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
function Ff28($phaseArgs) {
    $out = docker exec -e VIGILIMEN_OPCUA_USER=engineer -e VIGILIMEN_OPCUA_PASSWORD=eng1neer-demo vigilimen-collector python /tmp/ff28.py @phaseArgs
    $out | ForEach-Object { Write-Host $_ }
    $script:lastOut = $out -join "`n"
    return $LASTEXITCODE
}

Write-Host "== 1. local fitness functions =="
if (Get-Command python -ErrorAction SilentlyContinue) {
    foreach ($ff in 'ff07_alarm_state_model', 'ff22_compose_topology', 'ff25_alarm_persistence') {
        python "$root\scripts\$ff.py" | Out-Null
        if ($LASTEXITCODE -ne 0) { Stop-Here "$ff failed locally. Run it to see why: python scripts\$ff.py" }
        Write-Host "  PASS  $ff"
    }
    python -m py_compile "$root\scripts\ff28_alarm_durability.py"
    if ($LASTEXITCODE -ne 0) { Stop-Here "ff28_alarm_durability.py does not compile" }
    Write-Host "  PASS  ff28 compiles"
} else { Write-Host "  (python not on PATH: skipped)" }

$env:VIGILIMEN_ALARM_PERSIST = 'on'
Write-Host "`n== 2. up (embedded model, alarm persistence ON), migrate the historian =="
docker compose build gateway collector
if ($LASTEXITCODE -ne 0) { Stop-Here "docker compose build failed" }
docker compose up -d
if ($LASTEXITCODE -ne 0) { Stop-Here "docker compose up failed" }
$healthy = $false
foreach ($i in 1..45) {
    $g = (docker inspect -f '{{.State.Health.Status}}' vigilimen-gateway).Trim()
    $h = (docker inspect -f '{{.State.Health.Status}}' vigilimen-historian).Trim()
    Write-Host "  gateway=$g historian=$h"
    if ($g -eq 'healthy' -and $h -eq 'healthy') { $healthy = $true; break }
    Start-Sleep -Seconds 4
}
if (-not $healthy) { Stop-Here "gateway or historian not healthy: docker compose logs gateway --tail 40" }
Get-Content "$root\plant\historian\migrations\001_alarm_state.sql" | docker exec -i vigilimen-historian psql -U vigilimen -d vigilimen -v ON_ERROR_STOP=1 | Out-Null
if ($LASTEXITCODE -ne 0) { Stop-Here "migration failed" }
Start-Sleep -Seconds 5
docker compose logs collector --tail 4
$mode = (docker compose logs collector --tail 30 | Out-String)
if ($mode -notmatch 'persistence: on') { Stop-Here "collector does not report 'alarm state persistence: on'; the environment variable did not reach the container" }

docker cp "$root\scripts\ff28_alarm_durability.py" vigilimen-collector:/tmp/ff28.py | Out-Null

Write-Host "`n== 3. FF-26 alarm phase: belt running, Vibration spike ON, HI_HI raised =="
$rc = Ff26 @('--phase', 'alarm', '--expect-link', 'off')
if ($rc -ne 0) { Stop-Here "FF-26 alarm phase failed" }

Write-Host "`n== 4. FF-28 tamper: DELETE / TRUNCATE on alarm_event =="
$rc = Ff28 @('--phase', 'tamper')
if ($rc -ne 0) { Stop-Here "FF-28 tamper failed (read the SELF-TEST lines first: if they failed, the instrument is not validated)" }

Write-Host "`n== 5. FF-28 shelve: the operator shelves Vibration HI_HI for 1 minute =="
$rc = Ff28 @('--phase', 'shelve', '--minutes', '1')
if ($rc -ne 0) { Stop-Here "FF-28 shelve failed" }
$since = 0; $until = ''
if ($lastOut -match 'since-event-id (\d+)') { $since = [int]$Matches[1] }
if ($lastOut -match 'shelved-until (\S+)') { $until = $Matches[1] }
if (-not $until) { Stop-Here "shelve phase did not print shelved-until" }

Write-Host "`n== 6. restart the collector DURING the shelf =="
docker restart vigilimen-collector | Out-Null
Start-Sleep -Seconds 6
docker compose logs collector --tail 6
$rc = Ff28 @('--phase', 'after-restart', '--since-event-id', "$since", '--shelved-until', $until)
if ($rc -ne 0) { Stop-Here "after-restart failed: the shelf was lost, changed, or the alarm was raised again" }

Write-Host "`n== 7. FF-28 expiry: the shelf ends after the restart (about 1 minute) =="
$rc = Ff28 @('--phase', 'expiry', '--since-event-id', "$since", '--shelved-until', $until)
if ($rc -ne 0) { Stop-Here "expiry failed" }

Write-Host "`n== 8. FF-26 clear =="
$rc = Ff26 @('--phase', 'clear', '--expect-link', 'off', '--expect-append-only')
if ($rc -ne 0) { Stop-Here "clear phase failed" }

Write-Host "`n== 9. last alarm_event rows =="
docker exec vigilimen-historian psql -U vigilimen -d vigilimen -c "SELECT event_id, ts, condition, from_state, to_state, actor, note FROM alarm_event ORDER BY event_id DESC LIMIT 8;"

function Raise-Alarm($label) {
    $rc = Ff26 @('--phase', 'alarm', '--expect-link', 'off')
    if ($rc -ne 0) { Stop-Here "${label}: FF-26 alarm phase failed (the alarm could not be raised again)" }
}
function Shelve-Alarm($label, $extra) {
    $rc = Ff28 (@('--phase', 'shelve', '--minutes', '1') + $extra)
    if ($rc -ne 0) { Stop-Here "${label}: shelve failed" }
    $script:since = 0; $script:until = ''
    if ($lastOut -match 'since-event-id (\d+)') { $script:since = [int]$Matches[1] }
    if ($lastOut -match 'shelved-until (\S+)') { $script:until = $Matches[1] }
    if (-not $script:until) { Stop-Here "${label}: shelve did not print shelved-until" }
}
function Restart-Collector {
    docker restart vigilimen-collector | Out-Null
    Start-Sleep -Seconds 6
    docker compose logs collector --tail 4
}
function Check-Phase($label, $phaseArgs) {
    $rc = Ff28 $phaseArgs
    if ($rc -ne 0) { Stop-Here "$label failed" }
}

if ($Extended) {
    Write-Host "`n== A. restart AFTER the shelf expired =="
    Raise-Alarm 'A'
    Shelve-Alarm 'A' @()
    docker stop vigilimen-collector | Out-Null
    $left = ([DateTimeOffset]::Parse($until) - [DateTimeOffset]::UtcNow).TotalSeconds + 4
    if ($left -gt 0) { Write-Host "  collector stopped; waiting $([int]$left) s for the shelf to end"; Start-Sleep -Seconds ([int]$left) }
    docker start vigilimen-collector | Out-Null
    Start-Sleep -Seconds 8
    docker compose logs collector --tail 4
    Check-Phase 'A expiry' @('--phase', 'expiry', '--since-event-id', "$since", '--shelved-until', $until, '--settle', '4')

    Write-Host "`n== B. the condition clears DURING the shelf, restart in the middle =="
    Raise-Alarm 'B'
    Shelve-Alarm 'B' @()
    Restart-Collector                                  # the live collector now holds the SHELVED state
    Check-Phase 'B faults-off' @('--phase', 'faults-off', '--since-event-id', "$since", '--settle', '5')
    Restart-Collector
    Check-Phase 'B after-restart' @('--phase', 'after-restart', '--since-event-id', "$since", '--shelved-until', $until, '--expect-in-condition', 'false')
    Check-Phase 'B expiry' @('--phase', 'expiry', '--since-event-id', "$since", '--shelved-until', $until, '--expect-events', 'UNACK>SHELVED,SHELVED>NORMAL', '--expect-state', 'NORMAL', '--expect-in-condition', 'false')
    Write-Host "  OBSERVATION (not a failure): the history for this alarm holds UNACK>SHELVED then SHELVED>NORMAL. Nothing records that the condition ENDED while the alarm was shelved. Whether that is acceptable is a decision, not a test result."

    Write-Host "`n== C. ACKNOWLEDGED, then shelved, restart, expiry =="
    Raise-Alarm 'C'
    Shelve-Alarm 'C' @('--ack-first')
    Restart-Collector
    Check-Phase 'C after-restart' @('--phase', 'after-restart', '--since-event-id', "$since", '--shelved-until', $until, '--expect-events', 'UNACK>ACKED,ACKED>SHELVED')
    Check-Phase 'C expiry' @('--phase', 'expiry', '--since-event-id', "$since", '--shelved-until', $until, '--expect-events', 'UNACK>ACKED,ACKED>SHELVED,SHELVED>UNACK')

    Write-Host "`n== clear what the scenarios left =="
    $rc = Ff26 @('--phase', 'clear', '--expect-link', 'off', '--expect-append-only')
    if ($rc -ne 0) { Stop-Here "final clear phase failed" }
}

Stop-Transcript | Out-Null
Write-Host "FF-28 passed in Docker. Log: $log"
Write-Host "Stack left in embedded mode + persistence ON. To return to the default: new PowerShell window, docker compose up -d --build"
