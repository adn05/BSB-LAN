#!/usr/bin/env python3
"""Échange Specctra entre KiCad et Freerouting (docs/claude/09 §9).

    python3 specctra.py export <carte.kicad_pcb> <carte.dsn>   # règles de routage puis export DSN
    python3 specctra.py import <carte.kicad_pcb> <carte.ses>   # import du routage, plan de masse, sauvegarde
"""
import sys

import pcbnew

import carte
from sexpr import dump, parse, un

mm = pcbnew.FromMM
FIN = 0.25                     # mm : signaux et +3V3 (quelques mA côté carte, le module a son propre LDO)
GARDE = 0.25                   # mm : écart cuivre-cuivre
# classe : (largeur mm, nets). 0,3 mm en cuivre 35 µm : ~1 A pour +10 °C (IPC-2221, couche externe),
# pour ~0,5 A crête du SuperMini en émission WiFi ; 0,4 mm pour le bus (robustesse face aux surtensions).
CLASSES = {
    'Bus': (0.4, {'CL_N_IN', 'BUS_P', 'BUS_N'}),
    'Alim': (0.3, {'5V_IN', '+5V', 'GND'}),
}


def regles(board):
    ds = board.GetDesignSettings()
    ns = ds.m_NetSettings
    defaut = ns.GetDefaultNetclass()
    defaut.SetTrackWidth(mm(FIN))
    defaut.SetClearance(mm(GARDE))
    defaut.SetViaDiameter(mm(0.8))
    defaut.SetViaDrill(mm(0.4))
    for nom, (largeur, nets) in CLASSES.items():
        nc = pcbnew.NETCLASS(nom)
        nc.SetTrackWidth(mm(largeur))
        nc.SetClearance(mm(GARDE))
        nc.SetViaDiameter(mm(0.8))
        nc.SetViaDrill(mm(0.4))
        ns.SetNetclass(nom, nc)
        for n in nets:
            ns.SetNetclassPatternAssignment('/' + n, nom)
    board.SynchronizeNetsAndNetClasses(True)


def plan_masse(board):
    """Plan GND en face arrière, côté ESP32 seulement (à droite de la bande d'isolation), hors zone antenne."""
    gnd = board.FindNet('/GND')
    x0, y0, x1, y1 = carte.CARTE
    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNet(gnd)
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    o = z.Outline()
    o.NewOutline()
    for px, py in [(carte.ISOLATION[2] + 0.5, y0 + 0.5), (x1 - 0.5, y0 + 0.5), (x1 - 0.5, y1 - 0.5), (carte.ISOLATION[2] + 0.5, y1 - 0.5)]:
        o.Append(mm(px), mm(py))
    board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def a_nettoyer(board):
    """UUID des tronçons à supprimer après Freerouting (avertissements track_dangling de KiCad) :
    segments en double (même segment parcouru dans les deux sens), puis, itérativement, segments dont une
    extrémité ne touche ni l'extrémité d'une autre piste de la même couche, ni un via, ni une pastille du même net,
    et vias reliés à moins de deux pistes. Calcul sur une copie : l'API Python plante si l'on retire en boucle.
    """
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    items = []
    for t in board.GetTracks():
        via = t.GetClass() == 'PCB_VIA'
        a, b = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
        items.append(dict(uuid=t.m_Uuid.AsString(), via=via, net=t.GetNetCode(), couche=None if via else t.GetLayer(),
                          a=a, b=b, w=t.GetWidth(),
                          sur_pad=[any(p.GetNetCode() == t.GetNetCode() and (via or p.IsOnLayer(t.GetLayer())) and
                                       p.HitTest(pcbnew.VECTOR2I(*pt), 0) for p in pads) for pt in (a, b)]))
    morts, vus = set(), set()
    for it in items:
        if it['via']:
            continue
        cle = (it['net'], it['couche'], min(it['a'], it['b']), max(it['a'], it['b']))
        if cle in vus or it['a'] == it['b']:
            morts.add(it['uuid'])
        vus.add(cle)

    def proche(v, pt):
        return (v['a'][0] - pt[0]) ** 2 + (v['a'][1] - pt[1]) ** 2 <= (v['w'] / 2) ** 2

    while True:
        vivants = [it for it in items if it['uuid'] not in morts]
        nouveaux = set()
        for it in vivants:
            if it['via']:
                n = sum(1 for o in vivants if not o['via'] and o['net'] == it['net'] and it['a'] in (o['a'], o['b']))
                if n < 2 and not it['sur_pad'][0]:
                    nouveaux.add(it['uuid'])
                continue
            for k, pt in enumerate((it['a'], it['b'])):
                relie = it['sur_pad'][k] or any(
                    o is not it and o['net'] == it['net'] and
                    (o['via'] and proche(o, pt) or not o['via'] and o['couche'] == it['couche'] and pt in (o['a'], o['b']))
                    for o in vivants)
                if not relie:
                    nouveaux.add(it['uuid'])
                    break
        if not nouveaux:
            return morts
        morts |= nouveaux


def supprimer(chemin, uuids):
    """Retire du fichier .kicad_pcb les segments et vias dont l'UUID est donné."""
    doc = parse(open(chemin, encoding='utf-8').read())
    garde = [x for x in doc if not (isinstance(x, list) and x and x[0] in ('segment', 'via')
                                    and un(x, 'uuid') and un(x, 'uuid')[1] in uuids)]
    open(chemin, 'w', encoding='utf-8').write(dump(garde) + '\n')
    return len(doc) - len(garde)


def main():
    mode, pcb_path, fichier = sys.argv[1:4]
    board = pcbnew.LoadBoard(pcb_path)
    if mode == 'export':
        regles(board)
        pcbnew.SaveBoard(pcb_path, board)
        assert pcbnew.ExportSpecctraDSN(board, fichier), 'export DSN impossible'
    else:
        assert pcbnew.ImportSpecctraSES(board, fichier), 'import SES impossible'
        pcbnew.SaveBoard(pcb_path, board)
        print('tronçons en double ou en impasse supprimés :', supprimer(pcb_path, a_nettoyer(pcbnew.LoadBoard(pcb_path))))
        board = pcbnew.LoadBoard(pcb_path)
        plan_masse(board)
        pcbnew.SaveBoard(pcb_path, board)
    print(mode, 'ok :', fichier)


if __name__ == '__main__':
    main()
