"""Boîtier imprimable en 3D de la carte d'interface BSB (docs/claude/13_boitier_3d.md).

Deux pièces séparées par un plan de joint horizontal, à la hauteur de l'axe de l'USB-C : un FOND et un
COUVERCLE profond. Toutes les ouvertures (USB-C, câbles) sont à cheval sur le joint, moitié dans chaque
pièce : le câble est pincé entre les deux. Pas d'insert : les trous de fixation sont des avant-trous
Ø 2,5 taraudés par la vis M3 elle-même.
- carte : 4 vis M3 x 8 (ou x 6) dans les entretoises du fond ;
- couvercle : 4 vis M3 x 8 (ou x 6) dans 4 colonnes d'angle extérieures, têtes noyées dans un lamage
  qui descend jusqu'à SERRAGE mm au-dessus du joint.

Repère (mm) : X le long de la carte (0 = bord gauche, côté J1), Y en largeur (0 = bord avant, côté J3),
Z vertical (0 = dessous du fond). Carte KiCad : X = x - 100, Y = 133 - y.

Lancé par docker/cadquery/boitier.sh : python boitier.py <carte.step> <dossier_sorties>
"""
import sys
from pathlib import Path

import cadquery as cq

V = cq.Vector

# ---------------------------------------------------------------- paramètres (mm)
CARTE_X, CARTE_Y, CARTE_EP = 66.0, 33.0, 1.6          # contour Edge.Cuts du PCB
TROUS = [(3.2, 3.2), (62.787, 3.213), (3.2, 29.8), (62.787, 29.813)]   # trous M3 H1..H4
JEU_G, JEU_D, JEU_AV, JEU_AR = 4.0, 1.0, 1.0, 3.0   # carte -> paroi intérieure (arrière : débord possible de la fiche J2)
PAROI, FOND, COUV = 2.4, 2.4, 2.4                   # épaisseurs (6 lignes de 0,4 mm)
H_INT = 36.0                                        # du dessus du fond au dessous du couvercle
ENTRETOISE_H, ENTRETOISE_D = 6.0, 7.0               # sous la carte (pattes traversantes : 1,8 mm)
AVANT_TROU = 2.5                                    # avant-trou M3 taraudé par la vis (PETG ; 2,6 si le vissage force trop)
VIS_D = 3.4                                         # passage M3
VIS_CARTE, VIS_COUV = 8.0, 8.0                      # longueurs des vis M3 (M3 x 6 accepté : FILET_MIN)
FILET_MIN = 4.0                                     # filet minimal exigé avec une M3 x 6
SERRAGE = 2.0                                      # épaisseur serrée sous la tête, dans le couvercle
LAMAGE_D = 6.2                                     # logement de tête M3 (ISO 4762 Ø 5,5 ; ISO 7380 Ø 5,7)
COLONNE_D = 10.0                                    # colonnes d'angle (extérieures, centrées sur les coins)
LEVRE_H, LEVRE_EP, LEVRE_JEU = 2.0, 1.0, 0.2        # emboîtement au joint : lèvre intérieure du fond, jeu dans le couvercle
OREILLE_L, OREILLE_R, OREILLE_EP, OREILLE_TROU = 12.0, 8.0, 3.0, 4.5   # pattes murales à bout arrondi, passage M4

Z_CARTE = FOND + ENTRETOISE_H                       # dessous de la carte
Z_DESSUS_CARTE = Z_CARTE + CARTE_EP
Z_HAUT = FOND + H_INT                               # dessous du couvercle
Z_TOTAL = Z_HAUT + COUV
IX0, IX1 = -JEU_G, CARTE_X + JEU_D                  # cavité
IY0, IY1 = -JEU_AV, CARTE_Y + JEU_AR
EX0, EX1, EY0, EY1 = IX0 - PAROI, IX1 + PAROI, IY0 - PAROI, IY1 + PAROI
DECAL_COLONNE = 0.5                                  # centres des colonnes, décalés vers l extérieur des angles
COINS = [(EX0 - DECAL_COLONNE, EY0 - DECAL_COLONNE), (EX1 + DECAL_COLONNE, EY0 - DECAL_COLONNE),
         (EX0 - DECAL_COLONNE, EY1 + DECAL_COLONNE), (EX1 + DECAL_COLONNE, EY1 + DECAL_COLONNE)]

