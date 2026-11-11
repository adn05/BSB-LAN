# 11 — Mise en service sur la PAC (GATE 3, essai T3 en lecture seule)

> **Résumé**
>
> Note (2026-11-11) : les renvois aux docs 01 à 08a, 14 et 15, aux cibles `alfea-ecriture` / `alfea-complet` et aux outils d'essai (simulateur, pont, HA jetable) visent des éléments retirés au ménage du 2026-11-11 ; ils restent consultables dans l'historique de la branche `alfea-extensa`. Il n'y a plus qu'un firmware, `alfea` (README_docker).
> **GATE 3 validée par l'utilisateur le 2026-11-09.**
> Procédure du premier raccordement de la carte principale rev A (isolée) sur X86 du RVS21 de l'Alféa Extensa Duo A.I., **en lecture seule**. Elle ne s'applique qu'**après validation explicite de la GATE 3** par l'utilisateur (00 §2.5).
> Prérequis : banc réussi (09 §10), CL+ identifié sur X86, firmware `alfea` (lecture seule).
> Critères de réussite (08 §6, T3) :
> - aucune trame émise autre que des requêtes de lecture `QUR` et la requête d'identification `QINF` diffusée par BSB-LAN au démarrage ;
> - IHM sans alarme ;
> - valeurs cohérentes avec l'IHM ;
> - famille et variante (6225/6226) relevées.
> Arrêt immédiat, en débrochant la fiche de J1, au moindre défaut de l'IHM ou de la PAC.

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**.

---

## 1. Prérequis (à cocher avant de descendre à la chaufferie)

| # | Prérequis | Référence | État |
|---|---|---|---|
| P1 | Banc de la carte reçue réussi : isolation, 3,3 V, V(DATA) ≥ 3,1 V, bus simulé (D1 allumée au repos, écho des trames, niveau bas ≈ 1,5 V) | 09 §10 | à faire ou à me transmettre |
| P2 | SuperMini enfiché **retourné** (erratum rev A) ; s'il a été alimenté une fois à l'endroit, contrôle du 3,3 V, de D5 et de R10 | 09 §10.1 | à confirmer |
| P3 | Firmware **`alfea`** (lecture seule, liste HA 211/127), compilé avec `alfea/config/alfea_secrets.h` : `sh docker/compiler.sh alfea`, puis flash | README_docker §2 | **fait le 2026-11-09** : image complète flashée (configuration NVS effacée, la variante `alfea-ecriture` des essais est remplacée), démarrage contrôlé en console [CONSTATÉ] : BSB-LAN 5.1.34, bus BSB, WiFi (192.168.30.202, `bsb-lan-alfea`), MQTT connecté, famille 0 / variante 0 faute de bus |
| P4 | X86 : 11,5 V entre 1 et 2, 11,6 V entre 2 et 3 [CONSTATÉ] ; **signe des lectures et borne qui porte le trafic** encore à vérifier | 09 §8 | à faire (§2) |
| P5 | Alimentation de la carte : **chargeur USB 5 V ≥ 1 A** sur l'USB-C, rien n'est prélevé sur la PAC | 09 §4 | |
| P6 | Câble : paire torsadée, 2 conducteurs de 0,5 à 1,5 mm² ; fiche JJ1 (HC-JXDZK-3.5-2P) | 09 §5 | |

## 2. Identification de CL+ sur X86 (PAC sous tension, IHM allumée, rien de branché)

Précautions : 230 V à proximité sur la carte de régulation ; pointes isolées ; ne rien débrocher sous tension.

