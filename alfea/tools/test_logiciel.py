#!/usr/bin/env python3
"""Tests logiciels du firmware sur banc (pont + simulateur), avant la GATE 3 (docs/claude/08 §6, T1 et T2).

    python -I alfea/tools/test_logiciel.py lecture  --ip 192.168.30.202 --sim alfea/build/sim.log --panne alfea/build/panne.txt
    python -I alfea/tools/test_logiciel.py ecriture --ip 192.168.30.202 --sim alfea/build/sim.log

Prérequis : bsb_sim.py --pont --panne <fichier> lancé, sa sortie dans --sim ; firmware alfea (lecture) ou
alfea-ecriture (écriture) sur le SuperMini ; identifiants web et MQTT lus dans alfea/config/alfea_secrets.h
(jamais affichés).

lecture  : valeurs lues = scénario du simulateur (HTTP /JQ et MQTT) ; toute tentative d'écriture (/S, /I, /JS,
           MQTT set et inf) refusée sans aucune trame SET ni INF sur le bus ; routes /Y, /YR, /JY, /G inopérantes ;
           CRC faux et silence du bus signalés en erreur, puis reprise, sans redémarrage du SuperMini.
ecriture : mode d'écriture 0 = refus ; mode 1 = écriture des lignes de la liste blanche (SET émis, relecture),
           refus hors liste blanche ; le mode est remis à 0 à la fin.
Code de sortie 0 si tous les contrôles passent.
"""
import argparse
import base64
import json
import os
import re
import socket
import struct
import sys
import time
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, '..', '..'))
sys.path.insert(0, ICI)
import verif_discovery as vd  # noqa: E402
from analyse_liste import lire_liste  # noqa: E402

SECRETS = os.path.join(DEPOT, 'alfea', 'config', 'alfea_secrets.h')
CF_WRITEMODE = 33        # rang de CF_WRITEMODE dans BSB_LAN/BSB_LAN_EEPROMconfig.h (enum, à partir de 0)
resultats = []


def controle(nom, ok, detail=''):
    resultats.append(ok)
    print(f'{"OK   " if ok else "ÉCHEC"} {nom}' + (f' : {detail}' if detail else ''), flush=True)
    return ok


# ----------------------------------------------------------------------------- accès au SuperMini
class Cible:
    def __init__(self, ip):
        texte = open(SECRETS, encoding='utf-8').read()
        up = re.search(r'#define\s+ALFEA_USER_PASS\s+"([^"]*)"', texte).group(1)
        self.entete = {'Authorization': 'Basic ' + base64.b64encode(up.encode()).decode()}
        self.base = f'http://{ip}'

    def http(self, chemin, donnees=None, delai=60):
        entete = dict(self.entete, **({'Content-Type': 'application/json'} if donnees else {}))
        req = urllib.request.Request(self.base + chemin, headers=entete,
                                     data=json.dumps(donnees).encode() if donnees is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=delai) as r:
                return r.status, r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            return e.code, ''

    def jq(self, lignes):
        _, corps = self.http('/JQ=' + ','.join(f'{x:g}' for x in lignes), delai=180)
        return json.loads(corps[corps.index('{'):])

    def demarrages(self):
        """Durée de fonctionnement (s) depuis /JI, pour détecter un redémarrage."""
        _, corps = self.http('/JI')
        m = re.search(r'"uptime"\s*:\s*(\d+)', corps)
        return int(m.group(1)) if m else None


class Mqtt:
    def __init__(self):
        self.hote, self.port, self.util, self.mdp = vd.lire_secrets(SECRETS)

    def _session(self, ident):
        s = socket.create_connection((self.hote, self.port), timeout=10)
        corps = vd.chaine('MQTT') + bytes([4, 0xC2]) + struct.pack('>H', 30) + vd.chaine(ident)
        corps += vd.chaine(self.util) + vd.chaine(self.mdp)
        s.sendall(b'\x10' + vd.longueur(len(corps)) + corps)
        next(vd.paquets(s))
        return s

    def lire(self, motif, duree=5):
        s = self._session('test-logiciel-lecture')
        corps = struct.pack('>H', 1) + vd.chaine(motif) + b'\x00'
        s.sendall(b'\x82' + vd.longueur(len(corps)) + corps)
        msgs, fin = {}, time.time() + duree
        s.settimeout(1)
        while time.time() < fin:
            for entete, c in vd.paquets(s):
                if entete >> 4 == 3:
                    n = struct.unpack('>H', c[:2])[0]
                    msgs[c[2:2 + n].decode()] = c[2 + n + (2 if (entete >> 1) & 3 else 0):].decode('utf-8', 'replace')
        s.close()
        return msgs

    def publier(self, sujet, charge):
        s = self._session('test-logiciel-ecriture')
        corps = vd.chaine(sujet) + charge.encode()
        s.sendall(b'\x30' + vd.longueur(len(corps)) + corps)
        time.sleep(0.5)
        s.sendall(b'\xe0\x00')
        s.close()


