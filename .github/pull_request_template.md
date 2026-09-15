## What changed

<!-- One or two sentences. What is different after this PR that was not true before. -->

## Why

<!-- The problem, not the solution. If the answer is "because the sprint said so", link the sprint. -->

---

## Architectural decision

- [ ] This PR makes a structural decision, and **ADR-___ is included in it**
- [ ] This PR implements a decision already recorded in **ADR-___**
- [ ] No structural decision here

> A structural decision is one that is expensive to reverse: a boundary, a protocol, a dependency, a data flow across a zone, anything that constrains what can be built next.
>
> **"I'll write the ADR later" is not one of the options.** The reasoning is available now and will not be in three weeks.

## Safety and security

- [ ] This change does **not** place any control inside the trip path of a protective function *(MINED-ARC-001 — hard constraint)*
- [ ] This change does not create a communication path across a zone boundary — or it does, and the **conduit register is updated in this PR**
- [ ] This change does not introduce an IT → OT control path — or it does, and **ADR-005's four conditions are each addressed above**

> A path that exists and is not registered is a defect, whether or not it is exploitable.

## Cost

- [ ] No resource on the never-create deny-list is introduced *(FF-13 will fail the build if one is)*
- [ ] Anything billable is inside a scripted apply → evidence → destroy window, with teardown in `if: always()`

## Verification

- [ ] Fitness functions pass
- [ ] Claims of fact carry a source, and a claim that could not be verified against a primary source **says so inline** rather than being asserted

<!-- The last box is the one that matters most. An unverified claim that admits it is
     more useful than a confident one that turns out to be wrong. -->
