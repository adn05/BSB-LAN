#!/bin/sh
# Régénère et contrôle la carte d'interface dans des conteneurs aux versions figées.
# Usage, depuis la racine du dépôt : sh docker/kicad/generer_carte.sh
# Documentation : docs/claude/09_design_carte_interface.md §9.
#
# - Le schéma maître est alfea/hardware/carte_bsb_c3/carte_bsb_c3.kicad_sch, édité dans KiCad : il n'est jamais écrasé.
# - Carte CMS : placement (gen_kicad.py), routage Freerouting 2.1.0 (jar officiel, sha256 vérifié), plan de masse, contrôles.
set -eu
KICAD=kicad/kicad:9.0.6
JAVA=eclipse-temurin:21-jre
FR_VERSION=2.1.0
FR_SHA256=2c07d58f75dac03782664081e7a58b41c25400d871a9fcf166a2ea6fe60d5def
RACINE="$(cd "$(dirname "$0")/../.." && pwd)"
HW="$RACINE/alfea/hardware"
OUTILS="$RACINE/alfea/build/outils"            # ignoré par git
case "$(uname -s)" in MINGW*|MSYS*) W() { cygpath -w "$1"; }; export MSYS_NO_PATHCONV=1 ;; *) W() { echo "$1"; } ;; esac

# --- Freerouting : téléchargé une fois, empreinte contrôlée à chaque usage
mkdir -p "$OUTILS"
JAR="$OUTILS/freerouting-$FR_VERSION.jar"
if [ ! -f "$JAR" ]; then
  docker run --rm -v "$(W "$OUTILS"):/o" $KICAD sh -c \
    "python3 -c \"import urllib.request as u; u.urlretrieve('https://github.com/freerouting/freerouting/releases/download/v$FR_VERSION/freerouting-$FR_VERSION.jar', '/o/freerouting-$FR_VERSION.jar')\""
fi
docker run --rm -v "$(W "$OUTILS"):/o" $KICAD sh -c "echo '$FR_SHA256  /o/freerouting-$FR_VERSION.jar' | sha256sum -c -"

# --- Carte CMS : placement, export Specctra (le .kicad_pro de KiCad est préservé)
CMS=carte_bsb_c3
cp "$HW/$CMS/$CMS.kicad_pro" "$OUTILS/$CMS.kicad_pro.sauve"
docker run --rm -v "$(W "$HW"):/hw" -v "$(W "$OUTILS"):/o" -w /hw/gen $KICAD sh -c "
  set -e
  python3 gen_kicad.py /hw/$CMS
  python3 specctra.py export /hw/$CMS/$CMS.kicad_pcb /o/$CMS.dsn 2>&1 | grep -Ev 'assert|swig|Debug'
"
# --- routage : un seul fil d'exécution pour un résultat reproductible
docker run --rm -v "$(W "$OUTILS"):/o" -w /o $JAVA \
  java -jar freerouting-$FR_VERSION.jar -de $CMS.dsn -do $CMS.ses -mp 100 -mt 1 --gui.enabled=false > "$OUTILS/freerouting.log" 2>&1
docker run --rm -v "$(W "$HW"):/hw" -v "$(W "$OUTILS"):/o" -w /hw/gen $KICAD sh -c "
  set -e
  python3 specctra.py import /hw/$CMS/$CMS.kicad_pcb /o/$CMS.ses 2>&1 | grep -Ev 'assert|swig|Debug'
"
cp "$OUTILS/$CMS.kicad_pro.sauve" "$HW/$CMS/$CMS.kicad_pro"
docker run --rm -v "$(W "$HW"):/hw" -w /hw/$CMS $KICAD sh -c '
  set -e
  mkdir -p sorties
  kicad-cli sch erc --severity-all --exit-code-violations -o sorties/erc.rpt carte_bsb_c3.kicad_sch
  kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations -o sorties/drc.rpt carte_bsb_c3.kicad_pcb
  kicad-cli sch export pdf -o sorties/schema.pdf carte_bsb_c3.kicad_sch
  kicad-cli sch export bom --fields "Reference,Value,Footprint,MPN,\${QUANTITY}" --group-by Value,Footprint,MPN -o sorties/bom.csv carte_bsb_c3.kicad_sch
  kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,Edge.Cuts,Dwgs.User --mode-single -o sorties/pcb.svg carte_bsb_c3.kicad_pcb
  kicad-cli pcb export pdf --layers F.Fab,Edge.Cuts --mode-single -o sorties/assemblage.pdf carte_bsb_c3.kicad_pcb
  rm -rf sorties/gerbers
  kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts -o sorties/gerbers/ carte_bsb_c3.kicad_pcb
  kicad-cli pcb export drill -o sorties/gerbers/ carte_bsb_c3.kicad_pcb
  kicad-cli pcb render --side top --width 1600 --height 1000 --quality basic -o sorties/pcb_dessus.png carte_bsb_c3.kicad_pcb
  kicad-cli pcb render --side bottom --width 1600 --height 1000 --quality basic -o sorties/pcb_dessous.png carte_bsb_c3.kicad_pcb
'

echo "Carte régénérée et contrôlée (rapports dans alfea/hardware/carte_bsb_c3/sorties/)."
