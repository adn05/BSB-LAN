# 05 — Inventaire des fonctionnalités et coût mémoire

> **Résumé**
> J'ai compilé l'amont **non modifié** pour ESP32-C3 (arduino-esp32 3.3.12, `min_spiffs`, CDC-on-boot) : image de **1 610 749 o (81 % de la partition app)** et **65 624 o de RAM statique**. Les coûts ci-dessous viennent du `.map` de ce build.
> Le code propre de BSB-LAN ne représente que ≈ 322 Ko de flash, dont ≈ 129 Ko de chaînes fusionnées. L'essentiel de l'image est le framework : WiFi + lwIP + WPA ≈ 470 Ko, mbedTLS ≈ 245 Ko, mDNS, LittleFS, FAT/SD, WebServer…
> Les plus gros gains à attendre : TLS (bundle de 56 Ko + client TLS ≈ 120 Ko [estimé]), LittleFS/SD/FAT (≈ 70 Ko), `heating_cmdtbl` (**16 Ko de RAM**), I²C/RMT/ETH (≈ 30-50 Ko [estimé]).
> Pour l'Alféa, il faut : bus BSB, décodage, WiFi, MQTT + discovery, config web minimale, OTA, mDNS (optionnel). Le reste est supprimable.

Conventions : **[MESURÉ]** = valeur lue dans `BSB_LAN.ino.map` du build de mesure (méthode en annexe) ; **[ESTIMÉ]** = ordre de grandeur non mesuré directement, à confirmer par un build différentiel en Phase 4.

---

## 1. Répartition globale (build C3 amont) [MESURÉ]

