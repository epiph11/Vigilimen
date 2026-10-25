#!/usr/bin/env python3
"""
FF-21 — the safety program ON DISK matches the argument FF-06 makes about the MODEL.

FF-06 proves the independence argument about plant/sim/interlock_model.py, a
Python model. It never opens safety.st. So an edit to the real program that
breaks independence passes FF-06 untouched, and nothing in the repository
notices. That gap is the real risk ADR-011 creates (model and logic can drift).

This check reads safety.st itself and asserts the properties the argument
depends on:

  1. the inputs are exactly the seven physical inputs, at their addresses;
  2. nothing machine-protection, network or bypass-shaped appears in the code;
  3. every identifier used in the code is declared, and only the two expected
     function blocks are called;
  4. the program boots TRIPPED, the trip clears in exactly one place, and that
     place is a rising edge from the panel reset, not a level and not a write;
  5. the contactor coil is NOT Tripped, assigned once.

What it does NOT prove: that the logic is CORRECT (a wrong setpoint passes),
or that the wiring matches. Those are the FAT hold points.

It tests itself: each mutation below is applied to an in-memory copy of the
program, and the check must catch it. A mutation that cannot be applied, or
that is not caught, fails the run — an assertion whose setup never ran is the
mistake this repository has already made once.

    python3 scripts/ff21_safety_st_static.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SAFETY_ST = Path(__file__).resolve().parent.parent / "plant" / "plc-safety" / "safety.st"

# The seven physical inputs. Adding an eighth is a design change: edit this
# list deliberately, in the same commit as the ADR that explains why.
EXPECTED_INPUTS = {
    "EStop_ChA": "%IX0.0",
    "EStop_ChB": "%IX0.1",
    "PullCord_ChA": "%IX0.2",
    "PullCord_ChB": "%IX0.3",
    "BeltDrift_OK": "%IX0.4",
    "Guard_Closed": "%IX0.5",
    "Safety_Reset": "%IX0.6",
}
EXPECTED_OUTPUTS = {
    "Contactor_Coil": "%QX0.0",
    "Trip_Latched": "%QX0.1",
    "Device_Fault": "%QX0.2",
}
ALLOWED_TYPES = {"BOOL", "TON", "R_TRIG"}
ALLOWED_CALLS = {"Discrep_Timer", "Reset_Edge"}
KEYWORDS = {"IF", "THEN", "ELSE", "ELSIF", "END_IF", "NOT", "AND", "OR",
            "XOR", "TRUE", "FALSE", "T", "Q", "IN", "PT", "CLK"}
# Words that mean machine protection, a network path, or a way round the trip.
FORBIDDEN = ["scada", "network", "modbus", "opc", "remote", "bypass", "maint",
             "inhibit", "override", "force", "bearing", "temp", "current",
             "vibration", "overload", "speed", "setpoint"]

PASS, FAIL = "PASS", "FAIL"


def strip_comments(src: str) -> str:
    """Remove (* ... *) comments, including nested ones."""
    prev = None
    while prev != src:
        prev = src
        src = re.sub(r"\(\*(?:(?!\(\*).)*?\*\)", "", src, flags=re.S)
    return src


def parse_block(src: str, keyword: str) -> dict[str, tuple[str, str | None]]:
    """name -> (type, address-from-trailing-comment) for one VAR block."""
    m = re.search(rf"\b{keyword}\b(.*?)\bEND_VAR\b", src, flags=re.S)
    out: dict[str, tuple[str, str | None]] = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        d = re.match(r"\s*(\w+)\s*:\s*(\w+)[^;]*;\s*(?:\(\*\s*(%[A-Z]+[\d.]+))?", line)
        if d:
            out[d.group(1)] = (d.group(2), d.group(3))
    return out


def evaluate(src: str) -> list[tuple[str, str, str]]:
    """Return (status, name, why-this-case-exists) for every property."""
    res: list[tuple[str, str, str]] = []

    def check(name: str, ok: bool, why: str) -> None:
        res.append((PASS if ok else FAIL, name, why))

    code = strip_comments(src)
    inputs = parse_block(src, "VAR_INPUT")          # addresses live in comments
    outputs = parse_block(src, "VAR_OUTPUT")
    all_declared: dict[str, tuple[str, str | None]] = {}
    for kw in ("VAR_INPUT", "VAR_OUTPUT", "VAR"):
        all_declared.update(parse_block(code, kw))

    last_end = code.rfind("END_VAR")
    end_prog = code.find("END_PROGRAM")
    body = code[last_end + len("END_VAR"):end_prog] if last_end >= 0 and end_prog > last_end else ""

    check("inputs are exactly the seven physical inputs, at their addresses",
          {k: v[1] for k, v in inputs.items()} == EXPECTED_INPUTS,
          "an eighth input, or one moved off a physical %IX address, is a path "
          "from somewhere that is not the field. TRITON is the reason.")
    check("outputs are exactly the three expected, all %QX coils/lamps",
          {k: v[1] for k, v in outputs.items()} == EXPECTED_OUTPUTS,
          "an extra output is a second thing this function can do.")

    lowered = (code).lower()
    hits = [w for w in FORBIDDEN if w in lowered]
    check("no machine-protection, network or bypass words in the code",
          not hits,
          "machine protection lives in the control function; every demand "
          "added here is another way to trip spuriously, which is how safety "
          f"functions get bypassed. Found: {hits}")
    check("no located memory or word/double addresses in the code",
          not re.search(r"%[IQM][WDLB]|%M|\bAT\b", code),
          "a located %M or %IW variable is a way for something else to write "
          "or feed this program.")

    used = set(re.findall(r"\b[A-Za-z_]\w*\b", body))
    undeclared = sorted(u for u in used if u not in all_declared and u not in KEYWORDS)
    check("every identifier in the code is declared",
          not undeclared,
          f"an undeclared name is a tag the allow-list never saw. Found: {undeclared}")

    types = {t for t, _ in all_declared.values()}
    calls = {c for c in re.findall(r"\b(\w+)\s*\(", body) if c not in KEYWORDS}
    check("only BOOL, TON and R_TRIG are used, and only two blocks are called",
          types <= ALLOWED_TYPES and calls <= ALLOWED_CALLS,
          f"types={sorted(types - ALLOWED_TYPES)} calls={sorted(calls - ALLOWED_CALLS)}")

    check("the program boots TRIPPED",
          re.search(r"\bTripped\s*:\s*BOOL\s*:=\s*TRUE\s*;", code) is not None,
          "a cold start is not a safe start: a controller that powers up "
          "permissive has decided the plant is safe without looking at it.")

    clears = [m.start() for m in re.finditer(r"\bTripped\s*:=\s*FALSE\s*;", body)]
    cond_ok = False
    if len(clears) == 1:
        ifs = [m.start() for m in re.finditer(r"\bIF\b", body[:clears[0]])]
        if ifs:
            then_at = body.find("THEN", ifs[-1])
            cond_ok = "Reset_Edge.Q" in body[ifs[-1]:then_at]
    check("the trip clears in exactly one place, and only on Reset_Edge.Q",
          len(clears) == 1 and cond_ok,
          "any second way to clear a latched trip is a way to restart the belt "
          "under somebody's hands.")

    check("reset is a rising edge from the panel input, not a level",
          re.search(r"Reset_Edge\s*\(\s*CLK\s*:=\s*Safety_Reset\s*\)", body) is not None
          and len(re.findall(r"\bSafety_Reset\b", body)) == 1,
          "a level reset restarts the belt the moment the demand clears.")

    check("Contactor_Coil is NOT Tripped, assigned once",
          re.search(r"\bContactor_Coil\s*:=\s*NOT\s+Tripped\s*;", body) is not None
          and len(re.findall(r"\bContactor_Coil\s*:=", body)) == 1,
          "the coil must be the exact inverse of the latched trip, with no "
          "second writer.")
    return res


def mutations() -> list[tuple[str, str, str, str]]:
    """(label, find, replace, check-that-must-fail). Each is one realistic mistake."""
    return [
        ("a SCADA stop request wired into the trip decision",
         "   OR Device_Fault\nTHEN",
         "   OR Device_Fault\n   OR Scada_Stop_Request\nTHEN",
         "no machine-protection, network or bypass words in the code"),
        ("an eighth input declared with no physical address",
         "    Safety_Reset    : BOOL;",
         "    Spare_Input     : BOOL;\n    Safety_Reset    : BOOL;",
         "inputs are exactly the seven physical inputs, at their addresses"),
        ("an input moved onto located memory",
         "%IX0.6  MANUAL reset",
         "%MX0.6  MANUAL reset",
         "inputs are exactly the seven physical inputs, at their addresses"),
        ("bearing temperature migrated into the safety function",
         "   OR Device_Fault\nTHEN",
         "   OR Device_Fault\n   OR (Bearing_Temp > 95.0)\nTHEN",
         "no machine-protection, network or bypass words in the code"),
        ("boots permissive",
         "Tripped         : BOOL := TRUE;",
         "Tripped         : BOOL := FALSE;",
         "the program boots TRIPPED"),
        ("a second place that clears the trip",
         "Contactor_Coil := NOT Tripped;",
         "IF Safety_Reset THEN Tripped := FALSE; END_IF;\nContactor_Coil := NOT Tripped;",
         "the trip clears in exactly one place, and only on Reset_Edge.Q"),
        ("reset becomes a level instead of an edge",
         "IF Reset_Edge.Q\n   AND NOT EStop_Demand",
         "IF Safety_Reset\n   AND NOT EStop_Demand",
         "the trip clears in exactly one place, and only on Reset_Edge.Q"),
        ("a second function block called",
         "Reset_Edge(CLK := Safety_Reset);",
         "Reset_Edge(CLK := Safety_Reset);\nDelay(IN := Safety_Reset);",
         "only BOOL, TON and R_TRIG are used, and only two blocks are called"),
    ]


def main() -> int:
    if not SAFETY_ST.exists():
        print(f"FF-21 FAIL — {SAFETY_ST} not found")
        return 1
    src = SAFETY_ST.read_text(encoding="utf-8").replace("\r\n", "\n")

    results = evaluate(src)
    width = max(len(n) for _, n, _ in results)
    print("FF-21 — safety.st on disk matches the independence argument\n")
    for status, name, why in results:
        print(f"  {status}  {name.ljust(width)}")
        if status == FAIL:
            print(f"        why this case exists: {why}")
    program_failures = [r for r in results if r[0] == FAIL]

    print("\n  self-test — each mutation must be caught:")
    self_failures = 0
    for label, find, repl, must_fail in mutations():
        if src.count(find) != 1:
            print(f"  FAIL  could not apply mutation (text not found exactly once): {label}")
            self_failures += 1
            continue
        mutated = evaluate(src.replace(find, repl, 1))
        caught = any(s == FAIL and n == must_fail for s, n, _ in mutated)
        print(f"  {PASS if caught else FAIL}  caught: {label}")
        if not caught:
            self_failures += 1

    print(f"\n{len(results)} properties, {len(program_failures)} failed; "
          f"{len(mutations())} mutations, {self_failures} not caught")

    if program_failures or self_failures:
        print("\nFF-21 FAIL — safety.st no longer matches what FF-06 argues about the model.")
        print("Fix safety.st, or change this check deliberately in the same commit as an ADR.")
        return 1

    print("""
FF-21 pass.

What this proves: the program on disk has the same shape the model has — seven
physical inputs, nothing machine-protective, one clear point on a panel edge.
What it does not prove: that the logic is correct, or that the wiring matches.
A dangerous setpoint passes this check. That is what the FAT hold points are for.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
