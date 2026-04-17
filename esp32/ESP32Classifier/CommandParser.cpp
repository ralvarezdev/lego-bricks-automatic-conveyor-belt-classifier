#include "CommandParser.h"
#include <Arduino.h>

Command CommandParser::parse(const String& payload) {
    Command cmd = {false, -1, 0, 0};
    
    JsonDocument doc; 
    DeserializationError error = deserializeJson(doc, payload);

    if (error) {
        Serial.print("{\"debug\":\"JSON Parse Error: ");
        Serial.print(error.c_str());
        Serial.println("\"}");
        return cmd;
    }

    if (!doc["gate_idx"].isNull() && !doc["lead_time"].isNull() && !doc["active_time"].isNull()) {
        cmd.gateIdx = doc["gate_idx"];
        cmd.leadTime = doc["lead_time"];
        cmd.activeTime = doc["active_time"];
        cmd.isValid = true;
    } else {
        Serial.println("{\"debug\":\"JSON missing required keys!\"}");
    }

    return cmd;
}
