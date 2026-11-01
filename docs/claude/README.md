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

## GATE 1 — synthèse (fin des phases 1, 1 bis et 2)

**Statut : en attente de validation.**

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
