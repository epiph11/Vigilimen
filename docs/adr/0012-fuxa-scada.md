# ADR-012 — FUXA for SCADA. This is a licence decision.

**Status:** Accepted · **Date:** 14 September 2026 · **Deciders:** E. Zaré
**Related:** ADR-003 (simulated plant) · **Sprint:** 4

---

## Context

The plant needs a SCADA and HMI layer: a mimic an operator can watch, an alarm surface, and a client that speaks OPC UA to the gateway.

The obvious candidate is **Ignition Maker Edition** — free, capable, and the engine a great many Australian sites actually run. FUXA is the smaller open-source alternative.

**A feature comparison would favour Ignition and would be the wrong comparison to make.**

---

## Decision

**FUXA, MIT licence.**

---

## Why — and it is not about features

Ignition Maker Edition is free for **personal, non-commercial use**, and its terms name *sales demonstrations* among the prohibited uses.

This programme is a portfolio built to win work. It will be shown to recruiters and hiring managers, and its explicit purpose is to change what its author can be hired to do. **That sits squarely inside the prohibition, whatever else it is.**

The argument is not that anyone would enforce it. Nobody would. The argument is that **a security portfolio containing a licence violation is a portfolio whose author did not read the licence** — and licence literacy is not incidental to this role. Every 62443-4-1 supply chain question, every software bill of materials, every third-party component review runs on exactly this skill. Getting it wrong on one's own repository is a poor advertisement for getting it right on somebody else's.

FUXA's MIT licence carries no restriction on purpose, on commercial use, or on demonstration. The choice costs some capability and removes an entire question.

---

## What it costs

FUXA is genuinely less capable. Fewer drivers, a smaller component set, less mature scripting, a much smaller community, and no equivalent of Ignition's tag historian.

**Two of those are absorbed and one is not.**

- *Drivers* do not matter here: the gateway speaks OPC UA and FUXA is an OPC UA client. One protocol, well supported.
- *Historian* is absorbed because TimescaleDB is the historian (see `plant/historian/schema.sql`), which is the better architecture anyway — a historian inside the HMI is a historian that dies with the HMI.
- *Maturity* is the real cost, and it is accepted. Some things will need building by hand that Ignition provides.

---

## The honest note for an interview

If asked *"why not Ignition?"* the answer is the licence, stated plainly — not a claim that FUXA is better. **Pretending the open tool won a feature comparison it did not win is the kind of small dishonesty that costs credibility on everything else in the room.**

And the follow-up is worth volunteering: on a real site the answer would very likely be Ignition, properly licensed, because the maturity is worth paying for. The constraint here is a US$333 programme budget and a portfolio purpose, not a technical judgement about the products.

---

## Consequences

**Positive.** No licence question anywhere in the repository. The historian is architecturally separate from the HMI, which is where it belongs. The whole stack stays permissively licensed and freely shareable.

**Negative.** More hand-building at S4, and the SCADA layer will look less polished than a comparable Ignition project. Anyone who knows Ignition will notice.

**Revisit if** an employer funds a licence, or the programme stops being a portfolio.

---

*MINED-ADR-012 · Sprint 4*
