# 12 — Thermostats Home Assistant (circuits CC1 et CC2)

> **Résumé**
> Deux entités `climate` MQTT, une par circuit, définies dans un paquet HA (`alfea/homeassistant/alfea_thermostats.yaml`), à partir des sujets que BSB-LAN publie déjà. Il n'y a aucune modification du firmware.
> Elles affichent la température ambiante, la consigne de confort, le mode du régulateur et l'état du circuit, et pilotent consigne et mode par les sujets `set`. Pour piloter, il faut le firmware `alfea-ecriture` en mode d'écriture 1.
> Contrôles [CONSTATÉ] :
> - essai dans un HA 2026.10.4 jetable : `alfea/tools/test_thermostat_ha.py`, 13/13, aucun avertissement MQTT ;
> - commandes MQTT sur le banc : trames SET justes, 7/7.
> **Sur la PAC réelle, uniquement après la GATE 3.**

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**, **[CHOIX]** (décision prise en l'absence de consigne).

## 1. Pourquoi un paquet YAML plutôt que la discovery ou l'intégration native

| Option | Écartée ou retenue | Raison |
|---|---|---|
| Discovery `climate` publiée par BSB-LAN | écartée | La discovery amont ne connaît que `sensor`, `binary_sensor`, `switch`, `select` et `text` (`BSB_LAN/include/mqtt_handler.h:272-316`). Ajouter un `climate` coûterait environ 60 lignes de plus dans le code amont. |
| Intégration native `bsblan` de HA | écartée | L'utilisateur l'a ignorée (zeroconf, journal J27). Elle interroge en HTTP, sans l'authentification par MQTT déjà en place, et ne gère qu'un circuit [SUPPOSÉ]. |
| Paquet HA `mqtt: climate:` | **retenue** | Pas de code amont. La configuration est versionnée et survit à la perte du broker. Elle se rattache à l'appareil « BSB-LAN » de la discovery (`device.identifiers`). |

## 2. Correspondance avec les paramètres

| Élément HA | CC1 (chambre) | CC2 (salon) | Notes |
|---|---|---|---|
| Température actuelle | 8740 `BSB-LAN/0/32/8740/status` | 8770 `…/0/32/8770/status` | sonde ambiante (Navilink A59) |
| Consigne (lecture et écriture) | 710 `…/0/8/710/status`, `…/set` | 1010 `…/0/10/1010/status`, `…/set` | **consigne de confort** (§3.2) ; envoyée avec 1 décimale (`'%.1f'`) |
| Modes `off` / `auto` / `heat` | 700 = 0 / 1 / 3 | 1000 = 0 / 1 / 3 | réception : 0 → `off`, 1 → `auto`, 2 et 3 → `heat` ; valeur inconnue → `off` |
| Préréglages `eco` / `comfort` | état lu sur 8000 (112-115 → `comfort`, 116 / 119 / 120 → `eco`), commande 700 = 2 / 3 | idem sur 8001, commande 1000 = 2 / 3 | le préréglage suit le régime réel, même en automatique ; `none` en été, hors-gel, protection (2026-11-10, demande utilisateur) |
| Action (`hvac_action`) | 8000 `…/0/28/8000/status` | 8001 `…/0/29/8001/status` | voir §3.3 |
| Disponibilité | `BSB-LAN/status` (`online` / `offline`) | idem | message de dernière volonté de BSB-LAN (`mqtt_handler.h:447`) |

Sujets [CONSTATÉ] relevés sur le broker. Le format de commande est `BSB-LAN/<appareil>/<catégorie>/<paramètre>/set` (`mqtt_handler.h:582-600`). Les états énumérés arrivent sous la forme « `n - Texte` » (`mqtt_mode = 1`). Les modèles n'en lisent que le nombre : ils ne dépendent donc ni de la langue ni de l'encodage.

## 3. Comportement à connaître

### 3.1 Les modes du thermostat sont des modes du régulateur
- `heat` (ou le préréglage `comfort`) met le mode **Confort permanent** (700 = 3). Le programme horaire est ignoré jusqu'au retour en `auto`.
- Le préréglage `eco` met le mode **Réduit permanent** (700 = 2).
- `off` met le mode **Protection** (700 = 0). Ce n'est **pas un arrêt** : le régulateur garde la consigne hors-gel (714) [SUPPOSÉ, documentation RVS].
- `auto` (700 = 1) suit les programmes horaires 501-507 (CC1) et 521-527 (CC2).

### 3.2 La consigne affichée est celle de confort
Une entité `climate` n'a qu'un seul sujet de consigne. Le curseur agit donc toujours sur 710 (CC1) ou 1010 (CC2).

En période réduite (`auto` hors plage horaire, ou `eco`), la consigne réellement appliquée est 712 ou 1012. Ces valeurs restent réglables par leurs propres entités, issues de la discovery. La consigne en vigueur se lit sur 8741 et 8771 (« consigne ambiante actuelle »).

### 3.3 Action
8000 et 8001 donnent le **régime du circuit**, pas la marche du compresseur. La correspondance est [SUPPOSÉ] :

| Codes | Action HA |
|---|---|
| 103-106 (restreint), 111-114 (optimisation, chauffage accéléré, Confort), 116 (réduit) | `heating` |
| 25 (Arrêt), 162 (Chauffage à l'arrêt) | `off` |
| tout le reste : été (118), protections hors-gel, Eco de jour… | `idle` |

À recaler sur la PAC réelle [À VÉRIFIER] : relever 8000 et 8001 pendant une période confort, une période réduite et un arrêt d'été.

### 3.4 Limites et rafraîchissement
- **Plage du curseur** : 12-26 °C par pas de 0,5 °C [CHOIX]. Le régulateur a ses propres bornes : consigne de confort entre 712 et 716 [À VÉRIFIER sur la PAC]. BSB-LAN ne vérifie pas la plage avant l'écriture.
- **Rafraîchissement** :
  - toutes les 60 s (`log_interval`) ;
  - après une commande, BSB-LAN relit le paramètre et republie l'état [CONSTATÉ sur le banc] ;
  - HA n'est pas optimiste : il n'affiche une nouvelle valeur qu'après sa publication par BSB-LAN.
- **En lecture seule**, avec le firmware `alfea` ou le mode d'écriture 0, la commande est refusée par BSB-LAN : aucune trame SET (journal J28). Le thermostat reste sur l'état réel.
- **Navilink A59** : un réglage fait sur le boîtier apparaît dans HA au plus tard 60 s après si l'A59 modifie 710 ou 1010. S'il applique un décalage local, il n'apparaît pas [À VÉRIFIER].
- **Remplacement du SuperMini** : `device.identifiers` (`BSB-LAN-DC067567DA2C`) dérive de l'adresse MAC. Il faut alors l'aligner sur le nouvel identifiant de la discovery, faute de quoi les thermostats forment un appareil à part.

## 4. Installation dans Home Assistant (HA OS)

1. Copier `alfea/homeassistant/alfea_thermostats.yaml` dans `/config/packages/` (add-on File editor ou Samba).
2. Dans `/config/configuration.yaml`, ajouter si ce n'est pas déjà fait :
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. Aller dans Outils de développement > YAML > Vérifier la configuration, puis redémarrer HA. Le rechargement « Entités MQTT configurées manuellement » suffit pour les modifications suivantes.
4. Deux entités apparaissent dans l'appareil BSB-LAN : `climate.bsb_lan_thermostat_cc1_salon_cuisine` et `climate.bsb_lan_thermostat_cc2_chambres` (noms affichés « Thermostat chambre » et « Thermostat salon » depuis la correction du 2026-11-09 : CC1 = chambre, CC2 = salon ; les `entity_id` déjà créés gardent l'ancien libellé, à renommer dans HA si souhaité) [SUPPOSÉ : identifiants dérivés du nom de l'appareil ; dans le HA jetable, l'appareil n'avait pas de nom propre]. Ajouter ensuite une carte « Thermostat » au tableau de bord.
5. Pour piloter : firmware `alfea-ecriture` et mode d'écriture 1 (`/C`, ou `/JW {"Parameter":33,"Value":"1"}`). Seules les lignes de `alfea/params/ecriture.txt` sont modifiables.

## 5. Contrôles réalisés

| Contrôle | Moyen | Résultat |
|---|---|---|
| Rendu des modèles (états 0-3, `None`, codes 114/116/118/25, consignes) | Jinja2 hors ligne, 2 × 27 cas | [CONSTATÉ] tout juste |
| Chaîne MQTT → BSB-LAN → bus (SuperMini `alfea-ecriture`, mode 1, simulateur) | publication sur `…/710/set` `21.0`, `…/700/set` `3`/`2`/`1`, `…/1010/set` `19.5`, `…/1000/set` `0`/`1` | [CONSTATÉ] SET `01 05 40`, `01 03`, `01 02`, `01 01`, `01 04 e0`, `01 00`, `01 01` ; états relus et republiés |
| Paquet chargé par HA 2026.10.4 (jetable, Mosquitto de test) | `python -I alfea/tools/test_thermostat_ha.py` | [CONSTATÉ] 13/13 : 2 entités, modes, préréglages, bornes, action, services → sujets `set` attendus, retour d'état, `None` → inconnu, `offline` → indisponible ; 0 avertissement MQTT |
| `check_config` de HA | conteneur | sans valeur probante : il ne valide pas le schéma MQTT (un mode invalide passe, contrôle négatif) |
| HA réel de l'utilisateur | — | **non fait** : installation par l'utilisateur (§4) |

## 6. Évolution prévue : thermostat piloté par la dérogation temporaire (demande du 2026-11-10)
Objectif de l'utilisateur : le thermostat HA se comporte comme l'afficheur de la PAC et les A59.
- **Consigne affichée** = consigne en vigueur, 8741 (chambre) / 8771 (salon), et non plus la consigne de confort 710 / 1010.
- **Consigne modifiée dans HA** = **dérogation temporaire** (701.3 écart, 701.4 durée ; 1001.x pour le salon, objets cachés #829), qui prend fin d'elle-même, et non plus l'écriture de 710 / 1010.

Principe envisagé [SUPPOSÉ, à confirmer par la capture] : la commande du thermostat publie sur un sujet interne ; une automatisation calcule l'écart (consigne demandée − consigne de base, c'est-à-dire 8741 moins l'écart de dérogation éventuellement en cours), puis écrit la durée et l'écart. Les consignes de confort et de réduit restent réglables par leurs entités.

Préalables, dans l'ordre :
1. **Capture sur le bus** (console USB) d'une dérogation faite sur un A59 puis sur l'afficheur : objets écrits, format de l'écart et de la durée, ordre des écritures, effet sur 8741 et 8000, fin de dérogation.
2. 701, 701.3, 701.4, 1001, 1001.3, 1001.4 ajoutés à la liste HA en lecture.
3. Ajout à la liste blanche d'écriture avec l'accord de l'utilisateur (niveau d'accès 6, 08a I5), puis paquet YAML et automatisation.

Points à vérifier : pas d'écriture en mémoire permanente à chaque dérogation ; comportement si la plage horaire change pendant la dérogation ; pas de bouclage entre la consigne affichée et la commande.

### 6.1 Capture du 2026-11-11 [CONSTATÉ]
Dérogation faite sur l'A59 de la chambre, de 18,0 à 19,5 °C (période réduite) ; console USB, firmware alfea-complet. L'A59 passe par l'afficheur (DSP1, adresse 0x0A), qui écrit dans le régulateur (0x00) :

| # | Écriture (SET, DSP1 -> régulateur) | Données | Sens |
|---|---|---|---|
| 1 | 701 `0x053D1A83` = 1 « ... » | `01 01` | état neutre (préparation) |
| 2 | 701.3 `0x053D1AA6` = 1,5 °C | `01 00 60` | écart, VT_TEMP (/64), octet d'activation 01 |
| 3 | 701.4 `0x053D1AA5` = 24 h | `01 18` | durée ; l'A59 n'a pas de réglage de durée et envoie 24 h |
| 4 | 701 = 2 « Plus chaud » | `01 02` | activation (0 plus froid, 1 neutre, 2 plus chaud) |
| 5 | 1001 `0x063D1A83` = 1 « ... » | `01 01` | CC2 remis au neutre |

Chaque écriture est acquittée (ACK). 8741 passe de 18,0 à 19,5 °C ; 701.4 et 1001.4 relues à 24 h. BSB-LAN publie 701 et 701.3 sur MQTT dès le passage des trames (écoute passive, `print_telegram.h:1319-1329`).
Deuxième essai (même jour, ~08:50) [CONSTATÉ] :
- **Salon, « plus froid » 1 °C pendant 1 h** : 1001 = 1, 1001.3 = 1,0 °C, 1001.4 = 1 h, puis **1001 = 0 « Plus froid »** ; 8771 passe de 18,0 à 17,0 °C. L'écart reste **positif** : le sens est donné par 701 / 1001 (0 plus froid, 2 plus chaud).
- **Annulation (chambre)** : une seule écriture, **701 = 1 « ... »** ; 8741 revient aussitôt de 19,5 à 18,0 °C. 701.3 (1,5 °C) et 701.4 (24 h) restent mémorisés : seul 701 dit si une dérogation est active.
- **Fin de la dérogation du salon** (1 h, lancée vers 08:48) : vers 09:42, **sans aucune trame SET**, le régulateur remet lui-même 1001 à 1 « ... » et 8771 revient à 18,0 °C. 1001.4 est resté à 1 h tout du long : c'est la **durée réglée, pas un compte à rebours** (le temps restant n'est pas lisible dans la liste).
Reste à vérifier : fin anticipée au changement de plage horaire, écriture en mémoire permanente ou non.
Séquence à reproduire depuis HA : 701 = 1, 701.3 = écart (positif), 701.4 = durée, 701 = 2 (plus chaud) ou 0 (plus froid) ; annulation : 701 = 1 ; avec l'accord de l'utilisateur pour la liste blanche (08a I5).

### 6.2 Réalisation (2026-11-11) [CONSTATÉ sur HA jetable, à confirmer sur la PAC]
- Firmware : 701, 701.3, 701.4, 1001, 1001.3, 1001.4 dans la liste HA et la liste blanche (accord de l'utilisateur) ; 701 et 1001 lus chaque minute. 701.4 / 1001.4 ne sont pas interrogés : la durée est écrite avant chaque activation et publiée au passage.
- Paquet `alfea/homeassistant/alfea_thermostats.yaml` : consigne affichée = 8741 / 8771 ; commande publiée sur `alfea/thermostat/cc1|cc2/consigne` et traitée par l'automatisation `pac_thermostat_derogation` (séquence de l'A59, écart arrondi au 0,5 °C, durée `input_number.pac_duree_derogation`, 3 h au démarrage de HA ; retour à la consigne du programme = annulation). Aucune écriture tant que HA n'a pas reçu l'état de dérogation et la consigne en vigueur.
- Compte à rebours : `sensor.pac_chambre_fin_de_derogation` / `sensor.pac_salon_fin_de_derogation` (horodatage). Le régulateur ne publie pas le temps restant (701.4 constant) et l'afficheur le calcule lui-même [SUPPOSÉ : aucun objet interrogé par l'afficheur ne varie pendant la dérogation] ; HA note la fin quand il constate la dérogation.
- Essai : `python -I alfea/tools/test_thermostat_ha.py` (HA 2026.10.4 jetable), « TOUT OK » : séquences plus chaud, plus froid depuis une dérogation en cours, annulation, compte à rebours, préréglages, modes, indisponibilité.

