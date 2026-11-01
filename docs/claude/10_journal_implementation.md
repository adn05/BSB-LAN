# 10 — Journal d'implémentation (Phase 4)

> **Résumé**
> Phase 4 réalisée, à l'exception de **E6 et E7, écartées après mesure** (J14). Firmware Alféa : **1 410 705 o de flash (71 %, marge OTA de 29 %)** et **49 104 o de RAM statique**, contre 1 610 749 o et 65 624 o pour l'amont (**−200 044 o de flash, −16 520 o de RAM**).
> Lecture seule par défaut sans modifier le code (`DEFAULT_FLAG FL_RONLY`) ; écriture optionnelle limitée à une liste blanche (variante `alfea-ecriture`). Routes `/Y`, `/YR`, `/JY` et `/G` retirées ; mot de passe de l'AP configurable ; filtre d'IP de confiance corrigé. **Diff sur le code amont : 27 lignes ajoutées, 4 supprimées, dans `BSB_LAN/BSB_LAN.ino` seulement.**
> Validé sans matériel : builds, simulateur (autotest 13/13), pile HA. **Restent les tests sur banc (T1, T2) avec un SuperMini**, puis la GATE 3.
> Toutes les tailles sont **mesurées** par `sh docker/compiler.sh <cible>` (arduino-cli 1.3.1, esp32 3.3.12, `esp32c3`, `min_spiffs`, partition app de 1 966 080 o).

## Tableau de taille

| Étape | Cible | Flash | % app | RAM statique | Commit |
|---|---|---|---|---|---|
| E0 | amont non modifié (référence) | 1 610 749 o | 81 % | 65 624 o | E0 |
| E1 | alfea : configuration, liste réduite 96 entrées, lecture seule par `DEFAULT_FLAG` | 1 638 949 o | 83 % | 65 680 o | E1 |
| E2 | alfea (lecture seule, garde exclue) | 1 638 949 o | 83 % | 65 680 o | E2 |
| E2 | alfea-ecriture (`ALFEA_ECRITURE` : `DEFAULT_FLAG FL_SW_CTL_RONLY` + `WRITE_WHITELIST`) | 1 639 155 o | 83 % | 65 680 o | E2 |
| E3 | amont (gardes inactives : identique à E0) | 1 610 749 o | 81 % | 65 624 o | E3 |
| E3 | alfea + `NO_RAW_TELEGRAMS`, `NO_GPIO_URL` | 1 636 511 o | 83 % | 65 680 o | E3 |
| E3 | alfea-ecriture | 1 636 717 o | 83 % | 65 680 o | E3 |
| E4 | amont (correctif IP de confiance, message AP) | 1 610 807 o | 81 % | 65 624 o | E4 |
| E4 | alfea + `AP_PASSWORD` | 1 636 573 o | 83 % | 65 680 o | E4 |
| E4 | alfea-ecriture | 1 636 779 o | 83 % | 65 680 o | E4 |
| E5 | alfea + `NO_TLS` + `MAX_HEATINGTBL 1` | 1 410 705 o | 71 % | 49 104 o | E5 |
| E5 | alfea-ecriture | 1 410 911 o | 71 % | 49 104 o | E5 |

## Décisions et écarts au plan

