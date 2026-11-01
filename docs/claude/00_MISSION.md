# Mission : BSB-LAN minimal sur ESP32-C3 pour Atlantic Alféa Extensa Duo A.I.

> Fichier de référence pour Claude Code. Le relire au début de chaque session et avant chaque nouvelle phase.

## 1. Contexte

- **Demandeur** : ingénieur électronique (logiciel embarqué, cartes, câblage, automatisme). Les explications peuvent être techniques. Il attend des justifications chiffrées, pas des affirmations.
- **Dépôt** : fork de BSB-LAN (https://github.com/fredlcore/BSB-LAN), cloné dans le dossier courant.
- **Équipement cible** : pompe à chaleur Atlantic **Alféa Extensa Duo A.I.** (régulateur à identifier, cf. §6.1).
- **Objectif** : obtenir une version de BSB-LAN qui
  - tourne sur un **ESP32-C3**, soit une **ESP32-C3 SuperMini**, soit une **Ai-Thinker NodeMCU-Series ESP-C3-32S-Kit** ;
  - n'embarque que **le strict minimum** pour piloter et superviser cette PAC ;
  - se connecte en **Wi-Fi** ;
  - s'intègre à **Home Assistant**, de préférence par MQTT avec auto-discovery.

## 2. Règles de travail (non négociables)

### 2.1 Git
1. **Ne jamais modifier, committer ni pousser sur `master`.**
2. Créer la branche `alfea-extensa` à partir de `master` à jour, puis travailler exclusivement dessus.
3. Faire des **commits atomiques au fil de l'eau**, avec un message au format *Conventional Commits* en français, mais de manière cohérente. Exemples : `docs(claude): analyse du protocole BSB`, `feat(esp32c3): ajout env PlatformIO`, `refactor(cmdtbl): réduction aux paramètres Alféa`.
4. Aucun `git push`, `git push --force`, `rebase` de branches partagées ni suppression de branche sans accord explicite.
5. Vérifier que le build passe avant chaque commit de code. Si ce n'est pas possible, le signaler explicitement dans le message du commit.

### 2.2 Documentation
- Toute la documentation produite va dans **`docs/claude/`**.
- Format : Markdown, avec des schémas Mermaid quand c'est pertinent (diagrammes de séquence, de blocs, d'états).
- Chaque document commence par un résumé de 5 lignes maximum, puis le détail.
- Citer les fichiers et lignes du code source analysé, au format `chemin/fichier.ext:ligne`.
- Distinguer clairement ce qui est **constaté** dans le code ou la doc de ce qui est **supposé** ou reste **à vérifier**.

### 2.3 Environnements : Docker
- Tous les environnements de build, de test et de dev passent par **Docker / docker compose**. Pas d'installation de toolchain sur l'hôte, sauf pour le flash USB si le passage USB vers le conteneur est impossible (cas Windows et macOS, à documenter).
- Prévoir au minimum :
  - un conteneur **PlatformIO** pour compiler (et, sous Linux, flasher via `--device`) ;
  - une stack **Mosquitto + Home Assistant** pour les tests d'intégration ;
  - si c'est faisable, un **simulateur ou mock du bus BSB**, par exemple un script qui rejoue des trames capturées, pour tester sans la PAC.
- Fichiers Docker dans `docker/`, avec un `README` d'utilisation dans `docs/claude/`.

### 2.4 Sécurité vis-à-vis de l'équipement réel
- Le firmware doit être en **lecture seule par défaut** : écriture des paramètres désactivée tant que l'utilisateur ne l'a pas activée explicitement dans la configuration.
- Ne jamais proposer de procédure de test qui écrit sur la PAC sans un avertissement clair et une liste des paramètres concernés.
- L'interface matérielle doit garantir l'**isolation entre le bus et l'ESP32**. Justifier tout écart par rapport à l'adaptateur officiel.

### 2.5 Points d'arrêt obligatoires
Claude Code **s'arrête et attend une validation explicite** :
- **GATE 1** : à la fin des phases 1 et 2 (analyse et faisabilité) ;
- **GATE 2** : à la fin de la phase 3 (plan de migration et design de la carte). **Aucune implémentation avant cette validation.**
- **GATE 3** : avant tout premier test sur la PAC réelle.

À chaque gate, présenter un résumé, les décisions à prendre et les questions ouvertes.

## 3. Phase 0 : mise en place
1. `git status`, `git fetch`, s'assurer que `master` est propre et à jour avec le remote.
2. `git checkout -b alfea-extensa master`.
3. Créer `docs/claude/` avec un `README.md` servant d'index, mis à jour à chaque nouveau document.
4. Copier ce fichier de mission dans `docs/claude/00_MISSION.md`.
5. Commit : `chore: init branche alfea-extensa et docs/claude`.

