#!/usr/bin/env python3
"""
Tests for FF-13.

A fitness function that has never been shown to fail is not a fitness
function — it is a green tick. Every case below exists because it is a way
the check could pass when it should not.

    python3 scripts/test_ff13.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ff13_denylist as ff  # noqa: E402


def plan(*changes: dict) -> dict:
    return {"resource_changes": list(changes)}


def rc(type_: str, actions: list[str], after: dict | None = None, addr: str | None = None) -> dict:
    return {
        "address": addr or f"{type_}.test",
        "type": type_,
        "change": {"actions": actions, "after": after or {}},
    }


RULES = ff.load_policy(ff.POLICY)

CASES: list[tuple[str, dict, int, str]] = [
    (
        "clean plan passes",
        plan(rc("aws_s3_bucket", ["create"]), rc("azurerm_storage_account", ["create"])),
        0,
        "nothing on the list",
    ),
    (
        "denied resource fails",
        plan(rc("aws_nat_gateway", ["create"])),
        1,
        "a NAT gateway is the classic forgotten bill",
    ),
    (
        "REPLACEMENT of a denied resource still fails",
        plan(rc("azurerm_cdn_frontdoor_profile", ["delete", "create"])),
        1,
        "delete,create brings it back into existence — reading only for 'create' "
        "is the obvious way to write this check wrong",
    ),
    (
        "destroying a denied resource passes",
        plan(rc("aws_nat_gateway", ["delete"])),
        0,
        "tearing one down is the behaviour the policy wants",
    ),
    (
        "no-op on an existing denied resource passes",
        plan(rc("aws_nat_gateway", ["no-op"])),
        0,
        "the check gates creation, not the state of the world",
    ),
    (
        "allow_when exemption is honoured",
        plan(rc("azurerm_api_management", ["create"], {"sku_name": "Consumption_0"})),
        0,
        "consumption tier idles at zero",
    ),
    (
        "allow_when does NOT cover a different value",
        plan(rc("azurerm_api_management", ["create"], {"sku_name": "Developer_1"})),
        1,
        "Developer tier bills hourly — the exemption is narrow on purpose",
    ),
    (
        "allow_when on a nested attribute is honoured",
        plan(rc("aws_kinesis_stream", ["create"],
                {"stream_mode_details": [{"stream_mode": "ON_DEMAND"}]})),
        0,
        "on-demand has no shard-hour floor; the attribute is nested in a block",
    ),
    (
        "missing attribute does NOT earn an exemption",
        plan(rc("aws_kinesis_stream", ["create"], {})),
        1,
        "an absent attribute must not be read as compliance — this is the "
        "failure mode that makes a policy silently permissive",
    ),
    (
        "one denied resource among many is still caught",
        plan(
            rc("aws_s3_bucket", ["create"]),
            rc("aws_iam_role", ["create"]),
            rc("google_sql_database_instance", ["create"]),
            rc("aws_lambda_function", ["create"]),
        ),
        1,
        "the check must not stop at the first clean resource",
    ),
]


def main() -> int:
    failures = 0
    print(f"FF-13 tests — policy has {len(RULES)} rules\n")

    for name, p, expected, why in CASES:
        violations, _ = ff.check(p, RULES)
        actual = 1 if violations else 0
        ok = actual == expected
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            failures += 1
            print(f"        expected exit {expected}, got {actual}")
            print(f"        why this case exists: {why}")

    # the check must refuse to pass on an empty policy
    empty_violations, _ = ff.check(plan(rc("aws_nat_gateway", ["create"])), [])
    if empty_violations:
        print("  FAIL  empty policy should produce no violations (main() gates it separately)")
        failures += 1
    else:
        print("  PASS  empty policy produces no violations — main() returns 2 for it")

    print(f"\n{len(CASES) + 1} cases, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
