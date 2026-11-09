# 15 — Option B : carte non isolée, alimentée par G+ (schéma et placement)

> **Résumé**
> Demande de l'utilisateur : schéma complet **sans optocoupleur**, avec un **bornier d'entrée 3 points** (CL+, CL-, G+), des **circuits logiques plutôt que des transistors**, et **sans limiteur de courant** pour cette première version.
> Fichiers dans `alfea/hardware/carte_bsb_c3_b/` : schéma complet et **PCB routé par l'utilisateur**, avec vias de couture GND (§7). Le schéma principal `carte_bsb_c3` et son PCB routé ne sont pas touchés.
> - **Alimentation** : G+ → SS14 → abaisseur synchrone **AP63205WU-7** (5 V fixe, démarrage progressif de 4 ms) → `5V_IN` → D4 → SuperMini, comme avec J2 sur la carte principale.
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
| 1. Entrée | J1 HC-JXDZVC-3.5-3P (fiche JJ1 HC-JXDZK-3.5-3P), D3 et D6 SMAJ18CA | **J1-1 = G+ (X86-3), J1-2 = CL- (X86-2), J1-3 = CL+ (X86-1)** : câblage **croisé** 3 → 1, 2 → 2, 1 → 3 (ordre inversé par l'utilisateur au routage, sérigraphie « G+ » en haut et « CL+ » en bas). D3 écrête CL+, D6 écrête G+ |
| 2. Alimentation | D2 SS14, C6, R6, U2 AP63205WU-7, C9, L1 4,7 µH, C7 et C8, D4 | G+ vers 5 V. Valeurs du tableau 3 de la datasheet Diodes (L 4,7 µH, Cin 10 µF, Cout 2 × 22 µF, Cboot 100 nF) [CONSTATÉ] |
| 3. Réception | R1 100 k, R2 33 k, C4 100 pF, U1A (1 → 2), U1E (11 → 10), U1B (3 → 4), R3, D1 | CL+ vers RX (GPIO6) par U1A puis U1E ; U1B recopie le bus sur la LED |
| 4. Émission | R7 10 k, U1D (9 → 8), R4 100 Ω, R5 100 k, Q1 2N7002 | TX (GPIO7) vers CL+ |
| 5. U1 | U1G (alimentation), C5 ; U1C (5) et U1F (13), entrées à la masse | portes permutées par l'utilisateur au routage (version fabriquée) |
| 6. SuperMini, DHT22 | J4, J5, C1 à C3, J3, R9, R10, D5 | **repris tels quels du schéma principal** (mêmes valeurs et références JLCPCB). **Même erreur que la rev A** : rangées J4 / J5 en miroir (09 §10.1), à corriger avant toute fabrication |

**Retirés par rapport à la carte principale** : U1 et U2 (LTV-4N25), Q1 et Q2 (BC847C, BC857C), R1 à R8 de l'interface bus, D2 (1N4148W dans le retour CL-), J2 (entrée 5 V, inutile puisque G+ alimente la carte), J1 2 points.

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

U1A inverse, U1E rétablit le niveau : **RX = niveau du bus**, comme le phototransistor de V3. U1B, branché après U1A, recopie aussi le bus sur la LED D1 (1,5 mA pris sur le 3,3 V, pas sur le bus). D1 est allumée au repos et clignote au trafic, comme V3. Si J1 est branché par erreur sur G+, la LED reste fixe.

## 4. Émission (TX vers CL+)

| Grandeur | Valeur |
|---|---|
| TX haut (repos) | U1D en sortie basse, Q1 bloqué, bus libre |
| TX bas | U1D en sortie haute (3,3 V), Q1 conduit, CL+ tiré à **≈ 0,2 V** [SUPPOSÉ : R_DS(on) de quelques ohms sous V_GS 3,3 V, non spécifié en dessous de 4,5 V, **à mesurer**], pour quelques dizaines de mA de bus [SUPPOSÉ, 09 §2.3]. V3 descendait à environ 1,5 V |
| Démarrage, GPIO en haute impédance | R7 tire TX à 3,3 V : Q1 reste bloqué (rôle de R8 sur la carte principale) |
| 3,3 V absent | U1 n'est pas alimenté, R5 tient la grille à 0 : Q1 bloqué |
| Courant admissible de Q1 | 115 mA en continu, 800 mA en impulsion (2N7002 CJ) : suffisant si la source du bus est limitée, comme supposé pour V3 [SUPPOSÉ, 06 Q5] |

**Polarité identique à V3 et à la carte principale** : RX suit le bus et TX bas met le bus à 0. La configuration BSB-LAN (`bus_pins = {6, 7}`) ne change pas [SUPPOSÉ : écho de nos propres trames identique à V3, **à vérifier au banc T1**].

## 5. Conséquences de l'absence d'isolation

| Sujet | Effet | Disposition |
|---|---|---|
| USB-C | la masse de l'ESP32 est CL- de la PAC. Un PC fixe relié à la terre par sa prise relie la terre à CL- : courant de boucle, perturbation du bus, risque pour le port USB si CL- n'est pas au potentiel de la terre [SUPPOSÉ : référence de CL- inconnue] | carte raccordée : PC portable **sur batterie** ou isolateur USB (ADuM3160 ou équivalent). Pour flasher en temps normal : carte débranchée de X86 |
| Surtensions | elles arrivent sur la logique sans barrière | D3 et D6 en entrée, R1 (100 kΩ) devant U1, RX tamponné par U1E (aucune broche de l'ESP32 n'est reliée au bus) |
| Erreur de câblage CL+ ↔ CL- (J1-3 et J1-2) | carte non alimentée (G+ − « masse » ≈ 0 V) ; la diode interne de Q1 relie CL+ et CL- : **bus en court-circuit** tant que l'erreur dure [SUPPOSÉ : état toléré par la PAC, comme un bit à 0 prolongé] | contrôler au multimètre avant d'enficher la fiche (09 §8) |
| Erreur de câblage CL+ ↔ G+ (par exemple câblage 1-1, 3-3 au lieu du câblage croisé) | U2 se nourrit sur CL+ : ≈ 50 mA tirés sur le bus, **communication de la PAC perturbée**, et la LED reste fixe | même contrôle ; repérer les fils |
| Écart à la mission | décision D6 (« optocoupleurs conservés ») et adaptateur V3 | **choix explicite de l'utilisateur** pour cette option, à valider avant toute fabrication |

## 6. Nomenclature et coût

Sur la carte : **32 composants, 20 références**, contre 27 composants et 19 références pour la carte principale [CONSTATÉ, BOM exportées] ; le régulateur passe sur la carte. Le chargeur USB et son câble disparaissent.

| Nouvelle référence | JLCPCB | Catégorie |
|---|---|---|
| U2 AP63205WU-7 | C2071056 | **Extended** (frais d'ajout) |
| L1 SWPA4030S4R7MT | C57269 | **Extended** (frais d'ajout) |
| J1 HC-JXDZVC-3.5-3P et JJ1 HC-JXDZK-3.5-3P | C51927059, C51927078 | traversant (forfait de soudure) ; JJ1 hors carte |
| U1 74HC14D Nexperia | C5605 | Basic |
| Q1 2N7002 | C8545 | Basic |
| R1, R5, R6 100 k ; R2 33 k ; R3 1 k ; C4 100 pF | C149504, C17633, C17513, C1790 | Basic |

Les autres composants (SS14, SMAJ18CA, 22 µF, 100 nF, 10 k, 100 Ω, LED, barrettes, J3, DHT22) sont des références de la carte principale. Les deux références Extended sont inévitables : aucun régulateur abaisseur Basic n'a de démarrage progressif et de rendement comparables. Le XL1509-5.0 (Basic) est non synchrone, consomme 2 mA à vide et demande une self de 33 µH et un condensateur électrolytique.

**Empreintes des connecteurs** : J1 utilise l'empreinte Phoenix MCV 3 points de la même famille. La question des perçages de 1,2 mm contre 1,4 mm recommandés par Hong Cheng reste **ouverte**, comme sur la carte principale. Empreintes non modifiées, conformément à la consigne.

## 7. PCB

Demande de l'utilisateur : mêmes dimensions que la carte principale, avec le SuperMini (J4, J5), J1 et J3 placés de la même façon ; le routage est laissé à l'utilisateur.

Construction [CONSTATÉ, API pcbnew de `kicad/kicad:9.0.6`, à partir d'une copie en lecture du PCB principal] :
- **conservés à l'identique** : contour 66 × 33 mm, 4 trous M3 (H1 à H4), zone d'antenne (x = 140,7 à 149,8 mm, sans cuivre ni via), J3, J4 et J5, ainsi que C1, C2, C3, D3, D4, D5, R9 et R10 (mêmes positions), et les textes « ESP32-C3 Super Mini », « GND DAT 3V3 », « CL+ » ;
- **J1** : empreinte 3 points de la même famille, **broche 1 (CL+) au même endroit** (104,0 ; 114,77 mm), CL- et G+ en dessous, au pas de 3,5 mm ; texte « G+ » ajouté sous J1 ;
- **retirés** : toutes les pistes et vias, la bande d'isolation (inutile sans optocoupleur), J2 et ses textes, les composants de l'interface isolée ;
- **zone de masse** : étendue à toute la carte, sur les deux faces (GND = CL-), non remplie ;
- **placement des nouveaux composants**, en suivant le trajet du signal :
  - bande du haut, de gauche à droite : D2, C6, R6, U2, C9, L1, C7, C8, puis D4 et J4-1 (le 5 V suit le chemin de l'ancien J2) ;
  - au centre : U1 (SOIC-14) ;
  - à sa gauche, réception et émission : R1, R2, C4, R4, R5, Q1 ;
  - à sa droite : C5, R7, R3, D1 ;
  - D6 et D3 près de J1 (placement initial ; l'utilisateur a ensuite inversé J1 et déplacé D6 près de G+, J1-1) ;
- repères en sérigraphie de 0,8 mm, horizontaux. Règles de conception du projet principal reprises (`.kicad_pro`).

DRC avec parité, toutes sévérités [CONSTATÉ] : **0 écart avec le schéma**, aucun chevauchement de courtyard ni de sérigraphie, **63 connexions non routées** (normal : routage à faire). Les références et les champs JLCPCB sont liés au schéma : « Mettre à jour le PCB depuis le schéma » ne déplace rien.

**Routage de l'utilisateur** (2026-11-04) [CONSTATÉ, contrôle `kicad/kicad:9.0.6`] :
- **pistes** de 0,4 mm partout, 3 vias de 0,6/0,3 mm, aucune piste ni via dans la zone d'antenne, 0 écart avec le schéma ;
- **GND sans piste**, uniquement par les plans : une fois les zones remplies, la face avant était découpée en îlots non reliés, d'où 2 connexions manquantes (dont J3-3). Cela est corrigé par la couture ci-dessous ;
- la broche GND de U2 n'avait qu'une branche thermique sur 2 : elle est passée en **raccordement plein** au plan, ce qui est aussi meilleur pour la masse du régulateur.

**Finitions** (demande de l'utilisateur ; aucune piste modifiée) :
- **82 vias de couture GND**, en 0,6/0,3 mm comme ceux de l'utilisateur :
  - 79 sur une grille de 3 mm, placés seulement là où les deux plans sont remplis (disque du via entier dans le cuivre des deux faces), hors composants, hors zone d'antenne, à plus de 4 mm des trous M3 et à 1 mm du bord ;
  - 3 de plus dans les îlots de la face avant qui restaient isolés (vers J4, R7) ;
- **sérigraphie** : 16 repères en défaut déplacés à la main près de leur composant (U2, R6, C9, L1, C6, C7, C8, C5, U1, R7, R1, R2, C4, D1, R3, J1), texte « CL+ » sorti du contour de J1 ; les autres repères sont laissés là où l'utilisateur les avait mis.

DRC avec parité, toutes sévérités, zones remplies : **0 violation, 0 connexion manquante, 0 écart avec le schéma** [CONSTATÉ]. Sorties pour la fabrication : `bom_jlcpcb.csv`, `positions.csv` (format JLCPCB), `assemblage.pdf`. Les Gerber restent à produire par l'utilisateur.

## 8. Mise en service (quand la carte sera fabriquée)

Ordre à suivre, **sans la PAC** jusqu'à l'étape 6. Alimentation de labo réglée sur **12 V, limite de courant 150 mA**.

1. **Inspection** : sens de U1 (point de la broche 1), de U2 et de Q1, bague de cathode de D2 et D4 (côté K de la sérigraphie), LED D1. D3 et D6 sont bidirectionnelles (pas de sens). Aucun pont de soudure sur U1 (pas de 1,27 mm) ni sur U2 (TSOT-23-6).
2. **À l'ohmmètre, hors tension, SuperMini retiré** :

   | Entre | Attendu |
   |---|---|
   | J1-1 (G+) et J1-2 (GND) | pas de court-circuit (quelques kΩ ou plus) |
   | `5V_IN` (anode de D4) et GND | pas de court-circuit |
   | J1-3 (CL+) et GND | ≈ 133 kΩ (R1 + R2) |
   | J4-3 (3V3) et GND, J4-1 (5V) et GND | pas de court-circuit |
   | J1-1 et J1-3 | circuit ouvert |

3. **12 V sur J1-1 (+) et J1-2 (−), SuperMini retiré** :
   - courant ≤ 5 mA, car U2 passe en mode économie à vide ;
   - `5V_IN` = 5,0 V ± 0,1 V ;
   - J4-1 ≈ 4,7 V, avec la chute de D4 à faible courant ;
   - D1 éteinte (pas de 3,3 V, pas de bus).
4. **SuperMini enfiché**, flashé avec `sh docker/compiler.sh alfea` (lecture seule), USB débranché, 12 V sur J1-1 / J1-2 :
   - 3,3 V sur J4-3 ;
   - courant moyen de 40 à 60 mA sous 12 V une fois le WiFi connecté (§2) ;
   - BSB-LAN répond sur le réseau.

   Sur le banc, l'USB vers un PC est sans risque si l'alimentation de labo est flottante.
5. **Bus simulé** : résistance de **1 kΩ** entre le +12 V et J1-3 (CL+), qui joue la source du bus.
   - Au repos : CL+ ≈ 12 V, U1-1 ≈ 3,0 V, **RX (J5-2) = 3,3 V, D1 allumée**.
   - CL+ mis à GND à la main : RX = 0, D1 éteinte.
   - Pendant une émission de BSB-LAN (requête depuis l'interface web) : niveau bas de CL+ à mesurer, **≤ 0,3 V attendu** (Q1 sous 12 mA). À l'oscilloscope, créneaux de 208 µs ; à défaut, D1 clignote.
   - Relever aussi les seuils réels du 74HC14 : on monte puis descend lentement la tension de CL+ et on note les basculements de RX. Attendu : bascule à ≤ 9,3 V en montée et à ≥ 2,6 V en descente (§3).
6. **Avant de brancher sur la PAC** (GATE 3, accord de l'utilisateur) :
   - essai de charge de G+ (14 §6), avec un palier à environ 180 mA (68 Ω) ;
   - repérage de CL+ et G+ par la mesure en alternatif (09 §8) ;
   - repérage de CL- par rapport à la terre ;
   - puis câblage **croisé** X86-3 → J1-1, X86-2 → J1-2, X86-1 → J1-3, **PAC hors tension**, et firmware en lecture seule.

   Carte raccordée : USB-C seulement sur un PC portable sur batterie (§5).

Les mesures relevées aux étapes 3 à 5 remplacent les valeurs [SUPPOSÉ] des §2 à §4.

## 9. Points restant avant la mise sur la PAC

1. Essai de charge de G+ (14 §6), avec un palier proche de 180 mA.
2. Repérer CL- au multimètre par rapport à la terre de la chaufferie, PAC sous tension : si CL- est flottant, la règle de l'USB du §5 devient impérative.
3. Banc T1 sur simulateur : seuils réels du 74HC14 sous 3,3 V, niveau bas de Q1, écho des trames, tension du 5 V pendant l'émission WiFi.
4. Choix entre la variante A (doc 14) et l'option B, puis fabrication (la carte principale rev A, isolée, a été reçue le 2026-11-09).

## 10. Fichiers

| Fichier | Rôle |
|---|---|
| `alfea/hardware/carte_bsb_c3_b/carte_bsb_c3_b.kicad_sch`, `.kicad_pro` | schéma A3 câblé, 6 blocs |
| `alfea/hardware/carte_bsb_c3_b/carte_bsb_c3_b.kicad_pcb` | PCB 66 × 33 mm routé par l'utilisateur, 82 vias de couture GND |
| `alfea/hardware/carte_bsb_c3_b/alfea.kicad_sym`, `sym-lib-table` | copie du symbole sans broche des fiches (JJ1) |
| `alfea/hardware/carte_bsb_c3_b/sorties/` | `erc.rpt` (0 violation), `drc.rpt` (0 violation), `bom_jlcpcb.csv`, `positions.csv`, `assemblage.pdf`, `schema.pdf`, `schema.png`, `bom.csv`, `pcb.svg`, `pcb_dessus.png`, `pcb_dessous.png` |

Contrôle [CONSTATÉ] : `kicad-cli sch erc --severity-all --exit-code-violations`, puis comparaison de la netlist exportée avec les 20 nets attendus (ensembles de broches identiques).
