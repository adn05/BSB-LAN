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
| Préréglages `eco` / `comfort` | 700 = 2 / 3 | 1000 = 2 / 3 | `none` en protection ou en automatique |
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
