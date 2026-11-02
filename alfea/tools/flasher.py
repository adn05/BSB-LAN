#!/usr/bin/env python3
"""Flash et console des deux cartes du banc (docs/claude/README_docker.md §3).

    python alfea/tools/flasher.py ports              # liste les ports série et reconnaît les cartes
    python alfea/tools/flasher.py pont               # flashe le pont (NodeMCU ESP-C3-32S-Kit, CH340)
    python alfea/tools/flasher.py alfea              # 1er flash du SuperMini : image complète en 0x0
    python alfea/tools/flasher.py alfea --appli      # mises à jour : application seule en 0x10000
    python alfea/tools/flasher.py test-broches       # test des GPIO du SuperMini (alfea/tools/test_broches)
    python alfea/tools/flasher.py test-broches-pont  # même test sur la carte du pont
    python alfea/tools/flasher.py console            # console du SuperMini (Ctrl+C pour quitter)

Le port est détecté par l'identifiant USB ; --port COMx force un port. Les images viennent de
docker/compiler.sh (alfea/build/<image>).

Image complète en 0x0 : elle contient bootloader, table de partitions et application, et remplit les trous
de 0xFF, donc efface la NVS (0x9000) où BSB-LAN garde sa configuration. D'où --appli pour les mises à jour.
"""
import argparse
import os
import sys
import threading
import time

import serial
from serial.tools import list_ports

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build'))
# (VID, PID) -> carte
CARTES = {
    (0x1A86, 0x7523): 'pont',     # CH340 de la NodeMCU ESP-C3-32S-Kit
    (0x1A86, 0x55D4): 'pont',     # CH9102/CH343, selon les lots [SUPPOSÉ]
    (0x303A, 0x1001): 'alfea',    # USB-Serial/JTAG intégré de l'ESP32-C3 (SuperMini)
}
# image -> (fichier dans alfea/build/<image>/, carte)
IMAGES = {
    'pont': ('pont_bsb.ino', 'pont'),
    'pont-diag': ('pont_bsb.ino', 'pont'),
    'alfea': ('BSB_LAN.ino', 'alfea'),
    'alfea-ecriture': ('BSB_LAN.ino', 'alfea'),
    'test-broches': ('test_broches.ino', 'alfea'),
    'test-broches-pont': ('test_broches.ino', 'pont'),
}


def carte_de(p):
    return CARTES.get((p.vid, p.pid)) if p.vid is not None else None


def trouver_port(carte, force):
    if force:
        return force
    ports = [p.device for p in list_ports.comports() if carte_de(p) == carte]
    if len(ports) != 1:
        sys.exit(f'{len(ports)} port(s) reconnu(s) pour « {carte} » : préciser --port COMx (voir « ports »).')
    return ports[0]


def ports(_):
    for p in sorted(list_ports.comports(), key=lambda p: p.device):
        vidpid = f'{p.vid:04X}:{p.pid:04X}' if p.vid is not None else '----:----'
        print(f'{p.device:8} {vidpid}  {carte_de(p) or "?":6} {p.description}')


def flasher(a):
    import esptool
    base, carte = IMAGES[a.image]
    if a.appli:
        adresse, image = '0x10000', os.path.join(RACINE, a.image, base + '.bin')
    else:
        adresse, image = '0x0', os.path.join(RACINE, a.image, base + '.merged.bin')
    if not os.path.isfile(image):
        sys.exit(f'image absente : {image}\ncompiler d\'abord : sh docker/compiler.sh {a.image}')
    port = trouver_port(carte, a.port)
    print(f'{a.image} : {image} -> {port} @ {adresse}')
    esptool.main(['--chip', 'esp32c3', '--port', port, '--baud', str(a.baud),
                  'write-flash', adresse, image])


def console(a):
    """Affiche ce que la carte envoie et transmet chaque ligne tapée (Entrée). Ctrl+C pour quitter.
    Le port est rouvert s'il disparaît (le SuperMini se réénumère sur l'USB à chaque reset)."""
    port = trouver_port(a.carte, a.port)
    lien = {'ser': None}

    def clavier():
        for ligne in sys.stdin:
            ser = lien['ser']
            if ser is not None:
                try:
                    ser.write(ligne.rstrip('\r\n').encode() + b'\n')
                except serial.SerialException:
                    pass

    threading.Thread(target=clavier, daemon=True).start()
    print(f'console {port} à {a.vitesse} bauds (Ctrl+C pour quitter)', flush=True)
    try:
        while True:
            try:
                ser = serial.Serial()
                ser.port, ser.baudrate, ser.timeout = port, a.vitesse, 0.1
                # DTR et RTS inactifs : sur le CH340 du pont, RTS commande EN et DTR commande IO9 (reset, mode boot)
                ser.dtr = ser.rts = False
                ser.open()
                lien['ser'] = ser
                while True:
                    brut = ser.read(4096)
                    if brut:
                        sys.stdout.write(brut.decode('utf-8', 'replace'))
                        sys.stdout.flush()
            except serial.SerialException:
                lien['ser'] = None
                time.sleep(0.5)
    except KeyboardInterrupt:
        print('\nconsole fermée')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('ports').set_defaults(f=ports)
    for image in IMAGES:
        p = sp.add_parser(image)
        p.add_argument('--port')
        p.add_argument('--baud', type=int, default=460800)
        p.add_argument('--appli', action='store_true', help='application seule en 0x10000 (garde la NVS)')
        p.set_defaults(f=flasher, image=image)
    p = sp.add_parser('console')
    p.add_argument('--port')
    p.add_argument('--carte', choices=sorted(set(c for _, c in IMAGES.values())), default='alfea')
    p.add_argument('--vitesse', type=int, default=115200)
    p.set_defaults(f=console)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
