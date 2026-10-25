#!/usr/bin/env python3
"""
The I/O contract between the gateway and PLC-CONV-001 (ADR-013).

ONE TABLE, THREE READERS
------------------------
This file is the only place the addresses are written down as data:

  * plc_link.py        reads and writes the PLC through it;
  * plc-control/conveyor.st declares the same variables with `AT %...`;
  * scripts/ff23_plc_io_map.py fails the build if the ST and this table
    disagree on a name, an IEC address, a type or a direction.

On a real plant this table IS the interface contract, and an undocumented
register is how a commissioning engineer finds out that address 7 starts the
conveyor.

HOW OPENPLC EXPOSES A LOCATED VARIABLE ON MODBUS (runtime for Linux/Windows,
documented at autonomylogic.com "Modbus addressing")

    %QXb.i   coil              address = b*8 + i      read/write
    %QWn     holding register  address = n            read/write
    %IXb.i / %IWn              discrete input / input register: READ-ONLY
                               for a Modbus master.

A Modbus master cannot write %IX or %IW, so a simulated field value cannot be
fed to the PLC through them. The gateway therefore writes the simulated field
inputs into %QX/%QW variables that the program only READS. That is a
simulation device, not a design to copy: on a real plant those are physical
inputs and no network master writes them. conveyor.st never assigns these
variables, and FF-23 checks that it never does.

Range 100+ is the OpenPLC "slave device" range. Nothing else uses it here (no
slave device is configured), and it keeps clear of the physical I/O range 0-99.

NOT COVERED: PLC-SAFETY. Its I/O is not in this table and never will be.
See ADR-014 and plant/docker-compose.yml (net_safety has one member).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Bump when a point is added, moved or re-typed. The program publishes it in
# Plc_Map_Version and the gateway refuses to trust a PLC that reports another
# number. This is what catches "no program loaded" and "an older upload":
# an unlocated register reads 0, and a write of 0 to it reads back as 0, so a
# per-point read-back alone cannot see a missing input that happens to be idle.
MAP_VERSION = 1

TO_PLC = "to_plc"        # written by the gateway (simulated field input)
FROM_PLC = "from_plc"    # written by the program, read by the gateway


@dataclass(frozen=True)
class Point:
    name: str            # identifier in conveyor.st
    iec: str             # %QX100.0 / %QW100
    iec_type: str        # BOOL | UINT | WORD
    direction: str
    scale: float = 1.0   # raw = round(engineering * scale); registers only
    unit: str = ""

    @property
    def is_coil(self) -> bool:
        return self.iec.startswith("%QX")

    @property
    def modbus(self) -> int:
        return iec_to_modbus(self.iec)


def iec_to_modbus(iec: str) -> int:
    m = re.fullmatch(r"%QX(\d+)\.([0-7])", iec)
    if m:
        return int(m.group(1)) * 8 + int(m.group(2))
    m = re.fullmatch(r"%QW(\d+)", iec)
    if m:
        return int(m.group(1))
    raise ValueError(f"not a Modbus-mapped located address: {iec}")


POINTS: tuple[Point, ...] = (
    # ---- gateway -> PLC : simulated field inputs and operator commands ----
    Point("Start_PB",          "%QX100.0", "BOOL", TO_PLC),
    Point("Stop_PB",           "%QX100.1", "BOOL", TO_PLC),
    Point("Zero_Speed",        "%QX100.2", "BOOL", TO_PLC),
    Point("Upstream_Ready",    "%QX100.3", "BOOL", TO_PLC),
    Point("Downstream_Ready",  "%QX100.4", "BOOL", TO_PLC),
    Point("Bearing_Temp_x10",  "%QW100",   "UINT", TO_PLC, 10.0,  "degC"),
    Point("Motor_Current_x10", "%QW101",   "UINT", TO_PLC, 10.0,  "A"),
    Point("Belt_Speed_x100",   "%QW102",   "UINT", TO_PLC, 100.0, "m/s"),
    # ---- PLC -> gateway : what the program decided ------------------------
    Point("Motor_Run",         "%QX101.0", "BOOL", FROM_PLC),
    Point("Alarm_Horn",        "%QX101.1", "BOOL", FROM_PLC),
    Point("Alarm_Word",        "%QW110",   "WORD", FROM_PLC),
    Point("Plc_State",         "%QW111",   "UINT", FROM_PLC),
    Point("Plc_Map_Version",   "%QW112",   "UINT", FROM_PLC),
)

BY_NAME = {p.name: p for p in POINTS}

# Blocks the link reads and writes, derived so they cannot drift from POINTS.
COIL_WRITE = [p for p in POINTS if p.is_coil and p.direction == TO_PLC]
REG_WRITE = [p for p in POINTS if not p.is_coil and p.direction == TO_PLC]
COIL_BASE = min(p.modbus for p in POINTS if p.is_coil)
COIL_COUNT = max(p.modbus for p in POINTS if p.is_coil) - COIL_BASE + 1
REG_BASE = min(p.modbus for p in POINTS if not p.is_coil)
REG_COUNT = max(p.modbus for p in POINTS if not p.is_coil) - REG_BASE + 1


def to_raw(p: Point, value: float) -> int:
    """Engineering value to the 16-bit register, clamped. A UINT cannot be
    negative and a bad float must not wrap into a plausible temperature."""
    if value != value:                      # NaN
        return 0
    return max(0, min(0xFFFF, int(round(value * p.scale))))


def from_raw(p: Point, raw: int) -> float:
    return raw / p.scale


def self_check() -> None:
    """Cheap invariants, run by FF-23 and by the link on import-time demand."""
    seen: set[tuple[bool, int]] = set()
    for p in POINTS:
        key = (p.is_coil, p.modbus)
        assert key not in seen, f"two points share a Modbus address: {p.name}"
        seen.add(key)
    assert COIL_BASE == 800 and REG_BASE == 100, "OpenPLC slave range moved?"


if __name__ == "__main__":
    self_check()
    print(f"{'name':20} {'IEC':10} {'type':5} {'Modbus':>6}  {'dir':9} scale")
    for p in POINTS:
        kind = "coil" if p.is_coil else "hreg"
        print(f"{p.name:20} {p.iec:10} {p.iec_type:5} {kind}{p.modbus:>4}  {p.direction:9} {p.scale:g}")
