#!/usr/bin/env python3
"""
FF-13 — deny-list enforcement.

Reads a Terraform plan in JSON form (`terraform show -json tfplan`) and fails
the build if the plan proposes creating anything on the never-create list.

    terraform show -json tfplan > plan.json
    python3 scripts/ff13_denylist.py plan.json

Exit codes:
    0  nothing denied
    1  a denied resource is proposed
    2  the check could not run (bad input, missing policy)

Exit code 2 is deliberately distinct from 1. A check that cannot run is not a
pass, and CI must treat it as a failure rather than as silence — which is how
most policy gates quietly stop working.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

POLICY = Path(__file__).resolve().parent.parent / "infra" / "policy" / "deny-list.yml"


# --------------------------------------------------------------------------
# Policy loading
# --------------------------------------------------------------------------

def load_policy(path: Path) -> list[dict]:
    """Load the deny-list.

    PyYAML if it is available, otherwise a small parser for the subset of YAML
    this file actually uses. The check must run on a bare runner without a pip
    install step — a fitness function with a dependency chain is a fitness
    function that gets skipped on the day it matters.
    """
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text).get("rules", [])
    except ImportError:
        return _parse_minimal_yaml(text)


def _parse_minimal_yaml(text: str) -> list[dict]:
    rules: list[dict] = []
    current: dict | None = None
    nested_key: str | None = None

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip() if not raw.strip().startswith("#") else ""
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if stripped.startswith("- type:"):
            if current:
                rules.append(current)
            current = {"type": stripped.split(":", 1)[1].strip().strip('"')}
            nested_key = None
            continue

        if current is None or indent < 4:
            continue

        if stripped.endswith(":"):
            nested_key = stripped[:-1].strip()
            current[nested_key] = {}
            continue

        if ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()

        if value.startswith("["):
            parsed: object = [
                v.strip().strip('"').strip("'")
                for v in value.strip("[]").split(",")
                if v.strip()
            ]
        else:
            parsed = value.strip('"').strip("'")

        if nested_key and indent >= 6 and isinstance(current.get(nested_key), dict):
            current[nested_key][key] = parsed
        else:
            nested_key = None
            current[key] = parsed

    if current:
        rules.append(current)
    return rules


# --------------------------------------------------------------------------
# Plan inspection
# --------------------------------------------------------------------------

def planned_creations(plan: dict) -> list[dict]:
    """Every resource the plan proposes to create or replace.

    'create' and 'delete,create' both bring a resource into existence. A
    replacement of a denied resource is still a denied resource, and reading
    only for 'create' is the obvious way to write this check wrong.
    """
    out = []
    for change in plan.get("resource_changes", []):
        actions = change.get("change", {}).get("actions", [])
        if "create" in actions:
            out.append(change)
    return out


def _get(obj: dict, dotted: str):
    """Read a dotted attribute path out of a plan's `after` object."""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    if isinstance(cur, list) and cur and not isinstance(cur[0], (dict, list)):
        return cur[0]
    return cur


def is_allowed(change: dict, rule: dict) -> tuple[bool, str]:
    """Does an allow_when exemption apply to this specific resource?"""
    allow = rule.get("allow_when")
    if not allow:
        return False, ""
    after = change.get("change", {}).get("after") or {}
    for attr, permitted in allow.items():
        actual = _get(after, attr)
        if actual is None or actual not in permitted:
            return False, ""
    return True, rule.get("allow_reason", "matches an allow_when exemption")


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def check(plan: dict, rules: list[dict]) -> tuple[list[str], list[str]]:
    by_type = {r["type"]: r for r in rules if r.get("type")}
    violations: list[str] = []
    exempted: list[str] = []

    for change in planned_creations(plan):
        rule = by_type.get(change.get("type"))
        if not rule:
            continue
        addr = change.get("address", change.get("type", "?"))
        allowed, why = is_allowed(change, rule)
        if allowed:
            exempted.append(f"{addr} — allowed: {why}")
        else:
            violations.append(
                f"{addr}\n"
                f"      type   {change['type']}\n"
                f"      reason {rule.get('reason', 'on the never-create list')}\n"
                f"      cost   {rule.get('cost_if_forgotten', 'unbounded')}"
            )
    return violations, exempted


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: ff13_denylist.py <terraform-plan.json>", file=sys.stderr)
        return 2

    try:
        plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FF-13 could not read the plan: {exc}", file=sys.stderr)
        return 2

    if not POLICY.exists():
        print(f"FF-13 could not find the policy at {POLICY}", file=sys.stderr)
        return 2

    rules = load_policy(POLICY)
    if not rules:
        print("FF-13 loaded an empty policy — refusing to pass", file=sys.stderr)
        return 2

    violations, exempted = check(plan, rules)

    for line in exempted:
        print(f"  ~ {line}")

    if not violations:
        print(f"FF-13 pass — {len(rules)} rules, "
              f"{len(planned_creations(plan))} creations, 0 denied")
        return 0

    print("\nFF-13 FAIL — the plan proposes resources on the never-create list\n")
    for v in violations:
        print(f"  ✗ {v}\n")
    print("These resources bill by existing rather than by being used.")
    print("To proceed, either remove them from the plan, or amend")
    print("infra/policy/deny-list.yml in a PR that says why — an ADR is")
    print("required to delete a rule, because that is a decision to spend.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
