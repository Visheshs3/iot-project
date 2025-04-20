// MQ135 (Analog)

#include <WiFi.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "LAPTOP-KN9U1S5D 5942";
const char* password = "mewcat14";

// OM2M server details
const char* server_url = "http://192.168.137.1:5089/~/in-cse/in-name/PATIENT_DATA/Vishesh/sensor1";

// OM2M headers
const char* origin = "admin:admin";  // OM2M AE-ID or Admin
const char* content_type = "application/json;ty=4"; // ty=4 means contentInstance

const int buzzer = 19;

const int mq135Pin = 34;  // ADC input

// IR Sensor (Digital)
const int irSensorPin = 25;

// Capacitive Touch (Touch0 = GPIO4)
const int touchPin = T0;  // Touch pin
int touchThreshold = 40;  // Adjust this value based on testing

// 🔴 HARD-CODED: Replace this with your calibrated R0 value
const float R0 =68;   // Example: calculated in clean air
const float RL = 10.0;    // Load resistance in kΩ

float co2avg = 350;

int present = 0;


void setup() {
  Serial.begin(115200);

  // Pin setup
  pinMode(irSensorPin, INPUT);
  pinMode(mq135Pin, INPUT);
  pinMode(buzzer, OUTPUT);
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");
}

float co2ppm() {
  int adcValue = analogRead(mq135Pin);
  float voltage = adcValue * (3.3 / 4095.0);  // ESP32 is 12-bit ADC
  float Rs = ((3.3 - voltage) / voltage) * RL;
  float ratio = Rs / R0;

  // From MQ135 datasheet CO2 curve: log(ppm) = a*log(Rs/R0) + b
  float ppm = pow(10, -2.769 * log10(ratio) + 2.602);
  return ppm;
}

int infrared() {
  int irValue = digitalRead(irSensorPin);
  if (irValue == LOW) {
    return 1;
  } else return 0;
}

int touch() {
  int touchValue = touchRead(touchPin);
  if (touchValue < touchThreshold) {
    return 1;
  } else {
    return 0;
  }
}

int count =0;

int capacitivetouch = 0;
void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    


    float co2 = co2ppm();

    float new_avg = (((float)3)/4)*co2avg + (((float)1)/4)*co2;
    float co2avg = new_avg;
    int irr=infrared();
    if(irr){
      present = 1;
    }
    count++ ;
    int emergency = touch();
    if(emergency){
      count = 10;
      capacitivetouch = 1;
    }

    if(count == 10){
      HTTPClient http;
      if(!capacitivetouch){
        digitalWrite(buzzer, LOW);
      }
      if(capacitivetouch){
        digitalWrite(buzzer,HIGH);
      }
      String data = String(co2avg) + "," + String(present) + "," + String(capacitivetouch);
      count = 0;
      co2avg = 400;
      present = 0;
      capacitivetouch = 0;
      Serial.println(data);
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
  }

  delay(1000);  // send every 1 seconds
}