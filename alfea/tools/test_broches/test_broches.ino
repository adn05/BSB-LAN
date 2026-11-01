/*
 * Test des broches de l'ESP32-C3 SuperMini, sans instrument (docs/claude/README_docker.md §3).
 * Console USB du module : alfea/tools/flasher.py console. Compilation : sh docker/compiler.sh test-broches.
 *
 * 1. Rappels : chaque GPIO en entrée, rappel interne vers le haut (~45 kOhm) puis vers le bas. Une broche libre
 *    suit le rappel. « tenue à 0 » / « tenue à 1 » : la broche est reliée à GND / 3V3 ou pilotée par un circuit
 *    externe (la sortie IO7 du pont, par exemple). Un rappel externe du même ordre (entrée du pont) peut donner
 *    un niveau indéterminé.
 * 2. Courts-circuits : chaque broche libre est pilotée à 0 puis à 1 ; les autres broches libres, en entrée avec
 *    le rappel opposé, ne doivent pas suivre. Les broches tenues ne sont jamais pilotées (pas de conflit de sorties).
 * 3. Boucle : après un pilotage bref de contrôle (50 µs ; la broche doit suivre, sinon elle est forcée de
 *    l'extérieur et la bascule est refusée), la broche choisie (GPIO7 = TX bus par défaut) bascule toutes les 500 ms et la broche de retour
 *    (GPIO6 = RX bus) est relue. Avec le pont (IO6 <- GPIO7, IO7 -> GPIO6), GPIO6 doit recopier GPIO7.
 *
 * Commandes (puis Entrée) : « 7 » fait basculer GPIO7 (n'importe quel numéro de la liste, mesurable au
 * multimètre si l'on ralentit avec « l »), « l » bascule lente (2 s), « r » rapide (500 ms), « t » refait les
 * tests 1 et 2, « v » veille (signale tout changement de niveau des broches libres), « s » arrête bascule et veille.
 *
 * Le même programme tourne sur le pont (cible test-broches-pont, console du CH340) : une carte en veille, l'autre
 * qui fait basculer une broche, montre où aboutit chaque fil.
 *
 * Broches exclues : 11 à 17 (flash interne), 18 et 19 (USB de la console).
 * Particularités du SuperMini [À VÉRIFIER] : GPIO8 porte la LED bleue (vers 3V3), GPIO9 le bouton BOOT
 * (rappel externe vers 3V3), GPIO2, 8 et 9 sont des broches de démarrage.
 */

#if ARDUINO_USB_CDC_ON_BOOT
static const uint8_t BROCHES[] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 21};
#else   // carte à pont USB-UART (NodeMCU ESP-C3-32S-Kit, CH340) : la console occupe GPIO20/21 (UART0)
static const uint8_t BROCHES[] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
#endif
static const size_t N = sizeof(BROCHES);
static bool tenue[N];

static int index_de(int b) {
  for (size_t i = 0; i < N; i++)
    if (BROCHES[i] == b) return i;
  return -1;
}

static int lire(uint8_t b, uint8_t mode) {
  pinMode(b, mode);
  delay(2);
  return digitalRead(b);
}

static void test_rappels() {
  Serial.println("\n== 1. Rappels internes ==");
  for (size_t i = 0; i < N; i++) {
    uint8_t b = BROCHES[i];
    int h = lire(b, INPUT_PULLUP), l = lire(b, INPUT_PULLDOWN);
    pinMode(b, INPUT);
    const char *etat = (h == 1 && l == 0) ? "libre" : (h == 0 && l == 0) ? "tenue à 0" : (h == 1 && l == 1) ? "tenue à 1" : "incohérente";
    tenue[i] = !(h == 1 && l == 0);
    Serial.printf("GPIO%-2u  rappel haut -> %d  rappel bas -> %d  : %s\n", b, h, l, etat);
  }
}

static void test_courts_circuits() {
  Serial.println("\n== 2. Courts-circuits entre broches libres ==");
  int defauts = 0;
  for (size_t i = 0; i < N; i++) {
    if (tenue[i]) continue;
    for (int niveau = 0; niveau <= 1; niveau++) {
      for (size_t j = 0; j < N; j++)
        if (j != i && !tenue[j]) pinMode(BROCHES[j], niveau ? INPUT_PULLDOWN : INPUT_PULLUP);
      pinMode(BROCHES[i], OUTPUT);
      digitalWrite(BROCHES[i], niveau);
      delay(2);
      for (size_t j = 0; j < N; j++)
        if (j != i && !tenue[j] && digitalRead(BROCHES[j]) == niveau) {
          Serial.printf("GPIO%u à %d entraîne GPIO%u\n", BROCHES[i], niveau, BROCHES[j]);
          defauts++;
        }
      pinMode(BROCHES[i], INPUT);
    }
  }
  for (size_t j = 0; j < N; j++) pinMode(BROCHES[j], INPUT);
  Serial.printf("%d court(s)-circuit(s) détecté(s) (les broches tenues ne sont pas testées)\n", defauts);
}

