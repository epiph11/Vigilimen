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
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/opt/vigilimen")          # collector.py, engine.py, store.py in the image

import psycopg                                 # noqa: E402

DSN = os.environ.get("VIGILIMEN_PGDSN", "")
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
    print("\nphase shelve — the operator shelves the live Vibration HI_HI for 1 minute", flush=True)
    import collector                                   # the image's own write path
    feed = collector.AlarmFeed(persist=True)
    feed.restore(conn)
    a = feed.engine.get(VIB, COND)
    live = a.state.value in ("UNACK", "ACKED") and a.in_condition
    check("the alarm is live (UNACK or ACKED, in condition) before shelving", live,
          f"state={a.state.value} in_condition={a.in_condition}; run FF-26 --phase alarm first" if not live else a.state.value)
    if not live:
        return 1
    base = last_event_id(conn)
    feed.engine.shelve(VIB, COND, "ff28-operator", minutes=args.minutes)

    alarm_rows, mark = feed.pending()
    dirty = feed.dirty()
    with conn.cursor() as cur:                         # the same statements as collector.cycle()
        cur.executemany(collector.INSERT_ALARM, alarm_rows)
        collector.store.save(cur, dirty, datetime.now(timezone.utc))
    conn.commit()
    feed.committed(mark, dirty)

    ev = events_since(conn, base)
    st = state_row(conn)
    check("one event written: SHELVED, actor ff28-operator", len(ev) == 1 and ev[0][2] == "SHELVED" and ev[0][3] == "ff28-operator", str(ev))
    check("alarm_state is SHELVED with an expiry", bool(st) and st[0] == "SHELVED" and st[2] is not None, str(st))
    if st and st[2]:
        print(f"since-event-id {base}")
        print(f"shelved-until {st[2].astimezone(timezone.utc).isoformat()}")
    return 0 if all(r[0] for r in results) else 1


# --------------------------------------------------------------------------- after restart

def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s).astimezone(timezone.utc)


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
    ev = events_since(conn, args.since_event_id)
    to = [e[2] for e in ev]
    check("history for this alarm since the shelve is exactly [SHELVED]: no second NORMAL->UNACK", to == ["SHELVED"], str(to))
    return 0 if all(r[0] for r in results) else 1


# --------------------------------------------------------------------------- expiry

def phase_expiry(conn, args) -> int:
    print("\nphase expiry — the shelf runs out AFTER the restart", flush=True)
    until = _parse(args.shelved_until)
    wait = (until - datetime.now(timezone.utc)).total_seconds() + 6.0
    if wait > 0:
        print(f"  waiting {wait:.0f} s for the shelf to end", flush=True)
        time.sleep(wait)
    ev = events_since(conn, args.since_event_id)
    seq = [(e[1], e[2]) for e in ev]
    check("history is SHELVED then exactly one SHELVED->UNACK", seq == [("UNACK", "SHELVED"), ("SHELVED", "UNACK")], str(seq))
    check("the expiry event says 'shelf expired'", bool(ev) and ev[-1][4] == "shelf expired", str(ev[-1][4] if ev else None))
    st = state_row(conn)
    check("alarm_state is UNACK, in condition, shelf cleared", bool(st) and st[0] == "UNACK" and st[1] is True and st[2] is None, str(st))
    return 0 if all(r[0] for r in results) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["tamper", "shelve", "after-restart", "expiry"], required=True)
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
