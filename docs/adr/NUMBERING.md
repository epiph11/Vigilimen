# ADR numbering — rule (26 Oct 2026)

**The ADR files in `docs/adr/` are the numbering authority.** A number is given when the ADR is written (next free number) and never changes afterwards.

The delivery plan's ADR table (inherited from v2.0) numbers some decisions differently (for example its ADR-013 "Brokered remote access over VPN" is, in the repository, ADR-013 "Gateway to PLC over Modbus"). The plan's rows are therefore **referred to by title**, not by number.

Next free number: **ADR-020**. Planned, numbers assigned at write time:

| Decision (plan title) | Sprint | Repository number |
|---|---|---|
| Edge stack | S5 | next free (expected ADR-020) |
| Brokered remote access over VPN | S5 | next free (expected ADR-021) |
| Passive-first discovery | S6 | next free |
| Zone partitioning: consequence, not topology | S7 | next free |
| FAT hold-point criteria | S9 | next free |

Decision taken by default on 26 Oct 2026 (reversible: the alternative is to renumber the repository, which breaks every existing link).
