#!/usr/bin/env python3
"""Génère le projet KiCad 9 de la carte d'interface à partir de carte.py.

À lancer dans l'image kicad/kicad:9.0.6, via docker/kicad/generer_carte.sh (docs/claude/09 §9) :
    python3 gen_kicad.py <dossier_sortie>
Produit <PROJET>.kicad_pro, .kicad_sch (connexions par étiquettes de net) et
.kicad_pcb (composants placés, nets affectés, contour, zones interdites ; routage à faire).
Les UUID sont dérivés des références : la génération est reproductible.
"""
import json
import os
import sys
import uuid

import carte
import libsym
from sexpr import Sym, dump

ESPACE = uuid.UUID('6f1c2b1e-5a0e-4c1e-9d3a-a1fea0000000')
RACINE = str(uuid.uuid5(ESPACE, 'racine'))


def uid(*cles):
    return str(uuid.uuid5(ESPACE, '/'.join(cles)))


def S(x):
    return Sym(x)


def effets(taille=1.27, cache=False, justif=None):
    e = [S('effects'), [S('font'), [S('size'), taille, taille]]]
    if justif:
        e.append([S('justify'), S(justif)])
    if cache:
        e.append([S('hide'), S('yes')])
    return e


def prop(nom, valeur, x, y, cache=False, justif=None):
    return [S('property'), nom, valeur, [S('at'), x, y, 0], effets(cache=cache, justif=justif)]


def r(v):
    return round(v, 2)


# ----------------------------------------------------------------------------- schéma
VERTICAUX = {'Device:R', 'Device:C', 'Device:C_Polarized', 'Device:Polyfuse'}
HORIZONTAUX = {'Device:D', 'Device:LED', 'Device:D_TVS', 'Device:D_Schottky'}


def pos_ref(lib, x, y):
    """Positions de la référence et de la valeur selon l'orientation du symbole."""
    if lib in VERTICAUX:
        return (r(x + 2.54), r(y - 1.27)), (r(x + 2.54), r(y + 1.27))
    if lib in HORIZONTAUX:
        return (x, r(y - 3.81)), (x, r(y + 3.81))
    if lib.startswith('Connector'):
        return (x, r(y - 12.7)), (x, r(y + 15.24))
    return (x, r(y - 7.62)), (x, r(y + 7.62))


