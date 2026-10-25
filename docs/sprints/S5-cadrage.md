# S5 — cadrage (brouillon du 26/10/2026, démarrage prévu le 16/11)

Source : plan de livraison, Sprint 5 (22 h, porte M1). Rien ici n'est construit ni testé. À valider par Epiphane.

## Objectif
Les données ne quittent l'OT que par une DMZ ; les fournisseurs aussi. Porte M1.

## Points de départ réels (état au 26/10)
- Le banc a 3 réseaux (`net_control`, `net_supervisory`, `net_safety`). S5 ajoute une DMZ OT et une zone IT : **conséquence sur FF-22**, qui fige aujourd'hui 3 réseaux et 6 services.
- Le collecteur lit déjà le gateway (OPC UA, compte `historian`). L'edge (OPC UA client -> MQTT) est un 7e service ou remplace le chemin du collecteur : **décision à prendre (ADR-020)**.
- ADR-017 : `historian` peut écrire `StartCommand` et `Fault*`. L'edge ne doit PAS réutiliser ce compte en écriture : compte de lecture seule à créer.

## Lots (heures du plan)
| Lot | h | Dépend de |
|---|---|---|
| Edge : client OPC UA -> transformation -> publication MQTT | 4 | ADR-020 |
| Filtrage 1 Hz -> 0,1 Hz + exceptions, version de schéma | 3 | edge |
| Store and forward : file locale, rejeu, contre-pression | 4 | edge |
| Segmentation OT / DMZ / IT : seul le broker traverse | 3 | FF-22 à étendre |
| Accès distant courtié : jump host en DMZ, comptes nominatifs, MFA résistante au hameçonnage, approbation JIT, enregistrement de session, moindre privilège (1 actif, 1 protocole) | 5 | ADR-021 |
| Test de résilience : coupure WAN 1 h sous charge, zéro perte, rejeu ordonné | 3 | store and forward |
| Chaîne d'approvisionnement : images par digest, SBOM (Syft), scan (Grype/Trivy) en CI, Dependabot | 3 | CI |
| Version M1 : tag + DOI (Zenodo) | 1 | tout |

## Décisions à écrire (numéros libres : ADR-020, ADR-021)
- ADR-020 : pile edge (broker MQTT, bibliothèque, chemin collecteur).
- ADR-021 : accès distant courtié (conduit, pas VPN). Le plan l'appelle « ADR-013 » : voir `docs/adr/NUMBERING.md`, on désigne par titre.

## Numérotation des FF : conflit à trancher
Le plan nomme `FF-06` (résilience WAN), `FF-04` (aucun conteneur OT n'a de route Internet) et `FF-20` (chaîne d'approvisionnement). Dans le dépôt, **FF-06 existe déjà** (indépendance de sécurité, 15 cas) et FF-21 à FF-28 sont pris. Proposition, même règle que pour les ADR (les fichiers font foi) : résilience WAN = **FF-29**, route Internet = FF-04 et chaîne d'approvisionnement = FF-20 si libres (aucune trace dans le dépôt le 26/10, sauf une mention de FF-04).

## Porte M1 : critères du plan, avec la preuve attendue
| Critère | Preuve (à construire) |
|---|---|
| Chaîne complète depuis un seul `docker compose up` | script de validation S5 + transcription dans `docs/runs/` |
| Coupure WAN : zéro perte | FF-29 (Docker, hors CI) |
| Aucun conteneur OT n'a de route Internet | FF-04 (lecture du compose) + preuve en direct comme `prove-isolation.ps1` |
| Session fournisseur : ouverte seulement sur approbation, enregistrée, terminable en cours de session | scénario FAT S5, trois cas, chacun avec son pas négatif |
| Images par digest, SBOM, tag + DOI | FF-20 en CI |

## Limites à dire d'avance
- Un jump host simulé en conteneur ne prouve pas la MFA résistante au hameçonnage : on prouve la politique et l'enregistrement, pas le facteur matériel.
- Le test WAN coupe un réseau Docker : il montre le rejeu, pas le comportement d'un lien radio réel (cf. SAT).
- Tout attendu écrit par le même auteur que le code : agrément avec l'exigence, pas preuve indépendante.

## Premier pas proposé
Écrire ADR-020 et ADR-021 en brouillon, étendre FF-22 (réseau DMZ, un seul service qui traverse), puis l'edge sans filtrage.
