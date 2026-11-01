#!/usr/bin/env python3
"""Vérifie les messages d'auto-discovery Home Assistant publiés par BSB-LAN sur un broker MQTT.

Usage : verif_discovery.py [--broker hôte] [--port 1883] [--ecriture alfea/params/ecriture.txt] [--duree 5]
        verif_discovery.py --secrets alfea/config/alfea_secrets.h   # broker, utilisateur et mot de passe MQTT
                                                                    # lus dans les secrets, jamais affichés

Client MQTT 3.1.1 minimal (bibliothèque standard seulement) : s'abonne à homeassistant/+/BSB-LAN/+/config
et à BSB-LAN/status, lit les messages retenus pendant --duree secondes, puis contrôle :
- chaque entité a unique_id, state_topic et availability_topic ;
- sans --ecriture : uniquement des entités en lecture (sensor, binary_sensor) ;
- avec --ecriture : les entités modifiables (select, text, switch) appartiennent à la liste blanche.
Code de sortie 0 si tout est conforme.
"""
import argparse
import json
import re
import socket
import struct
import sys
import time

MODIFIABLES = {'select', 'text', 'switch', 'number'}


def longueur(n):
    o = bytearray()
    while True:
        b, n = n % 128, n // 128
        o.append(b | (0x80 if n else 0))
        if not n:
            return bytes(o)


def chaine(s):
    b = s.encode()
    return struct.pack('>H', len(b)) + b


def paquets(sock):
    tampon = b''
    while True:
        try:
            morceau = sock.recv(4096)
        except socket.timeout:
            return
        if not morceau:
            return
        tampon += morceau
        while len(tampon) >= 2:
            mult, n, i = 1, 0, 1
            while True:
                if i >= len(tampon):
                    break
                b = tampon[i]
                n += (b & 0x7F) * mult
                mult *= 128
                i += 1
                if not b & 0x80:
                    break
            if len(tampon) < i + n:
                break
            yield tampon[0], tampon[i:i + n]
            tampon = tampon[i + n:]


def collecter(hote, port, duree, utilisateur=None, mot_de_passe=None):
    sock = socket.create_connection((hote, port), timeout=duree)
    drapeaux = 0x02 | (0x80 if utilisateur else 0) | (0x40 if utilisateur and mot_de_passe else 0)
    corps = chaine('MQTT') + bytes([4, drapeaux]) + struct.pack('>H', 30) + chaine('verif-discovery')
    if utilisateur:
        corps += chaine(utilisateur) + (chaine(mot_de_passe) if mot_de_passe else b'')
    sock.sendall(b'\x10' + longueur(len(corps)) + corps)
    entete, connack = next(paquets(sock), (0, b''))
    if entete >> 4 != 2 or len(connack) < 2 or connack[1] != 0:
        sys.exit(f'connexion refusée par le broker (CONNACK {connack.hex() or "absent"} ; 05 = non autorisé)')
    abonnements = chaine('homeassistant/+/BSB-LAN/+/config') + b'\x00' + chaine('BSB-LAN/status') + b'\x00'
    corps = struct.pack('>H', 1) + abonnements
    sock.sendall(b'\x82' + longueur(len(corps)) + corps)
    messages, fin = {}, time.time() + duree
    sock.settimeout(1)
    while time.time() < fin:
        for entete, corps in paquets(sock):
            if entete >> 4 == 3:                     # PUBLISH (QoS 0 demandé, QoS livré ≤ 0 ici)
                n = struct.unpack('>H', corps[:2])[0]
                sujet = corps[2:2 + n].decode()
                qos = (entete >> 1) & 3
                charge = corps[2 + n + (2 if qos else 0):]
                messages[sujet] = charge.decode('utf-8', 'replace')
            if time.time() >= fin:
                break
    sock.close()
    return messages


def lire_secrets(chemin):
    texte = open(chemin, encoding='utf-8').read()
    val = dict(re.findall(r'#define\s+(ALFEA_MQTT_\w+)\s+"([^"]*)"', texte))
    hote, _, port = val['ALFEA_MQTT_BROKER'].partition(':')
    return hote, int(port or 1883), val.get('ALFEA_MQTT_USER'), val.get('ALFEA_MQTT_PASS')


def lire_plages(chemin):
    plages = []
    for ligne in open(chemin, encoding='utf-8'):
        ligne = ligne.split('#')[0].strip()
        if ligne:
            a, _, b = ligne.partition('-')
            plages.append((float(a), float(b or a) + 0.95))
    return plages


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--broker', default='localhost')
    p.add_argument('--port', type=int, default=1883)
    p.add_argument('--ecriture')
    p.add_argument('--duree', type=float, default=5)
    p.add_argument('--secrets', help='alfea_secrets.h : broker, utilisateur et mot de passe MQTT (jamais affichés)')
    args = p.parse_args()
    blanche = lire_plages(args.ecriture) if args.ecriture else None
    utilisateur = mot_de_passe = None
    if args.secrets:
        args.broker, args.port, utilisateur, mot_de_passe = lire_secrets(args.secrets)
    messages = collecter(args.broker, args.port, args.duree, utilisateur, mot_de_passe)
    print('BSB-LAN/status :', messages.get('BSB-LAN/status', '(absent)'))
    erreurs, par_type = [], {}
    for sujet, texte in sorted(messages.items()):
        if not sujet.startswith('homeassistant/') or not texte:
            continue
        composant = sujet.split('/')[1]
        par_type[composant] = par_type.get(composant, 0) + 1
        try:
            d = json.loads(texte)
        except ValueError:
            erreurs.append(f'{sujet} : JSON invalide')
            continue
        for champ in ('unique_id', 'state_topic', 'availability_topic'):
            if champ not in d:
                erreurs.append(f'{sujet} : champ {champ} absent')
        ligne = float(d.get('unique_id', '0-').split('-')[0] or 0)
        if composant in MODIFIABLES:
            if blanche is None:
                erreurs.append(f'{sujet} : entité modifiable ({composant}) alors que le firmware doit être en lecture seule')
            elif not any(a <= ligne <= b for a, b in blanche):
                erreurs.append(f'{sujet} : ligne {ligne:g} modifiable mais hors liste blanche')
    print('entités par type :', par_type or '(aucune)')
    for e in erreurs:
        print('ERREUR', e)
    print('CONFORME' if not erreurs and par_type else 'NON CONFORME')
    sys.exit(0 if not erreurs and par_type else 1)


if __name__ == '__main__':
    main()
