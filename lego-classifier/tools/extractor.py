import os
import json
import concurrent.futures
from pathlib import Path
from datasets import load_dataset

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "previews"
METADATA_FILE = DATA_DIR / "catalog.json"

# Asegurar que existan
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

def process_segment(worker_id, start_idx, end_idx, dataset_name, split):
    """Procesa un segmento e informa su propio progreso"""
    # Recargar el dataset (usa el caché local)
    ds = load_dataset(dataset_name, split=split)
    local_catalog = {}
    
    total_to_process = end_idx - start_idx
    log_interval = max(1, total_to_process // 10) # Log cada 10%
    
    print(f"[Worker {worker_id:02d}] Iniciando: {start_idx} -> {end_idx} ({total_to_process} registros)")
    
    found_count = 0
    for i in range(start_idx, end_idx):
        example = ds[i]
        label_id = example["label"]
        img_path = OUTPUT_DIR / f"piece_{label_id}.png"
        
        # Guardar si no existe
        if not img_path.exists():
            try:
                example["image"].save(img_path)
                local_catalog[label_id] = str(img_path)
                found_count += 1
            except Exception:
                continue
        
        # Log de progreso por porcentaje
        current_processed = i - start_idx
        if current_processed % log_interval == 0 and current_processed > 0:
            percent = (current_processed / total_to_process) * 100
            print(f"[Worker {worker_id:02d}] Progreso: {percent:.0f}% | Piezas nuevas encontradas: {found_count}")

    print(f"[Worker {worker_id:02d}] ¡FINALIZADO! Total piezas nuevas: {found_count}")
    return local_catalog

def run_extractor():
    dataset_name = "pvrancx/legobricks"
    split = "train"
    
    print("Mapeando dataset desde el caché local...")
    full_ds = load_dataset(dataset_name, split=split)
    total_records = len(full_ds)
    label_names = full_ds.features["label"].names
    total_classes = len(label_names)
    num_workers = os.cpu_count()

    print(f"Lanzando {num_workers} workers para {total_records} registros.")

    step = total_records // num_workers
    ranges = [(i, i * step, (i + 1) * step if i < num_workers - 1 else total_records) 
              for i in range(num_workers)]

    final_catalog = {}

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Pasamos el worker_id como primer argumento
        futures = [executor.submit(process_segment, r[0], r[1], r[2], dataset_name, split) for r in ranges]
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            final_catalog.update(res)
            print(f">>> Progreso Global: {len(final_catalog)}/{total_classes} clases identificadas.")

    # Guardar metadatos finales
    full_metadata = {
        label_id: {"name": label_names[int(label_id)], "image_path": str(Path(path).name)}
        for label_id, path in final_catalog.items()
    }

    with open(METADATA_FILE, "w") as f:
        json.dump(full_metadata, f, indent=4)

    print(f"\n¡Extracción terminada! {len(full_metadata)} piezas disponibles.")

if __name__ == "__main__":
    run_extractor()