def schema():
    libs, corps = {}, []
    for c in carte.COMPOSANTS:
        libs.setdefault(c['lib'], libsym.symbole(c['lib']))
        x, y = c['sch']
        brs = libsym.broches(c['lib'])
        sym = [S('symbol'), [S('lib_id'), c['lib']], [S('at'), x, y, 0], [S('unit'), 1],
               [S('exclude_from_sim'), S('no')], [S('in_bom'), S('yes')], [S('on_board'), S('yes')],
               [S('dnp'), S('no')], [S('uuid'), uid('sym', c['ref'])],
               prop('Reference', c['ref'], *pos_ref(c['lib'], x, y)[0], justif='left' if c['lib'] in VERTICAUX else None),
               prop('Value', c['val'], *pos_ref(c['lib'], x, y)[1], justif='left' if c['lib'] in VERTICAUX else None),
               prop('Footprint', c['fp'], x, y, cache=True),
               prop('Datasheet', '~', x, y, cache=True),
               prop('Description', '', x, y, cache=True),
               prop('MPN', c['mpn'], x, y, cache=True)]
        for num in sorted(brs, key=lambda n: int(n)):
            sym.append([S('pin'), num, [S('uuid'), uid('pin', c['ref'], num)]])
        sym.append([S('instances'), [S('project'), carte.PROJET,
                                     [S('path'), '/' + RACINE, [S('reference'), c['ref']], [S('unit'), 1]]]])
        corps.append(sym)
        noms = carte.SUPERMINI.get(c['ref'])
        for num, (px, py, angle, _, typ) in brs.items():
            ax, ay = r(x + px), r(y - py)
            net = c['pins'].get(num)
            if net:
                a_lbl = (angle + 180) % 360
                corps.append([S('label'), net, [S('at'), ax, ay, a_lbl],
                              effets(justif='left' if a_lbl in (0, 90) else 'right'), [S('uuid'), uid('lbl', c['ref'], num)]])
            elif num in c.get('nc', []) and typ != 'no_connect':
                corps.append([S('no_connect'), [S('at'), ax, ay], [S('uuid'), uid('nc', c['ref'], num)]])
            if noms:
                corps.append([S('text'), noms[int(num) - 1], [S('at'), r(x + 1.27), ay, 0],
                              effets(1.0, justif='left'), [S('uuid'), uid('txt', c['ref'], num)]])
    for i, ((x, y), texte) in enumerate(carte.NOTES):
        corps.append([S('text'), texte, [S('at'), x, y, 0], effets(1.5, justif='left'), [S('uuid'), uid('note', str(i))]])
    doc = [S('kicad_sch'), [S('version'), S('20250114')], [S('generator'), 'eeschema'], [S('generator_version'), '9.0'],
           [S('uuid'), RACINE], [S('paper'), 'A3'],
           [S('title_block'), [S('title'), "Interface BSB isolée pour ESP32-C3 SuperMini (Alféa Extensa Duo A.I.)"],
            [S('rev'), 'A'], [S('company'), 'branche alfea-extensa'],
            [S('comment'), 1, 'Généré par alfea/hardware/gen/gen_kicad.py, ne pas éditer sans régénérer ou reporter dans carte.py'],
            [S('comment'), 2, 'Connexions par étiquettes de net ; topologie adaptateur BSB-LAN V3 (docs/claude/06 et 09)']],
           [S('lib_symbols')] + list(libs.values())] + corps + [
        [S('sheet_instances'), [S('path'), '/', [S('page'), '1']]],
        [S('embedded_fonts'), S('no')]]
    return dump(doc) + '\n'


