// Drives the C that MatIEC generates from safety_upload.st with the vectors the Python model produced.
//
//   g++ ... safety_replay.cpp -o replay ;  ./replay < vectors.csv      (POUS.c is #included below)
//
// Only the PROGRAM is run: no OpenPLC runtime, no Modbus, no network. The timer (TON) and the
// rising-edge block (R_TRIG) are the real ones from OpenPLC's lib. Each scenario starts from a fresh
// init, as a cold start does.
//
// Output, one line per scan:
//   scenario,step,model_c,model_t,spec_c,spec_t,st_c,st_t,vs_model,vs_spec,edge_q,edge_m,estop_demand,clk,m_before,q_before
// vs_model / vs_spec are 1 when the program agrees. The model is NOT the authority: the SPEC (ADR-011)
// is, and the vectors carry both. A program that matches the model but not the spec is the worse case.
// Exit status 1 if any scan disagrees. A disagreement is a FINDING: either the model or the program is
// wrong, and this does not say which.
//
// RULES THAT MATTER IN THIS FILE
//  * POUS.h goes FIRST and no C++ standard header may come before it: <iostream>, <string> and <vector>
//    pull in <time.h>, whose `struct tm` clashes with the `tm` typedef in OpenPLC's iec_std_lib.h.
//    Plain C headers only, and after POUS.h.
//  * The include path must list the GENERATED directory before OpenPLC's core/, or "POUS.h" resolves to
//    the one left there by the last real compile (a different program).
#include "POUS.h"
#include "POUS.c"   // generated, and has NO includes of its own: OpenPLC builds it by #including it

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

TIME __CURRENT_TIME;   // the timer blocks read this global; the PLC runtime normally advances it

int main() {
  char line[512], current[128] = "";
  // STATIC, and zeroed before every cold start. The generated variables carry a `flags` byte next to
  // `value`, and OpenPLC's accessor macros consult it (a FORCE bit makes __GET_VAR return a forced
  // value and makes __SET_VAR skip the write). The PLC runtime keeps its instances in static storage,
  // i.e. zeroed. A local `SIS_CONV_001 inst;` holds whatever the stack held, so the program behaved
  // differently depending on unrelated code around it. See docs/runs/NOTES.md, 00:45 on 26 Oct.
  static SIS_CONV_001 inst;
  long long now_ns = 0;
  int total = 0, mism_model = 0, mism_spec = 0;

  // Library self-test, independent of safety.st: an R_TRIG fed CLK=1 on two consecutive scans must
  // give Q=1 then Q=0, and its memory M must be 1 after the first call. If it does not, the edge
  // detector as compiled here does not latch, whatever any program built on it says.
  {
    static R_TRIG t;
    memset(&t, 0, sizeof t);
    R_TRIG_init__(&t, 0);
    t.CLK.value = 1;
    R_TRIG_body__(&t);
    int q1 = t.Q.value ? 1 : 0, m1 = t.M.value ? 1 : 0;
    R_TRIG_body__(&t);
    int q2 = t.Q.value ? 1 : 0, m2 = t.M.value ? 1 : 0;
    printf("SELFTEST r_trig clk=1,1: q1=%d m1=%d q2=%d m2=%d (a working edge detector gives 1 1 0 1)\n", q1, m1, q2, m2);
  }

  if (!fgets(line, sizeof line, stdin)) return 2;  // header
  printf("scenario,step,model_c,model_t,spec_c,spec_t,st_c,st_t,vs_model,vs_spec,edge_q,edge_m,estop_demand,clk,m_before,q_before\n");

  while (fgets(line, sizeof line, stdin)) {
    char name[128];
    int step, dt, ea, eb, ca, cb, dr, gd, rs, mc, mt, pc, pt;
    if (sscanf(line, "%127[^,],%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",
               name, &step, &dt, &ea, &eb, &ca, &cb, &dr, &gd, &rs, &mc, &mt, &pc, &pt) != 14) continue;

    if (strcmp(name, current) != 0) {   // new scenario: cold start
      strcpy(current, name);
      memset(&inst, 0, sizeof inst);
      SIS_CONV_001_init__(&inst, 0);
      now_ns = 0;
    }
    now_ns += (long long)dt * 1000000LL;
    __CURRENT_TIME.tv_sec = now_ns / 1000000000LL;
    __CURRENT_TIME.tv_nsec = now_ns % 1000000000LL;

    inst.ESTOP_CHA.value = ea;
    inst.ESTOP_CHB.value = eb;
    inst.PULLCORD_CHA.value = ca;
    inst.PULLCORD_CHB.value = cb;
    inst.BELTDRIFT_OK.value = dr;
    inst.GUARD_CLOSED.value = gd;
    inst.SAFETY_RESET.value = rs;

    int m_before = inst.RESET_EDGE.M.value ? 1 : 0, q_before = inst.RESET_EDGE.Q.value ? 1 : 0;
    SIS_CONV_001_body__(&inst);

    int sc = inst.CONTACTOR_COIL.value ? 1 : 0, st = inst.TRIPPED.value ? 1 : 0;
    int ok_model = (mc == sc) && (mt == st);
    int ok_spec = (pc == sc) && (pt == st);
    total++;
    if (!ok_model) mism_model++;
    if (!ok_spec) mism_spec++;
    // Diagnostic columns: what the edge detector and the demand actually held on this scan.
    printf("%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n", name, step, mc, mt, pc, pt, sc, st, ok_model, ok_spec,
           inst.RESET_EDGE.Q.value ? 1 : 0, inst.RESET_EDGE.M.value ? 1 : 0,
           inst.ESTOP_DEMAND.value ? 1 : 0, inst.RESET_EDGE.CLK.value ? 1 : 0, m_before, q_before);
  }
  printf("SUMMARY %d scans, %d differ from the MODEL, %d differ from the SPEC (ADR-011)\n", total, mism_model, mism_spec);
  return (mism_model || mism_spec) ? 1 : 0;
}
