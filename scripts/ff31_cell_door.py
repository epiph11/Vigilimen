#!/usr/bin/env python3
"""
FF-31 - fw-cell is the door of the cell, and the readers read opcua-sup (ADR-023, points 1 to 4).

FF-22 reads WHICH containers are on WHICH network. This check reads the WIRING that makes
those networks useful: who connects to whom. A compose file can keep every network correct
and still send the collector to the gateway, which would hand the readers the command nodes
again without moving a container.

  1. the collector reads opcua-sup, not the gateway (F1);
  2. opcua-sup reads upstream through fw-cell, not the gateway (F8);
  3. fw-cell relays to the gateway and names exactly opcua-sup (FW-CELL-001) and scada (FW-CELL-002);
  4. no service except fw-cell names the gateway as an endpoint;
  5. the gateway publishes no port (it is on an internal network, Docker would ignore it, and
     a mapping that does nothing reads as a promise);
  6. the SCADA project has two OPC UA devices: the READ device points at opcua-sup and carries
     only the seven measurements; the COMMAND device points at fw-cell; none points at the gateway.

It tests itself with mutations, like FF-22.

    python3 scripts/ff31_cell_door.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:                                    # pragma: no cover
    print("FF-31 needs PyYAML:  pip install pyyaml", file=sys.stderr)
    raise

PLANT = Path(__file__).resolve().parent.parent / "plant"
FUXA = PLANT / "scada" / "project" / "vigilimen-conv001.fuxa.json"
MEASUREMENTS = {"Running", "SafetyTripped", "BeltSpeed_mps", "Load_tph", "BearingTemp_C", "Vibration_mms", "MotorCurrent_A"}
PASS, FAIL = "PASS", "FAIL"


def env(svc: dict) -> dict:
    e = svc.get("environment") or {}
    return e if isinstance(e, dict) else dict(x.split("=", 1) for x in e)


def host(url: str | None) -> str | None:
    return urlparse(url).hostname if url else None


def evaluate(c: dict, fuxa: dict) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []

    def check(name: str, ok: bool, why: str) -> None:
        out.append((PASS if ok else FAIL, name, why))

    svcs = c.get("services", {})
    col, sup, fw = (env(svcs.get(n, {})) for n in ("collector", "opcua-sup", "fw-cell"))

    check("the collector reads opcua-sup (F1)", host(col.get("VIGILIMEN_OPCUA_URL")) == "opcua-sup",
          f"VIGILIMEN_OPCUA_URL={col.get('VIGILIMEN_OPCUA_URL')!r}. A collector on the gateway can start the conveyor")
    check("opcua-sup reads upstream through fw-cell (F8)", host(sup.get("VIGILIMEN_UPSTREAM_URL")) == "fw-cell",
          f"VIGILIMEN_UPSTREAM_URL={sup.get('VIGILIMEN_UPSTREAM_URL')!r}. Going round fw-cell removes the policy point")
    check("fw-cell relays to the gateway", fw.get("FW_UPSTREAM_HOST") == "gateway",
          f"FW_UPSTREAM_HOST={fw.get('FW_UPSTREAM_HOST')!r}")
    check("FW-CELL-001 admits opcua-sup and FW-CELL-002 admits scada, nobody else",
          (fw.get("FW_F8_SOURCE"), fw.get("FW_F9_SOURCE")) == ("opcua-sup", "scada"),
          f"F8={fw.get('FW_F8_SOURCE')!r} F9={fw.get('FW_F9_SOURCE')!r}. The collector or the edge on that list is a write path")
    naming = sorted(n for n, v in svcs.items()
                    if n not in ("fw-cell", "gateway") and any("gateway" in str(x) for x in env(v).values()))
    check("no service except fw-cell names the gateway as an endpoint", not naming,
          f"{naming}. Only fw-cell may point at the gateway; everything else goes through it or reads opcua-sup")
    check("the gateway publishes no port", not svcs.get("gateway", {}).get("ports"),
          f"ports={svcs.get('gateway', {}).get('ports')}. On an internal network Docker ignores it: a dead promise")
    devs = [d for d in (fuxa.get("devices") or {}).values() if d.get("type") == "OPCUA"]
    by_host = {host((d.get("property") or {}).get("address")): d for d in devs}
    read, cmd = by_host.get("opcua-sup"), by_host.get("fw-cell")
    check("the SCADA read device points at opcua-sup and carries only the seven measurements",
          read is not None and {t["name"] for t in read["tags"].values()} == MEASUREMENTS,
          f"hosts: {sorted(h for h in by_host if h)}. A read view on the gateway brings the command nodes back")
    check("the SCADA command device points at fw-cell (F9), never at the gateway",
          cmd is not None and "gateway" not in by_host and len(devs) == 2,
          f"hosts: {sorted(h for h in by_host if h)}; devices: {len(devs)}")
    return out


def mutations(c: dict, f: dict):
    def m(label, fn, must_fail, target="c"):
        d, g = copy.deepcopy(c), copy.deepcopy(f)
        fn(d if target == "c" else g); return label, d, g, must_fail
    return [
        m("the collector goes back to the gateway", lambda d: d["services"]["collector"]["environment"].__setitem__(
            "VIGILIMEN_OPCUA_URL", "opc.tcp://gateway:4840/vigilimen/conv001/"),
          "the collector reads opcua-sup (F1)"),
        m("opcua-sup bypasses fw-cell", lambda d: d["services"]["opcua-sup"]["environment"].__setitem__(
            "VIGILIMEN_UPSTREAM_URL", "opc.tcp://gateway:4840/vigilimen/conv001/"),
          "opcua-sup reads upstream through fw-cell (F8)"),
        m("fw-cell relays somewhere else", lambda d: d["services"]["fw-cell"]["environment"].__setitem__(
            "FW_UPSTREAM_HOST", "plc-control"),
          "fw-cell relays to the gateway"),
        m("the collector is admitted by FW-CELL-002", lambda d: d["services"]["fw-cell"]["environment"].__setitem__(
            "FW_F9_SOURCE", "collector"),
          "FW-CELL-001 admits opcua-sup and FW-CELL-002 admits scada, nobody else"),
        m("scada is pointed at the gateway directly", lambda d: d["services"]["scada"].__setitem__(
            "environment", {"VIGILIMEN_OPCUA_URL": "opc.tcp://gateway:4840/"}),
          "no service except fw-cell names the gateway as an endpoint"),
        m("the gateway publishes 14840 again", lambda d: d["services"]["gateway"].__setitem__(
            "ports", ["127.0.0.1:14840:4840"]),
          "the gateway publishes no port"),
        m("the SCADA read device is pointed at the gateway", lambda g: [
            d["property"].__setitem__("address", "opc.tcp://gateway:4840/vigilimen/conv001/")
            for d in g["devices"].values() if d.get("name", "").endswith("(read)")],
          "the SCADA read device points at opcua-sup and carries only the seven measurements", "f"),
        m("a command tag moved to the read device", lambda g: [
            d["tags"].__setitem__("x", {"name": "StartCommand"}) for d in g["devices"].values()
            if d.get("name", "").endswith("(read)")],
          "the SCADA read device points at opcua-sup and carries only the seven measurements", "f"),
        m("the command device is pointed at the gateway", lambda g: [
            d["property"].__setitem__("address", "opc.tcp://gateway:4840/vigilimen/conv001/")
            for d in g["devices"].values() if d.get("name", "").endswith("(command)")],
          "the SCADA command device points at fw-cell (F9), never at the gateway", "f"),
    ]


def main() -> int:
    c = yaml.safe_load((PLANT / "docker-compose.yml").read_text(encoding="utf-8"))
    f = json.loads(FUXA.read_text(encoding="utf-8"))
    results = evaluate(c, f)
    print("FF-31 - the door of the cell (docker-compose.yml)\n")
    width = max(len(n) for _, n, _ in results)
    for status, name, why in results:
        print(f"  {status}  {name.ljust(width)}")
        if status == FAIL:
            print(f"        why this case exists: {why}")
    failures = [r for r in results if r[0] == FAIL]
    print("\n  self-test - each mutation must be caught:")
    bad = 0
    for label, mutated, mf, must_fail in mutations(c, f):
        caught = any(s == FAIL and n == must_fail for s, n, _ in evaluate(mutated, mf))
        print(f"  {PASS if caught else FAIL}  caught: {label}")
        bad += 0 if caught else 1
    print(f"\n{len(results)} properties, {len(failures)} failed; {len(mutations(c, f))} mutations, {bad} not caught")
    if failures or bad:
        print("\nFF-31 FAIL - the wiring no longer matches ADR-023.")
        return 1
    print("""
FF-31 pass.

What this proves: on paper, readers read opcua-sup, opcua-sup reads through fw-cell, and fw-cell
admits exactly two sources. What it does not prove: that the relay and its rules work. That is
FF-32 (live, Docker).""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
