#include <WiFi.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "LAPTOP-KN9U1S5D 5942";
const char* password = "mewcat14";

// OM2M server details
const char* server_url = "http://192.168.137.1:5089/~/in-cse/in-name/PATIENT_DATA/Vishesh";

// OM2M headers
const char* origin = "admin:admin";  // OM2M AE-ID or Admin
const char* content_type = "application/json;ty=4"; // ty=4 means contentInstance

void setup() {
  Serial.begin(115200);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    // Random values
    int heartRate = random(70, 100);
    int temp = random(36, 39);
    int spo2 = random(95, 100);

    // Make a comma-separated string
    String data = String(heartRate) + "," + String(temp) + "," + String(spo2);

    // JSON payload
    String payload = "{\"m2m:cin\": {\"con\": \"" + data + "\"}}";

    http.begin(server_url);
    http.addHeader("X-M2M-Origin", origin);
    http.addHeader("X-M2M-RI", "12345");
    http.addHeader("Content-Type", content_type);

    int httpResponseCode = http.POST(payload);
    Serial.print("POST Response: ");
    Serial.println(httpResponseCode);
    Serial.println(http.getString());

    http.end();
  }

  delay(10000);  // send every 10 seconds
}