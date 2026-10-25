<#
Live proof that PLC-CONV-001's network cannot reach SIS-CONV-001 (ADR-011, ADR-014).

    cd plant
    powershell -ExecutionPolicy Bypass -File tools\prove-isolation.ps1

WHY THIS REPLACES `docker exec vigilimen-plc-control ping -c2 sis-conv-001`
  * the OpenPLC image has no ping;
  * `sis-conv-001` is the SIS's `hostname:`, which Docker's DNS never answers, so
    that command fails on a bad NAME whether or not the networks are joined. It
    could not have failed any other way. A check that cannot fail proves nothing.

So this script (1) counts the members of net_safety, (2) tests the DNS name that
WOULD resolve if the networks were shared, (3) connects to the SIS by IP address,
and (4) runs the same probe against a reachable target as a POSITIVE CONTROL, so a
broken probe cannot pass for isolation.
#>
$ErrorActionPreference = 'Continue'   # native stderr must not become a terminating error in Windows PowerShell 5.1
$here = $PSScriptRoot
$fail = 0
function Result($ok, $text) {
    if ($ok) { Write-Host "  PASS  $text" } else { Write-Host "  FAIL  $text"; $script:fail++ }
}

Write-Host "Isolation proof: net_safety"

# 1. exactly one member, and not a relay someone left running
$members = (docker network inspect vigilimen-plant_net_safety --format '{{range .Containers}}{{.Name}} {{end}}').Trim()
Result ($members -eq 'vigilimen-plc-safety') "net_safety members: [$members] (expected only vigilimen-plc-safety; run tools\plc-ui-relay.ps1 -Action stop if a relay is listed)"

# 2. the DNS name that would resolve if the networks were shared
docker exec vigilimen-plc-control getent hosts plc-safety | Out-Null
Result ($LASTEXITCODE -ne 0) "plc-control cannot resolve the service name 'plc-safety' (Docker DNS only answers within a shared network)"

# 3. by IP, so DNS is not what blocks it.
# JSON, not a Go template: Windows PowerShell 5.1 strips the inner double quotes it passes to a
# native command, so a template naming "vigilimen-plant_net_safety" reaches docker as a bare word.
$sisIp = (docker inspect vigilimen-plc-safety | ConvertFrom-Json).NetworkSettings.Networks.'vigilimen-plant_net_safety'.IPAddress
$ctlIp = (docker inspect vigilimen-plc-control | ConvertFrom-Json).NetworkSettings.Networks.'vigilimen-plant_net_control'.IPAddress
Result (($sisIp -match '^\d+\.\d+\.\d+\.\d+$') -and ($ctlIp -match '^\d+\.\d+\.\d+\.\d+$')) "found both addresses: SIS=[$sisIp] control=[$ctlIp]"
if (-not $sisIp -or -not $ctlIp) { Write-Host "`nCannot test without both addresses. Not an isolation result."; exit 1 }
docker cp "$here\tcp_probe.py" vigilimen-plc-control:/tmp/tcp_probe.py | Out-Null

# 4. positive control first: the probe must be able to say CONNECTED
$ctl = (docker exec vigilimen-plc-control python3 /tmp/tcp_probe.py $ctlIp 8080) -join ' '
Result ($ctl -like 'CONNECTED*') "positive control: plc-control reaches its own UI at ${ctlIp}:8080 -> $ctl"

foreach ($port in 8080, 502) {
    $r = (docker exec vigilimen-plc-control python3 /tmp/tcp_probe.py $sisIp $port) -join ' '
    # REFUSED would mean a packet came back from the SIS: a route exists. That is a FAIL.
    Result ($r -like 'UNREACHABLE*') "plc-control -> SIS ${sisIp}:${port} -> $r"
}

# 5. the same on paper, from the compose files (needs Python on PATH)
if (Get-Command python -ErrorAction SilentlyContinue) {
    python "$here\..\..\scripts\ff22_compose_topology.py" | Out-Null
    Result ($LASTEXITCODE -eq 0) "FF-22 compose topology"
}

if ($fail -gt 0) { Write-Host "`nISOLATION NOT PROVEN ($fail failed). Do not 'fix' it: write symptom, cause, fix in the log first."; exit 1 }
Write-Host "`nIsolation proven. Screenshot this output."
