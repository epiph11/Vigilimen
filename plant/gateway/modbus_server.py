#!/usr/bin/env python3
"""
CONV-001 — Modbus TCP server.

Runs the physics simulator and both controllers, and exposes the result on
Modbus TCP exactly as a real PLC would: as bare registers, with no
authentication of any kind.

    python3 plant/gateway/modbus_server.py --port 15020

THE POINT OF THIS FILE
----------------------
It is not a convenience wrapper. It is the thing that makes the protocol
register's central claim CONCRETE rather than quoted:

    anyone who can reach the port can write any register

`plant/gateway/attack_demo.py` connects to this server as an ordinary
client, with no credential, and demonstrates three consequences in about
twenty seconds. That demo is the reason this server exists.

Port 15020 rather than 502 so it runs without root. A real PLC listens on
502 and would not ask who you are there either.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sim"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conveyor_physics import Conveyor as Physics          # noqa: E402
from interlock_model import Conveyor as Logic, Inputs     # noqa: E402

from modbus import Registers, Server                      # noqa: E402


# ---------------------------------------------------------------------------
# Register map
#
# Published as a table because on a real plant this IS the interface contract,
# and an undocumented register is how a commissioning engineer discovers by
# accident that address 7 starts the conveyor.
# ---------------------------------------------------------------------------

COILS = {
    0: "Start_PB",           # WRITABLE — operator start
    1: "Stop_PB",            # WRITABLE — operator stop
    2: "EStop_ChA",          # WRITABLE — should NOT be. See the demo.
    3: "EStop_ChB",          # WRITABLE — should NOT be. See the demo.
    4: "Safety_Reset",       # WRITABLE
    5: "Motor_Running",      # read-only in intent; Modbus has no such concept
    6: "Safety_Tripped",
    7: "Zero_Speed",
}

HOLDING = {
    0: "BearingTemp_C_x10",  # WRITABLE — the sensor spoofing target
    1: "Current_A_x10",
    2: "Speed_mps_x100",
    3: "Load_tph",
    4: "Vibration_mms_x100",
}

# "Writable in intent" is a fiction. Modbus function code 5 (write single
# coil) and 6 (write single register) apply to every address the server
# exposes. There is no read-only attribute in the protocol — only in the
# documentation, and documentation is not a control.


class Plant:
    """The simulated conveyor, driven by the register block."""

    def __init__(self) -> None:
        self.physics = Physics()
        self.logic = Logic()
        self.lock = threading.Lock()
        self.running = False
        self.scans = 0

    def scan(self, regs: Registers) -> None:
        with self.lock:
            i = Inputs(
                estop_ch_a=regs.get_coil(2),
                estop_ch_b=regs.get_coil(3),
                start_pressed=regs.get_coil(0),
                stop_pressed=regs.get_coil(1),
                safety_reset_pressed=regs.get_coil(4),
                zero_speed=self.physics.zero_speed,
                # The control function reads bearing temperature FROM THE
                # REGISTER, not from the physics object. That is deliberate
                # and it is the whole vulnerability: a PLC believes its
                # inputs, and on Modbus its inputs are whatever was last
                # written to them, by anyone.
                bearing_temp_c=regs.get_reg(0) / 10.0,
                motor_current_a=self.physics.motor_current_a,
            )

            self.running = self.logic.scan(i)
            self.physics.running = self.running
            tags = self.physics.step(1.0)
            self.scans += 1

            # Write the process values back — except bearing temperature,
            # which stays whatever the register holds. A real transmitter
            # would overwrite it every scan; leaving it writable is what
            # makes the spoof observable in a demo rather than a race.
            regs.set_coil(5, self.running)
            regs.set_coil(6, self.logic.safety.tripped)
            regs.set_coil(7, self.physics.zero_speed)
            regs.set_reg(1, int(tags["CONV001.Current_A"] * 10))
            regs.set_reg(2, int(tags["CONV001.Speed_mps"] * 100))
            regs.set_reg(3, int(tags["CONV001.Load_tph"]))
            regs.set_reg(4, int(tags["CONV001.Vibration_mms"] * 100))

    def status(self) -> str:
        return (f"scan {self.scans:5d}  "
                f"motor={'RUN ' if self.running else 'STOP'}  "
                f"safety={'TRIPPED' if self.logic.safety.tripped else 'ok     '}  "
                f"{self.logic.safety.trip_reason}")


def build_registers() -> Registers:
    regs = Registers()
    # Healthy initial state: e-stop channels closed, bearing at ambient.
    regs.set_coil(2, True)
    regs.set_coil(3, True)
    regs.set_reg(0, 400)
    return regs


def run(port: int, verbose: bool) -> None:
    regs = build_registers()
    plant = Plant()

    def loop() -> None:
        while True:
            plant.scan(regs)
            if verbose and plant.scans % 5 == 0:
                print("  " + plant.status(), flush=True)
            time.sleep(0.2)

    threading.Thread(target=loop, daemon=True).start()

    print(f"CONV-001 Modbus TCP server on 0.0.0.0:{port}")
    print("No authentication. None is available. See docs/architecture/protocol-register.md\n")
    Server(("0.0.0.0", port), regs).serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=15020)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    run(a.port, a.verbose)