# Ouvertures, toutes centrées sur le plan de joint
USB_Y, USB_L, USB_H, USB_R = 16.47, 13.0, 9.0, 3.0  # USB-C du SuperMini, paroi droite, coins arrondis R 3
SUPERMINI_DESSOUS = Z_DESSUS_CARTE + 8.6 + 2.5      # barrette femelle 8,6 mm + entretoise des picots 2,5 mm [SUPPOSÉ]
# Carte rev A : rangées J4 / J5 en miroir du brochage réel, le SuperMini s'enfiche RETOURNÉ (composants et USB-C
# vers la carte). Mettre False pour une carte corrigée (module à l'endroit).
SUPERMINI_RETOURNE = True
USB_BAS = SUPERMINI_DESSOUS - 3.2 if SUPERMINI_RETOURNE else SUPERMINI_DESSOUS + 1.0   # dessous de la prise USB-C
USB_Z = USB_BAS + 1.6                               # axe de l'USB-C (prise de 3,2 mm de haut, circuit 1 mm)
Z_JOINT = USB_Z                                     # plan de joint fond / couvercle
CABLE_J1 = dict(paroi='gauche', pos=16.48, d=7.0)   # bus BSB (paire de fils ou câble Ø ≤ 6)
SORTIE_DHT = dict(x=37.11, y=4.37, l=9.0, h=4.0)  # câble du DHT22 : lumière oblongue dans le dessus, au-dessus de J3,
                                                   # assez large pour passer le connecteur Dupont 3 points (7,6 x 2,5)
CABLE_J2 = dict(paroi='arriere', pos=37.15, d=7.0)  # entrée 5 V externe (J2), seulement si OUVERTURE_J2
OUVERTURE_J2 = False                                # alimentation par l'USB-C par défaut
LED_D1 = dict(x=15.03, y=5.76, d=3.2)               # fenêtre au-dessus de la LED de bus D1 (guide de lumière Ø 3)


def boite(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, p, d, h):
    return cq.Solid.makeCylinder(r, h, V(*p), V(*d))


def anneau(ext, inte, z0, z1):
    """Anneau suivant la cavité ; ext et inte : décalages depuis la paroi intérieure (positif vers l'extérieur)."""
    return boite(IX0 - ext, IX1 + ext, IY0 - ext, IY1 + ext, z0, z1).cut(
        boite(IX0 - inte, IX1 + inte, IY0 - inte, IY1 + inte, z0 - 1, z1 + 1))


def ouvertures():
    """Volumes retirés des deux pièces, à cheval sur le plan de joint (lèvre comprise)."""
    usb = (cq.Workplane('YZ', origin=(IX1 - 1.5, USB_Y, Z_JOINT)).rect(USB_L, USB_H).extrude(EX1 + 0.5 - (IX1 - 1.5))
           .edges('|X').fillet(USB_R).val())
    o = [usb]
    for c in [CABLE_J1] + ([CABLE_J2] if OUVERTURE_J2 else []):
        r, long = c['d'] / 2, PAROI + 2.0
        if c['paroi'] == 'gauche':
            o.append(cyl(r, (EX0 - 0.5, c['pos'], Z_JOINT), (1, 0, 0), long))
        elif c['paroi'] == 'avant':
            o.append(cyl(r, (c['pos'], EY0 - 0.5, Z_JOINT), (0, 1, 0), long))
        else:
            o.append(cyl(r, (c['pos'], IY1 - 1.5, Z_JOINT), (0, 1, 0), long))
    return o


