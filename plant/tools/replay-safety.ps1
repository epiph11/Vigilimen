<#
Drives safety.st BY EXECUTION and compares it with the Python model (ADR-014 follow-up).

    cd plant
    powershell -ExecutionPolicy Bypass -File tools\replay-safety.ps1

What it does: writes the model's expected outputs (scripts\safety_vectors.py), copies the vectors,
plc-upload\safety_upload.st and a small C++ harness into the plc-control container (chosen only because
it has iec2c and g++; this touches NO network and does NOT run the safety program on a runtime), has MatIEC
turn safety_upload.st into C, builds it with the harness, and replays every scan.

Any mismatch is a finding. Write SYMPTOM / CAUSE / FIX in docs\runs\NOTES.md before changing safety.st
or the model: this is the one place where changing the "wrong" side by reflex would be a safety decision.
#>
$ErrorActionPreference = 'Continue'
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$logDir = "$root\docs\runs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = "$logDir\safety-replay-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Transcript -Path $log | Out-Null

$vec = "$env:TEMP\safety_vectors.csv"
python "$root\scripts\safety_vectors.py" $vec
if ($LASTEXITCODE -ne 0) { Write-Host "could not write the vectors (is python on PATH?)"; Stop-Transcript | Out-Null; exit 1 }

docker exec vigilimen-plc-control mkdir -p /tmp/replay | Out-Null
docker cp $vec vigilimen-plc-control:/tmp/replay/vectors.csv | Out-Null
docker cp "$root\plant\plc-upload\safety_upload.st" vigilimen-plc-control:/tmp/replay/safety_upload.st | Out-Null
docker cp "$root\plant\tools\safety_replay.cpp" vigilimen-plc-control:/tmp/replay/safety_replay.cpp | Out-Null
docker cp "$root\plant\tools\replay_stubs.cpp" vigilimen-plc-control:/tmp/replay/replay_stubs.cpp | Out-Null
docker cp "$root\plant\tools\replay.sh" vigilimen-plc-control:/tmp/replay/replay.crlf.sh | Out-Null
# the checkout may have CRLF line endings; sh cannot run a script that has them
docker exec vigilimen-plc-control sh -c "tr -d '\r' < /tmp/replay/replay.crlf.sh > /tmp/replay/replay.sh"

$out = docker exec vigilimen-plc-control sh /tmp/replay/replay.sh
$rc = $LASTEXITCODE
$out | ForEach-Object { Write-Host $_ }

Stop-Transcript | Out-Null
if ($rc -eq 0) { Write-Host "`nsafety.st agrees with the model on every scan. Log: $log"; exit 0 }
Write-Host "`nNOT CLEAN (exit $rc). Lines with a 0 in the vs_model or vs_spec column are scans where the program disagrees. Log: $log"
exit 1
