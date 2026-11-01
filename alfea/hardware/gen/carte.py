"""Description unique de la carte d'interface BSB pour ESP32-C3 SuperMini.

Source de vérité du schéma et du PCB (docs/claude/09_design_carte_interface.md).
Chaque composant : référence, symbole, valeur, empreinte, référence fabricant,
position sur le schéma (mm, rotation 0), position sur le PCB (mm, rotation),
et affectation broche -> net. Les broches listées dans `nc` sont non connectées.
"""

PROJET = 'carte_bsb_c3'

# Nets côté bus : BUS_*, côté ESP32 : le reste. Aucun net ne traverse la frontière.
NETS_BUS = {'CL_P_IN', 'CL_N_IN', 'BUS_P', 'BUS_N', 'BUS_R2_OK1', 'BUS_OK1_D1', 'BUS_OK2_B', 'BUS_Q1_B'}

R0805 = 'Resistor_SMD:R_0805_2012Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'

COMPOSANTS = [
    # --- Entrée bus et protections (côté bus)
    dict(ref='J1', lib='Connector:Screw_Terminal_01x02', val='BSB (X86)', fp='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MPT-0,5-2-2.54_1x02_P2.54mm_Horizontal',
         mpn='Phoenix MPT 0,5/2-2,54', sch=(30.48, 63.5), pcb=(103.62, 117.7, 90),
         pins={'1': 'CL_P_IN', '2': 'CL_N_IN'}),
    dict(ref='F1', lib='Device:Polyfuse', val='PTC 0,1 A', fp='Fuse:Fuse_1812_4532Metric', mpn='Bourns MF-MSMF010-2',
         sch=(55.88, 50.8), pcb=(110.5, 104.0, 0), pins={'1': 'CL_P_IN', '2': 'BUS_P'}),
    dict(ref='D3', lib='Device:D_TVS', val='SMAJ18CA', fp='Diode_SMD:D_SMA', mpn='Littelfuse SMAJ18CA',
         sch=(76.2, 73.66), pcb=(117.5, 106.0, 90), pins={'1': 'BUS_P', '2': 'CL_N_IN'}),
    # --- Réception : bus -> OK1 (côté bus)
    dict(ref='R2', lib='Device:R', val='1k5 1206', fp='Resistor_SMD:R_1206_3216Metric', mpn='1,5 kOhm 1 % 1206',
         sch=(99.06, 50.8), pcb=(110.0, 110.0, 90), pins={'1': 'BUS_P', '2': 'BUS_R2_OK1'}),
    dict(ref='D1', lib='Device:LED', val='rouge', fp='LED_SMD:LED_0805_2012Metric', mpn='LED rouge 0805',
         sch=(114.3, 81.28), pcb=(113.0, 110.5, 90), pins={'1': 'BUS_N', '2': 'BUS_OK1_D1'}),
    dict(ref='D2', lib='Device:D', val='1N4148W', fp='Diode_SMD:D_SOD-123', mpn='1N4148W',
         sch=(114.3, 96.52), pcb=(116.5, 113.0, 90), pins={'1': 'CL_N_IN', '2': 'BUS_N'}),
    dict(ref='OK1', lib='Isolator:4N25', val='4N25', fp='Package_DIP:DIP-6_W7.62mm', mpn='Vishay 4N25',
         sch=(144.78, 55.88), pcb=(121.0, 104.5, 0),
         pins={'1': 'BUS_R2_OK1', '2': 'BUS_OK1_D1', '4': 'RX', '5': '+3V3', '6': 'OK1_B'}, nc=['3']),
    # --- Réception côté ESP32
    dict(ref='R4', lib='Device:R', val='330k', fp=R0805, mpn='330 kOhm 1 % 0805',
         sch=(180.34, 45.72), pcb=(131.45, 109.9, 90), pins={'1': 'OK1_B', '2': 'RX'}),
    dict(ref='R5', lib='Device:R', val='4k7', fp=R0805, mpn='4,7 kOhm 1 % 0805',
         sch=(195.58, 66.04), pcb=(134.05, 109.9, 90), pins={'1': 'RX', '2': 'GND'}),
    # --- Émission côté ESP32
    dict(ref='R6', lib='Device:R', val='4k7', fp=R0805, mpn='4,7 kOhm 1 % 0805',
         sch=(228.6, 116.84), pcb=(131.45, 113.5, 90), pins={'1': 'TX', '2': 'Q2_B'}),
    dict(ref='R8', lib='Device:R', val='10k', fp=R0805, mpn='10 kOhm 1 % 0805',
         sch=(213.36, 116.84), pcb=(134.05, 113.5, 90), pins={'1': 'Q2_B', '2': '+3V3'}),
    dict(ref='Q2', lib='Transistor_BJT:BC857', val='BC857C', fp='Package_TO_SOT_SMD:SOT-23', mpn='BC857C',
         sch=(200.66, 137.16), pcb=(132.75, 117.2, 0), pins={'3': 'Q2_C', '1': 'Q2_B', '2': '+3V3'}),
    dict(ref='R3', lib='Device:R', val='300', fp=R0805, mpn='300 Ohm 1 % 0805',
         sch=(180.34, 152.4), pcb=(131.45, 120.8, 90), pins={'1': 'Q2_C', '2': 'OK2_A'}),
    dict(ref='OK2', lib='Isolator:4N25', val='4N25', fp='Package_DIP:DIP-6_W7.62mm', mpn='Vishay 4N25',
         sch=(144.78, 137.16), pcb=(128.62, 129.08, 180),
         pins={'1': 'OK2_A', '2': 'GND', '4': 'BUS_Q1_B', '5': 'BUS_P', '6': 'BUS_OK2_B'}, nc=['3']),
    # --- Émission côté bus
    dict(ref='R1', lib='Device:R', val='330k', fp=R0805, mpn='330 kOhm 1 % 0805',
         sch=(114.3, 124.46), pcb=(117.0, 121.0, 90), pins={'1': 'BUS_Q1_B', '2': 'BUS_OK2_B'}),
    dict(ref='R7', lib='Device:R', val='330k', fp=R0805, mpn='330 kOhm 1 % 0805',
         sch=(99.06, 152.4), pcb=(113.0, 126.0, 90), pins={'1': 'BUS_Q1_B', '2': 'BUS_N'}),
    dict(ref='Q1', lib='Transistor_BJT:BC847', val='BC847C', fp='Package_TO_SOT_SMD:SOT-23', mpn='BC847C',
         sch=(76.2, 137.16), pcb=(113.0, 121.0, 0), pins={'3': 'BUS_P', '1': 'BUS_Q1_B', '2': 'BUS_N'}),
    # --- ESP32-C3 SuperMini (enfiché sur 2 barrettes femelles) [brochage À VÉRIFIER sur le lot]
    dict(ref='J4', lib='Connector_Generic:Conn_01x08', val='SuperMini gauche', fp='Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical',
         mpn='barrette femelle 1x8 2,54 mm', sch=(345.44, 73.66), pcb=(158.5, 108.8, 270),
         pins={'1': '+5V', '2': 'GND', '3': '+3V3'}, nc=['4', '5', '6', '7', '8']),
    dict(ref='J5', lib='Connector_Generic:Conn_01x08', val='SuperMini droite', fp='Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical',
         mpn='barrette femelle 1x8 2,54 mm', sch=(345.44, 111.76), pcb=(158.5, 124.04, 270),
         pins={'1': 'DHT_IO', '2': 'RX', '3': 'TX'}, nc=['4', '5', '6', '7', '8']),
    # --- Entrée DHT22
    dict(ref='J3', lib='Connector:Screw_Terminal_01x03', val='DHT22', fp='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MPT-0,5-3-2.54_1x03_P2.54mm_Horizontal',
         mpn='Phoenix MPT 0,5/3-2,54', sch=(345.44, 152.4), pcb=(136.85, 129.38, 180), ref_at=(140.6, 131.4), pins={'1': '+3V3', '2': 'DHT_DATA', '3': 'GND'}),
    dict(ref='R9', lib='Device:R', val='4k7', fp=R0805, mpn='4,7 kOhm 1 % 0805',
         sch=(271.78, 147.32), pcb=(147.2, 120.6, 0), pins={'1': 'DHT_DATA', '2': '+3V3'}),
    dict(ref='R10', lib='Device:R', val='100', fp=R0805, mpn='100 Ohm 0805',
         sch=(287.02, 147.32), pcb=(150.9, 120.6, 0), pins={'1': 'DHT_DATA', '2': 'DHT_IO'}),
    dict(ref='D5', lib='Device:D_TVS', val='PESD5V0S1BA', fp='Diode_SMD:D_SOD-323', mpn='Nexperia PESD5V0S1BA',
         sch=(279.4, 170.18), pcb=(154.6, 120.6, 0), pins={'1': 'DHT_DATA', '2': 'GND'}),
    dict(ref='C3', lib='Device:C', val='100n', fp=C0805, mpn='100 nF X7R 0805',
         sch=(256.54, 170.18), pcb=(143.5, 120.6, 0), pins={'1': '+3V3', '2': 'GND'}),
    # --- Alimentation 5 V
    dict(ref='J2', lib='Connector:Screw_Terminal_01x02', val='5V ext.', fp='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MPT-0,5-2-2.54_1x02_P2.54mm_Horizontal',
         mpn='Phoenix MPT 0,5/2-2,54', sch=(254.0, 30.48), pcb=(131.7, 103.62, 0), ref_at=(137.6, 103.6), pins={'1': '5V_IN', '2': 'GND'}),
    dict(ref='D4', lib='Device:D_Schottky', val='SS14', fp='Diode_SMD:D_SMA', mpn='SS14',
         sch=(279.4, 27.94), pcb=(154.3, 115.9, 90), pins={'1': '+5V', '2': '5V_IN'}),
    dict(ref='C1', lib='Device:C_Polarized', val='100u 10V', fp='Capacitor_SMD:CP_Elec_6.3x5.4', mpn='100 uF 10 V alu SMD 6,3 mm',
         sch=(299.72, 40.64), pcb=(146.8, 115.4, 0), pins={'1': '+5V', '2': 'GND'}),
    dict(ref='C2', lib='Device:C', val='100n', fp=C0805, mpn='100 nF X7R 0805',
         sch=(314.96, 40.64), pcb=(157.5, 115.9, 90), pins={'1': '+5V', '2': 'GND'}),
]

