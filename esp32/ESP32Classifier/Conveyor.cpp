#include "Conveyor.h"

void Conveyor::begin() {
    // Setup Motor A
    pinMode(Config::PIN_MOTOR_ENA, OUTPUT);
    pinMode(Config::PIN_MOTOR_IN1, OUTPUT);
    pinMode(Config::PIN_MOTOR_IN2, OUTPUT);

    // Setup Motor B
    pinMode(Config::PIN_MOTOR_ENB, OUTPUT);
    pinMode(Config::PIN_MOTOR_IN3, OUTPUT);
    pinMode(Config::PIN_MOTOR_IN4, OUTPUT);

    stop();
}

void Conveyor::start() {
    // Motor A forward (IN1=LOW, IN2=HIGH for forward based on TestMotorsAndServos)
    digitalWrite(Config::PIN_MOTOR_IN1, LOW);
    digitalWrite(Config::PIN_MOTOR_IN2, HIGH);
    analogWrite(Config::PIN_MOTOR_ENA, Config::CONVEYOR_SPEED);

    // Motor B forward (Assuming similar change needed if B is ever used)
    digitalWrite(Config::PIN_MOTOR_IN3, LOW);
    digitalWrite(Config::PIN_MOTOR_IN4, HIGH);
    analogWrite(Config::PIN_MOTOR_ENB, Config::CONVEYOR_SPEED);
}

void Conveyor::stop() {
    digitalWrite(Config::PIN_MOTOR_IN1, LOW);
    digitalWrite(Config::PIN_MOTOR_IN2, LOW);
    analogWrite(Config::PIN_MOTOR_ENA, 0);

    digitalWrite(Config::PIN_MOTOR_IN3, LOW);
    digitalWrite(Config::PIN_MOTOR_IN4, LOW);
    analogWrite(Config::PIN_MOTOR_ENB, 0);
}
