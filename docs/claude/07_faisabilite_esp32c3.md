# 07 — Faisabilité ESP32-C3

> **Résumé**
> **Faisable, mesures à l'appui.** L'amont non modifié compile pour ESP32-C3 : 1 610 749 o de flash (81 % de la partition app de 1,875 Mo) et 65 624 o de RAM statique, pour 327 680 o de DRAM disponibles. Le C3 est même déjà supporté en amont (Olimex ESP32-C3).
> L'Alféa Extensa Duo A.I. utilise un **Siemens RVS21** en **BSB** (connecteur X86) ; il a été identifié chez d'autres utilisateurs comme **RVS21.831F/127, famille 211, variante 127**. La liste de paramètres spécifique doit être produite par le mainteneur à partir d'un dump `/QD`.
> **Choix proposé : ESP32-C3 SuperMini**, à condition de valider la portée RF sur le lieu d'installation (critère chiffré au §6.5). La raison principale : 4 Mo de flash confirmés et donc l'OTA garanti, l'USB natif et un format adapté à une carte fille. Le kit Ai-Thinker est le plan B ; il pose deux problèmes : flash de 2 ou 4 Mo selon les sources, et produit arrêté.
> Risques principaux : qualité RF variable selon les lots de SuperMini, dépendance humaine pour la liste de paramètres, brochage X86 à confirmer.

