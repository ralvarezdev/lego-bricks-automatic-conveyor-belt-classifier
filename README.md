# LEGO Bricks Automatic Conveyor Belt Classifier

A computer-vision LEGO brick sorter. A Python desktop app (CustomTkinter) watches a conveyor belt through a camera, classifies each brick with an EfficientNet-B0 model exported to ONNX, and tells an ESP32 which servo gate to open so the brick lands in the right bin.

**Note:** This repository is archived and read-only.

## How it works

1. **Catalog** — `core/extractor.py` downloads the Hugging Face dataset `pvrancx/legobricks` and writes `data/catalog.json` (label id to part number) plus preview images.
2. **Studio tab** — choose the brick classes to sort and assign each to a gate (with a lead time and an active time). Projects are saved as JSON in `data/`.
3. **Training** — `core/trainer.py` fine-tunes `torchvision` EfficientNet-B0 (224x224, rotation and colour-jitter augmentation; defaults: batch 32, 5 epochs, learning rate 1e-4) and exports an ONNX model and a class mapping JSON to `models/`. `core/balance.py` checks class balance.
4. **Live sorting** — `infrastructure/vision_onnx.py` runs ONNX Runtime inference on camera frames in a worker. When a prediction passes the confidence threshold and the label has a gate, `core/use_cases/sorting_engine.py` (states `IDLE`, `PROCESSING`, `ERROR`) sends a gate command to the ESP32.
5. **Hardware** — the ESP32 drives a dual-motor conveyor (L298N) and servo gates.

Committed models in `lego-classifier/models/`: `lego_classifier_v3_5classes.onnx`, `lego_classifier_v4_5classes.onnx` and `lego_classifier_v6_6classes.onnx`, each with a `_mapping.json` (v6 covers parts 3001, 56145, 3649, 55981, 3003 and 3648a).

## Repository layout

```
esp32/
  ESP32Classifier/      main firmware (Arduino sketch + C++ classes)
  TestMotors/ TestServos/ TestMotorsAndServos/   test sketches
lego-classifier/        Python desktop app (uv project)
  main.py               entry point
  config/settings.py    pydantic-settings configuration
  core/                 domain, ports, use cases, extractor, trainer, balance, serial manager
  infrastructure/       Arduino serial controller, ONNX vision engine and worker
  gui/                  CustomTkinter UI
  data/ models/         catalog, projects, ONNX models and mappings
  tests/                manual serial and MQTT communication scripts
```

The code follows ports and adapters: `core/ports/interfaces.py` defines the conveyor controller, implemented by `infrastructure/serial_arduino.py`.

## Desktop application

- Python `>=3.12, <3.13`, managed with [uv](https://docs.astral.sh/uv/).
- Main dependencies: `customtkinter`, `datasets`, `matplotlib`, `onnx`, `onnxruntime` / `onnxruntime-gpu`, `opencv-python`, `paho-mqtt`, `pydantic-settings`, `pyserial`, `tensorboard`, `torch`, `torchvision`. PyTorch comes from the CUDA 12.1 wheel index.
- Settings in `config/settings.py`, overridable from `.env`: `CONFIDENCE_THRESHOLD` (0.75), `BAUD_RATE` (115200), `CAMERA_IDX` (0), `MODEL_PATH` (`models/classifier.onnx`).
- Tabs: gate configuration, Studio (catalog, class selection, gate assignment, save/load, balance check, training) and Live (serial connection, camera, model selection).

```bash
cd lego-classifier
uv sync
uv run python main.py
```

On first run the app guides you through extracting the catalog.

## ESP32 firmware

Arduino sketches under `esp32/`. `ESP32Classifier.ino` parses JSON commands (`CommandParser`), drives the conveyor (`Conveyor`) and servo gates (`ServoGate`), and reports status as JSON. It uses `ArduinoJson` and an MQTT client for the optional WiFi mode. Flash it with the Arduino IDE (ESP32 board support and libraries installed), connect over USB and pick the serial port in the Live tab.

`esp32/ESP32Classifier/Constants.h` holds the pin map, PWM settings, gate angles (home and divert), a 10 s safety limit and the mode switch `USE_MQTT` (default `false`, USB serial). It also has WiFi and MQTT broker settings: replace them with your own values and never commit credentials.

## Communication protocol

- Serial at 115200 baud, or MQTT topics `classifier/command` and `classifier/status` when `USE_MQTT` is enabled.
- PC to ESP32: JSON with all three keys required, `gate_idx`, `lead_time`, `active_time`.
- ESP32 to PC: JSON lines such as `{"status": "esp32_connected_and_ready"}` and `{"debug": "..."}`.

`tests/test_serial_comm.py` and `test_mqtt_comm.py` are manual hardware scripts (they open a real serial port or MQTT connection), not automated tests.

## License

No license file is present in this repository.
