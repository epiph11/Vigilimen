#!/usr/bin/env python3
"""
FF-24 — the gateway drives PLC-CONV-001 over Modbus, and fails SAFE when it can't (ADR-013).

Runs the real gateway code (plant_cycle.py, plc_link.py, modbus.py, the physics
and the safety-contactor model) against a FAKE OpenPLC: a Modbus TCP server with
OpenPLC's addressing rules and a Python port of conveyor.st's sequence behind it.
No Docker, no asyncua, no real time (one gateway cycle = 0.5 s of plant time).

Each case is a way this link fails while looking like it works:

  * the PLC is absent and the belt keeps running on the last request;
  * a write lands on an address no program locates, OpenPLC drops it silently,
    and the gateway believes the PLC has its Stop;
  * the motor runs against a dropped safety contactor because the AND got lost;
  * the pre-start horn is skipped, i.e. the PLC is not really in the loop;
  * a connect attempt to a stopped PLC blocks every cycle.

WHAT THIS DOES NOT PROVE
  That conveyor.st behaves like the Python port below (FF-23 checks the
  addresses, not the logic), or that real OpenPLC maps addresses as the fake does.
  The port is a TEST DOUBLE. The Docker run (FF-26) is the proof.

    python3 scripts/ff24_gateway_plc_link.py
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("plant/gateway", "plant/sim"):
    sys.path.insert(0, str(ROOT / sub))

import plc_io_map as M                                   # noqa: E402
from modbus import Client, Registers, Server             # noqa: E402
from plc_link import PlcLink                             # noqa: E402
from plant_cycle import PlantCycle                       # noqa: E402
from interlock_model import Contactor                    # noqa: E402

results: list[tuple[bool, str, str]] = []


def check(name: str, cond: bool, why: str) -> None:
    results.append((bool(cond), name, why))


# ---------------------------------------------------------------------------
# The fake OpenPLC
# ---------------------------------------------------------------------------

class LocatedList(list):
    """A coil or register table that STORES writes at any address.

    MEASURED, 25 Oct, on the real OpenPLC v3 build: with an old program that
    located nothing at these addresses, a Modbus write to HR100 and to coils
    801..804 was stored and read back. This fake used to DROP writes to
    unlocated addresses, which was a belief about OpenPLC, not an observation,
    and it was wrong. The consequence: a read-back cannot detect an unlocated
    address at all. Only the program's signature (Plc_Map_Version) can, and
    only FF-23 (static) catches a program that lacks one input but still
    reports the right signature.
    """

    def __init__(self, n: int, located: set[int]) -> None:
        super().__init__([0] * n)
        self.located = located            # kept for documentation; not used to filter

    def __setitem__(self, k, v):
        if isinstance(k, slice):
            for i, x in zip(range(*k.indices(len(self))), v):
                super().__setitem__(i, x)
        else:
            super().__setitem__(k, v)


class TrackingServer(Server):
    """Remembers accepted sockets so a 'stopped PLC' really drops its connections.
    shutdown() alone leaves established handler threads serving, which is not
    what stopping a container does."""

    def __init__(self, *a, **k) -> None:
        self.conns: list[socket.socket] = []
        super().__init__(*a, **k)

    def get_request(self):
        req, addr = super().get_request()
        self.conns.append(req)
        return req, addr


class FakeOpenPLC:
    """Modbus server + a port of conveyor.st's sequence. A TEST DOUBLE."""

    WARN_S, START_TIMEOUT_S = 10.0, 15.0
    SCAN_S = 0.02

    def __init__(self, loaded: bool = True, omit: tuple[str, ...] = (), map_version: int | None = None) -> None:
        self.map_version = M.MAP_VERSION if map_version is None else map_version
        pts = [p for p in M.POINTS if loaded and p.name not in omit]
        self.regs = Registers(1, 1)
        self.regs.coils = LocatedList(1600, {p.modbus for p in pts if p.is_coil})
        self.regs.regs = LocatedList(1024, {p.modbus for p in pts if not p.is_coil})
        self.loaded = loaded
        self.server: Server | None = None
        self.port = 0
        self.state, self.warn, self.startt, self.prev_start = 0, 0.0, 0.0, False
        self.alm_startfail = self.alm_runstop = False
        self.requests = 0

    # --- network -----------------------------------------------------------
    def serve(self, port: int = 0) -> int:
        self.server = TrackingServer(("127.0.0.1", port), self.regs)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self.port

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            for k in self.server.conns:
                try:
                    k.shutdown(socket.SHUT_RDWR)
                    k.close()
                except OSError:
                    pass
            self.server = None

    # --- the program -------------------------------------------------------
    def _c(self, name): return bool(self.regs.coils[M.BY_NAME[name].modbus])
    def _r(self, name): return self.regs.regs[M.BY_NAME[name].modbus]
    def _set_c(self, name, v): self.regs.coils[M.BY_NAME[name].modbus] = bool(v)
    def _set_r(self, name, v): self.regs.regs[M.BY_NAME[name].modbus] = int(v) & 0xFFFF

    def scan(self, dt: float) -> None:
        if not self.loaded:
            return
        temp = self._r("Bearing_Temp_x10") / 10.0
        cur = self._r("Motor_Current_x10") / 10.0
        start, stop, zero = self._c("Start_PB"), self._c("Stop_PB"), self._c("Zero_Speed")
        perm = self._c("Upstream_Ready") and self._c("Downstream_Ready")
        alm_bearing, alm_current = temp >= 85.0, cur >= 42.0 * 0.9
        edge, self.prev_start = start and not self.prev_start, start

        if temp >= 95.0 or cur >= 42.0:
            self.state = 5
        motor, horn = self._c("Motor_Run"), self._c("Alarm_Horn")
        s = self.state
        if s == 0:
            motor = horn = False
            if edge and perm:
                self.state = 1
        elif s == 1:
            motor, horn = False, True
            self.warn += dt
            if stop:
                self.warn, self.state = 0.0, 0
            elif self.warn >= self.WARN_S:
                self.warn, self.state = 0.0, 2
        elif s == 2:
            motor, horn = True, False
            self.startt += dt
            if not zero:
                self.startt, self.state = 0.0, 3
            elif self.startt >= self.START_TIMEOUT_S:
                self.startt, self.alm_startfail, self.state = 0.0, True, 5
        elif s == 3:
            motor = True
            if stop or not perm:
                self.state = 4
            elif zero:
                self.alm_runstop, self.state = True, 5
        elif s == 4:
            motor = False
            if zero:
                self.state = 0
        elif s == 5:
            motor = horn = False
            if stop and zero and temp < 85.0 and cur < 1.0:
                self.alm_startfail = self.alm_runstop = False
                self.state = 0
        self._set_c("Motor_Run", motor)
        self._set_c("Alarm_Horn", horn)
        self._set_r("Alarm_Word", int(alm_bearing) | int(alm_current) << 1 | int(not perm) << 2
                    | int(self.alm_startfail) << 3 | int(self.alm_runstop) << 4)
        self._set_r("Plc_State", self.state)
        self._set_r("Plc_Map_Version", self.map_version)

    def advance(self, seconds: float) -> None:
        for _ in range(round(seconds / self.SCAN_S)):
            self.scan(self.SCAN_S)


