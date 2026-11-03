# 13 — Boîtier imprimable en 3D de la carte d'interface

> **Résumé**
> Boîtier en **deux pièces** (fond et couvercle profond), **75,8 × 41,8 × 40,8 mm** hors pattes murales, généré par un script CadQuery paramétrique (`alfea/hardware/boitier/boitier.py`) dans Docker. Fichiers à imprimer : `alfea/hardware/boitier/sorties/boitier_fond.stl` et `boitier_couvercle.stl` (STEP à côté).
> **Ouvertures sur le plan de joint**, moitié dans chaque pièce : USB-C (droite), câble du bus (gauche), câble du DHT22 (avant). Pas de presse-étoupe ni d'insert : **4 vis M3 × 8** tiennent la carte et **4 vis M3 × 25** le couvercle, taraudées directement dans des avant-trous Ø 2,5. Deux pattes murales à bout arrondi, passage M4.
> Contrôle automatique : aucune interférence entre les pièces, la carte et l'encombrement des connecteurs [CONSTATÉ]. Plusieurs cotes reposent sur des hypothèses à mesurer sur le matériel (§5).

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**. Repère : X le long de la carte (0 = bord gauche, côté J1), Y en largeur (0 = bord avant, côté J3), Z vertical (0 = dessous du fond). Carte KiCad : X = x − 100, Y = 133 − y.

---

## 1. Conception

