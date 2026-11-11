#!/bin/sh
# Contrôle la carte d'interface et régénère ses sorties (hors Gerber, générés par l'utilisateur), dans un conteneur à version figée.
# Usage, depuis la racine du dépôt : sh docker/kicad/controler_carte.sh
# Documentation : docs/claude/09_design_carte_interface.md §9.
#
# Le schéma et le PCB sont édités dans KiCad (PCB routé à la main) : ce script ne les modifie JAMAIS.
# Il échoue au moindre écart ERC ou DRC (toutes sévérités, parité schéma/PCB comprise).
set -eu
KICAD=kicad/kicad:9.0.6
RACINE="$(cd "$(dirname "$0")/../.." && pwd)"
CARTE="$RACINE/alfea/hardware/carte_bsb_c3"
case "$(uname -s)" in MINGW*|MSYS*) W() { cygpath -w "$1"; }; export MSYS_NO_PATHCONV=1 ;; *) W() { echo "$1"; } ;; esac

docker run --rm -v "$(W "$CARTE"):/carte" -w /carte $KICAD sh -c '
  set -e
  S=carte_bsb_c3.kicad_sch; P=carte_bsb_c3.kicad_pcb
  mkdir -p sorties
  kicad-cli sch erc --severity-all --exit-code-violations -o sorties/erc.rpt $S
  kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations -o sorties/drc.rpt $P
  kicad-cli sch export pdf -o sorties/schema.pdf $S
  # BOM complète (avec les fiches JJ, hors carte), puis BOM d assemblage JLCPCB (composants montés seulement)
  kicad-cli sch export bom --fields "Reference,Value,Footprint,\${QUANTITY},JLCPCB Part #,Product link,MPN" \
    --labels "Designator,Comment,Footprint,Quantity,JLCPCB Part #,Product link,MPN" \
    --group-by "Value,Footprint,JLCPCB Part #" --ref-range-delimiter "" -o sorties/bom.csv $S
  grep -v "^\"JJ" sorties/bom.csv > sorties/bom_jlcpcb.csv
  # Positions (CPL) au format JLCPCB : face avant, en mm
  kicad-cli pcb export pos --format csv --units mm --side front -o sorties/positions.csv $P
  sed -i "1s/.*/Designator,Val,Package,Mid X,Mid Y,Rotation,Layer/" sorties/positions.csv
  kicad-cli pcb export svg --layers F.Cu,B.Cu,F.SilkS,Edge.Cuts,Dwgs.User --mode-single -o sorties/pcb.svg $P
  kicad-cli pcb export pdf --layers F.Fab,Edge.Cuts --mode-single -o sorties/assemblage.pdf $P
  kicad-cli pcb render --side top --width 1600 --height 1000 --quality basic -o sorties/pcb_dessus.png $P
  kicad-cli pcb render --side bottom --width 1600 --height 1000 --quality basic -o sorties/pcb_dessous.png $P
'
echo "Carte contrôlée, sorties régénérées dans alfea/hardware/carte_bsb_c3/sorties/."
