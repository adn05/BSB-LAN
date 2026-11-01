#!/usr/bin/env python3
"""Confronte une liste de paramètres BSB-LAN (cmdtbl d'un BSB_LAN_custom_defs.h)
au dump /QD du régulateur (télégrammes IA1, type 0x13).

Usage : analyse_liste.py <custom_defs.h> <dump.txt> <BSB_LAN_defs.h> [famille variante]

Décodage IA1 repris de BSB_LAN/BSB_LAN.ino:5481-5488 :
  msg[7]       = id2 : classe de donnée (taille sur le bus, cf. TAILLE_ID2)
  msg[8..10]   = CmdID sans son 2e octet (toujours 0x3D)
  msg[11..12]  = numéro de ligne (ligne de commande Siemens)
  msg[13]      = id4 : niveau d'accès, quartet haut = écriture (0 = lecture seule),
                 quartet bas = lecture [SUPPOSÉ, déduit de la corrélation avec FL_RONLY/FL_OEM]
  msg[17]      = id3 : code d'unité
"""
import collections
import re
import sys

# Taille de la donnée (hors octet d'activation) selon id2 [SUPPOSÉ : déduit des types connus,
# 643 entrées sur 677 concordent avec optbl, les 34 autres sont des ENUM 2 octets gérés par
# print_telegram.h:1166-1175].
TAILLE_ID2 = {0x01: 1, 0x02: 1, 0x05: 1, 0x08: 1, 0x03: 2, 0x06: 2, 0x09: 2, 0x04: 4, 0x07: 4}

ENTREE = re.compile(r'^\{(0x[0-9A-Fa-f]{8}),\s*(VT_\w+),\s*([\d.]+),\s*(\w+),\s*([^,]+),\s*(\w+),'
                    r'\s*([^,]+?),\s*(\w+),\s*(\w+)\},?\s*(?://\s*(.*))?$')


def lire_liste(chemin):
    txt = open(chemin, encoding='utf-8').read()
    textes = dict(re.findall(r'#define (\w+)_TEXT "(.*)"', txt))
    entrees = []
    for num, ligne in enumerate(txt.splitlines(), 1):
        m = ENTREE.match(ligne.strip())
        if m:
            cmd, vt, ln, desc, _, enum, flags, fam, var, com = m.groups()
            entrees.append(dict(src=num, cmd=int(cmd, 16), vt=vt, line=float(ln), desc=desc, enum=enum,
                                flags=flags.replace(' ', ''), fam=fam, var=var,
                                texte=textes.get(desc, com or '')))
    return entrees


def lire_dump(chemin, adresse=0):
    """Enregistrements IA1 de l'appareil `adresse` (section « Teste Geräteadresse <n>... »)."""
    txt = open(chemin, encoding='utf-8').read()
    sections = re.split(r'Teste Ger.teadresse (\d+)\.\.\.', txt)
    corps = dict(zip(sections[1::2], sections[2::2])).get(str(adresse), '')
    enr, ia2 = [], 0
    for ligne in corps.splitlines():
        b = ligne.split()
        if len(b) < 9 or b[0] != 'DC':
            continue
        v = [int(x, 16) for x in b]
        if v[4] == 0x15:
            ia2 += 1
        if v[4] != 0x13 or len(v) < 19 or (v[5] == 0 and v[6] == 0):
            continue
        enr.append(dict(idx=(v[5] << 8) | v[6], id2=v[7], cmd=(v[8] << 24) | 0x3D0000 | (v[9] << 8) | v[10],
                        line=(v[11] << 8) | v[12], id4=v[13], id3=v[17]))
    return enr, ia2


def lire_optbl(chemin):
    txt = open(chemin, encoding='utf-8').read()
    debut = txt.index('const units optbl[]={')
    opt = {}
    for m in re.finditer(r'\{(VT_\w+),\s*([\d.]+),\s*(\d+),\s*([\d+]+),\s*(DT_\w+)', txt[debut:debut + 40000]):
        vt, op, en, pl, dt = m.groups()
        opt[vt] = dict(op=float(op), en=int(en), pl=sum(int(x) for x in pl.split('+')), dt=dt)
    return opt


