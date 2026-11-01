"""Variante traversante de la carte d'interface, pour plaquette d'essai à bandes horizontales.

Même schéma que carte_bsb_c3 (même netlist, carte.py) ; seules changent les valeurs
de boîtier, les empreintes et les références fabricant (docs/claude/09b_plaquette_essai.md).

Repère : colonne c (trous de gauche à droite), rangée r (bandes de haut en bas), pas 2,54 mm.
Chaque bande court sur toute la largeur ; COUPES coupe la bande au trou indiqué ;
LIENS sont des fils (côté composants) entre deux trous de la même colonne.
"""

PROJET = 'carte_bsb_c3_tht'
LIB_LOCALE = 'alfea_tht'

PAS = 2.54
ORIGINE = (100.0, 100.0)            # position (mm) du trou (0, 0)
COLONNES = (-1, 55)                 # première et dernière colonne de la plaquette
RANGEES = (-1, 12)                  # première et dernière bande

RV = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical'
RV5 = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P5.08mm_Vertical'
CDISC = 'Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm'

# référence : (valeur, empreinte, référence fabricant, {pastille: (colonne, rangée)})
# Deux pastilles suffisent à fixer la position et l'orientation ; les autres sont contrôlées.
COMPOSANTS = {
    # --- côté bus
    'J1': ('BSB (X86)', None, None, {'1': (1, 4), '2': (1, 3)}),
    'F1': ('PTC 0,1 A', f'{LIB_LOCALE}:PTC_Radial_P5.08mm', 'Bourns MF-R010 (radiale, pas 5,1 mm)', {'1': (4, 4), '2': (4, 2)}),
    'D2': ('1N4148', 'Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal', '1N4148 (DO-35)', {'1': (6, 3), '2': (6, 0)}),
    'Q1': ('BC547C', 'Package_TO_SOT_THT:TO-92_Inline_Wide', 'BC547C', {'1': (8, 2), '3': (8, 0)}),
    'R7': ('330k', RV, '330 kOhm 1 % 0,25 W', {'1': (10, 1), '2': (10, 0)}),
    'D1': ('rouge', 'LED_THT:LED_D3.0mm', 'LED rouge 3 mm', {'1': (10, 7), '2': (10, 6)}),
    'R1': ('330k', RV5, '330 kOhm 1 % 0,25 W', {'1': (12, 1), '2': (12, 3)}),
    'R2': ('1k5', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', '1,5 kOhm 1 % 0,25 W', {'1': (14, 2), '2': (14, 5)}),
    'D3': ('SA18CA', 'Diode_THT:D_DO-15_P5.08mm_Vertical_AnodeUp', 'Littelfuse SA18CA (500 W, DO-15)', {'1': (16, 2), '2': (16, 0)}),
    'OK2': ('4N25', None, None, {'1': (22, 3), '4': (19, 1)}),
    'OK1': ('4N25', None, None, {'1': (19, 5), '4': (22, 7)}),
    # --- côté ESP32
    'R4': ('330k', RV5, '330 kOhm 1 % 0,25 W', {'1': (24, 5), '2': (24, 7)}),
    'Q2': ('BC557C', 'Package_TO_SOT_THT:TO-92_Inline_Wide', 'BC557C', {'1': (27, 4), '3': (27, 6)}),
    'R9': ('4k7', RV, '4,7 kOhm 1 % 0,25 W', {'1': (27, 10), '2': (27, 9)}),
    'R3': ('300', RV, '300 Ohm 1 % 0,25 W', {'1': (29, 4), '2': (29, 3)}),
    'D5': ('non monté', 'Diode_THT:D_DO-35_SOD27_P2.54mm_Vertical_AnodeUp', 'emplacement libre (option ESD, voir 09b)', {'1': (29, 10), '2': (29, 11)}),
    'R8': ('10k', RV, '10 kOhm 1 % 0,25 W', {'1': (31, 5), '2': (31, 6)}),
    'R6': ('4k7', RV, '4,7 kOhm 1 % 0,25 W', {'1': (33, 6), '2': (33, 5)}),
    'R5': ('4k7', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal', '4,7 kOhm 1 % 0,25 W', {'1': (35, 7), '2': (35, 11)}),
    'R10': ('100', RV5, '100 Ohm 0,25 W', {'1': (37, 10), '2': (37, 8)}),
    'J5': ('SuperMini GPIO', None, None, {'1': (39, 8), '2': (39, 7)}),
    'J4': ('SuperMini alim.', None, None, {'1': (45, 8), '2': (45, 7)}),
    'C3': ('100n', CDISC, '100 nF X7R 50 V', {'1': (42, 6), '2': (42, 7)}),
    'D4': ('1N5819', 'Diode_THT:D_DO-41_SOD81_P5.08mm_Vertical_AnodeUp', '1N5819 (Schottky 1 A, 40 V)', {'1': (47, 8), '2': (47, 6)}),
    'C2': ('100n', CDISC, '100 nF X7R 50 V', {'1': (49, 8), '2': (49, 7)}),
    'C1': ('100u 16V', 'Capacitor_THT:CP_Radial_D5.0mm_P2.50mm', '100 uF 16 V radial D5', {'1': (51, 8), '2': (51, 7)}),
    'J2': ('5V ext.', None, None, {'1': (54, 6), '2': (54, 7)}),
    'J3': ('DHT22', None, None, {'1': (54, 9), '2': (54, 10)}),
}

# Composants non montés (gardés dans le schéma et la netlist).
NON_MONTES = {'D5'}

# Symboles remplacés : les BC847/BC857 (SOT-23, broches B E C) deviennent des BC547/BC557 (TO-92, C B E).
SYMBOLES = {'Transistor_BJT:BC847': 'Transistor_BJT:BC547', 'Transistor_BJT:BC857': 'Transistor_BJT:BC557'}
# ancienne broche -> nouvelle broche (B: 1 -> 2, E: 2 -> 3, C: 3 -> 1)
BROCHES_TO92 = {'1': '2', '2': '3', '3': '1'}

# Isolation : toutes les bandes sont coupées aux colonnes 20 et 21 (rainure entre les rangées des 4N25).
ISOLATION = (20, 21)

COUPES = [
    (5, 4), (7, 3),                                   # fin de CL+ et de CL- (entrée J1)
    (18, 7),                                          # isole OK1-3 (non connectée)
    (25, 5), (30, 3), (30, 4), (32, 6), (36, 1), (36, 2), (36, 5),
    (40, 1), (40, 2), (40, 3), (40, 4), (40, 5), (40, 6), (40, 7), (40, 8),   # sous le SuperMini
    (46, 6),                                          # 3V3 du module | entrée 5 V
]

# Fils de liaison (net, colonne, rangée de départ, rangée d'arrivée).
LIENS = [
    ('BUS_N', 17, 0, 7),
    ('+3V3', 25, 6, 9),
    ('GND', 32, 2, 11),
    ('GND', 41, 7, 11),
    ('+3V3', 43, 6, 9),
]
