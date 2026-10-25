#!/usr/bin/env python3
"""
Alarm state in the historian: load at start, save what changed (ADR-019).

WHY STATE AS WELL AS EVENTS
---------------------------
`alarm_event` already records every transition, so the state could be rebuilt
by replaying it. It is not, for three reasons:

  * shelved_until and the on-delay clock are not transitions. A shelf has an
    expiry that no event carries once the shelving event is old;
  * replay must stay correct across releases that change an alarm's definition,
    and a replay of five years of history is a start-up cost nobody budgeted;
  * the collector must restart in milliseconds and be provably idempotent.

So the engine's state is stored beside the history, and it is written in the
SAME TRANSACTION as the events it explains. After a crash the two are either
both there or both absent: never an UNACK row whose NORMAL->UNACK event was
lost, and never an event with no state change behind it.

No psycopg import here: the functions take a cursor, so FF-25 can test them
with a fake one, and the module loads wherever the engine does.
"""

from __future__ import annotations

from datetime import datetime

SELECT = ("SELECT tag_id, condition, state, in_condition, shelved_until, pending_since "
          "FROM alarm_state")

UPSERT = ("INSERT INTO alarm_state "
          "(tag_id, condition, state, in_condition, shelved_until, pending_since, updated_at) "
          "VALUES (%s, %s, %s, %s, %s, %s, %s) "
          "ON CONFLICT (tag_id, condition) DO UPDATE SET "
          "state = EXCLUDED.state, in_condition = EXCLUDED.in_condition, "
          "shelved_until = EXCLUDED.shelved_until, pending_since = EXCLUDED.pending_since, "
          "updated_at = EXCLUDED.updated_at")

MIGRATION_HINT = (
    "alarm_state table is missing. The schema runs only on an EMPTY volume. For an existing one:\n"
    "  Get-Content plant\\historian\\migrations\\001_alarm_state.sql | "
    "docker exec -i vigilimen-historian psql -U vigilimen -d vigilimen -v ON_ERROR_STOP=1")


def load(cur) -> list[dict]:
    cur.execute(SELECT)
    cols = ("tag_id", "condition", "state", "in_condition", "shelved_until", "pending_since")
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def changed(prev: dict, snap: dict) -> dict:
    """The entries of `snap` that differ from what was last saved."""
    return {k: v for k, v in snap.items() if prev.get(k) != v}


def save(cur, rows: dict, now: datetime) -> None:
    for (tag_id, condition), v in rows.items():
        cur.execute(UPSERT, (tag_id, condition, v["state"], v["in_condition"],
                             v["shelved_until"], v["pending_since"], now))
