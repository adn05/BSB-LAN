# docs/claude — Mission BSB-LAN ESP32-C3 / Atlantic Alféa Extensa Duo A.I.

> Résumé : index de la documentation produite pendant la mission `alfea-extensa`.
> Chaque document commence par un résumé court puis le détail.
> Convention : **[CONSTATÉ]** = vérifié dans le code/la doc, **[SUPPOSÉ]** = hypothèse, **[À VÉRIFIER]** = question ouverte.

| # | Document | Phase | État |
|---|---|---|---|
| 00 | [00_MISSION.md](00_MISSION.md) | 0 | copie de la feuille de route |
| 01 | [01_architecture_bsb-lan.md](01_architecture_bsb-lan.md) | 1 | structure, cycle de vie, cmdtbl, configuration |
| 02 | [02_protocole_bsb.md](02_protocole_bsb.md) | 1 | couche physique, trames, CRC, BSB/LPB/PPS, Alféa = BSB |
| 03 | [03_serveur_web_et_api.md](03_serveur_web_et_api.md) | 1 | routes HTTP, API JSON, sécurité, tri indispensable/supprimable |
| 04 | [04_integration_home_assistant.md](04_integration_home_assistant.md) | 1 | MQTT, auto-discovery HA, alternatives, recommandation |
| 05 | [05_fonctionnalites.md](05_fonctionnalites.md) | 1 | inventaire des fonctionnalités, coûts mesurés (.map), tri pour Alféa |
| 06 | [06_carte_interface_bsb.md](06_carte_interface_bsb.md) | 1 bis | adaptateur officiel : étages, calculs, vigilance |
| 07 | [07_faisabilite_esp32c3.md](07_faisabilite_esp32c3.md) | 2 | identification Alféa, ESP32 vs C3, cartes, budget mémoire, choix |
| 08 | [08_plan_migration.md](08_plan_migration.md) | 3 | réduction par gardes `NO_…`, étapes et commits, build, secrets, paramètres HA, tests, risques |
| 08a | [08a_analyse_liste_parametres.md](08a_analyse_liste_parametres.md) | 3 | analyse de la liste 211/127 contre un dump `/QD`, incohérences, nouvelle liste générée |
| 09 | [09_design_carte_interface.md](09_design_carte_interface.md) | 3 | carte porteuse SuperMini : schéma, calculs, protections, alimentation, BOM, mesure de X86 |
| 09b | [09b_plaquette_essai.md](09b_plaquette_essai.md) | 4 | variante traversante sur plaquette à bandes : coupes, fils, implantation, contrôles |
| 10 | [10_journal_implementation.md](10_journal_implementation.md) | 4 | journal des étapes E0-E10, décisions et écarts, rapport de taille, diff amont |
| 12 | [12_thermostat_home_assistant.md](12_thermostat_home_assistant.md) | 4 | thermostats HA des circuits CC1 et CC2 (paquet MQTT `climate`), installation, limites, essais |
| — | [README_docker.md](README_docker.md) | 4 | build firmware, carte KiCad, simulateur BSB, pile HA de test |

## GATE 1 — synthèse (fin des phases 1, 1 bis et 2)

**Statut : validée le 2026-11-01** (décisions et réponses ci-dessous).

- **Faisabilité : oui, mesurée.** L'amont non modifié compile pour ESP32-C3 (arduino-esp32 3.3.12) : 1 610 749 o de flash (81 % de la partition app) et 65 624 o de RAM statique. Réduction estimée : ≈ 280-300 Ko de flash et ≈ 18 Ko de RAM (05 §3).
- **Cible** : Atlantic Alféa Extensa Duo A.I. = Siemens **RVS21**, bus **BSB** sur **X86**. Famille et variante probables **211/127** (RVS21.831F/127), à confirmer sur la machine (07 §6.1).
- **Carte proposée** : **ESP32-C3 SuperMini**, sous condition RF (RSSI ≥ −70 dBm sur site). Repli : kit Ai-Thinker en version 4 Mo (07 §6.5).
- **Sécurité** : la lecture seule amont est logicielle et contournable par `/Y`, `/YR` et **`/JY`** (01 §5, 03). La cible devra compiler en `FL_RONLY` et exclure ces routes.
- **Interface** : schéma V3 analysé. Compatible 3,3 V si l'adaptateur est alimenté en 3,3 V. Marge de CTR d'environ ×1,2 à ×2,3 (06 §3).

### Décisions demandées
1. Valider le choix de carte (SuperMini sous condition RF) et le brochage provisoire RX = GPIO6, TX = GPIO7, LED = GPIO8.
2. Outillage Docker : `arduino-cli` comme build de référence + environnement PlatformIO, ou PlatformIO seul ?
3. Liste de paramètres : solliciter le mainteneur (dump `/QD` de votre machine) ou partir d'une liste 211/127 existante ?
4. Stratégie de réduction : gardes `#if` ajoutées au code amont (diff minimal), comme le recommande la mission ?

