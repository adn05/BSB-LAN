#!/usr/bin/env python3
"""Génère la variante traversante (plaquette à bandes) de la carte d'interface.

À lancer dans l'image kicad/kicad:9.0.6, via docker/kicad/generer_carte.sh (docs/claude/09b) :
    python3 gen_plaquette.py <schéma_maître.kicad_sch> <dossier_sortie>
Produit, dans <dossier_sortie> :
- <PROJET>.kicad_sch : copie du schéma maître (celui édité dans KiCad), valeurs et empreintes traversantes ;
- <PROJET>.kicad_pcb : la plaquette ; chaque bande est une piste B.Cu (coupée aux COUPES),
  chaque fil de liaison est une piste F.Cu entre deux trous. Le DRC détecte ainsi un court-circuit
  (deux nets sur une même bande) ou une liaison manquante ;
- alfea_tht.pretty/ et fp-lib-table : empreinte locale de la PTC radiale ;
- sorties/plan.txt : coupes, fils et positions, en repère plaquette (bandes A, B, ..., trous 1, 2, ...).
"""
import json
import math
import os
import sys
import uuid

import carte
import libsym
import plaquette as P
from sexpr import Sym, dump, parse, trouver, un

S = Sym

ESPACE = uuid.UUID('6f1c2b1e-5a0e-4c1e-9d3a-a1fea0000001')


def uid(*cles):
    return str(uuid.uuid5(ESPACE, '/'.join(cles)))


def xy(c, r):
    return P.ORIGINE[0] + c * P.PAS, P.ORIGINE[1] + r * P.PAS


def nom_trou(c, r):
    """Repère lisible : bande (lettre) + trou (numéro), à partir du coin haut gauche de la plaquette."""
    return f'{chr(ord("A") + r - P.RANGEES[0])}{c - P.COLONNES[0] + 1}'


# ----------------------------------------------------------------------------- nets et broches
def broches_tht():
    """{réf: {pastille: net}} pour la variante : nets de carte.py, broches des TO-92 renumérotées."""
    res = {}
    for c in carte.COMPOSANTS:
        pins = dict(c['pins'])
        if c['lib'] in P.SYMBOLES:
            pins = {P.BROCHES_TO92[k]: v for k, v in pins.items()}
        res[c['ref']] = pins
    return res


# ----------------------------------------------------------------------------- schéma
def schema(maitre, sortie):
    doc = parse(open(maitre, encoding='utf-8').read())
    par_ref = {c['ref']: c for c in carte.COMPOSANTS}
    tb = un(doc, 'title_block')
    for x in tb:
        if isinstance(x, list) and x[0] == 'title':
            x[1] = x[1].split(' — ')[0] + ' — variante traversante (plaquette à bandes)'
        if isinstance(x, list) and x[0] == 'comment' and str(x[1]) == '1':
            x[2] = 'Dérivé du schéma maître carte_bsb_c3 par alfea/hardware/gen/gen_plaquette.py : ne pas éditer ici'
    # BC847/BC857 -> BC547/BC557 : même dessin (B à gauche, C en haut, E en bas), numéros de broches différents
    libs = un(doc, 'lib_symbols')
    for i, s in enumerate(libs):
        if isinstance(s, list) and s[0] == 'symbol' and s[1] in P.SYMBOLES:
            libs[i] = libsym.symbole(P.SYMBOLES[s[1]])
    for s in trouver(doc, 'symbol'):
        lib = un(s, 'lib_id')
        props = {p[1]: p for p in trouver(s, 'property')}
        ref = props['Reference'][2]
        if ref not in P.COMPOSANTS:
            continue
        val, fp, mpn, _ = P.COMPOSANTS[ref]
        if lib[1] in P.SYMBOLES:
            lib[1] = P.SYMBOLES[lib[1]]
        props['Value'][2] = val
        if fp:
            props['Footprint'][2] = fp
        if mpn:
            props['MPN'][2] = mpn
        if ref in P.NON_MONTES:
            un(s, 'dnp')[1] = Sym('yes')
            un(s, 'in_bom')[1] = Sym('no')
        for inst in trouver(s, 'instances'):
            for proj in trouver(inst, 'project'):
                proj[1] = P.PROJET
        assert ref in par_ref, ref
    texte = dump(doc) + '\n'
    open(os.path.join(sortie, P.PROJET + '.kicad_sch'), 'w', encoding='utf-8').write(texte)
    # même UUID racine que le maître : le PCB référence les symboles par /racine/symbole
    uuids = {}
    for s in trouver(doc, 'symbol'):
        ref = [p for p in trouver(s, 'property') if p[1] == 'Reference'][0][2]
        uuids[ref] = un(s, 'uuid')[1]
    return un(doc, 'uuid')[1], uuids


