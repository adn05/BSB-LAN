#!/bin/sh
# Compile BSB-LAN pour ESP32-C3 dans l'image docker/arduino-cli (lancé par docker/compiler.sh).
# Usage : build.sh <cible>
#   amont : code, configuration et liste par défaut de l'amont (référence de taille)
#   alfea : configuration alfea/config + liste réduite alfea/params (firmware Alféa, lecture seule)
#   alfea-ecriture : idem, compilé avec ALFEA_ECRITURE (écriture de la liste blanche possible
#                    après choix du mode d'écriture dans /C ; docs/claude/08 §5.2)
#   pont : firmware de la NodeMCU ESP-C3-32S-Kit servant de pont USB (CH340) <-> bus logique pour le simulateur
#          (alfea/tools/pont_bsb, docs/claude/README_docker.md §3)
# L'arbre BSB_LAN/ n'est jamais modifié : on compile une copie dans un répertoire temporaire.
set -eu
CIBLE="${1:-alfea}"
DEPOT=/work
SORTIE="$DEPOT/alfea/build/$CIBLE"
FQBN="esp32:esp32:esp32c3:PartitionScheme=min_spiffs,CDCOnBoot=cdc"
SEUIL_POURCENT=85

if [ "$CIBLE" = pont ]; then
  rm -rf "$SORTIE"
  mkdir -p "$SORTIE"
  arduino-cli compile --fqbn "esp32:esp32:esp32c3:CDCOnBoot=default" --warnings default --output-dir "$SORTIE"     "$DEPOT/alfea/tools/pont_bsb" 2>&1 | tee "$SORTIE/compile.log"
  [ -f "$SORTIE/pont_bsb.ino.merged.bin" ] || { echo "ÉCHEC de compilation" >&2; exit 1; }
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp -r "$DEPOT/BSB_LAN" "$TMP/BSB_LAN"
rm -f "$TMP/BSB_LAN/BSB_LAN_config.h" "$TMP/BSB_LAN/BSB_LAN_custom_defs.h"
case "$CIBLE" in
  amont)
    cp "$TMP/BSB_LAN/BSB_LAN_config.h.default" "$TMP/BSB_LAN/BSB_LAN_config.h"
    cp "$TMP/BSB_LAN/BSB_LAN_custom_defs.h.default" "$TMP/BSB_LAN/BSB_LAN_custom_defs.h"
    ;;
  alfea|alfea-ecriture)
    cp "$DEPOT/alfea/config/BSB_LAN_config.h" "$TMP/BSB_LAN/BSB_LAN_config.h"
    cp "$DEPOT/alfea/params/BSB_LAN_custom_defs_ha.h" "$TMP/BSB_LAN/BSB_LAN_custom_defs.h"
    if [ -f "$DEPOT/alfea/config/alfea_secrets.h" ]; then
      cp "$DEPOT/alfea/config/alfea_secrets.h" "$TMP/BSB_LAN/alfea_secrets.h"
    else
      echo "ATTENTION : alfea/config/alfea_secrets.h absent, build avec les valeurs du modèle (non flashable en l'état)"
      cp "$DEPOT/alfea/config/alfea_secrets.h.example" "$TMP/BSB_LAN/alfea_secrets.h"
    fi
    ;;
  *) echo "cible inconnue : $CIBLE (amont | alfea | alfea-ecriture | pont)" >&2; exit 2 ;;
esac
OPTIONS=""
[ "$CIBLE" = alfea-ecriture ] && OPTIONS="-DALFEA_ECRITURE"

rm -rf "$SORTIE"
mkdir -p "$SORTIE"
arduino-cli compile --fqbn "$FQBN" --warnings none --build-property "compiler.cpp.extra_flags=$OPTIONS" --output-dir "$SORTIE" "$TMP/BSB_LAN" 2>&1 | tee "$SORTIE/compile.log"
[ -f "$SORTIE/BSB_LAN.ino.bin" ] || { echo "ÉCHEC de compilation" >&2; exit 1; }

python3 "$DEPOT/alfea/tools/mapsize.py" "$SORTIE/BSB_LAN.ino.map" > "$SORTIE/taille.txt"
FLASH=$(sed -n 's/^Sketch uses \([0-9]*\) bytes (\([0-9]*\)%).*/\1 \2/p' "$SORTIE/compile.log")
RAM=$(sed -n 's/^Global variables use \([0-9]*\) bytes.*/\1/p' "$SORTIE/compile.log")
set -- $FLASH
echo "RAPPORT $CIBLE : flash $1 o ($2 %), RAM statique $RAM o" | tee "$SORTIE/rapport.txt"
if [ "$2" -gt "$SEUIL_POURCENT" ]; then
  echo "ÉCHEC : image au-delà de $SEUIL_POURCENT % de la partition app (marge OTA insuffisante)" >&2
  exit 1
fi
