# 09 — Design de la carte d'interface BSB pour ESP32-C3 SuperMini

> **Résumé**
> Carte porteuse 2 couches de **62 × 33 mm** (révision B, §6) : J1 et le SuperMini sur le même axe, borniers à vis au pas de 2,54 mm, trous M3 aux 4 coins, transistors en SOT-23, composants passifs sous le module. Le SuperMini s'y enfiche (2 × 8 broches au pas de 2,54 mm). Elle reprend **la topologie éprouvée de l'adaptateur officiel V3** : 2 × 4N25, BC547/BC557, mêmes valeurs. Les **écarts sont limités et justifiés** : rappel de TX au démarrage, transistor de bus en gain C, TVS sur l'entrée (PTC retirée, §7), R2 à 2 kΩ, retrait de l'EEPROM, entrée DHT22 protégée, entrée 5 V avec diode anti-retour.
> **Isolation galvanique conservée** : rien n'est prélevé sur le bus pour l'ESP32. L'alimentation vient d'un **chargeur USB 5 V** (défaut, aucune intervention sur le 230 V) ou d'un module 5 V rail DIN (option).
> Brochage : RX = GPIO6, TX = GPIO7, DHT22 = GPIO5, LED = GPIO8 (sur le SuperMini). **Projet KiCad 9 dans `alfea/hardware/carte_bsb_c3/`** : le schéma maître est celui retouché dans KiCad (émission conforme à V3, §2.3) ; PCB **routé par Freerouting 2.1.0**, plan de masse, Gerber ; ERC 0, DRC 0 (toutes sévérités), parité 0 (§9). Variante traversante pour plaquette à bandes : **09b**.
> **Avant tout branchement**, X86 doit être mesuré (§8). Première mesure de l'utilisateur : **0 V entre 1, 2 et 3**, résultat à confirmer par une mesure témoin (§8).

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**. Les calculs reprennent les valeurs de 06 §3 (4N25 : CTR ≥ 20 % à 10 mA, Vf 1,2 V ; C3 : V_IH ≥ 2,48 V, V_IL ≤ 0,83 V).

---

## 1. Schéma fonctionnel

```mermaid
flowchart LR
  subgraph PAC["Alféa : RVS21, connecteur X86"]
    CLP[CL+]
    CLM[CL-]
  end
  subgraph BUS["Côté bus (alimenté par le bus, ≈ 6 mA)"]
    J1[J1 bornier 2 pts<br/>D2 dans le retour CL-] --> TVS[D3 TVS SMAJ18CA]
    TVS --> RXL[R2 2k + LED U1 + D1]
    TVS --> Q1[Q1 BC847C<br/>tire le bus à 0]
  end
  subgraph MCU["Côté ESP32 (3,3 V du SuperMini)"]
    U1T[U1 phototransistor] --> RX[GPIO6 RX]
    TX[GPIO7 TX] --> Q2[Q2 BC857C<br/>+ R8 rappel] --> U2L[LED U2]
    DHT[J3 DHT22] --> G5[GPIO5]
    P5[J2 5 V ou USB-C] --> D4[D4 Schottky] --> SM[SuperMini 5V]
  end
  CLP --- J1
  CLM --- J1
  RXL -. optique .-> U1T
  U2L -. optique .-> Q1
```

Aucun conducteur ne traverse la frontière bus/ESP32 : les deux seuls chemins sont optiques (U1 en réception, U2 en émission).

## 2. Schéma électrique détaillé (netlist)

Nœuds côté bus [CONSTATÉ dans le schéma maître] : `BUS_P` (J1-1 = CL+ ; `CL_P_IN` a disparu avec F1, §7), `BUS_N` (anode de D2), `CL_N_IN` (J1-2 = CL-, cathode de D2). Dans les tableaux, `BUS+` = `BUS_P` et `BUS-` = `BUS_N`. Nœuds côté ESP32 : `+3V3` et `GND` (broches du SuperMini), `+5V`.

