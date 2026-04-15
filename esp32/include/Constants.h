#pragma once
#include <Arduino.h>

namespace Config {
    // Conveyor Dual-Motor (L298N)
    constexpr uint8_t PIN_MOTOR_ENA = 14;
    constexpr uint8_t PIN_MOTOR_IN1 = 27;
    constexpr uint8_t PIN_MOTOR_IN2 = 26;

    constexpr uint8_t PIN_MOTOR_ENB = 12;
    constexpr uint8_t PIN_MOTOR_IN3 = 25;
    constexpr uint8_t PIN_MOTOR_IN4 = 13;

    constexpr uint8_t PWM_CHANNEL_A = 0;
    constexpr uint8_t PWM_CHANNEL_B = 1;
    constexpr double PWM_FREQ = 5000.0;
    constexpr uint8_t PWM_RESOLUTION = 8;
    constexpr uint8_t CONVEYOR_SPEED = 200; // 0-255

    // Gates
    constexpr uint8_t PIN_GATE_0 = 32;
    constexpr uint8_t PIN_GATE_1 = 33;
    
    constexpr int GATE_ANGLE_HOME = 0;
    constexpr int GATE_ANGLE_DIVERT = 90;

    // Safety
    constexpr uint32_t MAX_SAFETY_TIME_MS = 10000; // 10 seconds max active
}
