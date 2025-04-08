// MQ135 (Analog)
const int mq135Pin = 34;  // ADC input

// IR Sensor (Digital)
const int irSensorPin = 25;

// Capacitive Touch (Touch0 = GPIO4)
const int touchPin = T0;  // Touch pin
int touchThreshold = 40;  // Adjust this value based on testing

void setup() {
  Serial.begin(115200);

  // Pin setup
  pinMode(irSensorPin, INPUT);
  pinMode(mq135Pin, INPUT);

  Serial.println("ESP32 - MQ135 + IR Sensor + Touch Sensor Ready");
}

void loop() {
  // MQ135 Reading
  int airQuality = analogRead(mq135Pin);
  Serial.print("Air Quality (ADC): ");
  Serial.print(airQuality);
  if (airQuality < 300) {
    Serial.println(" - Fresh");
  } else if (airQuality < 500) {
    Serial.println(" - Moderate");
  } else {
    Serial.println(" - Poor");
  }

  // IR Sensor Reading
  int irValue = digitalRead(irSensorPin);
  if (irValue == LOW) {
    Serial.println("IR Sensor: 🚧 Object Detected");
  } else {
    Serial.println("IR Sensor: ✅ No Object");
  }

  // Capacitive Touch Reading
  int touchValue = touchRead(touchPin);
  Serial.print("Touch Value: ");
  Serial.println(touchValue);
  if (touchValue < touchThreshold) {
    Serial.println("👆 Touch Detected!");
  }

  Serial.println("-----------------------------");
  delay(1000);  // 1 second delay
}
