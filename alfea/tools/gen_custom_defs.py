#!/usr/bin/env python3
"""Produit la liste Alféa (BSB_LAN_custom_defs.h) à partir de la liste 211/127 de référence.

Usage : gen_custom_defs.py <liste_source.h> <sortie.h> [--selection <fichier>]

Avec --selection, seules les entrées dont le numéro de ligne figure dans le fichier
(numéros ou plages « a-b », commentaires « # ») sont conservées dans la cmdtbl.
Les textes et énumérations non référencés sont éliminés à l'édition de liens.

Les corrections sont décrites et justifiées dans docs/claude/08a_analyse_liste_parametres.md.
Chaque ajout porte le commentaire « ALFEA » ; aucune entrée source n'est supprimée.
"""
import re
import sys

ENTETE = """\
// ALFEA : liste générée par alfea/tools/gen_custom_defs.py, ne pas modifier à la main.
// ALFEA : source = liste 211/127 générée par le mainteneur (RVS21.831F/127, OV 402.6),
// ALFEA : publiée dans https://github.com/fredlcore/BSB-LAN/issues/622 ; analyse : docs/claude/08a.
"""

# Textes des entrées ajoutées (déclarés avant la cmdtbl).
TEXTES = """\
// ALFEA : textes des entrées ajoutées
const char S701P3_0[] PROGMEM = "Dérogation temporaire : écart de consigne";
const char S701P4_0[] PROGMEM = "Dérogation temporaire : durée";
#define S1001P3_0 S701P3_0
#define S1001P4_0 S701P4_0
const char S3113P1_0[] PROGMEM = "Energie utilisée chauffage (compteur IHM)";
const char S3113P2_0[] PROGMEM = "Energie utilisée ECS (compteur IHM)";
const char S3113P3_0[] PROGMEM = "Energie utilisée rafraîchissement (compteur IHM)";
const char S3113P4_0[] PROGMEM = "Energie utilisée totale (compteur IHM)";
const char S5057_0[] PROGMEM = "Paramètre ECS 5057 (non documenté, valeur brute)";

"""

# (ligne après laquelle insérer, entrées à insérer)
AJOUTS = [
    (701.2, [  # issue #829, testé par son auteur sur RVS21.831F/127
        '{0x053D1AA6,  VT_TEMP,            701.3, S701P3_0, 0,                  NULL,         DEFAULT_FLAG, 211, 127}, // ALFEA #829 : écart de consigne de la dérogation CC1',
        '{0x053D1AA5,  VT_HOURS_SHORT,     701.4, S701P4_0, 0,                  NULL,         DEFAULT_FLAG, 211, 127}, // ALFEA #829 : durée de la dérogation CC1',
    ]),
    (1001.2, [
        '{0x063D1AA6,  VT_TEMP,            1001.3,S1001P3_0,0,                  NULL,         DEFAULT_FLAG, 211, 127}, // ALFEA #829 : écart de consigne de la dérogation CC2',
        '{0x063D1AA5,  VT_HOURS_SHORT,     1001.4,S1001P4_0,0,                  NULL,         DEFAULT_FLAG, 211, 127}, // ALFEA #829 : durée de la dérogation CC2',
    ]),
    (3113, [  # issue #831 : octet d'activation + uint32 en kWh, lus par l'IHM toutes les heures
        '{0x053D1094,  VT_ENERGY,          3113.1,S3113P1_0,0,                  NULL,         FL_RONLY,     211, 127}, // ALFEA #831',
        '{0x053D1095,  VT_ENERGY,          3113.2,S3113P2_0,0,                  NULL,         FL_RONLY,     211, 127}, // ALFEA #831',
        '{0x053D1B7E,  VT_ENERGY,          3113.3,S3113P3_0,0,                  NULL,         FL_RONLY,     211, 127}, // ALFEA #831',
        '{0x053D1082,  VT_ENERGY,          3113.4,S3113P4_0,0,                  NULL,         FL_RONLY,     211, 127}, // ALFEA #831',
    ]),
    (5055, [  # présent dans le dump (id2=0x08 : 1 octet, accès 0x33) mais absent de la liste
        '{0x313D0714,  VT_BYTE,            5057,  S5057_0,  0,                  NULL,         FL_RONLY,     211, 127}, // ALFEA : objet du dump absent de la liste',
    ]),
]

ENTREE_LIGNE = re.compile(r'^\{0x[0-9A-Fa-f]{8},\s*VT_\w+,\s*([\d.]+),')


def lire_selection(chemin):
    plages = []
    for ligne in open(chemin, encoding='utf-8'):
        ligne = ligne.split('#')[0].strip()
        if not ligne:
            continue
        debut, _, fin = ligne.partition('-')
        plages.append((float(debut), float(fin or debut) + 0.95))
    return plages


def main():
    src, dst = sys.argv[1:3]
    plages = lire_selection(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == '--selection' else None
    lignes = open(src, encoding='utf-8').read().splitlines()
    debut = next(i for i, l in enumerate(lignes) if 'const cmd_t cmdtbl[]' in l)
    sortie = lignes[:debut] + TEXTES.splitlines() + [lignes[debut]]
    restants = dict(AJOUTS)
    i = debut + 1
    while i < len(lignes):
        sortie.append(lignes[i])
        m = ENTREE_LIGNE.match(lignes[i])
        if m and float(m.group(1)) in restants:
            ancre = float(m.group(1))
            # insérer après la dernière entrée portant ce numéro de ligne
            suivante = ENTREE_LIGNE.match(lignes[i + 1]) if i + 1 < len(lignes) else None
            if not (suivante and float(suivante.group(1)) == ancre):
                sortie.extend(restants.pop(ancre))
        i += 1
    if restants:
        sys.exit(f'ancres introuvables : {sorted(restants)}')
    if plages is not None:
        retenues = []
        for l in sortie:
            m = ENTREE_LIGNE.match(l)
            if m and not any(a <= float(m.group(1)) <= b for a, b in plages):
                continue
            retenues.append(l)
        sortie = retenues
    with open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write(ENTETE + '\n'.join(sortie) + '\n')


if __name__ == '__main__':
    main()
