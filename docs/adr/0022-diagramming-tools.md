# ADR-022 — Diagramming tools: draw.io for drawings, Archi for ArchiMate, Mermaid for C4 in the docs site

**Status:** Proposed — to be accepted by E. Zaré · **Date:** 26 October 2026 · **Deciders:** E. Zaré
**Related:** ADR-006 · S5 cadrage · delivery plan §5 ("docs-as-code site", "C4 diagrams as Mermaid") · **Sprint:** from S5

> Number note: ADR-020 and ADR-021 stay reserved for the two S5 decisions (edge stack, brokered remote access). This ADR takes the next number after them. Update `docs/adr/NUMBERING.md` when it is accepted.

---

## Context

The delivery plan lists many diagrams (C4 L1/L2, Wardley, the S7 zone/conduit drawing) but names no drawing tool and no owner. Until now several diagrams (`docs/img/01` to `06`) were generated, not drawn, and the handover lists them as stale.

The owner wants to draw the architecture himself, with proper tools, and to produce many diagrams to clarify the programme. Two reasons:

- the S7 zone/conduit drawing is the most valuable artifact of the programme, and a text-rendered diagram does not show drawing skill;
- an architect profile (TOGAF Practitioner) is better evidenced by ArchiMate and hand-drawn views than by generated ones.

Constraints: the repository is public and the source of truth; no paid licence is justified on a personal budget; every source file must be readable in a Git diff or at least diffable as text.

## Decision

| Need | Tool | Source kept in the repo | Export |
|---|---|---|---|
| Zones and conduits, DMZ, sequences, runbook flows | **draw.io** (diagrams.net, desktop, offline) | `.drawio` (XML, uncompressed) | SVG and PDF |
| Enterprise view: motivation (CIRMP clause → CRS requirement → component), business/technology layers | **Archi** (ArchiMate 3.x) | `.archimate` (XML) | SVG, and CSV for the register |
| C4 levels maintained next to the text | **Mermaid** inside the MkDocs site | Markdown | rendered by the site |
| Wardley map | draw.io | `.drawio` | SVG |

**Rules**

1. The source file is committed next to its export. An export without its source is not accepted.
2. Files live in `docs/architecture/diagrams/`, named `<sprint>-<slug>.drawio` (for example `S7-zones-conduits.drawio`).
3. Drawings of zones and conduits are made **from the YAML register** (S7), not the other way round. Zone names, SL-T and conduit identifiers are copied from it. A drawing that disagrees with the register is a defect.
4. Every diagram carries: title, sprint, date, version, and a legend. Colours are not the only carrier of meaning.
5. draw.io files are saved **uncompressed** (File > Properties > Compressed off) so that Git diffs show something.
6. Generated diagrams in `docs/img/` are either redrawn with this ADR or removed. They are not mixed with drawn ones.

## Reasoning

**Why draw.io.** Free, offline, runs on Windows, and its file is XML. Not verified here: the exact diff quality of an uncompressed file. To be checked on the first drawing.

**Why Archi and not Sparx Enterprise Architect.** Archi is free and open source and covers ArchiMate. Sparx EA is paid and stores the model in a database or binary file, which cannot be reviewed in Git and does not fit a public repository. Sparx remains a valid skill to acquire if target employers ask for it. If so, learn it on a trial outside the repository.

**Why not Mermaid for everything.** It stays for C4 in the site because it is maintained as text. It lays out zone and conduit drawings poorly, and it does not show drawing skill.

## Consequences

**Positive.** A set of drawn artifacts a reader can open; ArchiMate evidence next to the TOGAF background; no licence cost.

**Negative.** Extra time, **not in the delivery plan**: estimated at 1 to 2 hours per diagram, placed in light weeks. Estimate only, to be replaced by measured hours after the first three drawings. Two tools to learn. Source files diff poorly compared to code.

**Review.** Reconsider at the M3 gate. If the diagrams cost more than the cycle's light-week budget, cut the Archi models first, never the S7 drawing.

---

*VIGILIMEN-ADR-022 · from Sprint 5 · proposed*
