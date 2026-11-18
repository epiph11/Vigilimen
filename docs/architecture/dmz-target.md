# S5 target topology — OT / DMZ / IT (design draft, 26 Oct 2026)

**Status:** draft for E. Zaré. Nothing here is built or tested. It feeds ADR-020 (edge stack), ADR-021 (brokered remote access), the extension of FF-22 and the first P1 diagram (`docs/architecture/diagram-plan.md`, D1).
**Source of the current state:** `plant/docker-compose.yml` as of commit 044767c (3 networks, 6 services).

> **Revision proposed 30 Oct 2026 (ADR-023 draft, physical design V4.1).** Section 7 below holds the proposed changes (cell firewall `fw-cell`, read-only `opcua-sup`, zone ZS). Sections 1 to 6 are the 26 Oct draft and stay valid until ADR-023 is decided. If it is accepted, sections 1, 2, 4, 5 and 6 are rewritten from section 7.

## 1. Zones and networks

| Zone | Network | `internal` | Members (target) | Change |
|---|---|---|---|---|
| OT, safety | `net_safety` | yes | `plc-safety` | none |
| OT, control | `net_control` | yes | `plc-control`, `gateway` | none |
| OT, supervisory | `net_supervisory` | **yes (new)** | `gateway`, `scada`, `historian`, `collector`, `edge` | made internal (see 3.1) |
| DMZ | `net_dmz` | no (Docker constraint, see 3.2) | `edge` (second leg), `broker`, `jump` | new |
| Access segment | `net_remote_historian` | yes | `jump`, `historian` (second leg) | new, one per brokered asset |
| IT / outside | the host's `127.0.0.1` | n/a | cloud stand-in consumer, vendor client (host processes) | none |

**New services:** `edge`, `broker` (Mosquitto), `jump` (OpenSSH). Six services become nine.
**Multi-homed services (each one is a registered conduit component):** `gateway` (control + supervisory, existing), `edge` (supervisory + DMZ), `jump` (DMZ + one access segment), `historian` (supervisory + one access segment). Anything else on two networks is a defect.

## 2. Flows

| # | From → to | Protocol, port | Initiator | Conduit | Notes |
|---|---|---|---|---|---|
| F1 | `collector` → `gateway` | OPC UA 4840 | collector | existing | account `historian`; unchanged |
| F2 | `collector` → `historian` | PostgreSQL 5432 | collector | existing | the local historian never depends on the edge or the broker (s8C) |
| F3 | `edge` → `gateway` | OPC UA 4840 | edge | existing | new account `edge` (attribution only, ADR-017) |
| F4 | `edge` → `broker` | MQTT over TLS 8883 | **edge (OT-initiated, outbound)** | C-EDGE | publish only; the edge has no subscription |
| F5 | host consumer → `broker` | MQTT over TLS, published `127.0.0.1:18883` | IT | C-BROKER | subscribe only; cannot publish to the edge's topics |
| F6 | host vendor client → `jump` | SSH, published `127.0.0.1:12222` | vendor | C-REMOTE-IN | named certificate, time-boxed, approved by the operator |
| F7 | `jump` → `historian` | PostgreSQL 5432 on `net_remote_historian` | vendor session | C-REMOTE-OT | read-only role; one asset, one protocol |

**Forbidden, and tested:** any container on an OT network reaching the host or the Internet; IT or the host reaching any OT address; `broker` or any DMZ service opening a connection to `edge`; `jump` reaching `gateway`, `plc-control`, `plc-safety`, `scada` or `collector`; anything but `edge` writing to the edge's topics; anything but `plc-safety` on `net_safety`.

Ports 18883 and 12222 are proposals (not used in the current compose).

## 3. Two Docker facts that change the design

**3.1 Making `net_supervisory` internal breaks three host ports.** Docker ignores `ports:` for a container whose networks are all internal (the walkthrough records this for the OpenPLC UI). Today `scada` (1881), `historian` (15432) and `gateway` (14840) are published through `net_supervisory`. If that network becomes internal, FUXA's UI and the host-side OPC UA and psql access stop working, unless a relay is used, as `tools\plc-ui-relay.ps1` already does for the PLC UIs.
*Decision needed (ADR-020, open question Q1):* (a) make `net_supervisory` internal and add relays, so that FF-04 ("no OT container has an Internet route") is true of the supervisory zone too; or (b) keep it routable and define FF-04 over `net_control` and `net_safety` only, saying plainly that SCADA, historian and collector keep a route today. Option (a) is the stricter reading of the S5 gate and costs a relay for FUXA.

