Projet Vigilimen (OT/IT sécurité mine, convoyeur CONV-001, local Docker, 6 conteneurs). Lis d'abord, dans le projet MINE 360 : claude/VIGILIMEN-etat-des-lieux.md puis claude/VIGILIMEN-walkthrough.md (rev 1.5). Dossier local : C:\Dev\Tech - Product\Vigilimen. Version PDF illustrée : docs\VIGILIMEN-etat-des-lieux.pdf (6 schémas dans docs\img\).

ÉTAT AU 26 OCT 2026, 2 h 30
- Fait et poussé (dernier commit e9d796c, CI #9 vert, FF-01..25 verts) : stations 1 à 4, 4e validée (embedded 7/7, FUXA à la main OK), liaison gateway-OpenPLC par Modbus, persistance des alarmes, isolation SIS prouvée, FF-27 13/13 en mode PLC, safety.st rejoué (63 scans, 0 écart modèle, 0 écart ADR-011), mode PLC par défaut dans docker-compose.yml (embedded = VIGILIMEN_PLC_LINK=off), docker-compose.plcio.yml supprimé du dépôt (FF-22 rouge en CI à cause de lui).
- Modifié localement, PAS commité : docs/adr/0006 et hydro-station/01-suc-description.md (seuil SOCI vérifié sur le texte primaire : Definitions Rules 2021 art. 5(1), 30 MW ou SRAS + marché de gros, version « as made », amendements non vérifiés) ; 05-detailed-risk-assessment.xlsx cellule Summary!A38 (« All six renotings ») ; docs/adr/NUMBERING.md (règle : les fichiers du dépôt font foi, prochain numéro libre ADR-020) ; ce prompt. Vérifie avec git status.
- Le stack peut être resté en embedded après validate-4e.ps1 : docker compose up -d --build pour revenir au mode PLC.

RESTE OUVERT
1. F1 : ouvrir 05-detailed-risk-assessment.xlsx dans Excel et enregistrer (le classeur n'a pas de valeurs en cache).
2. Non testés : DELETE et TRUNCATE sur alarm_event, redémarrage du collecteur pendant SHELVED (à écrire comme FF-xx avec Docker).
3. Anciens diagrammes docs/img (architecture, chemin-valeur, etats-alarme) à régénérer ou retirer.
4. pilotage\progress.md local périmé (le mettre à jour seulement si je le demande).
5. Quand le CI aura repassé : vérifier qu'aucune annotation n'est un vrai souci (1 warning, 1 notice vus, non lus).
6. Sprint S5 dès le 16 nov. : edge, DMZ OT, accès distant fournisseur courtié (ADR à écrire, numéros libres), porte M1.

CONTRAINTES PERMANENTES
- Ports sur 127.0.0.1 uniquement ; aucun secret réel ; chaque test = une fitness function FF-xx ; test local avant de me demander de reconstruire ; commandes PowerShell exactes.
- Ne commite et ne pousse rien sans mon accord (donne-moi les commandes git, je les lance ; AUCUN Co-Authored-By, aucune ligne Claude-Session et aucune mention de Claude dans les messages de commit ni dans les descriptions de PR).
- Avant de corriger un échec : écrire symptôme / cause / correction dans docs\runs\NOTES.md.
- Premier suspect quand un résultat surprend : l'instrument (banc, faux PLC, modèle), pas le programme. Dire d'où vient le résultat attendu.
- Ne jamais déclarer un CI ou un test vert sans avoir vu la sortie.
- Réponses courtes (mode caveman) ; français.
