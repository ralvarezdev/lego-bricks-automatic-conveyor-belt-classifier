import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import models, transforms
from datasets import load_dataset
from tqdm import tqdm
import json
from pathlib import Path
import warnings

# Suppress harmless tensor conversion warnings from Hugging Face
warnings.filterwarnings("ignore", message="To copy construct from a tensor", category=UserWarning)

# Path Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
CHECKPOINT_DIR = MODEL_DIR / "checkpoints"

# Ensure directories exist
MODEL_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(exist_ok=True)

# Hardware Acceleration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Data Augmentation Pipeline
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 1. Define a globally scoped, picklable class for transformations
class LEGOTransform:
    def __init__(self, label_map):
        self.label_map = label_map

    def __call__(self, examples):
        pixel_values = [preprocess(img.convert("RGB")) for img in examples["image"]]
        # Map original labels to our new sequential indices
        labels = [self.label_map[l] for l in examples["label"]]
        return {"image": pixel_values, "label": labels}

def main(args):
    # 2. Resolve Dynamic Configuration Path
    config_filename = args.config
    if not config_filename.endswith(".json"):
        config_filename += ".json"
        
    config_path = DATA_DIR / config_filename

    if not config_path.exists():
        print(f"ERROR: {config_path} not found. Please export your selection from the GUI first.")
        return

    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Retrieve dynamic project name
    project_name = config.get("project_name", "lego_classifier")
    
    # CRITICAL FIX: Cast IDs to integers so the dataset filter works correctly
    raw_ids = config.get("selected_ids", [])
    selected_ids = [int(x) for x in raw_ids]
    num_classes = len(selected_ids)
    
    # Create a mapping: Original Dataset ID (int) -> New Index (0 to N-1)
    label_map = {old_id: i for i, old_id in enumerate(selected_ids)}
    
    model_base_name = f"{project_name}_{num_classes}classes"
    print(f"Starting Training for Project: {project_name}")
    print(f"Reading configuration from: {config_filename}")
    print(f"Number of classes: {num_classes}")

    # 3. Dataset Setup
    print("Loading and filtering dataset from cache...")
    ds = load_dataset("pvrancx/legobricks", split="train")
    
    # Convert list to a set for instant O(1) lookups
    selected_set = set(selected_ids)
        
    # Filter dataset to only include selected pieces
    # input_columns=["label"] prevents Hugging Face from loading 400,000 images into memory!
    ds = ds.filter(
        lambda label: label in selected_set, 
        input_columns=["label"],
        num_proc=args.workers
    )
    
    # Safeguard: Check if filtering emptied the dataset
    if len(ds) == 0:
        print("ERROR: Dataset is empty after filtering! Check if the IDs in your JSON match the dataset labels.")
        return

    # Instantiate the picklable transform class and apply it
    ds.set_transform(LEGOTransform(label_map))

    # 4. Model Architecture (EfficientNet-B0)
    print(f"Initializing EfficientNet-B0 on {DEVICE}...")
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    model = model.to(DEVICE)

    # 5. Training Engine
    optimizer = optim.AdamW(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler('cuda')
    
    dataloader = DataLoader(
        ds, 
        batch_size=args.batch_size, 
        shuffle=True, 
        num_workers=args.workers, 
        pin_memory=True
    )

    # 6. Training Loop
    print(f"Beginning training for {args.epochs} epochs. Total images: {len(ds)}")
    for epoch in range(args.epochs):
        model.train()
        loop = tqdm(dataloader, desc=f"Epoch {epoch+1}/{args.epochs}")
        for batch in loop:
            images = batch["image"].to(DEVICE)
            labels = batch["label"].to(DEVICE)

            optimizer.zero_grad()
            with torch.amp.autocast('cuda'):
                outputs = model(images)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            
            loop.set_postfix(loss=loss.item())

        # Save Checkpoint
        ckpt_path = CHECKPOINT_DIR / f"{model_base_name}_epoch_{epoch+1}.pth"
        torch.save(model.state_dict(), ckpt_path)

    # 7. Export Assets
    print("\n--- Finalizing and Exporting Assets")
    
    # Save the Mapping JSON (Indices -> Human Readable Names)
    mapping_filename = f"{model_base_name}_mapping.json"
    mapping_path = MODEL_DIR / mapping_filename
    
    # Re-cast back to string for JSON dictionary keys
    inverse_map = {i: config["classes"][str(old_id)] for old_id, i in label_map.items()}
    
    with open(mapping_path, "w") as f:
        json.dump(inverse_map, f, indent=4)
    print(f"Mapping Exported: {mapping_path}")

    # Export to ONNX for real-time inference
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224).to(DEVICE)
    onnx_filename = f"{model_base_name}.onnx"
    onnx_path = MODEL_DIR / onnx_filename
    
    torch.onnx.export(
        model, 
        dummy_input, 
        str(onnx_path), 
        input_names=['input'], 
        output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
    )
    print(f"ONNX Model Exported: {onnx_path}")
    print("\nProcess finished successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LEGO Classifier Training Script")
    parser.add_argument("--batch-size", type=int, default=32, help="Images per batch")
    parser.add_argument("--epochs", type=int, default=15, help="Total training cycles")
    parser.add_argument("--lr", type=float, default=0.0001, help="Learning rate")
    parser.add_argument("--workers", type=int, default=4, help="CPU threads for data loading")
    
    # NEW ARGUMENT: Specify which JSON to load
    parser.add_argument("--config", type=str, default="selected_classes.json", help="Name of the JSON configuration file to load (e.g., custom_project.json)")
    
    args = parser.parse_args()
    main(args)