**3.2 `net_dmz` cannot be internal if the host must reach the broker and the jump host.** Same rule: a published port needs at least one non-internal network. So the DMZ here has a default route that a real DMZ would deny. This is a limitation of the simulation and goes into ADR-020 and ADR-021 as such. Not verified: that a container on one internal and one non-internal network publishes correctly. To test first, in Docker.

## 4. What FF-22 should check after S5 (proposal, numbers and cases decided when the script is edited)

1. The service set is exactly the nine expected.
2. `net_control`, `net_safety`, every `net_remote_*` and (if Q1 = a) `net_supervisory` are internal.
3. `net_safety` still has exactly one member, `plc-safety`, which is on nothing else.
4. `net_dmz` members are exactly `edge`, `broker`, `jump`.
5. The multi-homed set is exactly {`gateway`, `edge`, `jump`, `historian`}.
6. `edge` is on exactly {`net_supervisory`, `net_dmz`}; `broker` on exactly {`net_dmz`}.
7. No service is on both `net_dmz` and `net_control` or `net_safety`.
8. Each `net_remote_*` has exactly two members: `jump` and one asset.
9. Published ports: only `broker` and `jump` among the new services, all on `127.0.0.1`.

Mutations to add (each must make FF-22 fail): `edge` joins `net_control`; `broker` joins `net_supervisory`; `gateway` joins `net_dmz`; the broker port published on all addresses; a second asset joins `net_remote_historian`; `jump` joins `net_supervisory`.
Other tests are separate FFs: FF-04 (no Internet route, static and live), FF-20 (digests, SBOM, scan), FF-29 (WAN cut), and the proposed broker ACL and remote-access scenarios (see the ADRs).

## 5. Reference sketch (to check your drawing, not the deliverable)

```mermaid
flowchart LR
  subgraph IT["IT / outside = host loopback"]
    CONS["cloud stand-in consumer"]
    VEND["vendor client"]
  end
  subgraph DMZ["net_dmz (not internal: Docker constraint)"]
    BRK["broker (MQTT/TLS)"]
    JMP["jump (SSH, recorded)"]
  end
  subgraph OTS["OT supervisory (net_supervisory)"]
    EDGE["edge"]
    COL["collector"]
    HIS[("historian")]
    SCA["scada"]
    GW["gateway"]
  end
  subgraph OTC["OT control (net_control)"]
    PLC["plc-control"]
  end
  subgraph SAF["OT safety (net_safety)"]
    SIS["plc-safety"]
  end
  EDGE -- "F4 MQTT out (C-EDGE)" --> BRK
  CONS -- "F5 subscribe (C-BROKER)" --> BRK
  VEND -- "F6 SSH (C-REMOTE-IN)" --> JMP
  JMP -- "F7 psql, read-only (C-REMOTE-OT)" --> HIS
  EDGE -- "F3 OPC UA" --> GW
  COL -- "F1 OPC UA" --> GW
  COL -- "F2" --> HIS
  GW -- "Modbus" --> PLC
```

## 6. Drawing brief for D1 (draw.io)

- Landscape, left to right: **IT / outside | DMZ | OT supervisory | OT control | OT safety**. Safety at the bottom, visibly isolated, one box, no arrow in or out.
- One band per zone, label each with its network name and `internal` yes or no. Mark the DMZ band "not internal (simulation constraint)".
- Draw the four multi-homed services (`gateway`, `edge`, `jump`, `historian`) with a double border so the reader sees where zones touch.
- One arrow per flow F1 to F7, labelled with its number, protocol, port and **the initiator** (arrowhead at the target). Conduit IDs on F4 to F7. SL-T shown as "provisional until S7".
- A second layer or a red dashed set for the forbidden flows of section 2.
- Title block per ADR-022 rule 4: title, sprint, date, version, legend. Save uncompressed; commit the `.drawio` with its SVG export as `docs/architecture/diagrams/S5-dmz-target.drawio`.

## 7. Revision (ADR-023 accepted 15 Nov 2026; replaces sections 1, 2 and 4 where they differ)

> **Status 16 Nov 2026.** ADR-023 is accepted, ADR-020 Q1 = a (`net_supervisory` internal) is decided. `fw-cell` and `opcua-sup` are written and tested outside Docker (FF-22, FF-31, FF-33); they have **not yet run in Docker**. Edge, broker, jump and the DMZ are still design only. Sections 1, 2 and 4 above are the 26 Oct text and are superseded by this section.

Why: today the gateway is on `net_control` and `net_supervisory` at once, and any logged-in OPC UA client can write (ADR-017). Readers (edge, collector, SCADA read view) are connected to the thing that controls. Fix: one policy point in front of the cell, and a read-only server for everything that only reads.