### 2.1 Entrée et protections (côté bus)
| Réf. | Valeur | Connexion | Rôle |
|---|---|---|---|
| J1 | bornier à vis 2 pts, pas 2,54 | 1 = CL+, 2 = CL- | raccordement X86 |
| ~~F1~~ | **supprimé** (choix de l'utilisateur, §7) | J1-1 directement sur `BUS+` | comme en V3 ; conséquence en cas d'erreur de câblage : §5 |
| D2 | 1N4148W | anode `BUS-`, cathode `CL_N_IN` | **en série dans le retour CL-** : bloque tout l'étage bus (réception et émission) en cas d'inversion |
| D3 | TVS bidirectionnelle SMAJ18CA (V_RWM 18 V, V_BR ≥ 20 V) | `BUS_P` ↔ `CL_N_IN` (en amont de D2) | surtensions et ESD ; bidirectionnelle pour tolérer une inversion de polarité **[écart]** |

### 2.2 Réception : bus → GPIO6 (identique à V3)
| Réf. | Valeur | Connexion |
|---|---|---|
| R2 | **2 kΩ**, 1206 (250 mW) **[écart : 1,5 kΩ en V3]** | `BUS+` → U1 broche 1 (anode) |
| U1 | 4N25 | 1 anode, 2 cathode → D1 anode ; 5 collecteur → `+3V3`, 4 émetteur → `RX` (GPIO6), 6 base → R4 |
| D1 | LED rouge | D1 cathode → `BUS-` (témoin d'activité du bus) ; D2 (§2.1) est en série dans le retour |
| R4 | 330 kΩ | U1-6 (base) → U1-4 (émetteur) : accélère le blocage |
| R5 | 4,7 kΩ | `RX` → `GND` |

Calcul (06 §3.1) : seuil ≈ 3,7 V aux bornes de X86 = Vf(U1) 1,2 + Vf(D1) 1,8 + Vf(D2) 0,7, inchangé par le déplacement de D2 dans le retour ; Ic nécessaire = 2,48 V / 4,7 kΩ = 0,53 mA, soit I_F ≥ 0,53 / 0,20 = 2,65 mA au CTR minimal.

| R2 | I_F à 12 V / 13 V / 15 V | Marge au CTR min. (12 → 15 V) | Bus minimal pour RX | P(R2) au pire (15 V) |
|---|---|---|---|---|
| 1,5 kΩ (V3) | 5,5 / 6,2 / 7,5 mA | ×2,1 → ×2,8 | 7,7 V | 85 mW |
| **2 kΩ (retenu)** | 4,15 / 4,65 / 5,65 mA | **×1,57 → ×2,1** | **9,0 V** | **64 mW** (1206 : marge ×3,9) |

2 kΩ est un **écart à V3** (choix de l'utilisateur : référence Basic C17944, 1,5 kΩ en 1206 n'existant qu'en Extended). Il charge moins le bus (4,65 mA au lieu de 6,2 mA à 13 V) et reste suffisant pour un niveau haut de 12 à 15 V. **Condition** : le niveau haut réel du bus, mesuré sur X86 (§8), doit dépasser **9 V** avec marge ; le CTR baisse aussi avec le vieillissement de la LED [SUPPOSÉ : −20 à −30 % sur la vie]. Au-dessous de 11 V, revenir à 1,5 kΩ.

### 2.3 Émission : GPIO7 → bus
| Réf. | Valeur | Connexion |
|---|---|---|
| R6 | 4,7 kΩ | `TX` (GPIO7) → base de Q2 |
| **R8** | **10 kΩ** | base de Q2 → `+3V3` **[écart : rappel au démarrage]** |
| Q2 | BC857C (PNP, SOT-23) | E → `+3V3`, C → R3 |
| R3 | 300 Ω | Q2-C → U2 broche 1 (anode) ; U2-2 → `GND` |
| U2 | 4N25 | 5 collecteur → `BUS+`, 4 émetteur → base de Q1, 6 base → R1 |
| R1 | 330 kΩ | U2-6 (base) → U2-4 (émetteur) : accélère le blocage, comme R4 sur U1 |
| R7 | 330 kΩ | base de Q1 → `BUS-` |
| **Q1** | **BC847C** (NPN, SOT-23) | C → `BUS+`, E → `BUS-` **[écart : gain C imposé]** |

Calculs (VCC = 3,3 V) :
- **TX bas** : I_F(U2) = (3,3 − 0,2 − 1,2) / 300 = **6,3 mA**. Ib(Q2) = (3,3 − 0,7) / 4,7 k − 0,7 / 10 k = 0,55 − 0,07 = **0,48 mA** ; Ic = 6,3 mA, β forcé ≈ 13 ≪ β min (420) : saturé. Courant sur la GPIO : 0,55 mA.
- **TX haut ou haute impédance** (reset, bootloader) : R8 maintient V_EB = 0 et Q2 reste bloqué. **Sans R8**, une GPIO flottante ou tirée bas par un pull-down interne au reset pourrait allumer Q2 et **tirer le bus à 0 pendant le démarrage** (06 V5). R8 consomme 0,33 mA quand TX est bas, ce qui est négligeable.
- **Pouvoir de descente de Q1** (montage du schéma maître, celui de V3) : U2 et Q1 forment un Darlington. Le courant d'émetteur de U2 entre directement dans la base de Q1 : I_E(U2) ≥ CTR_min × I_F = 0,20 × 6,3 mA ≈ **1,3 mA**, moins ≈ 2 µA dans R1 et R7. Ic(Q1) possible ≥ 420 × 1,3 mA ≈ 0,5 A : Q1 n'est pas limité par sa commande, quel que soit le courant de court-circuit de la source du bus (inconnu, 06 Q5).
- **Niveau bas** : le phototransistor prend son courant sur le bus lui-même, donc Q1 ne sature pas complètement. V(`BUS+`) ≈ Vbe(Q1) + Vce,sat(U2) ≈ 0,65 + 0,2 = **0,85 V**, plus Vf(D2) aux bornes de X86, soit **≈ 1,5 à 1,6 V** entre CL+ et CL- [SUPPOSÉ : Vf(D2) ≈ 0,7 V au courant du bus]. C'est la topologie de V3, éprouvée sur le terrain ; le niveau bas réel se mesure à l'oscilloscope en GATE 3.
- **Correction de la rev B initiale** : j'avais placé R1 en série dans le collecteur de U2 (`BUS+` → R1 → U2-5). Le courant de base de Q1 valait alors (V(`BUS+`) − 0,65) / 330 kΩ et s'effondrait à mesure que le bus descendait. À l'équilibre, V(`BUS+`) ≈ 0,65 + 330 kΩ × I_bus / β : **≈ 4,6 V pour 5 mA de bus** avec β = 420. Le niveau bas aurait été douteux. Votre schéma retouché supprime ce défaut.
- **D2 dans le retour** porte tout le courant de l'étage, y compris celui que Q1 tire pendant nos bits à 0. 1N4148W : 150 mA en continu, ≈ 0,5 A en impulsion [À VÉRIFIER : datasheet du fabricant retenu]. C'est suffisant si la source du bus est limitée à quelques dizaines de mA, ce qui est probable [SUPPOSÉ] puisqu'un court-circuit du bus est son fonctionnement normal.

### 2.4 Entrée DHT22 (D5)
| Réf. | Valeur | Connexion | Rôle |
|---|---|---|---|
| J3 | barrette femelle 1 × 3, pas 2,54 | 1 = `+3V3`, 2 = DATA, 3 = `GND` | capteur à ≈ 10 cm, enfiché directement ou par câble Dupont |
| R9 | 4,7 kΩ | DATA → `+3V3` | rappel du bus 1-fil (DHT22 : 4,7-10 kΩ) |
| R10 | 100 Ω | DATA → GPIO5 | limite le courant d'une décharge ESD dans la GPIO |
| D5 | **SMF5.0A** (TVS unidirectionnelle, cathode sur DATA) | DATA ↔ `GND` | ESD sur le câble du capteur |
| C3 | 100 nF | `+3V3` ↔ `GND` près de J3 | découplage du capteur |

Alimentation du DHT22 en 3,3 V : la datasheet AM2302 donne 3,3-6 V, avec une portée réduite à 3,3 V. **Le capteur sera à une dizaine de centimètres** (information de l'utilisateur) : aucune contrainte de portée. D5 (SMF5.0A) : V_RWM 5 V, V_BR 6,4-7 V à 10 mA, V_C 9,2 V à 21,7 A, I_R ≤ 400 µA **à 5 V** [CONSTATÉ, fiche hongjiacheng rév. 2.2]. La fuite à 3,3 V n'est pas spécifiée ; à 0,5 × V_BR, elle est en principe de quelques µA, soit < 0,05 V de chute dans R9 [SUPPOSÉ]. **Contrôle sur la première carte** : V(DATA) au repos ≥ 3,1 V, capteur débranché ; sinon, ne pas monter D5 (câble de 10 cm, R10 et les diodes internes de l'ESP32-C3 suffisent). Ne pas l'alimenter en 5 V : DATA serait rappelée à 5 V et dépasserait la tension maximale de la GPIO (3,6 V).

### 2.5 Alimentation
| Réf. | Valeur | Connexion |
|---|---|---|
| J2 | bornier à vis 2 pts, pas 2,54 | 5 V externe (option rail DIN) |
| D4 | SS14 (Schottky 1 A, 40 V) | J2(+) → `+5V` (broche 5V du SuperMini) : empêche le 5 V de l'USB-C de remonter dans l'alimentation externe |
| C1 | **22 µF 25 V X5R, 1206** (céramique) | `+5V` ↔ `GND` : réservoir pour les pointes d'émission WiFi (risque R4 de 07) |
| C2 | 100 nF X7R | `+5V` ↔ `GND` |

Pas de condensateur ajouté sur le `+3V3` : la stabilité du LDO du SuperMini (ME6211 ou LP5907) avec une capacité de sortie supplémentaire n'est pas garantie [SUPPOSÉ].

## 3. Adaptation au SuperMini

| Broche SuperMini | Usage | Justification |
|---|---|---|
| 5V, GND | alimentation (USB-C du SuperMini **ou** J2 via D4) | |
| 3V3 | côté MCU de l'interface (< 10 mA, §4) | même potentiel que les GPIO : condition 06 §3.2 respectée |
| **GPIO6** | RX (UART1) | pas de strapping ; pin JTAG (MTCK) non utilisé, JTAG passe par l'USB [SUPPOSÉ : configuration eFuse par défaut] |
| **GPIO7** | TX (UART1) | idem (MTDO) ; **pas** GPIO21 (U0TXD, log ROM à 115 200 bauds au boot) |
| **GPIO5** | DHT22 | libre, pas de strapping |
| GPIO8 | LED bleue du SuperMini (active à l'état bas [À VÉRIFIER sur le lot]) | strapping : doit rester haut au boot, ce qu'assure la LED tirée au 3V3. l'amont ne fixe `LED_BUILTIN = 8` que pour les cartes Olimex C3/C6 (`BSB_LAN/BSB_LAN.ino:211-217`) : le définir dans notre configuration, sauf si la variante `esp32c3` d'arduino-esp32 le fait déjà [À VÉRIFIER au build] |
| GPIO9 | bouton BOOT du SuperMini | strapping, non utilisé |
| GPIO2 | non utilisé | strapping |
| GPIO18/19 | USB (flash, console) | |

Configuration logicielle : `bus_pins = {6, 7}`, `DHT_Pins[0] = 5` (08 §1.2), sans modification du code.

## 4. Alimentation : justification

**Pas d'alimentation par le bus.** Ni la puissance disponible sur X86 ni l'impédance de source ne sont documentées (06 §3.4, Q5). Surtout, alimenter l'ESP32 depuis G+ ou CL+ **relierait sa masse au bus**, ce qui annulerait l'isolation des optocoupleurs (décision D6). Une surconsommation pourrait aussi faire redémarrer le régulateur.

**Pas de 5 V documenté sur le RVS21** : je n'ai trouvé aucune sortie 5 V dans la notice R32 ni dans la doc BSB-LAN. G+ (alimentation des sondes d'ambiance) n'est pas prévu pour 100 à 350 mA.

| Solution | + | − | Choix |
|---|---|---|---|
| **Chargeur USB 5 V ≥ 1 A** (marque, marquage CE) + câble USB-C vers le SuperMini | aucune intervention sur le 230 V ; remplaçable | une prise 230 V à proximité ; câble USB exposé | **par défaut** |
| Module rail DIN 5 V (ex. Mean Well HDR-15-5 : 5 V 2,4 A, classe II, 17,5 mm) câblé sur J2 | propre, durable en chaufferie | raccordement 230 V à faire par une personne qualifiée, sans toucher au câblage de la PAC | option |
| Convertisseur AC/DC sur la carte | compact | 230 V sur notre carte : isolation renforcée, CE | **rejeté** |

Budget [SUPPOSÉ, ordres de grandeur de datasheet, à mesurer en T1] :

| Consommateur | Moyen | Pointe |
|---|---|---|
| ESP32-C3, WiFi connecté | 80-100 mA | 350 mA (émission) |
| Interface côté MCU (U2 6,3 mA × taux d'émission < 10 %, R5, R8, DHT22) | < 3 mA | 9 mA |
| **Total sur 5 V** | **≈ 0,1 A (0,5 W)** | **≈ 0,36 A** |
| Prélevé sur le bus (U1 + D1) | 6 mA | + courant de Q1 pendant nos bits à 0 |

Un chargeur de 1 A donne une marge ×2,8 sur la pointe. Avec un LP5907 (250 mA, risque R4), C1 ne fournit que la part de la pointe que le chargeur et le câble ne suivent pas. Avec C1 = 22 µF 25 V X5R, il reste ≈ 15 µF effectifs sous 5 V [SUPPOSÉ : courbe de polarisation Samsung à consulter], d'où ΔV ≈ 0,1 A × 50 µs / 15 µF ≈ **0,33 V** [SUPPOSÉ : transitoire de 50 µs]. L'ancien calcul (100 µF, 1 ms, 1 V) supposait que C1 fournissait toute la pointe pendant 1 ms ; avec 15 µF, ce même cas donnerait 6,7 V, donc il ne tient plus : **préférer les lots ME6211**, et mesurer la tension au SuperMini pendant l'émission en T1. Le 25 V donne une marge ×5 sur 5 V, utile au branchement à chaud de J2 (oscillation du câble sur une céramique, jusqu'à ≈ 2 × 5 V).

## 5. Isolation, protections, CEM, environnement

| Sujet | Disposition |
|---|---|
| Isolation | les deux côtés sont en TBTS ; l'isolation est fonctionnelle (boucles de masse, surtensions de mode commun), pas de sécurité. **Distance ≥ 3 mm** entre cuivres bus et MCU, sous les 4N25 (rangées de pastilles à 7,62 mm en DIP-6, pastilles de 1,6 mm, soit **6,0 mm entre bords de pastilles**) ; fente de 1 mm optionnelle. Isolement du LTV-4N25 (Lite-On) : 2 500 V eff. [CONSTATÉ, fiche Lite-On] |
| Polarité | D2 en série dans le retour CL- + TVS bidirectionnelle : une inversion bloque tout l'étage bus, rien n'est détruit et rien ne fonctionne (V1 de 06). La LED D1 éteinte signale l'inversion |
| Surtension, erreur de câblage | D3 écrête au-delà de 20 V. **Sans F1** (choix de l'utilisateur, comme en V3) : sur une source raide (ex. borne 24 V), D3 conduit en continu, dépasse sa dissipation et **se met en court-circuit** (mode de défaillance usuel des TVS), ce qui protège le reste de la carte mais court-circuite le bus jusqu'au remplacement de D3 ; côté PAC, un court-circuit du bus est un état normal [SUPPOSÉ : source limitée, 06 Q5]. D3 est raccordée entre `BUS_P` et `CL_N_IN`, **en amont de D2** (décision de l'utilisateur, J23) : le courant de surtension ne traverse que D3 (13,8 A crête en 10/1000 µs), plus D2 (1N4148W, I_FSM de l'ordre de 2 A sur 1 µs [À VÉRIFIER]). Une inversion de polarité reste sans effet : D3 est bidirectionnelle et D2 bloque |
| ESD | D3 côté bus, D5 côté DHT22 ; manipulation avec bracelet (V7 de 06) |
| CEM | **aucun condensateur** entre CL+ et CL- (il déformerait les fronts et chargerait le bus) ; câble en paire torsadée, si possible blindée, avec le blindage à la masse **côté PAC seulement** [À VÉRIFIER : recommandation Siemens] ; éloigné des câbles du compresseur et de l'onduleur |
| Environnement | chaufferie de 0 à 50 °C [SUPPOSÉ] : composants -40/+85 °C au minimum ; boîtier ABS avec presse-étoupes, hors des projections d'eau ; vernis de tropicalisation optionnel si condensation |
| RF | antenne céramique du SuperMini au **bord de la carte**, sans cuivre dessous ni dessus (dégagement de plan de masse), boîtier non métallique. Condition RSSI ≥ −70 dBm (D1) |

## 6. Format de la carte

Révision B, placement réel (rendu `alfea/hardware/carte_bsb_c3/sorties/pcb_dessus.png`) :

```
 62 mm
┌────────────────────────────────────────────────────────────┐
│ o      D3 │U1│ J2 (5 V, ouvert vers le haut)           o │
│   R2 D1 D2│   │ R4 R5 ┆      ═══════ J4 ═══════════        │
│ J1 ◄──    │iso│ R6 R8 ┆antenne  C1   D4  C2   ──► USB      │ 33 mm
│ (BSB)  Q1 │   │ Q2 R3 ┆       C3 R9 R10 D5   (SuperMini)   │
│   R1  R7  │U2│ J3 (DHT22, vers le bas) ═══ J5 ═══════     │
│ o         │   │                                          o │
└────────────────────────────────────────────────────────────┘
```
- **J1 et le SuperMini sur le même axe horizontal** (centres à y ≈ 116,4 mm) : le bus entre à gauche, l'USB sort à droite.
- SuperMini à l'horizontale sur ses barrettes : **C1, D4, C2, C3, R9, R10 et D5 sont sous le module**. Ces composants CMS bas (≤ 5,4 mm pour C1) passent sous la carte, que les barrettes surélèvent d'environ 8,5 mm [À VÉRIFIER selon les barrettes].
- Bande d'isolation de 3 mm (zone interdite au cuivre, x = 123,4 à 126,4 mm) entre les deux rangées de broches des 4N25.
- Zone sans cuivre de 4,2 × 18 mm sous l'antenne, qui se trouve à l'extrémité du module opposée à l'USB. Les pistes vers les barrettes passent au-dessus ou au-dessous de cette zone.
- Références des CMS passifs sur le plan d'assemblage (`sorties/assemblage.pdf`, couche F.Fab), faute de place en sérigraphie. Les bornes sont repérées en sérigraphie : CL+/CL-, 5V/GND, GND/DAT/3V3.
- Sens d'entrée des fils des borniers MPT (vers le bord de la carte) déduit du dessin de fabrication de l'empreinte KiCad **[À VÉRIFIER sur un bornier réel]**.

- 2 couches, FR-4 1,6 mm, finition HASL ou ENIG.
- Empreintes : CMS 0805 (1206 pour R2), 4N25 en **DIP-6 traversant** (LTV-4N25, §7), BC847C/BC857C en SOT-23 (mêmes gains que les BC547C/BC557C : β 420 à 800), embases enfichables **3,5 mm pour J1 et J2**, **barrette femelle 1 × 3 au pas de 2,54 mm pour J3** (§7).
- Le SuperMini est monté sur **barrettes femelles** (remplaçable) : écartement des rangées **[À VÉRIFIER sur un exemplaire au pied à coulisse]**, 15,24 mm (0,6") attendu.
- 4 trous M3 aux coins (entraxe 55,6 × 26,6 mm) ; boîtier de type 80 × 50 × 30 mm.

## 7. Nomenclature (BOM)

Références JLCPCB (assemblage) intégrées au schéma maître : pour chaque symbole, **Value = « Part # » du fabricant** (colonne « Comment » de JLCPCB), **sauf les résistances et condensateurs, dont Value donne la valeur électrique** (`330k`, `100n`… : demande de l'utilisateur, pour la lisibilité du schéma ; leur `Description` donne tolérance, puissance ou tension, et boîtier). S'y ajoutent les champs `JLCPCB Part #` et `Product link`. Le champ `MPN` donne le fabricant et sa référence ; pour les autres composants, `Description` reprend l'ancienne valeur (fonction ou valeur électrique ; elle est visible sur les connecteurs). JLCPCB rapproche les lignes par la colonne `JLCPCB Part #` : une colonne « Comment » différente du Part # ne provoque qu'un avertissement. Source : `sorties/bom-JLCPCB Assembly Order.xls`, rapprochement JLCPCB du 2026-11-02. Les lignes marquées ✱ s'en écartent.

| Réf. | Qté | Désignation | Part # (fabricant) | JLCPCB | Contrôle empreinte / compatibilité |
|---|---|---|---|---|---|
| U1, U2 | 2 | optocoupleur 4N25, **traversant DIP-6** | **LTV-4N25** (Lite-On) | C118160 | ✱ choix de l'utilisateur (2026-11-03) : les pièces traversantes ne paient pas le forfait « Extended » mais un forfait unique de soudure (information de l'utilisateur). Empreinte `Package_DIP:DIP-6_W7.62mm`. Même fiche Lite-On que le 4N25S-TA1, donc même puce et même brochage (1 A, 2 K, 3 NC, 4 E, 5 C, 6 B) ; CTR ≥ 20 % à 10 mA, 2 500 V eff. [CONSTATÉ]. Stock JLCPCB : 394 (le 2026-11-03) |
| Q1 | 1 | NPN gain C, SOT-23 | BC847C (hongjiacheng) | C7420337 | conforme (β 420-800) |
| Q2 | 1 | PNP gain C, SOT-23 | BC857C (hongjiacheng) | C20069137 | conforme |
| D1 | 1 | LED rouge 0805 | NCD0805R1 (NationStar) | C84256 | conforme (Vf 1,6-2,6 V : seuil RX de §2.2 entre 3,5 et 4,5 V [SUPPOSÉ]) |
| D2 | 1 | diode signal SOD-123 | 1N4148W (Semtech) | C81598 | conforme |
| D3 | 1 | TVS bidirectionnelle 400 W 18 V, SMA | SMAJ18CA (hongjiacheng) | C19077539 | conforme (V_BR 20 V, V_C 29,2 V) |
| D4 | 1 | Schottky 1 A 40 V, SMA | SS14 (MDD) | C2480 | conforme |
| D5 | 1 | TVS unidirectionnelle 200 W, V_RWM 5 V, SOD-123FL | **SMF5.0A** (hongjiacheng) | C19077497 | ✱ Extended **Preferred** (pas de forfait). Empreinte `Diode_SMD:D_SOD-123F`, cathode (bande) sur DATA ; symbole `Diode:SMF5V0A`. Fuite à 3,3 V à contrôler (§2.4) |
| ~~F1~~ | 0 | — | — | — | ✱ **supprimé** (choix de l'utilisateur) : aucune PTC n'est en Basic ou Preferred chez JLCPCB. J1-1 directement sur `BUS_P` ; conséquences en §5 |
| R1, R4, R7 | 3 | 330 kΩ 0805 1 % | **0805W8F3303T5E** (Uniroyal) | C17629 | ✱ Extended **Preferred** (pas de forfait), même empreinte |
| R2 | 1 | **2 kΩ** 1206 250 mW | **1206W4F2001T5E** (Uniroyal) | C17944 | ✱ Basic ; **écart à V3** (1,5 kΩ), marges en §2.2 (64 mW au pire) |
| R3 | 1 | 300 Ω 0805 | 0805W8F3000T5E | C17617 | conforme |
| R5, R6, R9 | 3 | 4,7 kΩ 0805 | 0805W8F4701T5E | C17673 | conforme |
| R8 | 1 | 10 kΩ 0805 | 0805W8F1002T5E | C17414 | conforme |
| R10 | 1 | 100 Ω 0805 | 0805W8F1000T5E | C17408 | conforme |
| C1 | 1 | **22 µF 25 V X5R, 1206** | **CL31A226KAHNNNE** (Samsung) | C12891 | ✱ Basic. Empreinte `Capacitor_SMD:C_1206_3216Metric` (au lieu de l'électrolytique 6,3 × 5,4), symbole non polarisé ; ≈ 15 µF effectifs sous 5 V [SUPPOSÉ], conséquences en §4 |
| C2, C3 | 2 | 100 nF X7R 0805 25 V | CGA0805X7R104K250KT (HRE) | C36911366 | conforme |
| J1, J2 | 2 | embase enfichable 2 pts, pas **3,5 mm**, verticale fermée | **HC-JXDZVC-3.5-2P** (Hong Cheng) | C51927058 | ✱ empreinte **MPT 2,54 mm → `PhoenixContact_MCV_1,5_2-G-3.5_1x02_P3.50mm_Vertical`** (décision de l'utilisateur). Perçage 1,2 mm [À VÉRIFIER : section des broches HC]. J2 n'avait pas de correspondance dans la BOM JLCPCB : même pièce que J1 |
| J3 | 1 | barrette femelle 1 × 3, pas 2,54, h 8,5 mm, traversante | **22850103ANG1SYA01** (JILN) | C41431926 | ✱ choix de l'utilisateur (option A du 2026-11-03) : l'embase JILN 2,5 mm (C2908480) n'avait que **6 pièces en stock**, soit tout juste 5 cartes + 1 de perte. Ici, 1 239 en stock. Le capteur est à ≈ 10 cm, donc le verrouillage n'est pas nécessaire. Même gamme que J4/J5, empreinte `PinSocket_1x03_P2.54mm_Vertical`, symbole `Conn_01x03`. Brochage 1 = 3V3, 2 = DATA, 3 = GND, conforme à la plupart des modules AM2302 à 3 broches (+, out, −) [À VÉRIFIER sur la sérigraphie du module] ; un DHT22 nu (4 broches) se branche par câble |
| J4, J5 | 2 | barrette femelle 1 × 8, pas 2,54, h 8,5 mm | 22850108ANG1SYA01 (JILN) | C429957 | conforme. J5 n'avait pas de correspondance dans la BOM JLCPCB : même pièce que J4 |
| JJ1, JJ2 | 2 | fiche 2 pts 3,5 mm (côté câble) pour J1, J2 | HC-JXDZK-3.5-2P (Hong Cheng) | C51927077 | symbole **sans empreinte** (hors carte, dans la BOM), bibliothèque du projet `alfea.kicad_sym` |
| — | 1 | ESP32-C3 SuperMini (4 Mo, LDO ME6211 de préférence) | générique | — | enfiché sur J4, J5 |
| — | 1 | capteur T/HR | **DHT22 / AM2302** | — | |
| — | 0 | fiche pour X86 | **inutile** : X86 est un bornier à vis débrochable [CONSTATÉ sur la photo] ; les fils du bus se serrent sous ses vis 1 et 2 | — | |
| — | 1 | chargeur USB 5 V ≥ 1 A + câble USB-C (ou Mean Well HDR-15-5) | | — | |

**Frais d'assemblage JLCPCB** [CONSTATÉ dans `sorties/bom-JLCPCB Assembly Order.xls` et la recherche de pièces JLCPCB, 2026-11-03] : chaque référence **Extended** distincte est facturée une fois par commande. Les références **Basic** et les Extended **« Preferred »** ne le sont pas, ce qui explique que les frais ne soient pas systématiques. Les pièces **traversantes** ne paient pas ce forfait, mais un forfait unique de soudure (information de l'utilisateur). Avant les choix du 2026-11-03, 10 références CMS Extended étaient facturées ; après : **C2/C3** (CGA0805X7R104K250KT) seulement. C49678 (Basic, 100 nF 50 V) est disponible, même empreinte, si l'on veut le supprimer. Les fiches JJ1 et JJ2 ne sont pas montées (JJ3 supprimée avec le passage de J3 en barrette) : JLCPCB ne livre pas de pièces en vrac, donc les retirer de la BOM d'assemblage et les commander chez LCSC.

Contrôles du schéma après intégration [CONSTATÉ, kicad-cli 9.0.5] : ERC **0** (toutes sévérités) ; netlist identique à la précédente, aux références U1/U2 près (seuls changent les noms automatiques des broches 3 non connectées). Nets renommés comme les optocoupleurs (demande de l'utilisateur) : `BUS_R2_OK1` → `BUS_R2_U1`, `BUS_OK1_D1` → `BUS_U1_D1`, `BUS_OK2_B` → `BUS_U2_B`, `OK1_B` → `U1_B`, `OK2_A` → `U2_A`, dans le schéma, le PCB et `gen/carte.py` ; connexions inchangées [CONSTATÉ, comparaison des netlists].

**PCB mis à jour depuis le schéma, sans routage** (demande de l'utilisateur), par l'API pcbnew de KiCad 9.0.5 :
- **références, valeurs et champs** de toutes les empreintes ;
- **J1, J2, U1 et U2 remplacées** : même orientation, centre des pastilles conservé, nets recopiés par numéro de pastille ;
- **toutes les pistes et vias supprimées** (207 segments, 8 vias), contours de zone gardés et plan GND recalculé ;
- **placement retouché** pour les nouvelles empreintes :
  - J2 (MCV 3,5 mm, pastille 1) en (133,95 ; 103,42) : le corps dépasse du bord haut d'environ 1,4 mm, du côté de l'entrée de la fiche ; le cuivre reste à 1,6 mm du bord ;
  - J3 (JILN 2,5 mm, pastille 1) en (138,61 ; 130,8), à 180° : le corps dépasse du bord bas d'environ 1,7 mm ; le cuivre reste à 0,9 mm du bord. **Depuis remplacée par une barrette 1 × 3** (§7, choix du 2026-11-03), qui ne déborde plus ;
  - D3 décalé de −0,65 mm, R3, R4 et R6 de +0,45 mm ;
  - textes de sérigraphie CL-, « GND DAT 3V3 » et « J2 : 5V / GND » déplacés avec leur connecteur.

DRC avec parité [CONSTATÉ] :
- 0 erreur d'empreinte (parité) ;
- 0 erreur d'isolation, de chevauchement ou de court-circuit ;
- **45 liaisons à router** ;
- 9 avertissements « sérigraphie tronquée par le bord » (corps de J2 et de J3 en débord).

Les fichiers `sorties/gerbers/` et `production/` correspondent à **l'ancien routage** : à refaire après routage. Ne pas lancer `docker/kicad/generer_carte.sh`, qui écrase le placement et lance Freerouting.

**Choix de BOM du 2026-11-03** (C1, D5, R1/R4/R7, R2, U1/U2, suppression de F1) : appliqués au **schéma maître seulement**. ERC **0** ; la netlist ne change que par la fusion de `CL_P_IN` dans `BUS_P` (J1-1 sur `BUS_P`) [CONSTATÉ, comparaison des netlists]. **Le PCB n'est pas modifié** : l'utilisateur a commencé le routage (fichier non committé). Le report se fait dans KiCad par « Mettre à jour le PCB depuis le schéma » (F8), qui :
- remplace les empreintes de **C1** (CP_Elec 6,3 × 5,4 → 1206), **D5** (SOD-323 → SOD-123F), **U1 et U2** (SMDIP-6 → DIP-6 traversant : rangées à ±3,81 mm au lieu de ±4,765 mm, pistes à reprendre) ;
- remplace l'empreinte de **J3** (JILN 2,5 mm → barrette 1 × 3 au pas de 2,54 : 3 pastilles à reprendre) ;
- supprime **F1** : ses pistes restent orphelines, et J1-1 rejoint `BUS_P` par le chevelu ;
- met à jour les valeurs et les champs des autres composants, sans toucher au routage.

Écarts à l'adaptateur officiel V3 (règle 00 §2.4), récapitulatif : **R8** (sûreté au démarrage), **Q1 en gain C** (marge de descente du bus), **D3** (protection demandée par la mission ; F1 retirée par l'utilisateur), **R2 à 2 kΩ** (§2.2), **suppression de la 24LC32** (inutile sur ESP32, 06 §2.4), **ajouts DHT22 et entrée 5 V** (périmètre MCU, sans effet sur le bus). Les valeurs des composants côté bus sont inchangées.

## 8. Mesure de X86 avant branchement (prérequis GATE 3)

**Constaté sur la photo** (`docs/claude/images/x86_alfea.jpeg`) : X86 est un **bornier à vis débrochable vert, 6 points**, sérigraphié `B2 M B1 3 2 1` de gauche à droite. Le bornier bleu voisin X84 sert à la PAC et à l'ECS. L'étiquette de la tôle montre un appareil d'ambiance raccordé sur **3 et 2**. Rien n'est branché sur X86. Les fils du bus se serreront directement sous les vis : aucune fiche à acheter.

**Interprétation [SUPPOSÉ]** : la doc BSB-LAN donne CL+ sur la borne la plus à droite (`1`) et CL- sur la suivante (`2`) (06 V2). Elle précise que les bornes 2-3 de l'étiquette ne servent qu'à alimenter l'appareil d'ambiance. Cela correspond au brochage Siemens CL+ / CL- / G+, avec G+ l'alimentation 12 V des appareils d'ambiance, et donne : **1 = CL+, 2 = CL-, 3 = G+**. `B1`, `B2` et `M` sont des entrées de sonde et leur masse.

**Mesure de l'utilisateur : 0 V entre 1-2, 2-3 et 1-3.** Sur un RVS21 sous tension, on attend 12 à 15 V entre CL+ et CL-, et environ 12 V sur G+. Trouver 0 V partout, **y compris sur la G+ supposée**, met plutôt en cause les conditions de mesure que le bus lui-même. Hypothèses, de la plus à la moins probable :
1. **mesure** : calibre alternatif ou 200 mV, pointe COM dans la mauvaise douille, bornier mal enfiché ;
2. **régulateur non alimenté** au moment de la mesure : PAC en arrêt, disjoncteur de la régulation ouvert, IHM éteinte ;
3. **X86 non alimenté par la régulation** tant qu'aucun appareil d'ambiance n'est déclaré [SUPPOSÉ, rien de documenté]. Dans ce cas, le BSB est à chercher ailleurs, par exemple sur la liaison vers l'IHM ou vers le récepteur radio des Navilink A59 : **question ouverte**.

**Mesure à refaire**, PAC sous tension, **IHM allumée**. Même précautions qu'avant : 230 V à proximité, pointes isolées, ne rien débrocher sous tension.
1. **Contrôler le multimètre** sur une source connue (chargeur USB : ≈ 5 V), en continu, calibre 20 V.
2. COM sur `2` : mesurer `1` (attendu 12 à 15 V, valeur moyenne un peu plus basse à cause du trafic), puis `3` (attendu ≈ 12 V si c'est G+).
3. **Mesure témoin**, COM sur `M` : mesurer `B1` et `B2`. Une entrée de sonde ouverte présente en général une tension de polarisation de quelques volts [SUPPOSÉ].
   - Si `B1`-`M` ≠ 0 et `1`-`2` = 0 V : X86 n'est pas alimenté (hypothèse 3), ne rien brancher et me transmettre les mesures.
   - Si tout vaut 0 V, même la mesure témoin : la carte n'est pas alimentée ou la mesure est fausse (hypothèses 1-2).
4. Si un oscilloscope est disponible (sonde différentielle, ou oscilloscope sur batterie) : des créneaux de 208 µs entre `1` et `2` confirment le BSB. Relever le niveau bas et la tension de repos.

Ces mesures fixent la tension nominale de D3 et le sens de raccordement de J1 (CL+ sur J1-1).

## 9. Fichiers KiCad et régénération

| Fichier | Rôle |
|---|---|
| `alfea/hardware/carte_bsb_c3/carte_bsb_c3.kicad_sch`, `.kicad_pro` | **schéma maître**, édité dans KiCad (retouches de l'utilisateur, commit e0b21e1d). Le générateur ne l'écrase jamais (sauf `gen_kicad.py --schema` sur un dossier vide) |
| `alfea/hardware/gen/carte.py` | placement du PCB, empreintes, références fabricant et affectation broche → net. Il doit refléter le schéma maître, ce que vérifie la **parité du DRC** |
| `alfea/hardware/gen/gen_kicad.py` | PCB placé (contour, trous, zones interdites d'isolation et d'antenne) |
| `alfea/hardware/gen/specctra.py` | classes de nets, export DSN, import du routage, nettoyage, plan de masse |
| `alfea/hardware/gen/plaquette.py`, `gen_plaquette.py` | variante traversante (09b) |
| `alfea/hardware/carte_bsb_c3/sorties/` | `schema.pdf`, `assemblage.pdf`, `bom.csv`, `pcb.svg`, `pcb_dessus.png`, `pcb_dessous.png`, `gerbers/` (Gerber et perçage), `erc.rpt`, `drc.rpt` |
| `docker/kicad/generer_carte.sh` | régénère et contrôle les deux variantes |

**Régénérer** : `sh docker/kicad/generer_carte.sh` depuis la racine du dépôt (≈ 1 min). Étapes :
1. placement du PCB (`kicad/kicad:9.0.6`), le `.kicad_pro` de KiCad étant sauvegardé puis restauré ;
2. export Specctra avec les classes de nets ;
3. **Freerouting 2.1.0** dans `eclipse-temurin:21-jre`, en mono-fil et 100 passes. Le jar officiel est téléchargé une fois dans `alfea/build/outils/` (ignoré par git), avec un sha256 vérifié à chaque usage : `2c07d58f75dac03782664081e7a58b41c25400d871a9fcf166a2ea6fe60d5def` ;
4. import, suppression des segments en double ou en impasse (laissés par l'optimiseur), plan GND en face arrière côté ESP32, hors bande d'isolation et hors zone antenne ;
5. ERC, DRC avec parité (toutes sévérités, échec au moindre avertissement), exports.

**Classes de nets** : bus (`CL_P_IN`, `CL_N_IN`, `BUS_P`, `BUS_N`) 0,4 mm ; alimentation (`5V_IN`, `+5V`, `GND`) 0,3 mm, soit ≈ 1 A pour +10 °C en couche externe 35 µm (IPC-2221), pour ≈ 0,5 A crête du SuperMini ; signaux et `+3V3` 0,25 mm ; garde 0,25 mm ; vias 0,8/0,4 mm.

**Contrôles** [MESURÉ, 2026-11-01] :
- schéma maître : ERC **0**, toutes sévérités ;
- netlist du schéma maître comparée à `carte.py` : 0 écart. Vos modifications touchent 5 nets côté bus et aucun côté ESP32 ;
- PCB routé : **0 connexion manquante**, DRC **0**, avertissements compris, parité **0** ; 198 segments, 4 vias.

Le routage automatique n'est pas reproductible à l'identique d'un passage à l'autre : nombre de vias et tracé varient, mais les contrôles restent à 0. **C'est une proposition de routage** : à relire dans KiCad avant commande, en particulier le cheminement des nets du bus et la continuité du plan de masse sous le SuperMini.

**Avant fabrication, à vérifier sur un exemplaire** :
- le brochage du SuperMini (5V, GND, 3V3, GPIO4-0 d'un côté ; GPIO5-10, 20, 21 de l'autre) et l'entraxe des rangées (15,24 mm) ;
- le sens du connecteur USB (vers la droite, débordant du bord) ;
- la position de l'antenne céramique, qui doit tomber dans la zone sans cuivre ;
- le sens d'entrée des fils des borniers MPT.
