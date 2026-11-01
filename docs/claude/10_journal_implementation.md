# 10 — Journal d'implémentation (Phase 4)

> **Résumé**
> Suivi étape par étape du plan 08 (E0 à E10) : ce qui a été fait, mesuré, décidé, et les écarts au plan.
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