# Libellés des broches du SuperMini (pour le schéma et la sérigraphie).
SUPERMINI = {
    'J4': ['5V', 'GND', '3V3', 'GPIO4', 'GPIO3', 'GPIO2', 'GPIO1', 'GPIO0'],
    'J5': ['GPIO5', 'GPIO6 RX', 'GPIO7 TX', 'GPIO8 LED', 'GPIO9 BOOT', 'GPIO10', 'GPIO20', 'GPIO21'],
}

TROUS = [(103.2, 103.2), (158.8, 103.2), (103.2, 129.8), (158.8, 129.8)]

# Carte (mm) : origine en haut à gauche.
CARTE = (100.0, 100.0, 162.0, 133.0)
# Bande d'isolation entre côté bus et côté ESP32 (zone interdite au cuivre hors pastilles).
ISOLATION = (123.4, 100.0, 126.4, 133.0)
# Zone sans cuivre sous et devant l'antenne céramique du SuperMini.
ANTENNE = (135.6, 106.0, 139.8, 124.0)

NOTES = [
    ((25.4, 22.86), 'COTE BUS (alimente par le bus, ~6 mA)  |  isolation optique OK1/OK2  |  COTE ESP32 (3,3 V du SuperMini)'),
    ((25.4, 27.94), 'Topologie de l adaptateur officiel V3, ecarts : R8, Q1/Q2 gain C en SOT-23, D3, F1, entree DHT22, entree 5 V (docs/claude/09).'),
    ((25.4, 210.82), 'RX : seuil ~3,7 V, I_F = (V_bus - 3,7)/1500 = 6,2 mA a 13 V ; TX : I_F(OK2) = 6,3 mA, Ib(Q1) ~34 uA -> 14 mA (BC847C).'),
    ((25.4, 215.9), 'R8 maintient Q2 bloque quand GPIO7 est en haute impedance (reset, bootloader) : le bus n est pas tire a 0 au demarrage.'),
    ((25.4, 220.98), 'Brochage du SuperMini et entraxe des rangees (15,24 mm) a verifier sur un exemplaire avant fabrication.'),
]
