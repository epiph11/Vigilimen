# ADR-020 — The edge is a separate service that publishes MQTT through a DMZ broker

**Status:** Proposed (draft of 26 October 2026, nothing built) · **Deciders:** E. Zaré
**Related:** ADR-005 (unidirectional boundary) · ADR-010 (UTC) · ADR-013 · ADR-017 · ADR-018 · ADR-019 · `docs/architecture/dmz-target.md` · `docs/sprints/S5-cadrage.md` · **Sprint:** 5 (gate M1)

> Draft. Choices marked **(to confirm)** are proposals. The open questions at the end block acceptance.

---

## Context

Today the collector reads the gateway over OPC UA at 1 Hz and writes to the local historian. Nothing leaves the plant. S5 must let data leave OT only through a DMZ, survive a WAN cut with zero loss, and not give the cloud any path back into OT (ADR-005).

Two facts from the current compose shape the decision. `net_supervisory` is not internal, so SCADA, historian and collector have an Internet route today. And ADR-017 records that OPC UA accounts differ in attribution, not authorisation: any authenticated session can write every writable node, including `StartCommand`.

## Decision

> **Amendment decided 15 Nov 2026 (ADR-023 accepted).** Point 1 ("second reader of the gateway") becomes "second reader of `opcua-sup`", point 8 becomes `net_supervisory` and `net_dmz` with the cell firewall `fw-cell` between the cell and `net_supervisory`, point 9 is closed (the edge cannot write because `opcua-sup` has no writable node) and Q2 is answered by option b. The text below is the 26 Oct draft and is left unchanged until the decision.