| Section de sortie | Taille |
|---|---|
| `.flash.text` (code en flash) | 1 135 614 o |
| `.flash.rodata` | 337 852 o |
| `.iram0.text` (code en IRAM) | 67 214 o |
| `.eh_frame` | 53 148 o |
| `.dram0.data` (RAM initialisée, copiée depuis la flash) | 16 325 o |
| `.dram0.bss` (RAM à zéro) | 49 296 o |
| **RAM statique totale** | **65 621 o** (l'outil arduino-cli annonce 65 624) |

Principaux contributeurs en flash :

| Composant | Flash | Rôle |
|---|---|---|
| `BSB_LAN.ino.cpp.o` | 321 708 o | tout le code BSB-LAN, ses chaînes et ses tables |
| libnet80211 + libpp + libphy + wpa_supplicant + esp_wifi | ≈ 361 000 o | pile WiFi (indispensable) |
| liblwip | 152 018 o | TCP/IP (indispensable) |
| libmbedcrypto + mbedtls + mbedtls_2 + mbedx509 | ≈ 245 300 o | crypto WPA2 (en partie indispensable) + TLS client (supprimable) |
| libespressif__mdns | 41 449 o | mDNS |
| libjoltwallet__littlefs | 33 905 o | LittleFS (journal en flash) |
| LIB:WebServer | 29 041 o | serveur OTA :8080 |
| libfatfs + LIB:SD + LIB:FS | ≈ 36 500 o | carte SD |
| libesp_driver_rmt / _i2c | 15 734 / 15 322 o | RMT (LED RGB du core [ESTIMÉ]) / I²C (BME280) |
| LIB:NetworkClientSecure | 6 516 o | client TLS |
| Bibliothèques embarquées `src/` | PubSubClient 5 007, bsb 3 360, BME280 3 266, Dallas 2 344, DHT 1 594, OneWireNg ≈ 2 500 o | |

RAM statique : `BSB_LAN.ino.cpp.o` 23 387 o, dont **`heating_cmdtbl` 16 000 o** et `bigBuff` 1 350 o ; WiFi ≈ 14 600 o ; spi_flash 6 479 o ; lwIP 5 060 o.

## 2. Tableau des fonctionnalités

Colonnes : coût flash/RAM (mesuré ou estimé), nécessaire pour l'Alféa (oui / non / optionnel).

| Fonctionnalité | Description | Fichiers principaux | Coût flash / RAM | Alféa ? | Justification |
|---|---|---|---|---|---|
| Couche bus BSB/LPB | trames, CRC, émission/réception | `src/BSB/bsb.cpp` | 3 360 o / ~0 [MESURÉ] | **oui** | cœur du produit |
| PPS | protocole point à point (sondes QAA50/70) | `include/pps_handling.h`, `BSB_LAN_defs.h:1314-1435` | 3 832 o [MESURÉ, symboles `*pps*`] + table ≈ 50 entrées | **non** | l'Alféa est en BSB (cf. 02 §3) |
| Décodage des valeurs (VT_*) | `printTelegram`, `optbl`, `build_pvalstr` | `include/print_telegram.h`, `BSB_LAN_defs.h` | ≈ 7 000 o [MESURÉ : printTelegram 3 054 + optbl 3 440 + build_pvalstr 600] | **oui** | |
| Table des paramètres | `cmdtbl[]` + chaînes et ENUM | `BSB_LAN_custom_defs.h` | 3 200 o pour 100 entrées × 32 o (défaut) [MESURÉ] ; liste Alféa ≈ 32 o/entrée + libellés [ESTIMÉ] | **oui** (réduite) | à filtrer aux paramètres utiles |
| `/QDB` (table temporaire en RAM) | 500 entrées construites depuis le régulateur | `BSB_LAN.ino:5250-5629`, `BSB_LAN_defs.h:618` | **16 000 o de RAM** [MESURÉ] | **non** | diagnostic seulement ; `/QD` reste utile |
| `/QD` dump | export de la structure pour la liste spécifique | `BSB_LAN.ino:5250-5612` | < 3 Ko [ESTIMÉ] | **oui** (phase d'identification) | indispensable pour obtenir la liste |
| Diffusions → compteurs 20000-20005 | durées et cycles brûleur/ECS | `include/broadcast_msg_handling.h` | 746 o [MESURÉ] | **optionnel** | sur une PAC, « brûleur » = compresseur ou appoint ? **[À VÉRIFIER]** sur trames réelles |
| Serveur HTTP + pages HTML | menu, catégories, lecture, config | `BSB_LAN.ino:4667-6994`, `include/print_webpage.h`, `html_strings.h` | `loop()` 23 042 o de code + 7 472 o de chaînes [MESURÉ] ; gros consommateur de chaînes | **oui** (allégé) | diagnostic local sans HA |
| API JSON `/J*` | lecture/écriture/config en JSON | `BSB_LAN.ino:5745-6378` | inclus dans `loop()` [MESURÉ global] | **optionnel** (garder `/JQ`, `/JI`, `/JL`, `/JW`) | secours REST, intégration `bsblan` |
| `/Y`, `/YR`, `/JY` (télégrammes bruts) | émission arbitraire | `BSB_LAN.ino:5630-5744`, `:5804-5862` | ≈ 2 Ko [ESTIMÉ] | **non** | **contourne la lecture seule** (cf. 01 §5) |
| `/G` GPIO | lecture/écriture de broches | `BSB_LAN.ino:6840-6884` | < 1 Ko [ESTIMÉ] | **non** | risque sur TX et les broches de strapping |
| Page de configuration `/C` + NVS | réglages persistants | `BSB_LAN.ino:1951-2720`, `BSB_LAN_EEPROMconfig.h`, `include/eeprom_io.h` | 7 575 o [MESURÉ, symboles `*onfig*`] + `config[]` 944 o | **oui** (allégée : WiFi, MQTT, bus, mode écriture) | évite de recompiler pour changer de réseau |
| **MQTT** | publication, commandes, LWT | `include/mqtt_handler.h`, `src/PubSubClient` | 9 520 + 5 007 o ; 2 Ko de tas + ≈ 4 Ko de pile en pointe [MESURÉ / code] | **oui** | voie HA retenue (cf. 04) |
| **Auto-discovery HA** | messages `homeassistant/…/config` | `mqtt_handler.h:178-344` | 2 084 + 1 318 o [MESURÉ] | **oui** | |
| TLS (MQTT sécurisé) | client TLS + bundle de CA | `x509_cert_bundle.h`, `NetworkClientSecure` | **56 244 o** (bundle) [MESURÉ] + ssl_client/mbedtls SSL ≈ 100-120 Ko [ESTIMÉ] | **non** | broker local en 1883 ; retirable par `NO_TLS` (déjà prévu en amont) |
| WiFi STA + AP de secours | connexion, scan BSSID, AP « BSB-LAN » | `BSB_LAN.ino:7468-7689`, `:8163-8207` | pile ≈ 470 Ko [MESURÉ] | **oui** | AP de secours : garder, mais **mot de passe à changer** |
| Ethernet (LAN8720/W5500) | réseau filaire | `BSB_LAN.ino:279-329`, `ETH.h` | ≈ 10-20 Ko [ESTIMÉ] | **non** | le C3 n'a pas de MAC Ethernet |
| mDNS | `bsb-lan.local` | `ESPmDNS` | 41 449 o [MESURÉ] | **optionnel** | pratique ; HA n'en a pas besoin si l'IP est fixe ou réservée |
| NTP + fuseau | heure Internet | `BSB_LAN.ino:4236-4252` | faible (SNTP inclus dans lwIP) | **optionnel** | sinon l'heure vient du régulateur |
| OTA HTTP :8080 | mise à jour à distance | `BSB_LAN.ino:1841-1889`, `WebServer`, `Update` | 29 041 o (WebServer) + 1 296 o [MESURÉ] | **oui** (protégée) | évite de démonter la carte |
| Journal SD / LittleFS, `/D*`, `/DG` | fichiers datalog, journal, tracé | `BSB_LAN.ino:4312-4516`, `:6379-6562`, `:7052-7230`, `graph_html` | 6 475 o (sketch) + LittleFS 33 905 + FAT/SD/FS ≈ 36 500 o [MESURÉ] | **non** | HA historise ; usure de la flash |
| Moyennes 24 h | moyennes glissantes | `BSB_LAN.ino:7173-7230`, `avg_parameters` | ≈ 1-2 Ko + 3 × 160 o de RAM [ESTIMÉ] | **non** | statistiques côté HA |
| Journal UDP | diffusion UDP :6502 | `BSB_LAN.ino:7075-7160` | < 1 Ko [ESTIMÉ] | **non** | |
| OneWire DS18B20 | capteurs de température | `src/OneWireNg`, `src/DallasTemperature` | ≈ 4 900 o [MESURÉ] + RMT ? | **non** | non demandé |
| DHT22 | capteurs T/HR | `src/DHTesp` | 1 594 o [MESURÉ] | **non** | |
| BME280 (+TCA9548A) | T/HR/pression I²C | `src/BlueDot_BME280`, `Wire` | 3 266 o + driver I²C 15 322 o [MESURÉ] | **non** | |
| Paramètres virtuels 20050-20899 | moyennes, capteurs, custom floats | `queryVirtualPrognr` | 2 876 o [MESURÉ] | **non** (sauf 20000-20005 si utiles) | |
| MAX! (CUL) | thermostats eQ-3 | `BSB_LAN.ino:3838-3870`, `:7273-7380` | 1 066 o [MESURÉ, partiel] | **non** | |
| IPWE | `/ipwe.cgi` | `include/print_ipwe.h` | 1 454 o [MESURÉ] | **non** | |
| Telnet (debug) | console :23 | `BSB_LAN.ino:7382-7398` | < 1 Ko [ESTIMÉ] | **optionnel** | le débogage passe par l'USB-CDC |
| Vérification de version | appel au serveur bsb-lan.de | `include/print_webpage.h` | < 1 Ko [ESTIMÉ] | **non** | transmet l'IP publique |
| Économie d'énergie 80 MHz | `setCpuFrequencyMhz(80)` | `BSB_LAN.ino:7974-7979` | ~0 | **optionnel** | le C3 tourne à 160 MHz ; gain thermique faible |
| Extensions `custom_functions/` | Modbus, NTP→régulateur… | `BSB_LAN_custom*.h` | 0 par défaut | **non** | Modbus : 332 o liés (Modbus.cpp) sans usage |
| Localisation | chaînes de la langue choisie + repli EN/DE | `localization/` | dans les ≈ 129 Ko de chaînes fusionnées [MESURÉ, agrégé] | **oui** (FR) | |
| Watchdog, maintenance 60 s | WDT 150 s, re-détection, reconnexion | `BSB_LAN.ino:7980-7991`, `:7423-7456` | faible | **oui** | robustesse |

## 3. Gains attendus d'une configuration minimale

| Action | Gain flash | Gain RAM | Statut |
|---|---|---|---|
| `NO_TLS` (existe déjà) | ≥ 56 244 o (bundle) + ≈ 100 Ko de SSL | quelques Ko de tas en connexion TLS | [MESURÉ pour le bundle, ESTIMÉ pour le reste] |
| Retrait de SD/LittleFS/journaux/`/DG` | ≈ 75 Ko | ~2 Ko | [MESURÉ, somme des composants] |
| `MAX_HEATINGTBL` → 1 ou retrait de `/QDB` | ≈ 1 Ko | **16 000 o** | [MESURÉ] |
| Retrait de OneWire/DHT/BME/I²C | ≈ 25 Ko | — | [MESURÉ, composants] |
| Retrait de PPS, IPWE, MAX!, UDP, moyennes, virtuels | ≈ 12 Ko | ≈ 1 Ko | [MESURÉ, partiel] |
| Retrait d'Ethernet | ≈ 10-20 Ko | — | [ESTIMÉ] |
| **Total indicatif** | **≈ 280-300 Ko** (image ≈ 1,31 Mo, soit 67 % de la partition) | **≈ 18 Ko** | à confirmer par build en Phase 4 |

Ce gain n'est **pas indispensable** : l'image amont tient déjà dans le C3 avec 18 % de marge (cf. 07 §6.4). La réduction vise surtout la **surface d'attaque**, la **lisibilité** et une **marge OTA** pour l'avenir.

## Annexe — méthode de mesure

1. Copie de `HEAD` dans un répertoire temporaire hors dépôt, avec `BSB_LAN_config.h` et `BSB_LAN_custom_defs.h` copiés des `.default` (aucune modification du dépôt).
2. Conteneur jetable `debian:trixie` avec `arduino-cli` et le core `esp32:esp32@3.3.12`, puis `arduino-cli compile --fqbn esp32:esp32:esp32c3 --board-options PartitionScheme=min_spiffs,CDCOnBoot=cdc`.
3. Analyse de `BSB_LAN.ino.map` avec un script Python : somme des tailles des sections d'entrée par fichier objet ou archive, en ne gardant que les sections de sortie allouées (`.iram0.text`, `.flash.text`, `.flash.rodata`, `.dram0.data`, `.dram0.bss`, `.eh_frame`…). Les sections `.debug_*` sont exclues.
4. Limite : les chaînes littérales fusionnées par l'éditeur de liens (`.rodata.*.str1.*`) sont attribuées au premier symbole qui les référence (≈ 129 Ko imputés à un lambda de `init_ota_update`). Les gains par fonctionnalité du §3 ne sont donc qu'**indicatifs** tant qu'un build différentiel ne les confirme pas.

Ces scripts seront versionnés dans `docker/` en Phase 4 pour rendre la mesure reproductible.