# ----------------------------------------------------------------------------- journal du simulateur
class Bus:
    """Trames vues par le simulateur (lignes « <- » de sa sortie) depuis le dernier repère."""
    def __init__(self, chemin):
        self.chemin, self.pos = chemin, 0

    def repere(self):
        self.pos = os.path.getsize(self.chemin)

    def depuis(self):
        with open(self.chemin, encoding='utf-8', errors='replace') as f:
            f.seek(self.pos)
            texte = f.read()
        trames = [bytes.fromhex(l[3:]) for l in texte.splitlines() if l.startswith('<- ')]
        return trames, texte

    def ecritures(self):
        """Trames SET (0x03) ou INF (0x02) émises par BSB-LAN, et lignes « SET reçu »."""
        trames, texte = self.depuis()
        return [t for t in trames if t[4] in (0x02, 0x03)], [l for l in texte.splitlines() if l.startswith('SET reçu')]


# ----------------------------------------------------------------------------- comparaison des valeurs
def conforme(attendu, obtenu):
    v = obtenu.get('value', '')
    if re.fullmatch(r'(\d\d:\d\d-\d\d:\d\d ?)+', attendu.strip()):
        return re.findall(r'\d\d:\d\d-\d\d:\d\d', v) == attendu.split()
    try:
        return abs(float(attendu) - float(v)) <= 0.051
    except ValueError:
        return attendu == v


def test_valeurs(cible, mqtt, scenario):
    print('\n== Valeurs lues (HTTP /JQ) contre le scénario ==')
    lignes = sorted({e['line'] for e in lire_liste(os.path.join(DEPOT, 'alfea', 'params', 'BSB_LAN_custom_defs_ha.h'))})
    valeurs = {float(k): v for k, v in scenario['valeurs'].items()}
    lu = {}
    for i in range(0, len(lignes), 12):                    # par paquets : temps de réponse du bus à 4800 bauds
        lu.update({float(k): v for k, v in cible.jq(lignes[i:i + 12]).items()})
    fausses = [f'{l:g} attendu {valeurs[l]!r} lu {lu.get(l, {}).get("value")!r}'
               for l in lignes if l in valeurs and not conforme(valeurs[l], lu.get(l, {}))]
    controle(f'{sum(1 for l in lignes if l in valeurs)} lignes simulées lues et justes', not fausses, '; '.join(fausses))
    hors = [f'{l:g}' for l in lignes if l not in valeurs]
    print(f'      lignes de la liste non simulées ({len(hors)}) : {" ".join(hors)}')
    sans_err = [f'{l:g}' for l in lignes if l not in valeurs and lu.get(l, {}).get('error', 1) == 0]
    print(f'      dont lues sans erreur (valeur par défaut du simulateur) : {" ".join(sans_err) or "aucune"}')

    print('\n== Valeurs publiées en MQTT ==')
    msgs = mqtt.lire('BSB-LAN/0/+/+/status', 6)
    pub = {float(t.split('/')[3]): c for t, c in msgs.items()}
    fausses, vues = [], 0
    for l, v in valeurs.items():
        if l in pub:
            vues += 1
            if not conforme(v, {'value': pub[l].split(' - ')[0]}):
                fausses.append(f'{l:g} attendu {v!r} publié {pub[l]!r}')
    controle(f'{vues} valeurs publiées (retain) conformes au scénario', vues > 0 and not fausses, '; '.join(fausses))


