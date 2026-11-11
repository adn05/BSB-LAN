/************************************************************************************/
/* Configuration BSB-LAN pour Atlantic Alféa Extensa Duo A.I. (RVS21, bus BSB)      */
/* sur ESP32-C3 SuperMini + carte d'interface alfea/hardware.                        */
/* Dérivée de BSB_LAN/BSB_LAN_config.h.default (CONFIG_VERSION 43).                 */
/* Copiée dans le répertoire de build par docker/build.sh.                          */
/* Choix et mesures : docs/claude/10_journal_implementation.md.                     */
/* Les secrets (WiFi, MQTT, mots de passe) sont dans alfea_secrets.h, hors dépôt.   */
/************************************************************************************/

#include "alfea_secrets.h"

#define LANG FR

// Les valeurs de ce fichier servent au premier démarrage, puis la NVS fait foi (modifiable via /C).
byte UseEEPROM = 1;

/*
 * Réseau : WiFi du SuperMini (pas d'Ethernet sur le C3), DHCP.
 */
uint8_t network_type = WLAN;
uint16_t HTTPPort = 80;
bool useDHCP = true;
byte ip_addr[4] = {192,168,1,88};
byte gateway_addr[4] = {192,168,1,1};
byte dns_addr[4] = {192,168,1,1};
byte subnet_addr[4] = {255,255,255,0};

char wifi_ssid[32] = ALFEA_WIFI_SSID;
char wifi_pass[64] = ALFEA_WIFI_PASS;
uint8_t bssid[6] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

char mDNS_hostname[32] = "bsb-lan-alfea";

const char ntp_server[20] = "pool.ntp.org";
const char local_timezone[30] = "CET-1CEST,M3.5.0,M10.5.0/3";

/*
 * Sécurité : authentification HTTP obligatoire (elle protège aussi l'OTA, BSB_LAN.ino:1842-1860).
 */
char PASSKEY[64] = "";
byte trusted_ip_addr[4] = {0,0,0,0};
byte trusted_ip_addr2[4] = {0,0,0,0};
char USER_PASS[64] = ALFEA_USER_PASS;
#if !defined(ALFEA_USER_PASS_DEFINI)
#error "ALFEA_USER_PASS doit être défini (utilisateur:mot_de_passe) dans alfea_secrets.h"
#endif

byte mac[6] = { 0x00, 0x80, 0x41, 0x19, 0x69, 0x90 };  // inutilisé en WiFi

/*
 * Bus BSB : adresse LAN 0x42, régulateur 0x00 (RVS21). L'IHM Atlantic est en 0x0A.
 */
uint8_t bus_type = 0;
byte own_address = 0x42;
byte dest_address = 0x00;
bool pps_write = 0;
byte QAA_TYPE = 0x53;

// Carte d'interface alfea/hardware : RX = GPIO6, TX = GPIO7 (docs/claude/09 §3).
byte bus_pins[2] = {6,7};

/*
 * Écriture limitée à la liste blanche (alfea/params/ecriture.txt), et seulement après avoir choisi le mode
 * d'écriture 1 dans /C (mode 0 = lecture seule, valeur remise par /NE).
 */
#define DEFAULT_FLAG FL_SW_CTL_RONLY
#define WRITE_WHITELIST               // garde de set() : seules les lignes de write_whitelist[] (alfea/params/ecriture.txt)

// Pas de carte SD sur le C3 : les broches SD par défaut (18, 19) sont celles de l'USB natif.
uint8_t LogDestination = FLASH;
#define SD_SCK 18
#define SD_MISO 19
#define SD_MOSI 23
#define SD_CS 5

// LED bleue du SuperMini (docs/claude/09 §3).
#define LED_BUILTIN 8

uint8_t logTelegram = LOGTELEGRAM_OFF;

/*
 * Paramètres journalisés et publiés en MQTT : 45 entrées, tableau de 48 (taille inchangée : la
 * modifier déplace la configuration enregistrée et la réinitialise).
 * 2026-11-11 : 8460, 8743, 3110, 3116, 8744, 8774 retirés (sans valeur sur la PAC) ; 701, 1001, 5072 ajoutés.
 * Les 8 dernières (8742 à 1001.3) sont ajoutées à la demande de l'utilisateur (2026-11-10) ; 701.3, 1001.3, 3110 et
 * 3116 n'existent que dans les listes régénérées à cette date (sinon ligne inconnue, ignorée).
 */
