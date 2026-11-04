# 14 — Alimentation de l'ESP32 par G+ de X86 (variante A, isolée)

> **Résumé**
> Proposition à la demande de l'utilisateur, en **schéma seul**, sans PCB : `alfea/hardware/proposition_alim_gplus/alim_gplus.kicad_sch`. Le schéma principal et le PCB routé ne sont pas modifiés.
> Le 5 V de l'ESP32 est pris sur **G+ (X86-3, 11,6 V mesurés)**. La chaîne est la suivante : diode anti-inversion, **limiteur de courant à environ 120 mA** (protège la sortie G+, dont la puissance n'est pas documentée), réserve de 470 µF, puis **convertisseur isolé non régulé B1205S-2WR3** (12 V vers 5 V, 400 mA, 1,5 kVDC). Sa sortie arrive sur le net `5V_IN` existant, en amont de D4, comme J2.
> **Les optocoupleurs et toute l'interface bus sont conservés** (décision de l'utilisateur, variante A) : l'ESP32 reste isolé du bus, et l'USB-C se branche toujours sans précaution.
> Coût : aucune nouvelle référence CMS Extended facturée (Q3 est Preferred). Trois composants traversants (U3, C5, C7). **Prérequis avant toute réalisation : un essai de charge de G+ (§6).**
> ERC 0 [CONSTATÉ, `kicad/kicad:9.0.6`], netlist contrôlée.

Conventions : **[CONSTATÉ]**, **[SUPPOSÉ]**, **[À VÉRIFIER]**.

---

## 1. Données d'entrée

