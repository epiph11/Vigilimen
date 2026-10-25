<#
FF-27: conveyor.st's 42 A and 95 degC trips in the REAL OpenPLC.

    cd plant
    powershell -ExecutionPolicy Bypass -File tools\validate-trips.ps1

Needs the PLC link on (the compose default) and the program loaded, i.e. the state validate-plcio.ps1 leaves behind:
  docker compose up -d   (and, if the stack was last run embedded: Remove-Item Env:VIGILIMEN_PLC_LINK first)
  (conveyor_upload.st compiled and PLC started)
Takes about three minutes (two 10 s horns, a fault reset, a cool-down check).

IF ANYTHING FAILS: write SYMPTOM / CAUSE / FIX in docs\runs\NOTES.md before changing it.
#>
$ErrorActionPreference = 'Continue'
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location "$root\plant"
$logDir = "$root\docs\runs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = "$logDir\trips-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Transcript -Path $log | Out-Null

docker cp "$root\scripts\ff27_plc_trips_e2e.py" vigilimen-gateway:/tmp/ff27.py | Out-Null
docker exec -e VIGILIMEN_OPCUA_USER=engineer -e VIGILIMEN_OPCUA_PASSWORD=eng1neer-demo vigilimen-gateway python3 /tmp/ff27.py
$rc = $LASTEXITCODE

Stop-Transcript | Out-Null
if ($rc -ne 0) { Write-Host "FF-27 FAILED. Log: $log"; exit 1 }
Write-Host "FF-27 passed. Log: $log"
