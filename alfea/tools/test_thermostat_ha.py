#!/usr/bin/env python3
"""Essai du paquet de thermostats (alfea/homeassistant/alfea_thermostats.yaml) dans un Home Assistant jetable.

    python -I alfea/tools/test_thermostat_ha.py

Lance en Docker un Mosquitto (anonyme) et HA 2026.10.4 (version de l'installation cible), sur le port 18123/18833
de l'hôte, avec une configuration vierge dans alfea/build/ha_thermostat ; fait l'onboarding et ajoute l'intégration
MQTT par l'API ; publie les états que publierait BSB-LAN ; vérifie les entités climate (modes, consignes, action,
disponibilité) et les sujets set émis par les services de HA, dont la séquence de dérogation ; supprime ensuite les conteneurs. Ne touche ni au
broker ni au HA réels. Code de sortie 0 si tous les contrôles passent (docs/claude/12_thermostat_home_assistant.md).
"""
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verif_discovery as v

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = os.path.join(RACINE, 'alfea', 'build', 'ha_thermostat')
IMAGE_HA = 'ghcr.io/home-assistant/home-assistant:2026.10.4'
IMAGE_MQ = 'eclipse-mosquitto:2.0.22'

HA = 'http://127.0.0.1:18123'
MQ = ('127.0.0.1', 18833)
CID = HA + '/'
TOK = None


def docker(*a, verifier=True):
    return subprocess.run(['docker', *a], check=verifier, capture_output=True, text=True)


def demarrer():
    shutil.rmtree(CONFIG, ignore_errors=True)
    os.makedirs(os.path.join(CONFIG, 'packages'))
    shutil.copy(os.path.join(RACINE, 'alfea', 'homeassistant', 'alfea_thermostats.yaml'), os.path.join(CONFIG, 'packages'))
    with open(os.path.join(CONFIG, 'configuration.yaml'), 'w', encoding='utf-8') as f:
        f.write('default_config:\nhomeassistant:\n  packages: !include_dir_named packages\n')
    arreter()
    docker('network', 'create', 'alfea-e2e')
    docker('run', '-d', '--rm', '--name', 'e2e-mosquitto', '--network', 'alfea-e2e', '-p', '18833:1883', '-v',
           os.path.join(RACINE, 'docker', 'ha-test', 'mosquitto', 'mosquitto.conf') + ':/mosquitto/config/mosquitto.conf:ro', IMAGE_MQ)
    docker('run', '-d', '--rm', '--name', 'e2e-ha', '--network', 'alfea-e2e', '-p', '18123:8123', '-e', 'TZ=Europe/Paris',
           '-v', CONFIG + ':/config', IMAGE_HA)


def arreter():
    docker('rm', '-f', 'e2e-ha', 'e2e-mosquitto', verifier=False)
    docker('network', 'rm', 'alfea-e2e', verifier=False)


