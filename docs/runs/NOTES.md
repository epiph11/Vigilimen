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

## 16:40 Next item: drive safety.st by execution (ADR-014 follow-up)

`scripts/safety_vectors.py` writes the PYTHON MODEL's expected outputs for 12 scenarios (59 scans). The other half, running safety.st through MatIEC's generated C in an OpenPLC container on no network, is not written yet: it needs the exact names iec2c generates (asked of Epiphane). Predicted divergence from reading both files, to be confirmed or refuted by execution, not assumed: the model resets on the reset LEVEL (`safety_reset_pressed`), safety.st only on a rising EDGE (`R_TRIG`); ADR-011 says edge. Side effect already visible: the gateway holds `safety_reset_pressed=True` forever, so the gateway's contactor MODEL auto-restarts as soon as a demand clears (scenario `reset_held_across_trip` ends energised). Inert today because nothing ever drives an e-stop input in the simulation; it would be wrong the first time something does.

## 21:45 replay-safety.ps1, first run (log safety-replay-20261025-214458.log), written BEFORE the fix

| Symptom (exact) | Cause | Fix |
|---|---|---|
| `g++`: `iec_std_lib.h: conflicting declaration 'typedef struct tm tm'`, then `tm_day` errors; also `'SIS_CONV_001' was not declared ... did you mean 'PLC_CONV_001'?` and `POUS.h` resolved to `/workdir/webserver/core/POUS.h` | **Two harness mistakes, mine.** (1) I passed `-I /workdir/webserver/core` before the generated directory, so `#include "POUS.h"` found the POUS.h of the CONV-001 program left there by the real compile, not the safety one. (2) The harness included `<iostream>`, `<string>`, `<vector>` before `POUS.h`; libstdc++ pulls in `<time.h>`, whose `struct tm` clashes with the `tm` typedef in OpenPLC's `iec_std_lib.h` (OpenPLC's own sources never include those first) | Generated directory first on the include path; the harness uses only C headers, after `POUS.h`. `iec2c` itself succeeded (the log ends with the generated file list) |

## 21:46 replay-safety.ps1, second run (log safety-replay-20261025-214648.log), written BEFORE the fix

| Symptom (exact) | Cause | Fix |
|---|---|---|
| The harness now compiles; `g++` fails only in `gen/POUS.c`: `'SIS_CONV_001' was not declared`, `'BOOL' was not declared` at line 1 | **My build line again.** MatIEC's `POUS.c` has no `#include` of its own: OpenPLC builds it by having `Res0.c` / `Config0.c` `#include "POUS.c"` after `POUS.h`. Compiling it as a separate translation unit leaves it with no types | `#include "POUS.c"` in the harness, after `POUS.h`, and `POUS.c` removed from the g++ command |
- 21:51 Third run again ended `G++ FAILED` but the log holds NO compiler text: `$out = docker exec ...` captures stdout only and g++ writes to stderr, so the error went to the console and not to the transcript. Not a result. replay.sh now writes g++ and iec2c output to files inside the container and prints the first 40 lines itself, so the transcript always carries the cause.

## 21:50 replay-safety.ps1, fourth run (log safety-replay-20261025-215030.log), written BEFORE the fix

| Symptom (exact) | Cause | Fix |
|---|---|---|
| Compiles; the LINK fails: `undefined reference to connect_to_tcp_server(...)`, `send_tcp_message(...)`, `receive_tcp_message(...)` from `TCP_CONNECT_body__`, `TCP_SEND_body__`, `TCP_RECEIVE_body__` | OpenPLC's `iec_std_FB.h` defines the TCP function blocks inline, and they call three functions the PLC runtime provides. `safety.st` uses none of them, but the blocks are compiled into every translation unit that includes the library | `-Wl,--unresolved-symbols=ignore-all`: the functions are never called by this program. (Not three hand-written stubs: that would guess their signatures.) |

## 21:55 replay-safety.ps1, fifth run (log safety-replay-20261025-215435.log), written BEFORE the fix

| Symptom (exact) | Cause | Fix |
|---|---|---|
| `/tmp/replay/replay: error while loading shared libraries: unexpected PLT reloc type 0x00`, exit 127 | My previous fix. `--unresolved-symbols=ignore-all` lets the linker finish but leaves relocations the loader cannot resolve | Real stubs for the three functions, in a separate translation unit (`replay_stubs.cpp`) that does not include OpenPLC's headers, so the C++ signatures from the linker's own error text are used as they are, with no guess about the return type (which is not part of the symbol). The flag is removed |

## 21:56 replay-safety.ps1: safety.st driven by execution for the first time (log safety-replay-20261025-215630.log)

`SUMMARY 63 scans, 0 mismatches` (12 scenarios; I wrote 59 scans earlier, the true count is 63). safety.st, compiled by MatIEC and run through OpenPLC's own TON and R_TRIG, agrees with the Python model on every scan, including cold start, e-stop and pull-cord trips, belt drift, guard open, reset refused while a demand persists, and the discrepancy timer.

**One result contradicts the code as I read it, and it is NOT yet explained.** Scenario `reset_held_across_trip` (reset held high on every scan, one e-stop pulse at step 2): both model and program re-energise at step 3, when the e-stop clears. The model does so by design (it resets on the reset LEVEL). But safety.st calls `Reset_Edge(CLK := Safety_Reset)` on every scan and resets only on `Reset_Edge.Q`; with the button held since step 0 there is no new rising edge at step 3, so by my reading the program should stay TRIPPED. I predicted a divergence (model level vs program edge) and the run showed none. Either R_TRIG as compiled here does not behave as an edge detector across scans in this harness, or the harness feeds it something other than I think, or my reading is wrong. Until that is settled the replay cannot be taken as evidence that safety.st implements ADR-011's "rising edge, not level". Checking: the R_TRIG body in OpenPLC's iec_std_FB.h and how the generated POUS.c calls it.
- 22:02 R_TRIG as compiled is correct (`Q = CLK && !M; M = CLK`) and safety.st calls it on EVERY scan (POUS.c lines 36-37), so by the code `reset_held_across_trip` step 3 cannot reset. `safety_upload.st` body is byte-identical to `safety.st` (checked), so the upload is not stale. The replay still shows the program energised at step 3. Not explained. The harness now prints the edge detector's Q, its memory M, the e-stop demand and CLK on every scan, so the next run shows which of them is not what the code says.
- 22:06 Diagnostic columns, scenario `reset_held_across_trip` (CLK held at 1 on every scan): `edge_q` = 1 and `edge_m` = 0 on EVERY scan, including the scans after the first. So the detector's memory M is 0 after each call and Q = CLK. That is not what the R_TRIG source says (`M = CLK` after computing Q). Either the library as compiled here does not latch M, or the harness reads M wrongly, or something re-initialises it. Next: an isolated R_TRIG self-test in the harness (CLK=1 on two consecutive calls, expect Q=1,0 and M=1). No safety conclusion until it runs. If the library itself is the cause, it matters beyond safety.st: conveyor.st's Start_Edge and the real OpenPLC runtime use the same block.
- 22:09 SELFTEST: `q1=1 m1=1 q2=0 m2=1`. The R_TRIG library, compiled the way the replay compiles it, is a working edge detector. So the library is cleared. In the program, though, `RESET_EDGE.M` reads 0 after every scan while CLK is 1. Something between scans, or inside SIS_CONV_001_body__, leaves M at 0 or my diagnostic reads a different thing. Next: the generated body (POUS.c lines 1-60) to see what touches RESET_EDGE.

## 22:10 Where the safety.st replay stands, in plain terms

