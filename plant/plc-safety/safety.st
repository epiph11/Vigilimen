(*
    SIS-CONV-001 — safety function for conveyor CONV-001
    MineDigital · Sprint 3 · runs on OpenPLC, separate runtime, separate zone

    ─────────────────────────────────────────────────────────────────────
    THIS PROGRAM TAKES NO INPUT FROM THE CONTROL FUNCTION.

    There is no tag, no network path and no shared memory between this
    program and PLC-CONV-001. That is not a convention to be respected —
    it is enforced by the two running on separate runtimes, on separate
    zones, with separate I/O.

    Its output drops the motor contactor coil through a safety relay,
    wired in SERIES with the control PLC's motor output. The control
    function can stop the belt by dropping its own output. It cannot
    start the belt against this one, and it has no means of inhibiting,
    bypassing, delaying or acknowledging a trip.

    That asymmetry is the design. TRITON is why.
    ─────────────────────────────────────────────────────────────────────

    CONVENTION: TRUE = healthy / not demanded, on every input.
    De-energise to trip. A broken wire reads FALSE, which is a demand.
    Loss of power, loss of wire and a real demand all produce the same
    outcome — a trip mechanism that needs power to trip has a failure
    mode indistinguishable from normal operation.

    Reference model: plant/sim/interlock_model.py
    Verified by:     scripts/ff06_safety_independence.py  (13 cases)
    Settled by:      a witnessed test, and nothing else
*)

PROGRAM SIS_CONV_001
VAR_INPUT
    (* Dual-channel field devices. Two wires, two terminals, two reads. *)
    EStop_ChA       : BOOL;   (* %IX0.0  emergency stop, channel A     *)
    EStop_ChB       : BOOL;   (* %IX0.1  emergency stop, channel B     *)
    PullCord_ChA    : BOOL;   (* %IX0.2  belt pull-cord, channel A     *)
    PullCord_ChB    : BOOL;   (* %IX0.3  belt pull-cord, channel B     *)
    BeltDrift_OK    : BOOL;   (* %IX0.4  belt drift switch             *)
    Guard_Closed    : BOOL;   (* %IX0.5  guard position                *)
    Safety_Reset    : BOOL;   (* %IX0.6  MANUAL reset, at the panel    *)
END_VAR

VAR_OUTPUT
    Contactor_Coil  : BOOL;   (* %QX0.0  TRUE energises. Hardwired.    *)
    Trip_Latched    : BOOL;   (* %QX0.1  lamp at the panel             *)
    Device_Fault    : BOOL;   (* %QX0.2  discrepancy detected          *)
END_VAR

VAR
    (* Boots TRIPPED. A cold start is not a safe start: a controller that
       powers up permissive has decided the plant is safe without having
       looked at it. *)
    Tripped         : BOOL := TRUE;

    EStop_Demand    : BOOL;
    Cord_Demand     : BOOL;
    EStop_Discrep   : BOOL;
    Cord_Discrep    : BOOL;
    Discrep_Timer   : TON;
    Reset_Edge      : R_TRIG;
END_VAR


(* ── 1. Dual-channel evaluation ─────────────────────────────────────── *)

EStop_Demand  := NOT (EStop_ChA AND EStop_ChB);
Cord_Demand   := NOT (PullCord_ChA AND PullCord_ChB);

(* A discrepancy is a FAULT, not a vote.

   One channel healthy and one not means a broken wire or a welded
   contact. Either way the device can no longer be trusted to demand a
   stop WHEN IT IS NEEDED — which is a different and far worse failure
   than a spurious trip, because it is silent. *)

EStop_Discrep := EStop_ChA <> EStop_ChB;
Cord_Discrep  := PullCord_ChA <> PullCord_ChB;

Discrep_Timer(IN := (EStop_Discrep OR Cord_Discrep), PT := T#500ms);
Device_Fault  := Discrep_Timer.Q;


(* ── 2. Trip conditions ─────────────────────────────────────────────── *)

IF EStop_Demand
   OR Cord_Demand
   OR NOT BeltDrift_OK
   OR NOT Guard_Closed
   OR Device_Fault
THEN
    Tripped := TRUE;
END_IF;


(* ── 3. Reset ───────────────────────────────────────────────────────── *)

(* The trip LATCHES. Clearing the demand does not restart the belt:
   somebody pressed that stop and may now be standing at the machine.
   Reset is a rising edge at a physical panel button, not a level, and
   not a network write. *)

Reset_Edge(CLK := Safety_Reset);

IF Reset_Edge.Q
   AND NOT EStop_Demand
   AND NOT Cord_Demand
   AND BeltDrift_OK
   AND Guard_Closed
   AND NOT Device_Fault
THEN
    Tripped := FALSE;
END_IF;


(* ── 4. Output ──────────────────────────────────────────────────────── *)

Contactor_Coil := NOT Tripped;
Trip_Latched   := Tripped;

(*
    WHAT IS DELIBERATELY ABSENT, AND WHY

    No bearing temperature. No motor current. No vibration. No overload.

    Those are MACHINE protection and they live in PLC-CONV-001. Loading
    this program with them would add demands that have nothing to do with
    anyone's safety, and every added demand is another way for this
    function to trip spuriously — which is how a safety function ends up
    bypassed by people who need the plant to run.

    A safety function that trips for reasons operations do not respect
    will eventually be defeated, and then it protects nobody. Keeping it
    narrow is not minimalism. It is what keeps it trusted.

    No network input of any kind. No remote reset. No SCADA write.
    No "maintenance mode" bit. No bypass, timed or otherwise.
*)

END_PROGRAM
