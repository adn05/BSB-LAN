# 13 — Boîtier imprimable en 3D de la carte d'interface

> **Résumé**
> Boîtier en **deux pièces** (fond et couvercle), **81,8 × 41,8 × 40,8 mm** hors pattes murales, généré par un script CadQuery paramétrique (`alfea/hardware/boitier/boitier.py`) dans Docker. Fichiers à imprimer : `alfea/hardware/boitier/sorties/boitier_fond.stl` et `boitier_couvercle.stl` (STEP à côté).
> **4 vis M3 × 40** traversent le couvercle, ses colonnes et la carte, et se vissent dans 4 inserts à chaud posés dans les entretoises du fond. Ouvertures : USB-C (paroi droite), presse-étoupe **M12** pour le bus (gauche), **M8** pour le DHT22 (avant), M8 à percer pour l'entrée 5 V (arrière), fenêtre Ø 3,2 au-dessus de la LED de bus D1.
> Contrôle automatique : aucune interférence entre les pièces, la carte et l'encombrement des connecteurs [CONSTATÉ]. Plusieurs cotes reposent sur des hypothèses à mesurer sur le matériel (§5).

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**. Repère : X le long de la carte (0 = bord gauche, côté J1), Y en largeur (0 = bord avant, côté J3), Z vertical (0 = dessous du fond). Carte KiCad : X = x − 100, Y = 133 − y.

---

## 1. Conception

