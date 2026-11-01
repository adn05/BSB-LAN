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
