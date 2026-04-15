#include <Arduino.h>
#include <vector>
#include <ArduinoJson.h>
#include "../include/Constants.h"
#include "../include/SystemState.h"
#include "../include/BaseGate.h"
#include "../include/ServoGate.h"
#include "../include/Conveyor.h"
#include "../include/CommandParser.h"

// Globals
SystemState currentState = SystemState::IDLE;
Conveyor conveyor;
std::vector<BaseGate*> gates;

// Timing variables
uint32_t stateStartTime = 0;
Command currentCmd;

void sendStatus(const char* statusStr, int gateIdx = -1) {
    StaticJsonDocument<128> doc;
    doc["status"] = statusStr;
    if (gateIdx >= 0) {
        doc["current_gate"] = gateIdx;
    }
    serializeJson(doc, Serial);
    Serial.println();
}

void setup() {
    Serial.begin(115200);
    
    // Initialize conveyor
    conveyor.begin();

    // Initialize gates
    gates.push_back(new ServoGate(Config::PIN_GATE_0, Config::GATE_ANGLE_HOME, Config::GATE_ANGLE_DIVERT));
    gates.push_back(new ServoGate(Config::PIN_GATE_1, Config::GATE_ANGLE_HOME, Config::GATE_ANGLE_DIVERT));

    for (auto gate : gates) {
        gate->begin();
    }

    sendStatus("idle");
}

void processSerial() {
    if (Serial.available() > 0) {
        String payload = Serial.readStringUntil('\n');
        Command cmd = CommandParser::parse(payload);
        
        if (cmd.isValid) {
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
        }
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
                gates[currentCmd.gateIdx]->divert();
                conveyor.start();
                
                currentState = SystemState::SORTING_ACTIVE;
                stateStartTime = millis(); // Reset timer for active phase
                sendStatus("active", currentCmd.gateIdx);
            }
            break;

        case SystemState::SORTING_ACTIVE:
            if (now - stateStartTime >= currentCmd.activeTime) {
                // Completion Phase
                gates[currentCmd.gateIdx]->home();
                conveyor.stop();
                
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

void loop() {
    processSerial();
    updateStateMachine();
}
