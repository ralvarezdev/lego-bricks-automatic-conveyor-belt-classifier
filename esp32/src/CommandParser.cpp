#include "../include/CommandParser.h"

Command CommandParser::parse(const String& payload) {
    Command cmd = {false, -1, 0, 0};
    
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, payload);

    if (error) {
        return cmd;
    }

    if (doc.containsKey("gate_idx") && doc.containsKey("lead_time") && doc.containsKey("active_time")) {
        cmd.gateIdx = doc["gate_idx"];
        cmd.leadTime = doc["lead_time"];
        cmd.activeTime = doc["active_time"];
        cmd.isValid = true;
    }

    return cmd;
}
