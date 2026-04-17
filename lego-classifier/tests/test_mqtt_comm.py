import time
import json
import paho.mqtt.client as mqtt

# Configuration
MQTT_BROKER = (
    "127.0.0.1"  # Change to your PC's IP address if the ESP32 is on a different device
)
MQTT_PORT = 1883
TOPIC_CMD = "classifier/command"
TOPIC_STATUS = "classifier/status"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT Broker at {MQTT_BROKER}")
        client.subscribe(TOPIC_STATUS)
        print(f"Subscribed to {TOPIC_STATUS} to listen for ESP32 status updates.")
    else:
        print(f"Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        print(f"\n[RX from ESP32 via MQTT]: {payload}")
    except Exception as e:
        print(f"Error decoding message: {e}")


def main():
    print(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}...")

    # Initialize the MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"Could not connect to MQTT Broker: {e}")
        print("Make sure Mosquitto or another MQTT broker is installed and running!")
        return

    # Start the network loop in a background thread to process incoming messages
    client.loop_start()
    time.sleep(1)  # Give it a moment to connect

    print("\n--- MQTT Simulation Started ---")
    print("Press Ctrl+C to exit.")

    try:
        gate_id = 1
        while True:
            # Simulate vision detecting a block
            print("\n[Vision] Detected block! Classifying...")
            time.sleep(1)  # Processing time

            # Decide which gate to send it to
            gate_id = 1 - gate_id  # Toggles between 0 and 1
            print(f"[Vision] Block classified. Sending to Gate {gate_id} via MQTT.")

            # Construct the payload
            payload = {"gate_idx": gate_id, "lead_time": 500, "active_time": 1500}
            msg = json.dumps(payload)

            print(f"[TX to ESP32 via MQTT]: {msg}")
            client.publish(TOPIC_CMD, msg)

            # Wait for the action to complete before sending next
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Disconnected from MQTT Broker.")


if __name__ == "__main__":
    main()
