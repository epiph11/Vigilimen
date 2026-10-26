# Diagram plan (draft of 26 Oct 2026, see ADR-022)

Nothing here is drawn yet. Hours are estimates, not in the delivery plan. Priority: **P1** = mandatory, **P2** = useful, **P3** = if time. Light weeks only; a lost heavy week does not move this plan.

| Sprint | Diagram | Tool | Priority |
|---|---|---|---|
| Before S5 | Target DMZ: OT / DMZ / IT, only the broker crosses | draw.io | P1 |
| S5 | C4-L2 refresh after the edge and the DMZ | Mermaid or draw.io | P1 |
| S5 | Brokered vendor session: request, approval, recording, termination (sequence) | draw.io | P1 |
| S5 | Store and forward: normal, WAN cut, replay (sequence or states) | draw.io | P2 |
| S6 | Passive capture topology: where Zeek sees the traffic | draw.io | P1 |
| S6 | As-built vs as-documented delta (what the documents got wrong) | draw.io | P2 |
| S7 | **Zone and conduit drawing with SL-T annotated (ZCR 6)** | draw.io | **P1, the key artifact** |
| S7 | Motivation view: CIRMP clause > CRS requirement > component | Archi | P1 |
| S8 | Attack paths for the four attacks, with the detection point of each | draw.io | P1 |
| S9 | FAT > SAT > cutover flow, hold points marked | draw.io | P1 |
| S10 | Supplier and critical component map (CIRMP s10A) | draw.io | P2 |
| S11 | CIRMP s8C independence: what must work with every external link cut | draw.io | P1 |
| S11 | OT incident decision flow (who decides the shutdown) | draw.io | P2 |
| S12 to S18 | Cross-cloud context and integration event flow | draw.io + Archi | P2 |
| S26 | Independence proof: severed dependencies and what failed first | draw.io | P1 |
| S28 to S29 | Storyboards of the two demonstrations; dossier overview | draw.io | P2 |

**Count:** 16 diagrams (10 P1, 6 P2), of which 9 P1 before S12; 20 to 30 hours over eight cycles if the estimate holds.

## Before 16 Nov (S5 preparation, added 26 Oct)

Hours are estimates, not measured. Do them in this order; each one feeds the next decision.

| # | Diagram | Tool | h | Feeds | Source |
|---|---|---|---|---|---|
| D1 | **Target DMZ**: zones, networks, the four multi-homed services, flows F1 to F7 with initiator, forbidden flows | draw.io | 2 | ADR-020, ADR-021, FF-22 extension | `docs/architecture/dmz-target.md` (brief in section 6) |
| D2 | **Vendor session**: request, approval, certificate, session, recording, termination, and the three refusal branches | draw.io | 1.5 | ADR-021, the remote-access FF | ADR-021 |
| D3 | **Edge data path and store-and-forward**: online, offline, replay, queue, `seq`, drops counter | draw.io | 1.5 | ADR-020, FF-29 | ADR-020 |

Total about 5 h. After S5 starts: C4-L2 refresh (the existing `c4-l2-ot.html` predates the edge and the DMZ).

## Checks before a diagram is accepted
- Source and export both in the repository (ADR-022 rule 1).
- Names, SL-T and conduit ids match the YAML register (from S7).
- Title, sprint, date, version and legend present.
