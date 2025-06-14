#include <Stepper.h>
#include <HX711_ADC.h>
#include <EEPROM.h>

// stepper config
const int STEPS_PER_REV = 2048;
const int IN1 = 9, IN2 = 10, IN3 = 11, IN4 = 12;
Stepper stepper(STEPS_PER_REV, IN1, IN3, IN2, IN4);

// load cell config
const int HX711_DOUT = 5;
const int HX711_SCK = 4;
const float CALIBRATION = 1880.83;

HX711_ADC loadCell(HX711_DOUT, HX711_SCK);

// IR sensor
const int IR_SENSOR_PIN = 2;
const unsigned long DETECTION_INTERVAL = 1000; // ms
unsigned long lastDetectionTime = 0;
bool motionDetected = false;

void setup() {
  Serial.begin(9600);
  
  stepper.setSpeed(14);
  
  loadCell.begin();
  loadCell.start(2000, false);
  loadCell.setCalFactor(CALIBRATION);

  pinMode(IR_SENSOR_PIN, INPUT_PULLUP);
  Serial.println("Taring...");
  loadCell.tareNoDelay();
  
  unsigned long tareStartTime = millis();
  while (!loadCell.getTareStatus()) {
    loadCell.update();
    if (millis() - tareStartTime > 5000) {
      Serial.println("Tare timeout! Check load cell connection");
      break;
    }
    delay(10);
  }
  
  if (loadCell.getTareStatus()) {
    Serial.println("Tare complete");
  }
  
  Serial.println("System ready. Send 'help' for commands");
}

void checkLoadCell() {
  static float lastWeight = 0;
  
  if (loadCell.update()) {
    float currentWeight = loadCell.getData();
    if (abs(currentWeight - lastWeight) >= 1.0) {
      lastWeight = currentWeight;
      Serial.print("WEIGHT:");
      Serial.println(currentWeight, 1);
    }
  }
}

void checkIRSensor() {
  int sensorState = digitalRead(IR_SENSOR_PIN);
  unsigned long currentTime = millis();
  
  if (sensorState == LOW && (currentTime - lastDetectionTime) > DETECTION_INTERVAL) {
    motionDetected = true;
    lastDetectionTime = currentTime;
    Serial.println("MOTION_DETECTED");
  } else {
    motionDetected = false;
  }
}

void dispenseFood(int amount) {
  // 2 steps per 10 grams
  int steps = (amount / 10) * 2;
  long totalSteps = (long)steps * STEPS_PER_REV;
  
  Serial.print("Dispensing ");
  Serial.print(amount);
  Serial.print("g (");
  Serial.print(totalSteps);
  Serial.println(" steps)");
  
  stepper.step(totalSteps);
  delay(500);
}

void loop() {
  checkLoadCell();
  checkIRSensor();

  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "help") {
      Serial.println("Available commands:");
      Serial.println("dispense - Dispense food");
      Serial.println("status   - Check weights");
      Serial.println("tare     - Reset scale");
    }
    else if (command.startsWith("dispense:")) {
      int amount = command.substring(9).toInt();
      dispenseFood(amount);
    }
    else if (command == "status") {
      Serial.print("Weight: ");
      Serial.print(loadCell.getData(), 1);
      Serial.println(" g");
    }
    else if (command == "tare") {
      loadCell.tareNoDelay();
      Serial.println("Taring...");
    }    
  }

  static bool tareComplete = false;

  if (loadCell.getTareStatus() && !tareComplete) {
    Serial.println("Tare complete");
    tareComplete = true;
  }
  
  if (!loadCell.getTareStatus()) tareComplete = false;
}