#!/usr/bin/env python3
"""
FF-23 — conveyor.st and the gateway agree on the I/O contract (ADR-013).

Two files describe the same interface: `plant/plc-control/conveyor.st` declares
the located variables, and `plant/gateway/plc_io_map.py` is what the gateway
reads and writes. If they drift, nothing fails loudly. OpenPLC accepts a Modbus
write to an address no program locates, and drops it. The gateway's read-back
(plc_link.py) catches that at run time; this check catches it in the commit.

It asserts, on the file as it is on disk:

  1. the located variables in conveyor.st are exactly the points in the map,
     with the same IEC address and the same type, and nothing else is located;
  2. every gateway-written input is only READ by the program: assigning to one
     would be silently overwritten by the next Modbus write, or worse, win;
  3. every program-written output is assigned somewhere (a declared output
     nobody drives reads as FALSE forever and looks healthy);
  4. the Modbus addresses derived from the IEC addresses are the ones the
     OpenPLC documentation gives (coil 800 = %QX100.0, holding register 100 =
     %QW100), so a wrong derivation cannot hide behind a consistent table;
  5. nothing safety-shaped is in the contract or in conveyor.st: the SIS has
     no I/O on this link (ADR-014);
  6. plc-upload/conveyor_upload.st is current, i.e. build.py was run after the
     last edit of conveyor.st. Uploading a stale file is the cheapest way to
     test the wrong program.

It tests itself: each mutation is applied to an in-memory copy and must be
caught. A mutation that cannot be applied fails the run, because an assertion
whose setup never ran is a mistake this repository has already made once.

What it does NOT prove: that conveyor.st COMPILES under MatIEC, or that OpenPLC
maps the addresses as documented. Only the Docker run settles those (FF-26).

    python3 scripts/ff23_plc_io_map.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plant" / "gateway"))

import plc_io_map as M  # noqa: E402

CONVEYOR_ST = ROOT / "plant" / "plc-control" / "conveyor.st"
UPLOAD_ST = ROOT / "plant" / "plc-upload" / "conveyor_upload.st"

PASS, FAIL = "PASS", "FAIL"

# Words that mean the safety function. None may appear in the contract or the program.
SAFETY_WORDS = re.compile(r"estop|e_stop|pullcord|pull_cord|beltdrift|guard|contactor|safety|sis_", re.I)

LOCATED = re.compile(r"^\s*(\w+)\s+AT\s+(%[A-Z]+[\d.]+)\s*:\s*(\w+)\s*;", re.M)

# What the OpenPLC docs say, written out independently of plc_io_map.iec_to_modbus.
DOCUMENTED = {"%QX100.0": 800, "%QX100.4": 804, "%QX101.0": 808, "%QX101.1": 809,
              "%QW100": 100, "%QW102": 102, "%QW110": 110, "%QW111": 111}


def strip_comments(src: str) -> str:
    return re.sub(r"\(\*.*?\*\)", "", src, flags=re.S)


def evaluate(src: str, upload: str | None) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []

    def check(name: str, ok: bool, why: str) -> None:
        out.append((PASS if ok else FAIL, name, why))

    code = strip_comments(src)
    located = {m.group(1): (m.group(2), m.group(3).upper()) for m in LOCATED.finditer(code)}
    table = {p.name: (p.iec, p.iec_type) for p in M.POINTS}

    check("located variables are exactly the points in plc_io_map.py",
          set(located) == set(table),
          f"extra in ST: {sorted(set(located) - set(table))}; missing from ST: {sorted(set(table) - set(located))}")
    check("every point has the same IEC address in both files",
          all(located.get(n, (None,))[0] == a for n, (a, _) in table.items()),
          "a moved address is a write that lands on another variable, or on none")
    check("every point has the same type in both files",
          all(located.get(n, (None, None))[1] == t for n, (_, t) in table.items()),
          "a BOOL where the gateway writes a UINT reads as 0 or 1 and looks plausible")
    mixed = []
    for blk in re.findall(r"^\s*VAR\b[^\n]*\n(.*?)^\s*END_VAR", code, flags=re.S | re.M):
        decls = [l for l in blk.splitlines() if re.match(r"\s*\w+\s*(AT\s+%\S+\s*)?:", l)]
        n_loc = sum(1 for l in decls if re.search(r"\bAT\s+%", l))
        if 0 < n_loc < len(decls):
            mixed.append(f"{n_loc} located + {len(decls) - n_loc} plain")
    check("no VAR block mixes located and plain declarations", not mixed,
          f"{mixed}. MatIEC rejects it: 'invalid located variable declaration' on every plain line, then a cascade")
    check("nothing is located in the input range (%I...)",
          not any(a.startswith("%I") for a, _ in located.values()),
          "a Modbus master cannot write %I..., so an input there is never fed")

    inputs = [p.name for p in M.POINTS if p.direction == M.TO_PLC]
    outputs = [p.name for p in M.POINTS if p.direction == M.FROM_PLC]
    assigned = {n for n in inputs + outputs if re.search(rf"\b{n}\s*:=", code)}
    check("the program never assigns a gateway-written input",
          not (assigned & set(inputs)),
          f"assigned: {sorted(assigned & set(inputs))}. The gateway would overwrite it every cycle")
    check("the program assigns every output the gateway reads",
          set(outputs) <= assigned,
          f"never assigned: {sorted(set(outputs) - assigned)}")

    m = re.search(r"MAP_VERSION\s*:\s*UINT\s*:=\s*(\d+)", code)
    check("the program's MAP_VERSION equals plc_io_map.MAP_VERSION",
          bool(m) and int(m.group(1)) == M.MAP_VERSION,
          "the gateway trusts a PLC only if it reports the version the gateway was written for")
    check("derived Modbus addresses match the documented OpenPLC mapping",
          all(M.iec_to_modbus(a) == m for a, m in DOCUMENTED.items()),
          "iec_to_modbus() disagrees with the OpenPLC addressing table")
    try:
        M.self_check()
        distinct = True
    except AssertionError:
        distinct = False
    check("no two points share a Modbus address", distinct, "plc_io_map.self_check() failed")

    check("nothing safety-shaped in the contract",
          not any(SAFETY_WORDS.search(p.name) for p in M.POINTS),
          "the SIS has no I/O on this link and never will (ADR-014, FF-21)")
    check("nothing safety-shaped is referenced by conveyor.st code",
          not SAFETY_WORDS.search(code),
          "control and safety stay separate in the program as well as on the network")

    if upload is not None:
        wiring_at = upload.find("(* ---------------------------------------------------------------------\n   GENERATED")
        body = upload[:wiring_at].rstrip() + "\n" if wiring_at > 0 else upload
        check("plc-upload/conveyor_upload.st is current (run plant/plc-upload/build.py)",
              body == src.replace("\r\n", "\n").rstrip() + "\n",
              "the file you would upload is not the file on disk")
    return out


def mutations():
    """(label, find, replace, the check that must fail)."""
    return [
        ("a moved address", "Stop_PB           AT %QX100.1", "Stop_PB           AT %QX100.5",
         "every point has the same IEC address in both files"),
        ("a changed type", "Bearing_Temp_x10  AT %QW100   : UINT", "Bearing_Temp_x10  AT %QW100   : BOOL",
         "every point has the same type in both files"),
        ("a point dropped from the program", "    Plc_State         AT %QW111   : UINT;",
         "    Plc_State_gone    : UINT;",
         "located variables are exactly the points in plc_io_map.py"),
        ("an extra located variable", "    Permissives_OK  : BOOL;",
         "    Spare AT %QX100.7 : BOOL;\n    Permissives_OK  : BOOL;",
         "located variables are exactly the points in plc_io_map.py"),
        ("located and plain variables in one block", "END_VAR\n\n(* MatIEC (and the IEC grammar)", "(* MatIEC (and the IEC grammar)",
         "no VAR block mixes located and plain declarations"),
        ("an input moved to %I", "Zero_Speed        AT %QX100.2", "Zero_Speed        AT %IX100.2",
         "nothing is located in the input range (%I...)"),
        ("the program writes a gateway input", "Permissives_OK := Upstream_Ready AND Downstream_Ready;",
         "Start_PB := FALSE;\nPermissives_OK := Upstream_Ready AND Downstream_Ready;",
         "the program never assigns a gateway-written input"),
        ("a stale signature", "MAP_VERSION     : UINT := 1;", "MAP_VERSION     : UINT := 2;",
         "the program's MAP_VERSION equals plc_io_map.MAP_VERSION"),
        ("an output nobody drives", "Plc_State := INT_TO_UINT(State);", "(* gone *)",
         "the program assigns every output the gateway reads"),
        ("a safety identifier in the control program", "Permissives_OK := Upstream_Ready AND Downstream_Ready;",
         "Permissives_OK := Upstream_Ready AND Downstream_Ready AND Guard_Closed;",
         "nothing safety-shaped is referenced by conveyor.st code"),
    ]


def main() -> int:
    src = CONVEYOR_ST.read_text(encoding="utf-8").replace("\r\n", "\n")
    upload = UPLOAD_ST.read_text(encoding="utf-8") if UPLOAD_ST.exists() else None
    results = evaluate(src, upload)

    print("FF-23 — conveyor.st and the gateway agree on the I/O contract\n")
    width = max(len(n) for _, n, _ in results)
    for status, name, why in results:
        print(f"  {status}  {name.ljust(width)}")
        if status == FAIL:
            print(f"        why this case exists: {why}")
    program_failures = [r for r in results if r[0] == FAIL]
    if upload is None:
        print("  FAIL  plc-upload/conveyor_upload.st does not exist (run plant/plc-upload/build.py)")
        program_failures.append((FAIL, "upload missing", ""))

    print("\n  self-test — each mutation must be caught:")
    self_failures = 0
    for label, find, repl, must_fail in mutations():
        if src.count(find) != 1:
            print(f"  FAIL  could not apply mutation (text not found exactly once): {label}")
            self_failures += 1
            continue
        mutated = evaluate(src.replace(find, repl, 1), None)
        caught = any(s == FAIL and n == must_fail for s, n, _ in mutated)
        print(f"  {PASS if caught else FAIL}  caught: {label}")
        if not caught:
            self_failures += 1

    print(f"\n{len(results)} properties, {len(program_failures)} failed; "
          f"{len(mutations())} mutations, {self_failures} not caught")
    if program_failures or self_failures:
        print("\nFF-23 FAIL — fix conveyor.st or plc_io_map.py so they describe one interface,")
        print("then run plant/plc-upload/build.py. Change this check only with the ADR that says why.")
        return 1
    print("""
FF-23 pass.

What this proves: the program and the gateway name the same addresses, types and
directions, and the file you upload is the file on disk.
What it does not prove: that MatIEC compiles conveyor.st, or that OpenPLC puts
%QX100.0 on Modbus coil 800. Both are settled by the Docker run (FF-26).""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
