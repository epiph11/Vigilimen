#!/usr/bin/env python3
"""
FF-25 — a collector restart does not rewrite the alarm history (ADR-019).

Before this, the alarm engine lived in memory. Restart the collector while an
operator had ACKNOWLEDGED an alarm that was still true, and the next sample
raised it again as a brand-new UNACK: the acknowledgement vanished and the
history gained a second NORMAL->UNACK for one incident. An alarm record that
changes when a container restarts is not a record.

Each case below is a way persistence fails while looking like it works.

  A. the engine round-trips its state (snapshot / restore), with no events;
  B. the collector saves state in the SAME transaction as the events, loses no
     event when a commit fails, and is OFF unless asked;
  C. schema.sql and the migration describe the same objects.

WHAT THIS DOES NOT PROVE
  That PostgreSQL accepts the SQL, that the trigger fires, or that a real
  `docker restart vigilimen-collector` behaves. FF-26 (run in Docker) does.

    python3 scripts/ff25_alarm_persistence.py
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("plant/alarms", "plant/historian"):
    sys.path.insert(0, str(ROOT / sub))

# The collector imports asyncua and psycopg at module level. Neither is needed
# to test its alarm wiring, and the CI image has neither, so stand-ins go in first.
_ua = types.SimpleNamespace(StatusCode=object)
sys.modules.setdefault("asyncua", types.SimpleNamespace(Client=object, ua=_ua))
class _UndefinedTable(Exception): ...
_psy = types.ModuleType("psycopg")
_psy.errors = types.SimpleNamespace(UndefinedTable=_UndefinedTable)
_psy.connect = lambda *a, **k: None
sys.modules.setdefault("psycopg", _psy)

from engine import State, build_conv001      # noqa: E402
import store                                 # noqa: E402
import collector                             # noqa: E402

results: list[tuple[bool, str, str]] = []


def check(name: str, cond: bool, why: str) -> None:
    results.append((bool(cond), name, why))


T0 = datetime(2026, 10, 25, 4, 0, 0, tzinfo=timezone.utc)
at = lambda s: T0 + timedelta(seconds=s)          # noqa: E731
VIB, TEMP = "CONV001.Vibration_mms", "CONV001.BearingTemp_C"


def restart(engine):
    """A new process: fresh engine, state restored from what the old one saved."""
    rows = [dict(tag_id=t, condition=c, **v) for (t, c), v in engine.snapshot().items()]
    fresh = build_conv001()
    fresh.restore(rows)
    return fresh


# ---------------------------------------------------------------------------
# A. the engine
# ---------------------------------------------------------------------------

e = build_conv001()
e.evaluate(VIB, 8.0, at(0))
e.acknowledge(VIB, "HI_HI", "operator.chen", at(1))
n_before = len(e.events)
e2 = restart(e)
e2.evaluate(VIB, 8.0, at(2))
check("restart while ACKED and still in alarm: no new event, still ACKED",
      e2.get(VIB, "HI_HI").state is State.ACKED and len(e2.events) == 0,
      "the acknowledgement is the operator's work; a restart must not undo it")
e2.evaluate(VIB, 2.0, at(3))
check("...and it returns to NORMAL when the condition clears",
      e2.get(VIB, "HI_HI").state is State.NORMAL, "state restored must still be live state")

ctl = build_conv001()                                # CONTROL: the old behaviour, no restore
ctl.evaluate(VIB, 8.0, at(2))
check("control: WITHOUT restore the same restart re-raises a fresh UNACK (this is the bug)",
      ctl.get(VIB, "HI_HI").state is State.UNACK and len(ctl.events) == 1,
      "if this does not fail the way it used to, the cases above prove nothing")

e = build_conv001()
e.evaluate(VIB, 8.0, at(0))
e2 = restart(e)
e2.evaluate(VIB, 8.0, at(2))
check("restart while UNACK and still in alarm: no duplicate NORMAL->UNACK",
      e2.get(VIB, "HI_HI").state is State.UNACK and len(e2.events) == 0,
      "one incident, one raise in the history")

e = build_conv001()
e.evaluate(VIB, 8.0, at(0)); e.evaluate(VIB, 2.0, at(5))
assert e.get(VIB, "HI_HI").state is State.RTN_UNACK
e2 = restart(e)
e2.evaluate(VIB, 2.0, at(6))
still = e2.get(VIB, "HI_HI").state is State.RTN_UNACK
e2.acknowledge(VIB, "HI_HI", "operator.chen", at(7))
check("RTN_UNACK survives a restart and an acknowledge still clears it",
      still and e2.get(VIB, "HI_HI").state is State.NORMAL,
      "RTN_UNACK is 'it cleared and nobody saw it': the state a boolean erases, and a restart must not")

e = build_conv001()
e.evaluate(TEMP, 90.0, at(0)); e.evaluate(TEMP, 90.0, at(6))          # 6 s into a 10 s on-delay
assert e.get(TEMP, "HI").state is State.NORMAL
e2 = restart(e)
e2.evaluate(TEMP, 90.0, at(11))                                       # 11 s after the FIRST sample
check("an on-delay already running is not restarted from zero",
      e2.get(TEMP, "HI").state is State.UNACK,
      "restarting the clock turns a restart into a free 10 s delay on every alarm")

e = build_conv001()
e.evaluate(VIB, 8.0, at(0))
e.shelve(VIB, "HI_HI", "operator.chen", 5, at(1))
e2 = restart(e)
shelved = e2.get(VIB, "HI_HI").state is State.SHELVED and e2.get(VIB, "HI_HI").shelved_until == at(1) + timedelta(minutes=5)
e2.evaluate(VIB, 8.0, at(2))
still_shelved = e2.get(VIB, "HI_HI").state is State.SHELVED
e2.unshelve_expired(at(1 + 301))
check("a shelf keeps its expiry across a restart and still expires on time",
      shelved and still_shelved and e2.get(VIB, "HI_HI").state is State.UNACK,
      "a restart that forgets the shelf un-hides alarms; one that forgets the expiry hides them forever")

e = build_conv001()
bad = e.restore([dict(tag_id="CONV001.Nope", condition="HI", state="UNACK", in_condition=True),
                 dict(tag_id=VIB, condition="HI_HI", state="MARTIAN", in_condition=True)])
check("rows for unknown alarms or unknown states are ignored, not fatal",
      bad == 0 and all(a.state is State.NORMAL for a in e.alarms.values()) and not e.events,
      "a rollback or a rename must not crash the collector at start-up")

# ---------------------------------------------------------------------------
# B. the collector
# ---------------------------------------------------------------------------

class Cur:
    def __init__(self, db): self.db = db
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params=()): self.db.log.append(("execute", sql.split()[0], sql, params))
    def executemany(self, sql, rows):  self.db.log.append(("executemany", sql.split()[0], sql, list(rows)))
    def fetchall(self): return self.db.rows


class Conn:
    def __init__(self, rows=None, fail_commit_times=0, missing_table=False):
        self.log, self.rows = [], rows or []
        self.commits, self.rollbacks = 0, 0
        self.fail_commit_times, self.missing_table = fail_commit_times, missing_table
    def cursor(self):
        if self.missing_table:
            raise _UndefinedTable()
        return Cur(self)
    def commit(self):
        if self.fail_commit_times > 0:
            self.fail_commit_times -= 1
            raise OSError("commit failed")
        self.commits += 1
    def rollback(self): self.rollbacks += 1


class DV:
    def __init__(self, v, ts): 
        self.Value = types.SimpleNamespace(Value=v)
        self.SourceTimestamp, self.ServerTimestamp = ts, ts
        self.StatusCode = types.SimpleNamespace(value=0)


class Node:
    def __init__(self, v): self.v = v
    async def read_data_value(self): return DV(self.v, self.ts)


import asyncio


def tick(feed, conn, vib, ts):
    nodes = [("CONV001.Running", Node(1.0)), ("CONV001.Speed_mps", Node(2.5)),
             (VIB, Node(vib))]
    for _, n in nodes:
        n.ts = ts
    return asyncio.run(collector.cycle(None, nodes, conn, feed))


check("persistence is OFF unless VIGILIMEN_ALARM_PERSIST says so",
      collector.PERSIST_ALARMS is False, "the default must work on a volume that has no alarm_state table")

feed = collector.AlarmFeed(persist=True)
db = Conn()
feed.restore(db)
db.log.clear(); db.commits = 0                      # measure the cycle, not the start-up read


def upserts(log):
    return [p for op, verb, sql, p in log if op == "execute" and verb == "INSERT" and "alarm_state" in sql]


tick(feed, db, 8.0, at(0))
events = [r for op, verb, sql, rows in db.log if op == "executemany" and "alarm_event" in sql for r in rows]
samples = [r for op, verb, sql, rows in db.log if op == "executemany" and "INTO sample" in sql for r in rows]
check("events and state are written in ONE transaction (one commit covers samples, events, state)",
      db.commits == 1 and len(samples) == 3 and len(events) == 1 and len(upserts(db.log)) >= 1,
      "after a crash they must both be there or both be absent")
check("the first cycle after a clean start saves only the alarms that changed (2 of 8: HI_HI raised, HI pending)",
      len(upserts(db.log)) == 2,
      "rewriting every row every second is write amplification nobody asked for")

n_log = len(db.log)
tick(feed, db, 8.0, at(1))
check("an unchanged second adds no state write",
      not upserts(db.log[n_log:]),
      "state is saved on change, not on a timer")

# a failed commit must not lose the event
feed = collector.AlarmFeed(persist=True)
feed.restore(Conn())
bad = Conn(fail_commit_times=1)
try:
    tick(feed, bad, 8.0, at(0))
    raised = False
except OSError:
    raised = True
good = Conn()
tick(feed, good, 8.0, at(1))
resent = [r for op, v, sql, rows in good.log if op == "executemany" and "alarm_event" in sql for r in rows]
check("a failed commit loses no event: the next cycle sends it again",
      raised and len(resent) == 1 and resent[0][2] == "HI_HI" and resent[0][4] == "UNACK",
      "pending() used to advance its mark BEFORE the insert, so a failed insert lost the transition for good")

# restore wiring
rows = [dict(tag_id=VIB, condition="HI_HI", state="ACKED", in_condition=True,
             shelved_until=None, pending_since=None)]
class LoadConn(Conn):
    def cursor(self):
        c = super().cursor(); return c
feed = collector.AlarmFeed(persist=True)
lc = LoadConn(rows=[(r["tag_id"], r["condition"], r["state"], r["in_condition"], None, None) for r in rows])
feed.restore(lc)
tick(feed, Conn(), 8.0, at(0))
check("collector restore + same sample: stays ACKED and writes no event",
      feed.engine.get(VIB, "HI_HI").state is State.ACKED and not feed.engine.events,
      "the end-to-end shape of the restart case in section A")

feed.restore(Conn(rows=[]))      # a second call must be a no-op (a reconnect must not reload)
check("restore runs once per process (a database reconnect must not reload stale state)",
      feed.engine.get(VIB, "HI_HI").state is State.ACKED, "the in-memory state is newer than the table")

try:
    collector.AlarmFeed(persist=True).restore(Conn(missing_table=True))
    msg = ""
except RuntimeError as ex:
    msg = str(ex)
check("a missing alarm_state table says how to fix it instead of crash-looping silently",
      "001_alarm_state.sql" in msg and "docker exec" in msg,
      "schema.sql only runs on an empty volume, so every existing volume hits this exactly once")

# ---------------------------------------------------------------------------
# C. schema and migration agree
# ---------------------------------------------------------------------------

schema = (ROOT / "plant/historian/schema.sql").read_text(encoding="utf-8")
mig = (ROOT / "plant/historian/migrations/001_alarm_state.sql").read_text(encoding="utf-8")
names = ["CREATE TABLE IF NOT EXISTS alarm_state", "alarm_event_append_only",
         "alarm_event_no_change", "alarm_event_no_truncate", "PRIMARY KEY (tag_id, condition)"]
check("schema.sql and the migration create the same objects",
      all(n in schema and n in mig for n in names), "a migration that drifts from the schema gives two kinds of database")
check("the migration is idempotent and ASCII-only",
      "IF NOT EXISTS" in mig and mig.count("DROP TRIGGER IF EXISTS") == 2 and mig.isascii(),
      "it is piped through PowerShell, which turns non-ASCII into '?', and it may be run twice")
check("the store's columns match the table's columns",
      all(c in schema.split("CREATE TABLE IF NOT EXISTS alarm_state")[1].split(");")[0]
          for c in ("tag_id", "condition", "state", "in_condition", "shelved_until", "pending_since", "updated_at")),
      "an UPSERT naming a column the table lacks fails at the first alarm, in production")

# ---------------------------------------------------------------------------

PASS, FAIL = "PASS", "FAIL"
print("FF-25 — a collector restart does not rewrite the alarm history\n")
width = max(len(n) for _, n, _ in results)
for ok, name, why in results:
    print(f"  {PASS if ok else FAIL}  {name.ljust(width)}")
    if not ok:
        print(f"        why this case exists: {why}")
failed = [r for r in results if not r[0]]
print(f"\n{len(results)} cases, {len(failed)} failed")
if failed:
    print("\nFF-25 FAIL.")
    sys.exit(1)
print("""
FF-25 pass.

What this proves: the engine round-trips its state, the collector writes events
and state together and loses nothing on a failed commit, and the schema and
migration agree. What it does not prove: that PostgreSQL accepts the SQL or that
the append-only trigger fires. FF-26 does, against the real database.""")
