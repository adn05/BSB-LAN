# 02 — Le protocole BSB (et LPB / PPS)

> **Résumé**
> Le BSB est un bus 2 fils (CL+/CL-) alimenté par le régulateur. Le niveau de repos est haut ; un émetteur tire la ligne vers le bas. Côté MCU, c'est un UART **4800 bauds, 8O1** (11 bits par octet, soit 2,29 ms) dont les octets de données sont **complémentés** (`^0xFF`) en logiciel.
> Une trame : `DC | src|0x80 | dst | len | type | CmdID(4) | payload | CRC16-XMODEM`, au plus 32 octets (73 ms). Le CRC est validé sur une trame réelle du dépôt.
> L'arbitrage se fait par écoute avant émission (63-82 ms de silence), puis relecture de l'écho pour détecter une collision.
> L'Alféa Extensa Duo A.I. utilise un **Siemens RVS21** en **BSB** (connecteur X86) [CONSTATÉ dans la doc et la notice Atlantic ; brochage exact à vérifier sur la carte].

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]** — cf. `README.md`.

---

## 1. Couche physique

### 1.1 Ce que dit le code [CONSTATÉ]

| Élément | Valeur | Référence |
|---|---|---|
| UART | `Serial1.begin(4800, SERIAL_8O1, rx_pin, tx_pin)` (ESP32) | `BSB_LAN/src/BSB/bsb.cpp:38` |
| Seuils du FIFO RX | `setRxFIFOFull(1)`, `setRxTimeout(1)` : interruption à chaque octet | `bsb.cpp:39-40` |
| Inversion | **logicielle, sur les données seulement** : `data ^ 0xFF` en émission, `read ^ 0xFF` en réception (sauf PPS) | `bsb.cpp:450-452`, `:655-660` |
| Lecture directe de la broche RX pour savoir si le bus est occupé | `rx_pin_read()` renvoie `!niveau` : « occupé » = RX à 0 | `bsb.cpp:651-653` |

**Conséquence sur la forme d'onde.** L'inversion logicielle ne touche ni le bit de start, ni le bit de stop, ni le repos. Côté MCU, l'UART reste donc **non inversé** : repos à 1, start à 0. L'adaptateur recopie le bus sans l'inverser (bus haut ↔ RX haut ; TX bas ↔ bus tiré bas, cf. `06_carte_interface_bsb.md`). Sur le fil, le bus au repos est **haut**. Un octet de valeur logique `V` est transmis comme l'octet UART `~V`.

**Compatibilité avec la parité.** Complémenter 8 bits fait passer le nombre de « 1 » de k à 8 − k, et k et 8 − k ont la même parité. Le bit de parité impaire est donc identique pour `V` et `~V` : pas besoin de traiter la parité à part. C'est ce qui permet d'utiliser l'UART matériel sans inversion.

**Pourquoi ne pas utiliser l'inversion matérielle de l'UART ?** Elle inverserait aussi start, stop et repos, ce qui ne correspond pas au bus. Elle n'est **pas** nécessaire et ne doit **pas** être activée sur le C3 (`HardwareSerial::begin(..., invert=false)`).

### 1.2 Niveaux électriques

| Grandeur | Valeur | Statut |
|---|---|---|
| Tension de repos (bus haut) | ≈ 12-15 V selon la littérature communautaire ; aucune donnée Atlantic | **[À VÉRIFIER]** à l'oscilloscope ou au multimètre sur X86 |
| Seuil de détection « haut » de l'adaptateur officiel | la LED d'entrée conduit dès que V(CL+ − CL-) dépasse ≈ Vf(1N4148) + Vf(4N25) + Vf(LED rouge) ≈ 0,7 + 1,2 + 1,8 = **3,7 V** | [SUPPOSÉ, déduit du schéma `BSB_LAN/schematics/bsb_adapter.pdf` et de Vf typiques] |
| Courant d'entrée de l'adaptateur au repos | (13 V − 3,7 V) / 1,5 kΩ ≈ **6,2 mA** | [SUPPOSÉ, pour 13 V] |
| Alimentation de tiers par le bus | la doc indique que l'adaptateur **n'est pas** alimenté par le régulateur et qu'il faut une alimentation USB d'au moins 2 A pour le MCU | [CONSTATÉ] `docs/en/install.md` (§ « Connecting… », point PowerSupply) |
| Borne G+ | « provides power only, no data » ; ne pas s'y raccorder | [CONSTATÉ] `docs/en/install.md` (même §) |

