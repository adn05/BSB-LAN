"""Lecture et écriture minimales des S-expressions KiCad."""
import re

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


class Sym(str):
    """Atome non quoté (mot-clé ou nombre)."""


def parse(texte):
    pile, courant = [], []
    for m in _TOKEN.finditer(texte):
        t = m.group(0)
        if t == '(':
            pile.append(courant)
            courant = []
        elif t == ')':
            fini = courant
            courant = pile.pop()
            courant.append(fini)
        elif t.startswith('"'):
            courant.append(t[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            courant.append(Sym(t))
    return courant[0]


def _atome(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, (int, float)):
        return f'{a:g}' if isinstance(a, float) else str(a)
    return '"' + str(a).replace('\\', '\\\\').replace('"', '\\"') + '"'


def dump(e, niveau=0):
    if not isinstance(e, list):
        return _atome(e)
    simples = all(not isinstance(x, list) for x in e)
    if simples:
        return '(' + ' '.join(_atome(x) for x in e) + ')'
    tab = '\t' * (niveau + 1)
    morceaux = [_atome(x) if not isinstance(x, list) else '\n' + tab + dump(x, niveau + 1) for x in e]
    texte = '('
    for i, mcx in enumerate(morceaux):
        texte += ('' if i == 0 or mcx.startswith('\n') else ' ') + mcx
    return texte + '\n' + '\t' * niveau + ')'


def trouver(e, cle):
    return [x for x in e if isinstance(x, list) and x and x[0] == cle]


def un(e, cle):
    r = trouver(e, cle)
    return r[0] if r else None