def oreille(cote):
    """Patte murale à bout arrondi (rayon OREILLE_R), trou de passage M4."""
    yc = (EY0 + EY1) / 2
    sens = -1 if cote == 'gauche' else 1
    x_paroi = EX0 if cote == 'gauche' else EX1
    xc = x_paroi + sens * OREILLE_L
    corps = boite(min(x_paroi, xc), max(x_paroi, xc), yc - OREILLE_R, yc + OREILLE_R, 0, OREILLE_EP)
    corps = corps.fuse(cyl(OREILLE_R, (xc, yc, 0), (0, 0, 1), OREILLE_EP))
    return corps.cut(cyl(OREILLE_TROU / 2, (xc, yc, -1), (0, 0, 1), OREILLE_EP + 2)).clean()


def fond():
    s = boite(EX0, EX1, EY0, EY1, 0, Z_JOINT).cut(boite(IX0, IX1, IY0, IY1, FOND, Z_JOINT + 1))
    s = s.fuse(anneau(0.01, -LEVRE_EP, Z_JOINT - 1, Z_JOINT + LEVRE_H))          # lèvre intérieure au-dessus du joint
    if SUPERMINI_RETOURNE:   # module abaissé : pas de lèvre contre la paroi droite (bout du SuperMini, USB-C)
        s = s.cut(boite(IX1 - LEVRE_EP - 0.5, IX1 + 0.01, IY0 - 0.01, IY1 + 0.01, Z_JOINT, Z_JOINT + LEVRE_H + 1))
    for x, y in COINS:
        s = s.fuse(cyl(COLONNE_D / 2, (x, y, 0), (0, 0, 1), Z_JOINT))
    for x, y in TROUS:
        s = s.fuse(cyl(ENTRETOISE_D / 2, (x, y, FOND - 0.01), (0, 0, 1), ENTRETOISE_H + 0.01))
        s = s.cut(cyl(AVANT_TROU / 2, (x, y, 0.6), (0, 0, 1), Z_CARTE))          # vis de la carte
    prof = VIS_COUV - SERRAGE + 2.0                                               # filet utile + 2 mm de dégagement
    for x, y in COINS:
        s = s.cut(cyl(AVANT_TROU / 2, (x, y, Z_JOINT - prof), (0, 0, 1), prof + 1))
    s = s.fuse(oreille('gauche')).fuse(oreille('droite'))
    for o in ouvertures():
        s = s.cut(o)
    return s.clean()


def couvercle():
    s = boite(EX0, EX1, EY0, EY1, Z_JOINT, Z_TOTAL).cut(boite(IX0, IX1, IY0, IY1, Z_JOINT - 1, Z_HAUT))
    for x, y in COINS:
        s = s.fuse(cyl(COLONNE_D / 2, (x, y, Z_JOINT), (0, 0, 1), Z_TOTAL - Z_JOINT))
        s = s.cut(cyl(VIS_D / 2, (x, y, Z_JOINT - 1), (0, 0, 1), Z_TOTAL - Z_JOINT + 2))
        s = s.cut(cyl(LAMAGE_D / 2, (x, y, Z_JOINT + SERRAGE), (0, 0, 1), Z_TOTAL - Z_JOINT))   # tête noyée
    # logement de la lèvre du fond (après les colonnes, qui débordent dans les angles de la cavité) :
    # paroi intérieure du couvercle reculée de LEVRE_JEU sur la hauteur de la lèvre
    s = s.cut(anneau(LEVRE_JEU, -LEVRE_EP - 0.5, Z_JOINT - 1, Z_JOINT + LEVRE_H + LEVRE_JEU))
    s = s.cut(cyl(LED_D1['d'] / 2, (LED_D1['x'], LED_D1['y'], Z_HAUT - 1), (0, 0, 1), COUV + 2))
    d = SORTIE_DHT
    s = s.cut(cq.Workplane('XY', origin=(d['x'], d['y'], Z_HAUT - 1)).slot2D(d['l'], d['h']).extrude(COUV + 2).val())
    for o in ouvertures():
        s = s.cut(o)
    return s.clean()