# ----------------------------------------------------------------------------- PCB
def pcb(chemin):
    import pcbnew
    mm = pcbnew.FromMM
    board = pcbnew.BOARD()
    nets = {}

    def net(nom):
        if nom not in nets:
            nets[nom] = pcbnew.NETINFO_ITEM(board, '/' + nom)
            board.Add(nets[nom])
        return nets[nom]

    racine_fp = '/usr/share/kicad/footprints'
    for c in carte.COMPOSANTS:
        lib, nom = c['fp'].split(':')
        fp = pcbnew.FootprintLoad(os.path.join(racine_fp, lib + '.pretty'), nom)
        fp.SetFPID(pcbnew.LIB_ID(lib, nom))
        fp.SetReference(c['ref'])
        fp.SetValue(c['val'])
        fp.SetPath(pcbnew.KIID_PATH('/' + uid('sym', c['ref'])))
        x, y, rot = c['pcb']
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(rot)
        if lib.split('_')[0] in ('Resistor', 'Capacitor', 'Diode', 'LED', 'Fuse') or lib == 'Package_TO_SOT_SMD':
            # carte dense : références des CMS sur le plan d'assemblage (F.Fab), pas en sérigraphie
            fp.Reference().SetLayer(pcbnew.F_Fab)
        if 'ref_at' in c:
            fp.Reference().SetPosition(pcbnew.VECTOR2I(mm(c['ref_at'][0]), mm(c['ref_at'][1])))
        brs = libsym.broches(c['lib'])
        for pad in fp.Pads():
            num = pad.GetNumber()
            n = c['pins'].get(num)
            if n:
                pad.SetNet(net(n))
            elif num in brs:
                # convention KiCad pour une broche non connectée : unconnected-(REF-Nom-PadN)
                nom_br = brs[num][3]
                nom_net = f"unconnected-({c['ref']}-{nom_br + '-' if nom_br != '~' else ''}Pad{num})"
                ni = pcbnew.NETINFO_ITEM(board, nom_net)
                board.Add(ni)
                pad.SetNet(ni)
        board.Add(fp)
    for i, (x, y) in enumerate(carte.TROUS, 1):
        fp = pcbnew.FootprintLoad(os.path.join(racine_fp, 'MountingHole.pretty'), 'MountingHole_3.2mm_M3')
        fp.SetFPID(pcbnew.LIB_ID('MountingHole', 'MountingHole_3.2mm_M3'))
        fp.SetReference(f'H{i}')
        fp.Reference().SetVisible(False)
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        board.Add(fp)

    def rect(couche, x0, y0, x1, y1, largeur=0.1):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetLayer(couche)
            s.SetWidth(mm(largeur))
            s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
            s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
            board.Add(s)

    rect(pcbnew.Edge_Cuts, *carte.CARTE, largeur=0.05)

    def zone_interdite(nom, x0, y0, x1, y1):
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetZoneName(nom)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
        o = z.Outline()
        o.NewOutline()
        for px, py in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            o.Append(mm(px), mm(py))
        o.Outline(0).SetClosed(True)
        board.Add(z)

    zone_interdite('ISOLATION', *carte.ISOLATION)
    zone_interdite('ANTENNE', *carte.ANTENNE)

    def texte(t, x, y, couche=pcbnew.F_SilkS, h=1.0):
        p = pcbnew.PCB_TEXT(board)
        p.SetText(t)
        p.SetLayer(couche)
        p.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        p.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h)))
        p.SetTextThickness(mm(h * 0.15))
        board.Add(p)

    texte('BUS BSB', 113.5, 131.0)
    texte('ESP32-C3', 149.0, 105.6)
    texte('CL+', 110.3, 117.7, h=0.8)
    texte('CL-', 110.3, 115.16, h=0.8)
    texte('J2 : 5V / GND', 143.5, 101.6, h=0.8)
    texte('GND DAT 3V3', 134.3, 124.2, h=0.8)
    texte('X86 : CL+ / CL-', 106.5, 122.6, h=0.8)
    texte('ANTENNE', 138.3, 116.0, couche=pcbnew.Dwgs_User, h=1.0)
    texte('Interface BSB C3 rev B', 148.5, 130.5, h=0.8)
    pcbnew.SaveBoard(chemin, board)


def projet(chemin):
    json.dump({'meta': {'filename': os.path.basename(chemin), 'version': 3},
               'board': {'design_settings': {'defaults': {}, 'rules': {'min_clearance': 0.2}}},
               'sheets': [[RACINE, 'Racine']]}, open(chemin, 'w', encoding='utf-8'), indent=2)


def main():
    """Le schéma et le projet, une fois édités dans KiCad, deviennent la référence : on ne les écrase
    que s'ils n'existent pas (ou avec --schema). Le PCB (placement) est toujours régénéré ; le DRC avec
    parité vérifie qu'il correspond au schéma."""
    sortie = sys.argv[1]
    force = '--schema' in sys.argv[2:]
    os.makedirs(sortie, exist_ok=True)
    base = os.path.join(sortie, carte.PROJET)
    pro_existe = os.path.exists(base + '.kicad_pro')
    if force or not os.path.exists(base + '.kicad_sch'):
        open(base + '.kicad_sch', 'w', encoding='utf-8').write(schema())
    if pro_existe:
        sauve = open(base + '.kicad_pro', encoding='utf-8').read()
    pcb(base + '.kicad_pcb')
    if pro_existe:          # SaveBoard réécrit le .kicad_pro : on restaure celui de KiCad
        open(base + '.kicad_pro', 'w', encoding='utf-8').write(sauve)
    else:
        projet(base + '.kicad_pro')
    print('généré :', base + '.kicad_pcb')


if __name__ == '__main__':
    main()
