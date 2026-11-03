"""Boîtier imprimable en 3D de la carte d'interface BSB (docs/claude/13_boitier_3d.md).

Deux pièces : un FOND qui porte la carte sur 4 entretoises (inserts M3 à chaud) et un COUVERCLE dont
4 colonnes viennent plaquer la carte. Une vis M3 x 40 par coin traverse couvercle, colonne et carte,
et se visse dans l'insert de l'entretoise : 4 vis tiennent à la fois la carte et le couvercle.

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
JEU_G, JEU_D, JEU_AV, JEU_AR = 10.0, 1.0, 1.0, 3.0  # carte -> paroi intérieure (gauche : écrou du presse-étoupe de J1)
PAROI, FOND, COUV = 2.4, 2.4, 2.4                   # épaisseurs (6 lignes de 0,4 mm)
H_INT = 36.0                                        # du dessus du fond au dessous du couvercle
ENTRETOISE_H, ENTRETOISE_D = 6.0, 7.0               # sous la carte (pattes traversantes : 1,8 mm)
INSERT_D, INSERT_P = 4.0, 6.0                       # insert à chaud M3 x 5,7 (type Ruthex) : Ø du trou, profondeur
VIS_D = 3.4                                         # passage M3
COLONNE_D = 6.5                                     # colonnes du couvercle, en appui autour des trous
LEVRE_H, LEVRE_EP, LEVRE_JEU = 3.0, 1.2, 0.25       # lèvre de centrage du couvercle
OREILLE_L, OREILLE_EP, OREILLE_TROU = 10.0, 3.0, 4.5   # pattes de fixation murale (vis Ø 4)

Z_CARTE = FOND + ENTRETOISE_H                       # dessous de la carte
Z_DESSUS_CARTE = Z_CARTE + CARTE_EP
Z_HAUT = FOND + H_INT                               # dessus des parois = dessous du couvercle
IX0, IX1 = -JEU_G, CARTE_X + JEU_D                  # cavité
IY0, IY1 = -JEU_AV, CARTE_Y + JEU_AR
EX0, EX1, EY0, EY1 = IX0 - PAROI, IX1 + PAROI, IY0 - PAROI, IY1 + PAROI

# Ouvertures (positions déduites du PCB : voir la doc 13 §2)
USB_Y, USB_L = 16.47, 13.0                          # USB-C du SuperMini, paroi droite
SUPERMINI_DESSOUS = Z_DESSUS_CARTE + 8.6 + 2.5      # barrette femelle 8,6 mm + entretoise des picots 2,5 mm [SUPPOSÉ]
USB_Z = SUPERMINI_DESSOUS + 1.0 + 1.6               # axe de l'USB-C (circuit 1 mm, prise de 3,2 mm de haut)
USB_H = 9.0
PE_J1 = dict(y=16.48, z=FOND + 20.0, d=12.2)        # presse-étoupe M12 x 1,5 du bus (J1), paroi gauche
PE_DHT = dict(x=52.0, z=FOND + 24.0, d=8.2)         # presse-étoupe M8 x 1,25 du DHT22, paroi avant
PE_J2 = dict(x=50.0, z=FOND + 24.0, d=8.2, voile=0.6)  # M8 de l'entrée 5 V (J2), paroi arrière, opercule à percer
LED_D1 = dict(x=15.03, y=5.76, d=3.2)               # fenêtre au-dessus de la LED de bus D1 (guide de lumière Ø 3)


def boite(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, p, d, h):
    return cq.Solid.makeCylinder(r, h, V(*p), V(*d))


def fond():
    s = boite(EX0, EX1, EY0, EY1, 0, Z_HAUT).cut(boite(IX0, IX1, IY0, IY1, FOND, Z_HAUT + 1))
    for x, y in TROUS:
        s = s.fuse(cyl(ENTRETOISE_D / 2, (x, y, FOND - 0.01), (0, 0, 1), ENTRETOISE_H + 0.01))
        s = s.cut(cyl(INSERT_D / 2, (x, y, Z_CARTE - INSERT_P), (0, 0, 1), INSERT_P + 0.1))
        s = s.cut(cyl(VIS_D / 2 - 0.2, (x, y, 0.6), (0, 0, 1), Z_CARTE))   # logement de la pointe de vis
    # pattes de fixation murale, à gauche et à droite
    for xa, xb, xt in ((EX0 - OREILLE_L, EX0 + 0.01, EX0 - OREILLE_L / 2), (EX1 - 0.01, EX1 + OREILLE_L, EX1 + OREILLE_L / 2)):
        yc = (EY0 + EY1) / 2
        s = s.fuse(boite(xa, xb, yc - 8, yc + 8, 0, OREILLE_EP))
        s = s.cut(cyl(OREILLE_TROU / 2, (xt, yc, -1), (0, 0, 1), OREILLE_EP + 2))
    # ouvertures
    s = s.cut(boite(IX1 - 0.5, EX1 + 0.5, USB_Y - USB_L / 2, USB_Y + USB_L / 2, USB_Z - USB_H / 2, USB_Z + USB_H / 2))
    s = s.cut(cyl(PE_J1['d'] / 2, (EX0 - 0.5, PE_J1['y'], PE_J1['z']), (1, 0, 0), PAROI + 1))
    s = s.cut(cyl(PE_DHT['d'] / 2, (PE_DHT['x'], EY0 - 0.5, PE_DHT['z']), (0, 1, 0), PAROI + 1))
    # opercule : trou M8 fermé par un voile de 0,6 mm au milieu de la paroi, à percer si J2 sert
    s = s.cut(cyl(PE_J2['d'] / 2, (PE_J2['x'], IY1 - 0.5, PE_J2['z']), (0, 1, 0), 0.5 + (PAROI - PE_J2['voile']) / 2))
    s = s.cut(cyl(PE_J2['d'] / 2, (PE_J2['x'], IY1 + (PAROI + PE_J2['voile']) / 2, PE_J2['z']), (0, 1, 0), PAROI))
    return s


def couvercle():
    s = boite(EX0, EX1, EY0, EY1, Z_HAUT, Z_HAUT + COUV)
    j = LEVRE_JEU
    levre = boite(IX0 + j, IX1 - j, IY0 + j, IY1 - j, Z_HAUT - LEVRE_H, Z_HAUT + 0.01).cut(
        boite(IX0 + j + LEVRE_EP, IX1 - j - LEVRE_EP, IY0 + j + LEVRE_EP, IY1 - j - LEVRE_EP, Z_HAUT - LEVRE_H - 1, Z_HAUT + 1))
    s = s.fuse(levre)
    for x, y in TROUS:
        s = s.fuse(cyl(COLONNE_D / 2, (x, y, Z_DESSUS_CARTE), (0, 0, 1), Z_HAUT - Z_DESSUS_CARTE + 0.01))
        s = s.cut(cyl(VIS_D / 2, (x, y, Z_DESSUS_CARTE - 1), (0, 0, 1), Z_HAUT + COUV))
    s = s.cut(cyl(LED_D1['d'] / 2, (LED_D1['x'], LED_D1['y'], Z_HAUT - 1), (0, 0, 1), COUV + 2))
    return s


def fantomes():
    """Encombrements simplifiés, pour le contrôle d'interférence et l'assemblage (non imprimés)."""
    t = Z_DESSUS_CARTE
    sm_x0 = 143.6 - 100                              # SuperMini 22,5 x 18 mm, USB-C au bord droit [SUPPOSÉ]
    return {
        'J1 embase + fiche': boite(0.47, 8.81, 133 - 121.24, 133 - 111.76, t, t + 19.0),   # fiche enfichée : ≈ 19 mm [SUPPOSÉ]
        'J2 embase + fiche': boite(132.43 - 100, 141.91 - 100, 133 - 108.37, 133 - 100.03, t, t + 19.0),
        'J3 + connecteur Dupont': boite(33.3, 40.95, 133 - 129.9, 133 - 127.36, t, t + 8.6 + 14.0),
        'J4, J5 barrettes': boite(44.72, 65.04, 133 - 125.42, 133 - 107.63, t, t + 8.6),
        'SuperMini': boite(sm_x0, sm_x0 + 22.5, 133 - 125.5, 133 - 107.5, SUPERMINI_DESSOUS, SUPERMINI_DESSOUS + 1.0),
        'USB-C': boite(66.6 - 7.4, 66.6, USB_Y - 4.5, USB_Y + 4.5, SUPERMINI_DESSOUS + 1.0, SUPERMINI_DESSOUS + 4.2),
        'U1, U2': boite(120.41 - 100, 128.30 - 100, 133 - 128.23, 133 - 104.73, t, t + 3.8),
        'pattes sous la carte': boite(7.0, 59.0, 0.5, 32.5, Z_CARTE - 1.9, Z_CARTE),   # hors entretoises
    }


def apercu(pieces, chemin):
    """Rendu ombré simple : toutes les facettes dans une seule collection, triées par profondeur."""
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    coupe_av = boite(EX0 - 30, EX1 + 30, EY0 - 30, USB_Y, -5, 100)       # moitié avant retirée (coupe en Y = axe USB/J1)
    vues = (('Assemblage, couvercle soulevé de 30 mm', 25, -60, 30, False),
            ('Coupe au niveau de l USB-C et de J1', 18, -75, 0, True),
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
        ax.set_xlim(EX0 - 12, EX1 + 12); ax.set_ylim(EY0 - 22, EY1 + 22); ax.set_zlim(0, 75 if eclate else 50)
        ax.set_box_aspect((EX1 - EX0 + 24, EY1 - EY0 + 44, 75 if eclate else 50))
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
            v = g.intersect(solide).Volume()        # appuis de la carte sur entretoises et colonnes : contact, volume nul
            if v > 1e-3:
                print(f'INTERFÉRENCE {nom} / {piece} : {v:.2f} mm3'); ok = False
    jeu = f.intersect(c).Volume()
    print(f'fond / couvercle : {jeu:.3f} mm3 en commun')
    ok = ok and jeu < 1e-3
    print('dimensions extérieures (hors pattes) : %.1f x %.1f x %.1f mm' % (EX1 - EX0, EY1 - EY0, Z_HAUT + COUV))
    print('vis : M3 x %.0f (tête sur le couvercle, %.1f mm dans l insert)' % (40, 40 - (Z_HAUT + COUV - Z_CARTE)))

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