### 1.3 Temps caractéristiques (calculés)

| Grandeur | Calcul | Valeur |
|---|---|---|
| Bit | 1 / 4800 | 208,3 µs |
| Octet 8O1 (start + 8 + parité + stop) | 11 / 4800 | **2,29 ms** |
| Trame minimale (11 o, sans charge utile) | 11 × 2,29 | 25,2 ms |
| Trame maximale (32 o) | 32 × 2,29 | **73,3 ms** |
| Temps d'attente « bus libre » avant émission | `random(1,20) + 3 + 59` | 63 à 82 ms (`bsb.cpp:362`) |
| Recul après activité détectée | `delay(146)` = 2 × 32 × 11 / 4800 | 146,7 ms (`bsb.cpp:376`) |
| Attente de réponse | 3 000 ms, au plus 15 trames étrangères examinées | `bsb.cpp:609-612` |
| Fin de trame en réception | `delay(4)` si le FIFO est vide (> 1 octet = 2,29 ms) | `bsb.cpp:224-226`, `:251-253` |

Remarque : le commentaire de `bsb.cpp:362` attribue 3 ms à « one full (32 bytes) telegram ». En réalité une trame de 32 octets dure 73 ms ; les 3 ms ne correspondent qu'à environ un octet. L'algorithme n'est pas faux, puisqu'il sonde la ligne en continu pendant toute l'attente, mais le commentaire est trompeur.

---

## 2. Couche liaison

### 2.1 Format d'une trame BSB [CONSTATÉ]

Construction en émission : `bsb.cpp:516-584` ; validation en réception : `bsb.cpp:179-295`.

| Octet | Champ | Détail |
|---|---|---|
| 0 | SOF | `0xDC` (`0xDE` aussi accepté en réception, `bsb.cpp:197`) |
| 1 | Source | adresse source OR `0x80` (`bsb.cpp:579`). BSB-LAN = `0x42` → `0xC2` |
| 2 | Destination | `0x00` régulateur, `0x0A` écran, `0x06` sonde d'ambiance, `0x7F` diffusion (`BSB_LAN/BSB_LAN_defs.h:48-62`) |
| 3 | Longueur | longueur **totale** de la trame, SOF et CRC compris : 11 + n (`bsb.cpp:553`) |
| 4 | Type | QINF 0x01, INF 0x02, SET 0x03, ACK 0x04, NACK 0x05, QUR 0x06, ANS 0x07, ERR 0x08, QRV 0x0F, ARV 0x10, IQ1-IA2 0x12-0x15 (`BSB_LAN_defs.h:29-45`) |
| 5-8 | Command ID | 4 octets ; **les 2 premiers sont permutés à l'émission** (`bsb.cpp:521-559`) et ne le sont pas dans les réponses (`bsb.cpp:630`) |
| 9…len-3 | Payload | n octets ; pour une valeur : 1 octet *enable* (0x00 = valide) + valeur gros-boutiste |
| len-2, len-1 | CRC | CRC-16 CCITT/XMODEM (poly 0x1021, init 0), MSB d'abord, calculé sur tous les octets précédents ; la trame complète doit donner CRC = 0 (`bsb.cpp:298-308`, `:276`) |

LPB : SOF `0x78`, longueur à l'octet 1, 4 octets d'en-tête supplémentaires (`offset = 4`), somme de contrôle différente (`bsb.cpp:62-80`, `:312-322`). PPS : trames courtes, CRC = complément à 2 de la somme (`bsb.cpp:325-336`).

### 2.2 Exemples de trames décodées

Valeurs calculées avec l'algorithme de `bsb.cpp` (script `crc.py`, conteneur `python:3.12-slim`) :

