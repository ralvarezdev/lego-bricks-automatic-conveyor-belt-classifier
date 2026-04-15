import json
from datasets import load_dataset
from collections import Counter
from core.constants import DATA_DIR


def run_check_balance(config_path):
    if not config_path.exists():
        print(f"ERROR: Configuration file not found at {config_path}")
        return

    with open(config_path, "r") as f:
        config = json.load(f)

    project_name = config.get("project_name", "lego_classifier")
    raw_ids = config.get("selected_ids", [])
    selected_ids = [int(x) for x in raw_ids]

    if not selected_ids:
        print("No classes found in the configuration JSON.")
        return

    selected_set = set(selected_ids)

    print(f"Project: {project_name}")
    print(f"Reading configuration from: {config_path.name}")
    print("Scanning dataset distribution (using fast filter)...")

    ds = load_dataset("pvrancx/legobricks", split="train")
    ds = ds.filter(lambda label: label in selected_set, input_columns=["label"])

    counts = Counter(ds["label"])
    print(f"\n--- Image Counts per Class ---")

    total_images = 0
    for class_id in selected_ids:
        name = config.get("classes", {}).get(str(class_id), f"Unknown_{class_id}")
        count = counts.get(class_id, 0)
        total_images += count
        print(f"Piece {name} (ID {class_id}): {count} images")

    print(f"------------------------------")
    print(f"Total dataset size: {total_images} images")