- WHY IT EXISTS: ADR-014 admitted safety.st had never been run, only read (FF-21) and modelled (FF-06). The replay runs the program MatIEC compiles from it, with the same timer and edge blocks OpenPLC uses, on 12 scenarios and compares with the Python model scan by scan.
- RESULT: 63 scans, 0 disagreements. That is good news and is established.
- WHY I KEEP DIGGING AT ONE SCENARIO: `reset_held_across_trip` is the stuck-reset-button case: reset held high, an e-stop pulses and clears. ADR-011 says reset must be a rising EDGE so a held or jammed button cannot restart the belt behind someone. Both model and program energise the contactor again at step 3. By the code the program should not. The diagnostic columns show the program's edge detector memory reading 0 after every scan; a stand-alone test of the same block works. So the library is cleared and the cause is unexplained.
- WHAT IS NOT CONCLUDED: that safety.st violates ADR-011. It is also not concluded that it complies on this point. My earlier prediction (model resets on level, program on edge, so they diverge) was WRONG: the run showed no divergence.
- DECISION FOR EPIPHANE, not for me: if it is a real property of safety.st, whether to change the program or the ADR is a safety decision.
- 22:15 POUS.c lines 1-62 read: the generated body reproduces safety.st statement for statement (demands, TON, trip IF, `RESET_EDGE.CLK := SAFETY_RESET`, `R_TRIG_body__`, reset IF, outputs). Nothing in it touches RESET_EDGE.M. Library cleared (SELFTEST ok), upload cleared (identical to safety.st), generated code cleared. What is left is the harness itself (how it feeds or reads the instance). Still unexplained; most likely my harness. NOT a safety conclusion.

## 00:30 Last bounded diagnostic on the held-reset question (Epiphane chose option 2)

The harness now also prints `m_before` and `q_before`: the edge detector's memory and output as they stand BEFORE each call of the program body. Reading: if `m_before` is 0 at a scan that follows a scan where CLK was 1, then M was cleared between scans (by something outside the body, so my harness or memory layout). If `m_before` is 1 but `q_before`/`edge_q` still shows 1 after the call, the body itself is computing Q wrongly. One run, then stop: whatever it shows, the next step is documenting it, not a fourth hypothesis.

## 00:45 RETRACTION: the "63 scans, 0 mismatches" result is NOT valid evidence (written before the fix)

Run at 00:31 with two extra read-only columns (`m_before`, `q_before`): `SUMMARY 63 scans, 35 mismatches`, `edge_m` = 1, and the held-reset scenario now behaves as the code says it should (program stays TRIPPED at step 3, model re-energises). Reading two variables cannot change what a program does, so the harness has **undefined behaviour**: its results moved when unrelated code around them moved.

Most likely cause (not yet confirmed by reading accessor.h): `SIS_CONV_001 inst;` was a LOCAL variable. MatIEC's variables are `{ value, flags }` pairs and OpenPLC's `__GET_VAR` / `__SET_VAR` look at `flags` (a FORCE bit returns a forced value and skips writes). OpenPLC keeps its instances in static storage, zeroed; a stack variable holds garbage there. The same garbage would explain `edge_m` reading 0 for scans, and the odd rows at 00:31 where contactor and tripped disagree.

Consequences, stated plainly:
 1. The earlier claim "safety.st agrees with the model on all 63 scans" is WITHDRAWN until the harness is re-run with static, zeroed storage. It may have been matching by luck.
 2. The "unexplained held-reset" puzzle probably was never about safety.st: its premise (edge_m = 0) was an artefact of the harness.
 3. The etat-des-lieux text that quotes the 63/0 result and the "Pourquoi on creuse" section describe findings that are not established. They must be rewritten with the re-run result.
Fix applied: `static` instance, `memset` before each cold start and before the R_TRIG self-test. Next: one clean run, then rewrite the docs from what it really shows.

## 00:50 Clean run after the `static` + `memset` fix: 63 scans, 2 mismatches. My original prediction was RIGHT

`SELFTEST q1=1 m1=1 q2=0 m2=1`. `SUMMARY 63 scans, 2 mismatches`. The two are `reset_held_across_trip` steps 3 and 4: model contactor 1 / tripped 0, program contactor 0 / tripped 1. `edge_m` now latches (1 after the first scan). Everything else (61 scans, 11 other scenarios) agrees.

Reading: with the reset button held high and an e-stop that pulses and clears, the PROGRAM stays tripped (it needs a new rising edge, as ADR-011 requires) and the MODEL re-energises (it resets on the level). So the program follows the requirement and the model does not. The model, and the gateway's contactor model that holds `safety_reset_pressed = True`, are the defective side.

Corrections to what I said earlier today:
 * "63 scans, 0 divergence" (earlier): an artefact of the harness reading uninitialised memory. Withdrawn, as already recorded.
 * "My prediction (model resets on level, program on edge) was wrong": WRONG about being wrong. The prediction was right; the harness hid it. I reached the wrong conclusion by trusting an instrument I had not validated.
 * The "unexplained edge detector" puzzle: closed. It was the harness (stack garbage in the `flags` bytes). safety.st was never the problem.

Still to do, and not done: (1) re-run with the new vectors that carry a SPEC column beside the MODEL column (expected from this run: 2 differ from the model, 0 from the spec; that is a prediction, not a result); (2) fix the model to reset on a rising edge, which is a change to a safety-related file and needs Epiphane's go-ahead; (3) the gateway must then send reset as a pulse.

## 00:42 Replay with the SPEC column (log of Epiphane's run): 63 scans, 2 differ from the MODEL, 0 differ from the SPEC (ADR-011)

SELFTEST ok. `reset_held_across_trip` steps 3 and 4: model contactor 1 / tripped 0; spec contactor 0 / tripped 1; program contactor 0 / tripped 1. So the program matches the requirement on every one of the 63 scans, and the model departs from it on exactly the two scans where the reset button is held while an e-stop clears. This confirms the prediction written at 00:30 (a prediction, now a result). Defect located in `interlock_model.SafetyFunction` (resets on the reset LEVEL) and, through it, in the gateway's contactor model, which holds `safety_reset_pressed = True`.

Not done, waiting for Epiphane's decision: change `interlock_model.py` to reset on a rising edge; then re-run FF-06, FF-07, FF-21, FF-24 and the replay; then make the gateway pulse the reset instead of holding it.

## 00:50 Epiphane approved the model fix (reset on a rising edge). Before the change:

