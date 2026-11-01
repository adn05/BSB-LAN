#!/bin/sh
# Régénère et contrôle la carte d'interface (schéma, PCB, ERC, DRC, sorties) dans l'image KiCad officielle.
# Usage, depuis la racine du dépôt : sh docker/kicad/generer_carte.sh
# Documentation : docs/claude/09_design_carte_interface.md §9.
set -eu
IMAGE=kicad/kicad:9.0.6
HW="$(cd "$(dirname "$0")/../../alfea/hardware" && pwd)"
case "$(uname -s)" in MINGW*|MSYS*) HW="$(cygpath -w "$HW")"; export MSYS_NO_PATHCONV=1 ;; esac
docker run --rm -v "$HW:/hw" -w /hw/gen "$IMAGE" sh -c '
  set -e
  python3 gen_kicad.py /hw/carte_bsb_c3
  cd /hw/carte_bsb_c3
  mkdir -p sorties
  kicad-cli sch erc --severity-all --exit-code-violations -o sorties/erc.rpt carte_bsb_c3.kicad_sch
  kicad-cli pcb drc --schematic-parity --severity-error -o sorties/drc.rpt carte_bsb_c3.kicad_pcb
  kicad-cli sch export pdf -o sorties/schema.pdf carte_bsb_c3.kicad_sch
  kicad-cli sch export bom --fields "Reference,Value,Footprint,MPN,\${QUANTITY}" --group-by Value,Footprint,MPN -o sorties/bom.csv carte_bsb_c3.kicad_sch
  kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,Edge.Cuts,Dwgs.User --mode-single -o sorties/pcb.svg carte_bsb_c3.kicad_pcb
  kicad-cli pcb render --side top --width 1600 --height 1150 --quality basic -o sorties/pcb_dessus.png carte_bsb_c3.kicad_pcb
'
