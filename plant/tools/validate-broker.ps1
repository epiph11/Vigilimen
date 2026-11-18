<#
FF-38 in Docker: the DMZ broker's refusals, ACL, limits and revocation, against the REAL Mosquitto container.

    cd plant
    powershell -ExecutionPolicy Bypass -File tools\validate-broker.ps1

Needs the stack up with the broker healthy (docker compose up -d --build). Does:
  local FFs (22, 36, 37)  ->  broker healthy  ->  FF-38 main (a throwaway container on net_dmz speaks MQTT over TLS
  with the lab certificates: positive controls, refusals, ACL, limits)  ->  revocation sequence:
    1. issue the tester identity edge-old with an EMPTY CRL, restart the broker, edge-old must CONNECT
    2. put edge-old on the CRL, do NOT restart: report whether the broker notices (a FINDING, not a pass/fail)
    3. restart the broker: edge-old must be REFUSED
  ->  restore the production state (no tester, empty CRL) and restart the broker.
About 2 minutes. The throwaway container is a temporary extra member of net_dmz while it runs; it is removed after.
The tester identity exists only during this script.

IF ANYTHING FAILS: stop, and write SYMPTOM / CAUSE / FIX in docs\runs\NOTES.md before changing a line.
A surprising result: suspect the instrument first (this script, ff38_broker_live.py), not the broker.
#>
$ErrorActionPreference = 'Continue'
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location "$root\plant"
$logDir = "$root\docs\runs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = "$logDir\broker-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Transcript -Path $log | Out-Null

$net = 'vigilimen-plant_net_dmz'
$vol = 'vigilimen-plant_pki-mqtt'
$img = 'vigilimen-plant-pki-init'

function Stop-Here($why) {
    Write-Host ""
    Write-Host "STOPPED: $why"
    Write-Host "Write SYMPTOM / CAUSE / FIX in docs\runs\NOTES.md BEFORE changing anything. Log: $log"
    Stop-Transcript | Out-Null
    exit 1
}

function Wait-Broker {
    foreach ($i in 1..30) {
        $h = (docker inspect -f '{{.State.Health.Status}}' vigilimen-broker 2>$null)
        if ($h -and $h.Trim() -eq 'healthy') { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Run-Ff38([string[]]$phaseArgs, [bool]$withOld = $false) {
    $dargs = @('run', '--rm', '--network', $net,
        '--mount', "type=volume,source=$vol,target=/pki/edge,volume-subpath=edge,readonly",
        '--mount', "type=volume,source=$vol,target=/pki/consumer,volume-subpath=consumer,readonly")
    if ($withOld) { $dargs += @('--mount', "type=volume,source=$vol,target=/pki/edge-old,volume-subpath=edge-old,readonly") }
    $dargs += @('-v', "$root\scripts:/t:ro", '--entrypoint', 'python3', $img, '/t/ff38_broker_live.py')
    $dargs += $phaseArgs
    docker @dargs 2>&1 | ForEach-Object { Write-Host $_ }
    return $LASTEXITCODE
}

function Mqtt-Pki([string[]]$extra) {
    # pki-init has no network and owns the volume; only the MQTT part is run, so the OPC UA trust lists are untouched.
    $a = @('compose', 'run', '--rm', '--no-deps', 'pki-init', 'python3', 'mqttpki.py', 'init', '/pki-mqtt') + $extra
    docker @a 2>&1 | ForEach-Object { Write-Host $_ }
    return $LASTEXITCODE
}

Write-Host "== 1. local FFs (22, 36, 37) =="
foreach ($ff in 'ff22_compose_topology', 'ff36_mqtt_pki', 'ff37_broker_config') {
    python "$root\scripts\$ff.py" | Out-Null
    if ($LASTEXITCODE -ne 0) { Stop-Here "$ff failed locally. Run it to see why: python scripts\$ff.py" }
    Write-Host "  PASS  $ff"
}

Write-Host "`n== 2. the broker is up and healthy =="
docker compose build pki-init | Out-Null
if ($LASTEXITCODE -ne 0) { Stop-Here "docker compose build pki-init failed" }
docker compose up -d broker 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { Stop-Here "docker compose up -d broker failed" }
if (-not (Wait-Broker)) { Stop-Here "the broker is not healthy after 60 s: docker compose logs broker --tail 40" }
Write-Host "  PASS  vigilimen-broker healthy"

Write-Host "`n== 3. FF-38 main: refusals, ACL, limits =="
$rc = Run-Ff38 @('--phase', 'main')
if ($rc -ne 0) { Stop-Here "FF-38 main failed (read the positive controls first: a refusal means nothing if they failed)" }

Write-Host "`n== 4. revocation (1/3): edge-old issued, CRL EMPTY, broker restarted: it must connect =="
$rc = Mqtt-Pki @('--tester', '--no-revoke')
if ($rc -ne 0) { Stop-Here "mqttpki init --tester --no-revoke failed" }
docker restart vigilimen-broker | Out-Null
if (-not (Wait-Broker)) { Stop-Here "the broker is not healthy after the restart" }
$rc = Run-Ff38 @('--phase', 'revocation', '--identity', 'edge-old', '--expect', 'accepted') $true
if ($rc -ne 0) { Stop-Here "edge-old was not accepted before the revocation: the later refusal would prove nothing" }

Write-Host "`n== 5. revocation (2/3): edge-old put on the CRL, broker NOT restarted: does it notice? (a finding) =="
$rc = Mqtt-Pki @('--tester')
if ($rc -ne 0) { Stop-Here "mqttpki init --tester failed" }
Start-Sleep -Seconds 2
$rc = Run-Ff38 @('--phase', 'revocation', '--identity', 'edge-old', '--expect', 'report') $true
if ($rc -ne 0) { Stop-Here "the control client failed during the report step" }

Write-Host "`n== 6. revocation (3/3): broker restarted: edge-old must be refused =="
docker restart vigilimen-broker | Out-Null
if (-not (Wait-Broker)) { Stop-Here "the broker is not healthy after the restart" }
$rc = Run-Ff38 @('--phase', 'revocation', '--identity', 'edge-old', '--expect', 'refused') $true
if ($rc -ne 0) { Stop-Here "edge-old was not refused after the restart" }

Write-Host "`n== 7. restore the production state: no tester, empty CRL =="
$rc = Mqtt-Pki @()
if ($rc -ne 0) { Stop-Here "mqttpki init (restore) failed" }
docker restart vigilimen-broker | Out-Null
if (-not (Wait-Broker)) { Stop-Here "the broker is not healthy after the restore" }
Write-Host "  PASS  restored; broker healthy"

Stop-Transcript | Out-Null
Write-Host "FF-38 passed in Docker. Log: $log"
Write-Host "Read the FINDING line of step 5: it says whether this Mosquitto re-reads the CRL without a restart."