def tentatives_ecriture(cible, mqtt, decouverte):
    """Toutes les voies d'écriture, sur une ligne de la liste blanche (710) et une ligne hors liste (6220)."""
    cat = {float(d['unique_id'].split('-')[0]): d['~'] for d in decouverte}
    essais = [('GET /S710=21.5', lambda: cible.http('/S710=21.5')),
              ('GET /I710=21.5 (INF)', lambda: cible.http('/I710=21.5')),
              ('GET /S501=05:30-22:00', lambda: cible.http('/S501=05:30-22:00')),
              ('GET /S700=3', lambda: cible.http('/S700=3')),
              ('POST /JS 710', lambda: cible.http('/JS', {'Parameter': '710', 'Value': '21.5', 'Type': '1'})),
              ('GET /S6220=1 (hors liste blanche)', lambda: cible.http('/S6220=1')),
              ('MQTT 710/set', lambda: mqtt.publier(cat[710.0] + '/set', '21.5')),
              ('MQTT 710/inf', lambda: mqtt.publier(cat[710.0] + '/inf', '21.5')),
              ('MQTT 700/set', lambda: mqtt.publier(cat[700.0] + '/set', '3'))]
    for nom, f in essais:
        f()
    time.sleep(3)


def test_lecture_seule(cible, mqtt, bus, decouverte):
    print('\n== Refus des écritures (firmware en lecture seule) ==')
    bus.repere()
    tentatives_ecriture(cible, mqtt, decouverte)
    trames, sets = bus.ecritures()
    controle('aucune trame SET ni INF émise sur le bus (9 tentatives : /S, /I, /JS, MQTT set et inf)', not trames and not sets,
             '; '.join(t.hex(' ') for t in trames))
    lu = cible.jq([710, 700, 501])
    controle('valeurs inchangées après les tentatives (710 = 20.5, 700 = 1, 501 = 06:00-22:00)',
             conforme('20.5', lu['710']) and conforme('1', lu['700']) and conforme('06:00-22:00', lu['501']))


def test_routes(cible, bus):
    print('\n== Routes retirées (NO_RAW_TELEGRAMS, NO_GPIO_URL) ==')
    bus.repere()
    essais = {'/Y06,0x053D0064': None, '/YR': None, '/G5=1': 'GPIO', '/G05': 'GPIO'}
    for chemin, mot in essais.items():
        code, corps = cible.http(chemin)
        texte = ' '.join(re.sub(r'<[^>]+>', ' ', corps).split())
        execute = (mot and re.search(r'GPIO\s*\d+\s*[:=]', texte)) or 'HEIZ->' in texte or 'Raw' in texte
        controle(f'{chemin} inopérante', not execute, f'HTTP {code}')
    code, corps = cible.http('/JY', {'Parameter': '0x053D0064'})
    controle('/JY inopérante', '"error"' not in corps and 'payload' not in corps.lower(), f'HTTP {code}')
    time.sleep(2)
    trames, _ = bus.depuis()
    # Une URL non reconnue retombe sur la lecture du paramètre 0 (« Y06… », « G5 » valent 0) : QUR date/heure,
    # inoffensif. Toute autre trame (QINF 0x053D0064 demandé par /Y, SET, INF) serait une trame brute.
    autres = [t for t in trames if not (t[4] == 0x06 and t[5:9] == bytes.fromhex('3d05000b'))]
    controle('aucune trame brute émise par ces routes (seule la lecture ordinaire du paramètre 0)', not autres,
             '; '.join(t.hex(' ') for t in autres))


def test_pannes(cible, chemin_panne):
    print('\n== Robustesse : CRC faux, silence du bus ==')
    avant = cible.demarrages()
    for panne in ('crc', 'muet'):
        open(chemin_panne, 'w', encoding='utf-8').write(panne)
        r = cible.jq([8700])['8700']
        controle(f'panne « {panne} » : lecture de 8700 signalée en erreur', r.get('error', 0) != 0 or r.get('value') in ('', '---'),
                 f'error {r.get("error")}, value {r.get("value")!r}')
    open(chemin_panne, 'w', encoding='utf-8').write('')
    r = cible.jq([8700])['8700']
    controle('reprise après la panne : 8700 = 3.5', r.get('error') == 0 and conforme('3.5', r))
    apres = cible.demarrages()
    controle('pas de redémarrage du SuperMini pendant les pannes', avant is None or apres is None or apres >= avant,
             f"uptime {avant} -> {apres} ms")


