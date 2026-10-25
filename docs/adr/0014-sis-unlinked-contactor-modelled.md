# ADR-014 — SIS-CONV-001 stays unlinked; its contactor is modelled in the gateway

**Status:** Accepted · **Date:** 25 October 2026 · **Deciders:** E. Zaré
**Related:** ADR-011 (safety separation) · ADR-013 · FF-06 · FF-21 · FF-22 · **Sprint:** 4

---

## Context

ADR-013 gives the control PLC a closed loop. The safety controller cannot have one on the same terms: ADR-011 puts it alone on `net_safety`, and the whole point is that nothing on the control side can reach it. Yet the motor's behaviour depends on its contactor, so the simulation needs *some* contactor state.

## Decision

**`plc-safety` gets no link of any kind.** Its contactor is a Python `SafetyFunction` (`interlock_model.py`) inside the gateway, standing in for the hardwired series connection. The motor turns only if that model is energised **and** the PLC requests run, which is ADR-011's series AND written as one line of code.

Engineering access to the SIS (uploading `safety_upload.st`) is a **deliberate, temporary human act**: `tools/plc-ui-relay.ps1 -Target safety -ConfirmSafety` makes a throwaway container a *second* member of `net_safety`. It is removed afterwards, and `tools/prove-isolation.ps1` fails if one is left behind.

## Reasoning

**A field simulator for the SIS on `net_safety` would be a second member**, and that is the exact property FF-22 forbids. Bridging it to the gateway would hand the control side a route to the safety function, which is what TRITON teaches not to do.

**The alternative that keeps the claim honest is to say what is not exercised.** `safety.st` runs on its own runtime with no I/O wired. Its behaviour is established by FF-21 (the *shape* of the file), by FF-06 (the *model*), and, nowhere yet, by the program itself being driven.

## Consequences

**Positive.** The isolation claim is the strongest one available and is checked three ways: on paper (FF-22), against the live networks (`prove-isolation.ps1`), and in the program text (FF-21).

**Negative, and stated once.** There are two implementations of the safety logic and only one runs in a loop, the Python one. **`safety.st` has never been driven by an input.** That is the drift risk ADR-011 already names, now with a precise shape.

**Follow-up, not done.** Replay the 13 FF-06 vectors against `safety_upload.st` in an **offline** OpenPLC instance on no network. That tests the program without joining anything.

**An isolation proof that cannot fail proves nothing.** The earlier instruction, `ping sis-conv-001` from the PLC, failed on a bad *name* (`sis-conv-001` is a `hostname:`, never resolvable) whether or not the networks were joined. `prove-isolation.ps1` tests by IP address, treats a *refused* connection as a **failure** (a refusal is a packet from the far side, so a route exists), and runs a positive control first.

---

*VIGILIMEN-ADR-014 · Sprint 4*