class SteppedClient(Client):
    """A real Modbus client that lets the fake PLC run between our write and our read."""
    plc: FakeOpenPLC

    def write_registers(self, addr, values):
        super().write_registers(addr, values)
        self.plc.advance(0.5)


def make_link(plc: FakeOpenPLC, clock=time.monotonic, retry_s: float = 5.0) -> PlcLink:
    def factory(host, port, unit):
        c = SteppedClient(host, port, unit)
        c.plc = plc
        return c
    return PlcLink("127.0.0.1", plc.port, client_factory=factory, clock=clock, retry_s=retry_s,
                   timeout_s=0.5)


def run(cycle: PlantCycle, seconds: float, *, start=False, stop=False, faults=None) -> dict:
    snap = {}
    for _ in range(round(seconds / cycle.dt_s)):
        snap = cycle.step(start, stop, faults or {})
    return snap


def pulse_start(cycle: PlantCycle) -> None:
    """START as the HMI sends it: one press, latched until STOP."""
    cycle.step(True, False, {})


# ---------------------------------------------------------------------------
# 0. FC 15 / FC 16 on their own
# ---------------------------------------------------------------------------

regs = Registers(64, 64)
srv = Server(("127.0.0.1", 0), regs)
threading.Thread(target=srv.serve_forever, daemon=True).start()
c = Client("127.0.0.1", srv.server_address[1])
c.connect()
c.write_coils(3, [True, False, True, True, False, True, False, False, True])
check("FC15 writes nine coils, bit-packed across a byte boundary",
      [regs.get_coil(3 + i) for i in range(9)] == [True, False, True, True, False, True, False, False, True],
      "the packing is the part that is easy to get wrong")
c.write_registers(10, [1, 65535, 300])
check("FC16 writes three registers", [regs.get_reg(10), regs.get_reg(11), regs.get_reg(12)] == [1, 65535, 300],
      "one write, one consistent set of inputs per PLC scan")
