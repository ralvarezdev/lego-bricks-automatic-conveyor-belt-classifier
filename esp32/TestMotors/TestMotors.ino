/*
 * ESP32 + L298N - Motor B Test Only
 */

// Pin Definitions
const int ENB = 14;  // PWM pin for speed control
const int IN3 = 27;  // Direction pin 1
const int IN4 = 26;  // Direction pin 2

// Speed setting (0 to 255)
// Note: L298N has an internal voltage drop of ~$1.5V$ to $2V$
int motorSpeed = 200; 

void setup() {
  // Set pins as outputs
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Initialize serial communication
  Serial.begin(115200);
  Serial.println("--- Starting Motor B Test ---");
}

void loop() {
  // 1. Forward/Clockwise
  Serial.println("Motor B: Rotating Direction A");
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  analogWrite(ENB, motorSpeed); 
  delay(3000); 

  // 2. Stop
  Serial.println("Motor B: Stopped");
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  delay(1000); 

  // 3. Backward/Counter-clockwise
  Serial.println("Motor B: Rotating Direction B");
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
  analogWrite(ENB, motorSpeed);
  delay(3000);

  // 4. Stop
  Serial.println("Motor B: Stopped");
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  delay(1000);
}