def test_ecriture(cible, mqtt, bus, decouverte):
    print('\n== Firmware alfea-ecriture, mode d\'écriture 0 (défaut) ==')
    cible.http('/JW', {str(CF_WRITEMODE): '0'})
    attendre_reprise(cible)
    bus.repere()
    tentatives_ecriture(cible, mqtt, decouverte)
    trames, sets = bus.ecritures()
    controle('mode 0 : aucune trame SET ni INF émise', not trames and not sets, '; '.join(sets))

    print('\n== Mode d\'écriture 1 : liste blanche ==')
    code, corps = cible.http('/JW', {str(CF_WRITEMODE): '1'})
    controle('passage en mode 1 par /JW', code == 200, f'HTTP {code}')
    attendre_reprise(cible)
    cas = [('/S710=21.5', 710, '21.5'), ('/S1012=16.5', 1012, '16.5'), ('/S1610=50', 1610, '50'),
           ('/S700=3', 700, '3'), ('/S501=05:30-22:00', 501, '05:30-22:00'),
           ('/S527=07:00-09:00_17:00-22:30', 527, '07:00-09:00 17:00-22:30')]
    for chemin, ligne, valeur in cas:
        bus.repere()
        cible.http(chemin)
        time.sleep(1)
        trames, sets = bus.ecritures()
        lu = cible.jq([ligne])[f'{ligne:g}']
        controle(f'{chemin} : SET émis, acquitté et relu', len(sets) == 1 and conforme(valeur, lu),
                 f'{sets[0] if sets else "aucun SET"} ; relu {lu.get("value")!r}')
    cat = {float(d['unique_id'].split('-')[0]): d['~'] for d in decouverte}
    bus.repere()
    mqtt.publier(cat[1010.0] + '/set', '19.5')
    time.sleep(3)
    _, sets = bus.ecritures()
    controle('MQTT 1010/set 19.5 : SET émis et relu', len(sets) == 1 and conforme('19.5', cible.jq([1010])['1010']),
             sets[0] if sets else 'aucun SET')
    for chemin in ('/S6220=1', '/S8700=10', '/S8000=1', '/S3113.1=0', '/I700=1'):
        bus.repere()
        cible.http(chemin)
        time.sleep(1)
        trames, sets = bus.ecritures()
        controle(f'{chemin} (hors liste blanche ou INF) refusé', not trames and not sets, '; '.join(sets))

    print('\n== Retour au mode 0 ==')
    cible.http('/JW', {str(CF_WRITEMODE): '0'})
    attendre_reprise(cible)
    bus.repere()
    cible.http('/S710=22')
    time.sleep(1)
    trames, sets = bus.ecritures()
    controle('mode 0 rétabli : /S710=22 refusé', not trames and not sets)


def attendre_reprise(cible, delai=90):
    """/JW peut redémarrer le SuperMini : on attend qu'il réponde de nouveau et que la PAC soit identifiée."""
    fin = time.time() + delai
    time.sleep(3)
    while time.time() < fin:
        try:
            if cible.jq([6225])['6225'].get('value') == '211':
                return True
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(3)
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('phase', choices=['lecture', 'ecriture'])
    ap.add_argument('--ip', required=True)
    ap.add_argument('--sim', required=True, help='sortie de bsb_sim.py')
    ap.add_argument('--panne', help='fichier --panne de bsb_sim.py (phase lecture)')
    ap.add_argument('--scenario', default=os.path.join(ICI, 'bsb_sim_scenario.json'))
    a = ap.parse_args()
    cible, mqtt, bus = Cible(a.ip), Mqtt(), Bus(a.sim)
    scenario = json.load(open(a.scenario, encoding='utf-8'))
    decouverte = [json.loads(c) for t, c in mqtt.lire('homeassistant/+/BSB-LAN/+/config', 5).items() if c]
    if a.phase == 'lecture':
        test_valeurs(cible, mqtt, scenario)
        test_lecture_seule(cible, mqtt, bus, decouverte)
        test_routes(cible, bus)
        if a.panne:
            test_pannes(cible, a.panne)
    else:
        test_ecriture(cible, mqtt, bus, decouverte)
    print(f'\n{sum(resultats)}/{len(resultats)} contrôles réussis')
    sys.exit(0 if all(resultats) else 1)


if __name__ == '__main__':
    main()
