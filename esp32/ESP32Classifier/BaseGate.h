#pragma once

class BaseGate {
public:
    virtual ~BaseGate() = default;
    
    // Initialize hardware pins and reset gate to home position
    virtual void begin() = 0;
    
    // Actuate the gate to divert an object
    virtual void divert() = 0;
    
    // Return the gate to the rest position
    virtual void home() = 0;
};