try:
    c.write_registers(62, [1, 2, 3])
    refused = False
except OSError:
    refused = True
check("FC16 past the end of the table is an exception, not a partial write",
      refused and regs.get_reg(62) == 0, "a partial write is a half-updated input set")
c.close(); srv.shutdown(); srv.server_close()

# ---------------------------------------------------------------------------
# 1. Embedded mode is unchanged (no link): START runs at once
# ---------------------------------------------------------------------------

emb = PlantCycle(None)
s = emb.step(True, False, {})
check("embedded mode (no PLC link) still starts on the first scan",
      s["Running"] is True and s["PlcLinkOK"] is False,
      "the default must keep acceptance test 4e meaning what it meant")

# ---------------------------------------------------------------------------
# 2. Linked: the PLC owns the sequence
# ---------------------------------------------------------------------------

plc = FakeOpenPLC()
plc.serve()
link = make_link(plc)
cy = PlantCycle(link)

s = run(cy, 2.0)
check("link comes up with a clean read-back before anything is commanded",
      link.ok and s["PlcLinkOK"] and s["PlcState"] == 0 and s["Running"] is False,
      "the read-back must pass on an idle plant, not only under load")

pulse_start(cy)
s = run(cy, 6.0, start=True)
check("after START the horn sounds and the belt has NOT moved (PLC state 1)",
      s["PlcState"] == 1 and s["Running"] is False and s["BeltSpeed_mps"] == 0.0,
      "if the belt moves at once, the PLC is not in the loop: the gateway is still deciding")
s = run(cy, 8.0, start=True)
check("after the 10 s warning the PLC requests RUN and the belt reaches speed",
      s["PlcState"] == 3 and s["Running"] is True and s["BeltSpeed_mps"] > 2.3,
      "the 10 s warning comes from conveyor.st, not from the gateway")

s = run(cy, 2.0, start=True, faults={"FaultVibrationSpike": 8.0})
check("a vibration spike reaches the process value and does not trip the PLC",
      s["Vibration_mms"] > 7.1 and s["PlcState"] == 3 and s["Running"] is True,
      "vibration is not a machine-protection input of conveyor.st; the ALARM is the collector's job")
run(cy, 1.0, start=True, faults={})

# Series connection: PLC says RUN, contactor says no.
real_scan = cy.logic.safety.scan
cy.logic.safety.scan = lambda i, dt_ms=100: Contactor.DROPPED
s = cy.step(True, False, {})
check("PLC requesting RUN cannot turn the motor against a dropped contactor",
      plc._c("Motor_Run") is True and s["Running"] is False,
      "motor turns = contactor energised AND run request. Losing the AND loses ADR-011")
cy.logic.safety.scan = real_scan

# Machine protection in the PLC: bearing over 95 degC.
cy.physics.bearing_temp_c = 96.0
s = run(cy, 1.0, start=True)
check("bearing at 96 degC: the PLC trips to FAULT and the belt stops",
      s["PlcState"] == 5 and s["Running"] is False and (s["PlcAlarmWord"] & 1) == 1,
      "the 95 degC trip lives in conveyor.st (BEARING_TRIP). Alarm_Word bit 0 = bearing")
cy.physics.bearing_temp_c = 40.0
run(cy, 40.0, stop=True)                                   # belt stops, then the operator presses STOP
s = run(cy, 2.0, stop=True)
check("FAULT clears only on STOP with the belt stopped and the bearing cool",
      s["PlcState"] == 0,
      "a fault needs an operator, not a timer")

# Current trip from injected faults, without touching the physics directly.
pulse_start(cy)
run(cy, 22.0, start=True)
s = run(cy, 1.0, start=True, faults={"FaultBeltSlip": 1.0, "FaultIdlerSeizure": 1.0})
check("slip plus a seized idler push current over 42 A and the PLC trips on overload",
      s["PlcState"] == 5 and s["Running"] is False,
      "fault injection reaches machine protection through the physics, as a real fault would")
run(cy, 30.0, stop=True)

# ---------------------------------------------------------------------------
# 3. Loss of the PLC: fail safe, do not block, do not hammer
# ---------------------------------------------------------------------------

