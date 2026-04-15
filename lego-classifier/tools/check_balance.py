import argparse
import json
from pathlib import Path
from collections import Counter
from datasets import load_dataset

# Path Configuration
BASE_DIR = Path(__file__).resolve().parent.parent if Path(__file__).parent.name == "tools" else Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def main(args):
    # 1. Resolve Dynamic Configuration Path
    config_filename = args.config
    if not config_filename.endswith(".json"):
        config_filename += ".json"
        
    config_path = DATA_DIR / config_filename

    if not config_path.exists():
        print(f"ERROR: Configuration file not found at {config_path}")
        return

    # 2. Load Configuration
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
    print(f"Reading configuration from: {config_filename}")
    print("Scanning dataset distribution (using fast filter)...")
    
    # 3. Load and Filter Dataset
    ds = load_dataset("pvrancx/legobricks", split="train")
    
    # Fast filtering by only loading the label column
    ds = ds.filter(lambda label: label in selected_set, input_columns=["label"])

    # 4. Count and Display Distribution
    counts = Counter(ds["label"])
    print(f"\n--- Image Counts per Class ---")
    
    total_images = 0
    for class_id in selected_ids:
        name = config["classes"].get(str(class_id), f"Unknown_{class_id}")
        count = counts.get(class_id, 0)
        total_images += count
        print(f"Piece {name} (ID {class_id}): {count} images")
        
    print(f"------------------------------")
    print(f"Total dataset size: {total_images} images")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check dataset balance for a specific LEGO configuration")
    
    # Added the --config argument (made it required so you don't accidentally check the wrong file)
    parser.add_argument("--config", type=str, required=True, help="Name of the JSON configuration file (e.g., custom_project)")
    
    args = parser.parse_args()
    main(args)