Conventions : **[CONSTATÉ]**, **[MESURÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**. Les sources web viennent d'une recherche documentaire du 2026-11-01 ; les URL sont citées.

---

## 6.1 Identification de l'appareil

### Liste de compatibilité BSB-LAN [CONSTATÉ]
- `docs/en/supported_models.md:11` : « Atlantic: Axeo, Alféa Excellia A.I., **Alféa Extensa A.I.**, Hynea hybrid duo gaz, Navistem, Perfinox, Varmax ».
- `docs/en/list_of_controllers.md:1` : **RVS21** fait partie des régulateurs supportés.
- `docs/en/supported_heating_systems.md:25` : RVS21, BSB sur **X86**, « + = rightmost pin, − = second pin from right ». Ne pas utiliser les bornes 2-3 de l'étiquette Navilink A59 (simple alimentation).
- `docs/en/faq.md:18-19` : sur certaines Atlantic, l'**IHM ne se resynchronise pas** avec le régulateur Siemens. Les changements faits par BSB-LAN sont actifs mais ne s'affichent pas sur l'écran.
- `BSB_LAN/BSB_LAN_defs.h:175` : `DEV_211_ALL 211,255 // … RVS21.831F/127`.

### Sources externes
- Notice Atlantic « Alfea Extensa Duo A.I. R32 » (U0671216_2114_FR_4, 06/10/2020), p. 65 : « Régulation : **RVS21** - 85.002.030 », IHM séparée. Sondes A59/A75 sur X86 bornes 2-3, Typass sur 1-2-3 ([PDF](https://files.izi-by-edf-renov.fr/files/catalogue/produits/notice-installation-alfea-extensa-ai-R32-ecs-atlantic.pdf)). La notice ne mentionne pas « BSB ».
- Retours d'utilisateurs BSB-LAN sur des Alféa Extensa Duo : **RVS21.831F/127, famille 211, variante 127, OV 4062** ([PR #812](https://github.com/fredlcore/BSB-LAN/pull/812), [#811](https://github.com/fredlcore/BSB-LAN/issues/811), [#829](https://github.com/fredlcore/BSB-LAN/issues/829), [#831](https://github.com/fredlcore/BSB-LAN/issues/831), [#622](https://github.com/fredlcore/BSB-LAN/issues/622)). X86 décrit comme `B2, M, B1, 3, 2, 1` ([#405](https://github.com/fredlcore/BSB-LAN/issues/405)). Une variante « Duo 6 » comporte un AVS37 ([#609](https://github.com/fredlcore/BSB-LAN/issues/609)). L'#622 signale que l'IHM réécrit l'heure toutes les 1-2 min.
- **[SUPPOSÉ]** Votre machine est très probablement un RVS21.831F/127 (211/127). La notice R32 ne donne que « RVS21 » sans suffixe, donc **[À VÉRIFIER]** sur la machine.

### Procédure d'identification sur la machine réelle (lecture seule, sans risque)
1. Brancher l'adaptateur sur X86 (après validation du brochage) avec un firmware en lecture seule (`DEFAULT_FLAG FL_RONLY`).
2. Au boot, `GetDevId()` envoie un QINF 0x053D0064 en diffusion et journalise `device family: …, device variant: …` sur la console série (`BSB_LAN/BSB_LAN.ino:4205-4216`). La liste des appareils présents sur le bus (régulateur 0x00, IHM 0x0A, sondes…) s'affiche aussi (`:4189-4200`).
3. Contrôle par HTTP : `http://<ip>/6224-6227` affiche identification, **famille (6225)**, **variante (6226)** et version OV (6227) (`BSB_LAN/BSB_LAN_custom_defs.h.default`, entrées 6224-6227).
4. `http://<ip>/QD` produit le fichier de structure (requêtes IQ1/IQ2 uniquement, en lecture). On l'envoie à bsb@code-it.de pour obtenir le `BSB_LAN_custom_defs.h` spécifique (`docs/en/install.md:49-57`).
5. En attendant, `/QDB` donne une table temporaire des températures et pourcentages en lecture seule (`BSB_LAN/BSB_LAN.ino:5489-5503`), utile pour un premier test HA.

## 6.2 ESP32 classique vs ESP32-C3

| Critère | ESP32 (WROOM-32) | ESP32-C3 | Impact BSB-LAN |
|---|---|---|---|
| CPU | 2 × Xtensa LX6, 240 MHz | 1 × RISC-V RV32IMC, 160 MHz | BSB-LAN est mono-fil (`loop()`) ; seul le WiFi partage le cœur unique. Le bus à 4 800 bauds n'impose aucune contrainte temps réel forte (FIFO RX ≥ une trame) [SUPPOSÉ] |
| SRAM | 520 Ko | 400 Ko (dont 16 Ko de cache) | DRAM utilisable : 327 680 o dans les deux cas selon arduino-cli [MESURÉ] |
| Flash | externe, 4 Mo typique | intégrée (FN4/FH4 : 4 Mo) ou externe | 4 Mo requis pour l'OTA (cf. §6.4) |
| UART | 3 | **2** (UART0, UART1) ([ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/peripherals/uart.html)) | `Serial1` = UART1 pour le bus. `Serial` = USB-CDC (SuperMini) ou UART0 (kit) : **pas de conflit** |
| Inversion matérielle de l'UART | oui | oui (`UART_RXD_INV`/`UART_TXD_INV` ; `setRxInvert()` dans arduino-esp32) | **non utilisée** : BSB-LAN inverse les données en logiciel (cf. 02 §1.1) |
| GPIO | 34 | 22 (FN4/FH4) ; strapping **GPIO2, 8, 9** ; USB **18/19** ; flash SPI 12-17 ([GPIO](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/peripherals/gpio.html)) | il faut 2 GPIO (RX/TX) + 1 LED : largement suffisant |
| USB | via un pont USB-UART externe | **USB-Serial-JTAG natif** (CDC + JTAG) | flash et debug sans pilote sur le SuperMini |
| Ethernet | MAC RMII | **aucun** | code ETH à neutraliser (compile tout de même [MESURÉ]) |
| SD_MMC | oui | non (`SOC_SDMMC_HOST_SUPPORTED` absent) → repli sur SPI (`BSB_LAN/BSB_LAN.ino:430-437`) | sans objet (journaux supprimés) |
| Errata | — | CPU-863, ADC-183, ADC-270 ; **aucun erratum UART ou WiFi** ([errata](https://docs.espressif.com/projects/esp-chip-errata/en/latest/esp32c3/02-errata-summary/index.html)) | sans impact |
| Taille de l'image BSB-LAN amont | **1 555 781 o / 76 568 o de RAM** [MESURÉ] | **1 610 749 o / 65 624 o de RAM** [MESURÉ] | +3,5 % de flash (densité RISC-V), −14 % de RAM statique |

### Framework et outillage
- **arduino-esp32 3.3.12** (version courante au 2026-11-01) : le build C3 passe **sans aucune modification** [MESURÉ]. Le code exige le core 3.x (cf. 01 §1.2).
- Cible Arduino : `esp32:esp32:esp32c3` (« ESP32C3 Dev Module »), options `PartitionScheme=min_spiffs`, `CDCOnBoot=cdc` (nécessaire pour que `Serial` sorte sur l'USB natif du SuperMini).
- PlatformIO : la plateforme officielle `platformio/platform-espressif32` v8.0.0 annonce le support d'arduino-esp32 3.3.12 ([releases](https://github.com/platformio/platform-espressif32/releases)) ; *pioarduino* propose un board `nologo_esp32c3_super_mini`. Boards génériques vérifiés : `esp32-c3-devkitm-1`, `lolin_c3_mini`. **[À VÉRIFIER par un build]** : la v8.0.0 est très récente (annoncée le 2026-10-19). Je propose de garder le build `arduino-cli` comme **référence** (identique à la CI amont, déjà validé) et d'y ajouter l'environnement PlatformIO demandé, dont les tailles devront être comparées à cette référence (décision à prendre à la GATE 1).
- Dépendances incompatibles : **aucune bloquante** [MESURÉ : 0 erreur]. À noter : `portInputRegister()` (`bsb.cpp:651`), `ETH.h` et la configuration du WDT avec `CONFIG_FREERTOS_NUMBER_OF_CORES` (`BSB_LAN.ino:7987`) compilent tous les trois sur C3.

## 6.3 Comparaison des deux cartes candidates

| Critère | ESP32-C3 SuperMini | Ai-Thinker NodeMCU ESP-C3-32S-Kit |
|---|---|---|
| Module, flash | SoC nu sur la carte ; **4 Mo** ([esp3d](https://esp3d.io/esp3d/v3.x/hardware/esp_boards/esp32-c3/esp-c3-super-mini/index.html), [RNT](https://randomnerdtutorials.com/?p=170189)) ; référence exacte FN4/FH4 non confirmée | module ESP-C3-32S. **4 Mo** selon la spec Ai-Thinker, **2 Mo** selon Waveshare ([spec](https://img.iceasy.com/product/product/files/202108/8a8a8a1a7aec7b55017b14be70f605b7.pdf), [wiki Waveshare](https://www.waveshare.com/wiki/ESP-C3-32S-Kit)) → **à vérifier lot par lot** |
| Antenne, qualité RF | **antenne céramique**. Lots documentés avec une antenne trop proche du SoC et un réseau d'adaptation incomplet → connexion WiFi difficile. Correctif usuel : `WiFi.setTxPower(WIFI_POWER_8_5dBm)` ([hackaday](https://hackaday.io/project/205906-esp32-c3-super-mini-wifi-fix-3-methods-that-work/details), [WLED](https://wled.discourse.group/t/some-c3-super-minis-cant-connect-to-wi-fi/12153), [µPy](https://github.com/micropython/micropython/discussions/10524)) | **antenne PCB du module**, avec option IPEX selon la version. Conception de module plus maîtrisée [SUPPOSÉ : meilleure RF, non mesurée] |
| Interface USB | **USB-Serial-JTAG natif** (USB-C). Flash, console CDC et JTAG sans pilote. Entrée en mode téléchargement automatique par esptool via USB-JTAG [SUPPOSÉ : comportement standard du C3] ; BOOT = GPIO9 en secours | **CH340C** (micro-USB), reset automatique par RTS/DTR ([schéma](https://www.waveshare.com/w/upload/4/46/Nodemcu-esp-c3-32s-kit-schematics.pdf)). Pilote CH340 nécessaire sous Windows |
| GPIO accessibles, strapping | GPIO 0-10, 20, 21 (13 broches). LED bleue sur GPIO8 (strapping, active à l'état bas), BOOT sur GPIO9 | IO0-10, 12, 14-21. **LED RGB sur IO3/4/5, LED blanches sur IO18/19** : ces dernières partagent les broches de l'USB-JTAG |
| Régulateur 3,3 V | selon le lot : **ME6211 (500 mA)** ou **LP5907 (250 mA)** ([Habr](https://habr.com/ru/companies/beget/articles/956868/)) | AMS1117-3.3 (1 A nominal [SUPPOSÉ, fiche non relue]) ; chute ≈ 1,1 V, sans problème sous 5 V |
| Consommation et thermique | C3 : pointes TX WiFi ≈ 300-350 mA [SUPPOSÉ : ordre de grandeur de la datasheet, à mesurer]. **Le LP5907 (250 mA) est sous-dimensionné** pour ces pointes : n'acheter que des lots en ME6211, ou ajouter un condensateur de découplage local | plus de marge (AMS1117), mais plus de dissipation linéaire : (5 − 3,3) × 0,1 A ≈ 0,17 W en moyenne |
| Encombrement | **22,5 × 18 mm**, 2 × 8 broches au pas de 2,54 mm ([mischianti](https://mischianti.org/esp32-c3-supermini-plus-v2-high-resolution-pinout-datasheet-and-specs/)) : se monte directement sur une carte fille | module de 25,5 × 18 mm sur une carte DIP-30 large ; dimensions exactes de la carte **non trouvées** ; empreinte de carte fille bien plus grande |
| Disponibilité, qualité des lots | très répandu et bon marché ; **qualité variable** (antenne, LDO) | **« no longer manufactured »** chez Farnell ([lien](https://uk.farnell.com/rf-solutions/esp32-c3-32s-kit/wlan-comm-module-160mhz/dp/3932672)) ; peu d'identifiants PlatformIO dédiés |

## 6.4 Budget mémoire

### Flash et partitions [MESURÉ]
Table `min_spiffs` (= `BSB_LAN/partitions.csv`) sur 4 Mo : nvs 20 Ko, otadata 8 Ko, **app0 = app1 = 1 966 080 o**, spiffs 128 Ko, coredump 64 Ko.

| Configuration | Image | Occupation de la partition app | Marge OTA |
|---|---|---|---|
| Amont non modifié, C3 | 1 610 749 o | 81,9 % | 355 331 o |
| Cible réduite (estimation de 05 §3) | ≈ 1,31-1,33 Mo | ≈ 67 % | ≈ 640 Ko |
| Cible + liste Alféa complète non filtrée [ESTIMÉ +50 à +100 Ko] | ≈ 1,4 Mo | ≈ 72 % | ≈ 550 Ko |

- L'OTA en double banque exige 2 × image ≤ flash − 192 Ko de partitions fixes. **Avec 2 Mo de flash, l'OTA est impossible** : 2 × 1,31 Mo > 1,8 Mo. C'est l'argument décisif contre un kit Ai-Thinker en version 2 Mo.
- On pourrait réduire `spiffs` (inutile sans journaux) au profit des partitions app. Ce n'est pas nécessaire.

### RAM
- Statique : 65 624 o sur 327 680 → **262 056 o** pour le tas et les piles au démarrage [MESURÉ]. La cible réduite gagne ≈ 18 Ko, dont `heating_cmdtbl` (16 000 o).
- Dynamique en fonctionnement [SUPPOSÉ, à mesurer via `/JI` en Phase 4] : WiFi STA ≈ 40-60 Ko, lwIP et sockets ≈ 10-20 Ko, PubSubClient 2 Ko + client, WebServer OTA quelques Ko, mDNS ≈ 5-10 Ko → tas libre attendu **≈ 150-200 Ko**. Critère d'acceptation proposé : tas libre ≥ 60 Ko et plus grand bloc libre ≥ 20 Ko après 24 h.
- Pile : la tâche `loopTask` dispose de 8 Ko (défaut d'arduino-esp32 [SUPPOSÉ]). Le chemin MQTT le plus profond place ≈ 4,3 Ko de tableaux sur la pile (2 × `MQTTPayload` + topics), comme sur un ESP32 classique où l'amont fonctionne. Critère : *high-water mark* ≥ 1 Ko, mesuré avec `uxTaskGetStackHighWaterMark` en Phase 4.

## 6.5 Conclusion

### Faisabilité : **OUI**
L'amont compile tel quel pour C3, avec 18 % de marge de flash et 80 % de DRAM libre au démarrage. Le protocole BSB n'utilise que des fonctions disponibles sur C3 : UART1 avec n'importe quelles broches via la matrice GPIO, inversion en logiciel, interruption à chaque octet. Une cible C3 existe déjà en amont.

### Risques

| # | Risque | Probabilité / impact | Atténuation |
|---|---|---|---|
| R1 | RF médiocre du SuperMini en chaufferie (mur, carter métallique de la PAC) | moyenne / élevé | test RSSI avant intégration ; `setTxPower` ; dégagement d'antenne sur la carte fille ; repli sur le kit Ai-Thinker ou sur une carte C3 à antenne externe |
| R2 | Liste de paramètres spécifique dépendante du mainteneur | élevée / moyen | `/QDB` en attendant ; demander la liste 211/127 déjà produite pour d'autres utilisateurs (PR #812) |
| R3 | Brochage X86 et polarité incertains | moyenne / moyen (pas de dégât grâce à D2) | contrôle au multimètre (≈ 12-15 V entre + et −) avant de brancher ; LED rouge |
| R4 | LDO 250 mA (LP5907) sur certains lots | moyenne / moyen (brown-out sur les pointes TX) | vérifier le marquage (ME6211 « S2W ») ; condensateur de 100 µF sur 5 V ; alimentation 5 V externe ≥ 1 A |
| R5 | Bus perturbé au boot (TX bas) | faible / élevé (erreurs sur la PAC) | rappel à VCC sur la base de Q2, GPIO TX sans activité ROM (pas GPIO21) |
| R6 | L'IHM Atlantic ne reflète pas les écritures (FAQ) ou les écrase (heure, #622) | moyenne / faible en lecture seule | lecture seule par défaut ; écriture documentée plus tard |
| R7 | PlatformIO v8 avec core 3.3.12 trop récent | faible / faible | build `arduino-cli` de référence |
| R8 | Dérive de l'amont (rebase) | moyenne / faible | réduction par `#if` sans suppression de code (cf. Phase 3) |

### Choix argumenté : **ESP32-C3 SuperMini** (sous condition RF)

Critères pondérés (note de 1 à 5, poids entre parenthèses) :

| Critère | SuperMini | Kit Ai-Thinker | Justification |
|---|---|---|---|
| Flash 4 Mo garantie → OTA (×3) | 5 | 2 | 4 Mo concordant chez toutes les sources pour le SuperMini ; 2 ou 4 Mo selon les sources pour le kit |
| Qualité RF (×3) | 2 | 4 | antenne céramique aux lots variables vs antenne PCB du module |
| Intégration sur carte fille et encombrement (×2) | 5 | 2 | 22,5 × 18 mm, 2 × 8 broches au pas de 2,54 mm vs DIP-30 large |
| USB, flash et debug (×2) | 5 | 3 | USB natif CDC + JTAG ; pas de pilote |
| Disponibilité, pérennité (×2) | 4 | 1 | produit courant vs arrêté |
| Alimentation (×1) | 3 | 4 | ME6211 500 mA (ou LP5907 250 mA) vs AMS1117 |
| Broches libres sans conflit (×1) | 4 | 3 | LED RGB et blanches sur des GPIO utiles côté kit |
| **Score pondéré (/70)** | **56** | **37** | |

Le SuperMini l'emporte sur tous les critères sauf la RF, qui est **mesurable et compensable**. Je propose de **conditionner le choix** à un critère d'acceptation : RSSI ≥ −70 dBm, stable sur 1 h, à l'emplacement réel de la carte, mesuré avec le firmware de test (Phase 4, avant la GATE 3). En cas d'échec, repli sur le kit Ai-Thinker en version 4 Mo vérifiée, ou sur une carte C3 à connecteur d'antenne externe (hors des deux candidates initiales : décision à vous).

Brochage proposé (à finaliser en Phase 3) : **RX = GPIO6, TX = GPIO7**. Ces broches existent sur les deux cartes et ne sont ni des broches de strapping, ni l'USB, ni l'UART0/log ROM, ni une LED. **LED d'état = GPIO8** (LED intégrée du SuperMini ; broche de strapping, ce qui est acceptable pour une sortie active à l'état bas).

➡️ **GATE 1** : voir la synthèse dans `README.md` et la réponse de fin de phase.