| Élément | Choix | Justification |
|---|---|---|
| Plan de joint | horizontal, à **Z = 23,7 mm**, sur l'axe de l'USB-C : fond de 23,7 mm, couvercle de 17,1 mm | toutes les ouvertures sont à cheval sur le joint (demande de l'utilisateur) ; les câbles sont pincés entre les deux pièces |
| Emboîtement | lèvre de 1 × 2 mm sur le pourtour intérieur du fond, logée dans le couvercle avec 0,2 mm de jeu | centrage et fermeture du joint |
| Carte | 4 entretoises Ø 7 × 6 mm ; **vis M3 × 8** tête cylindrique, avant-trou Ø 2,5 (6,4 mm de filet) | les pattes traversantes dépassent de **1,8 mm** sous la carte [CONSTATÉ, STEP KiCad] |
| Couvercle | 4 colonnes Ø 9 centrées sur les angles extérieurs ; **vis M3 × 25** par le dessus, passage Ø 3,4 dans le couvercle, avant-trou Ø 2,5 dans le fond (7,9 mm de filet) | vis de 25 mm au plus (contrainte de l'utilisateur) ; colonnes hors de la cavité, la carte occupant ses angles |
| Pas d'insert | avant-trous Ø 2,5, taraudés par la vis en forçant | demande de l'utilisateur. En PETG, Ø 2,5 pour M3 serre fort ; passer `AVANT_TROU` à 2,6 si le vissage force trop. Démontages répétés : le filet s'use, ne pas serrer au-delà du contact |
| Parois, fond, dessus | 2,4 mm (6 lignes à la buse de 0,4 mm) | rigidité |
| Hauteur intérieure | **36 mm** (du fond au dessous du couvercle) | fiches J1/J2 à **fil par le dessus** : embase 9,4 mm + fiche 15,6 mm [CONSTATÉ, fiches Hong Cheng], enfichée à ≈ 19 mm au-dessus de la carte [SUPPOSÉ : 6 mm d'emboîtement], plus la courbure des fils vers les sorties |
| Jeux carte → paroi | gauche 4 mm, arrière 3 mm, avant et droite 1 mm | gauche : passage des fils de J1 ; arrière : débord possible de la fiche J2 au-delà de l'embase (11,4 mm contre 7,5 mm) |
| Fixation murale | 2 pattes de 3 mm d'épaisseur, **bout arrondi R 8**, trou **Ø 4,5 pour vis M4** | demande de l'utilisateur |

## 2. Ouvertures (toutes centrées sur le plan de joint, Z = 23,7 mm)

| Ouverture | Paroi | Position | Cote | Origine |
|---|---|---|---|---|
| USB-C du SuperMini | droite | Y = 16,47 | 13 × 9 mm | axe des barrettes J4/J5 (PCB) ; hauteur : barrette femelle 8,6 mm [CONSTATÉ] + entretoise des picots 2,5 mm + circuit 1 mm + demi-prise 1,6 mm [SUPPOSÉ]. L'ouverture laisse ± 2 mm de marge et passe la surmoulure d'un câble USB-C courant (≈ 12 × 6,5 mm) |
| Bus BSB (J1) | gauche | Y = 16,48 (axe de J1) | Ø 7 | paire de fils ou câble jusqu'à Ø 6 |
| DHT22 (J3) | avant | X = 37,1 (en face de J3) | Ø 5,5 | câble du capteur |
| Entrée 5 V (J2) | arrière | X = 37,15 | Ø 7 | **désactivée par défaut** (`OUVERTURE_J2 = False`) : alimentation par l'USB-C. Passer à `True` si J2 sert |
| LED de bus D1 | dessus | X = 15,03, Y = 5,76 | Ø 3,2 | au-dessus de D1 ; guide de lumière Ø 3 en option, la LED étant à 30 mm sous le dessus |

Un câble plus fin que son ouverture peut être entouré d'un tour de ruban ou d'un passe-fil pour être serré par le joint.

## 3. Contrôles [CONSTATÉ, `sh docker/cadquery/boitier.sh`]

Le script calcule le volume commun entre chaque pièce imprimée et :
- le volume de la carte, exporté par KiCad 9.0.6 (`kicad-cli pcb export step --board-only`) ;
- l'encombrement simplifié des composants hauts et des têtes des vis de la carte. Les cotes viennent du STEP KiCad de la carte avec ses modèles 3D (embases J1/J2 9,3 mm, barrettes 8,6 mm, 4N25 3,8 mm, pattes −1,8 mm), des fiches Hong Cheng, ou d'hypothèses marquées dans le script : SuperMini, USB-C, fiches J1/J2 enfichées, connecteur Dupont sur J3.

Résultat : **0 mm³** partout, entre fond et couvercle compris (le contact carte/entretoises a un volume nul). Le script vérifie aussi la longueur des vis : 6,4 mm de filet pour la carte, 7,9 mm pour le couvercle (au moins 6 mm exigés). La génération échoue sinon.

Fichiers (`alfea/hardware/boitier/sorties/`) : `boitier_fond.step/.stl`, `boitier_couvercle.step/.stl`, `boitier_assemblage.step` (fond, couvercle, carte et encombrements en orange, à ouvrir dans FreeCAD ou un visualiseur STEP), `apercu.png` (assemblage, coupe, vue de dessus).

## 4. Impression et montage

| Sujet | Recommandation |
|---|---|
| Matière | **PETG** (ou ASA) : chaufferie de 0 à 50 °C [SUPPOSÉ, 09 §5]. Le PLA ramollit vers 55-60 °C |
| Orientation | fond posé sur son dessous ; couvercle **à l'envers** (dessus sur le plateau). Aucun support : les demi-ouvertures débouchent sur le joint |
| Réglages | couches de 0,2 mm, 4 parois, 25 % de remplissage ; 4 parois suffisent à donner de la matière pleine autour des avant-trous |
| Montage | 1. visser la carte (4 × M3 × 8), SuperMini enfiché ; 2. fils serrés dans les fiches JJ1 (et JJ2), fiches enfichées ; 3. câble du DHT22 sur J3 ; 4. poser les câbles dans les demi-ouvertures du fond ; 5. couvercle, puis 4 × M3 × 25, serrage modéré |

**Quincaillerie** : 4 vis M3 × 8 et 4 vis M3 × 25, tête cylindrique (ISO 7380 ou ISO 4762) ; 2 vis murales M4 ; en option, un guide de lumière Ø 3 × 30 mm.

## 5. Hypothèses à vérifier avant impression

| Cote | Valeur retenue | Comment la vérifier |
|---|---|---|
| Hauteur de la fiche J1/J2 enfichée | 19 mm au-dessus de la carte [SUPPOSÉ] | enficher JJ1 sur J1 et mesurer ; si plus de 22 mm, augmenter `H_INT` |
| Côté du verrou des fiches (débord de 3,9 mm) | vers l'intérieur de la carte [SUPPOSÉ] | à l'œil sur la carte montée ; s'il est vers le bord arrière, garder `JEU_AR` = 3 mm au moins |
| Hauteur du SuperMini (entretoise des picots) | 2,5 mm [SUPPOSÉ] | mesurer : axe de l'USB-C attendu à 13,7 mm au-dessus de la carte. Le plan de joint suit (`Z_JOINT = USB_Z`) |
| Débord de l'USB-C au-delà du module | 0,6 mm [SUPPOSÉ] | pied à coulisse ; le jeu à droite est de 1 mm |
| Connecteur Dupont sur J3 | 14 mm de haut [SUPPOSÉ] | selon le câble du DHT22 |
| Diamètres des câbles | bus ≤ 6 mm, DHT22 ≤ 5 mm [SUPPOSÉ] | ajuster `CABLE_J1` et `CABLE_DHT` |

Toutes ces cotes sont des paramètres en tête de `boitier.py`. Après modification : `sh docker/cadquery/boitier.sh`, qui régénère tout et refait les contrôles.

## 6. Régénération

`sh docker/cadquery/boitier.sh` depuis la racine du dépôt (≈ 10 s une fois l'image construite) :
1. export du volume de la carte par `kicad/kicad:9.0.6` dans `alfea/build/boitier/` (ignoré par git) ;
2. génération dans l'image `alfea-cadquery:2.5.2` (`docker/cadquery/Dockerfile` : Python 3.11, CadQuery 2.5.2, OCP 7.7.2, versions figées), contrôles, exports STEP, STL et aperçu.
