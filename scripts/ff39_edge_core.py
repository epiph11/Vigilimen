#!/usr/bin/env python3
"""FF-39 - the edge's core, outside Docker: message schema, durable queue, reporting rules (ADR-020 points 5, 6, 7).

    python3 scripts/ff39_edge_core.py

Runs the properties on the real code, then again on 15 deliberately broken copies (mutations). A mutation that no
property catches means a property is too weak: the script fails. Needs only the standard library.
Not covered here (later FFs): MQTT acknowledgement per message, the live WAN cut (FF-29), the network of the edge.
"""
import json, os, sys, tempfile
from datetime import datetime, timezone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "plant", "edge"))
import message as M                                   # noqa: E402
from durable_queue import EdgeQueue                   # noqa: E402
from reporter import Reporter, Spec, UnknownTag       # noqa: E402

T0 = datetime(2026, 11, 18, 9, 0, 0, tzinfo=timezone.utc)


def suite(Q, R):
    """Return the list of failed property names."""
    bad = []
    def check(name, ok):
        if not ok:
            bad.append(name)

    def mk(q, kind, tag="Speed_mps"):
        return q.enqueue(kind, M.topic("mine1", "CONV-001", tag),
                         lambda s: M.payload("edge1", "mine1", "CONV-001", tag, 1.0, 192, T0, s))
    d = tempfile.mkdtemp()
    p = os.path.join(d, "q.db")
    drops = []
    q = Q(p, max_items=5, on_drop=lambda s, k: drops.append((s, k)))
    # sequence and payload
    seqs = [mk(q, "baseline") for _ in range(3)]
    check("seq starts at 1 and increases by one", seqs == [1, 2, 3])
    rows = q.peek()
    check("peek returns seq order", [r[0] for r in rows] == [1, 2, 3])
    check("the payload carries the queue's seq", all(json.loads(r[2])["seq"] == r[0] for r in rows))
    check("ack removes the message, a second ack says so", q.ack(1) is True and q.ack(1) is False)
    q.ack(2); q.ack(3)
    check("the queue is empty after acks", q.stats()["depth"] == 0)
    check("seq is never reused after the queue empties", mk(q, "baseline") == 4)
    # durability
    q.close()
    q = Q(p, max_items=5, on_drop=lambda s, k: drops.append((s, k)))
    check("an unacknowledged message survives a restart", [r[0] for r in q.peek()] == [4])
    check("seq continues after a restart", mk(q, "baseline") == 5)
    check("journal mode is WAL and synchronous is FULL", q.pragmas() == ("wal", 2))
    # bound and drops
    q.ack(4); q.ack(5)
    for _ in range(8):
        mk(q, "baseline")
    st = q.stats()
    check("the queue never exceeds its bound", st["depth"] == 5)
    check("every drop is counted", st["dropped_baseline"] == 3 and st["dropped_exception"] == 0)
    check("every drop is reported to on_drop", len(drops) == 3 and all(k == "baseline" for _, k in drops))
    check("the oldest are the ones dropped", [r[0] for r in q.peek()] == [9, 10, 11, 12, 13])
    q.close()
    q = Q(p, max_items=5)
    check("the drop counter survives a restart", q.stats()["dropped_baseline"] == 3)
    for r in q.peek():
        q.ack(r[0])
    mk(q, "exception"); mk(q, "baseline"); mk(q, "baseline"); mk(q, "baseline"); mk(q, "baseline")
    mk(q, "baseline")
    kinds = [r[3] for r in q.peek()]
    check("an exception outlives older baselines", kinds[0] == "exception" and q.stats()["dropped_exception"] == 0)
    q.close()
    q = Q(os.path.join(d, "x.db"), max_items=2)
    for _ in range(4):
        mk(q, "exception")
    check("with only exceptions the oldest exception goes, and is counted", q.stats()["dropped_exception"] == 2 and q.stats()["depth"] == 2)
    q.close()
    # reporter
    r = R()
    check("first sample is published", r.decide("BearingTemp_C", 60.0, 192, 0) == "baseline")
    check("inside the deadband, nothing", r.decide("BearingTemp_C", 61.0, 192, 1) is None)
    check("at the deadband, an exception", r.decide("BearingTemp_C", 62.0, 192, 2) == "exception")
    r = R()
    r.decide("BearingTemp_C", 60.0, 192, 0)
    got = [r.decide("BearingTemp_C", 60.0 + 0.5 * i, 192, i) for i in range(1, 6)]
    check("slow drift is measured from the last PUBLISHED value", got == [None, None, None, "exception", None])
    r = R()
    r.decide("BearingTemp_C", 84.9, 192, 0)
    check("crossing an alarm limit publishes though the move is small", r.decide("BearingTemp_C", 85.1, 192, 1) == "exception")
    r = R()
    r.decide("Vibration_mms", 1.0, 192, 0)
    check("a quality change publishes", r.decide("Vibration_mms", 1.0, 64, 1) == "exception")
    r = R()
    r.decide("Vibration_mms", 1.0, 192, 0)
    check("baseline is due after 10 s, not before", r.decide("Vibration_mms", 1.0, 192, 9.9) is None and r.decide("Vibration_mms", 1.0, 192, 10.0) == "baseline")
    r = R()
    r.decide("Running", True, 192, 0)
    check("a boolean change is an exception, a repeat is not", r.decide("Running", True, 192, 1) is None and r.decide("Running", False, 192, 2) == "exception")
    r = R()
    try:
        r.decide("Nope_x", 1.0, 192, 0); unk = False
    except UnknownTag:
        unk = True
    check("an unknown tag raises, it is not silently ignored", unk)
    # message
    check("topic is vigilimen/v1/<site>/<asset>/<tag>", M.topic("mine1", "CONV-001", "Speed_mps") == "vigilimen/v1/mine1/CONV-001/Speed_mps")
    for bad_part in ("a/b", "a+b", "#", "", "a b"):
        try:
            M.topic("mine1", bad_part, "t"); ok = False
        except ValueError:
            ok = True
        check(f"topic level {bad_part!r} is refused", ok)
    body = json.loads(M.payload("e", "s", "a", "t", 1.5, 192, T0, 7))
    check("payload has exactly the nine schema fields", tuple(sorted(body)) == tuple(sorted(M.FIELDS)) and body["schema"] == "1")
    check("ts_src is UTC with a Z", body["ts_src"] == "2026-11-18T09:00:00.000000Z")
    try:
        M.payload("e", "s", "a", "t", 1, 192, datetime(2026, 1, 1), 1); naive = False
    except ValueError:
        naive = True
    check("a naive time is refused", naive)
    try:
        M.payload("e", "s", "a", "t", 1, 100, T0, 1); qual = False
    except ValueError:
        qual = True
    check("a quality outside 192/64/0 is refused", qual)
    return bad


