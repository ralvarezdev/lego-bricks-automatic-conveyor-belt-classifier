#include <Arduino.h>
#include <ESP32Servo.h>

// --- PIN DEFINITIONS ---
const int ENB = 14; 
const int IN3 = 27; 
const int IN4 = 26; 

const int SERVO_PIN_1 = 32;
const int SERVO_PIN_2 = 33;

// --- CONFIGURATION ---
const int MOTOR_SPEED = 255; // 0-255
const int SERVO_IDLE  = 150; // New Normal State
const int SERVO_OPEN  = 90;  // New Active State

// --- OBJECTS ---
Servo servo1;
Servo servo2;

// --- MOTOR ABSTRACTION ---

void moveForward(int speed) {
  // Logic: IN3 LOW / IN4 HIGH
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
  analogWrite(ENB, speed);
  Serial.println("Motor: [FORWARD]");
}

void moveReverse(int speed) {
  // Logic: IN3 HIGH / IN4 LOW
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  analogWrite(ENB, speed);
  Serial.println("Motor: [REVERSE]");
}

void stopMotor() {
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  analogWrite(ENB, 0);
  Serial.println("Motor: [STOPPED]");
}

void setup() {
    Serial.begin(115200);
    
    pinMode(ENB, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);

    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    
    servo1.setPeriodHertz(50);
    servo1.attach(SERVO_PIN_1, 500, 2500); 

    servo2.setPeriodHertz(50);
    servo2.attach(SERVO_PIN_2, 500, 2500); 

    // Set initial state
    stopMotor();
    servo1.write(SERVO_IDLE);
    servo2.write(SERVO_IDLE);
    
    Serial.println("System Ready. Normal State: 150 degrees.");
}

void loop() {
    // 1. DRIVE
    moveForward(MOTOR_SPEED);
    delay(3000); // Drives for 3 seconds

    // 2. STOP & INSPECT
    stopMotor();
    delay(500); // Short pause to stabilize current

    // Sequential Servo Action
    Serial.println("Servo: Activating 1...");
    servo1.write(SERVO_OPEN);
    delay(1500);
    servo1.write(SERVO_IDLE);
    delay(1000); // One finishes before the next starts

    Serial.println("Servo: Activating 2...");
    servo2.write(SERVO_OPEN);
    delay(1500);
    servo2.write(SERVO_IDLE);
    delay(1000);

    // 3. REPEAT
    Serial.println("Cycle Finished. Resuming Forward motion...");
    Serial.println("----------------------------------------");
}