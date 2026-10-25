#!/usr/bin/env python3
"""
FF-26 — the running stack does what the unit checks claim (needs Docker).

Every other fitness function runs on a laptop with no containers. This one runs
INSIDE the collector container, because that is the one place that already has
asyncua, psycopg and a route to both the gateway and the historian, and it
drives the real stack the way the HMI would:

    phase "alarm"          STOP, clear faults, START, wait for the belt, write
                           FaultVibrationSpike = 8, time how long until a
                           NORMAL->UNACK row for Vibration HI_HI is in alarm_event.
                           Leaves the spike ON. (acceptance test 4e: < 2 s)
    phase "after-restart"  after `docker restart vigilimen-collector`: the same
                           incident must NOT have been raised a second time, and
                           alarm_state must still hold it (ADR-019).
    phase "clear"          Clear all faults: HI_HI must go UNACK -> RTN_UNACK.
    phase "all"            alarm + clear.

It is NOT run in CI. It is how a person proves, once per change, that the Docker
build matches what FF-07, FF-23, FF-24 and FF-25 believed.

    docker cp scripts\\ff26_stack_e2e.py vigilimen-collector:/tmp/ff26.py
    docker exec -e VIGILIMEN_OPCUA_USER=engineer -e VIGILIMEN_OPCUA_PASSWORD=eng1neer-demo `
        vigilimen-collector python /tmp/ff26.py --phase all --expect-link modbus

It signs in as `engineer` because only that account is MEANT to write. Note
what that proves about the other one: ADR-017 records that `historian` can write
the Fault* tags too.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import timezone

import psycopg
from asyncua import Client

URL = os.environ.get("VIGILIMEN_OPCUA_URL", "opc.tcp://gateway:4840/vigilimen/conv001/")
USER = os.environ.get("VIGILIMEN_OPCUA_USER", "engineer")
PASSWORD = os.environ.get("VIGILIMEN_OPCUA_PASSWORD", "")
DSN = os.environ.get("VIGILIMEN_PGDSN", "")
VIB = "CONV001.Vibration_mms"
FAULTS = ["FaultBearingWear", "FaultBeltSlip", "FaultMisalignment", "FaultIdlerSeizure", "FaultVibrationSpike"]

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((bool(ok), name, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""), flush=True)


async def node_map(client: Client) -> dict:
    ns = await client.get_namespace_index("urn:vigilimen:plant:conv001")
    root = client.nodes.objects
    for n in ("Enterprise", "PilbaraSite", "ProcessingArea", "ConveyingCell", "CONV001"):
        root = await root.get_child(f"{ns}:{n}")
    names = ["Running", "BeltSpeed_mps", "Vibration_mms", "StartCommand", "StopCommand",
             "PlcLinkOK", "PlcState"] + FAULTS
    return {n: await root.get_child(f"{ns}:{n}") for n in names}


async def wait_for(pred, timeout_s: float, every_s: float = 0.25):
    t_end = time.monotonic() + timeout_s
    while time.monotonic() < t_end:
        v = await pred()
        if v:
            return v
        await asyncio.sleep(every_s)
    return None


def q(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
    conn.commit()
    return rows


def last_event_id(conn) -> int:
    return q(conn, "SELECT coalesce(max(event_id), 0) FROM alarm_event")[0][0]


def hh_events(conn, since: int):
    return q(conn, "SELECT event_id, ts, from_state, to_state FROM alarm_event "
                   "WHERE tag_id = %s AND condition = 'HI_HI' AND event_id > %s ORDER BY event_id", (VIB, since))


async def phase_alarm(t, conn, args) -> int:
    print("\nphase alarm — STOP, clear, START, spike", flush=True)
    for f in FAULTS:
        await t[f].write_value(0.0)
    await t["StartCommand"].write_value(False)
    await t["StopCommand"].write_value(True)

    if args.expect_link == "modbus":
        ok = await wait_for(lambda: _val(t["PlcLinkOK"]), 60)
        check("PLC link up (PlcLinkOK)", ok, "start the PLC in the OpenPLC UI if this fails" if not ok else "")
        if not ok:
            return 1
    else:
        v = await t["PlcLinkOK"].get_value()
        check("embedded mode: PlcLinkOK is False, as designed", v is False)

    stopped = await wait_for(lambda: _not(t["Running"]), 60)
    check("belt stopped before the test", stopped)
    await asyncio.sleep(1.5)

    await t["StopCommand"].write_value(False)
    await t["StartCommand"].write_value(True)
    t_start = time.monotonic()
    wait = 60 if args.expect_link == "modbus" else 15
    running = await wait_for(lambda: _val(t["Running"]), wait)
    took = time.monotonic() - t_start
    check("START: belt running", running, f"{took:.1f} s")
    if args.expect_link == "modbus":
        check("with the PLC in the loop START waits for the 10 s horn (>= 9 s)", took >= 9.0, f"{took:.1f} s")
    else:
        check("embedded mode: START is immediate (< 5 s)", took < 5.0, f"{took:.1f} s")
    if not running:
        return 1
    fast = await wait_for(lambda: _gt(t["BeltSpeed_mps"], 2.1), 10)
    check("belt at speed (> 2.1 m/s)", fast)
    await asyncio.sleep(3.0)                       # let the collector's speed gate arm

    base = last_event_id(conn)
    t0_wall = time.time()
    t0 = time.monotonic()
    await t["FaultVibrationSpike"].write_value(8.0)

    async def seen():
        rows = [r for r in hh_events(conn, base) if r[3] == "UNACK"]
        return rows[0] if rows else None

    row = await wait_for(seen, 6.0, every_s=0.05)
    latency = time.monotonic() - t0
    if row:
        ev_ts = row[1].astimezone(timezone.utc).timestamp()
        check("Spike +8: Vibration HI_HI NORMAL->UNACK is in alarm_event in < 2 s", latency < 2.0,
              f"{latency:.2f} s to the row; event stamped {ev_ts - t0_wall:+.2f} s from the write")
    else:
        check("Spike +8: Vibration HI_HI NORMAL->UNACK is in alarm_event in < 2 s", False, "no row within 6 s")
    print(f"  for the restart phase use:  --since-event-id {base}")
    return 0 if row and latency < 2.0 else 1


async def phase_after_restart(t, conn, args) -> int:
    print("\nphase after-restart — the incident must not be raised twice", flush=True)
    await asyncio.sleep(8.0)
    ev = hh_events(conn, args.since_event_id)
    raises = [e for e in ev if e[3] == "UNACK"]
    check("exactly one NORMAL->UNACK for the incident across the restart", len(raises) == 1,
          f"{len(raises)} raise(s) since event {args.since_event_id}")
    st = q(conn, "SELECT state, in_condition FROM alarm_state WHERE tag_id = %s AND condition = 'HI_HI'", (VIB,))
    check("alarm_state holds the live alarm", bool(st) and st[0][0] in ("UNACK", "ACKED") and st[0][1] is True,
          str(st))
    return 0 if all(r[0] for r in results) else 1


async def phase_clear(t, conn, args) -> int:
    print("\nphase clear — Clear all faults", flush=True)
    base = last_event_id(conn)
    for f in FAULTS:
        await t[f].write_value(0.0)

    async def rtn():
        rows = [r for r in hh_events(conn, base) if r[3] == "RTN_UNACK"]
        return rows[0] if rows else None

    row = await wait_for(rtn, 15.0, every_s=0.1)
    check("Clear all faults: HI_HI UNACK -> RTN_UNACK", bool(row))
    try:
        q(conn, "UPDATE alarm_event SET note = note WHERE event_id = (SELECT max(event_id) FROM alarm_event)")
        refused = False
    except psycopg.errors.RaiseException:
        conn.rollback()
        refused = True
    if args.expect_append_only:
        check("alarm_event refuses an UPDATE (append-only trigger)", refused)
    return 0 if row else 1


async def _val(node):
    return bool(await node.get_value())


async def _not(node):
    return not bool(await node.get_value())


async def _gt(node, x):
    return float(await node.get_value()) > x


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["alarm", "after-restart", "clear", "all"], default="all")
    ap.add_argument("--expect-link", choices=["off", "modbus"], default="off")
    ap.add_argument("--since-event-id", type=int, default=0)
    ap.add_argument("--expect-append-only", action="store_true")
    args = ap.parse_args()
    if not PASSWORD or not DSN:
        print("FF-26: set VIGILIMEN_OPCUA_PASSWORD and VIGILIMEN_PGDSN (docker exec -e ...)", file=sys.stderr)
        return 2

    print(f"FF-26 — stack end to end (phase={args.phase}, link={args.expect_link})")
    client = Client(URL, timeout=10)
    client.set_user(USER)
    client.set_password(PASSWORD)
    await client.connect()
    conn = psycopg.connect(DSN)
    try:
        t = await node_map(client)
        rc = 0
        if args.phase in ("alarm", "all"):
            rc |= await phase_alarm(t, conn, args)
        if args.phase == "after-restart":
            rc |= await phase_after_restart(t, conn, args)
        if args.phase in ("clear", "all") and rc == 0:
            rc |= await phase_clear(t, conn, args)
    finally:
        conn.close()
        await client.disconnect()

    failed = [r for r in results if not r[0]]
    print(f"\n{len(results)} checks, {len(failed)} failed")
    print("FF-26 pass." if not failed and rc == 0 else "FF-26 FAIL: write symptom, cause, fix in the log BEFORE changing anything.")
    return 1 if failed or rc else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
