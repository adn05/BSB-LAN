# 15 — Option B : carte non isolée, alimentée par G+ (schéma complet)

> **Résumé**
> Demande de l'utilisateur : schéma complet **sans optocoupleur**, avec un **bornier d'entrée 3 points** (CL+, CL-, G+), des **circuits logiques plutôt que des transistors**, et **sans limiteur de courant** pour cette première version.
> Le schéma est seul, sans PCB : `alfea/hardware/carte_bsb_c3_b/carte_bsb_c3_b.kicad_sch`. Le schéma maître `carte_bsb_c3` et son PCB routé ne sont pas touchés.
> - **Alimentation** : G+ → SS14 → abaisseur synchrone **AP63205WU-7** (5 V fixe, démarrage progressif de 4 ms) → `5V_IN` → D4 → SuperMini, comme avec J2 sur le maître.
> - **Réception** : pont 100 k / 33 k vers un **74HC14** (inverseurs à seuil de Schmitt). Deux portes en série donnent RX au même niveau que le bus.
> - **Émission** : une porte du 74HC14 commande un **2N7002** qui tire CL+ à la masse. C'est le seul composant discret côté bus, car aucun circuit logique ne supporte 12 V en sortie.
> - **Même polarité RX/TX que V3** : aucun changement logiciel.
> - ERC 0 [CONSTATÉ, `kicad/kicad:9.0.6`], netlist contrôlée net par net.
> **Pas d'isolation : GND = CL- = X86-2.** Carte raccordée à la PAC, l'USB-C ne se branche que sur un PC portable sur batterie ou à travers un isolateur USB (§5).

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**.

---

## 1. Schéma

Six blocs câblés. Les masses et les rails passent par des symboles d'alimentation ; les étiquettes ne servent qu'aux liaisons entre blocs (`BUS_P`, `RX`, `TX`, `DHT_IO`) et aux barrettes du SuperMini.

| Bloc | Composants | Rôle |
|---|---|---|
| 1. Entrée | J1 HC-JXDZVC-3.5-3P (fiche JJ1 HC-JXDZK-3.5-3P), D3 et D6 SMAJ18CA | J1-1 = CL+ (X86-1), J1-2 = CL- (X86-2), J1-3 = G+ (X86-3) : câblage 1-1, 2-2, 3-3. D3 et D6 écrêtent CL+ et G+ |
| 2. Alimentation | D2 SS14, C6, R6, U2 AP63205WU-7, C9, L1 4,7 µH, C7 et C8, D4 | G+ vers 5 V. Valeurs du tableau 3 de la datasheet Diodes (L 4,7 µH, Cin 10 µF, Cout 2 × 22 µF, Cboot 100 nF) [CONSTATÉ] |
| 3. Réception | R1 100 k, R2 33 k, C4 100 pF, U1A, U1B, U1D, R3, D1 | CL+ vers RX (GPIO6) ; U1D recopie le bus sur la LED |
| 4. Émission | R7 10 k, U1C, R4 100 Ω, R5 100 k, Q1 2N7002 | TX (GPIO7) vers CL+ |
| 5. U1 | U1G (alimentation), C5 ; U1E et U1F, entrées à la masse | |
| 6. SuperMini, DHT22 | J4, J5, C1 à C3, J3, R9, R10, D5 | **repris tels quels du schéma maître** (mêmes valeurs et références JLCPCB) |

**Retirés par rapport au maître** : U1 et U2 (LTV-4N25), Q1 et Q2 (BC847C, BC857C), R1 à R8 de l'interface bus, D2 (1N4148W dans le retour CL-), J2 (entrée 5 V, inutile puisque G+ alimente la carte), J1 2 points.

## 2. Alimentation (G+ vers 5 V)

| Grandeur | Valeur |
|---|---|
| Entrée de U2 | 11,6 V − 0,3 V (D2) ≈ **11,3 V** ; plage de U2 : 3,8 à 32 V [CONSTATÉ, datasheet] |
| Courant moyen sur G+ | 0,5 W / 0,87 / 11,3 V ≈ **51 mA** [SUPPOSÉ : rendement ≈ 87 % à 100 mA, courbe de la datasheet en 12 V → 5 V] |
| Pointe d'émission WiFi (0,36 A sur 5 V) | 1,75 W / 0,87 / 11,3 V ≈ **180 mA** sur G+, sans limiteur ni réserve |
| Mise sous tension | démarrage progressif interne de 4 ms : charge de 66 µF (C7, C8, C1) sous 5 V, soit ≈ 83 mA plus la charge. C6 (22 µF) se charge directement sur G+ : 1,4 mJ, limité par l'impédance de G+ |
| Ondulation dans L1 | (11,3 − 5) × 5 / (11,3 × 4,7 µH × 1,1 MHz) ≈ 0,54 A crête à crête : le régulateur passe en mode PFM aux faibles charges (prévu, 88 % à 5 mA selon la datasheet) |
| EN | tiré à VIN par R6 (100 kΩ) : démarrage automatique, verrouillage interne sous 3,1 V [CONSTATÉ, datasheet] |
| Surtension | D6 (SMAJ18CA) : écrêtage ≤ 29,2 V, sous les 32 V de fonctionnement de U2 |

