# Run notes: symptom, cause, fix

Write an entry BEFORE changing anything after a failed check. One block per failure.

| Date | Run | Symptom (exact text) | Cause | Fix |
|---|---|---|---|---|

## Found before Docker, in local runs (25 Oct 2026)

| Date | Run | Symptom | Cause | Fix |
|---|---|---|---|---|
| 25/10 | FF-24, first run | "PLC lost mid-run" case failed: belt kept running after the fake PLC was stopped | Test double: `shutdown()` leaves established handler threads serving, which is not what stopping a container does | `FakeOpenPLC.stop()` now closes accepted sockets |
| 25/10 | FF-24, first run | "program missing Stop_PB" not detected while idle | **Design flaw**: an unlocated coil reads FALSE, FALSE is what was written, so read-back alone cannot see a missing idle input | `Plc_Map_Version` signature (`MAP_VERSION`), checked every cycle; read-back kept for non-default values |
| 25/10 | FF-25, first run | two cases failed | Test bugs: `restore()` also commits (counted twice), and the SELECT matched the "alarm_state" filter | Test counts UPSERTs only, resets the counter after start-up |
| 25/10 | Review | Compose gave the PLC as `plc-conv-001`, a `hostname:` | Docker DNS does not answer for hostnames, only service names, container names, aliases | `VIGILIMEN_MODBUS_HOST: plc-control`; FF-22 checks it resolves |
| 25/10 | Review | `ping sis-conv-001` isolation proof | Fails on a bad name whether or not the networks are joined: a check that cannot fail | `tools/prove-isolation.ps1`: by IP, REFUSED counts as failure, positive control |
| 25/10 | Review | `pending()` advanced its mark before the insert | A failed insert lost alarm events permanently | Mark advances after commit (FF-25) |

## Docker runs

| Date | Run | Result |
|---|---|---|
| 25/10 15:17 | `validate-4e.ps1` (embedded mode), log `4e-20261025-151705.log` | FF-26: 7 checks, 0 failed. `alarm_event` 9: HI_HI NORMAL->UNACK 05:18:01.9, 10: UNACK->RTN_UNACK 05:18:02.9. FUXA by hand (import, START, Spike +8, Clear): works, per Epiphane. The measured spike-to-row latency line was not pasted; it is in the log. **4e validated on the embedded model.** |

## validate-plcio.ps1, first run (25/10 15:26)

