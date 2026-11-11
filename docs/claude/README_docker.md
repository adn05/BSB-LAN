# Environnements Docker

> **Résumé**
> Tout se construit dans des conteneurs aux versions figées : le firmware avec **arduino-cli 1.3.1 + core esp32 3.3.12** (`docker/compiler.sh`), les contrôles de la carte avec **KiCad 9.0.6** (`docker/kicad/controler_carte.sh`), le boîtier avec **CadQuery** (`docker/cadquery/boitier.sh`).
> Aucun outil à installer sur le poste à part Docker, sauf Python pour le flash (§2). L'arbre `BSB_LAN/` n'est jamais modifié par un build : chaque compilation travaille sur une copie.
> Sorties dans `alfea/build/` (ignoré par git) et dans les dossiers `sorties/` de `alfea/hardware/` (versionnés).

## 1. Firmware

| Fichier | Rôle |
|---|---|
| `docker/arduino-cli/Dockerfile` | image `bsblan-build:cli-1.3.1-esp32-3.3.12` : debian:trixie-slim, arduino-cli 1.3.1 (archive officielle vérifiée par sha256), core `esp32:esp32@3.3.12` |
| `docker/compiler.sh` | construit l'image si besoin, puis lance `docker/build.sh` dans un conteneur (utilisateur courant, dépôt monté en `/work`) |
| `docker/build.sh` | copie `BSB_LAN/` dans un répertoire temporaire, y place la configuration, la liste et les secrets, compile, produit le rapport de taille, échoue au-delà de 85 % de la partition app |

**Commande**, depuis la racine du dépôt (Linux, macOS, ou Git Bash sous Windows) :
```sh
sh docker/compiler.sh
```

Il faut d'abord copier `alfea/config/alfea_secrets.h.example` en `alfea/config/alfea_secrets.h` (fichier ignoré par git) et le remplir. Sans ce fichier, le build utilise le modèle et prévient que l'image n'est pas flashable en l'état.

**Sorties** dans `alfea/build/alfea/` :
- `BSB_LAN.ino.merged.bin` : image complète, à flasher en 0x0 au premier flash ;
- `BSB_LAN.ino.bin` : application seule, pour les mises à jour ;
- `BSB_LAN.ino.map`, `taille.txt` (répartition par composant, `alfea/tools/mapsize.py`), `rapport.txt` (flash, RAM statique), `compile.log`.

Paramètres de compilation : FQBN `esp32:esp32:esp32c3`, `PartitionScheme=min_spiffs` (2 × 1 920 Ko pour l'OTA), `CDCOnBoot=cdc` (console sur l'USB natif du C3).

Le premier build télécharge environ 600 Mo, dont la chaîne RISC-V. Les builds suivants réutilisent l'image.

**Liste de paramètres** : `alfea/params/BSB_LAN_custom_defs.h` est générée, ne pas la modifier à la main.
```sh
python alfea/tools/gen_custom_defs.py alfea/params/source/BSB_LAN_custom_defs_211-127_issue622.h \
  alfea/params/BSB_LAN_custom_defs.h --ecriture alfea/params/ecriture.txt --ha alfea/params/selection_ha.txt
```

## 2. Flash et console (hors Docker)

Sous Windows, Docker Desktop n'accède aux ports USB qu'avec usbipd et WSL : le flash se fait depuis l'hôte, dans un environnement Python aux versions figées (`alfea/tools/requirements-flash.txt` : esptool 5.6.0, pyserial 3.5). C'est le seul écart à la règle « tout par Docker ».
```sh
python -m venv alfea/build/venv
alfea/build/venv/Scripts/python -m pip install -r alfea/tools/requirements-flash.txt
```
Puis, avec `alfea/build/venv/Scripts/python` (désigné `PY`) :
- `PY alfea/tools/flasher.py ports` : liste les ports et reconnaît le SuperMini (303A:1001) ;
- `PY alfea/tools/flasher.py alfea` : image complète en 0x0. **Elle efface la NVS**, donc la configuration saisie dans l'interface web ;
- `PY alfea/tools/flasher.py alfea --appli` : mises à jour, application seule en 0x10000, configuration conservée ;
- `PY alfea/tools/flasher.py console` : console USB (Ctrl+C pour quitter). Les lignes tapées sont transmises à la carte. Arrêter la console avant de flasher.

`--port COMx` force un port. Si le port n'apparaît pas, maintenir BOOT en branchant l'USB.

Après un changement de la liste interrogée (`log_parameters` de `BSB_LAN_config.h`), la configuration gardée en NVS masque la nouvelle : `/NE` (efface la configuration et redémarre), puis remettre le mode d'écriture à 1 dans `/C`.

## 3. Carte d'interface

`sh docker/kicad/controler_carte.sh` (≈ 20 s, `kicad/kicad:9.0.6`) : ERC et DRC avec parité (toutes sévérités, échec au moindre écart), puis exports (PDF, BOM complète et BOM d'assemblage JLCPCB, positions CPL, SVG, rendus). Le script **ne modifie jamais** le schéma ni le PCB, routé à la main, et ne génère pas les Gerber. Détails : 09 §9.

## 4. Boîtier

`sh docker/cadquery/boitier.sh` : génère le boîtier (STEP, STL, assemblage, aperçu) depuis `alfea/hardware/boitier/boitier.py` et contrôle les interférences. Détails : doc 13.