## 4. Phase 1 : analyse de BSB-LAN

Document **`docs/claude/01_architecture_bsb-lan.md`**, qui couvre :
1. **Structure du dépôt** : arborescence commentée, rôle de chaque fichier ou dossier majeur, système de build (Arduino IDE / PlatformIO), plateformes supportées et mécanisme de sélection (`#define`, `BSB_LAN_config.h`, etc.).
2. **Cycle de vie du firmware** : `setup()` puis `loop()`, ordonnancement, gestion du réseau, timers, mémoire (RAM et flash), points chauds.
3. **Table des commandes** (`cmdtbl` / `BSB_LAN_defs.h` / `BSB_LAN_custom_defs.h`) : structure d'une entrée, types de données, conversions, et mécanisme de **génération d'une liste spécifique à l'appareil**. Ce point est crucial pour la réduction de taille.
4. **Configuration** : options de compilation et options runtime (EEPROM / NVS), liste exhaustive des fonctionnalités activables (MQTT, logging, SD, OneWire, DHT, IPWE, Max!, etc.).

Document **`docs/claude/02_protocole_bsb.md`** :
1. Couche physique : niveaux de tension, logique inversée, alimentation par le bus, vitesse et format série (à vérifier dans le code : 4800 bauds, 8O1).
2. Couche liaison : structure d'une trame (SOF, adresses source et destination, longueur, type de message, Command ID, payload, CRC), arbitrage et détection de collision, timings.
3. Différences entre **BSB, LPB et PPS**, et indication du bus présent sur l'Alféa Extensa Duo A.I.
4. Types de messages (QUERY, ANSWER, SET, ACK, INF…) avec des exemples de trames décodées.
5. Implémentation dans le code : classe BSB, réception, émission, gestion des erreurs.

Document **`docs/claude/03_serveur_web_et_api.md`** :
1. Serveur web : routes / URL-commands (`/K`, `/Q`, `/JQ`, `/JS`, etc.), API JSON, authentification, pages servies.
2. Ce qui est indispensable, optionnel ou supprimable dans notre cas.

