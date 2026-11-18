"""The edge's message: topic and payload, schema version 1 (ADR-020 point 6).

Plain JSON, versioned, one value per message. `seq` is per edge and strictly increasing: the queue assigns it
(durable_queue.py), so that it survives a restart. `ts_src` is the source time stamped by the OPC UA server (UTC),
never the time of publication: a replay after a WAN cut must keep the moment the plant was observed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

SCHEMA = "1"
FIELDS = ("schema", "edge_id", "site", "asset", "tag", "value", "quality", "ts_src", "seq")
_PART = re.compile(r"^[A-Za-z0-9_.-]+$")          # no '/', no '+', no '#', no spaces: one topic level each


def topic(site: str, asset: str, tag: str) -> str:
    for name, part in (("site", site), ("asset", asset), ("tag", tag)):
        if not isinstance(part, str) or not _PART.match(part):
            raise ValueError(f"{name} {part!r} is not a valid topic level (letters, digits, _ . - only)")
    return f"vigilimen/v1/{site}/{asset}/{tag}"


def ts_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("ts_src must be timezone-aware: a naive time is a guess about the zone")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def payload(edge_id: str, site: str, asset: str, tag: str, value, quality: int, ts_src: datetime, seq: int) -> bytes:
    if quality not in (0, 64, 192):
        raise ValueError(f"quality {quality!r}: the schema carries 192 Good, 64 Uncertain, 0 Bad (as the historian does)")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        raise ValueError("seq is a positive integer")
    body = {"schema": SCHEMA, "edge_id": edge_id, "site": site, "asset": asset, "tag": tag, "value": value,
            "quality": quality, "ts_src": ts_utc(ts_src), "seq": seq}
    return json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
