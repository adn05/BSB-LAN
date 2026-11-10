#!/usr/bin/env python3
"""Produit la liste Alféa (BSB_LAN_custom_defs.h) à partir de la liste 211/127 de référence.

Usage : gen_custom_defs.py <liste_source.h> <sortie.h> [--selection <fichier>] [--ecriture <fichier>] [--ha <fichier>]

Avec --selection, seules les entrées dont le numéro de ligne figure dans le fichier
(numéros ou plages « a-b », commentaires « # ») sont conservées dans la cmdtbl.
Les textes et énumérations non référencés sont éliminés à l'édition de liens.

Avec --ecriture (liste blanche, même format), toute entrée hors liste reçoit FL_RONLY
(FL_OEM conservé) et le tableau write_whitelist[][2] est émis pour la garde
WRITE_WHITELIST de set() (BSB_LAN.ino). Voir docs/claude/08_plan_migration.md §5.2.

Avec --ha (même format, en pratique alfea/params/selection_ha.txt), la fonction alfea_dans_ha(ligne) est émise :
elle dit si une ligne est annoncée à Home Assistant (filtre MQTT_DISCOVERY_SKIP de alfea/config/BSB_LAN_config.h).
La liste complète peut ainsi être compilée sans annoncer ses 900 paramètres à HA.

Les corrections sont décrites et justifiées dans docs/claude/08a_analyse_liste_parametres.md.
Chaque ajout porte le commentaire « ALFEA » ; aucune entrée source n'est supprimée.
"""
import argparse
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
# groupes : début jusqu'aux drapeaux inclus le séparateur, drapeaux, fin de l'entrée
ENTREE_DRAPEAUX = re.compile(r'^(\{0x[0-9A-Fa-f]{8},\s*VT_\w+,\s*[\d.]+,\s*\w+,\s*[^,]+,\s*\w+,\s*)([^,]+?)(,\s*\w+,\s*\w+\},?.*)$')


def lire_selection(chemin):
    plages = []
    for ligne in open(chemin, encoding='utf-8'):
        ligne = ligne.split('#')[0].strip()
        if not ligne:
            continue
        debut, _, fin = ligne.partition('-')
        plages.append((float(debut), float(fin or debut) + 0.95))
    return plages


def dans(plages, ligne):
    return any(a <= ligne <= b for a, b in plages)


def main():
    args = argparse.ArgumentParser()
    args.add_argument('source')
    args.add_argument('sortie')
    args.add_argument('--selection')
    args.add_argument('--ecriture')
    args.add_argument('--ha')
    args = args.parse_args()
    src, dst = args.source, args.sortie
    plages = lire_selection(args.selection) if args.selection else None
    blanche = lire_selection(args.ecriture) if args.ecriture else None
    ha = lire_selection(args.ha) if args.ha else None
    lignes = open(src, encoding='utf-8').read().splitlines()
    debut = next(i for i, l in enumerate(lignes) if 'const cmd_t cmdtbl[]' in l)
    entete = TEXTES.splitlines()
    if blanche is not None:
        entete += ["// ALFEA : liste blanche d'écriture (alfea/params/ecriture.txt), garde WRITE_WHITELIST de set()",
                   'const float write_whitelist[][2] = {'
                   + ', '.join(f'{{{a!r}, {b!r}}}' for a, b in blanche) + '};', '']
    if ha is not None:
        entete += ['// ALFEA : lignes annoncées à Home Assistant (alfea/params/selection_ha.txt), filtre MQTT_DISCOVERY_SKIP',
                   'static const float alfea_ha[][2] = {'
                   + ', '.join(f'{{{a!r}, {b!r}}}' for a, b in ha) + '};',
                   'static inline bool alfea_dans_ha(float l) {',
                   '  for (unsigned i = 0; i < sizeof(alfea_ha) / sizeof(alfea_ha[0]); i++) {',
                   '    if (l >= alfea_ha[i][0] && l <= alfea_ha[i][1]) return true;',
                   '  }',
                   '  return false;',
                   '}', '']
    sortie = lignes[:debut] + entete + [lignes[debut]]
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
    if blanche is not None:
        for k, l in enumerate(sortie):
            m = ENTREE_LIGNE.match(l)
            if m and not dans(blanche, float(m.group(1))):
                d = ENTREE_DRAPEAUX.match(l)
                if not d:
                    sys.exit(f'drapeaux illisibles : {l}')
                drapeaux = 'FL_RONLY' + ('+FL_OEM' if 'FL_OEM' in d.group(2) else '')
                sortie[k] = d.group(1) + drapeaux + d.group(3)
    with open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write(ENTETE + '\n'.join(sortie) + '\n')


if __name__ == '__main__':
    main()
