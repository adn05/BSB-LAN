# 04 — Intégration Home Assistant

> **Résumé**
> BSB-LAN publie chaque paramètre interrogé sur `<prefix>/<dest>/<cat>/<param>/status` (QoS 1, *retain*) et reçoit des commandes sur `…/set`, `…/inf`, `…/poll`. L'auto-discovery HA est implémentée (`/M1!0` ou automatiquement quand le broker a perdu la session) : chaque paramètre devient une entité `sensor`, `binary_sensor`, `switch`, `select` ou `text`, rattachée à un *device* « BSB-LAN ».
> Limites : pas d'entité `climate`/`water_heater`/`number`, découverte de **toute** la table (ou des seuls paramètres journalisés), noms techniques, `mqtt_mode` doit valoir 1 pour que les gabarits fonctionnent.
> Recommandation : **MQTT + discovery**, restreinte aux paramètres journalisés (`CF_LOGMODE_MQTT_ONLY_LOG_PARAMS`), avec `mqtt_unit_set = CF_MQTT_UNIT_HOMEASSISTANT` et `replaceDisabled = "None"`. L'intégration HA « BSB-LAN » (API JSON) reste une solution de secours.

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**.

---

## 1. MQTT

### 1.1 Connexion — `mqtt_connect()` (`BSB_LAN/include/mqtt_handler.h:362-504`)

| Élément | Valeur | Référence |
|---|---|---|
| Client | PubSubClient (version embarquée, publication en QoS 1), tampon de 2 048 o, keep-alive de 120 s | `mqtt_handler.h:398-400`, `src/PubSubClient/src/PubSubClient.h:544` |
| Broker | `mqtt_broker_addr` = `hôte[:port]`, port 1883 par défaut. **Tout autre port active TLS** (bundle de CA) | `:365-372`, `:384-397` |
| Client ID | `MQTTDeviceID`, sinon `BSB-LAN-XXXXXX` (3 derniers octets de la MAC) | `:36-47` |
| LWT | `<prefix>/status` = `offline` (retain), puis `online` à la connexion | `:170-176`, `:430`, `:461` |
| Message de naissance | `<prefix>/meta/<clientID>` = `mac=… ip=… fw=… build=…` (retain) | `:439-451` |
| Abonnement | `<prefix>/#` en QoS 1 | `:455-460` |
| Reconnexion | essai toutes les 10 s au plus (le commentaire dit 1 s) | `:404-414` |
| Republication de la discovery | si `sessionPresent() == false`, par exemple quand le broker a redémarré sans persistance | `:464-496` |

### 1.2 Topics et payloads publiés — `mqtt_sendtoBroker()` (`mqtt_handler.h:49-144`)

Topic : `<MQTTTopicPrefix>/<dest>/<cat>/<param>/status`, par exemple `BSB-LAN/0/51/8700/status` (`:57`). Le format dépend de `mqtt_mode` :

| `mqtt_mode` | Payload | Exemple |
|---|---|---|
| 1 (texte) | valeur seule, ou `"<code> - <libellé>"` pour les ENUM/ONOFF/YESNO/BIT/date | `5.0`, `1 - Automatique` |
| 2 (JSON) | `{"<clientID>":{"status":{"8700!0":"5.0"}}}` | |
| 3 (JSON riche) | `{"BSB-LAN":{"device":0,"parameter":8700,"name":"…","value":"5.0","desc":"","unit":"°C","error":0}}` | |

En cas d'erreur de lecture, la valeur publiée est `replaceDisabled` (« --- » par défaut) (`:58-60`).

### 1.3 Quand publie-t-on ?

1. **Périodiquement** : toutes les `log_interval` secondes, `loop()` interroge chaque entrée de `log_parameters[40]` (`BSB_LAN/BSB_LAN.ino:7002-7033`).
2. **À chaque lecture**, quelle qu'en soit l'origine (page web, `/JQ`, MQTT `poll`), si `CF_LOGMODE_MQTT` est actif sans `CF_LOGMODE_MQTT_ONLY_LOG_PARAMS` (`BSB_LAN/BSB_LAN.ino:3994-3996`, `include/mqtt_handler.h:146-158`).
3. Les trames diffusées (INF) **ne sont pas** publiées directement ; seuls les compteurs virtuels 20000-20005 en tirent parti, au moment où on les lit.

