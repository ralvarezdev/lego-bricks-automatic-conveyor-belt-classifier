#pragma once
#include <Arduino.h>

namespace Config {
    // --- Communication Mode ---
    constexpr bool USE_MQTT = false; // Set to false to use USB Serial, true to use WiFi/MQTT

    // --- WiFi & MQTT Settings (Used only if USE_MQTT is true) ---
    constexpr char WIFI_SSID[] = "Jubert Router 100% Real No Fake"; // "YOUR_WIFI_SSID";
    constexpr char WIFI_PASS[] = "qwertyuiop"; // "YOUR_WIFI_PASSWORD";
    constexpr char MQTT_BROKER[] = "192.168.137.1"; // IP address of your MQTT Broker (like your PC)
    constexpr int MQTT_PORT = 1883;

    constexpr char MQTT_TOPIC_CMD[] = "classifier/command";
    constexpr char MQTT_TOPIC_STATUS[] = "classifier/status";

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
    constexpr uint8_t CONVEYOR_SPEED = 255; // 0-255

    // Gates
    constexpr uint8_t PIN_GATE_0 = 32;
    constexpr uint8_t PIN_GATE_1 = 33;

    constexpr int GATE_ANGLE_HOME = 150;
    constexpr int GATE_ANGLE_DIVERT = 90;

    // Safety
    constexpr uint32_t MAX_SAFETY_TIME_MS = 10000; // 10 seconds max active
}
