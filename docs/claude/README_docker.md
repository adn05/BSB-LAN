# Environnements Docker

> **Résumé**
> Tout se construit dans des conteneurs aux versions figées : le firmware avec **arduino-cli 1.3.1 + core esp32 3.3.12** (`docker/compiler.sh`), la carte avec **KiCad 9.0.6** (`docker/kicad/generer_carte.sh`).
> Aucun outil à installer sur le poste à part Docker. L'arbre `BSB_LAN/` n'est jamais modifié par un build : chaque compilation travaille sur une copie.
> Sorties dans `alfea/build/` (ignoré par git) et `alfea/hardware/carte_bsb_c3/sorties/` (versionné).

## 1. Firmware

| Fichier | Rôle |
|---|---|
| `docker/arduino-cli/Dockerfile` | image `bsblan-build:cli-1.3.1-esp32-3.3.12` : debian:trixie-slim, arduino-cli 1.3.1 (archive officielle vérifiée par sha256), core `esp32:esp32@3.3.12` |
| `docker/compiler.sh` | construit l'image si besoin, puis lance `docker/build.sh` dans un conteneur (utilisateur courant, dépôt monté en `/work`) |
| `docker/build.sh` | copie `BSB_LAN/` dans un répertoire temporaire, y place la configuration et la liste de la cible, compile, produit le rapport de taille, échoue au-delà de 85 % de la partition app |

**Commandes**, depuis la racine du dépôt (Linux, macOS, ou Git Bash sous Windows) :
```sh
sh docker/compiler.sh amont   # amont non modifié, configuration et liste par défaut (référence de taille)
sh docker/compiler.sh alfea   # firmware Alféa : alfea/config/BSB_LAN_config.h + alfea/params/BSB_LAN_custom_defs_ha.h
```

**Cible `alfea`** : il faut d'abord copier `alfea/config/alfea_secrets.h.example` en `alfea/config/alfea_secrets.h` (fichier ignoré par git) et le remplir. Sans ce fichier, le build utilise le modèle et prévient que l'image n'est pas flashable en l'état.

**Sorties** dans `alfea/build/<cible>/` :
- `BSB_LAN.ino.merged.bin` : image complète, à flasher en 0x0 au premier flash ;
- `BSB_LAN.ino.bin` : application seule, pour l'OTA ;
- `BSB_LAN.ino.map`, `taille.txt` (répartition par composant, script `alfea/tools/mapsize.py`), `rapport.txt` (flash, RAM statique), `compile.log`.

Paramètres de compilation : FQBN `esp32:esp32:esp32c3`, `PartitionScheme=min_spiffs` (2 × 1 920 Ko pour l'OTA), `CDCOnBoot=cdc` (console sur l'USB natif du C3).

Le premier build télécharge environ 600 Mo, dont la chaîne RISC-V ; le Dockerfile allonge le délai réseau et fait 3 tentatives. Les builds suivants réutilisent l'image.

## 2. Carte d'interface

`sh docker/kicad/generer_carte.sh` régénère le projet KiCad à partir de `alfea/hardware/gen/carte.py`, puis lance l'ERC, le DRC avec parité schéma/PCB et les exports (PDF, BOM, SVG, rendu). Détails : `09_design_carte_interface.md` §9.

## 3. Simulateur de régulateur BSB (test sans PAC)

`alfea/tools/bsb_sim.py` joue le rôle du RVS21 : identification 211/127, réponses aux lectures à partir de `alfea/tools/bsb_sim_scenario.json`, ACK des écritures (journalisées), écho du bus.

- **Autotest sans matériel** (codage des trames et des valeurs contre des trames réelles : dump `/QD`, PR #812, code amont) :
  `docker run --rm -v "$PWD:/work" -w /work bsblan-build:cli-1.3.1-esp32-3.3.12 python3 alfea/tools/bsb_sim.py --autotest`
- **Banc de test** (T1) : adaptateur USB-UART **3,3 V** relié directement au SuperMini, sans carte d'interface. TX de l'adaptateur sur GPIO6, RX sur GPIO7, masses communes. Puis :
  `python3 alfea/tools/bsb_sim.py --port /dev/ttyUSB0` (Linux ; `COM5` sous Windows, avec `pip install pyserial`).
  Sous Linux, depuis Docker : ajouter `--device /dev/ttyUSB0` et installer `pyserial` dans le conteneur.
- En lecture seule, aucune ligne « SET reçu » ne doit apparaître, quoi qu'on demande à l'interface web ou en MQTT.

## 4. Pile de test Home Assistant (E9)

`docker/ha-test/compose.yaml` : **Mosquitto 2.0.22** (accès anonyme, **test uniquement**) et **Home Assistant 2026.10.4**, la même version que votre installation.

```sh
docker compose -f docker/ha-test/compose.yaml -p hatest up -d     # puis http://localhost:8123
docker compose -f docker/ha-test/compose.yaml -p hatest down
```
- Dans HA : créer le compte, puis Paramètres > Appareils et services > Ajouter > **MQTT**, broker `mosquitto`, port 1883.
- Firmware de test : `mqtt_broker_addr` = adresse IP du PC qui fait tourner la pile, port 1883 (dans `alfea_secrets.h` ou la page `/C`).
- **Vérification automatique de la discovery** (`alfea/tools/verif_discovery.py`, sans dépendance) :
  ```sh
  docker run --rm --network hatest_default -v "$PWD:/work" -w /work python:3.12-slim     python3 -I alfea/tools/verif_discovery.py --broker mosquitto            # firmware en lecture seule
  # ajouter --ecriture alfea/params/ecriture.txt pour le firmware alfea-ecriture
  ```
  Il signale toute entité modifiable en lecture seule, toute entité modifiable hors liste blanche et tout champ manquant. Il a été testé sur des messages factices : un capteur conforme, un `select` sur 700, un `text` sur 8743. Les deux anomalies attendues sont détectées dans chaque mode.

Le flash se fait avec `esptool` depuis l'hôte, car l'accès USB depuis Docker n'est simple que sous Linux (`--device /dev/ttyACM0`). La procédure ira dans le guide (doc 11).