# ----------------------------------------------------------------------------- empreinte locale
def empreinte_ptc(dossier):
    """PTC radiale à pattes droites au pas de 5,08 mm (Bourns MF-R010 : pas 5,1 mm, 7,4 × 3,0 mm)."""
    def rect(couche, x0, y0, x1, y1, l):
        return [S('fp_rect'), [S('start'), x0, y0], [S('end'), x1, y1],
                [S('stroke'), [S('width'), l], [S('type'), S('solid')]], [S('fill'), S('no')], [S('layer'), couche]]

    def pad(n, x, forme):
        return [S('pad'), n, S('thru_hole'), S(forme), [S('at'), x, 0], [S('size'), 1.6, 1.6], [S('drill'), 0.8],
                [S('layers'), '*.Cu', '*.Mask']]

    def txt(genre, valeur, y, couche):
        return [S('property'), genre, valeur, [S('at'), 2.54, y, 0], [S('layer'), couche],
                [S('effects'), [S('font'), [S('size'), 1, 1], [S('thickness'), 0.15]]]]
    fp = [S('footprint'), 'PTC_Radial_P5.08mm', [S('version'), S('20241229')], [S('generator'), 'gen_plaquette'],
          [S('layer'), 'F.Cu'],
          [S('descr'), 'PTC radiale, pattes droites, pas 5,08 mm, corps 7,4 x 3,0 mm (Bourns MF-R010)'],
          txt('Reference', 'REF**', -2.6, 'F.SilkS'), txt('Value', 'PTC_Radial_P5.08mm', 2.6, 'F.Fab'),
          [S('attr'), S('through_hole')],
          rect('F.Fab', -1.16, -1.5, 6.24, 1.5, 0.1), rect('F.SilkS', -1.28, -1.62, 6.36, 1.62, 0.12),
          rect('F.CrtYd', -1.41, -1.75, 6.49, 1.75, 0.05),
          pad('1', 0, 'rect'), pad('2', 5.08, 'circle')]
    os.makedirs(dossier, exist_ok=True)
    open(os.path.join(dossier, 'PTC_Radial_P5.08mm.kicad_mod'), 'w', encoding='utf-8').write(dump(fp) + '\n')


