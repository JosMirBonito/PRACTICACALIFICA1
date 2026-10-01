// ESP32 en Wokwi: recibe ON / OFF / STATUS por MQTT y responde el estado
#include <WiFi.h>
#include <PubSubClient.h>

const char* BROKER = "broker.hivemq.com";
const char* T_CMD  = "trez/jmiranda/foco/cmd";
const char* T_EST  = "trez/jmiranda/foco/estado";
const int LED = 26;
bool encendido = false;

WiFiClient net;
PubSubClient mqtt(net);

void publicarEstado() {
  mqtt.publish(T_EST, encendido ? "ON" : "OFF");
  Serial.println(encendido ? "Estado: ON" : "Estado: OFF");
}

void callback(char* topic, byte* payload, unsigned int len) {
  String cmd;
  for (unsigned int i = 0; i < len; i++) cmd += (char)payload[i];
  cmd.trim();
  Serial.println("Instruccion recibida: " + cmd);
  if (cmd == "ON")       { encendido = true;  digitalWrite(LED, HIGH); }
  else if (cmd == "OFF") { encendido = false; digitalWrite(LED, LOW);  }
  publicarEstado();   // ON, OFF y STATUS siempre responden el estado
}

void reconectar() {
  while (!mqtt.connected()) {
    String id = "esp32-foco-" + String(random(9999));
    if (mqtt.connect(id.c_str())) { mqtt.subscribe(T_CMD); Serial.println("MQTT conectado"); }
    else delay(2000);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED, OUTPUT);
  WiFi.begin("Wokwi-GUEST", "", 6);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.println("\nWiFi conectado");
  mqtt.setServer(BROKER, 1883);
  mqtt.setCallback(callback);
}

void loop() {
  if (!mqtt.connected()) reconectar();
  mqtt.loop();
}
