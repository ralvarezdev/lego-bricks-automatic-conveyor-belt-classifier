#include "ServoGate.h"

ServoGate::ServoGate(int pin, int homeAngle, int divertAngle)
    : _pin(pin), _homeAngle(homeAngle), _divertAngle(divertAngle) {}

void ServoGate::begin() {
    _servo.setPeriodHertz(50);
    // Write before attach is not standard in old servo library, but we can try it, or attach then immediately write.
    // ESP32Servo attach has 5 arguments: pin, min, max, initial_angle
    _servo.attach(_pin, 500, 2500);
    _servo.write(_homeAngle); // Ensure it immediately goes to home
    home();
}

void ServoGate::divert() {
    _servo.write(_divertAngle);
}

void ServoGate::home() {
    _servo.write(_homeAngle);
}