# ----------------------------------------------------------------------------- PCB
def pcb(sortie, racine, uuids):
    import pcbnew
    mm = pcbnew.FromMM
    dossier_lib = os.path.join(sortie, P.LIB_LOCALE + '.pretty')
    empreinte_ptc(dossier_lib)
    open(os.path.join(sortie, 'fp-lib-table'), 'w', encoding='utf-8').write(
        '(fp_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")(options "")(descr "Empreintes locales"))\n)\n'
        % (P.LIB_LOCALE, P.LIB_LOCALE))
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.m_MinClearance = mm(0.3)
    ds.SetCopperLayerCount(2)
    nets = {}

    def net(nom):
        if nom not in nets:
            nets[nom] = pcbnew.NETINFO_ITEM(board, nom if nom.startswith('unconnected') else '/' + nom)
            board.Add(nets[nom])
        return nets[nom]

    racine_fp = '/usr/share/kicad/footprints'
    affect = broches_tht()
    par_ref = {c['ref']: c for c in carte.COMPOSANTS}
    trous = {}          # (c, r) -> (réf, pastille, net)
    pastilles = []      # (réf, pastille, x, y, net)
    rapport = []
    for ref, (val, fp_nom, mpn, places) in P.COMPOSANTS.items():
        c = par_ref[ref]
        fp_id = fp_nom or c['fp']
        lib, nom = fp_id.split(':')
        chemin_lib = dossier_lib if lib == P.LIB_LOCALE else os.path.join(racine_fp, lib + '.pretty')
        fp = pcbnew.FootprintLoad(chemin_lib, nom)
        fp.SetFPID(pcbnew.LIB_ID(lib, nom))
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetPath(pcbnew.KIID_PATH('/' + racine + '/' + uuids[ref]))
        if ref in P.NON_MONTES:
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_DNP | pcbnew.FP_EXCLUDE_FROM_BOM)
        # orientation : on essaie les 4 rotations et on garde celle qui pose les pastilles demandées sur la grille
        (n1, p1), (n2, p2) = list(places.items())[:2]
        meilleur = None
        for rot in (0, 90, 180, 270):
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(pcbnew.VECTOR2I(0, 0))
            pads = {p.GetNumber(): p for p in fp.Pads() if p.GetNumber()}
            a, b = pads[n1].GetPosition(), pads[n2].GetPosition()
            cible1, cible2 = xy(*p1), xy(*p2)
            dx, dy = pcbnew.ToMM(b.x - a.x), pcbnew.ToMM(b.y - a.y)
            err = math.hypot(dx - (cible2[0] - cible1[0]), dy - (cible2[1] - cible1[1]))
            if meilleur is None or err < meilleur[0]:
                meilleur = (err, rot, pcbnew.ToMM(a.x), pcbnew.ToMM(a.y))
        err, rot, ax, ay = meilleur
        assert err < 0.15, f'{ref} : pastilles {n1}/{n2} impossibles à poser sur {p1}/{p2} (écart {err:.2f} mm)'
        fp.SetOrientationDegrees(rot)
        cx, cy = xy(*p1)
        fp.SetPosition(pcbnew.VECTOR2I(mm(cx - ax), mm(cy - ay)))
        # nets et contrôle de grille de toutes les pastilles
        brs = affect[ref]
        for pad in fp.Pads():
            num = pad.GetNumber()
            if not num:
                continue
            x, y = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
            cc, rr = (x - P.ORIGINE[0]) / P.PAS, (y - P.ORIGINE[1]) / P.PAS
            ci, ri = round(cc), round(rr)
            assert abs(cc - ci) * P.PAS < 0.15 and abs(rr - ri) * P.PAS < 0.15, f'{ref}.{num} hors grille ({x:.2f}, {y:.2f})'
            n = brs.get(num)
            if n:
                pad.SetNet(net(n))
            else:
                # convention KiCad pour une broche non connectée : unconnected-(REF-Nom-PadN)
                nom_br = libsym.broches(c['lib'])[num][3]
                n = f"unconnected-({ref}-{nom_br + '-' if nom_br != '~' else ''}Pad{num})"
                pad.SetNet(net(n))
            assert (ci, ri) not in trous, f'trou {nom_trou(ci, ri)} pris par {trous[(ci, ri)]} et {ref}.{num}'
            trous[(ci, ri)] = (ref, num, n)
            pastilles.append((ref, num, ci, ri, n))
        # référence au centre du composant, sur le plan d'assemblage (la plaquette n'a pas de sérigraphie)
        bb = fp.GetBoundingBox(False)
        fp.Reference().SetLayer(pcbnew.F_Fab)
        fp.Reference().SetPosition(bb.GetCenter())
        fp.Reference().SetTextAngleDegrees(0)
        board.Add(fp)
        rapport.append((ref, val, mpn or c['mpn'], fp_id, ', '.join(f'{nm}:{nom_trou(*places[nm])}' for nm in places), rot))

    # ---- fils de liaison : deux trous (vias) et une piste F.Cu
    for i, (n, c, r0, r1) in enumerate(P.LIENS):
        for r in (r0, r1):
            assert (c, r) not in trous, f'lien {n} : trou {nom_trou(c, r)} déjà pris par {trous[(c, r)]}'
            trous[(c, r)] = ('fil', str(i + 1), n)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(mm(xy(c, r)[0]), mm(xy(c, r)[1])))
            v.SetWidth(mm(1.6))
            v.SetDrill(mm(0.9))
            v.SetNet(net(n))
            board.Add(v)
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(mm(xy(c, r0)[0]), mm(xy(c, r0)[1])))
        t.SetEnd(pcbnew.VECTOR2I(mm(xy(c, r1)[0]), mm(xy(c, r1)[1])))
        t.SetWidth(mm(0.6))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(net(n))
        board.Add(t)

    # ---- bandes : segments entre coupes, net déduit des trous ; deux nets sur un segment = erreur
    coupes = set(P.COUPES) | {(c, r) for c in P.ISOLATION for r in range(P.RANGEES[0], P.RANGEES[1] + 1)}
    for c, r in coupes:
        assert (c, r) not in trous, f'coupe sur un trou utilisé : {nom_trou(c, r)} {trous[(c, r)]}'
    segments = []
    for r in range(P.RANGEES[0], P.RANGEES[1] + 1):
        debut = P.COLONNES[0] - 0.5
        bornes = sorted(c for c, rr in coupes if rr == r) + [P.COLONNES[1] + 1]
        for fin_c in bornes:
            fin = fin_c - 0.5
            if fin > debut:
                dans = [trous[(c, r)] for c in range(math.ceil(debut), math.floor(fin) + 1) if (c, r) in trous]
                noms = {t[2] for t in dans}
                assert len(noms) <= 1, f'bande {nom_trou(int(debut + 0.5), r)} : court-circuit entre {noms}'
                segments.append((r, debut, fin, noms.pop() if noms else None, dans))
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(mm(xy(debut, r)[0]), mm(xy(debut, r)[1])))
                t.SetEnd(pcbnew.VECTOR2I(mm(xy(fin, r)[0]), mm(xy(fin, r)[1])))
                t.SetWidth(mm(1.6))
                t.SetLayer(pcbnew.B_Cu)
                if dans:
                    t.SetNet(net(dans[0][2]))
                board.Add(t)
            debut = fin_c + 0.5

    # ---- contour, grille de trous, coupes, repères
    x0, y0 = xy(P.COLONNES[0] - 0.5, P.RANGEES[0] - 0.5)
    x1, y1 = xy(P.COLONNES[1] + 0.5, P.RANGEES[1] + 0.5)

    def segment(couche, a, b, l=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(couche)
        s.SetWidth(mm(l))
        s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        board.Add(s)

    for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        segment(pcbnew.Edge_Cuts, a, b, 0.05)
    for c in range(P.COLONNES[0], P.COLONNES[1] + 1):
        for r in range(P.RANGEES[0], P.RANGEES[1] + 1):
            if (c, r) in trous:
                continue
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_CIRCLE)
            s.SetLayer(pcbnew.Dwgs_User)
            s.SetWidth(mm(0.1))
            px, py = xy(c, r)
            s.SetCenter(pcbnew.VECTOR2I(mm(px), mm(py)))
            s.SetEnd(pcbnew.VECTOR2I(mm(px + 0.5), mm(py)))
            board.Add(s)
    for c, r in sorted(coupes):
        px, py = xy(c, r)
        for couche in (pcbnew.B_SilkS, pcbnew.Dwgs_User):
            segment(couche, (px - 0.9, py - 0.9), (px + 0.9, py + 0.9), 0.25)
            segment(couche, (px - 0.9, py + 0.9), (px + 0.9, py - 0.9), 0.25)

    def texte(t, x, y, couche=pcbnew.F_SilkS, h=1.0, miroir=False):
        p = pcbnew.PCB_TEXT(board)
        p.SetText(t)
        p.SetLayer(couche)
        p.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        p.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h)))
        p.SetTextThickness(mm(h * 0.15))
        p.SetMirrored(miroir)
        board.Add(p)

    for r in range(P.RANGEES[0], P.RANGEES[1] + 1):
        lettre = nom_trou(P.COLONNES[0], r)[0]
        texte(lettre, x0 - 1.5, xy(0, r)[1], pcbnew.Dwgs_User, 1.2)
        texte(lettre, x1 + 1.5, xy(0, r)[1], pcbnew.Dwgs_User, 1.2)
    for c in range(P.COLONNES[0], P.COLONNES[1] + 1):
        n = c - P.COLONNES[0] + 1
        if n == 1 or n % 5 == 0:
            texte(str(n), xy(c, 0)[0], y0 - 1.6, pcbnew.Dwgs_User, 1.0)
            texte(str(n), xy(c, 0)[0], y1 + 1.6, pcbnew.Dwgs_User, 1.0)
    texte('BUS BSB (isolé)', xy(9, 0)[0], y1 - 1.0, pcbnew.Dwgs_User, 1.2)
    texte('ESP32-C3', xy(30, 0)[0], y1 - 1.0, pcbnew.Dwgs_User, 1.2)
    texte('USB', xy(42, 0)[0], y1 - 1.0, pcbnew.Dwgs_User, 1.2)
    texte('CL+', xy(-1, 4)[0] + 0.2, xy(-1, 4)[1], pcbnew.F_SilkS, 0.8)
    texte('CL-', xy(-1, 3)[0] + 0.2, xy(-1, 3)[1], pcbnew.F_SilkS, 0.8)
    pcbnew.SaveBoard(os.path.join(sortie, P.PROJET + '.kicad_pcb'), board)
    return rapport, segments, pastilles