Document **`docs/claude/04_integration_home_assistant.md`** :
1. MQTT : topics, format des payloads, publication périodique, commandes entrantes.
2. **Auto-discovery Home Assistant** : comment c'est implémenté, quelles entités sont créées.
3. Les autres voies existantes (intégration HA via l'API JSON, REST) et une recommandation.

Document **`docs/claude/05_fonctionnalites.md`** : tableau de toutes les fonctionnalités avec les colonnes *description / fichiers / coût flash-RAM estimé / nécessaire pour Alféa ? (oui / non / optionnel) / justification*.

## 5. Phase 1 bis : analyse de la carte d'interface

Document **`docs/claude/06_carte_interface_bsb.md`** :
1. Recenser les schémas et documents d'adaptateur présents dans le dépôt ou référencés dans la doc officielle (adaptateurs v2, v3 et v4, version ESP32). Ne pas inventer de schéma : si une source n'est pas accessible, le dire.
2. Expliquer le fonctionnement **étage par étage** : protection d'entrée, réception (optocoupleur, seuil de détection), émission (transistor tirant le bus), isolation galvanique, alimentation.
3. Calculs de dimensionnement : résistances, courant LED de l'optocoupleur, CTR, temps de commutation comparés à la vitesse du bus, compatibilité avec une logique 3,3 V.
4. Points de vigilance : polarité du bus, câblage côté PAC (bornier, repérage CL+/CL- ou équivalent, **à vérifier sur la notice Atlantic**), mise à la masse.

## 6. Phase 2 : étude de faisabilité ESP32-C3

Document **`docs/claude/07_faisabilite_esp32c3.md`** :

### 6.1 Identification de l'appareil
- Vérifier dans la liste des appareils compatibles BSB-LAN si l'Alféa Extensa Duo A.I. ou son régulateur y figure, et quel bus il utilise.
- Décrire la procédure pour identifier le régulateur réel (paramètres d'identification de famille et de variante d'appareil dans BSB-LAN, à retrouver dans le code) et générer la liste de paramètres spécifique.

### 6.2 Comparaison ESP32 classique / ESP32-C3
Comparer : cœurs (Xtensa double cœur et RISC-V simple cœur), RAM, flash, UARTs disponibles et capacité d'inversion matérielle, GPIO utilisables et broches de strapping, USB natif (USB-Serial-JTAG), Ethernet (absent sur le C3), support par le framework Arduino-ESP32 et PlatformIO (versions, `board` à utiliser), dépendances de BSB-LAN incompatibles avec le C3 (bibliothèques, code spécifique `ESP32` ou Xtensa, `#ifdef`).

### 6.3 Comparaison des deux cartes candidates
| Critère | ESP32-C3 SuperMini | Ai-Thinker ESP-C3-32S-Kit |
|---|---|---|
| Module, flash | | |
| Antenne et qualité RF | | |
| Interface USB (natif ou pont USB-UART) | | |
| GPIO accessibles, broches de strapping | | |
| Régulateur 3,3 V, consommation, thermique | | |
| Encombrement, intégration sur une carte fille | | |
| Disponibilité, qualité des lots, retours connus | | |

### 6.4 Budget mémoire
Estimer flash et RAM pour la configuration minimale. Vérifier la marge OTA, la table de partitions et le tas disponible avec Wi-Fi, MQTT et le serveur web actifs.

### 6.5 Conclusion
Faisable ou non, risques, et **choix argumenté d'une carte**.

➡️ **GATE 1** : s'arrêter ici, présenter la synthèse et attendre la validation.

## 7. Phase 3 : plan de migration et design de la carte

Document **`docs/claude/08_plan_migration.md`** :
1. Stratégie de réduction : désactivation par `#define` (préférée, pour rester proche de l'amont et faciliter les rebases) ou suppression de code. Justifier, en visant à **minimiser le diff avec l'amont**.
2. Liste des étapes, chacune avec ses critères de validation et le commit prévu.
3. Environnement PlatformIO dédié (`env:esp32c3_alfea` ou équivalent).
4. Gestion de la configuration : identifiants Wi-Fi hors du dépôt (fichier ignoré par git ou portail de configuration), paramètres MQTT.
5. Liste des paramètres Alféa exposés dans HA : températures (extérieure, départ, retour, ECS), consignes, modes, état du compresseur et de l'appoint, erreurs, etc. Proposer la liste, que l'utilisateur validera.
6. Stratégie de test : build en CI Docker, mock du bus, test HA en Docker, puis tests sur la PAC réelle en lecture seule.
7. Risques et plan de repli.

Document **`docs/claude/09_design_carte_interface.md`** :
1. Schéma fonctionnel (Mermaid) et schéma électrique détaillé : liste des composants avec références et valeurs, ou netlist textuelle.
2. Adaptation à la carte choisie : brochage, GPIO RX et TX, LED d'état, bouton éventuel.
3. Alimentation de l'ESP32 : par le bus si la puissance disponible le permet (à vérifier et chiffrer), sinon externe. Justifier.
4. Isolation, protections (TVS, fusible, polarité), contraintes CEM et environnement chaufferie.
5. Proposition de format : carte fille sur laquelle on enfiche la carte ESP32-C3, avec les dimensions.
6. Nomenclature (BOM) avec des références courantes.
7. Optionnel : fichiers KiCad dans `hardware/alfea-esp32c3/`, uniquement après validation.

➡️ **GATE 2** : s'arrêter et attendre la validation du plan et du design.

## 8. Phase 4 : implémentation (après GATE 2 uniquement)
- Suivre le plan validé, étape par étape, avec un commit par étape.
- Build Docker vert à chaque étape.
- Mettre à jour `docs/claude/10_journal_implementation.md` : décisions, écarts au plan, problèmes rencontrés.
- Rapport de taille (flash et RAM) avant et après réduction.

➡️ **GATE 3** : avant le premier branchement sur la PAC réelle.

## 9. Phase 5 : documentation finale

Document **`docs/claude/11_guide_utilisateur.md`** :
1. **Matériel** : câblage de la carte d'interface à la PAC (avec avertissements de sécurité : coupure de l'alimentation, intervention sur les borniers).
2. **Compilation** avec Docker.
3. **Flash de l'ESP32-C3** :
   - sous Linux, depuis le conteneur (`--device /dev/ttyACM0` ou `ttyUSB0`) ;
   - sous Windows et macOS, avec `esptool` sur l'hôte ou un flasheur web ;
   - mode bootloader (BOOT + RESET), particularités de l'USB natif du C3 ;
   - mises à jour OTA ensuite.
4. **Première mise en service** : configuration Wi-Fi et MQTT, vérification de la communication avec la PAC, lecture des paramètres.
5. **Tests** : procédure de validation, d'abord en lecture seule, puis en écriture si elle est activée.
6. **Intégration Home Assistant** : broker MQTT, découverte automatique, exemple de tableau de bord, exemples d'automatisations.
7. **Dépannage** : symptômes courants et leurs causes.

## 10. Définition de « terminé »
- [ ] Branche `alfea-extensa` avec un historique de commits lisible ; `master` intact.
- [ ] Docs 00 à 11 présentes dans `docs/claude/` et indexées.
- [ ] Firmware compilé en Docker pour la carte choisie, avec un rapport de taille.
- [ ] Lecture des paramètres validée sur la PAC réelle.
- [ ] Entités remontées automatiquement dans Home Assistant.
- [ ] Guide de flash, de test et d'intégration HA rédigé.