// Pilotage bref (50 µs) à 1 puis à 0, avec relecture du plot (OUTPUT inclut l'entrée sur ESP32) : une broche
// qui ne suit pas est forcée par l'extérieur (court-circuit ou sortie externe), on ne la fait pas basculer.
static bool pilotable(uint8_t b) {
  pinMode(b, OUTPUT);
  digitalWrite(b, 1);
  delayMicroseconds(50);
  int r1 = digitalRead(b);
  digitalWrite(b, 0);
  delayMicroseconds(50);
  int r0 = digitalRead(b);
  pinMode(b, INPUT);
  if (r1 != 1 || r0 != 0)
    Serial.printf("GPIO%u pilotée à 1 relue %d, à 0 relue %d : forcée par l'extérieur, bascule refusée\n", b, r1, r0);
  return r1 == 1 && r0 == 0;
}

static int bascule = ARDUINO_USB_CDC_ON_BOOT ? 7 : -1, retour = 6;   // sur le pont : rien ne bascule au démarrage
static uint32_t periode = 500;
static bool veille = false;

// Veille : toutes les broches libres en entrée avec rappel haut ; tout changement de niveau est signalé.
// Avec la même commande sur l'autre carte (une broche qui bascule), on retrouve où aboutit chaque fil.
static void surveiller() {
  static int avant[N];
  static bool pret = false;
  if (!pret) {
    for (size_t i = 0; i < N; i++)
      if (!tenue[i]) pinMode(BROCHES[i], INPUT_PULLUP);
    delay(2);
    for (size_t i = 0; i < N; i++) avant[i] = digitalRead(BROCHES[i]);
    pret = true;
  }
  if (!veille) { pret = false; return; }
  for (size_t i = 0; i < N; i++) {
    if (tenue[i]) continue;
    int v = digitalRead(BROCHES[i]);
    if (v != avant[i]) Serial.printf("veille : GPIO%u passe à %d\n", BROCHES[i], v);
    avant[i] = v;
  }
}

static void tests() {
  test_rappels();
  test_courts_circuits();
  if (bascule >= 0) {
    Serial.println();
    if (!pilotable(bascule))
      bascule = -1;
    else
      Serial.printf("\n== 3. Bascule de GPIO%d, relecture de GPIO%d (« s » pour arrêter) ==\n", bascule, retour);
  }
}

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) delay(10);   // laisser la console USB se connecter
  delay(500);
  Serial.println("\nTest des broches ESP32-C3 SuperMini");
  tests();
}

void loop() {
  static uint32_t t = 0;
  static int niveau = 0, ok = 0, ko = 0;
  static String cmd;
  while (Serial.available()) {
    char c = Serial.read();
    if (c != '\n' && c != '\r') { cmd += c; continue; }
    cmd.trim();
    if (cmd == "t") tests();
    else if (cmd == "s") { if (bascule >= 0) pinMode(bascule, INPUT); bascule = -1; veille = false; Serial.println("bascule et veille arrêtées"); }
    else if (cmd == "v") {
      if (bascule >= 0) pinMode(bascule, INPUT);
      bascule = -1; veille = true;
      Serial.println("veille : toutes les broches libres en entrée, rappel haut (« s » pour arrêter)");
    }
    else if (cmd == "l") periode = 2000;
    else if (cmd == "r") periode = 500;
    else if (cmd.length()) {
      int b = cmd.toInt(), i = index_de(b);
      if (i < 0 || (b == 0 && cmd != "0")) Serial.println("commande inconnue : numéro de GPIO de la liste, t, s, l ou r");
      else if (pilotable(b)) {
        if (bascule >= 0) pinMode(bascule, INPUT);
        veille = false;
        bascule = b; ok = ko = 0;
        Serial.printf("bascule de GPIO%d\n", b);
      }
    }
    cmd = "";
  }
  surveiller();
  if (bascule < 0 || millis() - t < periode) return;
  t = millis();
  niveau = !niveau;
  pinMode(bascule, OUTPUT);
  digitalWrite(bascule, niveau);
  if (bascule == 7) {          // boucle par le pont
    pinMode(retour, INPUT);
    delay(1);
    int r = digitalRead(retour);
    (r == niveau ? ok : ko)++;
    Serial.printf("GPIO7=%d  GPIO6=%d  %s  (%d bons, %d faux)\n", niveau, r, r == niveau ? "OK" : "FAUX", ok, ko);
  } else {
    Serial.printf("GPIO%d=%d\n", bascule, niveau);
  }
}
