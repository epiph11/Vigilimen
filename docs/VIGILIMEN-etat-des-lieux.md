# Vigilimen — état des lieux complet (Stations 1 à 4, liaison PLC validée dans Docker)

Dernière mise à jour : 25 octobre 2026, 16 h. Même contenu que le doc du projet « MINE 360 » (`claude/VIGILIMEN-etat-des-lieux.md`). Schémas : `docs/img/` (à régénérer : ils décrivent l'état d'avant la liaison PLC).

## En bref

La station CONV-001 (un convoyeur de mine simulé) tourne en local dans six conteneurs Docker : deux automates OpenPLC, un gateway OPC UA, un historien TimescaleDB, un collecteur et un SCADA FUXA. Les stations 1 à 4 sont faites. **Le 25/10, 4e, la liaison PLC, la persistance des alarmes et l'isolation ont été validés dans Docker.**

**Vérifié sur la machine d'Epiphane (avant le 25/10)**

- Six conteneurs sains ; `conveyor.st` et `safety.st` compilent et tournent dans OpenPLC (version d'avant les variables `AT`).
- Le PLC de commande ne peut pas atteindre le PLC de sécurité (preuve réseau capturée, mais voir le constat sur le `ping`).
- Le gateway refuse les sessions anonymes ; le collecteur écrit 7 tags par seconde ; FUXA affiche les valeurs et START fait démarrer le convoyeur.

**Validé dans Docker le 25/10 (logs dans `docs\runs\`)**

| Élément | Résultat |
|---|---|
| 4e sur le modèle embedded (`validate-4e.ps1`, FF-26) | 7/7. Alarme Vibration HI_HI puis RTN_UNACK dans `alarm_event`. FUXA (import, START, Spike, Clear) confirmé à la main |
| Liaison gateway ↔ PLC-CONV-001 en Modbus (ADR-013, **Accepted**) | `linked to plc-control:502, read-back clean`. START attend **10,4 s** (l'avertisseur de `conveyor.st`). Spike → ligne `alarm_event` en **0,60 s** |
| Compilation de `conveyor.st` avec les variables `AT` | OK **après correction** : MatIEC refuse un bloc `VAR` qui mélange variables localisées et ordinaires. `%QW112` = registre 112 (signature lue = 1) |
| Persistance des alarmes (ADR-019, **Accepted**) | Redémarrage du collecteur en pleine alarme : un seul `NORMAL→UNACK`, `alarm_state` conservé. Le déclencheur refuse un UPDATE sur `alarm_event` |
| Isolation du SIS en direct (`prove-isolation.ps1`) | 7/7 : un seul membre, DNS non résolu, `Network is unreachable` par IP vers 8080 et 502, témoin positif CONNECTED |

**Pas encore prouvé**
- Les déclenchements 95 °C et 42 A, et la règle de remise à zéro des défauts, ont tourné dans le faux PLC seulement, pas dans OpenPLC.
- `safety.st` n'a jamais reçu d'entrée (ADR-014) ; rejouer les 13 vecteurs de FF-06 hors réseau reste à faire.
- Redémarrage du collecteur pendant qu'une alarme est SHELVED ; DELETE et TRUNCATE sur `alarm_event` (volontairement non testés).
- Le mode par défaut du compose reste *embedded* ; passer au mode PLC par défaut est un changement à part.

**Reste ouvert**
- Aucun commit : huit commits proposés dans `docs\runs\COMMITS.md`, rien n'est poussé. Un fichier a changé depuis la proposition (`prove-isolation.ps1`, `conveyor.st`, FF-23, FF-24) : relire avant de valider.
- Station 5 : sept constats (F1 à F7) dans `docs/assessments/hydro-station/EVALUATION-station5.md`.
- Le walkthrough (rev 1.2) dit encore « jamais lancé » dans sa table d'état : à passer en rev 1.3.
- FF-03 échoue sur ton `my-notes.md` ligne 66 (clé d'exemple écrite en clair ; fichier ignoré par git).

## Vue d'ensemble

```text
net_supervisory
  [SCADA FUXA :1881] <--OPC UA--> [Gateway OPC UA :4840] --OPC UA--> [Collecteur 1 Hz] --SQL--> [Historien :15432]
                                  (dans les deux réseaux)

net_control (internal)
  [Gateway] ==Modbus FC15/16/1/3, client== [PLC-CONV-001 :502]     (mode plcio seulement ; sinon non câblé)

========= aucune route entre net_control et net_safety (FF-22 sur le papier, prove-isolation.ps1 en vrai) =========

net_safety (internal, un seul membre)
  [SIS-CONV-001, safety.st]   aucune liaison. Son contacteur est un modèle Python dans le gateway (ADR-014)
```

Ports sur 127.0.0.1 seulement (1881 FUXA, 14840 OPC UA, 15432 base). **8081 et 8082 ne fonctionnent pas** : Docker ignore `ports:` sur un réseau `internal`. Les interfaces OpenPLC s'ouvrent par `tools\plc-ui-relay.ps1`, un conteneur socat jetable.

## Le chemin d'une valeur

```text
FUXA boutons --OPC UA--> Gateway, boucle de 0,5 s (plant_cycle.py) :
  mode par défaut ("embedded") :              mode plcio ("modbus") :
    interlock_model joue les deux contrôleurs   entrées simulées --Modbus--> PLC-CONV-001 (séquence, 95 °C, 42 A)
                                                run request <--Modbus-- PLC ; moteur = contacteur ET run request
  physique (courant, vibration, température) --> tags ns=2;i=6..12, status PLC i=20..22
       |-- OPC UA --> FUXA écran
       '-- OPC UA, 1 Hz --> Collecteur --> sample + AlarmFeed/engine --> alarm_event (+ alarm_state, mode plcio)
```

Avec le PLC dans la boucle, **START attend l'avertisseur de 10 s** de `conveyor.st` ; en mode embedded il est immédiat. Si le PLC ne répond pas ou que sa signature ne correspond pas, le gateway n'émet aucune demande de marche (échec sûr).

## Comment chaque valeur est calculée

Calculées par le gateway toutes les 0,5 s (`plant/sim/conveyor_physics.py`), pas mesurées.

| Valeur | Formule (convoyeur en marche) |
| --- | --- |
| Load (t/h) | `0,78 × 850 + 0,10 × 850 × sin(t/220) + bruit` ; 0 à l'arrêt |
| Belt speed (m/s) | `2,5 × (1 − 0,18 × belt_slip)` |
| Motor current (A) | `8 + 30 × charge/850` + bruit, × défauts (glissement +22 %, galet +30 %, usure +5 %) |
| Vibration (mm/s) | `1,6 + 0,4 × charge/850` + bruit ; défauts : usure `5,5 × usure^1,5`, désalignement `+4,0`, galet `+2,0`, spike `+valeur`. **0 à l'arrêt** |
| Bearing temperature (°C) | tend vers `28 + 26 × charge/850` (+34 usure, +12 galet), constante 420 s ; retour vers 28 °C à l'arrêt, 900 s |

Mesuré le 25/10 : l'usure à 100 % seule plafonne vers **85 °C** ; atteindre 95 °C demande usure **et** galet grippé, environ **50 minutes**, et le déclenchement sur 42 A peut venir avant.

## L'isolation de la sécurité

Le SIS est seul sur `net_safety` (`internal: true`). Ce qui le prouve maintenant :

- **FF-22** lit les fichiers compose fusionnés : un seul membre, ports en loopback, nom du PLC résolvable, six services attendus.
- **`tools\prove-isolation.ps1`** compte les membres du réseau, teste **par adresse IP**, traite un `REFUSED` comme un **échec** (un refus est un paquet venu de l'autre côté), et fait d'abord un test témoin positif.
- **FF-21** lit `safety.st` ; **FF-06** lit le modèle.

L'ancienne preuve `ping sis-conv-001` était vide : `sis-conv-001` est un `hostname:`, que le DNS de Docker ne résout jamais, donc elle échouait sur le nom, réseaux joints ou non.

## Les alarmes ISA-18.2

États : NORMAL, UNACK, ACKED, RTN_UNACK, SHELVED, SUPPRESSED, OOS. L'état qui compte est RTN_UNACK (revenue normale, jamais vue).

| Tag | Condition | Limite | Priorité | Délai |
| --- | --- | --- | --- | --- |
| BearingTemp_C | HI / HI_HI | 85 / 95 °C | HIGH / URGENT | 10 s / aucun |
| Vibration_mms | HI / HI_HI | 4,5 / 7,1 mm/s | LOW / HIGH | 30 s / aucun |
| Current_A | HI / HI_HI | 38 / 42 A | LOW / HIGH | 5 s / aucun |
| Speed_mps | LO / LO_LO | 2,0 / 0,1 m/s | LOW / HIGH | 15 s / aucun |

**Persistance (ADR-019, mode plcio).** Avant : un redémarrage du collecteur pendant une alarme acquittée la relevait en nouvel UNACK, perdait l'acquittement et écrivait deux fois l'incident. Maintenant l'état (`alarm_state`) est écrit dans **la même transaction** que les événements, chargé une fois au démarrage, et `alarm_event` est protégé par un déclencheur contre UPDATE/DELETE/TRUNCATE (pas un contrôle de sécurité : le propriétaire de la table peut le supprimer). Un volume existant demande `migrations/001_alarm_state.sql` une fois. Corrigé au passage : `pending()` avançait son repère avant l'insertion, donc un insert échoué perdait les événements.

## Inventaire

| Composant | Fichier | Rôle | Statut |
| --- | --- | --- | --- |
| Logique de commande | `plant/plc-control/conveyor.st` | Séquence, 95 °C, 42 A ; variables `AT` en bloc `VAR` séparé (ADR-013) | Compile et tourne dans OpenPLC |
| Logique de sécurité | `plant/plc-safety/safety.st` | Fonction de sécurité | Compile ; jamais pilotée par une entrée |
| Contrat E/S | `plant/gateway/plc_io_map.py` | Table unique des adresses, `MAP_VERSION` | FF-23 |
| Liaison PLC | `plant/gateway/plc_link.py`, `plant_cycle.py` | Client Modbus, échec sûr, signature | Validée dans Docker ; FF-24 (faux PLC) |
| Gateway OPC UA | `plant/gateway/opcua_server.py` | ISA-95, comptes, défauts i=15..19, statut PLC i=20..22 | Mode par défaut = embedded |
| Chargement OpenPLC | `plant/plc-upload/build.py` | Génère `*_upload.st` | À rejouer après chaque édition |
| Collecteur | `plant/historian/collector.py`, `alarms/store.py` | 7 tags à 1 Hz, alarmes, persistance | Persistance validée ; désactivée par défaut |
| Historien | `plant/historian/schema.sql`, `migrations/` | `sample`, `alarm_event`, `alarm_state` | Migration appliquée le 25/10 |
| SCADA | `plant/scada/project/` | Projet FUXA généré | Fichier d'import |
| Orchestration | `plant/docker-compose.yml` + `docker-compose.plcio.yml` | 6 services, 3 réseaux | override = opt-in |
| Outils | `plant/tools/` | `validate-4e`, `validate-plcio`, `prove-isolation`, `plc-ui-relay` | Lancés le 25/10 |

## Blocages rencontrés et corrections

**Avant le 25/10** (inchangés) : Docker/WSL arrêté ; image `openplc:v3` absente du registre ; build OpenPLC « vert » mais cassé (CRLF, MatIEC, `tee`) ; bail containerd expiré (veille) ; imports asyncua ; sonde de santé ; `.st` refusés (bits d'un WORD, CONFIGURATION) ; relais socat pour les UI ; page FUXA blanche ; boutons FUXA ; image gateway ancienne sans les nœuds `Fault*` (`build` puis `up -d`).

**Le 25/10, en local (détail dans `docs/runs/NOTES.md`) :**

| Symptôme | Cause | Correction |
| --- | --- | --- |
| FF-24 : « PLC perdu » ne coupait pas la marche | Double de test : `shutdown()` laisse les connexions établies | `stop()` ferme les sockets |
| FF-24 : un programme sans `Stop_PB` non détecté à l'arrêt | **Défaut de conception** : un coil non localisé lit FALSE, ce qu'on avait écrit | Signature `Plc_Map_Version` vérifiée à chaque cycle |
| `VIGILIMEN_MODBUS_HOST: plc-conv-001` | C'est un `hostname:`, non résolu par le DNS Docker | `plc-control` ; FF-22 le vérifie |
| `ping sis-conv-001` | Ne pouvait pas échouer autrement | `prove-isolation.ps1` |
| `pending()` perdait les événements sur insert échoué | Repère avancé avant le commit | Avancé après le commit (FF-25) |

**Le 25/10, dans Docker (détail dans `docs/runs/NOTES.md`) :**

| Symptôme | Cause | Correction |
| --- | --- | --- |
| Gateway : `program signature 0, expected 1` | Le nouveau programme n'avait jamais été compilé en binaire (binaire du runtime daté 02:24 alors que le téléversement datait de 05:25) | Voir la ligne suivante |
| Compilation : `invalid located variable declaration` sur les lignes ordinaires, puis 40 erreurs `invalid variable before ':='` | MatIEC veut un bloc `VAR` entièrement localisé ou entièrement ordinaire ; je les avais mélangés. FF-23 et FF-24 lisent le texte et ne lancent pas MatIEC | Deux blocs `VAR` ; FF-23 vérifie la forme. Compilation confirmée avec `iec2c` dans le conteneur, puis dans l'interface |
| OpenPLC garde une écriture Modbus à une adresse qu'aucun programme ne déclare (mesuré : HR100 et coils 801 à 804 avec l'ancien programme) | Le faux PLC de FF-24 supposait le contraire | La relecture ne prouve rien sur le programme ; seule la signature le fait. FF-24, `plc_link.py` et ADR-013 corrigés |
| `prove-isolation.ps1` : `bad character U+002D '-'`, puis trois FAIL | Windows PowerShell 5.1 retire les guillemets doubles internes passés à `docker inspect` : faux négatifs de mon script, pas de l'isolation | Adresses lues dans le JSON de `docker inspect` ; arrêt clair si une adresse manque |

## Constats et limites

| Constat | Pourquoi c'est important | Statut |
| --- | --- | --- |
| `historian` et `engineer` ne diffèrent que par l'attribution : `historian` peut écrire `StartCommand`, `StopCommand` et `Fault*` | Le collecteur prétendait ne rien pouvoir écrire ; commentaire corrigé | ADR-017, cible S8 |
| Rien n'enregistre qui a écrit un `Fault*` | Un défaut falsifié est indiscernable d'un défaut injecté | ADR-016 |
| OpenPLC v3 archivé le 4 avril 2026, remplacé par v4 (sans interface web) | Aucun correctif à attendre | ADR-015 |
| Pas de liste blanche d'écriture dans OpenPLC | N'importe quoi sur `net_control` écrit n'importe quelle variable `%Q`, et même des adresses non déclarées | ADR-013 |
| Un programme avec la bonne signature mais sans `Stop_PB` n'est détecté qu'à la validation (FF-23) | Aucune détection à l'exécution | FF-24 le documente |
| Mots de passe de démo | ADR-007 couvre le cloud ; la démo a ses règles et son registre | ADR-018 |
| Canal OPC UA `NoSecurity` | Mot de passe en clair sur le réseau Docker | Connu, ADR-018 |
| Deux implémentations de la logique de sécurité, une seule bouclée | Dérive possible entre `safety.st` et le modèle | ADR-014 |
| Le SCADA détient un identifiant qui peut démarrer le convoyeur (R-14) | Cible de S8 | Volontaire |
| Rien n'est commité | Tout le travail est local | `docs\runs\COMMITS.md` (à relire) |

## Commandes

Depuis le dossier `plant`, dans PowerShell. **Passe 1 : valider 4e sur le fichier compose de base.**

```powershell
cd "C:\Dev\Tech - Product\Vigilimen\plant"
powershell -ExecutionPolicy Bypass -File tools\validate-4e.ps1
```

Résultat du 25/10 : 7/7. Le script lance les FF locaux, construit, démarre, attend la santé, exécute FF-26 (STOP, clear, START, Spike +8, ligne `alarm_event` chronométrée < 2 s, Clear all faults → RTN_UNACK), puis affiche la liste FUXA à faire à la main. Transcription dans `docs\runs\`. **En cas d'échec : symptôme, cause, correction dans `docs\runs\NOTES.md` avant de corriger.**

**Passe 2 : liaison PLC et persistance, une fois la passe 1 réussie.**

```powershell
powershell -ExecutionPolicy Bypass -File tools\validate-plcio.ps1
```

Résultat du 25/10 : tout vert (la partie isolation après correction du script). Elle applique la migration, démarre avec `docker-compose.plcio.yml`, te laisse téléverser `plc-upload\conveyor_upload.st` (via `tools\plc-ui-relay.ps1 -Action start -Target control`, puis `http://127.0.0.1:8081`, `openplc` / `openplc`), lance FF-26 avec le PLC dans la boucle, redémarre le collecteur en pleine alarme, puis exécute `prove-isolation.ps1`. Pense à `tools\plc-ui-relay.ps1 -Action stop` ensuite.

Tests locaux : `python scripts\ff22_compose_topology.py` (idem 23, 24, 25, 21, 07, 06). Arrêt : `docker compose down` garde les données, `down -v` les supprime (avec l'override, passer les deux `-f`).

## Prompt de reprise

```text
Tu es mon architecte OT/IT. Projet : Vigilimen (sécurité OT/IT d'une mine, convoyeur CONV-001), 100 % local avec Docker.
Lis docs/VIGILIMEN-etat-des-lieux.md, docs/runs/NOTES.md et docs/adr/0013 à 0019.
Point de départ : 4e, la liaison PLC, la persistance et l'isolation sont validés dans Docker (25/10). Reste : déclenchements 95 °C et 42 A dans OpenPLC, commits, walkthrough rev 1.3. Si je te colle une sortie de validate-*.ps1, analyse-la : note symptôme, cause, correction dans NOTES.md AVANT de corriger. Chaque test = une fitness function FF-xx. Ports sur 127.0.0.1, aucun secret réel, ne commite rien sans mon accord.
```
