#!/usr/bin/env python3
"""
Gateway <-> PLC-CONV-001 over Modbus TCP (ADR-013).

The gateway plays the FIELD: it owns the simulated physics, so it feeds the
PLC the process values and operator commands that field devices and a SCADA
would, and reads back what the PLC decided (run request, horn, alarm word,
state). The PLC owns the SEQUENCE and the machine protection.

    gateway --FC15/FC16 write--> %QX100.0..4, %QW100..102   (inputs to the program)
    gateway <--FC1/FC3 read----- %QX101.0..1, %QW110..111   (decisions)

THREE BEHAVIOURS THAT ARE THE POINT OF THE FILE

1. FAIL-SAFE ON LOSS OF THE PLC. No answer means NO RUN REQUEST. interlock_model
   already models an absent control PLC as `control is None`; this is the same
   statement made against a real socket. The caller treats None as "not running".

2. SIGNATURE FIRST, BECAUSE "NO ERROR" DOES NOT MEAN "THE PLC HAS IT". On the
   real OpenPLC v3 build a Modbus write to an address NO program locates is
   still stored and read back (measured 25 Oct: HR100 and coils 801..804 held
   the gateway's values while an old program that located nothing there ran).
   So a read-back cannot detect a missing address. Two checks, every cycle; a
   failure of either means the outputs are NOT trusted:
     * SIGNATURE: the program publishes MAP_VERSION in Plc_Map_Version. An
       unloaded program or an older upload reads 0 or another number. This is
       the detector that works.
     * READ-BACK: kept as a cheap guard against framing or mapping errors in the
       link itself. It is NOT evidence that the program locates the addresses.
   What nothing detects at run time: a program with the right signature that
   lacks one input. FF-23 catches that in the commit (FF-24 documents the gap).

3. NEVER BLOCK THE OPC UA LOOP. Reconnects are rate-limited (retry_s), and the
   caller runs exchange() in a worker thread. A connect attempt to a stopped PLC
   would otherwise freeze every OPC UA session for the length of the timeout.

NO CREDENTIAL ANYWHERE IN THIS FILE, because Modbus has none to give. The
protection for this link is that it exists only on net_control, which is
`internal: true` (ADR-013, protocol-register.md).
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import plc_io_map as M            # noqa: E402
from modbus import Client         # noqa: E402


@dataclass
class PlcInputs:
    start: bool = False
    stop: bool = False
    zero_speed: bool = True
    upstream_ready: bool = True
    downstream_ready: bool = True
    bearing_temp_c: float = 28.0
    motor_current_a: float = 0.0
    belt_speed_mps: float = 0.0


@dataclass
class PlcOutputs:
    motor_run: bool
    alarm_horn: bool
    alarm_word: int
    state: int


class PlcLink:
    def __init__(self, host: str, port: int = 502, unit: int = 1,
                 timeout_s: float = 1.5, retry_s: float = 5.0,
                 client_factory=Client, clock=time.monotonic) -> None:
        self._mk = lambda: client_factory(host, port, unit)
        self.host, self.port = host, port
        self.timeout_s, self.retry_s = timeout_s, retry_s
        self._clock = clock
        self._client = None
        self._next_try = 0.0
        self.ok = False
        self.last_error = "never connected"
        self._announced: str | None = None

    # ---- bookkeeping -------------------------------------------------------

    def _say(self, kind: str, text: str) -> None:
        """Log on a CHANGE of condition only; a 2 Hz line saying 'still down'
        buries the one line that says why it went down."""
        if kind != self._announced:
            print(f"plc-link: {text}", flush=True)
            self._announced = kind

    def _drop(self, why: str) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:                     # noqa: BLE001
                pass
        self._client = None
        self.ok = False
        self.last_error = why
        self._next_try = self._clock() + self.retry_s

    def close(self) -> None:
        self._drop("closed")

    # ---- one exchange ------------------------------------------------------

    def exchange(self, inp: PlcInputs) -> PlcOutputs | None:
        """Write the inputs, read the decisions. None = PLC not usable."""
        if self._client is None:
            if self._clock() < self._next_try:
                return None
            c = self._mk()
            if not c.connect(self.timeout_s):
                self._drop(f"cannot connect to {self.host}:{self.port}")
                self._say("down", f"{self.last_error} (is the PLC started? retry in {self.retry_s:.0f} s)")
                return None
            self._client = c

        c = self._client
        try:
            by = M.BY_NAME
            coil_vals = {
                "Start_PB": inp.start, "Stop_PB": inp.stop,
                "Zero_Speed": inp.zero_speed,
                "Upstream_Ready": inp.upstream_ready,
                "Downstream_Ready": inp.downstream_ready,
            }
            reg_vals = {
                "Bearing_Temp_x10": M.to_raw(by["Bearing_Temp_x10"], inp.bearing_temp_c),
                "Motor_Current_x10": M.to_raw(by["Motor_Current_x10"], inp.motor_current_a),
                "Belt_Speed_x100": M.to_raw(by["Belt_Speed_x100"], inp.belt_speed_mps),
            }
            coil_w = [bool(coil_vals[p.name]) for p in sorted(M.COIL_WRITE, key=lambda p: p.modbus)]
            reg_w = [reg_vals[p.name] for p in sorted(M.REG_WRITE, key=lambda p: p.modbus)]

            c.write_coils(sorted(M.COIL_WRITE, key=lambda p: p.modbus)[0].modbus, coil_w)
            c.write_registers(sorted(M.REG_WRITE, key=lambda p: p.modbus)[0].modbus, reg_w)
            coils = c.read_coils(M.COIL_BASE, M.COIL_COUNT)
            regs = c.read_holding(M.REG_BASE, M.REG_COUNT)
        except (OSError, ConnectionError, ValueError) as e:
            self._drop(f"{type(e).__name__}: {e}")
            self._say("down", f"lost the PLC ({self.last_error}); no run request until it returns")
            return None

        # Signature first: it is the one check that works on an idle plant.
        sig = regs[M.BY_NAME["Plc_Map_Version"].modbus - M.REG_BASE]
        if sig != M.MAP_VERSION:
            self.ok = False
            self.last_error = f"program signature {sig}, expected {M.MAP_VERSION}"
            self._say("mapping", f"{self.last_error} - no program, or an older conveyor.st, is running "
                                 "on the PLC. Outputs ignored.")
            return None

        # Read-back: the PLC must hold exactly what we just wrote.
        bad = [p.name for p in M.COIL_WRITE
               if coils[p.modbus - M.COIL_BASE] != bool(coil_vals[p.name])]
        bad += [p.name for p in M.REG_WRITE
                if regs[p.modbus - M.REG_BASE] != reg_vals[p.name]]
        if bad:
            self.ok = False
            self.last_error = "read-back mismatch: " + ", ".join(bad)
            self._say("mapping", f"{self.last_error} - the program on the PLC does not "
                                 "locate these addresses. Outputs ignored.")
            return None

        out = PlcOutputs(
            motor_run=coils[M.BY_NAME["Motor_Run"].modbus - M.COIL_BASE],
            alarm_horn=coils[M.BY_NAME["Alarm_Horn"].modbus - M.COIL_BASE],
            alarm_word=regs[M.BY_NAME["Alarm_Word"].modbus - M.REG_BASE],
            state=regs[M.BY_NAME["Plc_State"].modbus - M.REG_BASE],
        )
        if not self.ok:
            self._say("up", f"linked to {self.host}:{self.port}, read-back clean")
        self.ok = True
        self.last_error = ""
        return out
