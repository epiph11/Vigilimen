#!/usr/bin/env python3
"""
FF-22 — the compose file still draws the zones it claims to (ADR-011, ADR-013, ADR-014, ADR-023).

FF-21 reads safety.st. FF-06 reads the model. NEITHER reads docker-compose.yml,
which is where the safety controller's isolation from the control network is
actually decided. A one-line edit there (`networks: [net_control, net_safety]`
on the gateway, say, to "just reach the SIS") passes every other check in the
repository and removes the property ADR-011 exists for.

This check reads the compose files MERGED, the way `docker compose -f a -f b`
would, so an opt-in override cannot quietly add a network either:

  1. net_safety exists, is `internal: true`, and has exactly ONE member:
     plc-safety, and plc-safety is a member of nothing else;
  2. net_control and net_supervisory are internal (ADR-020 Q1 = a); only plc-control, gateway
     and fw-cell are on net_control; only fw-cell, opcua-sup, scada, historian and collector
     are on net_supervisory;
  3. fw-cell is the only service on both net_control and net_supervisory (ADR-023): the
     gateway is on net_control ONLY, and opcua-sup on net_supervisory only. Since ADR-023
     fw-cell is also the only multi-homed service;
  4. every published port is bound to 127.0.0.1 (Docker's default is 0.0.0.0);
  5. no service uses host networking, privileged mode, or links/extra_hosts that
     route around a network;
  6. nothing configured for the gateway or collector names the safety controller;
  7. the service set is the expected nine: a new container is a new decision.
     fw-cell is the only service that may add capabilities: exactly NET_ADMIN, SETUID and
     SETGID, after dropping ALL, with ip_forward 0 (it relays, it does not route);
  9. the compose default for the control function is the PLC link, not the embedded model (ADR-013);
  8. the gateway's Modbus host is a name Docker's DNS can resolve on net_control
     (a service name, container name or alias). A container's `hostname:` is NOT
     resolvable, so the original value, plc-conv-001, would have failed at
     run time with a DNS error that reads like a network fault.

It tests itself with mutations, like FF-21 and FF-23.

    python3 scripts/ff22_compose_topology.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

try:
    import yaml
except ImportError:                                    # pragma: no cover
    print("FF-22 needs PyYAML:  pip install pyyaml", file=sys.stderr)
    raise

PLANT = Path(__file__).resolve().parent.parent / "plant"
FILES = [PLANT / "docker-compose.yml", PLANT / "docker-compose.plcio.yml"]
EXPECTED = {"plc-control", "plc-safety", "gateway", "scada", "historian", "collector", "fw-cell", "opcua-sup", "pki-init"}
FWCELL_CAPS = {"NET_ADMIN", "SETUID", "SETGID"}
PASS, FAIL = "PASS", "FAIL"


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that REFUSES a duplicate key. PyYAML keeps the last one silently; Docker Compose rejects the file
    ("mapping key volumes already defined"), so a check on the silent result passes a file that does not start."""


def _no_dup(loader, node, deep=False):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in seen:
            raise SystemExit(f"FF-22: duplicate key {key!r} at line {k.start_mark.line + 1} of a compose file")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def nets(svc: dict) -> set[str]:
    n = svc.get("networks", [])
    return set(n if isinstance(n, list) else n.keys())


def merge(docs: list[dict]) -> dict:
    out = copy.deepcopy(docs[0])
    for d in docs[1:]:
        for name, svc in (d.get("services") or {}).items():
            base = out["services"].setdefault(name, {})
            for k, v in svc.items():
                if k == "networks":
                    base["networks"] = sorted(nets(base) | nets({"networks": v}))
                elif isinstance(v, dict) and isinstance(base.get(k), dict):
                    base[k] = {**base[k], **v}
                elif isinstance(v, list) and isinstance(base.get(k), list):
                    base[k] = base[k] + v
                else:
                    base[k] = v
        for k in ("networks", "volumes"):
            if d.get(k):
                out[k] = {**(out.get(k) or {}), **d[k]}
    return out


