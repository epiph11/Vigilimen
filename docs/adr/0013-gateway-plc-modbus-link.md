# ADR-013 — The gateway plays the field and drives PLC-CONV-001 over Modbus

**Status:** Accepted — FF-26 passed with the PLC in the loop in Docker on 25 October 2026 · **Date:** 25 October 2026 · **Deciders:** E. Zaré
**Related:** ADR-003 (simulated plant) · ADR-005 (boundary) · ADR-011 · ADR-014 · **Sprint:** 4

---

## Context

Through Sprint 4 the plant was two things sitting next to each other. The gateway computed the physics **and** ran `interlock_model.py`, a Python model of both controllers. The two OpenPLC containers ran their programs against nothing: no I/O was linked, and `VIGILIMEN_MODBUS_HOST` was set and never read. The demo proved the network layout and the OT/IT split. It did not prove a control loop, and S8 cannot attack a loop that does not exist.

## Decision

**The gateway plays the field. PLC-CONV-001 owns the sequence and the machine protection.**

Each 0.5 s cycle the gateway writes the simulated inputs (start, stop, zero speed, two permissives, bearing temperature, motor current, belt speed) to the PLC as one FC 15 and one FC 16, reads back the run request, horn, alarm word, state and a signature, and turns the motor only if **contactor energised AND PLC run request**.

| | |
|---|---|
| Direction | Gateway is the Modbus **client** and opens every connection; the PLC is the server |
| Addresses | `%QX100.0..4`, `%QW100..102` in; `%QX101.0..1`, `%QW110..112` out. Coil = byte×8+bit, register = word number (OpenPLC slave range) |
| Source of truth | `plant/gateway/plc_io_map.py`. `conveyor.st` declares the same variables with `AT`; **FF-23** fails on any disagreement |
| Opt-in | `VIGILIMEN_PLC_LINK=modbus`, set by `docker-compose.plcio.yml`. The default stays *embedded* until validated, so 4e keeps its meaning |

Three behaviours are the substance, and **FF-24** exercises each against a fake OpenPLC:

1. **Fail safe.** No answer is *no run request*, the statement `control is None` already makes in the model. Reconnects are rate-limited and run in a worker thread so a dead PLC cannot freeze OPC UA.
2. **Signature first.** The first FF-24 run showed a read-back cannot see a missing *idle* input, and the real OpenPLC went further: it **stores and reads back a write to an address no program locates** (measured: with an old program, HR100 and coils 801 to 804 held the gateway's values). So the read-back proves nothing about the program. `Plc_Map_Version` is the detector: a PLC reporting another number is not trusted. A program with the right signature but a missing input is caught only by FF-23, in the commit.
3. **The PLC UI is not on this link.** See Consequences.

## Reasoning

**Why client, not OpenPLC as master with the gateway as a Modbus server.** OpenPLC would poll the gateway through *slave devices*, configured only in the web UI and stored in its database, so the wiring is neither reproducible nor reviewable. It would also reverse the north-south arrow: the field simulator would be on the listening side.

**Why `%QX/%QW` for inputs.** A Modbus master cannot write `%IX` or `%IW`. The program therefore only *reads* variables that live in the output space. This is a simulation device and is stated as one in `conveyor.st`; FF-23 fails if the program ever assigns one.

**Why not fix `hostname:`.** The compose file named the PLC by its `hostname:` (`plc-conv-001`). Docker's DNS answers for service names, container names and aliases, **not** hostnames, so that value would have failed with an error that reads like a network fault. It is now `plc-control`, and FF-22 checks the name is resolvable.

## Consequences

**Positive.** A real loop: START now waits for the 10 s horn from `conveyor.st`; the 95 °C trip, the 42 A trip and the fault-reset rule are the program's, not Python's.

**Negative.** Modbus authenticates nobody (protocol-register.md). OpenPLC has **no write allow-list**, so anything on net_control can write any `%Q` variable. ADR-005 condition 3 is not met here; the segmentation is the only control, which is the S8 target and is recorded rather than fixed.

**The PLC web UIs are unreachable.** Both networks are `internal: true`, and Docker ignores `ports:` on an internal network, so `8081`/`8082` in compose do nothing. `tools/plc-ui-relay.ps1` attaches a throwaway socat container for the length of an upload.

**Proven in Docker, 25 October.** MatIEC accepts the located variables only once they are in a `VAR` block of their own: mixing located and plain declarations in one block fails with `invalid located variable declaration` on every plain line, a cascade no text-level check could see (FF-23 now checks the shape). Then: runtime rebuilt, `%QW112` read at holding register 112 (`Plc_Map_Version` = 1), `%QW100` at HR100, the gateway reports `read-back clean`, START waits 10.4 s for the horn, and a spike reaches `alarm_event` in 0.60 s.

**Still not proven.** The 95 °C and 42 A trips and the fault-reset rule have run in the fake PLC only; `conveyor.st` itself has not been driven through them in Docker.

---

*VIGILIMEN-ADR-013 · Sprint 4*
