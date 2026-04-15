#include "../include/Conveyor.h"

void Conveyor::begin() {
    // Setup Motor A
    pinMode(Config::PIN_MOTOR_ENA, OUTPUT);
    pinMode(Config::PIN_MOTOR_IN1, OUTPUT);
    pinMode(Config::PIN_MOTOR_IN2, OUTPUT);

    // Setup Motor B
    pinMode(Config::PIN_MOTOR_ENB, OUTPUT);
    pinMode(Config::PIN_MOTOR_IN3, OUTPUT);
    pinMode(Config::PIN_MOTOR_IN4, OUTPUT);

    // Setup PWM
    ledcSetup(Config::PWM_CHANNEL_A, Config::PWM_FREQ, Config::PWM_RESOLUTION);
    ledcAttachPin(Config::PIN_MOTOR_ENA, Config::PWM_CHANNEL_A);

    ledcSetup(Config::PWM_CHANNEL_B, Config::PWM_FREQ, Config::PWM_RESOLUTION);
    ledcAttachPin(Config::PIN_MOTOR_ENB, Config::PWM_CHANNEL_B);

    stop();
}

void Conveyor::start() {
    // Motor A forward
    digitalWrite(Config::PIN_MOTOR_IN1, HIGH);
    digitalWrite(Config::PIN_MOTOR_IN2, LOW);
    ledcWrite(Config::PWM_CHANNEL_A, Config::CONVEYOR_SPEED);

    // Motor B forward
    digitalWrite(Config::PIN_MOTOR_IN3, HIGH);
    digitalWrite(Config::PIN_MOTOR_IN4, LOW);
    ledcWrite(Config::PWM_CHANNEL_B, Config::CONVEYOR_SPEED);
}

void Conveyor::stop() {
    digitalWrite(Config::PIN_MOTOR_IN1, LOW);
    digitalWrite(Config::PIN_MOTOR_IN2, LOW);
    ledcWrite(Config::PWM_CHANNEL_A, 0);

    digitalWrite(Config::PIN_MOTOR_IN3, LOW);
    digitalWrite(Config::PIN_MOTOR_IN4, LOW);
    ledcWrite(Config::PWM_CHANNEL_B, 0);
}
