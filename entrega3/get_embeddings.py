import json
import os
import sys
import torch
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
INPUT_FILE = "data.json"
OUTPUT_FILE = "data_with_vectors.json"
MODEL_NAME = 'NeuML/pubmedbert-base-embeddings'

# High Batch Size = High Speed. 
# 64 is safe for 8GB VRAM. 128 might work but risks OOM (Out of Memory).
BATCH_SIZE = 64 

# --- HELPER: TEXT CLEANING ---
def construct_input_text(doc):
    def clean(t): 
        if t is None: return ""
        if isinstance(t, list): return " ".join([str(x) for x in t])
        return str(t).strip()
    
    brand = clean(doc.get('brand_name'))
    generic = clean(doc.get('generic_name'))
    purpose = clean(doc.get('purpose'))
    indications = clean(doc.get('indications_and_usage'))
    core_text = f"{brand} {generic} {purpose} {indications}"
    
    active = clean(doc.get("active_ingredients"))
    warnings = clean(doc.get("warnings"))
    if len(warnings) > 1000: 
        warnings = warnings[:1000] + "..."
        
    return f"{core_text} . Active: {active} . Warnings: {warnings}"

# --- MAIN LOGIC ---
if __name__ == "__main__":
    # 0. GPU CHECK (Crucial!)
    # 0. Device Configuration
    device = 'cpu'
    if torch.cuda.is_available():
        device = 'cuda'
        print(f"✅ GPU Detected: {torch.cuda.get_device_name(0)}")
    elif torch.backends.mps.is_available():
        device = 'mps'
        print("✅ Apple MPS (Metal Performance Shaders) Detected")
    else:
        print("⚠️ No GPU detected. Using CPU (this will be slower).")



    
    # 1. Check if work is already done
    if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
        print(f"✅ Found existing '{OUTPUT_FILE}'. Skipping.")
        sys.exit(0)

    print(f"🚀 Generating embeddings from '{INPUT_FILE}'...")

    # 2. Load Input Data
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: '{INPUT_FILE}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict): data = [data]

    # 3. Load Model (Force CUDA)
    print(f"   Loading {MODEL_NAME} to {device}...")
    model = SentenceTransformer(MODEL_NAME, device=device)

    # 4. Prepare Text
    print(f"   Pre-processing {len(data)} documents...")
    all_texts = []
    for doc in data:
        text = construct_input_text(doc)
        doc["text_bm25"] = text
        all_texts.append(text)

    # 5. Generate Embeddings (BATCHED)
    print(f"   Computing vectors with Batch Size {BATCH_SIZE}...")
    
    # Pool start is generally overkill for single GPU unless doing massive preprocessing. 
    # Standard batching is the biggest win here.
    embeddings = model.encode(
        all_texts, 
        batch_size=BATCH_SIZE, 
        show_progress_bar=True, 
        convert_to_tensor=False,
        device=device
    )

    # 6. Save
    for i, doc in enumerate(data):
        doc["vector"] = embeddings[i].tolist()

    print(f"💾 Saving to '{OUTPUT_FILE}'...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print("✅ Done.")