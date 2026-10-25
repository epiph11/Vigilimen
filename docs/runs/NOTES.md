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