def evaluate(c: dict) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []

    def check(name: str, ok: bool, why: str) -> None:
        out.append((PASS if ok else FAIL, name, why))

    svcs, netdefs = c.get("services", {}), c.get("networks", {})
    members = lambda n: {s for s, v in svcs.items() if n in nets(v)}          # noqa: E731

    check("net_safety is internal", (netdefs.get("net_safety") or {}).get("internal") is True,
          "a non-internal bridge gives the SIS a route off the host")
    check("net_safety has exactly one member: plc-safety", members("net_safety") == {"plc-safety"},
          f"members: {sorted(members('net_safety'))}. A second container is a second path to the SIS")
    check("plc-safety is on no other network", nets(svcs.get("plc-safety", {})) == {"net_safety"},
          f"networks: {sorted(nets(svcs.get('plc-safety', {})))}")
    check("net_control is internal", (netdefs.get("net_control") or {}).get("internal") is True,
          "the control network has no route off the host; fw-cell is the only door")
    check("net_supervisory is internal (ADR-020 Q1 = a)", (netdefs.get("net_supervisory") or {}).get("internal") is True,
          "FF-04 reads 'no OT container has an Internet route'; a routable supervisory zone makes it false for SCADA, historian and collector")
    check("only plc-control, gateway and fw-cell are on net_control",
          members("net_control") == {"plc-control", "gateway", "fw-cell"},
          f"members: {sorted(members('net_control'))}")
    check("only fw-cell, opcua-sup, scada, historian and collector are on net_supervisory",
          members("net_supervisory") == {"fw-cell", "opcua-sup", "scada", "historian", "collector"},
          f"members: {sorted(members('net_supervisory'))}")
    check("the gateway is on net_control only (ADR-023)", nets(svcs.get("gateway", {})) == {"net_control"},
          f"networks: {sorted(nets(svcs.get('gateway', {})))}. A gateway on net_supervisory puts the readers back next to the controller")
    check("opcua-sup is on net_supervisory only", nets(svcs.get("opcua-sup", {})) == {"net_supervisory"},
          f"networks: {sorted(nets(svcs.get('opcua-sup', {})))}. On net_control it would be a second path into the cell")
    check("fw-cell is the only service on both net_control and net_supervisory",
          {s for s in svcs if {"net_control", "net_supervisory"} <= nets(svcs[s])} == {"fw-cell"},
          "a second bridge between zones is a second conduit nobody assessed")
    check("the multi-homed set is exactly {fw-cell}",
          {s for s in svcs if len(nets(svcs[s])) > 1} == {"fw-cell"},
          f"multi-homed: {sorted(s for s in svcs if len(nets(svcs[s])) > 1)}. (edge, jump and historian join it when S5 builds them: FF-22 is edited then)")

    bad_ports = []
    for s, v in svcs.items():
        for p in v.get("ports", []):
            if not str(p).startswith("127.0.0.1:"):
                bad_ports.append(f"{s}: {p}")
    check("every published port is bound to 127.0.0.1", not bad_ports,
          f"{bad_ports}. Docker publishes on 0.0.0.0 unless told otherwise")

    risky = [s for s, v in svcs.items()
             if (v.get("network_mode") and not (s == "pki-init" and v.get("network_mode") == "none"))
             or v.get("privileged") or v.get("links") or v.get("extra_hosts")
             or v.get("pid") == "host" or (v.get("cap_add") and s != "fw-cell")]
    check("no host networking, privileged mode, links, extra_hosts or added capabilities (except fw-cell's three)", not risky,
          f"{risky}. Each of these routes around the networks the file draws")
    fw = svcs.get("fw-cell", {})
    check("fw-cell drops ALL capabilities and adds exactly NET_ADMIN, SETUID, SETGID",
          set(fw.get("cap_drop", [])) == {"ALL"} and set(fw.get("cap_add", [])) == FWCELL_CAPS,
          f"cap_drop={fw.get('cap_drop')} cap_add={fw.get('cap_add')}. NET_ADMIN loads the rules; more than that is a reason to re-read ADR-023")
    check("fw-cell does not forward (ip_forward 0): it relays, it does not route",
          str((fw.get("sysctls") or {}).get("net.ipv4.ip_forward")) == "0",
          f"sysctls={fw.get('sysctls')}. A forwarding fw-cell would let Z2 reach Z1 without the relay's rules")

    leak = []
    for s in ("gateway", "collector", "scada"):
        blob = repr(svcs.get(s, {})).lower()
        if "plc-safety" in blob or "sis-conv" in blob or "net_safety" in blob:
            leak.append(s)
    check("nothing configured for gateway, collector or scada names the safety controller", not leak,
          f"{leak}. If it is named, someone intends to connect to it")

    gw_host = (svcs.get("gateway", {}).get("environment") or {}).get("VIGILIMEN_MODBUS_HOST")
    resolvable = set()
    for s, v in svcs.items():
        if "net_control" in nets(v):
            resolvable |= {s, v.get("container_name", s)}
            n = v.get("networks")
            if isinstance(n, dict):
                resolvable |= set((n.get("net_control") or {}).get("aliases", []))
    check("the gateway's Modbus host is resolvable by Docker DNS on net_control", gw_host in resolvable,
          f"VIGILIMEN_MODBUS_HOST={gw_host!r}; resolvable there: {sorted(resolvable)}. `hostname:` is not a DNS name")

    pki = svcs.get("pki-init", {})
    check("pki-init (the certificate generator) has no network at all and publishes nothing",
          pki.get("network_mode") == "none" and not pki.get("networks") and not pki.get("ports"),
          f"network_mode={pki.get('network_mode')!r} networks={pki.get('networks')!r}. It writes private keys: nothing may reach it or leave it")
    plc_mode = str((svcs.get("gateway", {}).get("environment") or {}).get("VIGILIMEN_PLC_LINK", ""))
    check("the compose default is the PLC link (embedded needs an explicit opt-out)",
          plc_mode.replace(" ", "") == "${VIGILIMEN_PLC_LINK:-modbus}",
          f"VIGILIMEN_PLC_LINK={plc_mode!r}. ADR-013: the PLC link is the default since 26 Oct 2026; a silent fall back to the embedded model would make every later check about a different plant")

    check("the service set is the expected nine", set(svcs) == EXPECTED,
          f"unexpected: {sorted(set(svcs) - EXPECTED)}; missing: {sorted(EXPECTED - set(svcs))}")
    return out