1. Multimètre en continu, calibre 20 V, **COM sur la borne 2**. Mesurer la borne 1, puis la borne 3 : les deux lectures doivent être **positives** (≈ 11,5 V).
2. Multimètre en **alternatif**, calibre le plus bas (mV ou 2 V), COM sur 2. Mesurer 1, puis 3. **La borne qui montre une tension alternative est CL+** : le trafic du bus y crée une composante alternative, alors que G+ reste lisse [SUPPOSÉ : le RVS21 émet sans appareil d'ambiance ; l'IHM Atlantic est l'appareil 10 sur le bus (08a)].
3. Si aucune des deux ne montre de tension alternative, on garde la borne 1, CL+ selon la doc BSB-LAN (`docs/en/supported_heating_systems.md:25`). Le premier essai le confirmera par la LED D1 (§4, étape 3). Une erreur ne détruit rien : D2 bloque l'inversion, et sur G+ D1 reste allumée sans clignoter.

## 3. Raccordement (PAC hors tension)

1. **Couper la PAC** au disjoncteur de la régulation ou de l'unité. Vérifier que l'IHM est éteinte.
2. **Débrocher** la fiche verte de X86 (bornier à vis débrochable, photo `images/x86_alfea.jpeg`) pour travailler hors de la PAC.
3. Serrer le fil de **CL+** sous la vis de la borne identifiée au §2 (1 par défaut), et le fil de **CL-** sous la vis de la borne **2**. Ne rien raccorder sur 3 (G+) ni sur B1, B2 ou M.
4. Côté carte : CL+ sur **J1-1**, CL- sur **J1-2**, dans la fiche JJ1.
5. Rembrocher la fiche de X86, puis enficher JJ1 sur J1. Le câble de la carte ne doit pas tirer sur le bornier.
6. Carte posée hors de tout contact avec des pièces métalliques, USB-C relié au chargeur 5 V. Le boîtier peut attendre la fin de l'essai.

## 4. Premier essai, en lecture seule

| Étape | Action | Attendu | Si ce n'est pas le cas |
|---|---|---|---|
| 1 | Alimenter la carte (chargeur USB) **avant** la PAC | BSB-LAN démarre et rejoint le WiFi ; D1 éteinte (pas de bus) | vérifier le WiFi (`alfea_secrets.h`) |
| 2 | Remettre la PAC sous tension | l'IHM redémarre normalement, **sans alarme** | **débrocher JJ1**, noter le code d'erreur |
| 3 | Observer D1 | **allumée, avec de brefs clignotements** (trafic IHM ↔ régulateur) | éteinte : polarité inversée ou mauvaise borne. Fixe, sans clignotement : G+ au lieu de CL+. Dans les deux cas, couper la PAC, corriger, recommencer |
| 4 | Attendre **1 min** : sans bus au démarrage, BSB-LAN relance la détection du régulateur chaque minute (`BSB_LAN/BSB_LAN.ino:7466-7470`) ; on peut aussi débrancher et rebrancher le chargeur. Puis interface web : `http://192.168.30.202/6220-6229` (ou `http://bsb-lan-alfea.local/`) | 6224 « RVS21.831F/127 » ou proche ; **noter 6225 (famille) et 6226 (variante)** ; 6227 (version OV) | si aucune réponse : relever le journal USB (§5) |
| 5 | Si 6225/6226 = **211/127** | la liste HA s'affiche ; comparer à l'IHM : température extérieure, températures de départ, consignes CC1/CC2, ECS, mode | si 6225/6226 ≠ 211/127 : **ne pas aller plus loin**, faire un dump `/QD` et me le transmettre (08a §6, I9) |
| 6 | Home Assistant | entités découvertes (doc 12), disponibilité, valeurs identiques à l'interface web | vérifier Mosquitto et l'utilisateur `bsblan` |
| 7 | Laisser tourner 1 h | IHM toujours sans alarme ; aucun redémarrage de la carte ; RSSI ≥ −70 dBm | noter l'heure et le symptôme |

**Lecture seule** : le firmware `alfea` refuse toute écriture (SET, INF). Ne **pas** flasher `alfea-ecriture` à ce stade. L'écriture fera l'objet d'un accord séparé, avec sauvegarde des programmes (08 §4, T5).

## 5. Journal et mesures à me transmettre

- 6220 à 6229 (copie de la page web) ;
- l'état de D1 aux étapes 1 à 3, et le comportement de l'IHM ;
- quelques valeurs comparées entre l'IHM et BSB-LAN ;
- si possible, le journal série USB du SuperMini pendant 2 minutes (`python alfea/tools/flasher.py console`), pour vérifier qu'aucune trame autre que `QUR` et la `QINF` d'identification (0x053D0064) n'est émise. La carte est isolée : n'importe quel PC convient ;
- RSSI du WiFi (page d'accueil de BSB-LAN) à l'emplacement définitif.

Ces relevés lèvent les questions ouvertes Q2 (brochage et polarité de X86), I1 et I9 (08a), et ouvrent l'endurance T4 (72 h).

## 6. Retour arrière

Débrocher JJ1 : la PAC revient exactement dans son état d'origine (rien n'a été modifié dans la régulation, aucune écriture n'a été faite).

## 7. Essai d'endurance de 48 h (T4, ramené de 72 h à 48 h par l'utilisateur)

**Avant** :
1. Analyse de la nuit avec la console USB (2026-11-09 au 10) : nombre de plantages, reconnexions WiFi et RSSI (08a §6.1).
2. Si possible, couverture WiFi améliorée : RSSI ≥ −70 dBm, contre −77 à −83 dBm relevés à la mise en service.
3. Essai lancé le 2026-11-11 à 14:42 en usage normal (choix de l'utilisateur) : écritures autorisées, console USB gardée pour obtenir la trace d'un éventuel plantage.

**Suivi**, sur le PC de développement allumé pendant 48 h, depuis la racine du dépôt :

    python alfea/tools/suivi_endurance.py            # Ctrl+C à la fin
    python alfea/tools/suivi_endurance.py --resume   # bilan

L'outil est passif vis-à-vis de la PAC : aucune trame supplémentaire sur le bus.
- Il interroge `/JI` toutes les 5 min. Ce sont des informations internes de BSB-LAN : `uptime`, mémoire libre.
- Il s'abonne au broker MQTT : disponibilité `BSB-LAN/status`, et valeurs publiées par BSB-LAN chaque minute, dont 6700, 6701 et 6708.
- Sorties dans `alfea/build/endurance/` (`ji.csv`, `mqtt.log`, ignorées par git).

**Critères** (08 §6, T4) :

| Critère | Seuil |
|---|---|
| Redémarrages (uptime qui recule) | 0 |
| Mémoire libre | stable : pas de baisse continue sur 48 h |
| Disponibilité MQTT | aucun « offline » hors coupure volontaire |
| Erreurs PAC (6700, 6701, 6708) | aucune valeur non nulle imputable à la carte ; IHM sans erreur de communication |
| Valeurs dans HA | continues, plausibles (comparaison ponctuelle avec l'IHM) |

En cas de redémarrage, rebrancher la console USB pour obtenir la trace (`python alfea/tools/flasher.py console`), puis la décoder (08a §6.1).

