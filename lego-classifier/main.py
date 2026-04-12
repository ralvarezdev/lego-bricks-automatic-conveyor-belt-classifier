import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import models, transforms
from datasets import load_dataset
from tqdm import tqdm
import warnings

# Suppress the harmless Hugging Face tensor conversion warning
warnings.filterwarnings("ignore", message="To copy construct from a tensor", category=UserWarning)

# Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
assert torch.cuda.is_available(), "CRITICAL ERROR: CUDA is not available!"
BATCH_SIZE = 64
EPOCHS = 10
LEARNING_RATE = 0.001
NUM_CLASSES = 1000

# 1. MOVED TO GLOBAL SCOPE: Augmentation Pipeline
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomRotation(180),
    transforms.ColorJitter(0.3, 0.3, 0.3),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 2. MOVED TO GLOBAL SCOPE: Transform mapping function
def apply_transforms(examples):
    return {
        "image": [preprocess(img.convert("RGB")) for img in examples["image"]],
        "label": examples["label"]
    }

def main():
    print("Loading dataset...")
    # Load dataset locally (no streaming)
    ds = load_dataset("pvrancx/legobricks", split="train")
    
    # 3. Apply the globally defined transformation
    ds.set_transform(apply_transforms)
    
    # Model Setup
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, NUM_CLASSES)
    model = model.to(DEVICE)

    # Optimization
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler('cuda')

    model.train()
    
    # DataLoader with multi-processing enabled
    dataloader = DataLoader(ds, batch_size=BATCH_SIZE, num_workers=4, pin_memory=True)

    for epoch in range(EPOCHS):
        print(f"\n--- Epoch {epoch+1}/{EPOCHS}")
        loop = tqdm(dataloader, desc="Training")
        for batch in loop:
            # Move data to GPU
            images = batch["image"].to(DEVICE)
            labels = batch["label"].to(DEVICE)

            optimizer.zero_grad()

            # Mixed Precision
            with torch.amp.autocast('cuda'):
                outputs = model(images)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            loop.set_postfix(loss=loss.item())

    # Export
    torch.save(model.state_dict(), "lego_model_v1.pth")
    print("Training complete. Model saved.")
    
    print("Exporting to ONNX...")
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224).to(DEVICE)
    torch.onnx.export(model, dummy_input, "classifier.onnx", input_names=['input'], output_names=['output'])
    print("ONNX export complete.")

# This block is absolutely mandatory on Windows when using num_workers > 0
if __name__ == "__main__":
    main()