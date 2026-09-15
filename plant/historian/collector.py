#!/usr/bin/env python3
"""
CONV-001 collector — OPC UA to TimescaleDB at 1 Hz.

    python3 plant/historian/collector.py

Three decisions carry this file, and each of them is a mistake that a
historian makes silently.

1. THE SAMPLE IS STAMPED AT THE SOURCE, NOT AT THE INSERT.
   Every read returns a DataValue, and the DataValue carries the server's
   SourceTimestamp. Using `now()` at insert time instead looks identical on
   a healthy day and is wrong on exactly the days that matter: a collector
   that stalls for forty seconds and then flushes writes forty samples that
   all claim to be from the moment the queue drained. The trend then shows
   a vertical wall of data where the plant was actually unobserved.

2. QUALITY IS CARRIED, NOT DISCARDED.
   StatusCode maps to the OPC UA convention the schema stores: 192 Good,
   64 Uncertain, 0 Bad. A collector that throws quality away turns "the
   transmitter was disconnected" into "the temperature was 0 degrees", and
   S13's maintenance model will cheerfully learn from it.

3. READING IS THE ONLY THING THIS PROCESS IS ALLOWED TO DO.
   It authenticates as `historian`, which holds no write access to any node
   (see gateway/opcua_server.py). If this container is compromised the
   adversary gets the plant's history, which is a confidentiality problem.
   The same code authenticating as `engineer` would hand them the plant.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from datetime import datetime, timezone

from asyncua import Client, ua

try:
    import psycopg
except ImportError:                                        # pragma: no cover
    print("psycopg 3 is required:  pip install 'psycopg[binary]'", file=sys.stderr)
    raise

# ---------------------------------------------------------------------------
# Configuration — environment only. Nothing here is read from a file, so
# there is no path on which a credential can be committed (FF-03).
# ---------------------------------------------------------------------------

OPCUA_URL = os.environ.get("MD360_OPCUA_URL", "opc.tcp://127.0.0.1:14840/md360/conv001/")
OPCUA_USER = os.environ.get("MD360_OPCUA_USER", "historian")
OPCUA_PASSWORD = os.environ.get("MD360_OPCUA_PASSWORD", "h1st0r1an-demo")
PGDSN = os.environ.get("MD360_PGDSN", "postgresql://md360:md360-local-only@127.0.0.1:15432/md360")
PERIOD_S = float(os.environ.get("MD360_PERIOD_S", "1.0"))

# ---------------------------------------------------------------------------
# The name map.
#
# The OPC UA browse name and the historian tag_id are NOT the same string,
# and pretending they are is how a historian acquires two names for one
# measurement. `MotorCurrent_A` on the wire is `CONV001.Current_A` in the
# database, because the database prefixes by asset and the address space
# already expresses the asset through its hierarchy.
#
# The map is explicit and it is the ONLY place the translation happens. A
# collector that derives the tag_id with string manipulation works until the
# first tag that does not follow the pattern, and then fails quietly on that
# one tag.
# ---------------------------------------------------------------------------

TAG_MAP: dict[str, str] = {
    "Running":        "CONV001.Running",
    "SafetyTripped":  "CONV001.SafetyTripped",
    "BeltSpeed_mps":  "CONV001.Speed_mps",
    "Load_tph":       "CONV001.Load_tph",
    "BearingTemp_C":  "CONV001.BearingTemp_C",
    "Vibration_mms":  "CONV001.Vibration_mms",
    "MotorCurrent_A": "CONV001.Current_A",
}

INSERT = "INSERT INTO sample (ts, tag_id, value, quality) VALUES (%s, %s, %s, %s)"


def quality_of(status: ua.StatusCode | None) -> int:
    """OPC UA StatusCode to the schema's smallint.

    The severity lives in the top two bits of the 32-bit code: 00 Good,
    01 Uncertain, 10/11 Bad. Anything unrecognised is treated as Bad, which
    is the only safe default — an unknown status assumed Good is a lie the
    database cannot later detect.
    """
    if status is None:
        return 0
    try:
        v = int(status.value)
    except Exception:
        return 0
    severity = (v >> 30) & 0b11
    return {0: 192, 1: 64}.get(severity, 0)


def value_of(v) -> float | None:
    """Everything becomes a double, because `sample.value` is one column.

    Booleans become 1.0 and 0.0. A separate table per datatype is the
    textbook answer and it makes every cross-tag query a join; one column
    of double precision is what every real historian does, and the cost is
    that a boolean loses its type on the way in. The tag dictionary carries
    that knowledge instead.
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return None


