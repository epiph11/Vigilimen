# ADR-020 — The edge is a separate service that publishes MQTT through a DMZ broker

**Status:** Proposed (draft of 26 October 2026, nothing built) · **Deciders:** E. Zaré
**Related:** ADR-005 (unidirectional boundary) · ADR-010 (UTC) · ADR-013 · ADR-017 · ADR-018 · ADR-019 · `docs/architecture/dmz-target.md` · `docs/sprints/S5-cadrage.md` · **Sprint:** 5 (gate M1)

> Draft. Choices marked **(to confirm)** are proposals. The open questions at the end block acceptance.

---

## Context

Today the collector reads the gateway over OPC UA at 1 Hz and writes to the local historian. Nothing leaves the plant. S5 must let data leave OT only through a DMZ, survive a WAN cut with zero loss, and not give the cloud any path back into OT (ADR-005).

Two facts from the current compose shape the decision. `net_supervisory` is not internal, so SCADA, historian and collector have an Internet route today. And ADR-017 records that OPC UA accounts differ in attribution, not authorisation: any authenticated session can write every writable node, including `StartCommand`.

## Decision

1. **`edge` is a new, seventh service. The collector and the historian stay as they are.** The local record of the plant must not depend on the edge, the broker or the WAN: that is the s8C independence argument, and the historian outage case in the collector's own header. The edge is a second reader of the gateway.
2. **Broker: Eclipse Mosquitto, in the DMZ, MQTT over TLS.** Per-client user and an ACL file. TLS certificates come from a lab CA generated at start into a volume, never committed (FF-03). Credentials are demo credentials under ADR-018. Mutual TLS is deferred to S12, where the cloud side needs per-gateway X.509 anyway. *(to confirm: Mosquitto over EMQX or others; chosen for size and ACL simplicity, no comparison run)*
3. **The edge only publishes.** Its ACL grants write on its own topic subtree and **no subscription at all**. The consumer's ACL grants read only. Control does not flow from IT to OT, by configuration that a test can check.
4. **Client stack: Python, an OPC UA client and an MQTT client library.** Same language as the collector and the gateway. *(to confirm: the library and its version, and its current API, before writing code)*
5. **Filtering.** The gateway is read at 1 Hz. Baseline publication is one value per tag every 10 s (0.1 Hz). A value is also published at once when it moves beyond a per-tag deadband, when its quality changes, or when it crosses an alarm limit. Deadbands come from a small table committed with the code. *(values to define, open question Q3)*
6. **Payload.** Plain JSON, versioned: `schema` (`"1"`), `edge_id`, `site`, `asset`, `tag`, `value`, `quality`, `ts_src` (UTC, stamped at the source as the collector does), `seq` (per-edge, strictly increasing). Topic `vigilimen/v1/<site>/<asset>/<tag>`. Sparkplug B stays deferred to S12, as already recorded.
7. **Store and forward.** A durable local queue (SQLite in WAL mode on a named volume) is the authority. Publish at QoS 1 with a fixed client identifier and a persistent session. A message leaves the queue only after the broker acknowledges it. After a reconnect, replay in `seq` order. QoS 1 is at-least-once, so the consumer deduplicates on `(edge_id, seq)`. The queue is bounded; when it is full the edge drops the oldest baseline message first, **counts every drop and logs it**. Loss must be visible, never silent.
8. **Network.** `edge` is on `net_supervisory` and `net_dmz`, nothing else. It opens every connection (outbound only).
9. **Accounts.** The edge uses its own OPC UA account, `edge`. Because of ADR-017 this is **attribution only**: the account can still write. See Q2.

## Reasoning

**Why a separate service, not a collector that also publishes.** The thing that persists and the thing that crosses a boundary fail differently, and the second one is the exposed one. A fault or compromise in the edge must not take the plant's own history with it.

**Why a durable queue and not the client library's offline buffer.** An in-memory buffer is lost when the edge restarts during the outage, which is exactly when it is needed. The same reasoning as ADR-019: state that matters is persisted, in a defined order.

**Why report-by-exception on top of a slow baseline.** The baseline keeps the stream alive and bounds the replay volume (about 2,500 messages for a 1 h cut at 7 tags and 0.1 Hz, before exceptions); the exceptions keep the alarm-relevant changes timely.

## Consequences

**Positive.** The historian is untouched. The boundary has one outbound publisher and a broker whose ACL can be tested. The WAN cut test (FF-29) has a defined success criterion: zero loss, ordered replay, drops counter at zero.

**Negative.** Nine services instead of six, and FF-22 pins the set at six. Duplicates reach the consumer by design. Time-stamping depends on the gateway's clock. The lab DMZ network is not internal (a Docker constraint recorded in `dmz-target.md`), so the broker and the jump host have an Internet route a real DMZ would deny.

**Limits to state in the gate report.** The WAN cut is a Docker network disconnect: it shows the replay, not the behaviour of a real radio link (that is a SAT item). The expected results are written by the author of the code.

## Tests (each one an FF; numbers are given when the script is written)

| Property | FF |
|---|---|
| Topology: nine services, zones, multi-homed set, published ports | FF-22 (extended) |
| No OT container has an Internet route, static and live | FF-04 |
| 1 h WAN cut under load: zero loss, ordered replay, drops counter zero | FF-29 |
| Images pinned by digest, SBOM, scan | FF-20 |
| Broker ACL: the edge cannot subscribe; the consumer cannot publish to the edge's topics | proposed new FF |

## Open questions (block acceptance)

- **Q1.** Is `net_supervisory` OT for FF-04? If yes it becomes internal and SCADA, historian and gateway lose their loopback ports unless relays are added (as for the PLC UIs). If no, FF-04 covers `net_control` and `net_safety` only and the report says so.
- **Q2.** ADR-017 means a "read-only" edge account cannot be enforced today. Accept attribution-only for S5 and detect by behaviour (the edge never writes), or bring forward the cheapest fix listed in ADR-017 (a second OPC UA instance exposing measurements only)?
- **Q3.** Deadband per tag and the "load" for the WAN test (message rate, duration) to be fixed before FF-29 is written.
- **Q4.** Who plays the cloud: a host script on the published broker port, or a container? Host script proposed (keeps the service count at nine).

---

*VIGILIMEN-ADR-020 · Sprint 5 · draft*
