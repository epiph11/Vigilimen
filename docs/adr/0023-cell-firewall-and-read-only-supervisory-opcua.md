# ADR-023 — A cell firewall and a read-only supervisory OPC UA server separate the cell from everything that only reads

**Status:** Proposed (draft of 30 October 2026, nothing built) · **Deciders:** E. Zaré
**Related:** ADR-005 (unidirectional boundary) · ADR-017 (accounts are attribution, not authorisation) · ADR-020 (edge stack, Q2) · ADR-021 (brokered access) · `docs/architecture/dmz-target.md` · physical design V4.1, section 22 · **Sprint:** 5 (gate M1)

> Draft. Values marked **(placeholder)** are not decisions. SL-T values come from the S7 risk assessment, not from this ADR. This ADR resolves Q2 of ADR-020 and takes the first of the three "cheapest first" options listed in ADR-017.

---

## Context

Two facts about the lab today differ from the real thing the lab is meant to resemble.

1. **The gateway sits on `net_control` and `net_supervisory` at once.** There is no policy point between the cell (PLC, gateway) and supervisory (SCADA, historian collector, and after S5 the edge). On the physical design (V3) Z1 and Z2 are two zones, but nothing sits between them. IEC 62443-3-2 expects a conduit with a stated policy between zones of different security level.
2. **Any logged-in OPC UA client can write** `StartCommand`, `StopCommand` and the five `Fault*` tags (ADR-017). ADR-020 point 9 makes the edge's account "attribution only", so a compromised edge can start the conveyor. The edge is the component that faces the cloud.

Both are the same defect seen from two sides: the thing that reads is connected to the thing that controls.

## Decision

1. **A cell firewall (`fw-cell`) is the single door of the cell.** Lab: one nftables container, default deny. Physical: firewall C (BOM-021, DIN-rail industrial firewall, between SW-CELL and SW-OT). Rules FW-CELL-001 to 003 plus FW-CELL-DEFAULT (deny and log).
2. **The gateway moves to `net_control` only.** It stops being multi-homed. Its only neighbours are the PLC and `fw-cell`.
3. **A read-only supervisory OPC UA server (`opcua-sup`, physical OT-OPC-01) lives in Z2.** It serves measurements and `Plc*` status. It has **no command node and no fault node**, so there is nothing to authorise: read-only is a property of the address space, not of a role.
4. **Everything that only reads reads `opcua-sup`.** The edge (F-01R), the historian collector and the SCADA read view. The only writer path is the operator's command channel (F-09), through `fw-cell`, to the gateway; it carries the S8 hardening and stays a known target (R-14).
5. **No route from the DMZ or the enterprise zone to Z1.** Flow F-DENY-01R / rule FW-DENY-001R. The jump host reaches the HMI, not the gateway.
6. **Zone and conduit register.** Z1 cell, Z2 supervisory, Z3 OT DMZ, Z4 enterprise, ZM management, **ZS safety (SIS) with no conduit**. Conduits C1 `fw-cell`, C2 firewall A, C3 firewall B, CM management. SL-T per zone is **(placeholder)** until S7.
7. **OPC UA secure channel with per-identity roles** (Sign and Encrypt, application certificates) on the supervisory server. The cell-side NoSecurity policy stays inside Z1 and is documented as a lab concession for the PLC link.

## Reasoning

The cheapest alternative is to keep one OPC UA server and accept attribution (ADR-020 Q2, option a). It leaves the edge able to write and relies on a detector that does not exist until S24. The second server costs one container and removes the capability instead of watching it. ADR-017 already named this as the cheapest fix and warned against a role enum inside the demo server, which looks like the real thing and is not; an address space without command nodes is the real thing.

A cell firewall is what the standard asks for between zones, and it is the part of the physical design (V3) that had no counterpart in the lab.

## Consequences

**Positive.** The edge and the collector can no longer start the conveyor or inject faults. ADR-017's "a compromised collector can start the conveyor" becomes true only of the operator command path. FF-22 gains a precise subject (what may cross C1). The lab and the physical design have the same number of firewalls (three).

**Negative.**
- Two containers more (`fw-cell`, `opcua-sup`), one more hop of latency on measurements (small), one more thing to keep in sync with the gateway's tag list.
- The edge, the collector and SCADA endpoints are re-pointed; the dmz-target flows F3 and F5 change (F3 becomes F-01R). A regression run of FF-21 to FF-28 is needed.
- Docker cannot reproduce a hardware DIN-rail firewall; `fw-cell` shows the policy, not the device (see section 22.9 of the V4.1 document).
- The collector still connects as DB owner (D-17, D-18); not addressed here.

**Open.** `net_supervisory` internal or not (ADR-020 Q1, recommendation A) is unchanged and compatible. Deadbands (Q3) unchanged.

## Tests (each one an FF; numbers are given when the script is written)

| Proposed | Checks |
|---|---|
| FF-31 | `fw-cell` is the only container attached to both `net_control` and `net_supervisory`; the gateway is on `net_control` only |
| FF-32 | From Z2 to Z1 only the permitted conduit flow passes; every other port is dropped and logged (NET-04) |
| FF-33 | `opcua-sup` exposes no writable node: a write attempt by any account fails (OPC-03); the edge, the collector and SCADA read view work |
| FF-34 | No path from `net_dmz` or the enterprise side to `net_control` (NET-05) |
| FF-22 | Updated: checks the new zone table and the multi-homed set |

FF-29 (WAN outage) is unchanged and must still pass with the edge reading `opcua-sup`.

---

*VIGILIMEN-ADR-023 · Sprint 5 · draft*