| Élément | Choix | Justification |
|---|---|---|
| Fixation | 4 entretoises Ø 7 × 6 mm dans le fond, 4 colonnes Ø 6,5 dans le couvercle, aux trous M3 de la carte (H1 à H4) | une seule vis par coin tient la carte et le couvercle ; la carte est pincée entre entretoise et colonne |
| Vis | **M3 × 40**, tête cylindrique (ISO 7380 ou ISO 4762), posée sur le couvercle | empilage : couvercle 2,4 + colonne 28,4 + carte 1,6 = 32,4 mm, donc 7,6 mm dans l'insert |
| Inserts | M3 × 5,7, trou Ø 4,0 × 6 mm en tête d'entretoise, puis Ø 3,0 pour la pointe de la vis | tenue dans le plastique malgré les démontages |
| Entretoises | 6 mm sous la carte | les pattes traversantes dépassent de **1,8 mm** sous la carte [CONSTATÉ, STEP KiCad] |
| Parois, fond, couvercle | 2,4 mm (6 lignes à la buse de 0,4 mm) | rigidité, tenue des presse-étoupe |
| Centrage du couvercle | lèvre de 1,2 × 3 mm, jeu de 0,25 mm | positionnement sans forcer |
| Hauteur intérieure | **36 mm** (du fond au couvercle) | fiches J1/J2 à **fil par le dessus** : embase 9,4 mm + fiche 15,6 mm [CONSTATÉ, fiches Hong Cheng], enfichée à ≈ 19 mm au-dessus de la carte [SUPPOSÉ : 6 mm d'emboîtement], plus le rayon de courbure des fils vers les presse-étoupe |
| Jeux carte → paroi | gauche 10 mm, arrière 3 mm, avant et droite 1 mm | gauche : écrou du presse-étoupe M12 hors de la fiche J1 ; arrière : débord possible de la fiche J2 au-delà de l'embase (11,4 mm contre 7,5 mm) |
| Fixation murale | 2 pattes de 10 mm, trou Ø 4,5 | vis Ø 4 sur le mur de la chaufferie |

## 2. Ouvertures

| Ouverture | Paroi | Position | Cote | Origine |
|---|---|---|---|---|
| USB-C du SuperMini | droite | Y = 16,47, axe à Z = 23,7 | 13 × 9 mm | axe des barrettes J4/J5 (PCB) ; hauteur : barrette femelle 8,6 mm [CONSTATÉ] + entretoise des picots 2,5 mm + circuit 1 mm + demi-prise 1,6 mm [SUPPOSÉ]. L'ouverture laisse ± 2 mm de marge et passe la surmoulure d'un câble USB-C courant (≈ 12 × 6,5 mm) |
| Bus BSB (J1) | gauche | Y = 16,48, Z = 22,4 | Ø 12,2 (M12 × 1,5) | axe de J1 ; écrou (≈ Ø 17) au-dessus du fond et à gauche de la carte |
| DHT22 (J3) | avant | X = 52, Z = 26,4 | Ø 8,2 (M8 × 1,25) | décalé de J3 pour que l'écrou ne touche pas le connecteur Dupont enfiché sur J3 |
| Entrée 5 V (J2) | arrière | X = 50, Z = 26,4 | Ø 8,2, **opercule de 0,6 mm** | fermé par défaut (alimentation par l'USB-C) ; à percer si J2 sert. Décalé de J2 pour la même raison |
| LED de bus D1 | couvercle | X = 15,03, Y = 5,76 | Ø 3,2 | au-dessus de D1 ; guide de lumière Ø 3 en option, la LED étant à 30 mm sous le couvercle |

Les écrous des presse-étoupe restent sous la lèvre du couvercle (Z ≤ 35).

## 3. Contrôles [CONSTATÉ, `sh docker/cadquery/boitier.sh`]

Le script calcule le volume commun entre chaque pièce imprimée et :
- le volume de la carte, exporté par KiCad 9.0.6 (`kicad-cli pcb export step --board-only`) ;
- l'encombrement simplifié des composants hauts. Les cotes viennent du STEP KiCad de la carte avec ses modèles 3D (embases J1/J2 9,3 mm, barrettes 8,6 mm, 4N25 3,8 mm, pattes −1,8 mm), des fiches Hong Cheng, ou d'hypothèses marquées dans le script : SuperMini, USB-C, fiches J1/J2 enfichées, connecteur Dupont sur J3.

Résultat : **0 mm³** partout, couvercle et fond compris (le contact carte/entretoises et carte/colonnes a un volume nul). La génération échoue sinon.

Fichiers (`alfea/hardware/boitier/sorties/`) : `boitier_fond.step/.stl`, `boitier_couvercle.step/.stl`, `boitier_assemblage.step` (fond, couvercle, carte et encombrements en orange, à ouvrir dans FreeCAD ou un visualiseur STEP), `apercu.png` (assemblage, coupe, vue de dessus).

## 4. Impression et montage

| Sujet | Recommandation |
|---|---|
| Matière | **PETG** (ou ASA) : chaufferie de 0 à 50 °C [SUPPOSÉ, 09 §5]. Le PLA ramollit vers 55-60 °C et se déforme sous la tête des vis |
| Orientation | fond posé sur son dessous ; couvercle **à l'envers** (face supérieure sur le plateau, colonnes vers le haut). Aucun support nécessaire : les ouvertures des parois sont des ponts de 13 mm au plus |
| Réglages | couches de 0,2 mm, 4 parois, 25 % de remplissage ; 100 % autour des inserts si le trancheur le permet |
| Inserts | les poser au fer (≈ 230 °C pour le PETG), bien d'aplomb, avant de monter la carte |
| Montage | 1. inserts ; 2. presse-étoupe ; 3. carte sur les entretoises, SuperMini enfiché ; 4. fils serrés dans les fiches JJ1 (et JJ2), passés dans les presse-étoupe, fiches enfichées ; 5. câble du DHT22 ; 6. couvercle et 4 vis M3 × 40, serrage modéré |

**Quincaillerie** : 4 vis M3 × 40, 4 inserts M3 × 5,7 (Ø extérieur 4,6, trou de 4,0), 1 presse-étoupe M12 × 1,5 (câble de 3 à 6,5 mm) avec écrou, 1 presse-étoupe M8 × 1,25 (câble de 2 à 5 mm), un second si J2 sert ; en option, un guide de lumière Ø 3 × 30 mm et 2 vis murales Ø 4.

## 5. Hypothèses à vérifier avant impression

| Cote | Valeur retenue | Comment la vérifier |
|---|---|---|
| Hauteur de la fiche J1/J2 enfichée | 19 mm au-dessus de la carte [SUPPOSÉ] | enficher JJ1 sur J1 et mesurer ; si plus de 22 mm, augmenter `H_INT` |
| Côté du verrou des fiches (débord de 3,9 mm) | vers l'intérieur de la carte [SUPPOSÉ] | à l'œil sur la carte montée ; s'il est vers le bord arrière, garder `JEU_AR` = 3 mm au moins |
| Hauteur du SuperMini (entretoise des picots) | 2,5 mm [SUPPOSÉ] | mesurer le dessus du circuit du SuperMini enfiché : axe USB attendu à 13,7 mm au-dessus de la carte |
| Débord de l'USB-C au-delà du module | 0,6 mm [SUPPOSÉ] | pied à coulisse ; le jeu à droite est de 1 mm |
| Connecteur Dupont sur J3 | 14 mm de haut [SUPPOSÉ] | selon le câble du DHT22 |
| Écrous des presse-étoupe | M12 : Ø ≈ 17 ; M8 : Ø ≈ 15 [SUPPOSÉ] | selon le modèle acheté |

Toutes ces cotes sont des paramètres en tête de `boitier.py`. Après modification : `sh docker/cadquery/boitier.sh`, qui régénère tout et refait le contrôle d'interférence.

## 6. Régénération

`sh docker/cadquery/boitier.sh` depuis la racine du dépôt (≈ 10 s une fois l'image construite) :
1. export du volume de la carte par `kicad/kicad:9.0.6` dans `alfea/build/boitier/` (ignoré par git) ;
2. génération dans l'image `alfea-cadquery:2.5.2` (`docker/cadquery/Dockerfile` : Python 3.11, CadQuery 2.5.2, OCP 7.7.2, versions figées), contrôle d'interférence, exports STEP, STL et aperçu.