### 7.1 Zones and networks (replaces section 1)

| Zone | Network | `internal` | Members (target) | Change vs section 1 |
|---|---|---|---|---|
| ZS safety | `net_safety` | yes | `plc-safety` | none; **no conduit**, zone ZS in the register |
| Z1 cell | `net_control` | yes | `plc-control`, `gateway`, `fw-cell` (cell leg) | **gateway is no longer multi-homed** |
| Z2 supervisory | `net_supervisory` | yes (Q1 = a) | `fw-cell` (supervisory leg), `opcua-sup`, `scada`, `historian`, `collector`, `edge` | `opcua-sup` and `fw-cell` added |
| Z3 DMZ | `net_dmz` | no (Docker constraint) | `edge` (second leg), `broker`, `jump` | none |
| Access segment | `net_remote_historian` | yes | `jump`, `historian` | none |
| IT / outside | host `127.0.0.1` | n/a | consumer, vendor client | none |

**New services vs the 26 Oct draft:** `fw-cell` (nftables, default deny) and `opcua-sup` (OPC UA server, measurements and `Plc*` status only, no command or fault node). Nine services become eleven.
**Multi-homed set:** {`fw-cell`, `edge`, `jump`, `historian`}. `gateway` leaves the set.

### 7.2 Flows (changes only; F2, F4 to F7 unchanged)

| # | From to | Protocol, port | Note |
|---|---|---|---|
| F1 | `collector` to `opcua-sup` | OPC UA 4840 (secure channel) | was `gateway` |
| F3 (F-01R) | `edge` to `opcua-sup` | OPC UA 4840 (secure channel) | was `gateway`; the edge can no longer write; FW-OT-001R |
| F8 | `opcua-sup` to `gateway`, through `fw-cell` | OPC UA 4840 | read path, conduit C1; FW-CELL-001 |
| F9 | `scada` (operator command) to `gateway`, through `fw-cell` | OPC UA 4840 | the only write path; FW-CELL-002; stays R-14 / S8 target |
| F10 | `fw-cell` log to `historian` or log sink | syslog or file | policy hits are evidence; FW-CELL-003 |
| F-DENY-01R | DMZ or enterprise to Z1 | any | no route; FW-DENY-001R; NET-05 |

Port numbers and the F8 to F10 numbering are proposals. Rule text and example addressing are in the V4.1 document, section 22.4 and 22.5.

### 7.3 FF-22 after ADR-023 (replaces section 4 items 1, 2, 5, 6, 7)

1. The service set is exactly the eleven expected.
2. `net_control`, `net_safety`, every `net_remote_*` and (Q1 = a) `net_supervisory` are internal.
3. `gateway` is on exactly {`net_control`}; `plc-control` on exactly {`net_control`}.
4. `fw-cell` is on exactly {`net_control`, `net_supervisory`}; it is the only service on both.
5. The multi-homed set is exactly {`fw-cell`, `edge`, `jump`, `historian`}.
6. `opcua-sup` is on exactly {`net_supervisory`}.
7. No service is on both `net_dmz` and `net_control` or `net_safety`.

Mutations to add (each must make FF-22 fail): `gateway` joins `net_supervisory`; `opcua-sup` joins `net_control`; `edge` joins `net_control`; `fw-cell` removed. New FFs proposed: FF-31 to FF-34 (ADR-023).

### 7.4 Sketch delta (for the mermaid in section 5)

Replace `EDGE -- F3 --> GW` and `COL -- F1 --> GW` by `EDGE -- "F3 / F-01R" --> OPS` and `COL -- "F1" --> OPS`; add `OPS["opcua-sup (read-only)"]` in the supervisory subgraph and `FWC["fw-cell (C1)"]` between it and `GW`; `OPS -- "F8" --> FWC --> GW`; `SCA -- "F9 command" --> FWC`. Remove `GW` from the supervisory subgraph.

### 7.5 D1 drawing brief delta

- Add the firewall C symbol (BOM-021 equivalent `fw-cell`) on the boundary between OT supervisory and OT control; label C1.
- Add `opcua-sup` in the supervisory band; re-aim the edge and collector arrows to it (F1, F3).
- Remove the double border from `gateway`; double border on `fw-cell`.
- Add F8 to F10, the red dashed F-DENY-01R, and the empty zone ZS box with the label "no conduit".
- Done 16 Nov 2026 in `docs/architecture/diagrams/S5-dmz-target.drawio`, v0.2. The layout was checked for overlaps by script, **not on screen**: open it in draw.io and tidy the labels. The C4-L2 (`c4-l2-ot.html`) has the same delta.

