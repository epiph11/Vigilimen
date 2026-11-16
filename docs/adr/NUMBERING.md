# ADR numbering — rule (26 Oct 2026)

**The ADR files in `docs/adr/` are the numbering authority.** A number is given when the ADR is written (next free number) and never changes afterwards.

The delivery plan's ADR table (inherited from v2.0) numbers some decisions differently (for example its ADR-013 "Brokered remote access over VPN" is, in the repository, ADR-013 "Gateway to PLC over Modbus"). The plan's rows are therefore **referred to by title**, not by number.

Next free number: **ADR-024** (updated 30 Oct 2026: ADR-020 to 022 exist, ADR-023 accepted 15 Nov 2026). Planned, numbers assigned at write time:

| Decision (plan title) | Sprint | Repository number |
|---|---|---|
| Edge stack | S5 | next free (expected ADR-020) |
| Brokered remote access over VPN | S5 | next free (expected ADR-021) |
| Passive-first discovery | S6 | next free |
| Zone partitioning: consequence, not topology | S7 | next free |
| FAT hold-point criteria | S9 | next free |

Decision taken by default on 26 Oct 2026 (reversible: the alternative is to renumber the repository, which breaks every existing link).

## Fitness functions (FF) : même règle (décidé le 26/10/2026)

**Les scripts du dépôt (`scripts/ff*.py`, `.sh`) font foi.** Un numéro FF est donné quand le script est écrit, jamais réutilisé. Le plan de livraison a ses propres numéros FF : ses lignes sont désignées par leur intitulé.

Pris au 26/10 : FF-01, 02, 03, 05, 06, 07, 13, 14, 21 à 28. Libres : FF-04, 08 à 12, 15 à 20, et à partir de FF-29.

| Intitulé (plan) | Numéro dans le dépôt |
|---|---|
| Résilience coupure WAN (le plan dit FF-06, déjà pris par l'indépendance de la sécurité) | **FF-29** |
| Aucun conteneur OT n'a de route Internet | FF-04 |
| Chaîne d'approvisionnement (digests, SBOM, scan) | FF-20 |

## Update 30 Oct 2026

- **ADR-023** (cell firewall and read-only supervisory OPC UA server) is Accepted (15 Nov 2026, nothing built). Next free ADR: **024**.
- **FF-31 to FF-34** are reserved for ADR-023 (accepted, scripts not written). FF-30 stays proposed for the vendor scenarios. Taken or reserved list is otherwise unchanged.

- **ADR-024** (operator command service, Proposed 16 Nov 2026, target S8) is drafted. Next free ADR: **025**.
