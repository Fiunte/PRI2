import json
import os
import gc
import requests
import numpy as np
from tqdm import tqdm

# --- IMPORT TENSORFLOW & FIX GPU MEMORY ---
import tensorflow as tf
import tensorflow_hub as hub
import tensorflow_text

# 🛑 CRITICAL FIX: Prevent TF from grabbing all GPU RAM
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(e)

# --- IMPORT PYTORCH LIBRARIES ---
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel

# --- CONFIG ---
DATA_PATH = "data.json"
OUTPUT_PATH = "data_with_vectors.json"
SOLR_BASE_URL = "http://solr:8983/solr/drugstest/update"

# --- HELPER: TEXT CLEANING ---
def construct_input_text(doc):
    def clean(t): return str(t).strip() if t else ""
    
    # Core identity of the drug
    core_text = f"{clean(doc.get('brand_name'))} {clean(doc.get('generic_name'))} {clean(doc.get('purpose'))} {clean(doc.get('indications_and_usage'))}"
    
    # Supplementary info (truncated to prevent massive tokens)
    active = clean(doc.get("active_ingredients"))
    warnings = clean(doc.get("warnings"))
    if len(warnings) > 1000: 
        warnings = warnings[:1000] + "..."
        
    return f"{core_text} . Active: {active} . Warnings: {warnings}"

# --- EMBEDDING FUNCTIONS ---

def get_sbert(texts):
    print("🔵 SBERT (MiniLM)...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
    # MiniLM is small, GTX 1070 can handle batch 512 easily
    return model.encode(texts, batch_size=512, convert_to_numpy=True, show_progress_bar=True).tolist()

def get_bio_clinicalbert(texts):
    print("🟣 Bio_ClinicalBERT...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
    model = AutoModel.from_pretrained("emilyalsentzer/Bio_ClinicalBERT").to(device)
    
    vectors = []
    # GTX 1070 8GB can usually handle 128 batch size for BERT-base in inference mode
    batch_size = 128 
    
    for i in tqdm(range(0, len(texts), batch_size), desc="Inferencing Bio_ClinicalBERT"):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=512).to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        # Mean pooling
        embeddings = outputs.last_hidden_state.mean(dim=1).cpu().tolist()
        vectors.extend(embeddings)
    return vectors

def get_use(texts):
    print("🟠 Universal Sentence Encoder...")
    embed = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
    vectors = []
    batch_size = 512 # USE is efficient
    
    for i in tqdm(range(0, len(texts), batch_size), desc="Inferencing USE"):
        batch = texts[i:i+batch_size]
        batch_vectors = embed(batch).numpy().tolist()
        vectors.extend(batch_vectors)
    return vectors

def get_pubmedbert(texts):
    print("🟣 PubMedBERT (NeuML)...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = SentenceTransformer('NeuML/pubmedbert-base-embeddings', device=device)
    # Base model, safe batch 128
    return model.encode(texts, batch_size=128, convert_to_numpy=True, show_progress_bar=True).tolist()

def get_sapbert_pubmed(texts):
    print("🔴 SapBERT (PubMedBERT version)...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = SentenceTransformer('cambridgeltl/SapBERT-from-PubMedBERT-fulltext', device=device)
    return model.encode(texts, batch_size=128, convert_to_numpy=True, show_progress_bar=True).tolist()

def get_bge_base(texts):
    print("🔵 BGE Base...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = SentenceTransformer('BAAI/bge-base-en-v1.5', device=device)
    return model.encode(texts, batch_size=128, convert_to_numpy=True, show_progress_bar=True).tolist()

def get_biobert_sentence_correct(texts):
    print("🟡 BioBERT-Sentence (PritamDeka - NLI/STS)...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # CORRECTED MODEL ID
    model = SentenceTransformer("pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb", device=device)
    return model.encode(texts, batch_size=128, convert_to_numpy=True, show_progress_bar=True).tolist()


# --- PIPELINE ---
# Removed the non-existent SapBERT Original
JOBS = [
    ("vector_sbert", "SBERT", get_sbert),
    ("vector_bio_clinicalbert", "Bio_ClinicalBERT", get_bio_clinicalbert),
    ("vector_use", "Universal Sentence Encoder", get_use),
    ("vector_pubmedbert", "PubMedBERT (NeuML)", get_pubmedbert),
    ("vector_sapbert_pubmed", "SapBERT (PubMed Version)", get_sapbert_pubmed),
    ("vector_bge", "BGE Base", get_bge_base),
    ("vector_biobert_sent", "BioBERT Sentence (NLI)", get_biobert_sentence_correct),
]

# --- MAIN ---
if __name__ == "__main__":

    # 1. Load Data
    if os.path.exists(OUTPUT_PATH):
        print(f"⚡ Found '{OUTPUT_PATH}'! Loading existing data...")
        with open(OUTPUT_PATH, 'r') as f:
            data = json.load(f)
    else:
        if not os.path.exists(DATA_PATH):
            print(f"❌ Error: {DATA_PATH} not found.")
            exit(1)
        with open(DATA_PATH, 'r') as f:
            data = json.load(f)

    # 2. Prepare Text
    print(f"📄 Loaded {len(data)} documents. Constructing input strings...")
    texts = [construct_input_text(doc) for doc in data]
    
    # Store BM25 text baseline
    for i, doc in enumerate(data):
        doc["text_bm25"] = texts[i]

    # 3. Run Models Sequentially
    print(f"\n🚀 Starting Inference Pipeline ...")
    
    for field_name, friendly_name, func in JOBS:
        
        # Check if vector already exists to skip
        if field_name in data[0]:
            print(f"⏭️  Skipping {friendly_name} (Already exists)")
            continue
            
        try:
            # Generate Vectors (Func handles progress bar)
            vectors = func(texts)
            
            # Assign to documents
            for i, doc in enumerate(data):
                doc[field_name] = vectors[i]
            
            print(f"✅ Finished {friendly_name}")
            
        except Exception as e:
            print(f"❌ Error running {friendly_name}: {e}")

        # 🧹 CLEANUP: Critical for VRAM management
        vectors = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # 4. Save to Disk
    print("\n💾 Saving all vectors to disk...")
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(data, f)
    print(f"✅ Saved to {OUTPUT_PATH}")

    # 5. Index to Solr
    headers = {"Content-Type": "application/json"}
    solr_batch_size = 1000
    print(f"\n🚀 Indexing to Solr (Batch Size: {solr_batch_size})...")

    for i in tqdm(range(0, len(data), solr_batch_size), desc="Indexing to Solr"):
        batch = data[i : i + solr_batch_size]
        try:
            requests.post(SOLR_BASE_URL, json=batch, headers=headers)
        except Exception as e:
            print(f"❌ Failed to index batch {i}: {e}")

    # 6. Final Commit
    print("💾 Sending Hard Commit to Solr...")
    requests.post(SOLR_BASE_URL + "?commit=true")
    print("✅ Indexing Complete.")