def fantomes():
    """Encombrements simplifiés, pour le contrôle d'interférence et l'assemblage (non imprimés)."""
    t = Z_DESSUS_CARTE
    sm_x0 = 143.6 - 100                              # SuperMini 22,5 x 18 mm, USB-C au bord droit [SUPPOSÉ]
    g = {
        'J1 embase + fiche': boite(0.47, 8.81, 133 - 121.24, 133 - 111.76, t, t + 19.0),   # fiche enfichée : ≈ 19 mm [SUPPOSÉ]
        'J2 embase + fiche': boite(132.43 - 100, 141.91 - 100, 133 - 108.37, 133 - 100.03, t, t + 19.0),
        'J3 + connecteur Dupont': boite(33.3, 40.95, 133 - 129.9, 133 - 127.36, t, t + 8.6 + 14.0),
        'câble du DHT22 (Ø 3,5)': cyl(1.75, (SORTIE_DHT['x'], SORTIE_DHT['y'], t + 8.6 + 14.0), (0, 0, 1), Z_TOTAL - t + 10),
        'J4, J5 barrettes': boite(44.72, 65.04, 133 - 125.42, 133 - 107.63, t, t + 8.6),
        'SuperMini': boite(sm_x0, sm_x0 + 22.5, 133 - 125.5, 133 - 107.5, SUPERMINI_DESSOUS, SUPERMINI_DESSOUS + 1.0),
        'USB-C': boite(66.6 - 7.4, 66.6, USB_Y - 4.5, USB_Y + 4.5, USB_BAS, USB_BAS + 3.2),
        'U1, U2': boite(120.41 - 100, 128.30 - 100, 133 - 128.23, 133 - 104.73, t, t + 3.8),
        'pattes sous la carte': boite(7.0, 59.0, 0.5, 32.5, Z_CARTE - 1.9, Z_CARTE),   # hors entretoises
    }
    for k, (x, y) in enumerate(TROUS):                # têtes des vis de la carte (M3 tête cylindrique Ø 5,5 x 3)
        g[f'tête de vis H{k + 1}'] = cyl(2.75, (x, y, t), (0, 0, 1), 3.0)
    return g


def apercu(pieces, chemin):
    """Rendu ombré simple : toutes les facettes dans une seule collection, triées par profondeur."""
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    coupe_av = boite(EX0 - 30, EX1 + 30, EY0 - 30, USB_Y, -5, 100)       # moitié avant retirée (coupe en Y = axe USB/J1)
    vues = (('Assemblage, couvercle soulevé de 25 mm', 25, -60, 25, False),
            ('Coupe au niveau de l USB-C et de J1', 12, -80, 0, True),
            ('Fond, carte et encombrements, vue de dessus', 89, -90, None, False))
    fig = plt.figure(figsize=(16, 6), dpi=110)
    lumiere = np.array([0.3, -0.5, 0.8]); lumiere /= np.linalg.norm(lumiere)
    for k, (titre, elev, azim, eclate, coupe) in enumerate(vues):
        ax = fig.add_subplot(1, 3, k + 1, projection='3d')
        polys, couleurs = [], []
        for nom, solide, couleur in pieces:
            if nom == 'couvercle' and eclate is None:
                continue
            if coupe:
                solide = solide.cut(coupe_av)
                if solide.Volume() < 1e-6:
                    continue
            dz = eclate if (nom == 'couvercle' and eclate) else 0
            sommets, triangles = solide.tessellate(0.2, 0.4)
            pts = np.array([(v.x, v.y, v.z + dz) for v in sommets])
            for tri in triangles:
                t = pts[list(tri)]
                n = np.cross(t[1] - t[0], t[2] - t[0]); nn = np.linalg.norm(n)
                if nn < 1e-12:
                    continue
                e = 0.35 + 0.65 * abs(np.dot(n / nn, lumiere))
                polys.append(t); couleurs.append(tuple(min(1, c * e) for c in couleur))
        ax.add_collection3d(Poly3DCollection(polys, facecolors=couleurs, edgecolors='none'))
        ax.set_xlim(EX0 - 22, EX1 + 22); ax.set_ylim(EY0 - 22, EY1 + 22); ax.set_zlim(0, 70 if eclate else 45)
        ax.set_box_aspect((EX1 - EX0 + 44, EY1 - EY0 + 44, 70 if eclate else 45))
        ax.view_init(elev=elev, azim=azim); ax.set_title(titre); ax.set_axis_off()
    fig.tight_layout(); fig.savefig(chemin); plt.close(fig)