def plan(sortie, rapport, segments):
    lignes = ['Plaquette à bandes : %d bandes (%s à %s) x %d trous (1 à %d), pas 2,54 mm.' % (
        P.RANGEES[1] - P.RANGEES[0] + 1, nom_trou(0, P.RANGEES[0])[0], nom_trou(0, P.RANGEES[1])[0],
        P.COLONNES[1] - P.COLONNES[0] + 1, P.COLONNES[1] - P.COLONNES[0] + 1),
        'Repère : bande = lettre (de haut en bas, côté composants), trou = numéro (de gauche à droite, côté composants).',
        '', '1. COUPES (côté cuivre : attention, gauche et droite sont inversées quand on retourne la plaquette)']
    iso = ', '.join(str(c - P.COLONNES[0] + 1) for c in P.ISOLATION)
    lignes.append(f'   - isolation : toutes les bandes aux trous {iso} (rainure continue conseillée)')
    for c, r in sorted(P.COUPES, key=lambda t: (t[1], t[0])):
        lignes.append(f'   - {nom_trou(c, r)}')
    lignes += ['', '2. FILS DE LIAISON (côté composants)']
    for i, (n, c, r0, r1) in enumerate(P.LIENS, 1):
        lignes.append(f'   - fil {i} : {nom_trou(c, r0)} -> {nom_trou(c, r1)} ({n.lstrip("/")})')
    lignes += ['', '3. COMPOSANTS (pastille:trou)']
    for ref, val, mpn, fp, places, rot in rapport:
        nm = ' [NON MONTÉ]' if ref in P.NON_MONTES else ''
        lignes.append(f'   - {ref:4s} {val:16s} {places:22s} {mpn}{nm}')
    lignes += ['', '4. BANDES UTILISÉES (net : bande, trous)']
    for r, d, f, n, dans in segments:
        if n:
            lignes.append(f'   - {n.lstrip("/"):12s} {nom_trou(int(d + 0.5), r)}..{nom_trou(int(f - 0.5), r)[1:]} '
                          f'({", ".join(t[0] + ("." + t[1] if t[0] != "fil" else "") for t in dans)})')
    os.makedirs(os.path.join(sortie, 'sorties'), exist_ok=True)
    open(os.path.join(sortie, 'sorties', 'plan.txt'), 'w', encoding='utf-8').write('\n'.join(lignes) + '\n')


