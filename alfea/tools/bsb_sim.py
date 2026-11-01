#!/usr/bin/env python3
"""Simulateur de régulateur BSB (RVS21 211/127) pour tester le firmware sans PAC.

Câblage (docs/claude/08 §6, T1) : adaptateur USB-UART 3,3 V relié directement aux GPIO du
SuperMini, sans carte d'interface : TX adaptateur -> GPIO6 (RX bus), RX adaptateur <- GPIO7 (TX bus),
masses communes. BSB-LAN complémente les octets en logiciel (^0xFF, src/BSB/bsb.cpp) : le simulateur
fait de même, en 4800 bauds 8O1.

Comportement :
- écho immédiat de chaque octet reçu, comme sur le vrai bus (BSB-LAN relit sa trame, bsb.cpp:488-503) ;
- QINF 0x053D0064 (diffusion) -> INF d'identification (famille, variante, OC, n° de série) ;
- QUR -> ANS avec la valeur du scénario, encodée selon le type de la liste (cmdtbl) et optbl ;
- SET -> ACK, valeur mémorisée et journalisée (« SET reçu ») : en lecture seule, il ne doit y en avoir aucun ;
- objet inconnu -> pas de réponse (BSB-LAN conclut à l'absence de réponse).

Usage :
  bsb_sim.py --autotest                       # contrôles de codage, sans matériel
  bsb_sim.py --port /dev/ttyUSB0 [--scenario f.json] [--liste ...] [--defs ...]
  bsb_sim.py --port COM7 --pont               # via une ESP-C3-32S-Kit (alfea/tools/pont_bsb), sans adaptateur USB-UART
"""
import argparse
import json
import os
import re
import struct
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, '..', '..'))
sys.path.insert(0, ICI)
from analyse_liste import lire_liste, lire_optbl  # noqa: E402

TYPE_QINF, TYPE_INF, TYPE_SET, TYPE_ACK, TYPE_NACK, TYPE_QUR, TYPE_ANS = 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07
ADDR_HEIZ, ADDR_ALL = 0x00, 0x7F
CMD_IDENT, CMD_NOM = 0x053D0064, 0x053D0001


# ----------------------------------------------------------------------------- trames
def crc16(data):
    """CRC-16 XMODEM (poly 0x1021, init 0), comme bsb.cpp."""
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def octets_cmd(cmd, typ, dst):
    """Les 2 premiers octets du CmdID sont permutés pour QINF/QUR/SET et pour un INF non diffusé
    (BSB_LAN.ino:2741, print_telegram.h:798)."""
    b = list(struct.pack('>I', cmd))
    if typ in (TYPE_QINF, TYPE_QUR, TYPE_SET) or (typ == TYPE_INF and dst != ADDR_ALL):
        b[0], b[1] = b[1], b[0]
    return b


def trame(src, dst, typ, cmd, charge=b''):
    corps = [0xDC, 0x80 | src, dst, 0, typ] + octets_cmd(cmd, typ, dst) + list(charge)
    corps[3] = len(corps) + 2
    c = crc16(corps)
    return bytes(corps + [c >> 8, c & 0xFF])


def lire_trame(t):
    """-> (src, dst, typ, cmd, charge) ; ValueError si la trame est invalide."""
    if len(t) < 11 or t[0] != 0xDC or t[3] != len(t) or crc16(t[:-2]) != (t[-2] << 8 | t[-1]):
        raise ValueError('trame invalide : ' + t.hex(' '))
    src, dst, typ = t[1] & 0x7F, t[2], t[4]
    b = list(t[5:9])
    if typ in (TYPE_QINF, TYPE_QUR, TYPE_SET) or (typ == TYPE_INF and dst != ADDR_ALL):
        b[0], b[1] = b[1], b[0]
    return src, dst, typ, struct.unpack('>I', bytes(b))[0], bytes(t[9:-2])


# ----------------------------------------------------------------------------- valeurs
def encoder(vt, opt, valeur):
    """Charge utile d'une réponse ANS pour la valeur texte `valeur` d'un paramètre de type `vt`."""
    if vt == 'VT_TIMEPROG':
        octets = []
        for plage in (valeur.split() + ['--'] * 3)[:3]:
            m = re.match(r'(\d+):(\d+)-(\d+):(\d+)$', plage)
            octets += [int(g) for g in m.groups()] if m else [0x80, 0, 0x80, 0]
        return bytes(octets)
    if vt in ('VT_DATETIME', 'VT_DAYMONTH', 'VT_TIME', 'VT_YEAR', 'VT_VACATIONPROG'):
        m = re.match(r'(\d+)\.(\d+)\.(\d+) (\d+):(\d+):(\d+)$', valeur)
        j, mo, a, h, mi, s = (int(g) for g in m.groups())
        return bytes([0, a - 1900, mo, j, 0, h, mi, s, 0])
    if vt == 'VT_STRING':
        return valeur.encode('latin-1').ljust(17, b'\0')
    pl = opt['pl'] & 31
    if valeur in ('---', None):
        return bytes([1] + [0] * pl)                       # octet d'activation ≠ 0 : valeur inactive
    if opt['dt'] == 'DT_ENUM':
        code = int(valeur.split(' ')[0])
        return bytes([0]) + code.to_bytes(2 if code > 255 else max(pl, 1), 'big')
    brut = round(float(valeur) * opt['op'])
    entete = b'' if opt['en'] == 8 else b'\0'
    return entete + brut.to_bytes(pl, 'big', signed=brut < 0)