**Sans limiteur** (choix de l'utilisateur pour cette version), G+ voit directement les pointes d'émission, environ 180 mA. L'**essai de charge de G+** (14 §6) reste le prérequis ; il faut le compléter par un palier proche de **180 mA** (résistance de 68 Ω, 2 W pendant quelques secondes). Le limiteur de la variante A (14 §3) pourra s'ajouter en amont de U2 si l'essai montre une sortie G+ fragile. Il faudrait alors programmer l'UVLO par EN (pont R5/R6 de la datasheet), car un régulateur à découpage derrière un limiteur peut se bloquer au démarrage.

## 3. Réception (CL+ vers RX)

Pont R1 / R2 : rapport 33 / 133 = **0,248**. Le 74HC14 est alimenté en 3,3 V.

| Grandeur | Valeur |
|---|---|
| Bus haut 11,5 V | 2,85 V sur U1A |
| Seuils du 74HC14 sous 3,3 V | VT+ ≤ 2,31 V, VT- ≥ 0,65 V **[SUPPOSÉ : interpolation linéaire des valeurs de la datasheet Nexperia à 2,0 et 4,5 V, à vérifier au banc]** |
| Seuils vus sur le bus | montant ≤ 2,31 / 0,248 = **9,3 V** ; descendant ≥ 0,65 / 0,248 = **2,6 V** |
| Marge | bus haut 11,5 V contre 9,3 V (×1,24) ; bas du bus ≈ 0,2 à 1,6 V contre 2,6 V |
| Charge du bus | 11,5 V / 133 kΩ = **86 µA**, contre ≈ 6 mA pour U1 + D1 sur V3 |
| Bus à 15 V | 3,72 V, sous VCC + 0,5 V (3,8 V) : pas d'injection dans les diodes d'entrée |
| Surtension (29 V écrêtés par D3) | 7,2 V au pont : courant d'injection ≤ (7,2 − 3,8) / 24,8 kΩ ≈ 0,14 mA, bref, admissible (20 mA max. selon la datasheet) |
| Filtre C4 | τ = 24,8 kΩ × 100 pF = 2,5 µs, pour un bit de 208 µs |

U1A inverse, U1B rétablit le niveau : **RX = niveau du bus**, comme le phototransistor de V3. U1D, branché après U1A, recopie aussi le bus sur la LED D1 (1,5 mA pris sur le 3,3 V, pas sur le bus). D1 est allumée au repos et clignote au trafic, comme V3. Si J1 est branché par erreur sur G+, la LED reste fixe.

## 4. Émission (TX vers CL+)

| Grandeur | Valeur |
|---|---|
| TX haut (repos) | U1C en sortie basse, Q1 bloqué, bus libre |
| TX bas | U1C en sortie haute (3,3 V), Q1 conduit, CL+ tiré à **≈ 0,2 V** [SUPPOSÉ : R_DS(on) de quelques ohms sous V_GS 3,3 V, non spécifié en dessous de 4,5 V, **à mesurer**], pour quelques dizaines de mA de bus [SUPPOSÉ, 09 §2.3]. V3 descendait à environ 1,5 V |
| Démarrage, GPIO en haute impédance | R7 tire TX à 3,3 V : Q1 reste bloqué (rôle de R8 sur le maître) |
| 3,3 V absent | U1 n'est pas alimenté, R5 tient la grille à 0 : Q1 bloqué |
| Courant admissible de Q1 | 115 mA en continu, 800 mA en impulsion (2N7002 CJ) : suffisant si la source du bus est limitée, comme supposé pour V3 [SUPPOSÉ, 06 Q5] |

**Polarité identique à V3 et au maître** : RX suit le bus et TX bas met le bus à 0. La configuration BSB-LAN (`bus_pins = {6, 7}`) ne change pas [SUPPOSÉ : écho de nos propres trames identique à V3, **à vérifier au banc T1**].

## 5. Conséquences de l'absence d'isolation

| Sujet | Effet | Disposition |
|---|---|---|
| USB-C | la masse de l'ESP32 est CL- de la PAC. Un PC fixe relié à la terre par sa prise relie la terre à CL- : courant de boucle, perturbation du bus, risque pour le port USB si CL- n'est pas au potentiel de la terre [SUPPOSÉ : référence de CL- inconnue] | carte raccordée : PC portable **sur batterie** ou isolateur USB (ADuM3160 ou équivalent). Pour flasher en temps normal : carte débranchée de X86 |
| Surtensions | elles arrivent sur la logique sans barrière | D3 et D6 en entrée, R1 (100 kΩ) devant U1, RX tamponné par U1B (aucune broche de l'ESP32 n'est reliée au bus) |
| Erreur de câblage 1 ↔ 2 (CL+ et CL- inversés) | carte non alimentée (G+ − « masse » ≈ 0 V) ; la diode interne de Q1 relie CL+ et CL- : **bus en court-circuit** tant que l'erreur dure [SUPPOSÉ : état toléré par la PAC, comme un bit à 0 prolongé] | contrôler au multimètre avant d'enficher la fiche (09 §8) |
| Erreur de câblage 1 ↔ 3 (CL+ et G+ inversés) | U2 se nourrit sur CL+ : ≈ 50 mA tirés sur le bus, **communication de la PAC perturbée**, et la LED reste fixe | même contrôle ; repérer les fils |
| Écart à la mission | décision D6 (« optocoupleurs conservés ») et adaptateur V3 | **choix explicite de l'utilisateur** pour cette option, à valider avant toute fabrication |

## 6. Nomenclature et coût

Sur la carte : **32 composants, 20 références**, contre 27 composants et 19 références pour le maître [CONSTATÉ, BOM exportées] ; le régulateur passe sur la carte. Le chargeur USB et son câble disparaissent.

| Nouvelle référence | JLCPCB | Catégorie |
|---|---|---|
| U2 AP63205WU-7 | C2071056 | **Extended** (frais d'ajout) |
| L1 SWPA4030S4R7MT | C57269 | **Extended** (frais d'ajout) |
| J1 HC-JXDZVC-3.5-3P et JJ1 HC-JXDZK-3.5-3P | C51927059, C51927078 | traversant (forfait de soudure) ; JJ1 hors carte |
| U1 74HC14D Nexperia | C5605 | Basic |
| Q1 2N7002 | C8545 | Basic |
| R1, R5, R6 100 k ; R2 33 k ; R3 1 k ; C4 100 pF | C149504, C17633, C17513, C1790 | Basic |

Les autres composants (SS14, SMAJ18CA, 22 µF, 100 nF, 10 k, 100 Ω, LED, barrettes, J3, DHT22) sont des références du maître. Les deux références Extended sont inévitables : aucun régulateur abaisseur Basic n'a de démarrage progressif et de rendement comparables. Le XL1509-5.0 (Basic) est non synchrone, consomme 2 mA à vide et demande une self de 33 µH et un condensateur électrolytique.

**Empreintes des connecteurs** : J1 utilise l'empreinte Phoenix MCV 3 points de la même famille. La question des perçages de 1,2 mm contre 1,4 mm recommandés par Hong Cheng reste **ouverte**, comme sur le maître. Empreintes non modifiées, conformément à la consigne.

## 7. Avant toute fabrication

1. Essai de charge de G+ (14 §6), avec un palier proche de 180 mA.
2. Repérer CL- au multimètre par rapport à la terre de la chaufferie, PAC sous tension : si CL- est flottant, la règle de l'USB du §5 devient impérative.
3. Banc T1 sur simulateur : seuils réels du 74HC14 sous 3,3 V, niveau bas de Q1, écho des trames, tension du 5 V pendant l'émission WiFi.
4. Décider entre la variante A (doc 14, isolée) et l'option B, puis faire le PCB (non commencé).

## 8. Fichiers

| Fichier | Rôle |
|---|---|
| `alfea/hardware/carte_bsb_c3_b/carte_bsb_c3_b.kicad_sch`, `.kicad_pro` | schéma A3 câblé, 6 blocs |
| `alfea/hardware/carte_bsb_c3_b/alfea.kicad_sym`, `sym-lib-table` | copie du symbole sans broche des fiches (JJ1) |
| `alfea/hardware/carte_bsb_c3_b/sorties/` | `erc.rpt` (0 violation), `schema.pdf`, `schema.png`, `bom.csv` |

Contrôle [CONSTATÉ] : `kicad-cli sch erc --severity-all --exit-code-violations`, puis comparaison de la netlist exportée avec les 20 nets attendus (ensembles de broches identiques).
