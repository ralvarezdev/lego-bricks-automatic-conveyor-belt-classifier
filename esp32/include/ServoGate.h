#pragma once
#include "BaseGate.h"
#include <ESP32Servo.h>

class ServoGate : public BaseGate {
public:
    ServoGate(int pin, int homeAngle, int divertAngle);
    
    void begin() override;
    void divert() override;
    void home() override;

private:
    int _pin;
    int _homeAngle;
    int _divertAngle;
    Servo _servo;
};
