# Environnements Docker

> **Résumé**
> Tout se construit dans des conteneurs aux versions figées : le firmware avec **arduino-cli 1.3.1 + core esp32 3.3.12** (`docker/compiler.sh`), les contrôles de la carte avec **KiCad 9.0.6** (`docker/kicad/controler_carte.sh`).
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
sh docker/compiler.sh pont    # pont de test sur NodeMCU ESP-C3-32S-Kit (§3)
```

**Cible `alfea`** : il faut d'abord copier `alfea/config/alfea_secrets.h.example` en `alfea/config/alfea_secrets.h` (fichier ignoré par git) et le remplir. Sans ce fichier, le build utilise le modèle et prévient que l'image n'est pas flashable en l'état.

**Sorties** dans `alfea/build/<cible>/` :
- `BSB_LAN.ino.merged.bin` : image complète, à flasher en 0x0 au premier flash ;
- `BSB_LAN.ino.bin` : application seule, pour l'OTA ;
- `BSB_LAN.ino.map`, `taille.txt` (répartition par composant, script `alfea/tools/mapsize.py`), `rapport.txt` (flash, RAM statique), `compile.log`.

Paramètres de compilation : FQBN `esp32:esp32:esp32c3`, `PartitionScheme=min_spiffs` (2 × 1 920 Ko pour l'OTA), `CDCOnBoot=cdc` (console sur l'USB natif du C3).

Le premier build télécharge environ 600 Mo, dont la chaîne RISC-V ; le Dockerfile allonge le délai réseau et fait 3 tentatives. Les builds suivants réutilisent l'image.

## 2. Carte d'interface

`sh docker/kicad/controler_carte.sh` (≈ 20 s, `kicad/kicad:9.0.6`) : ERC et DRC avec parité (toutes sévérités, échec au moindre écart), puis exports (PDF, BOM complète et BOM d'assemblage JLCPCB, positions CPL, SVG, rendus). Le script **ne modifie jamais** le schéma ni le PCB, routé à la main, et ne génère pas les Gerber. Détails : 09 §9.

## 3. Simulateur de régulateur BSB (test sans PAC)

`alfea/tools/bsb_sim.py` joue le rôle du RVS21 : identification 211/127, réponses aux lectures à partir de `alfea/tools/bsb_sim_scenario.json`, ACK des écritures (journalisées), écho du bus.

- **Autotest sans matériel** (codage des trames et des valeurs contre des trames réelles : dump `/QD`, PR #812, code amont) :
  `docker run --rm -v "$PWD:/work" -w /work bsblan-build:cli-1.3.1-esp32-3.3.12 python3 alfea/tools/bsb_sim.py --autotest`
- **Banc de test (T1) avec la NodeMCU ESP-C3-32S-Kit comme pont**, sans adaptateur USB-UART :
  1. **Pourquoi un firmware de pont** : BSB-LAN relit sa trame dès la fin de l'émission (`BSB_LAN/src/BSB/bsb.cpp:488-503`, `readByte()` non bloquant ligne 655). Sur le bus, cet écho est électrique. Un écho renvoyé par le PC arriverait plusieurs ms trop tard et chaque émission finirait en « Collision on the bus ». Le pont `alfea/tools/pont_bsb/pont_bsb.ino` recalcule donc, par interruption GPIO, **ligne = TX cible ET TX simulateur**, comme le ET câblé du bus. Il ne remonte au PC que les octets de la cible.
  2. **Compiler** : `sh docker/compiler.sh pont` → `alfea/build/pont/pont_bsb.ino.merged.bin`. La carte a un CH340 sur l'UART0 : la console est à 115 200 bauds et `CDCOnBoot` est désactivé. Son module ESP-C3-32S n'a que **2 Mo de flash** [MESURÉ : `esptool flash-id`] : compilation en `FlashSize=2M`, partitions `minimal`.
  3. **Environnement de flash** sur l'hôte, hors Docker : sous Windows, Docker Desktop n'accède aux ports USB qu'avec usbipd et WSL. Versions figées dans `alfea/tools/requirements-flash.txt` (esptool 5.6.0, pyserial 3.5) :
     ```sh
     python -m venv alfea/build/venv
     alfea/build/venv/Scripts/python -m pip install -r alfea/tools/requirements-flash.txt
     ```
     Puis, avec `alfea/build/venv/Scripts/python` (désigné `PY` ci-dessous) :
     - `PY alfea/tools/flasher.py ports` : liste les ports et reconnaît les cartes à leur identifiant USB (CH340 1A86:7523 = pont, 303A:1001 = SuperMini) ;
     - `PY alfea/tools/flasher.py pont` puis `PY alfea/tools/flasher.py alfea` : image complète en 0x0. **Elle efface la NVS**, donc la configuration saisie dans l'interface web ;
     - `PY alfea/tools/flasher.py alfea --appli` : mises à jour, application seule en 0x10000, configuration conservée ;
     - `PY alfea/tools/flasher.py console` : console du SuperMini (Ctrl+C pour quitter ; `--carte pont` pour le pont). Les lignes tapées sont transmises à la carte.
     - **Test des broches** (`alfea/tools/test_broches`, cibles `test-broches` et `test-broches-pont`) : rappels internes de chaque GPIO (libre, tenue à 0 ou à 1), courts-circuits entre broches, bascule d'une broche (« 7 ») avec relecture de GPIO6 par le pont, veille (« v ») qui signale tout changement de niveau. Une carte en veille et l'autre qui fait basculer une broche montrent où aboutit chaque fil. Les images effacent le firmware en place : reflasher `pont` et `alfea` ensuite. `--port COMx` force un port. Sur l'USB natif, si le port n'apparaît pas, maintenir BOOT en branchant l'USB.
  4. **Câbler** en 3,3 V, sans composant : **IO6 du pont ← GPIO7 du SuperMini** (TX bus), **IO7 du pont → GPIO6 du SuperMini** (RX bus), GND ↔ GND. **IO10 du pont reste en l'air** : c'est la sortie interne de l'UART, relue par le pont. Ne pas utiliser IO3/4/5 ni IO18/19 du pont, câblées aux LED de la carte [À VÉRIFIER sur la sérigraphie]. Chaque carte est alimentée par son propre câble USB.
  5. **Lancer le simulateur** sur l'hôte : `PY alfea/tools/bsb_sim.py --port COMx --pont`. La liaison PC-pont est à 115 200 bauds et l'écho est fait par le pont. Le terminal affiche `<-` pour chaque trame de BSB-LAN et `->` pour chaque réponse. La LED verte du pont clignote au trafic.
  6. Ouvrir l'interface web du SuperMini (adresse IP sur sa console USB) : identification 211/127, puis valeurs du scénario `alfea/tools/bsb_sim_scenario.json`.
- **Variante avec adaptateur USB-UART 3,3 V** : TX de l'adaptateur sur GPIO6, RX sur GPIO7, masses communes, puis `bsb_sim.py --port ...` sans `--pont` (le simulateur fait alors l'écho, avec le risque de collision expliqué en 1).
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

Le flash se fait depuis l'hôte, dans l'environnement Python `alfea/build/venv` (§3, étape 3) : l'accès USB depuis Docker n'est simple que sous Linux (`--device /dev/ttyACM0`). C'est le seul écart à la règle « tout par Docker ».
