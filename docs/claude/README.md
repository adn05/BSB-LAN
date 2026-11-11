# docs/claude — BSB-LAN sur ESP32-C3 pour Atlantic Alféa Extensa Duo A.I.

> Résumé : firmware BSB-LAN adapté à une pompe à chaleur **Atlantic Alféa Extensa** (régulateur Siemens **RVS21**,
> famille 211, variante 127, bus **BSB** sur X86), sur un **ESP32-C3 SuperMini** monté sur une carte d'interface
> isolée, intégré à **Home Assistant** par MQTT (auto-discovery).
> Convention : **[CONSTATÉ]** = vérifié, **[SUPPOSÉ]** = hypothèse, **[À VÉRIFIER]** = question ouverte.

| # | Document | Contenu |
|---|---|---|
| 00 | [00_MISSION.md](00_MISSION.md) | feuille de route d'origine et règles de travail |
| 09 | [09_design_carte_interface.md](09_design_carte_interface.md) | carte d'interface rev A : schéma, calculs, protections, alimentation, BOM, mise en service sur banc |
| 10 | [10_journal_implementation.md](10_journal_implementation.md) | journal des étapes, décisions et mesures |
| 11 | [11_mise_en_service_pac.md](11_mise_en_service_pac.md) | raccordement à la PAC, premier essai, essai d'endurance |
| 12 | [12_thermostat_home_assistant.md](12_thermostat_home_assistant.md) | thermostats HA (chambre CC1, salon CC2), dérogations, boost ECS |
| 13 | [13_boitier_3d.md](13_boitier_3d.md) | boîtier imprimable en 3D |
| — | [README_docker.md](README_docker.md) | compilation, flash, contrôle de la carte, boîtier |

## Contenu du dépôt

| Chemin | Rôle |
|---|---|
| `BSB_LAN/` | code amont, modifié par quelques gardes (`git diff 41558d24 -- BSB_LAN/` : 2 fichiers, +85 / −5) |
| `alfea/config/BSB_LAN_config.h` | configuration du firmware ; secrets dans `alfea_secrets.h` (ignoré par git, modèle `alfea_secrets.h.example`) |
| `alfea/params/` | liste complète 211/127 générée (`BSB_LAN_custom_defs.h`), sélection annoncée à HA (`selection_ha.txt`), liste blanche d'écriture (`ecriture.txt`), source de la liste (`source/`), dump et sauvegarde des réglages de la PAC |
| `alfea/tools/` | `flasher.py` (flash et console USB), `gen_custom_defs.py` (génération de la liste), `mapsize.py` (rapport de taille) |
| `alfea/homeassistant/` | paquet des thermostats (`alfea_thermostats.yaml`) et tableau de bord (`dashboard_pac.yaml`) |
| `alfea/hardware/carte_bsb_c3/` | carte d'interface rev A (KiCad 9), routée par l'utilisateur, sorties de fabrication |
| `alfea/hardware/boitier/` | boîtier CadQuery et ses sorties STEP / STL |
| `docker/` | environnements de build (arduino-cli, KiCad, CadQuery) |

## Firmware

- **Une seule cible** : `sh docker/compiler.sh` → `alfea/build/alfea/` (flash 74 % de la partition app).
- **Liste complète** du régulateur (908 lignes, consultables par l'interface web) ; **annonces HA limitées** à
  `selection_ha.txt` (88 lignes).
- **Écriture** limitée à la liste blanche `ecriture.txt` (programmes horaires, consignes, ECS, dérogations, boost),
  et seulement en mode d'écriture 1 choisi dans `/C`. `/NE` remet le mode 0 (lecture seule).
- Sécurité : pas de télégrammes bruts (`/Y`, `/YR`, `/JY`), pas de `/G`, mot de passe HTTP et du point d'accès
  obligatoires, filtre d'IP de confiance.
- Ne pas lancer `/QD` sur la PAC : il a provoqué l'erreur IHM 103.23.415.

## État (2026-11-11)

- PAC raccordée depuis le 2026-11-09, carte rev A (SuperMini enfiché retourné, erratum J4/J5 : journal J51).
- Thermostats, dérogations et boost ECS validés sur la PAC depuis HA (journal J77).
- Essai d'endurance de 48 h en cours (doc 11 §7).
- Questions ouvertes : couverture WiFi (−75 dBm, cible ≥ −70 dBm) ; plantage observé à la reconnexion WiFi
  (`NetworkEvents::postEvent`, non corrigé).