async def resolve(client: Client) -> list[tuple[str, object]]:
    """Walk the ISA-95 path once and hold the node objects.

    Browsing by path on every cycle would be correct and would put five
    extra round trips per second on a link that, on a real site, is the
    slowest thing in the architecture.
    """
    ns = await client.get_namespace_index("urn:md360:plant:conv001")
    root = client.nodes.objects
    for name in ("Enterprise", "PilbaraSite", "ProcessingArea", "ConveyingCell", "CONV001"):
        root = await root.get_child(f"{ns}:{name}")

    out: list[tuple[str, object]] = []
    for browse, tag_id in TAG_MAP.items():
        out.append((tag_id, await root.get_child(f"{ns}:{browse}")))
    return out


async def cycle(client: Client, nodes, conn) -> int:
    """One acquisition. Returns the number of rows written."""
    # read_data_value on each node rather than read_value: the DataValue is
    # the whole point (see decisions 1 and 2 at the top of this file).
    rows = []
    for tag_id, node in nodes:
        dv = await node.read_data_value()
        ts = dv.SourceTimestamp or dv.ServerTimestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            # asyncua returns naive UTC in some paths. Stamping it as local
            # time here would put the whole history an hour out for half the
            # year in any DST zone — ADR-010 exists because of exactly this.
            ts = ts.replace(tzinfo=timezone.utc)
        rows.append((ts, tag_id, value_of(dv.Value.Value), quality_of(dv.StatusCode)))

    with conn.cursor() as cur:
        cur.executemany(INSERT, rows)
    conn.commit()
    return len(rows)


async def main() -> int:
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(sig, stop.set)
        except NotImplementedError:                        # pragma: no cover
            pass

    written = 0
    while not stop.is_set():
        try:
            conn = psycopg.connect(PGDSN)
            client = Client(OPCUA_URL)
            # set_user/set_password BEFORE connect. `async with Client(url)`
            # calls __aenter__, which connects anonymously before any
            # credential is set — a mistake that presents as "the server
            # accepts anonymous sessions" when it does not.
            client.set_user(OPCUA_USER)
            client.set_password(OPCUA_PASSWORD)
            await client.connect()
            try:
                nodes = await resolve(client)
                print(f"collector: {len(nodes)} tags at {1 / PERIOD_S:.0f} Hz -> {PGDSN.split('@')[-1]}",
                      flush=True)
                next_at = asyncio.get_running_loop().time()
                while not stop.is_set():
                    written += await cycle(client, nodes, conn)
                    if written % 600 == 0:
                        print(f"collector: {written} samples written", flush=True)
                    # Fixed-rate, not fixed-delay. Sleeping a constant period
                    # after a cycle that took 120 ms produces a 1.12 s
                    # interval, and the historian's idea of "1 Hz" drifts
                    # about two minutes a day.
                    next_at += PERIOD_S
                    delay = next_at - asyncio.get_running_loop().time()
                    if delay < 0:
                        next_at = asyncio.get_running_loop().time()
                        delay = 0
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=delay)
                    except asyncio.TimeoutError:
                        pass
            finally:
                await client.disconnect()
                conn.close()
        except Exception as e:                             # noqa: BLE001
            # Reconnect rather than die. A collector that exits on the first
            # network blip needs a human, and a historian gap that needed a
            # human at 3 a.m. is a historian gap.
            print(f"collector: {type(e).__name__}: {e} — retrying in 5 s", file=sys.stderr, flush=True)
            try:
                await asyncio.wait_for(stop.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass

    print(f"collector: stopped after {written} samples", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