def main():
    carte_step, sortie = Path(sys.argv[1]), Path(sys.argv[2])
    sortie.mkdir(parents=True, exist_ok=True)
    f, c = fond(), couvercle()
    carte = cq.importers.importStep(str(carte_step)).val().translate(V(-100, 133, Z_CARTE))

    # contrôles : aucune interférence entre pièces, carte et encombrements
    ok = True
    for nom, g in list(fantomes().items()) + [('carte', carte)]:
        for piece, solide in (('fond', f), ('couvercle', c)):
            v = g.intersect(solide).Volume()        # appui de la carte sur les entretoises : contact, volume nul
            if v > 1e-3:
                print(f'INTERFÉRENCE {nom} / {piece} : {v:.2f} mm3'); ok = False
    jeu = f.intersect(c).Volume()
    print(f'fond / couvercle : {jeu:.3f} mm3 en commun')
    ok = ok and jeu < 1e-3
    filet_couv = VIS_COUV - SERRAGE
    print('dimensions extérieures (hors pattes et colonnes) : %.1f x %.1f x %.1f mm' % (EX1 - EX0, EY1 - EY0, Z_TOTAL))
    print('plan de joint à Z = %.1f mm : fond %.1f mm, couvercle %.1f mm de haut' % (Z_JOINT, Z_JOINT, Z_TOTAL - Z_JOINT))
    print('vis de la carte M3 x %.0f : %.1f mm de filet ; vis du couvercle M3 x %.0f : %.1f mm de filet' % (
        VIS_CARTE, VIS_CARTE - CARTE_EP, VIS_COUV, filet_couv))
    print('avec des M3 x 6 : %.1f mm de filet pour la carte, %.1f mm pour le couvercle' % (6 - CARTE_EP, 6 - SERRAGE))
    ok = ok and min(6 - CARTE_EP, 6 - SERRAGE) >= FILET_MIN and VIS_CARTE - CARTE_EP <= Z_CARTE - 0.6

    for nom, solide in (('boitier_fond', f), ('boitier_couvercle', c)):
        cq.exporters.export(cq.Workplane().add(solide), str(sortie / f'{nom}.step'))
        cq.exporters.export(cq.Workplane().add(solide), str(sortie / f'{nom}.stl'), tolerance=0.02, angularTolerance=0.1)
    a = cq.Assembly(name='boitier_bsb')
    a.add(f, name='fond', color=cq.Color(0.85, 0.85, 0.82))
    a.add(c, name='couvercle', color=cq.Color(0.55, 0.65, 0.75, 0.6))
    a.add(carte, name='carte', color=cq.Color(0.1, 0.45, 0.2))
    for nom, g in fantomes().items():
        a.add(g, name=nom, color=cq.Color(0.9, 0.5, 0.1, 0.5))
    a.export(str(sortie / 'boitier_assemblage.step'))
    pieces = [('fond', f, (0.85, 0.85, 0.8)), ('couvercle', c, (0.55, 0.68, 0.85)), ('carte', carte, (0.15, 0.55, 0.25))]
    pieces += [(n, g, (0.95, 0.6, 0.15)) for n, g in fantomes().items()]
    apercu(pieces, sortie / 'apercu.png')
    print('CONTRÔLES OK' if ok else 'CONTRÔLES EN ÉCHEC')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