unsigned long log_interval = 60;
parameter log_parameters[48] = {
  {8700, -1},    // Température extérieure
  {8740, -1},    // Température ambiante CC1 (chambre)
  {8741, -1},    // Consigne ambiante actuelle CC1
  {8770, -1},    // Température ambiante CC2 (salon)
  {8771, -1},    // Consigne ambiante actuelle CC2
  {8773, -1},    // Température de départ CC2
  {8410, -1},    // Température de retour PAC
  {8411, -1},    // Consigne PAC
  {8412, -1},    // Température de départ PAC
  {8400, -1},    // État compresseur 1
  {8413, -1},    // Modulation compresseur
  {8402, -1},    // Résistance électrique départ 1
  {8403, -1},    // Résistance électrique départ 2
  {8830, -1},    // Température ECS haut (B3)
  {8831, -1},    // Consigne actuelle ECS
  {8821, -1},    // Résistance électrique ECS
  {8000, -1},    // État CC1
  {8001, -1},    // État CC2
  {8003, -1},    // État ECS
  {8006, -1},    // État PAC
  {700, -1},     // Mode CC1
  {1000, -1},    // Mode CC2
  {8820, -1},    // État pompe ECS (remplace 1600, mode ECS, retiré le 2026-11-11)
  {710, -1},     // Consigne confort CC1
  {712, -1},     // Consigne réduit CC1
  {1010, -1},    // Consigne confort CC2
  {1012, -1},    // Consigne réduit CC2
  {1610, -1},    // Consigne nominale ECS
  {3113.1, -1},  // Énergie utilisée chauffage (#831)
  {3113.2, -1},  // Énergie utilisée ECS (#831)
  {3113.4, -1},  // Énergie utilisée totale (#831)
  {8450, -1},    // Heures de fonctionnement compresseur
  {8451, -1},    // Démarrages compresseur
  {6700, -1},    // Erreur
  {6708, -1},    // Message d'erreur PAC
  {20100.1, -1}, // DHT22 : température
  {20100.2, -1}, // DHT22 : humidité
  {8742, -1},    // Température modèle d'ambiance CC1 (chambre)
  {8772, -1},    // Température modèle d'ambiance CC2 (salon)
  {6701, -1},    // Erreur 2
  {701, -1},     // Dérogation temporaire : état CC1 (0 plus froid, 1 neutre, 2 plus chaud)
  {1001, -1},    // Dérogation temporaire : état CC2
  {5072, -1},    // Boost ECS (forçage) : 0 « ... », 1 « Rechargement »
  {701.3, -1},   // Dérogation temporaire : écart de consigne CC1 (#829)
  {1001.3, -1},  // Dérogation temporaire : écart de consigne CC2 (#829)
};

/*
 * MQTT vers le broker Mosquitto de Home Assistant (add-on de HA OS).
 */
char mqtt_broker_addr[65] = ALFEA_MQTT_BROKER;
char MQTTUsername[65] = ALFEA_MQTT_USER;
char MQTTPassword[65] = ALFEA_MQTT_PASS;
char MQTTTopicPrefix[65] = "BSB-LAN";
bool MQTTRefAD = true;                       // republier la discovery si le broker l'a perdue
byte mqtt_mode = 1;                          // texte : requis par les gabarits de la discovery (04 L1)
byte mqtt_unit_set = CF_MQTT_UNIT_HOMEASSISTANT;
char MQTTDeviceID[32] = "bsb-lan-alfea";
// Discovery sur toute la liste réduite (programmes horaires inclus), publication périodique des log_parameters.
byte LoggingMode = CF_LOGMODE_MQTT;

parameter avg_parameters[40] = {};

char replaceDisabled[10] = "None";           // valeur attendue par HA pour un capteur inactif

int8_t One_Wire_Pin = -1;

// DHT22 sur GPIO5 (entrée J3 de la carte).
int8_t DHT_Pins[10] = {5, -1, -1, -1, -1, -1, -1, -1, -1, -1};

byte BME_Sensors = 0;

bool enable_ipwe = false;
parameter ipwe_parameters[40] = {};

#define USE_ADVANCED_PLOT_LOG_FILE
#define DEFAULT_DAYS_TO_PLOT "3"

bool enable_max_cul = false;
byte max_cul_ip_addr[4] = {0,0,0,0};
char max_device_list[20][11] = {};

bool enable_version_check = false;

// OTA activé : protégé par USER_PASS (obligatoire, voir plus haut).
bool enable_ota_update = true;

bool esp32_save_energy = false;
bool webserver = false;

byte debug_mode = 1;  // journal sur l'USB natif (CDC)
byte verbose = 1;
bool show_unknown = false;

#define CONFIG_VERSION 43


// Sécurité : pas de télégrammes bruts (/Y, /YR, /JY contournent la lecture seule),
// pas de pilotage de GPIO par URL (/G).
#define NO_RAW_TELEGRAMS
#define NO_GPIO_URL