| Symptom (exact) | Cause | Fix |
|---|---|---|
| gateway: `plc-link: program signature 0, expected 1`; FF-26 waits for PlcLinkOK | **Not yet established.** Observed: Modbus answers on plc-control:502; HR100 = 283 and coils 801..804 hold the values the gateway wrote; HR112 (Plc_Map_Version) = 0. Leading hypothesis: the program running in OpenPLC is not the new `conveyor_upload.st` (not uploaded, compile failed, or not started) | Pending: OpenPLC compile log and Dashboard (active program, Running) |
| Observation, whichever the cause | OpenPLC appears to **store Modbus writes to addresses no program locates** (HR100 holds 283 although the old program located nothing there). FF-24's fake **drops** them, which is wrong for this build. The read-back therefore cannot detect an unlocated address at all; **the signature is the only detector** | Correct FF-24's fake and the ADR-013 / plc_link wording after the real behaviour is confirmed |
- 15:31 plc-control log shows "OpenPLC Runtime starting" at 05:25:05 UTC with Modbus on 502, i.e. the PLC was started about a minute before the gateway first reported signature 0. That makes "program never started" less likely and "program started but signature not at HR112" more likely. Still unconfirmed: content of 843197.st, and where (if anywhere) the value 1 lands.
- 15:35 Evidence: `/workdir/webserver/core/openplc` (the runtime binary) is dated 02:24:29 UTC, and it is now 05:35. `active_program` = 843197.st, which DOES contain the new `AT` variables and Plc_Map_Version, but **no binary was built from it**. So the compile of the new program did not complete (or was not run), and the runtime restarted at 05:25:05 on the OLD binary. Memory scan: only HR100 (=287, the gateway's own write) and coils 801..804 (the gateway's own writes) are non-zero; HR112 = 0.
  - Cause (probable, not yet seen): MatIEC or the build rejected the new program. Next: the compile log from the OpenPLC UI.
  - Confirmed observation: this OpenPLC build STORES Modbus writes at addresses the running program does not locate (old binary, no `AT`, yet HR100 and coils 801..804 hold the gateway's values). The read-back cannot detect an unlocated address; only the signature can.

## MatIEC rejects conveyor_upload.st (25/10 15:38), written BEFORE the fix

| Symptom (exact) | Cause | Fix |
|---|---|---|
| Compile log of `630051.st` (same 8778 bytes as 843197.st, i.e. my file): `error: invalid located variable declaration` on lines 49-51, 53-56, 58, 64-68, then 40+ cascading `invalid variable before ':='` errors; `62 error(s) found. Bailing out!` | Lines 49-68 are the **plain** declarations (`Bearing_Temp : REAL;`, `State : INT := 0;`, `Warn_Timer : TON;`, `Alm_* : BOOL;`), not the `AT` ones (lines 32-46, which were accepted). MatIEC, like the IEC grammar, treats a `VAR` block as either **all located or all unlocated**: once the block starts with an `AT` declaration, every following line must be one too. I put both kinds in one block. The `:=` errors are the cascade: the variables were never declared | Split into two `VAR` blocks: located variables only, then the plain ones. FF-23 gains a property (no `VAR` block mixes the two) and a mutation. **Not yet re-compiled by MatIEC**: that is the next Docker step |

What FF-23 and FF-24 could not see: both read the file as text and neither runs MatIEC. FF-23's own epilogue said so.
- 15:46 Fix confirmed at the compiler stage: `iec2c -f -l -p -r -R -a -T /tmp/mt conveyor_upload.st` inside plc-control printed no errors and wrote POUS.c/.h, Config0.c/.h, Res0.c, LOCATED_VARIABLES.h, VARIABLES.csv. (The `EXIT=True` in that run is PowerShell expanding `$?` inside double quotes, my command's fault, not an exit code.) **MatIEC now accepts the located variables.** Still to do: full compile via the UI (g++ stages), Start PLC, signature check.
- 15:49 **Compile and start confirmed in OpenPLC.** Runtime binary rebuilt 05:48:32 UTC (was 02:24). Modbus read `HR100-112 = [286, 0, ..., 1]`: HR112 (`Plc_Map_Version`) = 1, so `%QW112` is holding register 112 as documented, and `%QW100` is HR100 (286 = the gateway's bearing temperature, 28.6 degC). Signature check satisfied. Still to run: `validate-plcio.ps1` end to end (FF-26 with the PLC in the loop, collector restart mid-alarm, isolation).

## validate-plcio.ps1 run 15:49 (log plcio-20261025-154947.log)

Passed in the real stack: gateway `plc-link: linked to plc-control:502, read-back clean`; FF-26 alarm phase 6/6 (START 10.4 s with the PLC horn, Spike +8 to `alarm_event` row 0.60 s); after-restart 2/2; clear 2/2 including **the append-only trigger refusing an UPDATE**.

| Symptom (exact) | Cause | Fix |
|---|---|---|
| prove-isolation: `template parsing error: template: :1: bad character U+002D '-'`, then `$sisIp` and `$ctlIp` null, then `tcp_probe.py` `IndexError` and three FAILs | **My script, not the isolation.** Windows PowerShell 5.1 strips the inner double quotes when it passes the Go template to docker, so `"vigilimen-plant_net_safety"` reached Go as a bare word containing `-`. The three FAILs are false negatives from empty IP arguments. The two checks that ran (net_safety has one member; plc-control cannot resolve `plc-safety`) and FF-22 passed | Read the IPs from `docker inspect` JSON with `ConvertFrom-Json` (no template quoting), and fail loudly if an IP is empty. **Isolation is NOT yet proven live.** |

## 15:54 validate-plcio.ps1 complete, isolation re-run

`prove-isolation.ps1` after the quoting fix: 7/7 PASS. net_safety has one member; plc-control cannot resolve `plc-safety`; SIS 172.20.0.2 and control 172.21.0.2 found; positive control CONNECTED to 172.21.0.2:8080; plc-control to SIS :8080 and :502 both `UNREACHABLE OSError [Errno 101] Network is unreachable` (not REFUSED); FF-22 pass. **Isolation proven live.**

Follow-ups done: FF-24's fake now STORES writes at unlocated addresses (the measured behaviour) and a KNOWN LIMIT case documents that a program with the right signature but a missing input is undetectable at run time; plc_link.py docstring and ADR-013 corrected; ADR-013 and ADR-019 moved to Accepted with what was and was not proven; README updated.

## 16:23 FF-27 in the real OpenPLC (log trips-20261025-162339.log): 13/13

PLC link up; START to state 3 after the horn (11.8 s); slip + seized idler trip FAULT in 1.4 s and the belt stops; **START does not clear a FAULT**, STOP does (1.2 s); one forged Modbus frame writing 96.0 degC to HR100 trips the PLC in **0.21 s**, belt stops, STOP recovers. So `conveyor.st`'s 42 A and 95 degC trips and its reset rule are proven in OpenPLC, not only in FF-24's port. The forged frame is also the S8 finding: no credential was asked for.

8 commits made locally by Epiphane (056dbc7..5443d67), not pushed. FF-03 passes after my-notes.md was cleaned.
