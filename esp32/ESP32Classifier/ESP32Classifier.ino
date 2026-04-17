#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <vector>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include "Constants.h"
#include "SystemState.h"
#include "BaseGate.h"
#include "ServoGate.h"
#include "Conveyor.h"
#include "CommandParser.h"

// Globals
SystemState currentState = SystemState::IDLE;
Conveyor conveyor;
std::vector<BaseGate*> gates;

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Timing variables
uint32_t stateStartTime = 0;
Command currentCmd;

void sendStatus(const char* statusStr, int gateIdx = -1) {
    JsonDocument doc; 
    doc["status"] = statusStr;
    if (gateIdx >= 0) {
        doc["current_gate"] = gateIdx;
    }
    
    if (Config::USE_MQTT) {
        String out;
        serializeJson(doc, out);
        mqttClient.publish(Config::MQTT_TOPIC_STATUS, out.c_str());
        Serial.println(out); // Also print locally for debugging
    } else {
        serializeJson(doc, Serial);
        Serial.println();
    }
}

void processCommand(Command cmd) {
    if (cmd.isValid) {
        Serial.print("{\"debug\":\"Valid Cmd Gate: ");
        Serial.print(cmd.gateIdx);
        Serial.println("\"}");

        if (cmd.gateIdx >= 0 && cmd.gateIdx < (int)gates.size()) {
            if (currentState == SystemState::IDLE) {
                currentCmd = cmd;
                currentState = SystemState::PRE_ACTUATION_WAIT;
                stateStartTime = millis();
                sendStatus("wait", currentCmd.gateIdx);
            } else {
                sendStatus("busy", currentCmd.gateIdx);
            }
        } else {
            sendStatus("error_invalid_gate");
        }
    } else {
        Serial.println("{\"debug\":\"Command is invalid!\"}");
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String msg = "";
    for (int i = 0; i < length; i++) {
        msg += (char)payload[i];
    }
    
    Serial.print("{\"debug\":\"MQTT RX: ");
    Serial.print(msg);
    Serial.println("\"}");

    Command cmd = CommandParser::parse(msg);
    processCommand(cmd);
}

void reconnectMQTT() {
    // Retry connection without completely blocking everything forever
    if (!mqttClient.connected()) {
        Serial.print("Attempting MQTT connection...");
        String clientId = "ESP32ClassifierClient-";
        clientId += String(random(0xffff), HEX);
        
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("connected");
            
            // Subscribing is critical! Verify it works
            bool subSuccess = mqttClient.subscribe(Config::MQTT_TOPIC_CMD);
            if (subSuccess) {
                Serial.println("{\"debug\":\"Successfully subscribed to command topic.\"}");
            } else {
                Serial.println("{\"debug\":\"FAILED to subscribe to command topic!\"}");
            }
            
            sendStatus("mqtt_connected");
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" (retrying shortly)");
        }
    }
}

void setup() {
    Serial.begin(115200);
    
    Serial.println("{\"status\": \"esp32_connected_and_ready\"}");

    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    conveyor.begin();

    gates.push_back(new ServoGate(Config::PIN_GATE_0, Config::GATE_ANGLE_HOME, Config::GATE_ANGLE_DIVERT));
    gates.push_back(new ServoGate(Config::PIN_GATE_1, Config::GATE_ANGLE_HOME, Config::GATE_ANGLE_DIVERT));

    for (auto gate : gates) {
        gate->begin();
    }

    if (Config::USE_MQTT) {
        Serial.print("Connecting to WiFi: ");
        Serial.println(Config::WIFI_SSID);
        WiFi.begin(Config::WIFI_SSID, Config::WIFI_PASS);
        
        while (WiFi.status() != WL_CONNECTED) {
            delay(500);
            Serial.print(".");
        }
        Serial.println("\nWiFi connected! IP address: ");
        Serial.println(WiFi.localIP());

        mqttClient.setServer(Config::MQTT_BROKER, Config::MQTT_PORT);
        mqttClient.setCallback(mqttCallback);
    }

    sendStatus("idle");
}

void processSerial() {
    if (Serial.available() > 0) {
        String payload = Serial.readStringUntil('\n');
        
        Serial.print("{\"debug\":\"Raw RX: ");
        Serial.print(payload);
        Serial.println("\"}");

        Command cmd = CommandParser::parse(payload);
        processCommand(cmd);
    }
}

void updateStateMachine() {
    uint32_t now = millis();

    // Safety Watchdog
    if (currentState != SystemState::IDLE) {
        if (now - stateStartTime > Config::MAX_SAFETY_TIME_MS) {
            currentState = SystemState::SAFETY_STOP;
        }
    }

    switch (currentState) {
        case SystemState::IDLE:
            break;

        case SystemState::PRE_ACTUATION_WAIT:
            if (now - stateStartTime >= currentCmd.leadTime) {
                // Actuation Phase
                Serial.println("{\"debug\":\"Actuating gate and starting conveyor!\"}");
                
                // Start conveyor FIRST, let inrush current settle, then move servo
                conveyor.start();
                delay(100); // 100ms delay to prevent power brownout on the 5V rail
                gates[currentCmd.gateIdx]->divert();
                
                currentState = SystemState::SORTING_ACTIVE;
                stateStartTime = millis(); // Reset timer for active phase
                sendStatus("active", currentCmd.gateIdx);
            }
            break;

        case SystemState::SORTING_ACTIVE:
            if (now - stateStartTime >= currentCmd.activeTime) {
                // Completion Phase
                Serial.println("{\"debug\":\"Homing gate and stopping conveyor!\"}");
                
                // Stop conveyor FIRST, then home servo
                conveyor.stop();
                delay(100); 
                gates[currentCmd.gateIdx]->home();
                
                currentState = SystemState::IDLE;
                sendStatus("idle");
            }
            break;

        case SystemState::SAFETY_STOP:
            conveyor.stop();
            for (auto gate : gates) {
                gate->home();
            }
            currentState = SystemState::IDLE;
            sendStatus("safety_stop_triggered");
            break;
    }
}

uint32_t lastMqttReconnectAttempt = 0;

void loop() {
    if (Config::USE_MQTT) {
        if (!mqttClient.connected()) {
            uint32_t now = millis();
            if (now - lastMqttReconnectAttempt > 5000) {
                lastMqttReconnectAttempt = now;
                reconnectMQTT();
            }
        } else {
            mqttClient.loop();
        }
    } else {
        processSerial();
    }
    
    updateStateMachine();
}
