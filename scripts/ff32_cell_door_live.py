#!/usr/bin/env python3
"""
FF-32 - the cell firewall drops a source that is not on its list (needs Docker, run on the host).

ADR-023, FW-CELL-DEFAULT. Static wiring is FF-31; this is the live behaviour:

  1. read the fw-cell drop counter and its dropped-sources list
  2. from the COLLECTOR container (not an F8 or F9 source) try to open fw-cell:4840 -> must time out
  3. read the counter again -> must have grown, and the collector's address must be listed

Why the collector: it is on net_supervisory, has a route to fw-cell, and is neither opcua-sup (F8) nor
scada (F9). If someone adds it to the allowed list this test fails. Do NOT run it while
docker-compose.ff26.yml is up (that override makes the collector the F9 source on purpose).

    python scripts\\ff32_cell_door_live.py
"""
from __future__ import annotations

import re
import subprocess
import sys

CELL = "vigilimen-fw-cell"
PROBE = "vigilimen-collector"


def sh(*cmd: str, timeout: int = 60) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")


def last_status() -> dict:
    line = [ln for ln in sh("docker", "logs", CELL, "--tail", "30").splitlines() if "FW-CELL-DEFAULT_drops=" in ln]
    if not line:
        return {}
    m = re.search(r"FW-CELL-DEFAULT_drops=(\d+)", line[-1])
    return {"drops": int(m.group(1)), "line": line[-1]}


def probe_ip() -> str:
    out = sh("docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}", PROBE)
    return out.split()[0] if out.split() else ""


def main() -> int:
    results: list[tuple[bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((ok, name))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))

    print("FF-32 - fw-cell drops an unlisted source")
    ov = sh("docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", CELL)
    f9 = re.search(r"FW_F9_SOURCE=(\S+)", ov)
    if not f9 or f9.group(1) == "collector":
        print(f"  cannot run: F9 source is {f9.group(1) if f9 else 'unknown'} "
              "(the FF-26 override is up, or fw-cell is not running). Run `docker compose up -d` first.")
        return 2
    before = last_status()
    check("fw-cell status line found in its log", bool(before))
    if not before:
        return 1
    ip = probe_ip()
    check("probe container address found", bool(ip), ip)

    out = sh("docker", "exec", PROBE, "python", "-c",
             "import socket\ntry:\n socket.create_connection(('fw-cell',4840),3); print('CONNECTED')\n"
             "except Exception as e:\n print(type(e).__name__)")
    check("an unlisted source cannot connect (times out)", "TimeoutError" in out and "CONNECTED" not in out, out.strip())

    import time
    time.sleep(6)                                   # the log line is refreshed every 5 s
    after = last_status()
    grew = bool(after) and after["drops"] > before["drops"]
    check("the drop counter grew", grew, f"{before['drops']} -> {after.get('drops')}")
    check("the probe's address is in dropped_sources", bool(after) and ip in after["line"].split("dropped_sources=")[-1])

    failed = [n for ok, n in results if not ok]
    print(f"\n{len(results)} checks, {len(failed)} failed")
    print("FF-32 pass." if not failed else "FF-32 FAIL: write symptom, cause, fix in docs/runs/NOTES.md BEFORE changing anything.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