def mutations(c: dict):
    def m(label, fn, must_fail):
        d = copy.deepcopy(c); fn(d); return label, d, must_fail
    return [
        m("gateway added to net_safety", lambda d: d["services"]["gateway"].__setitem__(
            "networks", d["services"]["gateway"]["networks"] + ["net_safety"]),
          "net_safety has exactly one member: plc-safety"),
        m("net_safety no longer internal", lambda d: d["networks"]["net_safety"].__setitem__("internal", False),
          "net_safety is internal"),
        m("plc-safety also on net_control", lambda d: d["services"]["plc-safety"].__setitem__(
            "networks", ["net_safety", "net_control"]),
          "plc-safety is on no other network"),
        m("a port bound to every interface", lambda d: d["services"]["plc-control"]["ports"].__setitem__(
            0, "8081:8080"),
          "every published port is bound to 127.0.0.1"),
        m("pki-init gets a network", lambda d: d["services"]["pki-init"].pop("network_mode"),
          "pki-init (the certificate generator) has no network at all and publishes nothing"),
        m("plc-safety on host networking", lambda d: d["services"]["plc-safety"].__setitem__(
            "network_mode", "host"),
          "no host networking, privileged mode, links, extra_hosts or added capabilities (except fw-cell's three)"),
        m("collector told where the SIS is", lambda d: d["services"]["collector"]["environment"].__setitem__(
            "SIS_HOST", "sis-conv-001"),
          "nothing configured for gateway, collector or scada names the safety controller"),
        m("the gateway pointed at a hostname, not a service", lambda d: d["services"]["gateway"]["environment"].__setitem__(
            "VIGILIMEN_MODBUS_HOST", "plc-conv-001"),
          "the gateway's Modbus host is resolvable by Docker DNS on net_control"),
        m("the default silently falls back to the embedded model", lambda d: d["services"]["gateway"]["environment"].__setitem__(
            "VIGILIMEN_PLC_LINK", "${VIGILIMEN_PLC_LINK:-off}"),
          "the compose default is the PLC link (embedded needs an explicit opt-out)"),
        m("an unreviewed ninth container", lambda d: d["services"].__setitem__(
            "debug", {"image": "alpine", "networks": ["net_supervisory"]}),
          "the service set is the expected nine"),
        m("scada joins net_control", lambda d: d["services"]["scada"].__setitem__(
            "networks", ["net_supervisory", "net_control"]),
          "only plc-control, gateway and fw-cell are on net_control"),
        m("the gateway joins net_supervisory again", lambda d: d["services"]["gateway"].__setitem__(
            "networks", ["net_control", "net_supervisory"]),
          "the gateway is on net_control only (ADR-023)"),
        m("opcua-sup joins net_control", lambda d: d["services"]["opcua-sup"].__setitem__(
            "networks", ["net_supervisory", "net_control"]),
          "opcua-sup is on net_supervisory only"),
        m("the collector joins net_control", lambda d: d["services"]["collector"].__setitem__(
            "networks", ["net_supervisory", "net_control"]),
          "only plc-control, gateway and fw-cell are on net_control"),
        m("net_supervisory no longer internal", lambda d: d["networks"]["net_supervisory"].__setitem__("internal", False),
          "net_supervisory is internal (ADR-020 Q1 = a)"),
        m("fw-cell removed", lambda d: d["services"].pop("fw-cell"),
          "the service set is the expected nine"),
        m("fw-cell gains a capability", lambda d: d["services"]["fw-cell"]["cap_add"].append("SYS_ADMIN"),
          "fw-cell drops ALL capabilities and adds exactly NET_ADMIN, SETUID, SETGID"),
        m("fw-cell forwards packets", lambda d: d["services"]["fw-cell"]["sysctls"].__setitem__("net.ipv4.ip_forward", "1"),
          "fw-cell does not forward (ip_forward 0): it relays, it does not route"),
        m("another service adds a capability", lambda d: d["services"]["opcua-sup"].__setitem__("cap_add", ["NET_ADMIN"]),
          "no host networking, privileged mode, links, extra_hosts or added capabilities (except fw-cell's three)"),
    ]


