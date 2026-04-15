#include "../include/ServoGate.h"

ServoGate::ServoGate(int pin, int homeAngle, int divertAngle)
    : _pin(pin), _homeAngle(homeAngle), _divertAngle(divertAngle) {}

void ServoGate::begin() {
    _servo.setPeriodHertz(50);
    _servo.attach(_pin, 500, 2400);
    home();
}

void ServoGate::divert() {
    _servo.write(_divertAngle);
}

void ServoGate::home() {
    _servo.write(_homeAngle);
}
