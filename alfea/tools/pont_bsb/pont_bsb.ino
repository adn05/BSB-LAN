/*
 * Pont USB <-> « bus BSB logique » sur une carte Ai-Thinker NodeMCU ESP-C3-32S-Kit, pour tester le
 * firmware sans PAC avec le simulateur alfea/tools/bsb_sim.py (docs/claude/README_docker.md §3).
 *
 * Pourquoi pas un simple pont série : BSB-LAN relit sa propre trame juste après l'émission, sans attendre
 * (BSB_LAN/src/BSB/bsb.cpp, readByte() non bloquant après serial->flush()). Sur le vrai bus, cet écho
 * est électrique (bus en ET câblé). Un écho renvoyé par le PC arriverait plusieurs ms trop tard et
 * BSB-LAN conclurait à une collision. Le pont reproduit donc le ET câblé :
 *
 *     ligne (vers RX de la cible) = TX de la cible  ET  TX du simulateur
 *
 * recalculé dans une interruption GPIO à chaque front (latence de quelques µs pour 208 µs par bit).
 *
 * Carte : l'USB de l'ESP-C3-32S-Kit passe par un CH340 relié à l'UART0 (GPIO20/21) : « Serial » est cet
 * UART0, à 115 200 bauds 8N1 côté PC. GPIO3/4/5 pilotent la LED RVB et GPIO18/19 les LED blanches
 * [À VÉRIFIER sur la sérigraphie] : on ne s'en sert pas comme lignes de données.
 *
 * Câblage (3,3 V des deux côtés, aucune résistance ni diode) :
 *     pont IO6   <-  cible GPIO7 (TX bus de BSB-LAN, SuperMini)
 *     pont IO7   ->  cible GPIO6 (RX bus de BSB-LAN, SuperMini)
 *     pont GND   --  cible GND
 *     pont IO10 : sortie TX interne de l'UART1, à laisser EN L'AIR.
 * Chaque carte est alimentée par son propre câble USB.
 *
 * Côté PC : 115 200 bauds 8N1 ; le pont émet et reçoit sur le bus logique en 4800 bauds 8O1, octets
 * transmis tels quels (le complément ^0xFF est fait par BSB-LAN et par le simulateur).
 * Le simulateur doit être lancé avec --pont : l'écho est fait ici, et le débit PC est 115 200 bauds.
 * LED verte (IO4) : bascule à chaque paquet transmis dans un sens ou dans l'autre.
 */
#include "driver/gpio.h"

static const gpio_num_t BROCHE_TX_CIBLE = GPIO_NUM_6;   // entrée : TX de la cible
static const gpio_num_t BROCHE_LIGNE = GPIO_NUM_7;      // sortie : ligne vue par la cible
static const gpio_num_t BROCHE_TX_SIM = GPIO_NUM_10;    // sortie de l'UART1, relue (ne pas câbler)
static const int BROCHE_LED = 4;                        // LED verte de la LED RVB, active à l'état haut

#ifdef PONT_DIAG
// Diagnostic (compilation avec -DPONT_DIAG) : une ligne texte par seconde sur la console, au lieu des octets du bus.
static volatile uint32_t fronts = 0;
#endif

static void IRAM_ATTR et_cable(void *) {
#ifdef PONT_DIAG
  fronts = fronts + 1;
#endif
  gpio_set_level(BROCHE_LIGNE, gpio_get_level(BROCHE_TX_CIBLE) & gpio_get_level(BROCHE_TX_SIM));
}

void setup() {
  Serial.begin(115200);                                  // UART0 -> CH340 -> USB du PC
  // UART1 : RX sur le TX de la cible (seuls les octets de la cible remontent au PC), TX sur une broche interne
  Serial1.begin(4800, SERIAL_8O1, BROCHE_TX_CIBLE, BROCHE_TX_SIM);
  gpio_input_enable(BROCHE_TX_SIM);                      // relire la sortie de l'UART
  gpio_pullup_en(BROCHE_TX_CIBLE);                       // cible absente ou éteinte : ligne au repos (1)
  gpio_reset_pin(BROCHE_LIGNE);
  gpio_set_direction(BROCHE_LIGNE, GPIO_MODE_OUTPUT);
  gpio_set_level(BROCHE_LIGNE, 1);
  gpio_install_isr_service(0);
  for (gpio_num_t b : {BROCHE_TX_CIBLE, BROCHE_TX_SIM}) {
    gpio_set_intr_type(b, GPIO_INTR_ANYEDGE);
    gpio_isr_handler_add(b, et_cable, nullptr);
    gpio_intr_enable(b);
  }
  et_cable(nullptr);
  pinMode(BROCHE_LED, OUTPUT);
  digitalWrite(BROCHE_LED, LOW);
}

void loop() {
  static bool led = false;
#ifdef PONT_DIAG
  static uint32_t t = 0, octets = 0;
  while (Serial1.available()) { Serial1.read(); octets++; }
  if (millis() - t >= 1000) {
    t = millis();
    Serial.printf("fronts=%lu octets_uart1=%lu IO6=%d IO7=%d IO10=%d\n",(unsigned long)fronts, (unsigned long)octets,
                  gpio_get_level(BROCHE_TX_CIBLE), gpio_get_level(BROCHE_LIGNE), gpio_get_level(BROCHE_TX_SIM));
  }
  return;
#endif
  uint8_t tampon[64];
  size_t n = Serial1.available();
  if (n) {
    n = Serial1.readBytes(tampon, min(n, sizeof(tampon)));
    Serial.write(tampon, n);
    digitalWrite(BROCHE_LED, led = !led);
  }
  n = Serial.available();
  if (n) {
    n = Serial.readBytes(tampon, min(n, sizeof(tampon)));
    Serial1.write(tampon, n);
    digitalWrite(BROCHE_LED, led = !led);
  }
}