def main():
    defs, dump_txt, bsb_defs = sys.argv[1:4]
    fam, var = (sys.argv[4], sys.argv[5]) if len(sys.argv) > 5 else ('211', '127')
    entrees = lire_liste(defs)
    dump, n_ia2 = lire_dump(dump_txt)
    optbl = lire_optbl(bsb_defs)
    par_cmd = collections.defaultdict(list)
    for d in dump:
        par_cmd[d['cmd']].append(d)
    spec = [e for e in entrees if (e['fam'], e['var']) == (fam, var)]
    listes = {e['cmd'] for e in entrees}

    print(f'# Analyse {defs}\n')
    print(f'- entrées cmdtbl : {len(entrees)} (spécifiques {fam}/{var} : {len(spec)}, autres : {len(entrees) - len(spec)})')
    idx = [d['idx'] for d in dump]
    trous = sorted(set(range(1, max(idx) + 1)) - set(idx)) if idx else []
    print(f'- dump : {len(dump)} enregistrements IA1, {n_ia2} IA2, index manquants : {trous}')
    for t in trous:
        voisins = {d['idx']: d['line'] for d in dump}
        avant, apres = voisins.get(t - 1, '?'), voisins.get(t + 1, '?')
        print(f'  - trou {t} : entre les lignes {avant} et {apres}')

    print('\n## A. Entrées spécifiques sans objet dans le dump (hors lignes >= 10000)')
    for e in spec:
        if e['cmd'] not in par_cmd and e['line'] < 10000:
            print(f"- {e['line']:g} {e['cmd']:#010x} {e['vt']} {e['flags']} « {e['texte']} »")

    print('\n## B. Objets du dump absents de la liste')
    for d in dump:
        if d['cmd'] not in listes:
            print(f"- ligne {d['line']} {d['cmd']:#010x} id2={d['id2']:#04x} id3={d['id3']:#04x} id4={d['id4']:#04x}")

    print('\n## C. Numéro de ligne différent (hors objets de ligne 0 renumérotés >= 10000)')
    for e in spec:
        for d in par_cmd.get(e['cmd'], []):
            if d['line'] and int(e['line']) != d['line'] and e['line'] < 10000:
                print(f"- {e['cmd']:#010x} liste {e['line']:g} / dump {d['line']} « {e['texte']} »")

    print('\n## D. Taille de donnée : optbl contre dump')
    bilan = collections.Counter()
    for e in spec:
        for d in par_cmd.get(e['cmd'], []):
            if d['line'] != int(e['line']) or d['id2'] not in TAILLE_ID2 or e['vt'] not in optbl:
                continue
            ok = (optbl[e['vt']]['pl'] & 31) == TAILLE_ID2[d['id2']]
            bilan[ok] += 1
            if not ok and not (optbl[e['vt']]['dt'] == 'DT_ENUM' and TAILLE_ID2[d['id2']] == 2):
                print(f"- {e['line']:g} {e['vt']} optbl={optbl[e['vt']]['pl'] & 31} o, dump={TAILLE_ID2[d['id2']]} o")
    print(f'- concordants : {bilan[True]}, discordants : {bilan[False]} (ENUM 2 octets exclus de la liste ci-dessus)')

    print('\n## E. Niveau d\'accès (id4) contre drapeaux')
    acces = collections.Counter()
    for e in spec:
        for d in par_cmd.get(e['cmd'], []):
            if d['line'] == int(e['line']):
                acces[(e['flags'], d['id4'])] += 1
                if (d['id4'] >> 4) and 'FL_RONLY' in e['flags'] or (d['id4'] >> 4) == 0 and 'FL_RONLY' not in e['flags'] \
                        or (d['id4'] >> 4) == 6 or (d['id4'] >> 4) not in (0, d['id4'] & 15):
                    print(f"- {e['line']:g} {e['flags']} id4={d['id4']:#04x} « {e['texte']} »")
    for (f, i), n in sorted(acces.items()):
        print(f'  - {f:16s} id4={i:#04x} : {n}')

    print('\n## F. Types sans contrôle de taille (structures)')
    nc = collections.Counter(e['vt'] for e in spec if optbl.get(e['vt'], {}).get('dt') in ('DT_STRN', 'DT_DTTM', 'DT_TIMEPROG', 'DT_DDMM'))
    print('- ' + ', '.join(f'{k} : {v}' for k, v in nc.most_common()))

    print('\n## G. Textes partagés par plusieurs entrées')
    c = collections.Counter(e['texte'] for e in spec if e['texte'])
    print(f'- {sum(1 for v in c.values() if v > 1)} textes partagés par {sum(v for v in c.values() if v > 1)} entrées')


if __name__ == '__main__':
    main()