| # | Étape | Décision ou écart | Raison |
|---|---|---|---|
| J1 | E0 | arduino-cli épinglé en **1.3.1** (archive officielle, sha256 vérifié), délai réseau de 1 800 s et 3 tentatives pour le téléchargement du core | le premier essai a échoué sur « context deadline exceeded » pendant le téléchargement de la chaîne RISC-V (563 Mo) |
| J1b | E0 | `ARDUINO_DIRECTORIES_DOWNLOADS=/tmp/arduino-staging` passé au lancement | le conteneur tourne sous l'utilisateur courant (fichiers de sortie non root) et ne peut pas créer de répertoire dans `/opt/arduino` |
| J2 | E1 | `LogDestination = FLASH` imposé | avec `SDCARD`, `startLoggingDevice()` appelle `SPI.begin(18, 19, 23, 5)` (`BSB_LAN/BSB_LAN.ino:7629`). Sur le C3, GPIO18/19 sont les lignes **USB D−/D+** : la console et le flash USB seraient perdus, et GPIO23 n'existe pas |
| J3 | E2 | lecture seule par **`#define DEFAULT_FLAG FL_RONLY`** dans la configuration (mécanisme prévu par l'amont, `BSB_LAN/BSB_LAN_config.h.default:127-132`) au lieu d'une garde `FORCE_READ_ONLY` dans le code | même effet sans modifier le code : toutes les entrées de la table globale portent `DEFAULT_FLAG` ou `FL_RONLY` (seule exception : 15042 `FL_NO_CMD`, que `findLine()` ignore), et toute écriture SET/INF passe par `set()` → `programIsreadOnly()` (`BSB_LAN/BSB_LAN.ino:2922`), hors routes brutes (E3) |
| J4 | E2 | le générateur force `FL_RONLY` (en gardant `FL_OEM`) sur toute entrée hors liste blanche `alfea/params/ecriture.txt` | sans cela, une entrée marquée seulement `FL_OEM` (ex. 8451) resterait modifiable avec `DEFAULT_FLAG = FL_RONLY`, et la discovery HA présenterait comme modifiables des paramètres hors liste |
| J5 | E2 | garde `WRITE_WHITELIST` dans `set()` en plus des drapeaux | en mode écriture (`DEFAULT_FLAG = FL_SW_CTL_RONLY`), les entrées globales PPS 15000-15086 et les paramètres virtuels deviendraient modifiables ; la garde refuse toute ligne hors `write_whitelist[]` |
| J6 | E1 | la lecture seule par configuration (J3) et le marquage `FL_RONLY` du générateur (J4) sont livrés dès E1 ; E2 ne garde que la garde `WRITE_WHITELIST` dans le code et la variante de build avec écriture | aucun build Alféa n'existe sans lecture seule, même entre deux étapes |
| J7 | E2 | test fonctionnel de la garde (SET refusé hors liste, accepté dans la liste) reporté au simulateur (E8) | nécessite une carte C3 ; à ce stade, preuve par compilation des deux variantes (+206 o pour la garde) |
| J8 | E2 | scripts `docker/*.sh` remis en fins de ligne LF | une réécriture sous Windows les avait passés en CRLF (`set: Illegal option -`) ; `docker/.gitattributes` impose LF à l'extraction |
| J9 | E3 | contrôle dans le binaire : le message « …in order to use /Y command! » est présent dans l'image amont et absent de l'image Alféa | preuve que les routes `/Y` sont retirées ; test HTTP sur carte en E8 |
| J10 | E4 | correctif du filtre d'IP de confiance **sans garde** (comportement amont modifié) | c'est un bug : avec une seule adresse configurée, personne n'était rejeté (`BSB_LAN/BSB_LAN.ino`, `client_flag`). Table de vérité vérifiée : aucune adresse → accepté ; adresse 1 seule → seul ce client accepté ; deux adresses → l'une ou l'autre. Test HTTP sur carte en E8 |
| J11 | E4 | le message de débogage de l'AP ne révèle plus le mot de passe configuré | il s'affichait en clair sur la console |
| J12 | E4 | `static_assert` sur la longueur de `ALFEA_AP_PASSWORD` (≥ 8 caractères) | WPA2 refuse un mot de passe plus court ; l'AP de secours ne démarrerait pas |
| J13 | E5 | gain mesuré : −225 868 o de flash (−13,8 %) et −16 576 o de RAM | supérieur à l'estimation de 05 §3 (bundle de CA 56 Ko + SSL ≈ 100-120 Ko) : mbedTLS et le client sécurisé partent entièrement ; la RAM correspond à `heating_cmdtbl` (500 × 32 o = 16 000 o) plus les tampons TLS |
| J14 | E6, E7 | **non réalisées** : journalisation fichier (`NO_LOGGING_FS`) et modules capteurs (`NO_ONEWIRE`…) restent compilés, inactifs | mesuré dans le `.map` d'E5 : système de fichiers ≈ 77 Ko au maximum (LittleFS 33 905, FatFS 22 201, SD 7 401, FS 6 919, journal 6 484 o), soit ≈ 4 points de partition ; il faudrait poser des gardes sur une centaine de sites de `BSB_LAN.ino`, le plus gros diff du projet. L'image est à 71 % (seuil 85 %, marge OTA de 29 %) : le gain ne justifie pas le diff ni le risque de rebase. Aucun effet fonctionnel : `LoggingMode` n'écrit rien sur le système de fichiers. Réversible si besoin de place |
| J15 | E8 | simulateur `alfea/tools/bsb_sim.py` : autotest 13/13 en Docker (CRC 0x3F7B du code amont, trame d'identification du dump, SET et ACK de la PR #812, QUR 8700, encodage des types utilisés) | la boucle série (écho, temporisations) reste à valider sur banc, avec un SuperMini et un adaptateur USB-UART : c'est le test T1 |
| J16 | E8 | le simulateur renvoie l'**écho** de chaque octet | sans écho, BSB-LAN prendrait la réponse, arrivée dans sa fenêtre de 50 ms, pour une collision (`src/BSB/bsb.cpp:488-503`) |
| J17 | E9 | pile `docker/ha-test` (Mosquitto 2.0.22, HA 2026.10.4) démarrée : HA répond sur 8123 (302 vers la création de compte), 0 ligne d'erreur dans ses journaux ; vérificateur de discovery testé sur messages factices (anomalies détectées dans les deux modes) | la discovery réelle sera vérifiée avec le firmware sur banc (T2), car elle demande le SuperMini |
| J18 | après E10 | **J16 amendée** : l'écho logiciel du PC arrive trop tard. Après `serial->flush()`, BSB-LAN attend le premier octet puis lit toute sa trame d'un coup avec `readByte()` non bloquant (`bsb.cpp:488-503`, `:655-661`). Tout octet d'écho absent à cet instant est lu comme 0x00, d'où une collision. Écho réalisé par le **pont ESP32-C3 en ET câblé** (interruption GPIO, latence de quelques µs pour des bits de 208 µs) | l'option `--pont` du simulateur coupe l'écho logiciel. Sans pont, l'écho via adaptateur USB-UART reste disponible mais risque des collisions [SUPPOSÉ, non mesuré] |
| J19 | après E10 | pont sur **NodeMCU ESP-C3-32S-Kit** (matériel de l'utilisateur) : USB par CH340 sur l'UART0, donc 115 200 bauds côté PC ; lignes IO6/IO7, UART interne sur IO10 ; IO3/4/5 et IO18/19 évitées (LED de la carte) | broches LED de la carte [À VÉRIFIER sur la sérigraphie] |
| J20 | carte | schéma maître = fichier KiCad retouché par l'utilisateur ; le générateur ne l'écrase plus ; `carte.py` aligné, parité DRC 0. La retouche corrige la commande de Q1 (R1 en série dans le collecteur de OK2 dans ma rev B : niveau bas ≈ 4,6 V à 5 mA de bus) | 09 §2.3 |
| J21 | carte | routage par **Freerouting 2.1.0** en conteneur, nettoyage des segments en double ou en impasse, plan GND côté ESP32 : DRC 0 toutes sévérités | routage non reproductible au tracé près ; contrôles toujours à 0. À relire avant commande |
| J23 | carte | **D3 déplacée** entre `BUS_P` et `CL_N_IN`, en amont de D2 (décision de l'utilisateur) ; notes du schéma maître mises à jour. Plaquette : D3 debout au pas de 2,54 mm (D10-E10), Q1, R7, R1, R2 décalés de 2 trous, coupe E9 → E11. ERC 0, DRC 0 toutes sévérités et parité 0 sur les deux cartes | les surtensions positives ne passent plus par D2 (09 §5) |
| J24 | banc | environnement de flash `alfea/build/venv` (esptool 5.6.0, pyserial 3.5, `alfea/tools/requirements-flash.txt`) et `alfea/tools/flasher.py` ; pont recompilé en 2 Mo (module ESP-C3-32S, 2 Mo mesurés). Pont et SuperMini flashés, images vérifiées par esptool. 1er démarrage : réseau WiFi configuré absent du scan (4 réseaux vus, -69 à -74 dBm), repli sur l'AP `BSB-LAN` 192.168.4.1 | flash hors Docker : USB inaccessible depuis Docker Desktop sans usbipd |
| J22 | carte | **variante traversante** pour plaquette à bandes (14 × 57), vérifiée par le DRC (bandes = pistes) ; D5 non montée faute d'équivalent traversant à faible fuite | 09b |

## Rapport de taille final (E10)

| | Amont (E0) | Alféa (E5, final) | Écart |
|---|---|---|---|
| Flash (image app) | 1 610 749 o (81 %) | **1 410 705 o (71 %)** | **−200 044 o (−12,4 %)** |
| RAM statique | 65 624 o | **49 104 o** | **−16 520 o (−25 %)** |
| Marge OTA dans la partition app | 355 331 o | **555 375 o** | +200 044 o |

Principaux postes retirés (d'après `alfea/build/*/taille.txt`) : mbedTLS (`libmbedtls` + `libmbedtls_2` ≈ 115 Ko, `libmbedcrypto` −37 Ko), code du sketch −48 Ko (client TLS et bundle de certificats, routes retirées), `heating_cmdtbl` −16 000 o de RAM. Ajoutés : la liste réduite 211/127 (+27 784 o par rapport à la liste par défaut, surtout la table de textes des codes d'erreur).

## Diff sur le code amont

`git diff 41558d24 -- BSB_LAN/` : un seul fichier, `BSB_LAN/BSB_LAN.ino`, **+27 / −4 lignes**.
| Garde ou correctif | Lignes |
|---|---|
| `WRITE_WHITELIST` dans `set()` | +11 |
| `NO_RAW_TELEGRAMS` (`/Y`, `/YR`, `/JY`) | +4 |
| `NO_GPIO_URL` (`/G`) | +2 |
| `AP_PASSWORD` | +3, et 2 lignes remplacées (+2 / −2) |
| filtre d'IP de confiance | +5 / −2 (commentaire de 2 lignes, condition de 3 lignes au lieu de 2) |

Tout le reste est hors de `BSB_LAN/` : `alfea/`, `docker/`, `docs/claude/`.

## Reste à faire avant la GATE 3 (nécessite le matériel)

| Test | Moyen | Critère |
|---|---|---|
| T1 banc | SuperMini + **pont NodeMCU ESP-C3-32S-Kit** (`pont_bsb`) + `bsb_sim.py --pont` (README_docker §3) | identification 211/127, valeurs du scénario lues, **aucun « SET reçu »** en lecture seule, `/Y` `/JY` `/G` inopérants, garde de liste blanche (variante écriture), IP de confiance |
| T2 HA | pile `docker/ha-test` + `verif_discovery.py` | « CONFORME » en lecture seule ; entités, unités, disponibilité |
| Carte | plaquette (09b) ou carte CMS fabriquée, sans PAC | 3,3 V présent, LED D1 éteinte sans bus, TX au repos pendant le démarrage (R8), bus de banc 15 V + seconde carte |