plc2 = FakeOpenPLC(); plc2.serve()
fake_t = [0.0]
link2 = make_link(plc2, clock=lambda: fake_t[0], retry_s=5.0)
cy2 = PlantCycle(link2)
pulse_start(cy2)
s = run(cy2, 20.0, start=True)
assert s["Running"] is True, "setup: PLC 2 should be running the belt"
port2 = plc2.port
plc2.stop()
t0 = time.monotonic()
s = cy2.step(True, False, {})
dt_call = time.monotonic() - t0
check("PLC lost mid-run: no run request, belt stops, link reported down",
      s["Running"] is False and s["PlcLinkOK"] is False,
      "an absent control PLC is no request, the same as `control is None` in interlock_model.py")
check("a failed connect returns quickly (OPC UA is not frozen by a dead PLC)",
      dt_call < 1.5, f"took {dt_call:.2f} s")

attempts = {"n": 0}
orig_connect = Client.connect
def counting_connect(self, timeout=5.0):
    attempts["n"] += 1
    return orig_connect(self, timeout)
Client.connect = counting_connect
for _ in range(8):
    cy2.step(True, False, {})
Client.connect = orig_connect
check("reconnects are rate-limited (8 cycles inside the retry window, 0 attempts)",
      attempts["n"] == 0, f"{attempts['n']} attempts. Hammering a stopped PLC is its own outage")

plc2.serve(port2)
fake_t[0] += 6.0
s = run(cy2, 3.0, start=True)
check("PLC returns: the link recovers on the next window",
      link2.ok and s["PlcLinkOK"] is True,
      "a link that needs a gateway restart is a link that needs a human")
plc2.stop()

# ---------------------------------------------------------------------------
# 4. The program is not loaded / not the right one: read-back catches it
# ---------------------------------------------------------------------------

for label, plc3 in (("no program loaded", FakeOpenPLC(loaded=False)),
                    ("an older conveyor.st (signature 0 is 'unloaded', 7 is 'someone else's')",
                     FakeOpenPLC(map_version=7))):
    plc3.serve()
    l3 = make_link(plc3)
    cy3 = PlantCycle(l3)
    s = run(cy3, 3.0)                                       # IDLE: nothing commanded at all
    check(f"{label}: caught on an IDLE plant by the signature, belt not run",
          l3.ok is False and "signature" in l3.last_error and s["PlcLinkOK"] is False,
          "an unlocated register reads 0, and 0 is what an idle input holds: read-back alone sees nothing")
    s = run(cy3, 3.0, start=True)
    check(f"{label}: START is not honoured",
          s["Running"] is False, "the gateway must not act on outputs from a PLC it cannot identify")
    plc3.stop()

plc4 = FakeOpenPLC(omit=("Stop_PB",))                       # signature fine, one input not located
plc4.serve()
l4 = make_link(plc4)
cy4 = PlantCycle(l4)
run(cy4, 2.0)
s = run(cy4, 2.0, stop=True)
check("KNOWN LIMIT: a program with the right signature but no Stop_PB is NOT detected at run time",
      l4.ok is True,
      "measured on real OpenPLC: unlocated addresses still store and read back, so read-back proves nothing. "
      "FF-23 (static) and the signature are the only defences, and this case documents that rather than hides it")
plc4.stop()

# ---------------------------------------------------------------------------
# 5. Scaling
# ---------------------------------------------------------------------------

check("scaling clamps instead of wrapping (a bad float is not a plausible temperature)",
      M.to_raw(M.BY_NAME["Bearing_Temp_x10"], -5.0) == 0
      and M.to_raw(M.BY_NAME["Bearing_Temp_x10"], 1e9) == 0xFFFF
      and M.to_raw(M.BY_NAME["Bearing_Temp_x10"], float("nan")) == 0
      and M.to_raw(M.BY_NAME["Belt_Speed_x100"], 2.5) == 250,
      "a UINT register that wraps turns 6554 degC into 18 degC")

plc.stop()

# ---------------------------------------------------------------------------

PASS, FAIL = "PASS", "FAIL"
print("FF-24 — the gateway drives PLC-CONV-001 over Modbus, and fails safe\n")
width = max(len(n) for _, n, _ in results)
for ok, name, why in results:
    print(f"  {PASS if ok else FAIL}  {name.ljust(width)}")
    if not ok:
        print(f"        why this case exists: {why}")
failed = [r for r in results if not r[0]]
print(f"\n{len(results)} cases, {len(failed)} failed")
if failed:
    print("\nFF-24 FAIL.")
    sys.exit(1)
print("""
FF-24 pass.

What this proves: the gateway's link code, framing, scaling, fail-safe and
read-back behave as ADR-013 says, against a fake PLC with OpenPLC's rules.
What it does not prove: that conveyor.st behaves like the port above, or that
real OpenPLC maps addresses as the fake does. The Docker run (FF-26) does.""")
