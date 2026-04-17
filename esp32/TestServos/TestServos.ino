#include <Arduino.h>
#include <ESP32Servo.h>

// Create two servo objects
Servo servo1;
Servo servo2;

const int SERVO_PIN_1 = 32;
const int SERVO_PIN_2 = 33;

void setup() {
    Serial.begin(115200);
    
    // Allocate two timers for the two servos
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    
    // Attach both servos with standard SG90 pulse widths
    servo1.setPeriodHertz(50);
    servo1.attach(SERVO_PIN_1, 500, 2500); 

    servo2.setPeriodHertz(50);
    servo2.attach(SERVO_PIN_2, 500, 2500); 
}

void loop() {
    // Move both servos to 150 degrees
    Serial.println("Moving both to 150...");
    servo1.write(150);
    servo2.write(150);
    delay(2000);

    // Move both servos to 90 degrees
    Serial.println("Moving both to 90...");
    servo1.write(90);
    servo2.write(90);
    delay(2000);
}