| Cas | Trame (hex) | Décodage |
|---|---|---|
| **Trame réelle citée dans le code** (`BSB_LAN/BSB_LAN_custom_defs.h.default:7133-7138`) | `DC 80 0A 0E 07 2D 3D 05 A5 00 08 C0 3F 7B` | HEIZ(0x00) → DISP(0x0A), ANS, CmdID 0x2D3D05A5, enable 00, 0x08C0 = 2240 / 64 = **35,0 °C**. CRC recalculé = **0x3F7B** ✔ (valide l'algorithme) |
| Requête de la T° extérieure 8700 (`0x053D0521`) | `DC C2 00 0B 06 3D 05 05 21 B9 7C` | 0x42 → 0x00, QUR ; CmdID permuté `3D 05 05 21` |
| Réponse attendue (exemple 5,0 °C) | `DC 80 42 0E 07 05 3D 05 21 00 01 40 C6 A8` | 0x00 → 0x42, ANS, CmdID non permuté, valeur 0x0140 / 64 = 5,0 °C (`VT_TEMP`, opérande 64, `BSB_LAN/BSB_LAN_defs.h:928`) |
| Détection des appareils (`GetDevId`) | `DC C2 7F 0B 01 3D 05 00 64 37 B4` | QINF 0x053D0064 en diffusion ; chaque appareil répond par un INF contenant famille, variante, OC et numéro de série (`BSB_LAN/BSB_LAN.ino:4150-4176`) |

### 2.3 Séquence requête/réponse et arbitrage

```mermaid
sequenceDiagram
  participant L as BSB-LAN (0x42)
  participant BUS as Bus BSB
  participant R as RVS21 (0x00)
  L->>BUS: sonde RX pendant 63-82 ms (bsb.cpp:370-391)
  alt activité détectée
    L->>L: delay 146 ms, vide le FIFO, recommence (timeout 1 s → BUS_NOTFREE)
  end
  L->>BUS: émet 11 o (25 ms), chaque octet ^0xFF
  BUS-->>L: écho de sa propre trame sur RX (bus partagé)
  L->>L: compare l'écho octet par octet (bsb.cpp:489-512) ; différence → collision, recul 146 ms, réémission
  R->>BUS: ANS (≈ 14 o, 32 ms)
  L->>L: GetMessage : SOF, longueur, CRC ; correspond si dst=0x42 et CmdID égal (bsb.cpp:630)
```

- **Collision** : il n'y a pas d'arbitrage bit à bit pendant l'émission (commentaires historiques `bsb.cpp:397-442`). La détection se fait *a posteriori* en comparant l'écho après `flush()`. C'est suffisant parce que le BSB est peu chargé : le régulateur est maître et les trames spontanées sont rares.
- **Réessais** : 3 tentatives par paramètre au niveau applicatif (`QUERY_RETRIES`, `BSB_LAN/BSB_LAN.ino:116`, boucle `:3978-4008`).
- **Erreurs** : CRC ou longueur invalide → trame ignorée et message « CRC error » sur `Serial` (`bsb.cpp:271-288`). Réponse de type ERR (0x08) → paramètre non supporté (`decodedTelegram.error`, codes listés `BSB_LAN/BSB_LAN.ino:505`).

---

## 3. BSB, LPB et PPS — et ce qu'utilise l'Alféa

| | BSB | LPB | PPS |
|---|---|---|---|
| Usage | régulateur ↔ sondes d'ambiance/écrans (QAA55/75) | inter-régulateurs, cascade | ancien, point à point vers une sonde d'ambiance |
| Couche physique | identique (même adaptateur) | identique | identique |
| Adressage | 1 octet, régulateur = 0 | segment/appareil : `seg*16 + dev − 1` | aucun, le régulateur est maître |
| SOF / contrôle | 0xDC / CRC16 | 0x78 / somme | variable / complément à 2 |
| Bornes usuelles | CL+ / CL- | DB / MB | A6 / M |

Source : `docs/en/bus_systems.md` et `docs/en/install.md` [CONSTATÉ].

**Alféa Extensa Duo A.I.** :
- [CONSTATÉ] `docs/en/supported_models.md:11` cite « Alféa Extensa A.I. ». La notice Atlantic « Alfea Extensa Duo A.I. R32 » (réf. U0671216_2114_FR_4, p. 65) indique « Régulation : **RVS21** - 85.002.030 » avec une IHM séparée ([PDF](https://files.izi-by-edf-renov.fr/files/catalogue/produits/notice-installation-alfea-extensa-ai-R32-ecs-atlantic.pdf)).
- [CONSTATÉ] Pour le RVS21, le BSB est sur le **connecteur X86** : « + = rightmost pin, − = second pin from right ». Il ne faut **pas** utiliser les bornes 2-3 indiquées par l'autocollant Navilink A59, qui ne servent qu'à l'alimenter (`docs/en/supported_heating_systems.md:25`). La notice Atlantic ne mentionne ni « BSB » ni « CL+/CL- ».
- [CONSTATÉ, retours d'utilisateurs] Des Alféa Extensa Duo ont été identifiées comme **RVS21.831F/127, famille 211, variante 127** ([PR #812](https://github.com/fredlcore/BSB-LAN/pull/812), [#811](https://github.com/fredlcore/BSB-LAN/issues/811), [#622](https://github.com/fredlcore/BSB-LAN/issues/622)). `DEV_211_ALL` existe déjà dans `BSB_LAN/BSB_LAN_defs.h:175`.
- **[À VÉRIFIER]** Famille et variante réelles de *votre* machine (paramètres 6225/6226), brochage physique de X86 (l'[issue #405](https://github.com/fredlcore/BSB-LAN/issues/405) le décrit B2, M, B1, 3, 2, 1 sans conclure clairement) et polarité.

**Conclusion : bus = BSB**, adresse cible 0x00, adresse propre 0x42 (valeurs par défaut).

---

## 4. Types de messages

| Type | Code | Sens | Utilisé par BSB-LAN |
|---|---|---|---|
| QINF | 0x01 | demande d'information (diffusion) | `GetDevId()`, paramètres `FL_QINF_ONLY` |
| INF | 0x02 | information spontanée ou diffusée | réception (heure 0x0500006C, ECS 0x31000212, brûleur/compresseur 0x05000213 : `include/broadcast_msg_handling.h:14-105`) ; émission pour la T° ambiante 10000-10002 (`FL_FORCE_INF`) |
| SET | 0x03 | écriture | `set()` (`BSB_LAN/BSB_LAN.ino:2899`) |
| ACK / NACK | 0x04 / 0x05 | acquittement de SET | contrôle du résultat |
| QUR / ANS | 0x06 / 0x07 | lecture | `query()` (`BSB_LAN/BSB_LAN.ino:3937`) |
| ERR | 0x08 | paramètre inconnu ou refusé | erreur 7 / 261 |
| QRV / ARV | 0x0F / 0x10 | valeur par défaut | `/R`, `/JR` |
| IQ1/IA1, IQ2/IA2 | 0x12-0x15 | lecture de la structure interne (non documentée) | `/QD` (dump pour liste spécifique) |

---

## 5. Implémentation dans le code

| Élément | Où | Rôle |
|---|---|---|
| `class BSB` | `BSB_LAN/src/BSB/bsb.h:46-83` | état : type de bus, adresses, `len_idx`, `pl_start`, `offset`, pointeur `Stream* serial` (= `Serial1`) |
| `enableInterface()` | `bsb.cpp:36-54` | init UART 4800 8O1 sur les broches choisies |
| `GetMessage()` | `bsb.cpp:179-295` | non bloquante si FIFO vide ; resynchronisation sur SOF, lecture jusqu'à la longueur annoncée, CRC |
| `Send()` | `bsb.cpp:516-649` | construit la trame, purge RX, `_send()`, attend la réponse correspondante (3 s) |
| `_send()` | `bsb.cpp:353-514` | attente bus libre, émission ^0xFF, détection de collision par écho |
| Décodage applicatif | `include/print_telegram.h:724` (`printTelegram`) | trame → `decodedTelegram` (valeur, unité, énum, erreur) |
| Diffusions | `include/broadcast_msg_handling.h` | compteurs internes 20000-20005 |

**Points de vigilance pour le C3** :
1. `rx_pin_read()` utilise `portInputRegister(digitalPinToPort())` (`bsb.cpp:651-653`). Ces macros existent dans arduino-esp32 pour toutes les cibles, puisque la cible Olimex C3 compile déjà [SUPPOSÉ ; confirmé par le build de mesure, cf. 07].
2. `Serial1` correspond à UART1 sur le C3, qui n'a que 2 UART (UART0 et UART1 ; cf. 07). `Serial` (debug) doit passer par l'USB-CDC natif (SuperMini) ou par UART0 via le pont CH340 (kit Ai-Thinker) : il n'y a pas de conflit avec UART1.
3. Les deux UART du C3 ont un FIFO RX matériel de 128 octets [SUPPOSÉ, valeur du TRM]. Il contient au moins une trame complète (32 o), donc pas de risque de perte, même si `loop()` est bloquée quelques ms par le WiFi.