### 6.3 Premier essai sur la PAC (2026-11-11, ~10:39) [CONSTATÉ]
Salon passé en confort permanent depuis HA (1000 = 3, 8771 = 22,5 °C), puis consigne 24,0 °C demandée au thermostat : 1001.3 = 1,5 °C, 1001.4 = 3 h, 1001 = 2 écrits et acquittés, **8771 = 24,0 °C**. L'écriture initiale 1001 = 1 a échoué à l'envoi (« set failed », `bus->Send` différent de BUS_OK, aucune trame émise : collision probable avec l'afficheur, BSB-LAN ne réessaie pas) : l'automatisation attend désormais la confirmation de l'écart et de l'état final (8 s) et réécrit une fois sinon.
**Un changement de mode du circuit annule la dérogation** : retour en automatique (1000 = 1), le régulateur remet lui-même 1001 à 1 et 8771 revient à 18,0 °C (période réduite).

## 7. Boost ECS (forçage 5072)
Capture du 2026-11-11 [CONSTATÉ] : l'afficheur écrit une seule trame, **5072 = 1 « Rechargement »** (`DC 8A 00 0D 03 05 31 05 73 01 01`). Effets dans la minute : consigne ECS en vigueur 40 -> 55 °C (consigne nominale 1610), 8003 = 93 « Push, Consigne nominale », pompe ECS 8820 activée, compresseur en marche.
Dans HA : entité de la discovery « ECS - Forçage ECS » (liste « ... » / « Rechargement »), 5072 dans la liste blanche (accord de l'utilisateur) et lu chaque minute.
Fin [CONSTATÉ] : lancé vers 09:44, ballon de 52 à **55,1 °C** ; vers 10:12 le régulateur remet **lui-même 5072 à 0** « ... », sans trame SET, la consigne en vigueur revient à 40 °C (consigne réduite hors plage) et 8003 passe à 17 « Retard à l'arrêt activ » (post-circulation de la pompe ECS), compresseur arrêté. Le boost est donc une charge unique jusqu'à la consigne nominale.
