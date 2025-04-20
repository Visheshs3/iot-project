#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <WiFi.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "LAPTOP-KN9U1S5D 5942";
const char* password = "mewcat14";

// OM2M server details
const char* server_url = "http://192.168.137.1:5089/~/in-cse/in-name/PATIENT_DATA/Vishesh/sensor2";

// OM2M headers
const char* origin = "admin:admin";  // OM2M AE-ID or Admin
const char* content_type = "application/json;ty=4"; // ty=4 means contentInstance

MAX30105 particleSensor;

int max(long a, long b) {
  return (a > b) ? a : b;
}

// BPM variables - IMPROVED
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute;
int beatAvg;
int finalBPM = 70;

// SpO2 variables
const int BUFFER_SIZE = 75;
float redBuffer[BUFFER_SIZE];
float irBuffer[BUFFER_SIZE];
int bufferIndex = 0;
float spo2 = 98.0;
float filteredSpO2 = 98.0;

// Calibration parameters
const float CALIBRATION_OFFSET = 15.0;
const float CALIBRATION_SLOPE = 0.7;
const float MIN_RATIO = 0.4;
const float MAX_RATIO = 1.2;

// Filtering
float alpha = 0.2;
unsigned long lastReportTime = 0;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");
  while (!Serial);

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 not found. Check wiring.");
    while (1);
  }

  // Sensor configuration
  byte ledBrightness = 60;
  byte sampleAverage = 4;
  byte ledMode = 2;
  int sampleRate = 100;
  int pulseWidth = 411;
  int adcRange = 4096;

  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeGreen(0);

  // Initialize buffers with realistic values
  for (int i = 0; i < BUFFER_SIZE; i++) {
    while (!particleSensor.available()) particleSensor.check();
    redBuffer[i] = particleSensor.getRed();
    irBuffer[i] = particleSensor.getIR();
    particleSensor.nextSample();
    delay(10);
  }
}

void loop() {
  // Get new sample
 
  float redValue = particleSensor.getRed();
  float irValue = particleSensor.getIR();


  //Serial.println(irValue);
  // IMPROVED BPM CALCULATION
  if (checkForBeat(irValue) == true) {
    Serial.println("hello");
    Serial.println("hello");
    long delta = millis() - lastBeat;
    lastBeat = millis();
    
      beatsPerMinute = 60 / (delta / 1000.0);

      if (beatsPerMinute < 255 && beatsPerMinute > 20) {
        Serial.println("mew");
        rates[rateSpot++] = (byte)beatsPerMinute;
        rateSpot %= RATE_SIZE;
        
        // Calculate average
        beatAvg = 0;
        for (byte x = 0; x < RATE_SIZE; x++) {
          beatAvg += rates[x];
        }
        beatAvg /= RATE_SIZE;
      }
    }
  
   // Update circular buffers

  // Smooth BPM only when we have valid readings
  if (beatAvg > 40 && beatAvg < 150) {
    finalBPM = int(0.75 * finalBPM + 0.25 * beatAvg);
  }

  redBuffer[bufferIndex] = redValue;
  irBuffer[bufferIndex] = irValue;
  bufferIndex = (bufferIndex + 1) % BUFFER_SIZE;
  calculateSpO2();
  // Report every 2 seconds
  if (millis() - lastReportTime > 10000) {
    HTTPClient http;
    float payloadbpm;
    float payloadspo2;
    Serial.println(irValue);
    if(irValue < 50000){
      payloadbpm = -1;
      payloadspo2 = -1;
    }
    else{
      payloadbpm =finalBPM;
      payloadspo2 = filteredSpO2;
    }
    String data = String(payloadbpm) + "," + String(payloadspo2);
    Serial.println(data);
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
    lastReportTime = millis();
  }

  delay(20);
}

void calculateSpO2() {
  // Find min and max values in the buffer
  float redMin = redBuffer[0], redMax = redBuffer[0];
  float irMin = irBuffer[0], irMax = irBuffer[0];
  
  for (int i = 1; i < BUFFER_SIZE; i++) {
    if (redBuffer[i] < redMin) redMin = redBuffer[i];
    if (redBuffer[i] > redMax) redMax = redBuffer[i];
    if (irBuffer[i] < irMin) irMin = irBuffer[i];
    if (irBuffer[i] > irMax) irMax = irBuffer[i];
  }

  // Calculate AC and DC components
  float redAC = redMax - redMin;
  float redDC = (redMax + redMin) / 2.0;
  float irAC = irMax - irMin;
  float irDC = (irMax + irMin) / 2.0;

  // Calculate ratio-of-ratios with protection against divide-by-zero
  float ratio = (redAC / max(redDC, 1.0)) / (irAC / max(irDC, 1.0));

  // Apply ratio constraints
  ratio = constrain(ratio, MIN_RATIO, MAX_RATIO);

  // Custom calibration formula
  float calculatedSpO2 = 102.0 - (25.0 * CALIBRATION_SLOPE * ratio) + CALIBRATION_OFFSET;

  // Apply physiological constraints
  calculatedSpO2 = constrain(calculatedSpO2, 70.0, 100.0);

  // Exponential smoothing filter
  filteredSpO2 = alpha * calculatedSpO2 + (1.0 - alpha) * filteredSpO2;
}