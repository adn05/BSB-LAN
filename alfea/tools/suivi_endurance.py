#!/usr/bin/env python3
"""Suivi de l'essai d'endurance (T4) sans console USB, sans requête supplémentaire sur le bus BSB.

Deux sources, toutes deux passives vis-à-vis de la PAC :
  - /JI de BSB-LAN toutes les 5 min (informations internes, aucune trame sur le bus) :
    uptime (ms) et mémoire libre, d'où les redémarrages (uptime qui recule) et une éventuelle fuite de mémoire ;
  - le broker MQTT (abonnement en lecture, conteneur eclipse-mosquitto) : disponibilité BSB-LAN/status
    (online / offline) et valeurs publiées par BSB-LAN chaque minute (dont 6700 / 6708 erreurs).

Usage (depuis la racine du dépôt, PC allumé pendant tout l'essai) :
    python alfea/tools/suivi_endurance.py            # lance le suivi, Ctrl+C pour arrêter
    python alfea/tools/suivi_endurance.py --resume   # bilan des fichiers enregistrés
Sorties dans alfea/build/endurance/ (ignoré par git) : ji.csv, mqtt.log.
Identifiants lus dans alfea/config/alfea_secrets.h, jamais affichés ni écrits.
Documentation : docs/claude/11_mise_en_service_pac.md §7.
"""
import base64, csv, datetime, http.client, json, os, re, signal, subprocess, sys, time

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SECRETS = os.path.join(RACINE, 'alfea', 'config', 'alfea_secrets.h')
SORTIE = os.path.join(RACINE, 'alfea', 'build', 'endurance')
HOTE_BSB = '192.168.30.202'
PERIODE_JI = 300
IMAGE_MQTT = 'eclipse-mosquitto:2.0.22'


def secret(nom):
    m = re.search(r'#define\s+' + nom + r'\s+"([^"]*)"', open(SECRETS, encoding='utf-8').read())
    if not m:
        sys.exit(f'{nom} absent de alfea_secrets.h')
    return m.group(1)


def lire_ji(auth):
    c = http.client.HTTPConnection(HOTE_BSB, 80, timeout=30)
    c.request('GET', '/JI', headers={'Authorization': 'Basic ' + auth})
    return json.loads(c.getresponse().read().decode('utf-8', 'replace'))


def suivre():
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))   # arrêt propre aussi sur SIGTERM
    os.makedirs(SORTIE, exist_ok=True)
    auth = base64.b64encode(secret('ALFEA_USER_PASS').encode()).decode()
    hote_mqtt = secret('ALFEA_MQTT_BROKER').split(':')[0]
    env = dict(os.environ, H=hote_mqtt, U=secret('ALFEA_MQTT_USER'), P=secret('ALFEA_MQTT_PASS'), MSYS_NO_PATHCONV='1')
    journal = open(os.path.join(SORTIE, 'mqtt.log'), 'a', encoding='utf-8')
    # -F : horodatage ISO, sujet, contenu ; les sujets /set (commandes) ne sont pas enregistrés
    mqtt = subprocess.Popen(['docker', 'run', '--rm', '--name', 'suivi_endurance_mqtt', '-e', 'H', '-e', 'U', '-e', 'P', IMAGE_MQTT, 'sh', '-c',
                             'mosquitto_sub -h "$H" -u "$U" -P "$P" -t "BSB-LAN/status" -t "BSB-LAN/0/+/+/status" '
                             '-F "%I %t %p"'], stdout=journal, stderr=subprocess.STDOUT, env=env)
    chemin_ji = os.path.join(SORTIE, 'ji.csv')
    neuf = not os.path.exists(chemin_ji)
    f = open(chemin_ji, 'a', newline='', encoding='utf-8')
    w = csv.writer(f)
    if neuf:
        w.writerow(['date', 'uptime_s', 'freeram', 'redemarrage', 'erreur'])
    precedent = None
    print(f'suivi lancé : {SORTIE} (Ctrl+C pour arrêter)', flush=True)
    try:
        while True:
            date = datetime.datetime.now().isoformat(timespec='seconds')
            try:
                ji = lire_ji(auth)
                up = int(ji.get('uptime', 0)) // 1000
                redem = precedent is not None and up < precedent
                w.writerow([date, up, ji.get('freeram'), int(redem), ''])
                if redem:
                    print(f'{date} REDÉMARRAGE détecté (uptime {up} s)', flush=True)
                precedent = up
            except Exception as e:
                w.writerow([date, '', '', '', type(e).__name__])
                print(f'{date} carte injoignable : {type(e).__name__}', flush=True)
            f.flush()
            time.sleep(PERIODE_JI)
    except KeyboardInterrupt:
        pass
    finally:
        mqtt.terminate()
        subprocess.run(['docker', 'stop', 'suivi_endurance_mqtt'], capture_output=True)
        f.close()
        journal.close()
        print('suivi arrêté')


def resume():
    lignes = list(csv.DictReader(open(os.path.join(SORTIE, 'ji.csv'), encoding='utf-8')))
    ok = [l for l in lignes if l['uptime_s']]
    print(f'/JI : {len(lignes)} relevés, {len(lignes) - len(ok)} sans réponse, '
          f'{sum(int(l["redemarrage"] or 0) for l in ok)} redémarrage(s)')
    if ok:
        ram = [int(l['freeram']) for l in ok]
        print(f'  mémoire libre : min {min(ram)} o, max {max(ram)} o, début {ram[0]} o, fin {ram[-1]} o')
        print(f'  du {ok[0]["date"]} au {ok[-1]["date"]}, uptime final {int(ok[-1]["uptime_s"]) / 3600:.1f} h')
    for l in lignes:
        if l['redemarrage'] == '1' or l['erreur']:
            print(f'  {l["date"]} : {"redémarrage" if l["redemarrage"] == "1" else l["erreur"]}')
    p = os.path.join(SORTIE, 'mqtt.log')
    if os.path.exists(p):
        etats, erreurs, n = [], [], 0
        for ligne in open(p, encoding='utf-8', errors='replace'):
            parts = ligne.rstrip('\n').split(' ', 2)
            if len(parts) < 3:
                continue
            n += 1
            d, sujet, val = parts
            if sujet == 'BSB-LAN/status':
                etats.append((d, val))
            elif re.search(r'/(6700|6701|6708)/status$', sujet) and not re.match(r'^(0|65535)\b', val):
                erreurs.append((d, sujet, val))
        print(f'MQTT : {n} messages ; disponibilité : {sum(1 for _, v in etats if v == "offline")} « offline », '
              f'{sum(1 for _, v in etats if v == "online")} « online »')
        for d, v in etats:
            print(f'  {d} {v}')
        print(f'  erreurs PAC (6700, 6701, 6708 non nulles) : {len(erreurs)}')
        for e in erreurs[:20]:
            print('  ', *e)


if __name__ == '__main__':
    resume() if '--resume' in sys.argv else suivre()
