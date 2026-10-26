#!/usr/bin/env python3
"""
FF-28 — the alarm history survives tampering, and a restart during SHELVED (needs Docker).

Closes the two gaps FF-26 left open (état des lieux, "Pas encore prouvé"):

    phase "tamper"            DELETE and TRUNCATE on alarm_event are refused by the
                              trigger, and the row count does not move. INSTRUMENT
                              SELF-TEST first: inside a transaction that is rolled
                              back, the two triggers are dropped and the same
                              DELETE / TRUNCATE succeed. A refusal test that cannot
                              be shown to fail proves nothing (the `ping` lesson).
    phase "shelve"            acts as the operator: loads the saved state, SHELVES the
                              live Vibration HI_HI for 1 minute through the real
                              AlarmFeed / engine / store code, and commits event and
                              state in one transaction, exactly as the collector does.
    phase "after-restart"     after `docker restart vigilimen-collector`, during the
                              shelf: alarm_state still SHELVED with the SAME
                              shelved_until, and NO second NORMAL->UNACK was written.
    phase "expiry"            once the shelf runs out (after the restart): exactly ONE
                              SHELVED->UNACK 'shelf expired', and the shelf is cleared.

    Extended scenarios (validate-durability.ps1 -Extended), each from a live alarm:
      A  restart AFTER the shelf expired: first cycle after the restart gives one
         SHELVED->UNACK ("shelf expired"), not zero and not two;
      B  the condition CLEARS during the shelf, with a restart in the middle: still
         SHELVED, in_condition False, and at expiry SHELVED->NORMAL (no UNACK);
      C  ACKNOWLEDGED, then shelved, restart, expiry: the acknowledgement is not
         silently kept, the alarm comes back UNACK (re-annunciation).
    The extra phases are `faults-off` (writes the Fault* tags to 0 over OPC UA, like
    FF-26 "Clear all faults") and the options --ack-first, --expect-events,
    --expect-state, --expect-in-condition, --settle.

WHERE THE EXPECTED RESULT COMES FROM
    The requirement is ADR-019 ("a restart does not rewrite the alarm history") and
    ISA-18.2 (a shelf is time-limited and its expiry returns an alarm that is still
    true to UNACK). The engine, the store and this test share an author, so a green
    run shows agreement with the requirement as written, not an independent proof.

WHAT THIS DOES NOT PROVE
    * It does not stop the table OWNER: the self-test shows the owner can drop the
      trigger (ADR-019 records this; separate write/administer roles are an S8 item).
    * DELETE with a WHERE that matches no row is not refused (no row, no trigger
      call): that is correct, and is not tested as a defect.
    * The shelve is made by this script, not through an operator screen: the stack
      has none yet. It uses the collector's own AlarmFeed, so the write path is real.
    * The live collector keeps its older in-memory state until it restarts; that is
      the point of the test, not a defect of it.

    docker cp scripts\\ff28_alarm_durability.py vigilimen-collector:/tmp/ff28.py
    docker exec vigilimen-collector python /tmp/ff28.py --phase tamper
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/opt/vigilimen")          # collector.py, engine.py, store.py in the image

import psycopg                                 # noqa: E402

DSN = os.environ.get("VIGILIMEN_PGDSN", "")
OPCUA_URL = os.environ.get("VIGILIMEN_OPCUA_URL", "opc.tcp://gateway:4840/vigilimen/conv001/")
OPCUA_USER = os.environ.get("VIGILIMEN_OPCUA_USER", "engineer")
OPCUA_PASSWORD = os.environ.get("VIGILIMEN_OPCUA_PASSWORD", "")
FAULTS = ["FaultBearingWear", "FaultBeltSlip", "FaultMisalignment", "FaultIdlerSeizure", "FaultVibrationSpike"]
VIB, COND = "CONV001.Vibration_mms", "HI_HI"

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((bool(ok), name, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""), flush=True)


def q(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
    conn.commit()
    return rows


def count(conn) -> int:
    return q(conn, "SELECT count(*) FROM alarm_event")[0][0]


def last_event_id(conn) -> int:
    return q(conn, "SELECT coalesce(max(event_id), 0) FROM alarm_event")[0][0]


def events_since(conn, base: int):
    return q(conn, "SELECT event_id, from_state, to_state, actor, note FROM alarm_event "
                   "WHERE tag_id = %s AND condition = %s AND event_id > %s ORDER BY event_id",
             (VIB, COND, base))


def state_row(conn):
    r = q(conn, "SELECT state, in_condition, shelved_until FROM alarm_state WHERE tag_id = %s AND condition = %s",
          (VIB, COND))
    return r[0] if r else None


def refused(conn, sql: str) -> tuple[bool, str]:
    """True if PostgreSQL raised the trigger's exception. Always rolls back."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.rollback()
        return False, "statement SUCCEEDED"
    except psycopg.errors.RaiseException as e:
        conn.rollback()
        return True, str(e).splitlines()[0]
    except Exception as e:                      # a different error is not a refusal by the trigger
        conn.rollback()
        return False, f"{type(e).__name__}: {str(e).splitlines()[0]}"