### 1.4 Commandes entrantes — `mqtt_callback()` (`mqtt_handler.h:553-684`)

| Topic | Payload | Effet |
|---|---|---|
| `<prefix>/<dest>/<cat>/<param>/set` | valeur | `set(param, valeur, SET)` → **soumis à la lecture seule**, puis relecture et publication |
| `<prefix>/<dest>/<cat>/<param>/inf` | valeur | `set(…, INF)` (température ambiante 10000…) |
| `<prefix>/<dest>/<cat>/<param>/poll` | — | lecture et publication |
| `<prefix>/poll` | `8700,8743!0,/0/51/8700` | lecture groupée |
| `<prefix>` (hérité) | `S700=1`, `I10000=21.5`, `8700` | équivalent des commandes URL |

Le `…/status` est ignoré pour éviter de boucler sur ses propres messages (`:587-588`). [CONSTATÉ] Toutes les écritures passent par `set()`, donc par `programIsreadOnly()` (`BSB_LAN/BSB_LAN.ino:2919-2922`). Le MQTT ne contourne pas la lecture seule, contrairement à `/JY` et `/Y` (cf. 03).

## 2. Auto-discovery Home Assistant — `mqtt_send_discovery()` (`mqtt_handler.h:178-344`)

### 2.1 Déclenchement

- Manuel : `/M1!<dest>` pour créer, `/M0!<dest>` pour supprimer (payload vide) (`BSB_LAN/BSB_LAN.ino:4997-5045`).
- Automatique : à la (re)connexion, si le broker n'avait plus de session (`mqtt_handler.h:464-496`).

### 2.2 Périmètre