### Questions ouvertes
- Q1. Régulateur exact de votre machine : suffixe RVS21.8xx, valeurs 6225/6226, version OV (lecture sur site).
- Q2. Brochage physique et polarité de X86 sur votre carte (photo de la carte de régulation ?), tension de repos du bus (multimètre).
- Q3. Présence d'accessoires sur le bus : Navilink A59/A75/A78, Cozytouch, Typass ? (risque d'écrasement de consignes, adresse de BSB-LAN).
- Q4. Schéma de l'adaptateur ESP32 v4.x : introuvable dans le dépôt. En avez-vous un exemplaire, ou faut-il concevoir notre propre carte (Phase 3) ?
- Q5. Budget de courant du BSB sur RVS21 et impédance de la source : non documentés. Le design prévoit une alimentation 5 V externe.
- Q6. Lot de SuperMini disponible : LDO ME6211 ou LP5907 ? Version de l'antenne ?
- Q7. Distance et obstacles entre la PAC (module hydraulique) et le point d'accès WiFi.
- Q8. Broker MQTT existant (Mosquitto, add-on HA) et version de Home Assistant.

### Décisions de l'utilisateur (GATE 1)
| # | Décision |
|---|---|
| D1 | Carte : **ESP32-C3 SuperMini** retenue (condition RF maintenue avant la GATE 3). |
| D2 | Outillage : **arduino-cli** comme build de référence, en Docker (PlatformIO non retenu pour l'instant). |
| D3 | Liste de paramètres : **analyser la liste 211/127 existante, relever les incohérences, puis générer une nouvelle liste** → doc 08a. |
| D4 | Réduction par **gardes `#if`** dans le code amont (diff minimal). |
| D5 | **Ajouter le support DHT22** (déjà présent en amont) et prévoir son entrée sur la carte. |
| D6 | Carte d'interface **à concevoir** (KiCad), optocoupleurs conservés, **alimentation non prélevée sur le bus**. |
| D7 | `MISSION_ALFEA_EXTENSA.md` supprimé de la racine (copie conservée dans `00_MISSION.md`). |

### Réponses aux questions ouvertes
| # | Réponse | Conséquence |
|---|---|---|
| Q1 | IHM, menu « version logicielle » : **Régulation : RVS21 - 89.006.090** | version applicative Atlantic, différente de la notice R32 (85.002.030). La correspondance avec la version OV (402.6 dans la liste de référence) et avec famille/variante est inconnue : **lecture de 6220-6229 obligatoire à la mise en service** (08a §6) |
| Q2 | X86 : bornier à vis débrochable `B2 M B1 3 2 1` (photo `images/x86_alfea.jpeg`) ; **0 V mesuré entre 1, 2 et 3** | à confirmer par une mesure témoin (09 §8) : 0 V même sur G+ suggère une mesure faussée ou une régulation non alimentée. **Question ouverte** tant que la mesure n'est pas refaite |
| Q3 | **2 Navilink A59 sans fil**, pas sur X86 | pas d'autre maître sur X86 ; les sondes passent par une liaison radio dont le récepteur n'est pas sur X86 [À VÉRIFIER]. Deux sondes suggèrent deux circuits (CC1 et CC2) : la liste HA inclut CC2 |
| Q4 | Concevoir notre carte avec KiCad | design dans 09, fichiers KiCad dans `hardware/alfea-esp32c3/` **après la GATE 2** (règle de la mission) |
| Q5 | Optocoupleurs conservés ; alimentation hors bus ; « alim 5 V de la PAC, sinon chargeur de téléphone » | pas de 5 V documenté sur le RVS21 ; G+ casserait l'isolation. Retenu : **chargeur USB 5 V** par défaut, module rail DIN en option (09 §4) |
| Q6 | À vérifier (LDO du SuperMini, distance WiFi) | reste ouvert |
| Q7 | Question non comprise | reformulée dans la synthèse GATE 2 |

## GATE 2 — synthèse (fin de la phase 3)

**Statut : design de la carte, paramètres et alimentation validés ; plan amendé, en attente du feu vert pour la Phase 4.**

Réponses de l'utilisateur (après la synthèse ci-dessous) :
- liste de paramètres : **réduite aux paramètres utiles** → 96 entrées, 1 638 533 o (83 %), soit −58 752 o (08a §5.4) ;
- paramètres HA validés ; **2 circuits** (CC1 : salon et cuisine ; CC2 : chambres) ;
- **écriture** souhaitée pour les **programmes horaires, modes et consignes** (CC1, CC2, ECS) : liste blanche, désactivée par défaut, avertissement et procédure dans 08 §5.2 ;
- fichiers de la carte dans **`alfea/hardware/`** : projet KiCad 9 généré, ERC/DRC/parité à 0, **non routé** (09 §9) ;
- alimentation : **chargeur USB**, rail DIN en option ;
- Q7 : **HA OS**, Core 2026.10.4, pas de broker → add-on Mosquitto (08 §5.3) ; Q6 : à observer pendant les essais.

- **Liste de paramètres (08a)** : la liste 211/127 de l'issue #622 (903 entrées) est fidèle à un dump `/QD` d'une autre machine 211/127 : 847/882 objets retrouvés, aucun numéro divergent, tailles cohérentes. Les 3 « absents » correspondent aux 3 enregistrements perdus du dump. Incohérences : 73 compteurs typés chaîne dont **3113** (I1), objets cachés manquants (#829, #831), 5057 oublié, niveau d'accès 6 inscriptible (**ramonage 7131**), `VT_VACATIONPROG` (#812). Nouvelle liste générée par script, 912 entrées : **1 697 285 o (86 %)** mesuré.
- **Plan (08)** : gardes `NO_…` + `FORCE_READ_ONLY`, 10 étapes/commits, arduino-cli en Docker, secrets hors dépôt, **38 paramètres HA** (dont DHT22), tests build → simulateur → HA Docker → PAC.
- **Carte (09)** : porteuse 50 × 40 mm pour SuperMini, topologie V3 conservée, écarts justifiés (R8 rappel TX, BC547C, TVS + PTC, DHT22 sur GPIO5, entrée 5 V + Schottky), alimentation par chargeur USB 5 V.

### Décisions demandées
1. Valider la stratégie de gardes et l'ordre des étapes E0-E10 (08 §2).
2. Valider ou amender la liste des 38 paramètres HA (08 §5) ; confirmer l'existence d'un 2e circuit (CC2).
3. Valider le design (09), en particulier les écarts à V3, et autoriser les fichiers KiCad dans `hardware/alfea-esp32c3/`.
4. Alimentation : chargeur USB (défaut) ou module rail DIN ?

### Questions ouvertes
- Q6 : marquage du LDO du SuperMini (ME6211 / LP5907), distance PAC ↔ point d'accès WiFi.
- Q7 reformulée : Home Assistant est-il déjà installé, comment (HA OS ou Docker) et en quelle version ? Avez-vous un broker MQTT (en général l'add-on Mosquitto de HA) ?
- Q9 : photo de la sérigraphie de X86, pas du connecteur, mesures de tension (09 §8), à faire avant la GATE 3.
- Q10 : à la mise en service, valeurs de 6224-6227 (famille/variante, 08a §6).

## Phase 4 — synthèse (avant la GATE 3)

**Statut : implémentation terminée et validée sans matériel. GATE 3 à venir** : rien n'a été branché sur la PAC.

- **Firmware Alféa** (`sh docker/compiler.sh alfea`) : **1 410 705 o (71 %)**, **49 104 o de RAM** (amont : 1 610 749 o, 65 624 o). Lecture seule par défaut ; variante `alfea-ecriture` limitée à la liste blanche (programmes horaires, modes, consignes).
- **Diff sur le code amont** : 27 lignes ajoutées, 4 supprimées, dans `BSB_LAN/BSB_LAN.ino` seulement. Le reste est dans `alfea/`, `docker/` et `docs/claude/`.
- **E6 et E7 écartées après mesure** : environ 4 points de partition, pour des gardes sur une centaine de sites (10 J14).
- **Validé sans matériel** : builds amont et Alféa, simulateur (autotest 13/13 sur trames réelles), pile Mosquitto + HA 2026.10.4, vérificateur de discovery.
- **Carte** : schéma maître retouché par l'utilisateur (émission V3), révision B 62 × 33 mm **routée par Freerouting** (DRC 0 toutes sévérités, Gerber) ; **variante traversante** sur plaquette à bandes (09b, DRC 0).
- **Pont de test** : firmware `pont_bsb` pour la NodeMCU ESP-C3-32S-Kit (ET câblé du bus, 10 J18-J19).

### Avant la GATE 3 (de votre côté)
1. Banc T1/T2 : SuperMini + NodeMCU ESP-C3-32S-Kit en pont (README_docker §3), puis la plaquette (09b) ou la carte CMS fabriquée.
2. **Refaire la mesure de X86** avec la mesure témoin (09 §8) : la première a donné 0 V partout. Photo reçue.
3. ~~Fichier `alfea/config/alfea_secrets.h`~~ : créé (firmware compilé avec, 71 %). L'utilisateur MQTT est resté `bsblan` : à créer tel quel dans l'add-on Mosquitto.
