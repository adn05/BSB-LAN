# 09b — Variante traversante sur plaquette à bandes

> **Résumé**
> Même schéma que la carte CMS (même netlist, mêmes UUID), en composants traversants, sur une **plaquette à bandes horizontales de 14 bandes × 57 trous** (≈ 145 × 36 mm) : 19 coupes ponctuelles, une rainure d'isolation sur 2 trous et 5 fils de liaison.
> Le projet KiCad `alfea/hardware/carte_bsb_c3_tht/` modélise chaque bande comme une piste et chaque coupe comme une interruption de piste : **le DRC de KiCad vérifie l'absence de court-circuit entre bandes et l'absence de liaison manquante** [MESURÉ : DRC 0 toutes sévérités, 0 connexion manquante, parité 0, ERC 0].
> Plans de montage : `sorties/plaquette_composants.svg` (dessus), `sorties/plaquette_cuivre.svg` (dessous, en miroir), `sorties/plan.txt` (listes). Écarts au CMS : boîtiers, D5 non montée (§3).

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**.

## 1. Repère et lecture des plans

- **Bandes** : lettres A à N, de haut en bas, **vues côté composants**.
- **Trous** : numéros 1 à 57, de gauche à droite, **vus côté composants**.
- Exemple : `G21` désigne la bande G, trou 21.
- Côté cuivre, la plaquette est retournée et la gauche devient la droite. `plaquette_cuivre.svg` est déjà dessiné en miroir pour qu'on puisse couper en le gardant sous les yeux.
- Sur les plans, une croix rouge marque une coupe et un trait bleu un fil de liaison. Une bande foncée porte un net (son nom est indiqué), une bande claire n'est pas utilisée.

Génération : `sh docker/kicad/generer_carte.sh` (variante dérivée du schéma maître CMS, 09 §9). Les positions sont dans `alfea/hardware/gen/plaquette.py`. Une erreur de placement fait échouer la génération : deux nets sur une même bande, coupe sur un trou utilisé, pastille hors grille ou trou occupé deux fois.

## 2. Ordre de montage conseillé

1. **Couper** côté cuivre, avec un foret de 3 à 4 mm tourné à la main ou un coupe-bande :
   - la **rainure d'isolation** sur toutes les bandes aux trous 22 et 23. Une rainure continue au cutter sur ces deux colonnes est plus rapide et plus sûre que 28 coupes ponctuelles ;
   - les 19 coupes de `plan.txt` §1.
2. **Contrôler à l'ohmmètre** : aucune continuité entre une bande quelconque côté bus (trous 1-21) et côté ESP32 (trous 24-57). Contrôler aussi chaque coupe (bande ouverte de part et d'autre).
3. Poser les **5 fils de liaison** (`plan.txt` §2), côté composants. Les fils 4 et 5 passent sous le SuperMini : prendre du fil isolé et le plaquer.
4. Monter les composants **du plus bas au plus haut** : résistances couchées, diodes, résistances debout, supports DIP-6 (conseillés), transistors, borniers, barrettes femelles du SuperMini, C1.
5. Avant d'enficher le SuperMini et les 4N25, alimenter par J2 en 5 V et vérifier : 5 V sur J4 (5V), 0 V entre J4 GND et la bande M ; puis, module enfiché, 3,3 V sur la bande K.

## 3. Choix des composants traversants

| Réf. | CMS (carte) | Traversant (plaquette) | Remarque |
|---|---|---|---|
| Q1 / Q2 | BC847C / BC857C, SOT-23 | **BC547C / BC557C**, TO-92 | mêmes puces et gains (β 420-800), ceux de l'adaptateur V3. Brochage différent (TO-92 : 1 C, 2 B, 3 E), le symbole du schéma est changé en conséquence. Empreinte TO-92 « Wide » : pattes au pas de 2,54 mm |
| D3 | SMAJ18CA (400 W) | **SA18CA** (500 W, DO-15) | même V_RWM (18 V), bidirectionnelle. Montée debout au pas de 2,54 mm (D10-E10) : elle relie `BUS_P` (bande D) à `CL_N_IN` (bande E), deux bandes voisines |
| F1 | MF-MSMF010-2 (1812) | **MF-R010** (radiale, pas 5,1 mm) | même maintien (0,10 A). Empreinte locale `alfea_tht:PTC_Radial_P5.08mm` à pattes droites, celles de KiCad étant décalées |
| D4 | SS14 | **1N5819** (DO-41) | Schottky 1 A, 40 V, comme le SS14 |
| D2 | 1N4148W | 1N4148 (DO-35) | |
| C1 | 100 µF 10 V | 100 µF **16 V**, radial Ø 5 mm | marge de tension, même encombrement |
| D5 | PESD5V0S1BA | **non montée** | aucune protection ESD bidirectionnelle 5 V courante en traversant. Les TVS DO-15 de 5 V (SA5.0CA) fuient de l'ordre de la centaine de µA à 3,3 V [SUPPOSÉ, ordre de grandeur des datasheets], ce qui est trop pour le rappel de 4,7 kΩ du DHT22. Pour un banc d'essai avec un câble court, R10 (100 Ω) et les diodes internes de la GPIO suffisent. L'emplacement L31-M31 reste libre : on peut y souder une PESD5V0S1BA en CMS côté cuivre, à cheval sur les bandes L et M |
| R | 0805 / 1206 | 0207, 0,25 W | P(R2) max 85 mW (09 §2.2) : 0,25 W convient |
| J1-J3, OK1-2, J4-J5 | inchangés | inchangés | déjà traversants |