### 7.6 As written on 15 Nov (differences from the proposal above)

- `fw-cell` in the lab is a **TCP relay plus nftables, not a router** (`ip_forward` 0). Docker bridges are not routed to each other, so the relay is the only path. It shows the policy, not the DIN-rail device.
- **F10 is `docker logs vigilimen-fw-cell`** (counters and the sources it dropped), not syslog: Linux does not log from a container's network namespace by default.
- **F8 and F9 share port 4840** through one relay. nftables admits `opcua-sup` (FW-CELL-001) and `scada` (FW-CELL-002) by source address; it cannot tell a read from a write. The gateway sees `fw-cell` as the source.
- The SCADA project has two OPC UA devices: read (`opcua-sup`, account `scada`) and command (`fw-cell`, account `engineer`).
- Host access to FUXA, the historian and `opcua-sup` goes through `plant/tools/supervisory-relay.ps1` (run 16 Nov: FUXA relay up); the gateway has no published port.
- **F9 also carries two reads.** The HMI shows `StartCommand` and `StopCommand`, which `opcua-sup` does not have, so FUXA reads them from the gateway on the command device. Command state is read through F9; every measurement is read from `opcua-sup`.
- **FUXA needs its OPC UA driver built into the image** (`plant/scada/Dockerfile`): the stock image downloads it at runtime, impossible on an internal network.
- **Not done:** the OPC UA secure channel on `opcua-sup` (ADR-023 point 7: passwords still travel in clear), FF-34 (needs the DMZ), the DMZ itself (`edge`, broker, `jump`), and an F10 sink beyond `docker logs`. FF-32 is written and not yet run. FF-26 and FF-28 now read from `opcua-sup` and write through `fw-cell` (16 Nov); FF-27 is unchanged and runs inside the gateway. Run on 16 Nov: FF-26, FF-33 live, 4e by hand in FUXA.

### 7.7 DMZ topology B (decided 17 Nov 2026; replaces the "DMZ is not internal" rows of 7.1 and section 3.2)

**Problem.** With a non-internal `net_dmz`, `edge` (also on `net_supervisory`) would have an Internet route, which makes FF-04 false for an OT container.
**Decision.** `net_dmz` is **internal**: `edge`, `broker` (and `jump` later). A new `net_hostleg` is **not internal** and holds only the services the host must reach (`broker` now, `jump` later); it exists only because Docker publishes a port from a non-internal network. It is a lab artifice and is labelled as such in the compose file and the drawing.

| Network | `internal` | Members |
|---|---|---|
| `net_dmz` | yes | `edge`, `broker` (`jump` later) |
| `net_hostleg` | no (lab artifice) | `broker` (`jump` later) |
| `net_edgelink` | yes | `edge`, `opcua-sup` only (added 18 Nov 2026, see below) |

**Correction 18 Nov 2026: `edge` leaves `net_supervisory`.** In Docker, two services on the same network can reach each other on every port; there is no filter inside a network. An `edge` on `net_supervisory` could therefore reach `scada`, `historian` and `collector`, not only `opcua-sup`. A dedicated internal network `net_edgelink` holds `edge` and `opcua-sup` and nothing else: the edge reaches `opcua-sup` and no other supervisory service. `opcua-sup` becomes multi-homed (`net_supervisory` and `net_edgelink`). There is no firewall between the DMZ and the supervisory zone in the lab; the separation is network membership, which FF-22 pins. A filtering firewall between the zones is a production target (`hardening-targets.md`).

**Consequences.** The multi-homed set becomes {`fw-cell`, `opcua-sup`, `edge`, `broker`} (`jump`, `historian` later). FF-22: `edge` is on exactly {`net_edgelink`, `net_dmz`}; `net_edgelink` has exactly {`edge`, `opcua-sup`}; `edge` is not on `net_supervisory`; `broker` on exactly {`net_dmz`, `net_hostleg`}; `net_dmz` has exactly the members above; no service is on `net_dmz` and `net_control` or `net_safety`; nothing but `broker` (and `jump`) is on `net_hostleg`. FF-04 holds for `edge`; `broker` and `jump` keep an Internet route through `net_hostleg`, stated as a limit.
**Verified 18 Nov 2026 (spike).** A container on one internal and one non-internal network publishes on `127.0.0.1` (HTTP 200 from the host); a container on the internal network reaches it (200) and has no route to 1.1.1.1 ("Network is unreachable").
**Not verified.** That `edge` has IP forwarding off (to be tested in FF-22 or the edge validation).