// Mot de passe de l'AP de secours « BSB-LAN » (WPA2 : au moins 8 caractères), défini dans alfea_secrets.h.
#define AP_PASSWORD ALFEA_AP_PASSWORD
static_assert(sizeof(AP_PASSWORD) >= 9, "ALFEA_AP_PASSWORD : au moins 8 caractères (WPA2)");

// Discovery MQTT republiée à chaque démarrage, dès que la PAC est identifiée, et à chaque changement du mode
// d'écriture (entités modifiables ou non ; journal J28). Sans cela, BSB-LAN ne la renvoie
// que si le broker a perdu la session persistante, ou sur /M1!0 (journal J27).
#define MQTT_DISCOVERY_ON_BOOT
// Le type d'entité (sensor, select, text...) dépend du mode d'écriture : chaque publication de discovery efface les
// configurations retenues des autres types pour le même unique_id (sinon doublons périmés dans HA, journal J28).
#define MQTT_DISCOVERY_CLEAN_TYPES
// Discovery sans les lignes virtuelles ajoutées par BSB-LAN à la liste réduite : 10195-10199 (codes bruts),
// 20000-20006 (durées internes), 20700-20899 (custom_floats/longs). Publiées à chaque démarrage, elles ne pouvaient
// pas être supprimées dans HA (journal J29). Restent : la liste réduite (10020-10033 compris) et le DHT22 (20100-20199).
// Masquées dans HA à la demande de l'utilisateur (journal J63), mais gardées dans le firmware (pages web, et 6225/6226
// interrogées par BSB-LAN lui-même) : heure et dates séparées 1-3 (la ligne 0 « Date actuelle / Heure actuelle » suffit),
// 6220, 6221 et 6225-6229 (versions, famille, variante). Restent 6222 (heures de fonctionnement) et 6224 (identification).
#define ALFEA_HORS_HA(l) (((l) >= 1 && (l) < 4) || (l) == 6220 || (l) == 6221 || ((l) >= 6225 && (l) < 6230))
// Seules les lignes de alfea/params/selection_ha.txt sont annoncées (alfea_dans_ha(), émise par gen_custom_defs.py --ha) :
// le firmware peut contenir la liste complète du régulateur sans 900 entités dans HA.
#define MQTT_DISCOVERY_SKIP(line) (ALFEA_HORS_HA(line) || ((line) < 10100 && !alfea_dans_ha(line)) || \
                                   ((line) >= 10100 && !((line) >= BSP_DHT22 && (line) < BSP_BME280)))
// Noms courts des entités HA : « <pièce ou fonction> - <description> » au lieu de
// « 00-08 Circuit de chauffe 1 - 712 - <description> » (demande de l'utilisateur, journal J61).
// CC1 = chambre, CC2 = salon (confirmé par l'utilisateur le 2026-11-09). Chaîne vide : description seule.
// L'identifiant unique (unique_id) ne change pas : HA garde les entity_id existants.
#define MQTT_DISCOVERY_SHORT_NAMES
// Compteurs en kWh (3113.1 à 3113.4) annoncés en state_class total_increasing : sans state_class, le tableau Énergie
// de HA les refuse (BSB-LAN n'en met pas aux kWh, mqtt_handler.h). Demande de l'utilisateur, 2026-11-10.
#define MQTT_DISCOVERY_ENERGY_TOTAL
static inline const char *alfea_prefixe(float l) {
  if (l >= 501 && l < 508) return "Prog chambre";
  if (l >= 521 && l < 528) return "Prog salon";
  if (l >= 561 && l < 568) return "Prog ECS";
  if (l >= 10020 && l < 10027) return "Prog caché chambre";
  if (l >= 10027 && l < 10034) return "Prog caché salon";
  if (l >= 700 && l < 1000) return "Chambre";
  if (l >= 1000 && l < 1300) return "Salon";
  if ((l >= 1600 && l < 1700) || (l >= 5000 && l < 5200)) return "ECS";
  if (l >= 3113 && l < 3114) return "Énergie";
  if (l >= 6220 && l < 6230) return "Config";
  if (l >= 6700 && l < 6710) return "Défaut";
  if (l == 8000 || (l >= 8740 && l < 8750)) return "Chambre";
  if (l == 8001 || (l >= 8770 && l < 8780)) return "Salon";
  if (l == 8003 || (l >= 8820 && l < 8840)) return "ECS";
  if (l == 8006 || (l >= 8400 && l < 8470)) return "PAC";
  return "";   // heure (0-3), température extérieure (8700), DHT22 (20100) : la description suffit
}

// Broker Mosquitto local en 1883 : TLS inutile.
#define NO_TLS
// Pas de /QDB : économise la table temporaire de 500 entrées en RAM (/QD reste disponible).
#undef MAX_HEATINGTBL
#define MAX_HEATINGTBL 1