def req(meth, path, data=None, form=False):
    h = {}
    if TOK: h['Authorization'] = 'Bearer ' + TOK
    if data is not None:
        if form:
            data = urllib.parse.urlencode(data).encode(); h['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            data = json.dumps(data).encode(); h['Content-Type'] = 'application/json'
    r = urllib.request.Request(HA + path, data=data, headers=h, method=meth)
    try:
        x = urllib.request.urlopen(r, timeout=30)
    except urllib.error.HTTPError as e:
        print('HTTP', e.code, path, e.read().decode()[:500]); raise
    with x:
        b = x.read().decode()
        return json.loads(b) if b else None


def mq_session(cid, maintien=60):
    s = socket.create_connection(MQ, timeout=10)
    c = v.chaine('MQTT') + bytes([4, 0x02]) + struct.pack('>H', maintien) + v.chaine(cid)
    s.sendall(b'\x10' + v.longueur(len(c)) + c); next(v.paquets(s)); return s


def pub(t, p, retain=True):
    s = mq_session('e2e-pub'); c = v.chaine(t) + p.encode()
    s.sendall(bytes([0x31 if retain else 0x30]) + v.longueur(len(c)) + c); time.sleep(0.3)
    s.sendall(b'\xe0\x00'); s.close()


ok = True
recus = []


def ecoute():
    # maintien 0 : sinon le broker coupe l'écoute, qui n'émet rien
    s = mq_session('e2e-ecoute', 0); c = struct.pack('>H', 1) + v.chaine('BSB-LAN/+/+/+/set') + b'\x00'
    s.sendall(b'\x82' + v.longueur(len(c)) + c); s.settimeout(None)
    for e, cc in v.paquets(s):
        if e >> 4 == 3:
            n = struct.unpack('>H', cc[:2])[0]; t, p = cc[2:2 + n].decode(), cc[2 + n:].decode(); recus.append((t, p))
            # comme BSB-LAN : la valeur écrite est relue puis publiée (l'automatisation de dérogation l'attend)
            if t.endswith(('/701/set', '/1001/set')):
                threading.Thread(target=pub, args=(t[:-3] + 'status', {'0': '0 - Plus froid', '1': '1 - ...', '2': '2 - Plus chaud'}.get(p, p))).start()
            elif t.endswith(('/701.3/set', '/1001.3/set', '/701.4/set', '/1001.4/set')):
                threading.Thread(target=pub, args=(t[:-3] + 'status', p)).start()


def verifie(eid, attendu):
    global ok
    fin = time.time() + 60
    while True:
        try:
            s = req('GET', '/api/states/' + eid)
            g = {'state': s['state'], **{k: s['attributes'].get(k) for k in attendu if k != 'state'}}
        except Exception as e:
            g = {'erreur': str(e)}
        if all(g.get(k) == x for k, x in attendu.items()) or time.time() > fin: break
        time.sleep(2)
    bon = all(g.get(k) == x for k, x in attendu.items()); ok &= bon
    print('OK ' if bon else 'ERR', eid, g if not bon else attendu)


def appel(service, data, attendu, attente=3):
    global ok
    n = len(recus); req('POST', '/api/services/climate/' + service, data); time.sleep(attente)
    nv = recus[n:]; bon = nv == attendu; ok &= bon
    print('OK ' if bon else 'ERR', service, data, '->', nv)


def essai():
    global TOK, ok
    # 1. attendre HA, onboarding, jeton
    fin = time.time() + 300
    while True:
        try:
            req('GET', '/api/onboarding'); break
        except Exception:
            if time.time() > fin: raise
            time.sleep(5)
    r = req('POST', '/api/onboarding/users', {'client_id': CID, 'name': 'Test', 'username': 'test', 'password': 'test-e2e-1234', 'language': 'fr'})
    TOK = req('POST', '/auth/token', {'grant_type': 'authorization_code', 'code': r['auth_code'], 'client_id': CID}, form=True)['access_token']
    for p, d in [('/api/onboarding/core_config', {}), ('/api/onboarding/analytics', {})]:
        try: req('POST', p, d)
        except Exception as e: print('onboarding', p, e)

    # 2. intégration MQTT vers le broker de test
    f = req('POST', '/api/config/config_entries/flow', {'handler': 'mqtt', 'show_advanced_options': False})
    for _ in range(4):
        if f.get('type') == 'create_entry': break
        if f.get('type') == 'menu':
            f = req('POST', '/api/config/config_entries/flow/' + f['flow_id'], {'next_step_id': 'broker' if 'broker' in f['menu_options'] else f['menu_options'][0]}); continue
        f = req('POST', '/api/config/config_entries/flow/' + f['flow_id'], {'broker': 'e2e-mosquitto', 'port': 1883, 'other_settings': {'set_client_cert': False, 'set_ca_cert': 'off'}})
    print('flux MQTT :', f.get('type'), f.get('errors'))
    # entités à déclencheur MQTT (template) et automatisation : rechargées une fois l'intégration MQTT présente
    for d in ('template', 'automation'):
        req('POST', '/api/services/' + d + '/reload', {})
    time.sleep(3)

    # 3. états publiés par BSB-LAN (comme sur le broker réel)
    # consignes confort / réduit annoncées comme par la discovery de BSB-LAN (le préréglage les cherche par nom)
    dev = {'identifiers': 'BSB-LAN-DC067567DA2C', 'name': 'BSB-LAN'}
    for ligne, cat, nom in [(710, 8, 'Chambre - Consigne de confort (°C)'), (712, 8, 'Chambre - Consigne régime REDUIT (°C)'),
                            (1010, 10, 'Salon - Consigne de confort (°C)'), (1012, 10, 'Salon - Consigne régime REDUIT (°C)')]:
        pub(f'homeassistant/text/BSB-LAN/{ligne}-test/config', json.dumps(
            {'name': nom, 'unique_id': f'{ligne}-test', 'state_topic': f'BSB-LAN/0/{cat}/{ligne}/status',
             'command_topic': f'BSB-LAN/0/{cat}/{ligne}/set', 'device': dev}))
    time.sleep(5)   # entités text créées avant la première consigne en vigueur (le préréglage les cherche)
    etats = {'BSB-LAN/status': 'online', 'BSB-LAN/0/32/8740/status': '20.2', 'BSB-LAN/0/32/8741/status': '20.5',
             'BSB-LAN/0/8/710/status': '20.5', 'BSB-LAN/0/8/712/status': '18.0',
             'BSB-LAN/0/8/700/status': '1 - Automatique', 'BSB-LAN/0/28/8000/status': '114 - Régime chauffage Confort',
             'BSB-LAN/0/8/701/status': '1 - ...', 'BSB-LAN/0/8/701.3/status': '1.5',
             'BSB-LAN/0/32/8770/status': '18.7', 'BSB-LAN/0/32/8771/status': '18.0',
             'BSB-LAN/0/10/1010/status': '19.0', 'BSB-LAN/0/10/1012/status': '18.0',
             'BSB-LAN/0/10/1000/status': '2 - Réduit', 'BSB-LAN/0/29/8001/status': "118 - Régime d'été",
             'BSB-LAN/0/10/1001/status': '1 - ...', 'BSB-LAN/0/10/1001.3/status': '4.0'}
    for t, p in etats.items(): pub(t, p)
    # BSB-LAN republie chaque minute : la consigne en vigueur revient après les consignes confort / réduit
    pub('BSB-LAN/0/32/8741/status', '20.5'); pub('BSB-LAN/0/32/8771/status', '18.0')
    threading.Thread(target=ecoute, daemon=True).start()

    time.sleep(5)
    ents = [s['entity_id'] for s in req('GET', '/api/states') if s['entity_id'].startswith('climate.')]
    print('entités climate :', ents)
    cc1 = next(e for e in ents if 'chambre' in e or 'cc1' in e); cc2 = next(e for e in ents if 'salon' in e or 'cc2' in e)
    s = req('GET', '/api/states/' + cc1)['attributes']
    print('attributs CC1 :', {k: s.get(k) for k in ('hvac_modes', 'preset_modes', 'min_temp', 'max_temp', 'target_temp_step')})
    verifie(cc1, {'state': 'heat', 'current_temperature': 20.2, 'temperature': 20.5, 'hvac_action': 'heating', 'preset_mode': 'comfort'})
    verifie(cc2, {'state': 'heat', 'current_temperature': 18.7, 'temperature': 18.0, 'hvac_action': 'idle', 'preset_mode': 'eco'})
    verifie('input_number.pac_duree_derogation', {'state': '3.0'})

    # 4. consigne -> dérogation (séquence de l'A59, doc 12 §6.1) ; consigne du programme : CC1 20,5, CC2 18,0
    D = 9
    appel('set_temperature', {'entity_id': cc1, 'temperature': 21.5},
          [('BSB-LAN/0/8/701/set', '1'), ('BSB-LAN/0/8/701.3/set', '1.0'), ('BSB-LAN/0/8/701.4/set', '3'), ('BSB-LAN/0/8/701/set', '2')], D)
    pub('BSB-LAN/0/8/701.4/status', '3'); pub('BSB-LAN/0/8/701/status', '2 - Plus chaud'); pub('BSB-LAN/0/8/701.3/status', '1.0'); pub('BSB-LAN/0/32/8741/status', '21.5')
    verifie(cc1, {'temperature': 21.5, 'preset_mode': 'none'})
    fin = req('GET', '/api/states/sensor.pac_chambre_fin_de_derogation')['state']
    reste = (time.mktime(time.strptime(fin[:19], '%Y-%m-%dT%H:%M:%S')) - time.mktime(time.gmtime())) / 3600 if fin[:2] == '20' else -1
    bon = 2.9 < reste < 3.1; ok &= bon
    print('OK ' if bon else 'ERR', 'fin de dérogation chambre', fin, f'(dans {reste:.2f} h)')
    appel('set_temperature', {'entity_id': cc1, 'temperature': 20.5}, [('BSB-LAN/0/8/701/set', '1')], D)   # retour au programme
    pub('BSB-LAN/0/8/701/status', '1 - ...'); pub('BSB-LAN/0/32/8741/status', '20.5')
    verifie(cc1, {'temperature': 20.5, 'preset_mode': 'comfort'})
    verifie('sensor.pac_chambre_fin_de_derogation', {'state': 'unknown'})
    # CC2 : écart mémorisé (4,0) ignoré au neutre ; plus froid, puis plus chaud depuis une dérogation en cours
    appel('set_temperature', {'entity_id': cc2, 'temperature': 17},
          [('BSB-LAN/0/10/1001/set', '1'), ('BSB-LAN/0/10/1001.3/set', '1.0'), ('BSB-LAN/0/10/1001.4/set', '3'), ('BSB-LAN/0/10/1001/set', '0')], D)
    pub('BSB-LAN/0/10/1001/status', '0 - Plus froid'); pub('BSB-LAN/0/10/1001.3/status', '1.0'); pub('BSB-LAN/0/32/8771/status', '17.0')
    verifie(cc2, {'temperature': 17.0, 'preset_mode': 'none'})
    appel('set_temperature', {'entity_id': cc2, 'temperature': 19.5},
          [('BSB-LAN/0/10/1001/set', '1'), ('BSB-LAN/0/10/1001.3/set', '1.5'), ('BSB-LAN/0/10/1001.4/set', '3'), ('BSB-LAN/0/10/1001/set', '2')], D)

    pub('BSB-LAN/0/32/8771/status', '19.5')

    # 5. préréglages = consigne cible réduit / confort, par dérogation ou annulation (modes : automatique seul)
    print('modes CC1 :', req('GET', '/api/states/' + cc1)['attributes'].get('hvac_modes'))
    appel('set_preset_mode', {'entity_id': cc1, 'preset_mode': 'eco'},     # confort 20,5 -> réduit 18,0 : plus froid 2,5
          [('BSB-LAN/0/8/701/set', '1'), ('BSB-LAN/0/8/701.3/set', '2.5'), ('BSB-LAN/0/8/701.4/set', '3'), ('BSB-LAN/0/8/701/set', '0')], D)
    pub('BSB-LAN/0/32/8741/status', '18.0')
    verifie(cc1, {'temperature': 18.0, 'preset_mode': 'eco'})
    appel('set_preset_mode', {'entity_id': cc1, 'preset_mode': 'comfort'}, [('BSB-LAN/0/8/701/set', '1')], D)   # = programme
    appel('set_preset_mode', {'entity_id': cc2, 'preset_mode': 'eco'}, [('BSB-LAN/0/10/1001/set', '1')], D)     # annule +1,5

    # 6. retour d'état de BSB-LAN et indisponibilité ; le mode reste « auto » quel que soit 700
    pub('BSB-LAN/0/8/700/status', '3 - Confort'); pub('BSB-LAN/0/32/8741/status', '20.5')
    verifie(cc1, {'state': 'heat', 'temperature': 20.5, 'preset_mode': 'comfort'})
    pub('BSB-LAN/0/32/8740/status', 'None')
    verifie(cc1, {'current_temperature': None})
    pub('BSB-LAN/status', 'offline')
    verifie(cc1, {'state': 'unavailable'})
    print('TOUT OK' if ok else 'ECHEC')
    return ok


if __name__ == '__main__':
    demarrer()
    try:
        bon = essai()
        journal = docker('logs', 'e2e-ha', verifier=False)
        # « Cannot subscribe » : déclencheurs MQTT des entités template au démarrage, avant que l'essai ajoute l'intégration
        # MQTT (rechargées ensuite) ; propre au HA jetable, sans objet sur une installation où MQTT est configuré.
        avert = [l for l in (journal.stdout + journal.stderr).splitlines() if 'mqtt' in l.lower() and ('WARNING' in l or 'ERROR' in l)
                 and 'Cannot subscribe to topic' not in l]
        print('avertissements MQTT dans le journal de HA :', len(avert)); print(*avert[:10], sep='\n')
        sys.exit(0 if bon and not avert else 1)
    finally:
        arreter()
