# ADR-015 — OpenPLC Runtime v3 is end-of-life, and is used anyway

**Status:** Accepted · **Date:** 25 October 2026 · **Deciders:** E. Zaré
**Related:** ADR-003 (simulated plant) · ADR-013 · 62443-4-1 SM-9 (patch management) · **Sprint:** 4

---

## Context

The plant's controllers run OpenPLC Runtime **v3**, built from source into a local image (`openplc:v3`: the image is not in a registry). The v3 repository was **archived on 4 April 2026** and carries a notice that the project has reached end of life and been replaced by Runtime v4.

v4 is not a drop-in. It is headless, driven by the desktop Editor over a REST API with JWT and TLS; there is no web interface to open. It would change how programs are loaded, how the gateway is tested, and what S8 attacks.

## Decision

**Stay on v3 for this programme and record it as a dependency with no upstream.**

## Reasoning

**The plant is meant to be attacked, and v3 is the version much of the published OpenPLC security work was done on.** It is an open-source controller whose whole source is readable, which is why it appears in research papers; v3 also has public weaknesses (for instance CVE-2021-31630, command injection through its hardware-layer page, and a 2026 third-party report of a heap overflow in its Modbus slave-device parser, which I have not reproduced). A simulated plant with a patched controller would teach less about the thing S8 is for.

**Exposure is bounded by construction.** Both UIs are on `internal` networks, published nowhere, reachable only through a temporary relay on loopback (ADR-013). No slave device is configured, so the reported parser path is not reachable from the programme's own use. The default `openplc` / `openplc` login is covered by ADR-018.

**Moving to v4 now would delay S5 to S8 to chase a version the programme does not need yet.**

## Consequences

**Positive.** Web upload, a readable codebase, behaviour that matches most published material.

**Negative.** No security fixes will arrive. The image is built from a clone whose submodules and MatIEC build failed silently once already (see the état des lieux). It must never be exposed beyond loopback; FF-22 checks the ports.

**This is the 62443-4-1 SM-9 finding for the plant itself.** Software with no maintainer is a component the asset owner must either replace, isolate or accept in writing. This ADR is the acceptance, and the isolation is FF-22.

**Revisit when:** S8 is finished, or the programme starts demonstrating something v3 cannot (signed program upload, role-based access), or v4 gains a way to load a program without the desktop Editor. A v4 migration is an ADR of its own, not an edit to this one.

---

*VIGILIMEN-ADR-015 · Sprint 4*