class Regulateur:
    def __init__(self, liste, defs, scenario):
        self.optbl = lire_optbl(defs)
        self.par_cmd = {}
        for e in lire_liste(liste):
            if e['fam'] in ('211', '255'):
                self.par_cmd.setdefault(e['cmd'], e)
        self.valeurs = {float(k): v for k, v in scenario.get('valeurs', {}).items()}
        self.ident = scenario.get('identification', {})
        self.sets = []

    def repondre(self, src, dst, typ, cmd, charge):
        """Trame de réponse (bytes) ou None."""
        if typ == TYPE_QINF and cmd == CMD_IDENT:
            i = self.ident
            # 00 | famille | 00 | variante | OC (2 o) | n° de série (4 o) : dump l. 15, lu en BSB_LAN.ino:4180-4184
            p = bytes([0, i.get('famille', 211), 0, i.get('variante', 127)])
            p += struct.pack('>H', i.get('oc', 0x0FBA)) + struct.pack('>I', i.get('serie', 137987))
            return trame(ADDR_HEIZ, src, TYPE_INF, CMD_IDENT, p)
        if dst != ADDR_HEIZ:
            return None
        if typ == TYPE_QUR and cmd == CMD_NOM:
            return trame(ADDR_HEIZ, src, TYPE_ANS, cmd, self.ident.get('nom', 'RVS21.831F/127').encode().ljust(17, b'\0'))
        e = self.par_cmd.get(cmd)
        if e is None:
            return None
        if typ == TYPE_SET:
            self.sets.append((e['line'], charge.hex(' ')))
            print(f'SET reçu : ligne {e["line"]:g} ({e["texte"]}) charge {charge.hex(" ")}', flush=True)
            self.valeurs[e['line']] = ('raw', charge)
            return trame(ADDR_HEIZ, src, TYPE_ACK, cmd)
        if typ == TYPE_QUR:
            v = self.valeurs.get(e['line'], '---')
            charge = v[1] if isinstance(v, tuple) else encoder(e['vt'], self.optbl.get(e['vt'], {'pl': 2, 'op': 1, 'en': 1, 'dt': 'DT_VALS'}), v)
            return trame(ADDR_HEIZ, src, TYPE_ANS, cmd, charge)
        return None


# ----------------------------------------------------------------------------- liaison série
def boucle(port, reg, pont=False):
    import serial  # pyserial, seulement pour le mode matériel
    if pont:   # NodeMCU ESP-C3-32S-Kit : liaison PC <-> pont en 115 200 8N1, le pont fait le 4800 8O1
        ser = serial.Serial(None, 115200, timeout=0.005)
    else:
        ser = serial.Serial(None, 4800, bytesize=8, parity=serial.PARITY_ODD, stopbits=1, timeout=0.005)
    ser.port = port
    ser.dtr = ser.rts = False          # cartes ESP32 : DTR/RTS pilotent EN et IO9 (reset, mode flash)
    ser.open()
    tampon = bytearray()
    dernier = time.monotonic()
    print(f'simulateur BSB sur {port} (4800 8O1, octets complémentés'
          f'{", via le pont ESP32-C3 en 115 200 bauds, écho matériel" if pont else ""})', flush=True)
    while True:
        brut = ser.read(64)
        if brut:
            if not pont:
                ser.write(brut)                              # écho du bus (adaptateur USB-UART)
            tampon += bytes(b ^ 0xFF for b in brut)
            dernier = time.monotonic()
        while tampon and tampon[0] != 0xDC:
            tampon.pop(0)
        if len(tampon) >= 4 and len(tampon) >= tampon[3]:
            t = bytes(tampon[:tampon[3]])
            del tampon[:tampon[3]]
            try:
                src, dst, typ, cmd, charge = lire_trame(t)
            except ValueError as err:
                print(err, flush=True)
                continue
            print(f'<- {t.hex(" ")}', flush=True)
            rep = reg.repondre(src, dst, typ, cmd, charge)
            if rep:
                time.sleep(0.03)
                ser.write(bytes(b ^ 0xFF for b in rep))
                print(f'-> {rep.hex(" ")}', flush=True)
        elif tampon and time.monotonic() - dernier > 0.2:
            tampon.clear()                                   # trame tronquée