def mut_q(**kw):
    return type("Q", (EdgeQueue,), kw)


def mut_r(**kw):
    return type("R", (Reporter,), kw)


MUTATIONS = [
    ("queue: seq reused when the queue is empty", mut_q(_alloc_seq=lambda s: s.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM msg").fetchone()[0]), Reporter),
    ("queue: payload seq differs from queue seq", mut_q(_payload_seq=lambda s, n: n + 1), Reporter),
    ("queue: bound not enforced", mut_q(_enforce_bound=lambda s: []), Reporter),
    ("queue: drops are not counted", mut_q(_count_drop=lambda s, k: None), Reporter),
    ("queue: oldest message dropped whatever its kind", mut_q(_victim=lambda s: s.db.execute("SELECT seq, kind FROM msg ORDER BY seq LIMIT 1").fetchone()), Reporter),
    ("queue: newest baseline dropped instead of oldest", mut_q(_victim=lambda s: s.db.execute("SELECT seq, kind FROM msg WHERE kind='baseline' ORDER BY seq DESC LIMIT 1").fetchone()), Reporter),
    ("queue: replay in reverse order", mut_q(_order=lambda s: "DESC"), Reporter),
    ("queue: synchronous OFF", mut_q(_synchronous="OFF"), Reporter),
    ("reporter: deadband strict (> instead of >=)", EdgeQueue, mut_r(_beyond=lambda s, d, b: d > b)),
    ("reporter: alarm limit crossing ignored", EdgeQueue, mut_r(_zone=lambda s, sp, v: None)),
    ("reporter: quality change ignored", EdgeQueue, mut_r(_quality_changed=lambda s, a, b: False)),
    ("reporter: baseline never due", EdgeQueue, mut_r(_baseline_due=lambda s, n, t: False)),
    ("reporter: baseline always due", EdgeQueue, mut_r(_baseline_due=lambda s, n, t: True)),
    ("reporter: unknown tag accepted silently", EdgeQueue, mut_r(_spec=lambda s, t: Spec(1.0))),
    ("reporter: deadband measured from the last sample, not the last publication", EdgeQueue,
     type("R", (Reporter,), {"decide": lambda s, tag, v, q, n: (lambda k: (s._last.__setitem__(tag, (v, s._last[tag][1] if k is None else n, q, s._zone(s._spec(tag), v))) if tag in s._last and k is None else None) or k)(Reporter.decide(s, tag, v, q, n))})),
]


def main():
    bad = suite(EdgeQueue, Reporter)
    print(f"FF-39 baseline: {'PASS' if not bad else 'FAIL'}")
    for b in bad:
        print("  FAILED:", b)
    missed = []
    if not bad:
        for name, Q, R in MUTATIONS:
            try:
                caught = suite(Q, R)
            except Exception as e:           # a crash is a detection too
                caught = [f"crash: {type(e).__name__}"]
            print(f"  mutation {'caught    ' if caught else 'NOT CAUGHT'}: {name}")
            if not caught:
                missed.append(name)
    print(f"FF-39: {len(MUTATIONS)} mutations, {len(missed)} not caught")
    return 1 if bad or missed else 0


if __name__ == "__main__":
    sys.exit(main())