La fonction parcourt **toute** `active_cmdtbl`, sauf les paramètres PPS en BSB, 19999 et les numéros > 20999 (`:188-197`). Si `CF_LOGMODE_MQTT_ONLY_LOG_PARAMS` est actif, elle **ne garde que les paramètres de `log_parameters[]`** (`:197-205`). Avec une liste RVS21 complète (plusieurs centaines d'entrées [SUPPOSÉ]), la discovery créerait des centaines d'entités et chaque publication coûterait jusqu'à 2 Ko de payload : il faut absolument filtrer.

### 2.3 Messages produits

Topic : `homeassistant/<component>/BSB-LAN/<param>-<fam>-<var>-<serial>/config` (les `.` sont remplacés par `-`) (`:215`, `:324-326`).

Payload (abrégé), d'après `:216-322` :
```json
{"~":"BSB-LAN/0/51/8700",
 "unique_id":"8700-211-127-<serial>",
 "state_topic":"~/status",
 "availability_topic":"BSB-LAN/status",
 "icon":"mdi:thermometer","device_class":"temperature",
 "unit_of_measurement":"°C","state_class":"measurement",
 "name":"00-51 Diagnostic consommateurs - 8700 - Température extérieure",
 "device":{"name":"BSB-LAN","identifiers":"BSB-LAN-<MAC>","manufacturer":"bsb-lan.de","model":"5.1.34"}}
```
(Valeurs de famille et variante données à titre d'exemple pour 211/127 ; le numéro de catégorie dépend de la liste spécifique.)

### 2.4 Règles de typage des entités [CONSTATÉ]

| Condition | Composant HA | Détails |
|---|---|---|
| lecture seule (ou `VT_CUSTOM_*`) et `VT_ONOFF`/`VT_YESNO` | `binary_sensor` | `value_template` : `'OFF' if value.split(' - ')[0] == '0' else 'ON'` |
| lecture seule, autres types | `sensor` | unité, `state_class: measurement` si `DT_VALS` (sauf h et kWh) |
| modifiable, ONOFF/YESNO | `switch` | `command_topic: ~/set`, `payload_on "1"`, `state_on "1 - On"` |
| modifiable, ENUM | `select` | options `"<code> - <libellé>"` générées depuis la chaîne ENUM, plus `"65535 - ---"` |
| modifiable, autres types | `text` | `command_template {{value}}` (les consignes numériques **ne sont pas** des entités `number`) |

`device_class` (temperature, humidity, power, energy, pressure…) n'est ajouté que si `mqtt_unit_set == CF_MQTT_UNIT_HOMEASSISTANT` (`:222-265`).

### 2.5 Limites et points d'attention

| # | Constat | Conséquence |
|---|---|---|
| L1 | Les `value_template` et `state_on` supposent un payload en **texte (`mqtt_mode` = 1)**. En mode 2 ou 3, le state est un JSON non décodé | `mqtt_mode` = 1 obligatoire [SUPPOSÉ, déduit du code] |
| L2 | Paramètre désactivé publié comme « --- » : un `sensor` numérique avec `state_class` produit des erreurs dans HA | `replaceDisabled = "None"`, comme le recommande `BSB_LAN/BSB_LAN_config.h.default:214` |
| L3 | Le mode lecture seule est évalué **au moment de la discovery** (`decodedTelegram.readwrite`) : en lecture seule, tout devient `sensor`/`binary_sensor` | cohérent avec la mission. Si on active l'écriture plus tard, il faut relancer `/M1!0` |
| L4 | Pas d'entité `climate`/`water_heater` | un thermostat HA « joli » demandera un *template* ou un paquet YAML côté HA (proposé en Phase 3) |
| L5 | `mqtt_send_discovery()` appelle `MQTTPubSubClient->connected()` sans tester le pointeur nul (`:331`) | `/M1` appelle d'abord `mqtt_connect()` (`BSB_LAN/BSB_LAN.ino:5019`), qui crée le client, **sauf** en TLS (port ≠ 1883) sans heure valide : `mqtt_handler.h:388-392` sort avant le `new`, d'où un déréférencement de nullptr possible. Sans objet si l'on compile avec `NO_TLS` [CONSTATÉ par lecture] |
| L6 | Payload et topic de 2 128 o **sur la pile** de `loop()`, profondeur d'appel `mqtt_callback → set → query → LogToMQTT → mqtt_sendtoBroker` | à surveiller sur le C3 (pile `loopTask` de 8 Ko par défaut [SUPPOSÉ : valeur par défaut d'arduino-esp32]) |
| L7 | Noms d'entités longs, contenant la catégorie et le numéro | lisibles par un technicien. Renommage possible dans HA (`unique_id` stable) |

## 3. Les autres voies d'intégration

| Voie | Principe | + | − |
|---|---|---|---|
| **MQTT + discovery (natif)** | décrit ci-dessus | push, LWT/disponibilité, aucun YAML, fonctionne même si HA redémarre (retain) | entités génériques, typage limité |
| Intégration HA « BSB-LAN » (core, `bsblan`) | HA interroge l'API JSON `/JQ`, `/JI`… en HTTP | entités `climate` et `water_heater` | elle vise un **jeu fixe de paramètres** (consignes CC1, ECS…) dont les numéros peuvent différer sur RVS21 **[À VÉRIFIER]**, polling, pas de push |
| REST/`command_line` dans HA | `rest:` sur `/JQ=…` | contrôle total | YAML à maintenir, polling |

## 4. Recommandation

**MQTT avec auto-discovery** comme voie principale, configuré ainsi :
- `LoggingMode = CF_LOGMODE_MQTT | CF_LOGMODE_MQTT_ONLY_LOG_PARAMS` : seuls les paramètres listés sont découverts et publiés ;
- `log_parameters[]` = la liste Alféa validée en Phase 3 (≈ 15-25 entrées), `log_interval` = 30 à 60 s ;
- `mqtt_mode = 1`, `mqtt_unit_set = CF_MQTT_UNIT_HOMEASSISTANT`, `replaceDisabled = "None"`, broker local sur le port 1883 → compiler avec `NO_TLS` (gain de 56 Ko rien que pour le bundle de CA) ;
- en complément (Phase 3) : un paquet YAML HA facultatif pour composer une entité `climate` à partir des entités découvertes.

L'API JSON reste compilée (elle coûte peu, cf. 05) pour le diagnostic et pour un éventuel usage de l'intégration `bsblan`.
