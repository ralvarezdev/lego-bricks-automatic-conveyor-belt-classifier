#pragma once
#include <ArduinoJson.h>

struct Command {
    bool isValid;
    int gateIdx;
    uint32_t leadTime;
    uint32_t activeTime;
};

class CommandParser {
public:
    static Command parse(const String& payload);
};
