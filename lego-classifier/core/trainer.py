import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import models, transforms
from datasets import load_dataset
from core.constants import DATA_DIR, MODELS_DIR, CHECKPOINTS_DIR
import warnings

warnings.filterwarnings(
    "ignore", message="To copy construct from a tensor", category=UserWarning
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

preprocess = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


class LEGOTransform:
    def __init__(self, label_map):
        self.label_map = label_map

    def __call__(self, examples):
        pixel_values = [preprocess(img.convert("RGB")) for img in examples["image"]]
        labels = [self.label_map[l] for l in examples["label"]]
        return {"image": pixel_values, "label": labels}


def run_training(config_path, batch_size=32, epochs=5, lr=0.0001, workers=0):
    if not config_path.exists():
        print(
            f"ERROR: {config_path} not found. Please save your selection from the GUI first."
        )
        return

    with open(config_path, "r") as f:
        config = json.load(f)

    project_name = config.get("project_name", "lego_classifier")
    selected_ids = [int(x) for x in config.get("selected_ids", [])]
    num_classes = len(selected_ids)

    if num_classes == 0:
        print("ERROR: No classes selected. Add items to tray before training.")
        return

    label_map = {old_id: i for i, old_id in enumerate(selected_ids)}
    model_base_name = f"{project_name}_{num_classes}classes"

    print(f"Starting Training for Project: {project_name}")
    print(f"Number of classes: {num_classes}")

    print("Loading and filtering dataset from cache...")
    ds = load_dataset("pvrancx/legobricks", split="train")
    selected_set = set(selected_ids)

    ds = ds.filter(
        lambda label: label in selected_set,
        input_columns=["label"],
        num_proc=max(1, workers),
    )

    if len(ds) == 0:
        print("ERROR: Dataset is empty after filtering!")
        return

    ds.set_transform(LEGOTransform(label_map))

    print(f"Initializing EfficientNet-B0 on {DEVICE}...")
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    model = model.to(DEVICE)

    optimizer = optim.AdamW(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler("cuda") if DEVICE == "cuda" else None

    dataloader = DataLoader(
        ds, batch_size=batch_size, shuffle=True, num_workers=workers, pin_memory=True
    )

    print(f"Beginning training for {epochs} epochs. Total images: {len(ds)}")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        batches = 0

        for batch in dataloader:
            images = batch["image"].to(DEVICE)
            labels = batch["label"].to(DEVICE)

            optimizer.zero_grad()

            if DEVICE == "cuda":
                with torch.amp.autocast("cuda"):
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

            total_loss += loss.item()
            batches += 1
            if batches % 10 == 0:
                print(
                    f"Epoch {epoch + 1}/{epochs} | Batch {batches}/{len(dataloader)} | Loss: {loss.item():.4f}"
                )

        print(
            f"--- Epoch {epoch + 1} Complete | Average Loss: {total_loss / batches:.4f} ---"
        )
        ckpt_path = CHECKPOINTS_DIR / f"{model_base_name}_epoch_{epoch + 1}.pth"
        torch.save(model.state_dict(), ckpt_path)

    print("\n--- Finalizing and Exporting Assets")
    mapping_path = MODELS_DIR / f"{model_base_name}_mapping.json"
    inverse_map = {
        i: config["classes"].get(str(old_id), f"Unknown {old_id}")
        for old_id, i in label_map.items()
    }

    with open(mapping_path, "w") as f:
        json.dump(inverse_map, f, indent=4)
    print(f"Mapping Exported: {mapping_path.name}")

    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224).to(DEVICE)
    onnx_path = MODELS_DIR / f"{model_base_name}.onnx"

    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )
    print(f"ONNX Model Exported: {onnx_path.name}")
    print("\nTraining Process Finished Successfully!")