# ----------------------------------------------------------------------------- autotest
def autotest(liste, defs, scenario):
    def verifier(nom, obtenu, attendu):
        ok = obtenu == attendu
        print(f'{"OK " if ok else "ÉCHEC"} {nom}' + ('' if ok else f'\n   obtenu  {obtenu}\n   attendu {attendu}'))
        return ok

    h = bytes.fromhex
    ok = True
    # vecteurs réels : BSB_LAN_custom_defs.h.default:7137, dump /QD (issue #622), PR #812, doc 02
    ok &= verifier('CRC trame du code amont', crc16(h('DC 80 0A 0E 07 2D 3D 05 A5 00 08 C0')), 0x3F7B)
    ok &= verifier('QUR 8700 (02 §2.2)', trame(0x42, 0x00, TYPE_QUR, 0x053D0521).hex(' '), 'dc c2 00 0b 06 3d 05 05 21 b9 7c')
    ok &= verifier('ANS identification (dump l. 15)',
                   trame(0x00, 0x42, TYPE_ANS, CMD_IDENT, h('00 D3 00 7F 0F BA 00 02 1B 03')).hex(' '),
                   'dc 80 42 15 07 05 3d 00 64 00 d3 00 7f 0f ba 00 02 1b 03 83 51')
    ok &= verifier('ACK 642 (PR #812)', trame(0x00, 0x42, TYPE_ACK, 0x053D09C4).hex(' '), 'dc 80 42 0b 04 05 3d 09 c4 14 4e')
    ok &= verifier('SET 642 (PR #812)', trame(0x42, 0x00, TYPE_SET, 0x053D09C4, h('01 00 05 08 00 00 00 00 17')).hex(' '),
                   'dc c2 00 14 03 3d 05 09 c4 01 00 05 08 00 00 00 00 17 dc c1')
    ok &= verifier('lecture d\'une trame', lire_trame(h('dc c2 00 0b 06 3d 05 05 21 b9 7c'))[:4], (0x42, 0x00, TYPE_QUR, 0x053D0521))
    reg = Regulateur(liste, defs, scenario)
    opt = reg.optbl
    ok &= verifier('encodage VT_TEMP 21,5 °C', encoder('VT_TEMP', opt['VT_TEMP'], '21.5').hex(' '), '00 05 60')
    ok &= verifier('encodage VT_TEMP -3,25 °C', encoder('VT_TEMP', opt['VT_TEMP'], '-3.25').hex(' '), '00 ff 30')
    ok &= verifier('encodage VT_ENUM 1', encoder('VT_ENUM', opt['VT_ENUM'], '1').hex(' '), '00 01')
    ok &= verifier('encodage VT_ENERGY 32545 kWh (#831)', encoder('VT_ENERGY', opt['VT_ENERGY'], '32545').hex(' '), '00 00 00 7f 21')
    ok &= verifier('encodage VT_TIMEPROG', encoder('VT_TIMEPROG', {}, '06:00-08:00 17:00-22:30').hex(' '),
                   '06 00 08 00 11 00 16 1e 80 00 80 00')
    ok &= verifier('réponse INF d\'identification', reg.repondre(0x42, ADDR_ALL, TYPE_QINF, CMD_IDENT, b'')[4:15].hex(' '),
                   '02 3d 05 00 64 00 d3 00 7f 0f ba')
    absents = [k for k in scenario.get('valeurs', {}) if not any(e['line'] == float(k) for e in reg.par_cmd.values())]
    ok &= verifier('scénario : toutes les lignes existent dans la liste', absents, [])
    print('AUTOTEST', 'RÉUSSI' if ok else 'ÉCHOUÉ')
    return 0 if ok else 1


def main():
    a = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    a.add_argument('--port')
    a.add_argument('--autotest', action='store_true')
    a.add_argument('--pont', action='store_true', help='port = NodeMCU ESP-C3-32S-Kit avec alfea/tools/pont_bsb (115 200 bauds, écho fait par le pont)')
    a.add_argument('--liste', default=os.path.join(DEPOT, 'alfea', 'params', 'BSB_LAN_custom_defs_ha.h'))
    a.add_argument('--defs', default=os.path.join(DEPOT, 'BSB_LAN', 'BSB_LAN_defs.h'))
    a.add_argument('--scenario', default=os.path.join(ICI, 'bsb_sim_scenario.json'))
    args = a.parse_args()
    scenario = json.load(open(args.scenario, encoding='utf-8'))
    if args.autotest:
        sys.exit(autotest(args.liste, args.defs, scenario))
    if not args.port:
        a.error('--port ou --autotest requis')
    boucle(args.port, Regulateur(args.liste, args.defs, scenario), args.pont)


if __name__ == '__main__':
    main()