| Donnée | Valeur | Source |
|---|---|---|
| Tension de G+ par rapport à X86-2 | **11,6 V** à vide (11,5 V sur CL+) | mesure de l'utilisateur, 2026-11-04 (09 §8) [CONSTATÉ] |
| Rôle de G+ | « Power supply DC 12 V » du rétroéclairage du QAA75.611 (borne 3) ; réservée sur le QAA75.610 | doc Siemens Albatros2 / RVS41 [CONSTATÉ] ; BSB-LAN : « provides power only, no data » (`docs/en/install.md:44`) |
| Courant disponible sur G+ | **non documenté** : ni Siemens, ni Atlantic, ni BSB-LAN | **[À VÉRIFIER par l'essai de charge, §6]** |
| Besoin de l'ESP32 sur 5 V | ≈ 0,1 A en moyenne (0,5 W), ≈ 0,36 A en pointe d'émission WiFi | 09 §4 [SUPPOSÉ, ordres de grandeur de datasheet, à mesurer en T1] |

G+ est conçue pour un rétroéclairage, sans doute quelques dizaines de mA [SUPPOSÉ]. Notre besoin moyen, ≈ 60 mA sous 11,6 V (§3), est du même ordre ou au-dessus. **D'où le limiteur et l'essai de charge** : on ne sait pas si l'alimentation interne de G+ est commune à CL+, ni si elle supporte ce courant.

## 2. Choix d'architecture

| Option | Analyse | Choix |
|---|---|---|
| **Convertisseur isolé non régulé** (B1205S-2WR3, rapport fixe) | garde l'isolation des optocoupleurs. Il se comporte comme un transformateur : derrière un limiteur, il ralentit simplement la montée de tension, sans instabilité. Faible consommation à vide (2 mA) | **retenu** |
| Convertisseur isolé régulé à entrée large (HLK URB1205S / URB2405S-3WR3) | régulé, mais **appel au démarrage de 631 mA en moyenne** pour la série 12 V (datasheet Hi-Link, §4), soit 5 fois la limite prévue. La série 24 V demande jusqu'à 18 V pour démarrer. À puissance constante, il présente une résistance d'entrée négative : derrière un limiteur, il oscillerait (démarrages en boucle) | rejeté |
| Abaisseur non isolé 12 V vers 5 V | masse de l'ESP32 reliée à CL- : l'isolation des optocoupleurs ne sert plus à rien, et l'USB-C d'un PC relié à la terre serait relié à la PAC | rejeté (variante B, écartée par l'utilisateur) |
| Pas de limiteur | à la mise sous tension, C5 et C7 tirent un courant non borné sur G+ ; un défaut côté carte la court-circuite | rejeté |

## 3. Schéma et calculs

Nets : `GP_IN` (G+ après J6), `GP_D` (après D6, rail positif), `GP_LIM` (retour du module, collecteur de Q3), `GP_S` (shunt), `GP_B` (base de Q3), `GP_RET` (X86-2). Les nets `5V_IN` et `GND` sont ceux du schéma principal.

| Réf. | Valeur | Rôle | JLCPCB |
|---|---|---|---|
| J6 | HC-JXDZVC-3.5-2P | 1 = G+ (X86-3), 2 = CL- (X86-2) | C51927058 (déjà J1, J2) |
| D6 | SS14 | anti-inversion : U3 ne tolère que −0,7 V | C2480 (déjà D4) |
| C4 | 100 nF 0805 | découplage d'entrée | C49678 (déjà C2, C3) |
| Q3 | BCP56-16, SOT-223 | ballast du limiteur, côté retour | C41375109, **Preferred** (sans frais) |
| Q4 | BC847C | mesure : il retire le courant de base de Q3 quand V(R12 // R13) atteint Vbe | C7420337 (déjà Q1) |
| R11 | 4,7 kΩ | polarisation de Q3 | C17673 (déjà R5, R6, R9) |
| R12, R13 | 10 Ω 0805 en parallèle (5 Ω) | shunt ; pas de 5 Ω en Basic | C17415, Basic |
| C5 | 470 µF 25 V polymère, radial D6,3 | réserve d'énergie pour les pointes WiFi | C46550440 (traversant) |
| C6 | 22 µF 25 V 1206 | découplage au plus près de U3 | C12891 (déjà C1) |
| U3 | **B1205S-2WR3** (YLPTEC) | isolement 1,5 kVDC, 5 V 400 mA, SIP 19,5 × 7 mm, broches 1 +Vin, 2 −Vin, 4 −Vo, 6 +Vo | C2992387 (traversant) |
| C7 | 470 µF 25 V polymère | sortie : pointes WiFi (charge capacitive max. du module : 2 400 µF) | C46550440 |
| R14 | 270 Ω 1206, **non montée** | charge minimale, seulement si `5V_IN` dépasse 5,8 V à vide | C4466 |

**Limiteur.** I_max = Vbe(Q4) / (R12 // R13) ≈ 0,62 / 5 = **124 mA** à 25 °C, ≈ 114 mA à 50 °C (−2 mV/°C) [SUPPOSÉ : Vbe typique du BC847C à 1-2 mA]. En dessous de la limite, Q3 est saturé : I_B = (11,3 − 0,7 − 0,3) / 4,7 kΩ ≈ 2,2 mA, soit un β forcé de 27 à 60 mA, très en dessous du hFE minimal de 100. La chute vaut Vce,sat ≈ 0,1 V plus 0,3 V dans le shunt.

**Tensions à 60 mA moyens** [SUPPOSÉ : chutes typiques] :

| Point | Tension |
|---|---|
| G+ | 11,6 V [CONSTATÉ à vide] |
| après D6 (SS14 ≈ 0,3 V) | 11,3 V |
| entrée de U3 (shunt 0,3 V + Q3 0,1 V) | **≈ 10,9 V**, soit 91 % du nominal (plage du module : 10,8 à 13,2 V) |
| sortie de U3, à environ 25 % de charge | ≈ 5,0 × 0,91 × 1,07 ≈ **4,9 V** [SUPPOSÉ : régulation de charge type B_S, environ +7 % à 25 % de charge] |
| broche 5 V du SuperMini (après D4, 0,3 à 0,4 V) | ≈ 4,5 V en moyenne, ≈ 4,1 V en pointe |
| marge du LDO ME6211 (3,3 V + 0,26 V de chute à 300 mA) | **≥ 0,5 V** en pointe |

Hors tolérance du module, au-dessous de 10,8 V, U3 n'est pas abîmé : sa sortie baisse dans le même rapport.

**Puissance prélevée sur G+.** Sortie moyenne de 0,5 W, rendement ≈ 75 % à faible charge [SUPPOSÉ ; 85/88 % à pleine charge selon la datasheet], soit ≈ 0,67 W en entrée et **≈ 61 mA sur G+ (0,71 W)**. En pointe, le module demande 1,75 W / 0,85 / 10,9 V ≈ 189 mA. Le limiteur plafonne à 124 mA et **C5 fournit les ≈ 65 mA restants** : ΔV = 65 mA × 2 ms / 470 µF ≈ **0,28 V** pour une rafale d'émission de 2 ms [SUPPOSÉ]. Pour 10 ms d'émission continue : 1,4 V, et le SuperMini reste au-dessus de 3,85 V. Une émission soutenue au-delà de 124 mA en moyenne ferait baisser la tension progressivement. Ce cas n'est pas réaliste pour BSB-LAN, mais il est à mesurer en T1.

**Mise sous tension.** C5 se charge à 124 mA en ≈ 11 V × 470 µF / 0,124 A ≈ **42 ms**, et C7 suit à travers U3. Q3 dissipe ½CV² ≈ 28 mJ, sans danger pour un SOT-223. L'alimentation de l'ESP32 monte en ≈ 50 à 100 ms, une rampe compatible avec l'ESP32-C3 [SUPPOSÉ : circuit RC sur EN du SuperMini].

**Défaut.** Si `GP_D`–`GP_LIM` est en court-circuit (C5 ou U3 claqué), Q3 dissipe 11,6 V × 0,124 A ≈ **1,44 W en continu**, soit plus que ses 1,33 W nominaux. Au routage, prévoir ≥ 2 cm² de cuivre sur la languette (collecteur, `GP_LIM`) ; G+ reste protégée dans tous les cas. Un court-circuit côté 5 V est géré par U3 (protection continue, réarmement automatique) [CONSTATÉ, datasheet].

**Isolation.** U3 est le seul composant à traverser la barrière : 1 500 VDC pendant 1 min [CONSTATÉ, datasheet]. Au PCB, il faut l'orienter à cheval sur la bande d'isolation. Entre les broches 2 (bus) et 4 (ESP32), il y a 5,08 − 1,5 = **3,58 mm** entre bords de pastilles avec l'empreinte retenue (TRACO TMA, pastilles de 1,5 mm), ce qui respecte l'objectif de 3 mm (09 §5). L'empreinte TRACO TMA a les mêmes broches 1, 2, 4 et 6 au pas de 2,54 mm. Son boîtier fait 6,3 mm d'épaisseur contre 7 mm pour le B1205S-2WR3 **[À VÉRIFIER au placement]**.

## 4. Intégration au schéma principal (à faire avec l'accord de l'utilisateur)

1. Copier le bloc dans `carte_bsb_c3.kicad_sch` : les nets `5V_IN` et `GND` s'y raccordent d'eux-mêmes. Le symbole de U3 est dans `proposition_alim_gplus/alim.kicad_sym`, à ajouter à `alfea.kicad_sym`.
2. **J2 et J6 sont exclusifs** : ne jamais raccorder une alimentation 5 V sur J2 quand G+ alimente J6. L'USB-C reste utilisable : D4 empêche le 5 V de l'USB de réalimenter U3.
3. Câblage : X86-3 vers J6-1, X86-2 vers J6-2. Deux fils se partagent donc la vis X86-2, avec J1-2. Option future, si l'utilisateur l'accepte : bornier 3 points (CL+, CL-, G+) et `GP_RET` relié à `CL_N_IN` sur la carte, ce qui ne laisse qu'un câble à 3 fils. Les empreintes des connecteurs ne sont pas modifiées pour l'instant (consigne de l'utilisateur).
4. PCB : environ 2,5 cm² de plus (U3 19,5 × 7 mm, deux condensateurs Ø 6,3, Q3). Il ne tient pas dans le 66 × 33 mm actuel sans agrandir la carte, puis il faut revoir le boîtier (doc 13).

## 5. Écarts et limites

- Écart à l'adaptateur V3 (règle 00 §2.4) : **ajout** d'une source d'alimentation. La partie bus, avec ses optocoupleurs, est inchangée.
- Charge ajoutée sur l'alimentation interne du RVS21 : ≈ 0,7 W en continu. Ses conséquences (échauffement, stabilité de CL+) ne sont pas connues **[À VÉRIFIER, §6]**.
- Le chargeur USB 5 V (09 §4) reste la solution par défaut tant que l'essai de charge n'est pas concluant.

## 6. Essai de charge de G+ (prérequis, PAC sous tension, IHM allumée)

Matériel : résistances de **220 Ω 2 W** (53 mA, 0,61 W) et **100 Ω 3 W** (116 mA, 1,35 W), deux multimètres. Précautions : comme en 09 §8 (230 V à proximité, pointes isolées). Les résistances chauffent : les poser à l'air, loin des câbles.

1. Résistance de 220 Ω entre X86-3 et X86-2. Pendant 5 min, relever **G+** (X86-3 / X86-2) et **CL+** (X86-1 / X86-2), et surveiller l'IHM.
2. Même chose avec 100 Ω.
3. **Critères d'acceptation** : à 116 mA, G+ ≥ 11,0 V ; CL+ varie de moins de 0,3 V ; aucune alarme ni redémarrage de l'IHM ou de la régulation.
4. Si G+ s'effondre ou si CL+ bouge : **abandon de la variante**, retour au chargeur USB. Si G+ tient à 53 mA mais pas à 116 mA : un shunt de 10 Ω seul (R13 non montée, ≈ 62 mA) est possible, mais la marge sur le besoin moyen (≈ 61 mA) devient nulle. À rediscuter.

## 7. Fichiers

| Fichier | Rôle |
|---|---|
| `alfea/hardware/proposition_alim_gplus/alim_gplus.kicad_sch`, `.kicad_pro` | schéma de la proposition (A4), connexions par fils |
| `alfea/hardware/proposition_alim_gplus/alim.kicad_sym`, `sym-lib-table` | symbole du B1205S-2WR3 (brochage de la datasheet YLPTEC, différent de la version 1 W) |
| `alfea/hardware/proposition_alim_gplus/sorties/` | `erc.rpt` (0 violation), `schema.pdf`, `schema.png`, `bom.csv` |

Contrôle : `kicad-cli sch erc --severity-all` dans `kicad/kicad:9.0.6`, puis vérification de la netlist exportée, net par net, contre le tableau du §3 [CONSTATÉ].