Nomenclature complète : `alfea/hardware/carte_bsb_c3_tht/sorties/bom.csv` (D5 exclue).

## 4. Implantation

```
 trous 1 ......... 21 |22 23| 24 ................. 39   41 ... 47   48 ......... 57
       J1 F1 D2 D3 Q1 R7  | iso | R4  Q2 R3 R8 R6 R5 R10  [SuperMini]   D4 C2 C1  J2
             D1 R1 R2     |     | R9  D5                   USB en bas              J3
       OK1, OK2 à cheval sur la rainure (rangées de broches aux trous 21 et 24)
```
- **Côté bus** (trous 1-21, bandes B-I) : J1 au bord gauche (fils vers la gauche), puis l'étage d'entrée et d'émission.
- **Isolation** : toutes les bandes coupées aux trous 22 et 23. Distance de cuivre ≥ 5 mm entre les deux côtés (2 pas d'écart + bords de coupe), sous les 4N25 dont les rangées sont à 7,62 mm.
- **SuperMini** : les rangées de broches doivent être verticales, sinon les 8 broches d'une rangée tomberaient sur la même bande. On le monte donc **USB vers le bas**, colonne GPIO (GPIO5-21) au trou 41, colonne d'alimentation (5V, GND, 3V3, GPIO4-0) au trou 47. Les 8 bandes sont coupées sous le module (trou 42). **[À VÉRIFIER avant de souder les barrettes]** : en tenant le module USB vers le bas, composants au-dessus, la colonne marquée 5V / G / 3.3 doit être à droite. Si c'est l'inverse sur votre lot, le dire : le plan se régénère en échangeant J4 et J5.
- Sous le module, réhaussé d'environ 8,5 mm par les barrettes : C3 et deux fils, éléments bas uniquement.
- **Borniers** : J2 (5 V externe) et J3 (DHT22) au bord droit, fils vers la droite. Le sens d'entrée est déduit de l'empreinte KiCad **[À VÉRIFIER sur la pièce]**.

## 5. Bandes et nets (extrait de `plan.txt` §4)

| Net | Bande(s) | Remarque |
|---|---|---|
| `BUS_N` | B1-21 et I1-19 | reliées par le fil 1 (B19 → I19) |
| `BUS_P` | D1-21 | |
| `BUS_Q1_B` | C1-21 | |
| `CL_P_IN` / `CL_N_IN` | F1-6 / E1-10 | entre J1 et F1 / D2 et D3 |
| `+3V3` | H24-33, H43-47, K24-57 | fils 2 (H27 → K27) et 5 (H45 → K45) |
| `GND` | D24-37, I43-57, M24-57 | fils 3 (D34 → M34) et 4 (I43 → M43) |
| `RX` / `TX` / `DHT_IO` | I24-41 / H35-41 / J24-41 | vers les GPIO 6, 7, 5 du module |
| `+5V` / `5V_IN` | J43-57 / H49-57 | |

## 6. Limites

- La plaquette est un **montage d'essai** : pas de plan de masse, ni de zone dégagée sous l'antenne (les bandes passent sous le module). La portée WiFi peut être un peu inférieure à celle de la carte CMS.
- L'isolation (≥ 5 mm de cuivre à cuivre, à l'air) est fonctionnelle, comme sur la carte CMS (09 §5). Elle ne vaut **pas** isolation de sécurité.
- Les tests sur la PAC réelle restent soumis à la GATE 3.