def main() -> int:
    docs = [yaml.load(f.read_text(encoding="utf-8"), _StrictLoader) for f in FILES if f.exists()]
    merged = merge(docs)
    results = evaluate(merged)
    print(f"FF-22 — compose topology ({' + '.join(f.name for f in FILES if f.exists())})\n")
    width = max(len(n) for _, n, _ in results)
    for status, name, why in results:
        print(f"  {status}  {name.ljust(width)}")
        if status == FAIL:
            print(f"        why this case exists: {why}")
    program_failures = [r for r in results if r[0] == FAIL]

    print("\n  self-test — each mutation must be caught:")
    self_failures = 0
    for label, mutated, must_fail in mutations(merged):
        caught = any(s == FAIL and n == must_fail for s, n, _ in evaluate(mutated))
        print(f"  {PASS if caught else FAIL}  caught: {label}")
        self_failures += 0 if caught else 1

    n_mut = len(mutations(merged))
    print(f"\n{len(results)} properties, {len(program_failures)} failed; {n_mut} mutations, {self_failures} not caught")
    if program_failures or self_failures:
        print("\nFF-22 FAIL — the compose files no longer draw the zones ADR-011 and ADR-013 describe.")
        return 1
    print("""
FF-22 pass.

What this proves: on paper, the SIS network has one member, the control network
has three (PLC, gateway, fw-cell), fw-cell is the only door between Z1 and Z2, and
nothing is published beyond loopback.
What it does not prove: that Docker enforces it. The live proof is the failed
connection from plc-control to the SIS's IP address (plant/tools/prove-isolation.ps1).""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
