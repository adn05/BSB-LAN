"""Extraction des symboles des bibliothèques KiCad (aplatissement des symboles dérivés)."""
import copy
import os

from sexpr import Sym, parse, trouver, un

DOSSIER_SYMBOLES = os.environ.get('KICAD_SYMBOL_DIR', '/usr/share/kicad/symbols')
_cache = {}


def _bibli(nom):
    if nom not in _cache:
        texte = open(os.path.join(DOSSIER_SYMBOLES, nom + '.kicad_sym'), encoding='utf-8').read()
        _cache[nom] = {s[1]: s for s in trouver(parse(texte), 'symbol')}
    return _cache[nom]


def symbole(lib_id):
    """Retourne la définition aplatie, renommée « Lib:Nom », prête pour lib_symbols."""
    lib, nom = lib_id.split(':')
    table = _bibli(lib)
    s = copy.deepcopy(table[nom])
    parent = un(s, 'extends')
    if parent:
        p = copy.deepcopy(table[parent[1]])
        props = {x[1]: x for x in trouver(s, 'property')}
        corps = []
        for x in p[2:]:
            if isinstance(x, list) and x[0] == 'property':
                corps.append(props.pop(x[1], x))
            elif isinstance(x, list) and x[0] == 'symbol':
                x[1] = x[1].replace(parent[1], nom, 1)
                corps.append(x)
            else:
                corps.append(x)
        corps += list(props.values())
        s = [Sym('symbol'), nom] + corps
    s[1] = lib_id
    return s


def broches(lib_id):
    """{numéro: (x, y, angle, nom, type)} en coordonnées de bibliothèque (y vers le haut)."""
    res = {}

    def visite(e):
        for x in e:
            if isinstance(x, list):
                if x and x[0] == 'pin':
                    at = un(x, 'at')
                    num = un(x, 'number')[1]
                    nom = un(x, 'name')[1]
                    res[num] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, nom, str(x[1]))
                else:
                    visite(x)
    visite(symbole(lib_id))
    return res