Files touched: `plant/sim/interlock_model.py` (SafetyFunction: remember the previous reset level and reset only on a rising edge, updated on EVERY scan including the scans that return early on a trip, as safety.st's R_TRIG is called on every scan) and `plant/gateway/plant_cycle.py` (reset becomes a single pulse on the first scan after start, instead of being held). Backups of both before-states are in /tmp of the working session only; the repository history has the originals. To be re-run locally: FF-06, FF-07, FF-21, FF-22, FF-23, FF-24, FF-25 and the vector generator. The replay itself needs Docker and is Epiphane's to run. Any FF-06 case that relied on a held reset will fail, and would be shown before being changed.
- 00:58 Done locally (nothing committed): `SafetyFunction` now resets on a rising edge (`_reset_prev` updated on every scan, before any early return); `PlantCycle` presses the panel reset once, on the first scan. FF-06 gained two cases (15 total): a HELD reset does not restart the belt after a trip, and releasing then pressing again does. **The new case fails on the old model and passes on the new one** (checked by swapping the old file back in and restoring). FF-06, 07, 21, 22, 23, 24, 25 and FF-01 pass. The vector generator now gives model == spec on every row (63), so `SPEC_OVERRIDES` stays as the independent statement of the rule but no longer differs from the model. Not run, needs Docker: the gateway rebuild with the one-shot reset, FF-27, and the replay (prediction: 0 differ from the model, 0 from the spec).

## 00:52 After the model fix and the gateway rebuild (one-shot reset): FF-27 13/13 (log trips-20261026-004914.log)

PLC link up; START to RUNNING after the horn in 11.4 s; overload trip in 1.6 s; START does not clear a FAULT; STOP clears it in 1.0 s; one forged Modbus frame (96.0 degC) trips the PLC in 0.21 s; recovery 1.0 s. So pressing the panel reset once at start, instead of holding it, did not break the running plant: the contactor model energised on the first scan's edge and the PLC loop behaved as before. Commits 9634611 (replay bench) and b55c150 (edge-triggered model, FF-06 15 cases) are local, not pushed. Still to see: the replay with the corrected model (prediction: 0 differ from the model, 0 from the spec).

## 00:55 Replay after the model fix still shows the OLD model column (not understood yet)

Epiphane's run printed `reset_held_across_trip,3,1,0,0,1,...` i.e. model contactor 1 / tripped 0, and `SUMMARY ... 2 differ from the MODEL`: identical to the run before the fix. The corrected model gives `0,1` on the same row when the generator is run in my environment (checked: model == spec on all 63 rows). So on Epiphane's machine the vectors were generated by the old model, or the CSV copied into the container is stale. Not concluded; the prediction (0 / 0) is NOT confirmed. Asked for: the model columns of a freshly generated CSV, and a grep for `_reset_prev` in the file on Epiphane's disk.
- 00:58 Epiphane's checks: `_reset_prev` is in his interlock_model.py (lines 99, 105, 106), and his own `safety_vectors.py` run gives `reset_held_across_trip,3,...,0,1,0,1` (model 0/1, spec 0/1), i.e. the corrected model. So the generator is right on his machine; yet the replay output still shows model 1/0. Either that output was the earlier one, or the container kept a stale `vectors.csv` (docker cp failing quietly), or the CSV the script wrote was not the one copied. replay-safety.ps1 now prints the host row, the container row and the container file's timestamp before replaying, so the log shows which.

## 00:57 Replay with the corrected model: CONFIRMED. 63 scans, 0 differ from the MODEL, 0 differ from the SPEC (ADR-011)

The new diagnostics showed the host row and the container row identical (`reset_held_across_trip,3,...,0,1,0,1`) and the container file stamped 00:57 Brisbane, i.e. fresh. `reset_held_across_trip` steps 3 and 4 now read model 0/1, spec 0/1, program 0/1. SELFTEST ok. I do NOT know why the run at 00:53 still showed the old model column: the transcript I was given for it matches the earlier run line for line, so a stale paste is the likeliest reason, but that is a guess and is recorded as one.

State: the safety program matches the requirement on all 63 scans; the model, after commit b55c150, matches it too; FF-06 has 15 cases, one of which fails on the old model. Commits 9634611 (bench) and b55c150 (model) are local. `replay-safety.ps1` was changed after 9634611 (it prints what the container received); that needs a small third commit. Nothing pushed.

## 01:20 Station 5 findings F2 and F4 fixed in text (F1 and the xlsx Summary sheet are not)

F2: hydro-station README said "seven risks were renoted"; document 12 says seven inherited consequence 5, six renoted, R-20 already direct. README now agrees with document 12. The Summary sheet of the xlsx may still carry the "seven" wording: editing it needs Excel, not a script (it would also fix F1, the missing cached values). F4: document 01 section 2 said both regulatory characterisations were "assumed, not verified"; it now says the first is resolved on a SECONDARY source (30 MW, ADR-006) and still to be confirmed against the primary SOCI rules, and the second is open. I did not verify the 30 MW figure myself.

## 01:30 Decision (Epiphane): follow the plan (S5 starts 16 Nov); make the PLC link the compose default; keep the embedded model if it has value

Value of keeping embedded, judged: (1) it is the Python control logic FF-06/FF-07 reason about, so it is the REFERENCE the PLC behaviour can be compared against; (2) a zero-setup baseline: with no program loaded in OpenPLC the PLC mode shows PlcLinkOK=False and the belt will not run (fail-safe), so a fresh clone or a demo needs the embedded model to show anything move; (3) it separates a gateway fault from a PLC fault when debugging. Cost: two modes to keep honest, and the risk of running the wrong one without noticing. So: keep it, as an explicit opt-out (`VIGILIMEN_PLC_LINK=off`), default is `modbus`. The mode is visible in the gateway's startup line and in the PlcLinkOK tag. Changes: base compose reads the two env vars with defaults (modbus, on); docker-compose.plcio.yml becomes redundant (stub now, `git rm` by Epiphane); validate-4e.ps1 sets embedded for itself; validate-plcio.ps1 and validate-trips.ps1 use the base file; FF-22 gains a property and a mutation (the default is the PLC link); ADR-013, ADR-019, README updated. The code defaults (gateway, collector) stay `off`, so anything run outside compose is embedded and safe.
- 01:40 Local checks after the default switch: FF-22 (now 12 properties, 10 mutations), FF-06, 07, 21, 23, 24, 25, FF-01 pass. NOT run, needs Docker: `docker compose up -d --build` in default mode, validate-trips.ps1, validate-4e.ps1 (which now opts into embedded for itself). The état-des-lieux and walkthrough copies in the MINE 360 project still describe docker-compose.plcio.yml; they are to be resynchronised once, after the Docker results.
- 01:50 Epiphane asked for the containers to be explained in the state document (why each, why collector, why gateway, how they connect, in simple terms). Section added to docs/VIGILIMEN-etat-des-lieux.md before "Les tests de sécurité", written from docker-compose.yml (networks, ports, depends_on, healthchecks) and the code, not from memory. Also published as a short standalone project doc, claude/VIGILIMEN-conteneurs.md.

## 26/10 (matin) FF-28 écrit, PAS ENCORE LANCÉ : DELETE/TRUNCATE sur alarm_event, redémarrage du collecteur pendant SHELVED

Fichiers : `scripts/ff28_alarm_durability.py` (4 phases : tamper, shelve, after-restart, expiry) et `plant/tools/validate-durability.ps1` (orchestre, mode embedded + persistance ON). Vérifié ici : compile, FF-03 et FF-05 passent. Non vérifié : tout ce qui touche Docker.
Choix à connaître : (1) l'attendu vient de l'ADR-019 et d'ISA-18.2, écrits par le même auteur que le moteur : accord avec l'exigence telle qu'écrite, pas une preuve indépendante. (2) Auto-test de l'instrument : dans une transaction annulée, on supprime les deux triggers et DELETE/TRUNCATE doivent RÉUSSIR ; sinon le test de refus ne prouve rien. Il montre aussi que le propriétaire de la table peut supprimer le trigger (limite déjà connue, ADR-019, S8). (3) Le SHELVE est fait par le script via AlarmFeed/engine/store du collecteur (le stack n'a pas d'écran opérateur) ; le collecteur vivant garde son état mémoire jusqu'au redémarrage, c'est voulu. (4) Étagère de 1 minute (minimum du moteur) : le redémarrage doit tomber dedans, sinon « TOO SLOW », relancer.
Prédictions (à confirmer par l'exécution, ce ne sont pas des résultats) : tamper tout PASS ; après redémarrage historique du Vibration HI_HI = [SHELVED] seul ; à l'expiration, un seul SHELVED->UNACK « shelf expired ».

## 26/10 03:15 validate-durability.ps1 s'arrête à l'étape 1 : ff25 « échoue en local »

SYMPTOM: validate-durability.ps1 s'arrête à l'étape 1 sur ff25_alarm_persistence ; lancé seul, ff25 passe (19 cas, 0 échec).
CAUSE (confirmée par l'exécution) : le script met VIGILIMEN_ALARM_PERSIST=on pour tout son processus AVANT les fitness functions locales ; ff25 contient le cas « persistence is OFF unless VIGILIMEN_ALARM_PERSIST says so », qui échoue dans cet environnement. Avec la variable à 'on' : 19 cas, 1 échec ; sans : 19 cas, 0 échec. Défaut de l'instrument (le script), pas du collecteur.
FIX : la variable n'est positionnée qu'APRÈS l'étape 1 (les FF locales tournent sans elle), juste avant le docker compose.

## 26/10 03:01 validate-durability.ps1 : arrêt à l'étape 2 (build), Docker injoignable. Aucun test FF-28 n'a tourné.

SYMPTÔME : `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine ... The system cannot find the file specified`. Étape 1 (FF-07, FF-22, FF-25, compilation FF-28) : PASS. Log : docs\runs\durability-20261026-030055.log.
CAUSE : Docker Desktop (moteur Linux) n'est pas démarré. Pas un défaut de FF-28 ni du script ; même famille que « Docker/WSL arrêté » déjà vu avant le 25/10. Déduit de l'erreur, pas encore confirmé par `docker version`.
CORRECTION : démarrer Docker Desktop, attendre que le moteur soit « running », puis relancer le script. Aucun changement de code.
- 03:19 Deuxième essai, même erreur exacte (npipe dockerDesktopLinuxEngine introuvable). Docker n'était donc toujours pas joignable. Log : docs\runs\durability-20261026-031908.log. Cause précise (Docker Desktop fermé, moteur WSL arrêté, ou autre) non établie : en attente de `docker version` et `wsl --status`.

## 26/10 03:36 FF-28 dans Docker : 11 + 3 + 4 + 3 contrôles, 0 échec (log durability-20261026-033558.log)

Embedded + persistance ON. Tamper : DELETE (une ligne, toutes), TRUNCATE (simple, RESTART IDENTITY CASCADE) et UPDATE refusés par le déclencheur, 31 lignes avant et après. Auto-test de l'instrument : sans les deux déclencheurs, DELETE et TRUNCATE réussissent (deleted=1, 0 ligne restante dans la transaction), puis annulation : 31 lignes. Shelve : événement 32 UNACK->SHELVED (ff28-operator, 1 min), alarm_state SHELVED avec échéance. Redémarrage du collecteur à 51 s de la fin : SHELVED conservé, shelved_until identique à la microseconde, historique de ce HI_HI depuis le shelve = [SHELVED] seul. Expiration après le redémarrage : un seul SHELVED->UNACK « shelf expired » (événement 34, 0,5 s après l'échéance), alarm_state UNACK, échéance vidée. Les trois prédictions écrites avant le run sont confirmées.
À ne pas sur-lire : (1) l'attendu vient de l'ADR-019 et d'ISA-18.2, même auteur que le moteur. (2) Le côté « redémarrage » n'a pas eu de mutation (ex. restore qui ignore shelved_until) : l'égalité exacte de l'échéance rend un tel défaut visible, mais je ne l'ai pas démontré. (3) Non couverts : redémarrage APRÈS l'échéance, alarme revenue normale pendant l'étagère puis redémarrage, ACKED puis shelve. (4) Le shelve est fait par le script avec le code du collecteur, pas par un écran opérateur. (5) Les « ΓÇö » dans la sortie sont l'em dash du script lu en cp437 par PowerShell 5.1 : cosmétique.

## 26/10 14:00 Finding F1 (xlsx sans valeurs en cache) : classeur recalculé avec LibreOffice, pas Excel
Epiphane n'a pas Excel. 05-detailed-risk-assessment.xlsx recalculé et réenregistré avec LibreOffice (headless). Vérifié sur une copie avant remplacement : 8 feuilles identiques, 283 formules inchangées (0 écart), 283 valeurs en cache (0 avant), aucune erreur, mises en forme conditionnelles, validations, fusions et volets figés comptés identiques. Résultats (Extreme 11, High 28, Medium 1, 39 à traiter sur 40, 16 en dérogation vie-sécurité) égaux à ceux de scripts/s5_recompute_register.py. Non vérifié : l'aspect visuel (polices, couleurs, largeurs) dans Excel ; le fichier porte maintenant LibreOffice comme application d'origine. Retour arrière : git checkout -- le fichier.

## 26/10 14:01 Annotations CI : run #14 sans annotation (constat d Epiphane sur la page Summary)
Le warning Node.js 20 et la notice ubuntu-latest du run #13 ont disparu après 4547f93 (ubuntu-24.04, checkout v5, setup-terraform v4). Constat visuel d Epiphane, pas relu dans les logs par moi. FF-02 vert (init + validate).

## 26/10 14:30 FF-28 étendu (écrit, PAS lancé) : trois scénarios + section « Deux modes de fonctionnement » dans l'état des lieux
Scénarios (`validate-durability.ps1 -Extended`) : A redémarrage APRÈS l'échéance ; B condition revenue normale PENDANT l'étagère, avec redémarrage au milieu ; C acquittée puis mise en étagère. Prédictions écrites AVANT l'exécution, obtenues en rejouant seulement le moteur (`engine.py`) dans un environnement séparé, donc des prédictions, pas des résultats : A un seul SHELVED->UNACK « shelf expired » ; B reste SHELVED avec in_condition False après le redémarrage, puis SHELVED->NORMAL à l'expiration (jamais UNACK) ; C UNACK->ACKED, ACKED->SHELVED, puis SHELVED->UNACK (l'acquittement n'est pas conservé).
Observation déjà visible dans le code, à décider (pas un échec de test) : tant qu'une alarme est SHELVED, `_on_condition_start` et `_on_condition_clear` rendent la main sans événement. Dans le scénario B l'historique ne contient donc aucune ligne disant que la condition a cessé pendant l'étagère, alors que le commentaire de FF-07 dit « hidden from the LIST, never from the AUDIT ». Ce que demande ISA-18.2 là-dessus n'a pas été vérifié.
Instrument : le banc (ff28, orchestrateur) n'a pas tourné ; il compile et les parenthèses du .ps1 sont équilibrées, rien de plus. Un résultat surprenant : suspecter d'abord ce banc (par exemple le minutage du scénario B, deux redémarrages dans une étagère d'une minute).

## 26/10 14:31 validate-durability.ps1 -Extended : erreur d'analyse PowerShell, rien n'a tourné
SYMPTÔME : `Variable reference is not valid. ':' was not followed by a valid variable name character` aux lignes 129, 133 et 137 (`"$label: ..."`). Aucun test lancé, la pile n'a pas été touchée.
CAUSE : défaut du script que j'ai écrit : dans une chaîne entre guillemets, `$label:` est lu comme une référence de lecteur (`$env:`, `$script:`). Le script n'avait pas pu être analysé ici (pas de PowerShell dans mon environnement : seules les parenthèses étaient comptées, ce qui ne détecte pas ce genre d'erreur).
CORRECTION : `"${label}: ..."` aux trois endroits ; recherche des autres `$nom:` dans le fichier.
CONTRÔLE de l'instrument : PowerShell 7.4.6 (téléchargé dans mon environnement) analyse l'ancien fichier et reproduit exactement les trois erreurs (129:33, 133:33, 137:42), puis analyse le fichier corrigé sans erreur. Limite : analyse en PowerShell 7, pas en Windows PowerShell 5.1 que tu utilises, et analyse seulement : le déroulement du script n'a pas été exécuté.

## 26/10 14:33 validate-durability.ps1 -Extended : arrêt à l'étape 1, ff25_alarm_persistence « failed locally »
SYMPTÔME : FF-07 et FF-22 passent, FF-25 échoue, le script s'arrête avant toute action Docker. Reproduit chez moi : `VIGILIMEN_ALARM_PERSIST=on python scripts/ff25_alarm_persistence.py` donne 19 cas, 1 échec : « persistence is OFF unless VIGILIMEN_ALARM_PERSIST says so » ; sans la variable, 19/19.
CAUSE : mon erreur. Le script validé dans le commit e1eefef posait VIGILIMEN_ALARM_PERSIST='on' APRÈS l'étape 1 (correction du 03:15, voir plus haut). Pour livrer les scénarios étendus j'ai réécrit le fichier à partir de MA copie de départ, sans relire la version présente sur ta machine, et je l'ai écrit par-dessus : la correction a disparu et la variable était de nouveau posée avant FF-25. Aucune vérification de date de modification n'a été demandée à l'écriture. Le même contrôle montre que ff28_alarm_durability.py n'a perdu aucune ligne autre que celles que je remplaçais volontairement.
CORRECTION : variable reposée juste avant l'étape 2, avec le commentaire d'origine. Différence restante avec e1eefef : l'option -Extended et les trois scénarios, plus le passage des identifiants OPC UA à `docker exec` pour ff28. Fichier analysé sans erreur avec PowerShell 7.4.6 (pas 5.1) ; non exécuté.
Leçon pour mes écritures sur ta machine : relire la version courante et garder la date de modification comme garde-fou.

## 26 oct. 2026, 14 h 35 : FF-28 -Extended (log durability-20261026-143527.log)
Résultat : étapes 1 à 9 et scénarios A, B, C tous verts, 0 échec (log complet, fin 14 h 41). Les prédictions écrites avant le lancement sont toutes confirmées.
A : arrêt du collecteur, attente de l'échéance, redémarrage -> exactement UNACK>SHELVED, SHELVED>UNACK. B : condition retirée pendant SHELVED, deux redémarrages -> SHELVED reste, in_condition False, puis SHELVED>NORMAL. C : UNACK>ACKED, ACKED>SHELVED, redémarrage, SHELVED>UNACK.
Limites : (1) les prédictions venaient de la lecture de engine.py, pas d'une source indépendante ; (2) l'étape 9 (psql, 8 dernières lignes) n'apparaît pas dans la transcription, sortie des commandes natives non capturée par Start-Transcript, cause non vérifiée ; (3) la pile reste en embedded après le script.
OBSERVATION B : aucun événement quand la condition cesse pendant SHELVED. Décision à prendre, pas un test.

## 15/11 Lot V4.1, première tranche (ADR-023 accepté) : écrit et testé localement, rien lancé dans Docker
Écrit : `plant/opcua-sup/` (serveur OPC UA en lecture seule, miroir du gateway), `plant/fw-cell/` (nftables + relais socat), compose (gateway sur net_control seul, net_supervisory internal, collecteur sur opcua-sup), FUXA à deux appareils, FF-22 mis à jour (19 propriétés, 18 mutations), FF-31 (câblage, 8 propriétés, 9 mutations), FF-33 (opcua-sup en lecture seule : statique + vivant).
Mesuré ici (Python 3.10 hors Docker, asyncua 1.1.5) : miroir contre le vrai serveur du gateway : NodeIds i=6..12 conservés, horodatage source et statut copiés, écriture refusée pour tous les comptes, anonyme refusé ; gateway arrêté : statut BadNoCommunication en 7 s, valeur None, retour à Good en moins de 9 s après redémarrage. Jeu de règles nftables chargé dans un espace de noms réseau privé (unshare), sans trafic.
Pas mesuré : le relais fw-cell, les rejets nftables, le démarrage de la pile, FUXA à deux appareils, FF-26 à FF-28. L'attendu vient d'ADR-023 (même auteur) : à relire comme tel.
Reste décidé mais pas fait : canal sécurisé OPC UA (ADR-023 point 7), FF-32 et FF-34, relais hôte `supervisory-relay.ps1`.

## 15/11 FF-25 échoue après le passage du collecteur à `read_data_value(raise_on_bad_status=False)`
SYMPTÔME : `TypeError: Node.read_data_value() got an unexpected keyword argument 'raise_on_bad_status'` dans `scripts/ff25_alarm_persistence.py`, ligne 179 (faux nœud).
CAUSE : mon changement de `historian/collector.py`. Le vrai `Node.read_data_value` d'asyncua 1.1.5 accepte l'argument (vérifié contre le vrai serveur) ; le faux nœud de FF-25 n'a pas la même signature. C'est l'instrument qui diffère, pas le collecteur. Le changement lui-même vient d'un défaut constaté : sans lui, un statut Bad lève une exception, le collecteur boucle sur la reconnexion et l'historian montre un trou au lieu d'une ligne de qualité 0.
CORRECTION : le faux nœud prend `raise_on_bad_status=True` comme le vrai.

## 16/11/2026 - FF-26, FF-28 and validate-4e.ps1 reworked for ADR-023 (not run)
- Why: the collector no longer has a route to the gateway (gateway is on net_control only). FF-26 and FF-28 opened OPC UA to gateway:4840 and would fail with a connection error.
- Change: FF-26 reads measurements from opcua-sup (account historian) and writes START/STOP/Fault* through fw-cell:4840 (account engineer). FF-28 faults-off writes through fw-cell. validate-4e.ps1 builds fw-cell and opcua-sup, waits for their health, runs FF-31 and FF-33 locally.
- fw-cell accepts F9 from one source only (scada). The scripted run needs the collector to play the operator, so docker-compose.ff26.yml sets FW_F9_SOURCE=collector for the run and validate-4e.ps1 restores the design afterwards. While the override is up FUXA cannot command the belt.
- Not measured: none of this has run in Docker. Syntax checked only. FF-27 is unchanged (runs inside the gateway, 127.0.0.1).

## 16/11/2026 - first Docker run: fw-cell restarts in a loop (relay "exited")
- Symptom: `docker logs vigilimen-fw-cell` repeats "relay :4840 -> gateway:4840 ... relay exited" about every 5 s; `docker compose ps` shows fw-cell "health: starting"; opcua-sup logs ConnectionError / ConnectionRefused / gaierror (fw-cell is not up long enough). The nft table loaded (counters printed), so the firewall part works.
- Cause (strong suspicion, confirmed only if the fix works): the supervision loop used `kill -0 $RELAY`. With cap_drop ALL the entrypoint has no CAP_KILL and the relay runs as `nobody`, so kill -0 returns EPERM although socat is alive; the loop ends and the container exits.
- Fix: loop on `[ -d /proc/$RELAY ]` instead. Needs `docker compose build fw-cell`.
- Earlier the same run: `docker compose up -d` failed with "network net_supervisory has active endpoints" because the network became internal while the old gateway still held it; cure was `docker compose down` then `up -d` (volumes kept).

## 16/11/2026 - fw-cell allow-set refresh dropped the allowed source
- Symptom: after the /proc fix fw-cell stays up, but counters show FW-CELL-001=1 and FW-CELL-DEFAULT_drops=1 with dropped source 172.20.0.5 = opcua-sup, the one source meant to be allowed.
- Cause: `fill` did `nft flush set` then `nft add element` as two commands every 5 s; a packet arriving between them meets an empty set and falls to the default drop.
- Fix: one `nft -f -` transaction with flush + add. Not yet run.
- Open: opcua-sup still logs `gaierror` (name resolution) while fw-cell is healthy. Cause not known; diagnostics requested before any change.

## 16/11/2026 - FF-33 inside the collector container: FileNotFoundError
- Symptom: `docker exec vigilimen-collector python /tmp/ff33.py --url ...` ends with FileNotFoundError '/plant/opcua-sup/opcua_sup.py'.
- Cause: FF-33 always ran its static part first, and that reads the source file, which is not in the container. My own command skipped nothing; the script had no live-only mode.
- Fix: new flag `--live-only` (needs --url). Static part stays on the laptop (it passes there).
- Same run, positive: after the two fw-cell fixes all 8 services healthy, FW-CELL-001=1, drops=0, opcua-sup log quiet; the gaierror lines were from the moment fw-cell was restarting (fw-cell resolves to 172.20.0.4 from opcua-sup).

## 16/11/2026 - first Docker run of the ADR-023 stack: results (validate-4e, log 4e-20261116-121726.log)
- Measured, passed: 8 services healthy; fw-cell stable after two fixes (/proc supervision, atomic set refresh); FF-33 live (anonymous refused, 10 nodes, read works, write refused on every node for historian and scada); historian newest row 1.08 s old via collector -> opcua-sup -> fw-cell -> gateway; FF-26 7/7 (START 0.8 s; Spike +8 to alarm_event row 1.12 s, stamped +0.32 s; Clear all faults UNACK -> RTN_UNACK).
- Instrument caveat: FF-26 ran with docker-compose.ff26.yml, so F9 source = collector, not scada. It proves the command path through fw-cell works; it does not prove FUXA can use it (step 8, by hand, not done yet).
- Not proven: that fw-cell drops a source that is not allowed (FF-32 not written). The F9 counter value after FF-26 was not captured: `up -d` at the end recreated fw-cell and reset the counters.
- Still open: OPC UA runs with a plain-text password (ADR-023 point 7); FF-27/FF-28 not run against the new stack.

## 16/11/2026 - FUXA has no OPC UA type: devices show "internal", log "Unsupported protocol opc.tcp:"
- Symptom: after importing the project, both devices show Type "internal"; the Type dropdown offers only WebAPI, MQTTclient, internal; docker logs vigilimen-scada repeats `'CONV-001 (read)' _readRequest error! AxiosError: Unsupported protocol opc.tcp:` every 3 s (FUXA treats the device as a web API).
- Cause: the stock FUXA image does not contain the OPC UA driver. Plugins page: OPCUA node-opcua 2.149.0, Installed "-"; only node-red installed. FUXA installs drivers from the Internet at runtime. It worked in Sprint 4 because net_supervisory had a route; since ADR-023 the network is internal, and `docker compose down` deleted the container and the runtime install.
- Wrong turn on the way: I read the container creation time as the image build time and suspected a moving `latest`. The image is 3 weeks old and unchanged. The instrument was my own reading of `docker inspect`.
- Fix: plant/scada/Dockerfile = FUXA pinned by digest + `npm install node-opcua@2.149.0` at build time, with a build-time check; compose builds it. Not yet built or run.

## 16/11/2026 - 4e passes on the ADR-023 stack, including FUXA (by hand)
- Measured: FUXA (image rebuilt with node-opcua 2.149.0) connects both devices with scada and engineer credentials; no ERR in `docker logs vigilimen-scada --since 2m`; page values live (belt 2.5 m/s, load 602.9 t/h); START -> Running green; Spike +8 -> vibration 10.059 mm/s, lamp red; Clear all faults -> alarm_event rows 65/66 HI and HI_HI UNACK -> RTN_UNACK at 04:18:44 UTC.
- alarm_event 63..66 (UTC): 63 HI_HI RTN_UNACK->UNACK 04:18:00; 64 HI NORMAL->UNACK 04:18:31; 65, 66 RTN_UNACK 04:18:44. HI follows HI_HI by 31 s because engine.py sets on_delay_s=30 for Vibration HI and none for HI_HI; checked in the source, not measured separately.
- fw-cell counters: FW-CELL-002 = 92 new connections, almost all FUXA retries before the credentials were set; it stopped growing once connected. Not a count of commands. Live ruleset (`nft list ruleset`) matches entrypoint.sh.
- FF-32 live: not run yet (script written 16 Nov).
- Layout defect found on screen: "Clear all faults" button overlapped the R-14 footnote. Footnote moved to y=750 in build_project.py; JSON regenerated; needs a re-import to show.
- Not proven: that FUXA's command path is refused when the credentials are wrong (not tried); the 4e latency from a button press was not timed on screen.

## 16/11/2026 - ArchiMate model updated for ADR-023 (opened in Archi once, layout reworked)
- Model edited by script (lxml), not in Archi: new opcua-sup, its interface, fw-cell (device), net_dmz, requirement m09; readers re-pointed to opcua-sup (r05, r06, r08); r12 (gateway on net_supervisory) removed; F8/F9 flows, 12 new relations. Archi loaded the file without error (seen on screen).
- Symptom: first layout overlapped (fw-cell on "Operate the conveyor", opcua-sup on "Safe conveyor operation") and the association lines to the networks crossed everything. Cause: new boxes placed by guessed coordinates in free-looking spots without computing overlaps. Fix: Plant layers relaid out by layer with no network lines; new view "Network membership" carries networks and associations; box-overlap check added to the validation (no overlaps in the final layout, lines not checked).
- vigilimen-exchange.xml not regenerated (stale).

## 16/11/2026 - FF-32 passes; FF-27 fails with "PLC link up (PlcLinkOK)" (precondition, not yet a regression)
- Measured: FF-32 5/5 (drops 6 -> 9, probe 172.20.0.6 listed in dropped_sources). FF-27: FAIL PLC link up (PlcLinkOK) - its own message says to run validate-plcio.ps1 first.
- Suspected cause (not confirmed): validate-4e.ps1 sets VIGILIMEN_PLC_LINK=off in its own PowerShell process, and its final `docker compose up -d` runs in that same process, so the gateway was recreated in embedded mode (the header of that script says the containers stay embedded afterwards). Also the PLC program is lost if the PLC containers were recreated by `docker compose down`.
- Next: check `docker exec vigilimen-gateway env` for VIGILIMEN_PLC_LINK, then run validate-plcio.ps1 in a NEW PowerShell window.
- validate-plcio.ps1 reworked for ADR-023 (not run): builds fw-cell/opcua-sup/scada, local FF-31/FF-33, F9 source switched to the collector via docker-compose.ff26.yml for the FF-26 steps and restored at step 9.

## 16/11/2026 - validate-plcio step 5: FF-26 "PLC link up" failed once, then passed on a manual re-run
- Symptom: validate-plcio.ps1 step 5 stopped at `FAIL PLC link up (PlcLinkOK)` although the gateway log ended with "plc-link: linked to plc-control:502, read-back clean" and PLC_LINK=modbus. opcua-sup's log tail showed repeated "ConnectionError: Connection is closed" (no timestamps; it logs only on error, so the tail can be old).
- Measured afterwards (15:05-15:16 Brisbane): stack steady, opcua-sup silent and healthy, FF-26 alone passes 6/6 with the PLC in the loop (START 10.7 s, alarm row 0.93 s).
- Cause: NOT established. Suspicion: start-up order (gateway restarted, fw-cell recreated, PLC link still retrying). It does not fit FF-26's own 60 s wait for PlcLinkOK, so it may be wrong.
- Change: when FF-26 fails, validate-plcio.ps1 now prints the last 15 timestamped log lines of gateway, opcua-sup and fw-cell before stopping.

## 16/11/2026 - after-restart and clear phases failed: the PLC link dropped and the gateway stopped the belt
- Symptom: validate-plcio steps run by hand. FF-26 after-restart: "alarm_state holds the live alarm" FAIL, state RTN_UNACK in_condition False. FF-26 clear: "UNACK -> RTN_UNACK" FAIL. Plant at that moment: Running 0, speed 0, current 0, vibration 0, SafetyTripped 0.
- Evidence (UTC): alarm_event 101 HI_HI raised 05:13:03, 102 HI 05:13:34 (30 s on-delay), 103/104 both RTN_UNACK 05:14:16. Gateway log: "plc-link: lost the PLC (ConnectionResetError ... Connection reset by peer); no run request until it returns" at 05:14:15, one second before. Link history: linked 04:59:26, cannot connect 05:10:46, linked 05:12:47, lost 05:14:15. plc-control log shows "OpenPLC Runtime starting ... Persistent Storage is empty" (timestamps not collected).
- Cause: the operator pressed Start PLC in the OpenPLC page more than once (confirmed by the operator, not by runtime timestamps). Each start restarts the runtime and resets the gateway's Modbus connection; the gateway withdraws the run request (designed fail-safe), the belt stops, vibration reads 0, and the collector's speed gate ends the alarm. Not a fault of ADR-023, fw-cell or opcua-sup.
- Instrument note: FF-26 phases assume the PLC stays running between them; it does not check the link at each phase.
- Fix (test side, not yet written): FF-26 after-restart and clear should check PlcLinkOK and Running first and report "plant stopped / link lost" as the reason instead of a misleading alarm failure. Procedure: press Start PLC once, then leave the page alone until the run ends.

## 16/11/2026 - validate-plcio step 5 failed again: plc-control was not listening on Modbus port 502
- Symptom: second run of validate-plcio.ps1 (no clicks in the OpenPLC page): FF-26 "PLC link up (PlcLinkOK)" FAIL. Gateway log (UTC): restarted 06:58, 06:59:09 "plc-link: cannot connect to plc-control:502", no "linked" line in the next 7+ minutes. From the gateway container: ConnectionRefusedError on plc-control:502. /proc/net/tcp in plc-control: listeners on 8080, 8443 and 127.0.0.1:43628 (interactive server), none on 502 (hex 01F6).
- Evidence after Stop PLC, 5 s, Start PLC once: connection to plc-control:502 succeeds ("connected").
- Cause (consistent with the evidence, not proven): the runtime's Modbus listener was gone since the 05:14:15 link loss, after Start PLC had been pressed more than once, while the dashboard still said Running. The earlier "about two minutes after a gateway restart" idea was wrong: the link did not come back for 7+ minutes until Stop/Start. plc-control's runtime log is block-buffered (identical timestamps, nothing after 05:06:42), so it cannot show when the listener went away.
- Fix (test side): validate-plcio.ps1 now tests port 502 from the gateway after the PLC step and stops with an instruction (Stop PLC, 5 s, Start PLC once) if it does not answer; after the gateway restart it waits for the gateway's own "plc-link: linked" line up to 2 minutes instead of sleeping 12 s. FF-26 after-restart and clear now print the plant state (Running, PlcLinkOK, belt speed) in the failure detail. Not yet run.
- Observation, not investigated: asyncua prints "RuntimeError: Task cannot await on itself" (UaProcessor session watchdog) in the gateway and opcua-sup logs when sessions close during a restart.

## 16/11/2026 - validate-plcio.ps1 passes end to end on the ADR-023 stack (log plcio-20261116-171606.log)
- Result: the script ended with "PLC link, persistence and isolation all proven in Docker" after the port 502 check, the wait for "plc-link: linked", FF-26 alarm with the PLC in the loop, the collector restart in the middle of the alarm, the after-restart and clear phases, and the isolation proof. Step 9 restored the F9 source to scada.
- What the maintainer saw: the last lines only; the per-step output is in the log file. Not re-read by the assistant at the time of writing.
- Procedure that made it pass: press Start PLC once, leave the OpenPLC page alone; the script checks Modbus port 502 itself.
- Still open: FF-27 on the new stack; OPC UA secure channel (ADR-023 point 7); the cause of the lost Modbus listener is a suspicion (repeated Start PLC), not proven.

## 16/11/2026 - FF-27 passes on the ADR-023 stack with the real OpenPLC
- Result (seen in full): 13 checks, 0 failed. PLC link up; START to RUNNING 11.5 s; slip plus seized idler trips the PLC to FAULT in 1.6 s and the belt stops; START does not clear a FAULT; STOP with the belt stopped and the machine cool clears it; one forged Modbus frame (bearing 96.0 degC) trips the PLC in 0.21 s with no credential asked (the known Z1 lab concession, ADR-023).

## 16/11/2026 - OPC UA secure channel (ADR-023 point 7): spike errors and the build
- Symptom 1: first spike, an untrusted client certificate CONNECTED with Sign and Encrypt. Cause: the certificate validator was set as a plain attribute on Server, which asyncua never reads. Correction: server.set_certificate_validator(validator.validate).
- Symptom 2: after that, the TRUSTED client was refused too (BadCertificateUntrusted). Cause: the trust store was never loaded (await store.load()) and was given single files where it expects a folder of DER certificates. Correction: load it, pass the folder.
- Symptom 3: first run of FF-35 live, positive control failed with BadCertificateUriInvalid. Cause: Server.set_application_uri is a coroutine in asyncua 1.1.5 and was not awaited, so the server kept the default URI and the client's validation of the server certificate failed. Correction: await it.
- Symptom 4: FF-25 failed locally after the build (ModuleNotFoundError: uasec). Cause: collector.py now imports uasec and FF-25 imports collector.py outside the image. Correction: repo-path fallback in collector.py, as in the gateway and opcua-sup.
- Symptom 5: `--live-only` without `--url` printed "FF-35 pass" with nothing run. Cause: the local live branch was skipped when live-only was set. Correction: without a URL, live means the local live run.
- Built: plant/pki/uasec.py, pki-init service and `pki` volume (one folder per service via volume subpath), servers/clients/health checks moved to Sign and Encrypt, FF-35 (static with 7 mutations, live local and in Docker), FF-22 updated (nine services, pki-init network_mode none and nothing else), FF-26/27/28/33 moved to secure clients (FF-26/28 use a `tester` certificate that exists only under docker-compose.ff26.yml).
- Proven (local, no Docker): FF-35 static 15/15 and 7/7 mutations caught; FF-35 live against the real gateway and opcua-sup servers with a generated PKI; FF-33 live against a secured opcua-sup; FF-03, FF-07, 21, 22, 23, 24, 25, 31, 33 pass. One refusal (client pinned to the wrong server) appears as TimeoutError: the server drops a channel encrypted to the wrong certificate; the positive control in the same run shows the server and network are fine.
- NOT proven: anything in Docker (pki-init, volume subpath, compose `depends_on` on a completed one-shot, health checks with certificates, fw-cell relay of the secure channel, FF-26/27/28 with the new clients). FUXA is NOT moved: its OPC UA driver must present a certificate and pin the server's; whether it can is unchecked, so FUXA will not connect to the secured servers yet.

## 16/11/2026 - FUXA and the secure channel: decision A (temporary workaround)
- Measured (scripts/fuxa_client_probe.js in the scada container): node-opcua reads its client certificate from /root/.config/node-opcua-default-nodejs/PKI/own/certs/client_certificate.pem and the key from own/private/private_key.pem; autoAcceptUnknown is true. FUXA's driver (server/runtime/devices/opcua/index.js lines 35-36) passes only securityMode and securityPolicy.
- The probe's first run failed with "Cannot find an Endpoint matching security mode 3 Basic256Sha256" because the stack running at the time was the OLD one (opcua-sup logs had no `uasec:` line). It said nothing about FUXA. Lesson: check what the server is serving before reading a client failure.
- Decision (maintainer, A): the scada image links FUXA's default certificate folder to the `scada` certificate from pki-init. One identity for FUXA, trusted by both servers; the certificate also carries the URI urn:scada:NodeOPCUA-Client in case FUXA announces its default name. Limit recorded in ADR-023: FUXA accepts any server certificate. Temporary; the real fix is another SCADA.
- Not yet proven in Docker: that FUXA's node-opcua accepts the linked files and that the servers accept its URI. FUXA's Security mode and policy (SignAndEncrypt, Basic256Sha256) must be set by hand on both devices, with the credentials (ADR-018).
- Also: PyYAML keeps the last of two duplicate keys silently, so FF-22 passed a compose file that Docker refused ("mapping key volumes already defined"). FF-22 now fails on a duplicate key (proved by putting the bug back).

## 16/11/2026 - validate-4e step 2: gateway build failed, '"/secure": not found'
- Symptom: `docker compose build` stopped at gateway 7/7: `COPY pki/uasec.py /opt/vigilimen/gateway/uasec.py     # OPC UA secure channel (ADR-023 point 7)` -> failed to calculate checksum ... "/secure": not found. The other images (collector, opcua-sup) built their COPY of uasec.py fine.
- Cause: in a Dockerfile `#` starts a comment only at the beginning of a line. After an instruction it is part of the arguments, so "OPC", "UA", "secure"... were read as more source files. My mistake; the local tests do not build images.
- Fix: the comment is on its own line above the COPY. Checked every Dockerfile for an instruction line with a trailing `#`.

## 16/11/2026 - validate-4e FF-26: BadUserAccessDenied on a write once the secure channel was on
- Symptom: FF-26 (collector container, `tester` certificate, account engineer) stopped at the first write (a Fault* tag) with BadUserAccessDenied. The secure sessions themselves opened fine. The transcript of validate-4e.ps1 had no docker output at all (PowerShell's transcript does not record native-command output), so the output was fetched by running FF-26 by hand.
- Reproduced locally: secured gateway, engineer writes StartCommand, FaultBeltSlip -> refused; node AccessLevel 3 and UserAccessLevel 3. The SAME write on the previous unsecured gateway (git HEAD) worked. So the secure channel changed authorisation.
- Cause: asyncua attaches its default permission ruleset (SimpleRoleRuleset: only Admin may write, User may only read) to every SECURED security policy and to none for NoSecurity. Both gateway accounts hold UserRole.User (ADR-017), so enabling the secure channel made every write by every account refuse. FF-33/FF-35 (reads, refusals) could not see it; FF-26 did because it needs a permitted write to work.
- Fix: uasec.py passes its own ruleset (_PerNodeRuleset): refuses anonymous only. Authorisation stays per node, as in ADR-017: the node's access level decides, and asyncua's address space still allows only Admin to add/delete nodes. FF-35 now checks (gateway, `--writable`) that a permitted write works and a measurement write is refused, plus a static check and mutation. Proved: with the fix removed, the live check fails; with it, FF-35 passes.
- validate-4e.ps1 now writes docker output into its transcript (ForEach-Object { Write-Host $_ }) for FF-35, FF-26, the log tail and the alarm rows.
- Lesson: FF-33 and FF-35 only prove refusals and a read; FF-26 is the one that proves a permitted write, so a change to the channel needs FF-26 before it counts.

## 16/11/2026 - FUXA with the linked certificate: the probe opens a session
- Symptom (first probe on the secured stack): channel opened, then `BadCertificateUntrusted` at createSession. Cause: the running scada container was the OLD image (built before the Dockerfile links existed): validate-4e.ps1 did not build `scada`, so node-opcua generated its own certificate. Fix: `docker compose build scada` + `up -d scada`; validate-4e.ps1 now builds scada.
- Result after the rebuild (scripts/fuxa_client_probe.js, node-opcua 2.149.0 in the scada container, read endpoint opcua-sup): "SESSION OPENED as scada". The certificate is the one pki-init issued, presented over Basic256Sha256 Sign and Encrypt; autoAcceptUnknown is still true (FUXA does not pin the server).
- Still by hand and not yet seen: FUXA's own UI path (import, credentials and security on both devices, START, spike, Clear) and the command device through fw-cell.

## 16/11/2026 - FUXA by hand on the secured stack (ADR-023 point 7, decision A): works
- Seen by the maintainer on the HMI (three screenshots): both connections green after the credentials and Sign & Encrypt / Basic256Sha256 were set on CONV-001 (read) and CONV-001 (command). START: Running green, belt 2.5 m/s, StartCommand 1. Spike vibration +8: vibration 9.864 mm/s, lamp red. Clear all faults: vibration 1.864, lamp grey. STOP: belt speed, current and load 0, StopCommand 1.
- Path proven by that run: reads FUXA -> opcua-sup (read-only), commands FUXA -> fw-cell (F9, source scada) -> gateway, all over Basic256Sha256 Sign and Encrypt with the certificate linked in the scada image.
- Before this the connections showed red for a short while after a relay restart; they turned green on their own. Not investigated further (the relay holds the old container address until it is restarted: supervisory-relay.ps1 must be re-run whenever scada, historian or opcua-sup is recreated).
- Cosmetic, open: the 'Clear all faults' button overlaps the footnote because the HMI imported earlier has the old layout (the project file in git has the footnote at y=750). Re-import once at the very end; it resets the credentials and security fields (ADR-018).
- Not yet run: validate-plcio.ps1 on the secured stack (PLC in the loop, persistence, isolation) and FF-27/FF-28 with the new clients.

## 17/11/2026 - validate-plcio, FF-27, FF-28 on the secured stack (ADR-023 point 7): all pass
- Seen (logs plcio-20261117-144300, trips-20261117-155125, durability-20261117-155404, no FAIL in any): validate-plcio steps 1-9 PASS (FF-26 with the PLC in the loop 6/6, restart in the middle of an alarm = one raise, Clear + append-only, isolation 7/7); FF-27 13/13; FF-28 tamper, shelve, after-restart, expiry and FF-26 clear all PASS. FUXA links in the scada container point to /pki/identities/scada.pem and scada-key.pem. fw-cell counters after START: FW-CELL-001=1, FW-CELL-002=2, drops 0.
- Symptom (predicted from reading, not seen as a failure): validate-durability.ps1 had not been updated for ADR-023. It started the stack with docker-compose.yml only, so there was no `tester` certificate and F9 stayed on scada; FF-26 and FF-28 command through fw-cell and would have been refused.
- Cause: the ADR-023 lot changed validate-plcio.ps1 and validate-4e.ps1 (docker-compose.ff26.yml) but not this script.
- Fix: validate-durability.ps1 now builds and starts with `-f docker-compose.yml -f docker-compose.ff26.yml` (same $composeTest as validate-plcio). The corrected script ran green. Not tested: -Extended (A, B, C).
- Not in these scripts: FF-27/FF-28 are not part of validate-plcio.ps1; they run on their own (validate-trips.ps1, validate-durability.ps1). validate-durability leaves the stack in embedded mode with F9 = collector; return with `docker compose up -d --build` in a new window, then re-run supervisory-relay.ps1.
- Open, not investigated: gateway logs one 'lost the PLC (Connection reset)' then relinks when the PLC is started; FF-26 after-restart header prints link=off although the same test reads PlcLinkOK=True.

## 17/11/2026 - CI: FF-01 fails, threat-model-v1.md is 125 lines (limit 115)
- Symptom: the CI step `bash scripts/ff01_doc_cut_line.sh` fails: `docs/architecture/threat-model-v1.md 125 lines (+10 over)`. Reproduced locally (exit 1) before any change.
- Cause: commit ed76f9c (30 Oct, ADR-023 proposal) appended a 17-line "Update 30 Oct 2026, TB-1a" section to a file that was already near the cap. FF-01 was not run on that commit locally; the Docker validations do not run it.
- Fix: the section moved unchanged (heading level only) to `docs/architecture/threat-model-tb1a.md`; `threat-model-v1.md` keeps a one-line pointer (112 lines). FF-01 passes locally. Limit NOT raised (that needs an ADR).
- Limit of this fix: the new file is not in FF-01's GOVERNED list (a directory entry would be needed), so it is not under the cut line. Adding it is a choice for the maintainer.
- To confirm: the next CI run on GitHub after the push (not seen yet).

## 18/11/2026 - S5: Docker publish spike passed; edge moves to net_edgelink; FF-22 extended for topology B

- Spike (user, PowerShell): a container on `spike-hostleg` (non-internal) plus `spike-dmz` (internal) publishes on `127.0.0.1:18884` (host got HTTP 200); a container on the internal net reaches it (200) and gets "Network is unreachable" for 1.1.1.1. Topology B holds. The first attempt failed only because Docker Desktop was not running.
- Design correction: an edge on `net_supervisory` would reach scada, historian and collector (Docker: same network = every port). New internal `net_edgelink` holds `opcua-sup` and the edge only. `opcua-sup` becomes multi-homed. No filtering firewall between DMZ and supervisory in the lab (production target in `hardening-targets.md`).
- `plant/docker-compose.yml`: `net_edgelink` added, `opcua-sup` on {net_supervisory, net_edgelink}. NOT yet run in Docker: needs `docker compose up -d --build` then validate-plcio, FF-27, FF-28, FF-32, FF-35 to confirm opcua-sup still serves the collector, SCADA and fw-cell F8 when multi-homed.
- `scripts/ff22_compose_topology.py`: 23 properties on the real compose, plus an S5 target compose built from the design (31 properties hold), 44 mutations all caught. Edge and broker properties run on the target until the real services exist. Not tested: ip_forward on the real edge (set and checked in the compose only).

## 18/11/2026 - S5: net_edgelink compose change validated in Docker
- Measured, passed (opcua-sup on net_supervisory + net_edgelink): validate-plcio steps 1-9 PASS incl. FF-26 6/6, 2/2, 2/2 and isolation 7/7 (log plcio-20261118-182446); FF-27 13/13; FF-28 passed (log durability-20261118-184341); FF-32 5/5 (drops 8 -> 11, probe 172.20.0.6 listed); validate-4e automated part passed (log 4e-20261118-185229): FF-35 7/7 on opcua-sup and 9/9 on the gateway, FF-26 7/7 in embedded mode, all services healthy.
- Not proven: FF-33 live (write refused on every node) was not shown in this output; its local static part runs in validate-4e before the stack step (it stops on failure). Edge and broker are not built yet, so net_edgelink carries only opcua-sup for now. FUXA step 8 by hand not done.
- Open, not investigated: FF-26 after-restart header prints link=off while PlcLinkOK=True; certificate warning "hostname not in DNSNames" (collector, gateway).

## 18/11/2026 - S5: MQTT lab CA written (plant/pki/mqttpki.py) and FF-36 static part
- Written: `plant/pki/mqttpki.py` (CA EC P-256, path length 0; broker server certificate, edge and consumer client certificates, `edge-old` only with --tester and revoked by the CRL; SAN carries the host names; CN = identity = ACL key). `scripts/ff36_mqtt_pki.py`: baseline checks + 16 mutations.
- Run in the authoring container (Python 3.13, cryptography 50.0.1, openssl present): baseline all PASS, 16 of 16 mutations caught. NOT run on the Windows machine, NOT run in Docker.
- Not done: pki-init does not call mqttpki yet, no `pki-mqtt` volume in compose, no broker. The broker uid 1883 in UIDS is to confirm when the Mosquitto image is chosen. CRL is 30 days and nobody republishes it (lab). Whether Mosquitto re-reads the CRL without a restart is unverified: that is the live part of FF-36, still to write.

## 18/11/2026 - S5: pki-init wired for the MQTT CA, broker configuration written (FF-37 static)
- Changed: `plant/pki/Dockerfile` (copies mqttpki.py; CMD runs uasec.py init /pki then mqttpki.py init /pki-mqtt), `plant/docker-compose.yml` (volume `pki-mqtt`, mounted in pki-init only). Service count unchanged (no new service). FF-22, FF-03, FF-05 pass locally after the change. NOT run in Docker.
- Written: `plant/broker/mosquitto.conf` (one listener 8883, mutual TLS, identity from the CN, CRL, limits, no retained, no 1883) and `plant/broker/acl` (edge write only, consumer read only, topics under vigilimen/v1/). `scripts/ff37_broker_config.py`: 25 checks and 26 mutations, all caught, run in the authoring container and on the project machine.
- Not done / not proven: no broker service in the compose, so nothing was run against Mosquitto. FF-22 requires the S5 services together ({edge, broker}), so adding the broker alone needs a deliberate FF-22 change. Unverified: that tls_version unset gives TLS 1.2 and 1.3 only on the pinned image; that an edge with a write-only ACL cannot subscribe; that Mosquitto refuses a revoked certificate and whether it re-reads the CRL without a restart; broker uid 1883 for the key files.
