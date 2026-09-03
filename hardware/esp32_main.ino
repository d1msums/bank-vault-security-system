/*
  ============================================================
  Smart Vault Access System — ESP32 ONLY
  No RFID — user selection via keypad 1/2/3
  Gas sensor: AO pin with threshold 600
  ============================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <UniversalTelegramBot.h>
#include <ArduinoJson.h>
#include <time.h>
#include <Keypad.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ESP32Servo.h>

// ── WiFi / Telegram ────────────────────────────────────────
const char* ssid     = "FARISHA 4105";
const char* password = "20277Afs";
#define BOT_TOKEN   "8912130376:AAG-teKuQoBxDHgiAe2FpvOMn0VOx5s_hos"
#define CHAT_ID     "5738671708"

// ── Flask server ───────────────────────────────────────────
// UPDATE THIS IP every time your hotspot IP changes
const char* flaskURL = "http://192.168.43.55:5000/log";

// ── NTP ────────────────────────────────────────────────────
const char* ntpServer      = "pool.ntp.org";
const long  gmtOffset      = 28800;
const int   daylightOffset = 0;

WiFiClientSecure secured_client;
UniversalTelegramBot bot(BOT_TOKEN, secured_client);

// ── Pin definitions ────────────────────────────────────────
#define BUZZER_PIN   2
#define PIR_PIN      35
#define MQ2_AO_PIN   34  // AO pin — analog read
#define SERVO_PIN    32
#define GAS_THRESHOLD 600 // trigger alert if analog value above this

// ── Objects ────────────────────────────────────────────────
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo vaultServo;

// ── Keypad 3x4 ────────────────────────────────────────────
const byte ROWS = 4;
const byte COLS = 3;
char keys[ROWS][COLS] = {
  {'1','2','3'},
  {'4','5','6'},
  {'7','8','9'},
  {'*','0','#'}
};
byte rowPins[ROWS] = {13, 12, 14, 27};
byte colPins[COLS] = {26, 25, 33};
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// ── User database ──────────────────────────────────────────
struct User {
  String pin;
  String name;
  String role;
  int allowedStart;
  int allowedEnd;
};

User users[] = {
  {"1234", "Ahmad Staff",  "Staff",   9,  18},
  {"5678", "Siti Manager", "Manager", 0,  23},
  {"9012", "Ali Cleaner",  "Cleaner", 18, 22}
};

// ── State variables ────────────────────────────────────────
int wrongPinCount          = 0;
bool lockedOut             = false;
unsigned long lockoutStart = 0;
const unsigned long LOCKOUT_DURATION = 30000;
int selectedUser           = -1;
bool userSelected          = false;

// ── Sensor cooldowns ───────────────────────────────────────
unsigned long lastMotionAlert       = 0;
const unsigned long MOTION_COOLDOWN = 10000;
unsigned long lastGasAlert          = 0;
const unsigned long GAS_COOLDOWN    = 15000;

// ── Gas warmup ─────────────────────────────────────────────
unsigned long systemStartTime        = 0;
const unsigned long GAS_PREHEAT_TIME = 30000;

// ── Time helpers ───────────────────────────────────────────
String getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return "unknown";
  char buf[32];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &timeinfo);
  return String(buf);
}

int getCurrentHour() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return -1;
  return timeinfo.tm_hour;
}

// ── Telegram ───────────────────────────────────────────────
void sendTelegram(String msg) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, skipping Telegram.");
    return;
  }
  bool sent = bot.sendMessage(CHAT_ID, msg, "");
  Serial.println(sent ? "Telegram sent!" : "Telegram failed.");
}

// ── Flask logging ──────────────────────────────────────────
void sendToFlask(String userName, String role, String risk,
                 bool motion, bool gas, String alert,
                 String timestamp) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, skipping Flask.");
    return;
  }

  Serial.println("--- Sending to Flask ---");
  Serial.println("URL: " + String(flaskURL));

  HTTPClient http;
  http.begin(flaskURL);
  http.addHeader("Content-Type", "application/json");

  String body = "{";
  body += "\"user_name\":\"" + userName + "\",";
  body += "\"role\":\"" + role + "\",";
  body += "\"risk_score\":\"" + risk + "\",";
  body += "\"motion_detected\":" + String(motion ? "1" : "0") + ",";
  body += "\"gas_detected\":" + String(gas ? "1" : "0") + ",";
  body += "\"alert_triggered\":\"" + alert + "\",";
  body += "\"access_time\":\"" + timestamp + "\"";
  body += "}";

  Serial.println("Body: " + body);
  int responseCode = http.POST(body);
  Serial.println("Flask response: " + String(responseCode));

  if (responseCode == 200) {
    Serial.println("Flask log SUCCESS ✓");
  } else {
    Serial.println("Flask FAILED. Code: " + String(responseCode));
  }
  http.end();
}

// ── Buzzer patterns ────────────────────────────────────────
void buzzPattern(String type) {
  if (type == "granted") {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(200);
    digitalWrite(BUZZER_PIN, LOW);
  } else if (type == "denied") {
    for (int i = 0; i < 3; i++) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(150);
      digitalWrite(BUZZER_PIN, LOW);
      delay(150);
    }
  } else if (type == "lockout") {
    digitalWrite(BUZZER_PIN, HIGH);
  } else if (type == "stop") {
    digitalWrite(BUZZER_PIN, LOW);
  }
}

// ── Servo open/close ───────────────────────────────────────
void openDoor() {
  lcd.setCursor(0, 1);
  lcd.print("Door Opening... ");
  vaultServo.write(90);
  delay(5000);
  vaultServo.write(0);
  lcd.setCursor(0, 1);
  lcd.print("Door Closed     ");
  delay(1000);
}

// ── Idle screen ────────────────────────────────────────────
void showIdleScreen() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Press 1/2/3 for");
  lcd.setCursor(0, 1);
  lcd.print("Staff/Mgr/Clean");
}

// ── PIN entry ──────────────────────────────────────────────
String getPIN() {
  String pin = "";
  lcd.setCursor(0, 1);
  lcd.print("PIN:            ");
  lcd.setCursor(5, 1);
  while (pin.length() < 4) {
    char key = keypad.getKey();
    if (key && key != '#' && key != '*') {
      pin += key;
      lcd.print("*");
      Serial.print("*");
    }
  }
  Serial.println();
  return pin;
}

// ── Setup ──────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(PIR_PIN,    INPUT);
  // MQ2 AO pin — no pinMode needed for analogRead
  digitalWrite(BUZZER_PIN, LOW);

  delay(500);
  Wire.begin(21, 22);
  Wire.setClock(100000);

  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.print("System Ready");
  delay(1000);

  vaultServo.attach(SERVO_PIN);
  vaultServo.write(0);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Vault System");
  lcd.setCursor(0, 1);
  lcd.print("Initialising...");

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected!");
  Serial.println("IP: " + WiFi.localIP().toString());

  secured_client.setInsecure();

  configTime(gmtOffset, daylightOffset, ntpServer);
  Serial.print("Syncing time");
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nTime synced!");

  systemStartTime = millis();
  delay(2000);
  showIdleScreen();

  bot.sendMessage(CHAT_ID,
    "🔒 Vault System Online\nESP32 ready.", "");
  Serial.println("System ready.");
}

// ── Main loop ──────────────────────────────────────────────
void loop() {

  bool motionDetected = digitalRead(PIR_PIN);

  // ── Gas sensor — AO analog read with threshold 600 ────
  int gasValue    = analogRead(MQ2_AO_PIN);
  bool gasDetected = (gasValue > GAS_THRESHOLD);
  Serial.println("Gas AO value: " + String(gasValue)); // debug

  String timestamp  = getTimestamp();
  unsigned long now = millis();

  // ── Gas warmup window ─────────────────────────────────
  bool sensorReady = (now - systemStartTime >= GAS_PREHEAT_TIME);
  if (!sensorReady) {
    int remaining = (GAS_PREHEAT_TIME - (now - systemStartTime)) / 1000;
    lcd.setCursor(0, 0);
    lcd.print("Gas sensor      ");
    lcd.setCursor(0, 1);
    lcd.print("warmup: " + String(remaining) + "s   ");
    delay(500);
    return;
  }

  // ── Gas alert ─────────────────────────────────────────
  if (gasDetected && (now - lastGasAlert > GAS_COOLDOWN)) {
    lastGasAlert = now;
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("!! GAS ALERT !!");
    lcd.setCursor(0, 1);
    lcd.print("EVACUATE NOW");
    buzzPattern("lockout");
    Serial.println("GAS DETECTED - Value: " + String(gasValue) + " - HIGH RISK");

    String msg = "🔴 HIGH RISK ALERT\n";
    msg += "━━━━━━━━━━━━━━\n";
    msg += "💨 Event: Gas / Smoke detected\n";
    msg += "📊 Gas level: " + String(gasValue) + "\n";
    msg += "🕐 Time: " + timestamp + "\n";
    msg += "⚠️ Evacuate immediately!";
    sendTelegram(msg);
    sendToFlask("N/A", "N/A", "HIGH",
                motionDetected, true,
                "GAS_DETECTED", timestamp);

    delay(5000);
    buzzPattern("stop");
    showIdleScreen();
    return;
  }

  // ── Handle lockout ────────────────────────────────────
  if (lockedOut) {
    if (now - lockoutStart >= LOCKOUT_DURATION) {
      lockedOut     = false;
      wrongPinCount = 0;
      userSelected  = false;
      selectedUser  = -1;
      buzzPattern("stop");
      showIdleScreen();
      Serial.println("Lockout ended. System reset.");
    }
    return;
  }

  // ── Motion without auth ───────────────────────────────
  if (motionDetected && !userSelected &&
      (now - lastMotionAlert > MOTION_COOLDOWN)) {
    lastMotionAlert = now;
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Motion Detected");
    lcd.setCursor(0, 1);
    lcd.print("Select user now!");
    buzzPattern("denied");
    Serial.println("MOTION WITHOUT AUTH - HIGH RISK");

    String msg = "🔴 HIGH RISK ALERT\n";
    msg += "━━━━━━━━━━━━━━\n";
    msg += "🚶 Event: Motion without authentication\n";
    msg += "🕐 Time: " + timestamp;
    sendTelegram(msg);
    sendToFlask("Unknown", "N/A", "HIGH",
                motionDetected, gasDetected,
                "MOTION_NO_AUTH", timestamp);

    delay(2000);
    showIdleScreen();
    return;
  }

  // ── Step 1: User selection ────────────────────────────
  if (!userSelected) {
    char key = keypad.getKey();
    if (!key) return;

    int userIndex = -1;
    if      (key == '1') userIndex = 0;
    else if (key == '2') userIndex = 1;
    else if (key == '3') userIndex = 2;

    if (userIndex == -1) {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Invalid Key!");
      lcd.setCursor(0, 1);
      lcd.print("Press 1 / 2 / 3");
      buzzPattern("denied");
      Serial.println("Invalid key: " + String(key));
      delay(1500);
      showIdleScreen();
      return;
    }

    selectedUser = userIndex;
    userSelected = true;
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Hi " + users[selectedUser].name.substring(0, 12));
    lcd.setCursor(0, 1);
    lcd.print("Enter PIN:");
    Serial.println("User selected: " + users[selectedUser].name);
    return;
  }

  // ── Step 2: PIN entry ─────────────────────────────────
  if (userSelected && selectedUser != -1) {
    User currentUser  = users[selectedUser];
    String enteredPIN = getPIN();

    if (enteredPIN != currentUser.pin) {
      wrongPinCount++;
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Wrong PIN!");
      lcd.setCursor(0, 1);
      lcd.print("Attempt: " + String(wrongPinCount) + "/3");
      buzzPattern("denied");
      Serial.println("Wrong PIN attempt " + String(wrongPinCount) +
                     " by " + currentUser.name);

      if (wrongPinCount >= 3) {
        lockedOut    = true;
        lockoutStart = now;
        userSelected = false;
        selectedUser = -1;

        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("!! LOCKED !!");
        lcd.setCursor(0, 1);
        lcd.print("Wait 30 seconds");
        buzzPattern("lockout");
        Serial.println("LOCKOUT - HIGH RISK - " + currentUser.name);

        String msg = "🔴 HIGH RISK ALERT\n";
        msg += "━━━━━━━━━━━━━━\n";
        msg += "👤 User: " + currentUser.name + "\n";
        msg += "🏷 Role: " + currentUser.role + "\n";
        msg += "⚠️ Event: 3 wrong PIN attempts\n";
        msg += "🔒 Locked for 30 seconds\n";
        msg += "🕐 Time: " + timestamp;
        sendTelegram(msg);
        sendToFlask(currentUser.name, currentUser.role, "HIGH",
                    motionDetected, gasDetected,
                    "PIN_LOCKOUT", timestamp);

      } else {
        delay(2000);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Hi " + currentUser.name.substring(0, 12));
        lcd.setCursor(0, 1);
        lcd.print("Enter PIN:");
      }
      return;
    }

    // ── PIN correct ───────────────────────────────────
    wrongPinCount = 0;

    int currentHour = getCurrentHour();
    bool authorised = (currentHour >= currentUser.allowedStart &&
                       currentHour <  currentUser.allowedEnd);

    // ── Risk scoring ──────────────────────────────────
    String risk = "LOW";
    if (!authorised) risk = "MEDIUM";
    if (motionDetected && !authorised) risk = "HIGH";

    Serial.println("User: "    + currentUser.name +
                   " | Role: " + currentUser.role +
                   " | Hour: " + String(currentHour) +
                   " | Auth: " + String(authorised) +
                   " | Risk: " + risk);

    String alertMsg = "";

    // ── LOW risk ──────────────────────────────────────
    if (risk == "LOW") {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Access Granted!");
      lcd.setCursor(0, 1);
      lcd.print(currentUser.role + " | LOW");
      buzzPattern("granted");
      sendToFlask(currentUser.name, currentUser.role, "LOW",
                  motionDetected, gasDetected, "", timestamp);
      openDoor();

    // ── MEDIUM risk ───────────────────────────────────
    } else if (risk == "MEDIUM") {
      alertMsg = "UNUSUAL_HOUR";

      String msg = "🟡 MEDIUM RISK ALERT\n";
      msg += "━━━━━━━━━━━━━━\n";
      msg += "👤 User: " + currentUser.name + "\n";
      msg += "🏷 Role: " + currentUser.role + "\n";
      msg += "⚠️ Event: Access outside authorised hours\n";
      msg += "🕐 Time: " + timestamp;
      sendTelegram(msg);
      sendToFlask(currentUser.name, currentUser.role, "MEDIUM",
                  motionDetected, gasDetected, alertMsg, timestamp);

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Unusual Hour");
      lcd.setCursor(0, 1);
      lcd.print("Access Allowed");
      buzzPattern("granted");
      openDoor();

    // ── HIGH risk ─────────────────────────────────────
    } else {
      alertMsg = "HIGH_RISK_ENTRY";

      String msg = "🔴 HIGH RISK ALERT\n";
      msg += "━━━━━━━━━━━━━━\n";
      msg += "👤 User: " + currentUser.name + "\n";
      msg += "🏷 Role: " + currentUser.role + "\n";
      msg += "⚠️ Event: High risk entry attempt\n";
      msg += "🚶 Motion: " + String(motionDetected ? "Yes" : "No") + "\n";
      msg += "🕐 Time: " + timestamp;
      sendTelegram(msg);
      sendToFlask(currentUser.name, currentUser.role, "HIGH",
                  motionDetected, gasDetected, alertMsg, timestamp);

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("!! HIGH RISK !!");
      lcd.setCursor(0, 1);
      lcd.print("ACCESS DENIED");
      buzzPattern("lockout");
      delay(3000);
      buzzPattern("stop");
    }

    // ── Reset ─────────────────────────────────────────
    userSelected = false;
    selectedUser = -1;
    delay(1000);
    showIdleScreen();
  }
}
