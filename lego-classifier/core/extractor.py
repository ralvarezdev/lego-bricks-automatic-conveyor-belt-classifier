import os
import json
import concurrent.futures
from datasets import load_dataset
from core.constants import PREVIEWS_DIR, CATALOG_FILE


def process_segment(worker_id, start_idx, end_idx, dataset_name, split):
    ds = load_dataset(dataset_name, split=split)
    local_catalog = {}
    total_to_process = end_idx - start_idx
    log_interval = max(1, total_to_process // 10)

    print(
        f"[Worker {worker_id:02d}] Start: {start_idx} -> {end_idx} ({total_to_process} records)"
    )

    found_count = 0
    for i in range(start_idx, end_idx):
        example = ds[i]
        label_id = example["label"]
        img_path = PREVIEWS_DIR / f"piece_{label_id}.png"

        if not img_path.exists():
            try:
                example["image"].save(img_path)
                local_catalog[label_id] = str(img_path)
                found_count += 1
            except Exception:
                continue

        current_processed = i - start_idx
        if current_processed % log_interval == 0 and current_processed > 0:
            percent = (current_processed / total_to_process) * 100
            print(
                f"[Worker {worker_id:02d}] Progress: {percent:.0f}% | New: {found_count}"
            )

    print(f"[Worker {worker_id:02d}] DONE! Total new: {found_count}")
    return local_catalog


def run_extractor():
    dataset_name = "pvrancx/legobricks"
    split = "train"

    print("Mapping dataset from local cache...")
    full_ds = load_dataset(dataset_name, split=split)
    total_records = len(full_ds)
    label_names = full_ds.features["label"].names
    total_classes = len(label_names)
    num_workers = os.cpu_count() or 4

    print(f"Launching {num_workers} workers for {total_records} records.")
    step = total_records // num_workers
    ranges = [
        (i, i * step, (i + 1) * step if i < num_workers - 1 else total_records)
        for i in range(num_workers)
    ]
    final_catalog = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(process_segment, r[0], r[1], r[2], dataset_name, split)
            for r in ranges
        ]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            final_catalog.update(res)
            print(
                f">>> Global Progress: {len(final_catalog)}/{total_classes} classes identified."
            )

    full_metadata = {
        label_id: {
            "name": label_names[int(label_id)],
            "image_path": f"piece_{label_id}.png",
        }
        for label_id, path in final_catalog.items()
    }

    with open(CATALOG_FILE, "w") as f:
        json.dump(full_metadata, f, indent=4)

    print(f"\nExtraction complete! {len(full_metadata)} pieces available.")
