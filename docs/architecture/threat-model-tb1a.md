# Threat model v1: update TB-1a (Z1 cell <-> Z2 supervisory)

Split out of `threat-model-v1.md` on 17 Nov 2026 because FF-01 caps that file at 115 lines (it was 125). The text below is unchanged except its heading level.

### Update 30 Oct 2026 — TB-1a, Z1 cell ↔ Z2 supervisory (proposal, ADR-023 draft)

Inside the plant, between the cell and the readers. Not in scope of v1 because the lab had no policy point there (the gateway sat on both networks). With `fw-cell` (conduit C1) it becomes a boundary.

| | Threat | Mitigation | Carried to |
|---|---|---|---|
| **S** | A host in Z2 impersonates the supervisory server toward the gateway | Only `opcua-sup` and the operator command path may open C1 (FW-CELL-001, 002); default deny and log | FF-32 |
| **T** | A reader alters a command or fault tag | `opcua-sup` has no writable node; the edge and collector have no path to the gateway | FF-33 |
| **R** | A start command cannot be attributed (ADR-017) | Unchanged for the operator path (R-14); `fw-cell` logs every C1 flow as evidence | S8, S24 |
| **I** | Process data read from the cell by an unintended host | Only `opcua-sup` is allowed to read the gateway; secure channel on the supervisory side | FF-32 |
| **D** | A flood from Z2 degrades the gateway | Rate and connection limit on FW-CELL-001; the gateway is no longer reachable from the DMZ (F-DENY-01R) | FF-34 |
| **E** | Compromised edge reaches the PLC | Edge is in Z2 with no route to Z1 except through `opcua-sup`'s read path; no conduit from Z3 to Z1 or to ZS | FF-31, FF-34 |

The safety zone ZS has **no conduit** by construction; the table carries no row for it (as for command flows at TB-1, ADR-005). SL-T per zone is a placeholder until S7.