def dessin(sortie, pastilles, segments, miroir):
    """Plan de montage SVG : côté composants, ou côté cuivre (miroir gauche-droite) pour les coupes."""
    k = 10.0                      # pixels par pas
    c0, c1 = P.COLONNES
    r0, r1 = P.RANGEES
    larg, haut = (c1 - c0 + 4) * k, (r1 - r0 + 5) * k

    def X(c):
        u = c - c0 + 2
        return (larg - u * k) if miroir else u * k

    def Y(r):
        return (r - r0 + 2.5) * k
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{larg * 2:.0f}" height="{haut * 2:.0f}" '
         f'viewBox="0 0 {larg:.0f} {haut:.0f}" font-family="sans-serif">',
         f'<rect width="{larg:.0f}" height="{haut:.0f}" fill="#fff"/>',
         f'<text x="{larg / 2:.0f}" y="{k * 0.9:.1f}" font-size="{k * 0.8:.1f}" text-anchor="middle">'
         f'{"CÔTÉ CUIVRE (plaquette retournée) : X rouge = coupe" if miroir else "CÔTÉ COMPOSANTS : trait bleu = fil de liaison"}</text>']
    for r, d, f, n, dans in segments:
        xa, xb = sorted((X(d), X(f)))
        o.append(f'<rect x="{xa:.1f}" y="{Y(r) - 0.38 * k:.1f}" width="{xb - xa:.1f}" height="{0.76 * k:.1f}" '
                 f'fill="{"#e9b97a" if n else "#f3e3cc"}"/>')
        if n and not miroir and not n.startswith('unconnected'):
            o.append(f'<text x="{xb - 0.2 * k:.1f}" y="{Y(r) + 0.15 * k:.1f}" font-size="{0.42 * k:.1f}" '
                     f'text-anchor="end" fill="#8a5a1c">{n.lstrip("/")}</text>')
    for c in range(c0, c1 + 1):
        for r in range(r0, r1 + 1):
            o.append(f'<circle cx="{X(c):.1f}" cy="{Y(r):.1f}" r="{0.13 * k:.1f}" fill="#fff" stroke="#999" stroke-width="0.3"/>')
        n = c - c0 + 1
        if n == 1 or n % 5 == 0:
            for y in (Y(r0) - 1.1 * k, Y(r1) + 1.5 * k):
                o.append(f'<text x="{X(c):.1f}" y="{y:.1f}" font-size="{0.6 * k:.1f}" text-anchor="middle">{n}</text>')
    for r in range(r0, r1 + 1):
        for x in (k * 0.9, larg - k * 0.9):
            o.append(f'<text x="{x:.1f}" y="{Y(r) + 0.2 * k:.1f}" font-size="{0.6 * k:.1f}" text-anchor="middle">'
                     f'{nom_trou(c0, r)[0]}</text>')
    coupes = set(P.COUPES) | {(c, r) for c in P.ISOLATION for r in range(r0, r1 + 1)}
    for c, r in coupes:
        s = 0.42 * k
        o.append(f'<path d="M{X(c) - s:.1f},{Y(r) - s:.1f}L{X(c) + s:.1f},{Y(r) + s:.1f}M{X(c) - s:.1f},{Y(r) + s:.1f}'
                 f'L{X(c) + s:.1f},{Y(r) - s:.1f}" stroke="#d00" stroke-width="{0.18 * k:.1f}"/>')
    if not miroir:
        par_ref = {}
        for ref, num, c, r, n in pastilles:
            par_ref.setdefault(ref, []).append((c, r, num))
        for ref, pts in par_ref.items():
            xs, ys = [X(c) for c, r, _ in pts], [Y(r) for c, r, _ in pts]
            pad = 0.45 * k
            o.append(f'<rect x="{min(xs) - pad:.1f}" y="{min(ys) - pad:.1f}" width="{max(xs) - min(xs) + 2 * pad:.1f}" '
                     f'height="{max(ys) - min(ys) + 2 * pad:.1f}" rx="{0.3 * k:.1f}" fill="#ffffffaa" '
                     + ('stroke="#999" stroke-width="0.6" stroke-dasharray="2,1"/>' if ref in P.NON_MONTES
                        else 'stroke="#222" stroke-width="0.6"/>'))
            for c, r, num in pts:
                o.append(f'<circle cx="{X(c):.1f}" cy="{Y(r):.1f}" r="{0.28 * k:.1f}" fill="#333"/>')
                o.append(f'<text x="{X(c) + 0.3 * k:.1f}" y="{Y(r) - 0.3 * k:.1f}" font-size="{0.35 * k:.1f}" fill="#555">{num}</text>')
            vertical = max(ys) - min(ys) >= max(xs) - min(xs)
            tx = max(xs) + pad + 0.1 * k if vertical else (min(xs) + max(xs)) / 2
            ty = (min(ys) + max(ys)) / 2 + 0.2 * k if vertical else min(ys) - pad - 0.15 * k
            o.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="{0.55 * k:.1f}" font-weight="bold" '
                     f'text-anchor="{"start" if vertical else "middle"}">{ref}</text>')
        for n, c, ra, rb in P.LIENS:
            o.append(f'<line x1="{X(c):.1f}" y1="{Y(ra):.1f}" x2="{X(c):.1f}" y2="{Y(rb):.1f}" stroke="#1565c0" '
                     f'stroke-width="{0.2 * k:.1f}"/>')
            for r in (ra, rb):
                o.append(f'<circle cx="{X(c):.1f}" cy="{Y(r):.1f}" r="{0.25 * k:.1f}" fill="#1565c0"/>')
        # SuperMini vu de dessus, USB vers le bas [brochage À VÉRIFIER sur le module]
        xa, xb, ya, yb = X(38.4), X(45.6), Y(0.4), Y(10.2)
        o.append(f'<rect x="{xa:.1f}" y="{ya:.1f}" width="{xb - xa:.1f}" height="{yb - ya:.1f}" fill="none" '
                 f'stroke="#2e7d32" stroke-width="1" stroke-dasharray="4,2"/>')
        o.append(f'<text x="{(xa + xb) / 2:.1f}" y="{yb - 0.3 * k:.1f}" font-size="{0.5 * k:.1f}" text-anchor="middle" '
                 f'fill="#2e7d32">SuperMini, USB en bas</text>')
        for c, r, lib in ((39, 6, 'TX 7'), (39, 7, 'RX 6'), (39, 8, 'IO 5'), (45, 6, '3V3'), (45, 7, 'GND'), (45, 8, '5V')):
            o.append(f'<text x="{X(c) + (0.45 if c == 39 else -0.45) * k:.1f}" y="{Y(r) + 0.15 * k:.1f}" '
                     f'font-size="{0.38 * k:.1f}" text-anchor="{"start" if c == 39 else "end"}" fill="#2e7d32">{lib}</text>')
        o.append(f'<text x="{X(19.5):.1f}" y="{Y(r1) + 0.2 * k:.1f}" font-size="{0.6 * k:.1f}" text-anchor="middle" fill="#d00">isolation</text>')
    o.append('</svg>')
    nom = 'plaquette_cuivre.svg' if miroir else 'plaquette_composants.svg'
    open(os.path.join(sortie, 'sorties', nom), 'w', encoding='utf-8').write('\n'.join(o) + '\n')


def projet(sortie):
    json.dump({'meta': {'filename': P.PROJET + '.kicad_pro', 'version': 3},
               'board': {'design_settings': {'meta': {'version': 2}, 'defaults': {}, 'rules': {
                   'min_clearance': 0.3},
               # plaquette : trous percés partout, bandes jusqu'au bord et sous les ergots des borniers
               'rule_severities': {'hole_clearance': 'ignore', 'copper_edge_clearance': 'ignore',
                                   'track_dangling': 'ignore'}}}},
              open(os.path.join(sortie, P.PROJET + '.kicad_pro'), 'w', encoding='utf-8'), indent=2)


def main():
    maitre, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    racine, uuids = schema(maitre, sortie)
    rapport, segments, pastilles = pcb(sortie, racine, uuids)
    projet(sortie)          # après SaveBoard, qui écrit un .kicad_pro par défaut
    plan(sortie, rapport, segments)
    dessin(sortie, pastilles, segments, miroir=False)
    dessin(sortie, pastilles, segments, miroir=True)
    print('généré :', os.path.join(sortie, P.PROJET + '.{kicad_pro,kicad_sch,kicad_pcb}'))


if __name__ == '__main__':
    main()