# --------------------------------------------------------------------------- tamper

def phase_tamper(conn) -> int:
    print("\nphase tamper — DELETE and TRUNCATE on alarm_event", flush=True)
    n0 = count(conn)
    check("there is history to protect (alarm_event is not empty)", n0 > 0,
          f"{n0} rows; run the alarm phase of FF-26 first" if n0 == 0 else f"{n0} rows")
    if n0 == 0:
        return 1

    trg = q(conn, "SELECT tgname, tgenabled FROM pg_trigger WHERE tgrelid = 'alarm_event'::regclass AND NOT tgisinternal")
    names = {t[0]: t[1] for t in trg}
    check("both triggers exist and are enabled",
          names.get("alarm_event_no_change") == "O" and names.get("alarm_event_no_truncate") == "O", str(names))

    # --- instrument self-test: the same statements MUST succeed without the triggers
    print("  -- instrument self-test (rolled back) --", flush=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout = '5s'")
            cur.execute("DROP TRIGGER alarm_event_no_change ON alarm_event")
            cur.execute("DROP TRIGGER alarm_event_no_truncate ON alarm_event")
            cur.execute("DELETE FROM alarm_event WHERE event_id = (SELECT min(event_id) FROM alarm_event)")
            deleted = cur.rowcount
            cur.execute("TRUNCATE alarm_event")
            cur.execute("SELECT count(*) FROM alarm_event")
            inside = cur.fetchone()[0]
        conn.rollback()
        check("self-test: without the triggers DELETE and TRUNCATE do succeed (the test CAN fail)",
              deleted == 1 and inside == 0, f"deleted={deleted}, rows left inside the transaction={inside}")
        check("self-test: the owner can drop the trigger (known limit, ADR-019)", True,
              "so the trigger stops accidents, not the table owner")
    except Exception as e:
        conn.rollback()
        check("self-test: without the triggers DELETE and TRUNCATE do succeed (the test CAN fail)", False,
              f"{type(e).__name__}: {str(e).splitlines()[0]} — the instrument is NOT validated, do not trust the next lines")
    check("self-test left the history untouched (rolled back)", count(conn) == n0, f"{count(conn)} rows")

    # --- the real refusals
    print("  -- the real statements --", flush=True)
    cases = [
        ("DELETE one row",            "DELETE FROM alarm_event WHERE event_id = (SELECT min(event_id) FROM alarm_event)"),
        ("DELETE every row",          "DELETE FROM alarm_event"),
        ("TRUNCATE",                  "TRUNCATE alarm_event"),
        ("TRUNCATE RESTART IDENTITY CASCADE", "TRUNCATE alarm_event RESTART IDENTITY CASCADE"),
        ("UPDATE (control: FF-26 saw this refused)", "UPDATE alarm_event SET note = note"),
    ]
    for name, sql in cases:
        ok, why = refused(conn, sql)
        check(f"{name}: refused by the trigger", ok, why)
    n1 = count(conn)
    check("row count unchanged after all of the above", n1 == n0, f"{n0} -> {n1}")
    return 0 if all(r[0] for r in results) else 1


# --------------------------------------------------------------------------- shelve

def phase_shelve(conn, args) -> int:
    print("\nphase shelve — the operator shelves the live Vibration HI_HI for 1 minute"
          + (" (after acknowledging it)" if args.ack_first else ""), flush=True)
    import collector                                   # the image's own write path
    feed = collector.AlarmFeed(persist=True)
    feed.restore(conn)
    a = feed.engine.get(VIB, COND)
    live = a.state.value == "UNACK" and a.in_condition
    check("the alarm is live and UNACK (in condition) before the operator acts", live,
          f"state={a.state.value} in_condition={a.in_condition}; run FF-26 --phase alarm first" if not live else a.state.value)
    if not live:
        return 1
    base = last_event_id(conn)
    if args.ack_first:
        feed.engine.acknowledge(VIB, COND, "ff28-operator")
    feed.engine.shelve(VIB, COND, "ff28-operator", minutes=args.minutes)

    alarm_rows, mark = feed.pending()
    dirty = feed.dirty()
    with conn.cursor() as cur:                         # the same statements as collector.cycle()
        cur.executemany(collector.INSERT_ALARM, alarm_rows)
        collector.store.save(cur, dirty, datetime.now(timezone.utc))
    conn.commit()
    feed.committed(mark, dirty)

    seq = _seq(events_since(conn, base))
    want = ["UNACK>ACKED", "ACKED>SHELVED"] if args.ack_first else ["UNACK>SHELVED"]
    check("events written by the operator, actor ff28-operator", seq == want
          and all(e[3] == "ff28-operator" for e in events_since(conn, base)), str(seq))
    st = state_row(conn)
    check("alarm_state is SHELVED with an expiry", bool(st) and st[0] == "SHELVED" and st[2] is not None, str(st))
    if st and st[2]:
        print(f"since-event-id {base}")
        print(f"shelved-until {st[2].astimezone(timezone.utc).isoformat()}")
    return 0 if all(r[0] for r in results) else 1


# --------------------------------------------------------------------------- faults off

async def _faults_off() -> None:
    from asyncua import Client
    client = Client(OPCUA_URL, timeout=10)
    client.set_user(OPCUA_USER)
    client.set_password(OPCUA_PASSWORD)
    await client.connect()
    try:
        ns = await client.get_namespace_index("urn:vigilimen:plant:conv001")
        root = client.nodes.objects
        for n in ("Enterprise", "PilbaraSite", "ProcessingArea", "ConveyingCell", "CONV001"):
            root = await root.get_child(f"{ns}:{n}")
        for f in FAULTS:
            await (await root.get_child(f"{ns}:{f}")).write_value(0.0)
    finally:
        await client.disconnect()


def phase_faults_off(conn, args) -> int:
    print("\nphase faults-off — Clear all faults while the alarm is SHELVED", flush=True)
    if not OPCUA_PASSWORD:
        print("FF-28: VIGILIMEN_OPCUA_PASSWORD is not set (docker exec -e ...)", file=sys.stderr)
        return 2
    asyncio.run(_faults_off())
    time.sleep(args.settle if args.settle else 5.0)       # a few collector cycles
    st = state_row(conn)
    check("the shelved alarm stays SHELVED while the condition clears", bool(st) and st[0] == "SHELVED", str(st))
    check("alarm_state records in_condition = False", bool(st) and st[1] is False, str(st))
    seq = _seq(events_since(conn, args.since_event_id))
    check("no event was written for the condition clearing (hidden from the list, and today also from this log)",
          seq == ["UNACK>SHELVED"], str(seq))
    return 0 if all(r[0] for r in results) else 1


# --------------------------------------------------------------------------- after restart

def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def _seq(ev) -> list[str]:
    return [f"{e[1]}>{e[2]}" for e in ev]


def _want(args, default: str) -> list[str]:
    return [x for x in (args.expect_events or default).split(",") if x]


def phase_after_restart(conn, args) -> int:
    print("\nphase after-restart — restart happened DURING the shelf", flush=True)
    until = _parse(args.shelved_until)
    now = datetime.now(timezone.utc)
    check("the shelf had not expired when we looked (else the test says nothing)", now < until,
          f"{(until - now).total_seconds():+.0f} s left" if now < until else "TOO SLOW: re-run, restart sooner")
    if now >= until:
        return 1
    time.sleep(2.0)                                    # let at least two collector cycles run
    st = state_row(conn)
    check("alarm_state is still SHELVED", bool(st) and st[0] == "SHELVED", str(st))
    check("shelved_until is exactly what was saved", bool(st) and st[2] is not None and st[2].astimezone(timezone.utc) == until,
          f"saved {until.isoformat()}  now {st[2].isoformat() if st and st[2] else None}")
    want_cond = args.expect_in_condition != "false"
    check(f"in_condition is {want_cond} as it was before the restart", bool(st) and st[1] is want_cond, str(st))
    seq = _seq(events_since(conn, args.since_event_id))
    want = _want(args, "UNACK>SHELVED")
    check(f"history for this alarm since the start is exactly {want}: no second NORMAL->UNACK", seq == want, str(seq))
    return 0 if all(r[0] for r in results) else 1


# --------------------------------------------------------------------------- expiry

def phase_expiry(conn, args) -> int:
    print("\nphase expiry — the shelf runs out AFTER the restart(s)", flush=True)
    until = _parse(args.shelved_until)
    wait = (until - datetime.now(timezone.utc)).total_seconds() + 6.0
    if args.settle:
        wait = max(wait, args.settle)
    if wait > 0:
        print(f"  waiting {wait:.0f} s", flush=True)
        time.sleep(wait)
    ev = events_since(conn, args.since_event_id)
    want = _want(args, "UNACK>SHELVED,SHELVED>UNACK")
    check(f"history is exactly {want}", _seq(ev) == want, str(_seq(ev)))
    check("the last event says 'shelf expired'", bool(ev) and ev[-1][4] == "shelf expired", str(ev[-1][4] if ev else None))
    st = state_row(conn)
    want_state = args.expect_state or "UNACK"
    want_cond = args.expect_in_condition != "false"
    check(f"alarm_state is {want_state}, in_condition {want_cond}, shelf cleared",
          bool(st) and st[0] == want_state and st[1] is want_cond and st[2] is None, str(st))
    return 0 if all(r[0] for r in results) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["tamper", "shelve", "faults-off", "after-restart", "expiry"], required=True)
    ap.add_argument("--ack-first", action="store_true")
    ap.add_argument("--expect-events", default="", help="comma list of from>to, oldest first")
    ap.add_argument("--expect-state", default="")
    ap.add_argument("--expect-in-condition", default="true")
    ap.add_argument("--settle", type=float, default=0.0)
    ap.add_argument("--minutes", type=int, default=1)
    ap.add_argument("--since-event-id", type=int, default=0)
    ap.add_argument("--shelved-until", default="")
    args = ap.parse_args()
    if not DSN:
        print("FF-28: VIGILIMEN_PGDSN is not set (run inside vigilimen-collector)", file=sys.stderr)
        return 2
    if args.phase in ("after-restart", "expiry") and not args.shelved_until:
        print("FF-28: --shelved-until is required (printed by the shelve phase)", file=sys.stderr)
        return 2

    print(f"FF-28 — alarm durability (phase={args.phase})")
    conn = psycopg.connect(DSN)
    try:
        rc = {"tamper": lambda: phase_tamper(conn),
              "shelve": lambda: phase_shelve(conn, args),
              "faults-off": lambda: phase_faults_off(conn, args),
              "after-restart": lambda: phase_after_restart(conn, args),
              "expiry": lambda: phase_expiry(conn, args)}[args.phase]()
    finally:
        conn.close()
    failed = [r for r in results if not r[0]]
    print(f"\n{len(results)} checks, {len(failed)} failed")
    print("FF-28 pass." if not failed and rc == 0 else "FF-28 FAIL: write symptom, cause, fix in the log BEFORE changing anything.")
    return 1 if failed or rc else 0


if __name__ == "__main__":
    sys.exit(main())
