/*
 * Pont USB <-> « bus BSB logique » sur un 2e ESP32-C3 SuperMini, pour tester le firmware sans PAC
 * avec le simulateur alfea/tools/bsb_sim.py (docs/claude/README_docker.md §3, docs/claude/08 §6 T1).
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
 * Câblage (3,3 V des deux côtés, aucune résistance ni diode) :
 *     pont GPIO4  <-  cible GPIO7 (TX bus de BSB-LAN)
 *     pont GPIO5  ->  cible GPIO6 (RX bus de BSB-LAN)
 *     pont GND    --  cible GND
 *     pont GPIO3 : sortie TX interne de l'UART, à laisser EN L'AIR.
 * Chaque carte est alimentée par son propre câble USB.
 *
 * Côté PC : port série USB du pont, débit indifférent (USB CDC). Le pont émet et reçoit en 4800 bauds 8O1,
 * octets transmis tels quels (le complément ^0xFF est fait par BSB-LAN et par le simulateur).
 * Le simulateur doit être lancé avec --pont : l'écho est fait ici, pas par le PC.
 * LED (GPIO8, active à l'état bas) : bascule à chaque octet transmis dans un sens ou dans l'autre.
 */
#include "driver/gpio.h"

static const gpio_num_t BROCHE_TX_CIBLE = GPIO_NUM_4;   // entrée : TX de la cible
static const gpio_num_t BROCHE_LIGNE = GPIO_NUM_5;      // sortie : ligne vue par la cible
static const gpio_num_t BROCHE_TX_SIM = GPIO_NUM_3;     // sortie de l'UART1, relue (ne pas câbler)
static const int BROCHE_LED = 8;

static void IRAM_ATTR et_cable(void *) {
  gpio_set_level(BROCHE_LIGNE, gpio_get_level(BROCHE_TX_CIBLE) & gpio_get_level(BROCHE_TX_SIM));
}

void setup() {
  Serial.begin(115200);                                  // USB CDC : débit ignoré
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
  digitalWrite(BROCHE_LED, HIGH);
}

void loop() {
  static bool led = false;
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
