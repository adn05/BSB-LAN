#!/bin/sh
# Génère le boîtier imprimable de la carte d'interface (STEP, STL, assemblage, aperçu) et contrôle les interférences.
# Usage, depuis la racine du dépôt : sh docker/cadquery/boitier.sh
# Documentation : docs/claude/13_boitier_3d.md.
set -eu
KICAD=kicad/kicad:9.0.6
CQ=alfea-cadquery:2.5.2
RACINE="$(cd "$(dirname "$0")/../.." && pwd)"
CARTE="$RACINE/alfea/hardware/carte_bsb_c3"
BOITIER="$RACINE/alfea/hardware/boitier"
TMP="$RACINE/alfea/build/boitier"                  # ignoré par git
case "$(uname -s)" in MINGW*|MSYS*) W() { cygpath -w "$1"; }; export MSYS_NO_PATHCONV=1 ;; *) W() { echo "$1"; } ;; esac
mkdir -p "$TMP"

# 1. Volume de la carte (contour, épaisseur, perçages) exporté par KiCad
docker run --rm -v "$(W "$CARTE"):/carte" -v "$(W "$TMP"):/o" -w /carte $KICAD \
  kicad-cli pcb export step --board-only --force -o /o/carte.step carte_bsb_c3.kicad_pcb > "$TMP/step.log" 2>&1

# 2. Boîtier (image construite une fois, versions figées dans le Dockerfile)
docker image inspect $CQ > /dev/null 2>&1 || docker build -t $CQ "$(W "$RACINE/docker/cadquery")"
docker run --rm -v "$(W "$BOITIER"):/b" -v "$(W "$TMP"):/o" -w /b $CQ python boitier.py /o/carte.step /b/sorties
