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
| **Lot V4.1 (ADR-023 accepté le 15/11, intégré à S5) :** ADR-023, conteneur `fw-cell` (nftables), conteneur `opcua-sup` (lecture seule), repointage edge / collecteur / SCADA, FF-31 à FF-34, mise à jour FF-22 | environ 15 | ADR-023 |
| **Socle entreprise (décidé le 17/11/2026) :** TLS mutuel et ACL sur le broker, limites et dernier-vœu, conteneurs durcis, journaux UTC, modèle de menaces TB-2. Détail et cibles production : `docs/architecture/hardening-targets.md` | environ 8 (estimation de l'auteur) | ADR-020 |

## Décisions à écrire (numéros libres : ADR-020, ADR-021)
- ADR-020 : pile edge (broker MQTT, bibliothèque, chemin collecteur).
- ADR-021 : accès distant courtié (conduit, pas VPN). Le plan l'appelle « ADR-013 » : voir `docs/adr/NUMBERING.md`, on désigne par titre.

## Numérotation des FF : tranché le 26/10/2026
Règle des ADR étendue aux FF (voir `docs/adr/NUMBERING.md`) : les scripts du dépôt font foi. Le plan dit `FF-06` pour la résilience WAN, mais FF-06 est pris : **résilience WAN = FF-29**. Aucun conteneur OT n'a de route Internet = **FF-04**, chaîne d'approvisionnement = **FF-20** (libres : aucune trace dans les scripts).

## Porte M1 : critères du plan, avec la preuve attendue
| Critère | Preuve (à construire) |
|---|---|
| Chaîne complète depuis un seul `docker compose up` | script de validation S5 + transcription dans `docs/runs/` |
| Coupure WAN : zéro perte | FF-29 (Docker, hors CI) |
| Aucun conteneur OT n'a de route Internet | FF-04 (lecture du compose) + preuve en direct comme `prove-isolation.ps1` |
| Session fournisseur : ouverte seulement sur approbation, enregistrée, terminable en cours de session | scénario FAT S5, trois cas, chacun avec son pas négatif |
| Images par digest, SBOM, tag + DOI | FF-20 en CI |

## Révision du 30/10/2026, décidée le 15/11/2026 (conception physique V4.1, ADR-023 accepté)
- Le gateway est aujourd'hui sur `net_control` ET `net_supervisory` : aucun point de politique entre la cellule et le supervisory. Proposition : `fw-cell` devant la cellule, gateway sur `net_control` seul, `opcua-sup` (lecture seule, aucun nœud de commande) pour tout ce qui ne fait que lire (edge, collecteur, vue SCADA).
- Conséquence : la question Q2 d'ADR-020 reçoit la réponse b (le « compte lecture seule » devient une propriété de l'espace d'adressage, pas d'un rôle). Le point de départ ci-dessus sur le compte edge est donc remplacé (ADR-023 accepté le 15/11).
- Services : neuf deviennent onze. Ensemble multi-homed : {`fw-cell`, `edge`, `jump`, `historian`}. Détail : `docs/architecture/dmz-target.md` section 7.
- Numéros : ADR-023 (prochain libre : 024), FF-31 à FF-34 réservés, FF-30 reste proposé.
- Rien n'est construit. ADR-023 est accepté : le banc change au fil de S5 (tâches t242 à t246).

## Limites à dire d'avance
- Un jump host simulé en conteneur ne prouve pas la MFA résistante au hameçonnage : on prouve la politique et l'enregistrement, pas le facteur matériel.
- Le test WAN coupe un réseau Docker : il montre le rejeu, pas le comportement d'un lien radio réel (cf. SAT).
- Un conteneur nftables montre la politique d'un pare-feu de cellule, pas l'appareil sur rail DIN (V4.1, section 22.9).
- Tout attendu écrit par le même auteur que le code : agrément avec l'exigence, pas preuve indépendante.

## Premier pas proposé
Écrire ADR-020 et ADR-021 en brouillon, étendre FF-22 (réseau DMZ, un seul service qui traverse), puis l'edge sans filtrage.

## Deadbands et charge WAN (ADR-020 Q3, décidé le 17/11/2026)
Les deadbands d'exception reprennent ceux du moteur d'alarmes (`plant/alarms/engine.py`), pour ne pas avoir une seconde table de chiffres. Ce sont les valeurs de l'auteur et du simulateur, pas celles d'un ingénieur procédé : le rapport M1 doit le dire.

| Tag | Seuils | Deadband d'exception | Origine |
|---|---|---|---|
| `CONV001.BearingTemp_C` | HI 85 / HI_HI 95 | 2,0 degC | deadband d'alarme |
| `CONV001.Vibration_mms` | HI 4,5 / HI_HI 7,1 | 0,3 mm/s | deadband d'alarme |
| `CONV001.Current_A` | HI 38 / HI_HI 42 | 1,0 A | deadband d'alarme |
| `CONV001.Speed_mps` | LO 2,0 / LO_LO 0,1 | 0,1 m/s | deadband d'alarme |
| `CONV001.Load_tph` | HI 950 / HI_HI 1100 (schéma, pas d'alarme dans le moteur) | 36 t/h | 3 x sigma, le bruit simulé étant sigma = 12 t/h |
| `CONV001.Running`, `CONV001.SafetyTripped` | n/a | à chaque changement | booléens |

Publication immédiate aussi au franchissement d'un seuil et au changement de qualité (ADR-020, point 5).

**Charge du test WAN (FF-29) :** 7 tags à 0,1 Hz, environ 2 500 messages pour une coupure d'une heure ; pendant la coupure, des exceptions injectées (spike vibration +8, puis Clear). Critères : zéro perte, rejeu dans l'ordre de `seq`, compteur de pertes à 0, dédoublonnage sur `(edge_id, seq)`. Run final d'une heure ; en développement, coupure de 5 minutes. Taille de la file : de l'ordre de 10 fois la charge d'une heure (valeur à fixer au moment d'écrire l'edge).
