import serial
import time
import json
import threading

# Configuration
PORT = "COM9"  # Change to your ESP32 COM port
BAUD_RATE = 115200


def read_from_esp32(ser):
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode("utf-8").strip()
                if line:
                    print(f"\n[RX from ESP32]: {line}")
        except Exception as e:
            print(f"Error reading: {e}")
            break


def main():
    print(f"Connecting to ESP32 on {PORT} at {BAUD_RATE}...")
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for ESP32 to reset upon connection
        print("Connected!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Start a thread to continuously read from the ESP32
    reader_thread = threading.Thread(target=read_from_esp32, args=(ser,), daemon=True)
    reader_thread.start()

    print("\n--- Simulation Started ---")
    print("Press Ctrl+C to exit.")

    try:
        gate_id = 1
        while True:
            # Simulate vision detecting a block
            print("\n[Vision] Detected block! Classifying...")
            time.sleep(1)  # Processing time

            # Decide which gate to send it to
            gate_id = 1 - gate_id  # Toggles between 0 and 1
            print(f"[Vision] Block classified. Sending to Gate {gate_id}.")

            # Construct the payload (this should match what your app sends)
            # You might need to check your CommandParser.cpp to see what it expects.
            # Usually it's something like {"command": "sort", "gate": 0, "lead_time": 1000, "active_time": 2000}
            payload = {"gate_idx": gate_id, "lead_time": 500, "active_time": 1500}

            msg = json.dumps(payload) + "\n"
            print(f"[TX to ESP32]: {msg.strip()}")
            ser.write(msg.encode("utf-8"))
            ser.flush()

            # Wait for the action to complete before sending next
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()
