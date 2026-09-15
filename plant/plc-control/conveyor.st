(*
    PLC-CONV-001 — control function for conveyor CONV-001
    MineDigital360 · Sprint 3 · OpenPLC · Purdue Level 1, control zone

    This program sequences and protects the MACHINE. It does not protect
    people — SIS-CONV-001 does that, on a separate runtime, in a separate
    zone, with its own I/O, and this program has no path to it.

    Motor_Run below is a REQUEST. It is wired in series with the safety
    relay's contactor output, so:

        motor turns  =  safety contactor energised  AND  Motor_Run

    This program can stop the belt. It cannot start it against a trip.

    Reference model: plant/sim/interlock_model.py
*)

PROGRAM PLC_CONV_001
VAR_INPUT
    Start_PB        : BOOL;    (* %IX1.0  start, local or SCADA          *)
    Stop_PB         : BOOL;    (* %IX1.1  normal stop                    *)
    Zero_Speed      : BOOL;    (* %IX1.2  TRUE when belt is stationary   *)
    Upstream_Ready  : BOOL;    (* %IX1.3  crusher permissive             *)
    Downstream_Ready: BOOL;    (* %IX1.4  stockpile permissive           *)

    Bearing_Temp    : REAL;    (* %IW10   drive-end bearing, degC        *)
    Motor_Current   : REAL;    (* %IW11   amps                           *)
    Belt_Speed      : REAL;    (* %IW12   m/s                            *)
END_VAR

VAR_OUTPUT
    Motor_Run       : BOOL;    (* %QX1.0  RUN REQUEST — in series with SIS *)
    Alarm_Horn      : BOOL;    (* %QX1.1  pre-start warning              *)
    Alarm_Word      : WORD;    (* %QW20   to SCADA                       *)
END_VAR

VAR
    State           : INT := 0;  (* 0 stopped 1 warning 2 starting 3 running 4 stopping 5 fault *)
    Warn_Timer      : TON;
    Start_Timer     : TON;
    Start_Edge      : R_TRIG;

    Permissives_OK  : BOOL;
END_VAR

VAR CONSTANT
    BEARING_ALARM   : REAL := 85.0;
    BEARING_TRIP    : REAL := 95.0;
    OVERLOAD_TRIP   : REAL := 42.0;
    WARN_TIME       : TIME := T#10s;
    START_TIMEOUT   : TIME := T#15s;
END_VAR


(* ── Permissives ────────────────────────────────────────────────────── *)

Permissives_OK := Upstream_Ready AND Downstream_Ready;


(* ── Machine protection ─────────────────────────────────────────────── *)

(* Alarms advise. Trips act. Both belong HERE and not in the safety
   function: they protect the conveyor, not a person, and a safety
   function loaded with machine protection trips more often for reasons
   operations do not respect. *)

Alarm_Word.0 := Bearing_Temp >= BEARING_ALARM;
Alarm_Word.1 := Motor_Current >= (OVERLOAD_TRIP * 0.9);
Alarm_Word.2 := NOT Permissives_OK;

IF Bearing_Temp >= BEARING_TRIP OR Motor_Current >= OVERLOAD_TRIP THEN
    State := 5;
END_IF;


(* ── Sequence ───────────────────────────────────────────────────────── *)

Start_Edge(CLK := Start_PB);

CASE State OF

0:  (* STOPPED *)
    Motor_Run  := FALSE;
    Alarm_Horn := FALSE;
    IF Start_Edge.Q AND Permissives_OK THEN
        State := 1;
    END_IF;

1:  (* PRE-START WARNING — the horn sounds before anything moves.
       A conveyor that starts silently is a conveyor someone is standing
       on. This delay is not politeness; it is the reason the belt is
       clear when it moves. *)
    Motor_Run  := FALSE;
    Alarm_Horn := TRUE;
    Warn_Timer(IN := TRUE, PT := WARN_TIME);
    IF Stop_PB THEN
        Warn_Timer(IN := FALSE);
        State := 0;
    ELSIF Warn_Timer.Q THEN
        Warn_Timer(IN := FALSE);
        State := 2;
    END_IF;

2:  (* STARTING — waiting for the belt to move *)
    Motor_Run  := TRUE;
    Alarm_Horn := FALSE;
    Start_Timer(IN := TRUE, PT := START_TIMEOUT);
    IF NOT Zero_Speed THEN
        Start_Timer(IN := FALSE);
        State := 3;
    ELSIF Start_Timer.Q THEN
        (* Commanded to run and did not move. Either the belt is stalled,
           or the SAFETY CONTACTOR IS OPEN — this program cannot tell the
           difference, and deliberately does not try. It stops asking. *)
        Start_Timer(IN := FALSE);
        Alarm_Word.3 := TRUE;
        State := 5;
    END_IF;

3:  (* RUNNING *)
    Motor_Run := TRUE;
    IF Stop_PB OR NOT Permissives_OK THEN
        State := 4;
    ELSIF Zero_Speed THEN
        (* Was running, now stationary, and nobody asked. Same reasoning
           as above: an unexplained stop is a fault, not a state to sit in *)
        Alarm_Word.4 := TRUE;
        State := 5;
    END_IF;

4:  (* STOPPING *)
    Motor_Run := FALSE;
    IF Zero_Speed THEN
        State := 0;
    END_IF;

5:  (* FAULT — requires an operator acknowledgement, not a timer *)
    Motor_Run  := FALSE;
    Alarm_Horn := FALSE;
    IF Stop_PB AND Zero_Speed
       AND Bearing_Temp < BEARING_ALARM
       AND Motor_Current < 1.0
    THEN
        Alarm_Word := 0;
        State := 0;
    END_IF;

END_CASE;

(*
    NOTE FOR THE 62443 ASSESSMENT AT S7

    Every input above arrives over Modbus TCP or S7comm. NEITHER PROTOCOL
    AUTHENTICATES ANYTHING. Anyone who can reach the port can write
    Start_PB, or Bearing_Temp, or Zero_Speed.

    That is not a defect in this program and cannot be fixed in it. It is
    why FR5 — restricted data flow — carries the weight it does in OT:
    the segmentation IS the authentication. See docs/architecture/
    protocol-register.md, and the write allow-list requirement that
    reaches the controller rather than the HMI.
*)

END_PROGRAM
