(*
    PLC-CONV-001 — control function for conveyor CONV-001
    Vigilimen · Sprint 3 · OpenPLC · Purdue Level 1, control zone

    This program sequences and protects the MACHINE. It does not protect
    people — SIS-CONV-001 does that, on a separate runtime, in a separate
    zone, with its own I/O, and this program has no path to it.

    Motor_Run below is a REQUEST. It is wired in series with the safety
    relay's contactor output, so:

        motor turns  =  safety contactor energised  AND  Motor_Run

    This program can stop the belt. It cannot start it against a trip.

    Reference model: plant/sim/interlock_model.py
    I/O contract:    plant/gateway/plc_io_map.py  (ADR-013), checked by FF-23
*)

PROGRAM PLC_CONV_001
VAR
    (* ── I/O contract with the gateway: plant/gateway/plc_io_map.py ────────
       FF-23 fails the build if this block and that table disagree.

       INPUTS. On a real plant these are physical inputs (%IX / %IW). Here
       the gateway plays the field over Modbus, and a Modbus master cannot
       write %IX or %IW, so the simulated field values live in %QX / %QW
       variables that this program only READS. It must never assign them:
       FF-23 checks that too. A simulation device, not a design to copy.
       Addresses 100+ are OpenPLC's slave range: coil = byte*8+bit, holding
       register = word number (ADR-013). *)
    Start_PB          AT %QX100.0 : BOOL;   (* start, local or SCADA          coil 800 *)
    Stop_PB           AT %QX100.1 : BOOL;   (* normal stop                    coil 801 *)
    Zero_Speed        AT %QX100.2 : BOOL;   (* TRUE when belt is stationary   coil 802 *)
    Upstream_Ready    AT %QX100.3 : BOOL;   (* crusher permissive             coil 803 *)
    Downstream_Ready  AT %QX100.4 : BOOL;   (* stockpile permissive           coil 804 *)
    Bearing_Temp_x10  AT %QW100   : UINT;   (* drive-end bearing, 0.1 degC    hreg 100 *)
    Motor_Current_x10 AT %QW101   : UINT;   (* amps x 10                      hreg 101 *)
    Belt_Speed_x100   AT %QW102   : UINT;   (* m/s x 100                      hreg 102 *)

    (* OUTPUTS. Written by this program, read by the gateway. *)
    Motor_Run         AT %QX101.0 : BOOL;   (* RUN REQUEST, in series with SIS coil 808 *)
    Alarm_Horn        AT %QX101.1 : BOOL;   (* pre-start warning              coil 809 *)
    Alarm_Word        AT %QW110   : WORD;   (* to SCADA                       hreg 110 *)
    Plc_State         AT %QW111   : UINT;   (* State below, for diagnostics   hreg 111 *)
    Plc_Map_Version   AT %QW112   : UINT;   (* signature: MAP_VERSION         hreg 112 *)
END_VAR

(* MatIEC (and the IEC grammar) takes a VAR block as ALL located or ALL plain.
   Mixing them in one block fails with 'invalid located variable declaration'
   on every plain line, then a cascade of ':=' errors (found by compiling in
   OpenPLC, 25 Oct). Located variables stay above; plain ones start here.
   FF-23 checks that no block mixes the two. *)
VAR
    (* Engineering values, decoded from the registers once per scan. *)
    Bearing_Temp    : REAL;    (* degC *)
    Motor_Current   : REAL;    (* amps *)
    Belt_Speed      : REAL;    (* m/s  *)

    State           : INT := 0;  (* 0 stopped 1 warning 2 starting 3 running 4 stopping 5 fault *)
    Warn_Timer      : TON;
    Start_Timer     : TON;
    Start_Edge      : R_TRIG;

    Permissives_OK  : BOOL;

    (* One BOOL per alarm bit. MatIEC does not accept bit access on a WORD
       (Alarm_Word.0 := ...), so the bits are kept separately and packed
       into Alarm_Word once per scan, at the end of the program.
       Bit 0 bearing, 1 current, 2 permissive, 3 start fail, 4 run stop. *)
    Alm_Bearing     : BOOL;
    Alm_Current     : BOOL;
    Alm_Permissive  : BOOL;
    Alm_StartFail   : BOOL;
    Alm_RunStop     : BOOL;
END_VAR

VAR CONSTANT
    BEARING_ALARM   : REAL := 85.0;
    BEARING_TRIP    : REAL := 95.0;
    OVERLOAD_TRIP   : REAL := 42.0;
    WARN_TIME       : TIME := T#10s;
    START_TIMEOUT   : TIME := T#15s;
    MAP_VERSION     : UINT := 1;   (* = plc_io_map.MAP_VERSION, FF-23 *)
END_VAR


(* ── Decode the registers ───────────────────────────────────────────── *)

Bearing_Temp  := UINT_TO_REAL(Bearing_Temp_x10) / 10.0;
Motor_Current := UINT_TO_REAL(Motor_Current_x10) / 10.0;
Belt_Speed    := UINT_TO_REAL(Belt_Speed_x100) / 100.0;


(* ── Permissives ────────────────────────────────────────────────────── *)

Permissives_OK := Upstream_Ready AND Downstream_Ready;


(* ── Machine protection ─────────────────────────────────────────────── *)

(* Alarms advise. Trips act. Both belong HERE and not in the safety
   function: they protect the conveyor, not a person, and a safety
   function loaded with machine protection trips more often for reasons
   operations do not respect. *)

Alm_Bearing    := Bearing_Temp >= BEARING_ALARM;
Alm_Current    := Motor_Current >= (OVERLOAD_TRIP * 0.9);
Alm_Permissive := NOT Permissives_OK;

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
        Alm_StartFail := TRUE;
        State := 5;
    END_IF;

3:  (* RUNNING *)
    Motor_Run := TRUE;
    IF Stop_PB OR NOT Permissives_OK THEN
        State := 4;
    ELSIF Zero_Speed THEN
        (* Was running, now stationary, and nobody asked. Same reasoning
           as above: an unexplained stop is a fault, not a state to sit in *)
        Alm_RunStop   := TRUE;
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
        Alm_StartFail := FALSE;
        Alm_RunStop   := FALSE;
        State := 0;
    END_IF;

END_CASE;


Plc_State := INT_TO_UINT(State);
Plc_Map_Version := MAP_VERSION;


(* ── Pack the alarm bits for SCADA ──────────────────────────────────── *)

Alarm_Word := BOOL_TO_WORD(Alm_Bearing)
              OR SHL(BOOL_TO_WORD(Alm_Current), 1)
              OR SHL(BOOL_TO_WORD(Alm_Permissive), 2)
              OR SHL(BOOL_TO_WORD(Alm_StartFail), 3)
              OR SHL(BOOL_TO_WORD(Alm_RunStop), 4);

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