1. **`edge` is a new service (the ninth, after `fw-cell` and `opcua-sup`). The collector and the historian stay as they are.** The local record of the plant must not depend on the edge, the broker or the WAN: that is the s8C independence argument, and the historian outage case in the collector's own header. The edge is a second reader of `opcua-sup`, the read-only supervisory OPC UA server (ADR-023). It never reads the gateway.
2. **Broker: Eclipse Mosquitto, in the DMZ, MQTT over TLS.** Per-client user and an ACL file. TLS certificates come from a lab CA generated at start into a volume, never committed (FF-03). Credentials are demo credentials under ADR-018. Mutual TLS from S5 (maintainer, 17 Nov 2026): one certificate per client, ACL keyed on its identity; S12 reuses the pattern. See `docs/architecture/hardening-targets.md`. *(decided 17 Nov 2026: Mosquitto, 2.x series, image pinned by digest (FF-20); no comparison run)*
3. **The edge only publishes.** Its ACL grants write on its own topic subtree and **no subscription at all**. The consumer's ACL grants read only. Control does not flow from IT to OT, by configuration that a test can check.
4. **Client stack: Python, an OPC UA client and an MQTT client library.** Same language as the collector and the gateway. *(decided 17 Nov 2026: paho-mqtt 2.x with `CallbackAPIVersion.VERSION2`, aiomqtt (it wraps paho) as fallback; asyncua stays at the stack's version. Criterion: the library exposes the broker's acknowledgement per message (point 7), proved by a test. Check paho's maintenance on PyPI and GitHub before pinning.)*
5. **Filtering.** The gateway is read at 1 Hz. Baseline publication is one value per tag every 10 s (0.1 Hz). A value is also published at once when it moves beyond a per-tag deadband, when its quality changes, or when it crosses an alarm limit. Deadbands come from a small table committed with the code. *(values: `docs/sprints/S5-cadrage.md`, Q3)*
6. **Payload.** Plain JSON, versioned: `schema` (`"1"`), `edge_id`, `site`, `asset`, `tag`, `value`, `quality`, `ts_src` (UTC, stamped at the source as the collector does), `seq` (per-edge, strictly increasing). Topic `vigilimen/v1/<site>/<asset>/<tag>`. Sparkplug B stays deferred to S12, as already recorded.
7. **Store and forward.** A durable local queue (SQLite in WAL mode on a named volume) is the authority. Publish at QoS 1 with a fixed client identifier and a persistent session. A message leaves the queue only after the broker acknowledges it. After a reconnect, replay in `seq` order. QoS 1 is at-least-once, so the consumer deduplicates on `(edge_id, seq)`. The queue is bounded; when it is full the edge drops the oldest baseline message first, **counts every drop and logs it**. Loss must be visible, never silent.
8. **Network (amended 17 Nov 2026, option B, publish test passed 18 Nov 2026, `dmz-target.md` 7.7).** `edge` is on `net_edgelink` and `net_dmz`, nothing else (corrected 18 Nov 2026), and both are internal: the edge has no route off the host. `net_edgelink` holds only `edge` and `opcua-sup`, so the edge cannot reach `scada`, `historian` or `collector`; `opcua-sup` is the one supervisory service on two networks. It opens every connection (outbound only). The broker is on `net_dmz` and on `net_hostleg`, a non-internal network that exists only because Docker publishes a port to the host from a non-internal network (lab artifice, a recorded limit). `net_supervisory` is internal (ADR-023); `fw-cell` sits between the cell and `net_supervisory`, and the edge has no route to the cell.
9. **Accounts.** The edge reads `opcua-sup` with its own account, `edge`. `opcua-sup` has no writable node, so the edge **cannot** write, whatever its account: read-only is a property of the address space, not of a role (ADR-023). The ADR-017 limit does not apply to this path.

## Reasoning

**Why a separate service, not a collector that also publishes.** The thing that persists and the thing that crosses a boundary fail differently, and the second one is the exposed one. A fault or compromise in the edge must not take the plant's own history with it.

**Why a durable queue and not the client library's offline buffer.** An in-memory buffer is lost when the edge restarts during the outage, which is exactly when it is needed. The same reasoning as ADR-019: state that matters is persisted, in a defined order.

**Why report-by-exception on top of a slow baseline.** The baseline keeps the stream alive and bounds the replay volume (about 2,500 messages for a 1 h cut at 7 tags and 0.1 Hz, before exceptions); the exceptions keep the alarm-relevant changes timely.

## Consequences

**Positive.** The historian is untouched. The boundary has one outbound publisher and a broker whose ACL can be tested. The WAN cut test (FF-29) has a defined success criterion: zero loss, ordered replay, drops counter at zero.

**Negative.** Ten services once `edge` and the broker are added (eight today with `fw-cell` and `opcua-sup`), and FF-22 pins the set; it is extended when they arrive. Duplicates reach the consumer by design. Time-stamping depends on the gateway's clock. The lab's `net_hostleg` is not internal (a Docker constraint, `dmz-target.md` 7.7), so the broker and the jump host keep an Internet route a real DMZ would deny; the edge does not.

**Limits to state in the gate report.** The WAN cut is a Docker network disconnect: it shows the replay, not the behaviour of a real radio link (that is a SAT item). The expected results are written by the author of the code.

## Tests (each one an FF; numbers are given when the script is written)

| Property | FF |
|---|---|
| Topology: ten services, zones, multi-homed set, published ports | FF-22 (extended) |
| No OT container has an Internet route, static and live | FF-04 |
| 1 h WAN cut under load: zero loss, ordered replay, drops counter zero | FF-29 |
| Images pinned by digest, SBOM, scan | FF-20 |
| Broker ACL: the edge cannot subscribe; the consumer cannot publish to the edge's topics | proposed new FF |

## Open questions (block acceptance)

- **Q1.** *(Answered 15 Nov: yes, `net_supervisory` is internal, with host relays; see ADR-023.)* Is `net_supervisory` OT for FF-04? If yes it becomes internal and SCADA, historian and gateway lose their loopback ports unless relays are added (as for the PLC UIs). If no, FF-04 covers `net_control` and `net_safety` only and the report says so.
- **Q2.** *(Answered 15 Nov: option b, see ADR-023, accepted.)* ADR-017 means a "read-only" edge account cannot be enforced today. Accept attribution-only for S5 and detect by behaviour (the edge never writes), or bring forward the cheapest fix listed in ADR-017 (a second OPC UA instance exposing measurements only)?
- **Q3.** *(Answered 17 Nov 2026: deadband table and WAN load in `docs/sprints/S5-cadrage.md`, section "Deadbands et charge WAN".)* Deadband per tag and the load for the WAN test.
- **Q4.** *(Answered 17 Nov 2026 by the maintainer: a host script on the published broker port; the service count stays at ten.)* Who plays the cloud: a host script on the published broker port, or a container?

---

*VIGILIMEN-ADR-020 · Sprint 5 · draft*

*Amendment note 16 Nov 2026: ADR-023 is accepted. The body above (points 1, 8, 9, Q1, Q2) now reflects it. Service count: 8 today, 10 with `edge` and the broker, 11 with `jump` (ADR-021).*
