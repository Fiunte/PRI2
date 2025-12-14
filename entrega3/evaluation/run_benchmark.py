import os
import json
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import requests
import torch
import concurrent.futures
from sklearn.metrics import precision_recall_curve, auc
from tqdm import tqdm
import pandas as pd
import gc 

# --- IMPORTS ---
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import tensorflow_hub as hub
import tensorflow as tf

# 🛑 CRITICAL FIX: Prevent TF from grabbing all GPU RAM
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(e)


# --- CONFIG ---
SOLR_URL = "http://solr:8983/solr"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
COLLECTION = "drugstest"
MODEL_NAME = "deepseek-r1"
TOP_K = 20
P_AT_K_LIST = [5, 10, 20]  # Evaluate P@5, P@10, P@20
CHUNK_SIZE = 5  # Number of documents to evaluate per DeepSeek call
MAX_LLM_RETRIES = 3 # Number of times to retry if JSON parsing fails
# os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
# Device
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🚀 Running on {DEVICE.upper()}")

# --- OLLAMA ---
def ensure_ollama_model():
    print(f"🦙 Checking Ollama for model '{MODEL_NAME}'...")
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags")
        models = [m['name'] for m in r.json().get('models', [])]
        if f"{MODEL_NAME}:latest" not in models and MODEL_NAME not in models:
            print(f"⬇️ Pulling '{MODEL_NAME}'...")
            requests.post(f"{OLLAMA_URL}/api/pull", json={"name": MODEL_NAME})
        print(f"✅ Model Ready.")
    except Exception as e:
        print(f"❌ Ollama Error: {e}")
        exit(1)

def query_ollama(prompt, context_name="Query", json_mode=True):
    payload = { 
        "model": MODEL_NAME, 
        "prompt": prompt, 
        "stream": False, 
        "format": "json" if json_mode else "",
    }
    
    # --- DEBUG PROMPTS RE-ADDED ---
    print(f"\n--- [DEBUG] Sending to {context_name} ---")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("------------------------------------------")
    # --- END DEBUG PROMPTS ---

    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
        resp = r.json().get('response', "")
        clean_resp = re.sub(r'<think>.*?</think>', '', resp, flags=re.DOTALL).strip()
        
        # --- DEBUG RESPONSE RE-ADDED ---
        print(f"[DEBUG] {context_name} Response (Cleaned): {clean_resp}")
        # --- END DEBUG RESPONSE ---
        
        return clean_resp
    except:
        return "{}"

# --- JSON EXTRACTION HELPER ---
def extract_json_from_text(text):
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except: pass
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except: pass
    try: return json.loads(text)
    except: return None

ensure_ollama_model()

# --- QUERY GENERATION ---
def generate_queries():
    all_queries = []
    personas = {
        "Basic": {"prompt": "Generate short queries (1 word, sometimes 2-3) for common drugs ailments.", "num": 10},
        "Complex": {"prompt": "Generate queries (1-3 words) for chronic medical conditions.", "num": 5},
        "Safety": {"prompt": "Generate queries (1-5 words) asking for safe drugsm, examples are pregnancy, addiction, liver failure, natural drugs, etc..", "num": 5}
    }
    print(f"🧠 Generating {sum(p['num'] for p in personas.values())} Queries...")
    def fetch(persona_name, instr, n):
        # FIX: Explicitly request 'n' queries in the prompt
        prompt = f"Act as a search user. {instr} Generate {n} queries. Return ONLY a JSON array of strings."
        
        # Simple retry logic for query generation too
        for attempt in range(MAX_LLM_RETRIES):
            resp = query_ollama(prompt, f"Gen-{persona_name}")
            data = extract_json_from_text(resp)
            if data:
                break
            print(f"⚠️ Query gen failed attempt {attempt+1}, retrying...")

        queries = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, list):
                    queries.extend(item)
                elif isinstance(item, str):
                    queries.append(item)
        elif isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    queries.extend(v)
        return queries[:n]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(fetch, name, info["prompt"], info["num"]) for name, info in personas.items()]
        for f in concurrent.futures.as_completed(futures):
            all_queries.extend(f.result())
    if not all_queries:
        return ["flu remedy", "hypertension medication", "pain killer safe for liver"]
    return all_queries

QUERIES_TEXT = generate_queries()
print(f"✅ Generated {len(QUERIES_TEXT)} queries.")


# --- EMBEDDING (LOW MEMORY MODE) ---
print("⏳ Starting Low-Memory Embedding Pipeline...")

# We will store all vectors here
QUERY_VECS = {}

def get_sbert_embeddings(texts):
    print("   🔵 Loading SBERT...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device=DEVICE)
    vecs = model.encode(texts, convert_to_numpy=True)
    del model
    return vecs

def get_use_embeddings(texts):
    print("   🟠 Loading Universal Sentence Encoder (TF)...")
    

    # Load the model
    embed = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
    
    # Process in batches
    vecs = []
    batch_size = 512
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_vecs = embed(batch).numpy()
        vecs.append(batch_vecs)
    
    vecs = np.vstack(vecs) if vecs else np.array([])
    
    # Cleanup
    del embed
    
    # IMPORTANT: Clear TensorFlow session
    tf.keras.backend.clear_session()
    
    return vecs


def get_bio_clinicalbert_embeddings(texts):
    print("   🟣 Loading Bio_ClinicalBERT...")
    tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
    model = AutoModel.from_pretrained("emilyalsentzer/Bio_ClinicalBERT").to(DEVICE)
    
    vecs = []
    # Batch process to save RAM
    batch_size = 128
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=512).to(DEVICE)
        with torch.no_grad():
            outputs = model(**inputs)
            # Mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
            vecs.append(embeddings)
    
    del model
    del tokenizer
    return np.vstack(vecs)

def get_pubmedbert_embeddings(texts):
    print("   🟣 Loading PubMedBERT...")
    model = SentenceTransformer('NeuML/pubmedbert-base-embeddings', device=DEVICE)
    vecs = model.encode(texts, convert_to_numpy=True)
    del model
    return vecs

def get_sapbert_embeddings(texts):
    print("   🔴 Loading SapBERT...")
    model = SentenceTransformer('cambridgeltl/SapBERT-from-PubMedBERT-fulltext', device=DEVICE)
    vecs = model.encode(texts, convert_to_numpy=True)
    del model
    return vecs

def get_bge_embeddings(texts):
    print("   🔵 Loading BGE Base...")
    model = SentenceTransformer('BAAI/bge-base-en-v1.5', device=DEVICE)
    vecs = model.encode(texts, convert_to_numpy=True)
    del model
    return vecs

def get_biobert_sent_embeddings(texts):
    print("   🟡 Loading BioBERT Sentence...")
    model = SentenceTransformer("pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb", device=DEVICE)
    vecs = model.encode(texts, convert_to_numpy=True)
    del model
    return vecs

# List of jobs: (key_name, function)
embedding_jobs = [
    # ("use", get_use_embeddings), comentado pq n sei pq deixou de correr ? antes funcionava mas mudei umas merads e agr n csg voltar a por a dar 
    ("sbert", get_sbert_embeddings),
    ("bio_clinicalbert", get_bio_clinicalbert_embeddings),
    ("pubmedbert", get_pubmedbert_embeddings),
    ("sapbert_pubmed", get_sapbert_embeddings),
    ("bge", get_bge_embeddings),
    ("biobert_sent", get_biobert_sent_embeddings)
]

# Run sequentially with cleanup
for key, func in embedding_jobs:
    print(f"🚀 Processing {key}...")
    try:
        QUERY_VECS[key] = func(QUERIES_TEXT)
    except Exception as e:
        print(f"❌ Error embedding {key}: {e}")
        QUERY_VECS[key] = []
    
    # FORCE CLEANUP
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

all_vtypes = list(QUERY_VECS.keys())
print("✅ All queries embedded.")

# --- SIMPLIFIED SEARCH FUNCTIONS ---
def search_solr(vtype, q_vec, query_idx):
    """Vector search that returns drug_id, document content, and ANN score"""
    vec_str = "[" + ",".join(map(str, q_vec)) + "]"
    try:
        r = requests.post(
            f"{SOLR_URL}/{COLLECTION}/select",
            data={
                "q": f"{{!knn f=vector_{vtype} topK={TOP_K}}}{vec_str}",
                "fl": "drug_id,brand_name,purpose,indications_and_usage,warnings,score",
                "rows": TOP_K
            }
        )
        docs = r.json().get('response', {}).get('docs', [])
        # Add query index to each doc for tracking
        for doc in docs:
            doc['query_idx'] = query_idx
        return docs
    except Exception as e:
        print(f"❌ Solr search error for {vtype}: {e}")
        return []

# --- PER-METHOD JUDGMENT SYSTEM ---
print("⚖️ Setting up PER-METHOD Judgment System...")

RESULTS = []
METHOD_QRELS = {}  # {query_idx: {"vtype": {"drug_id1": 1, "drug_id2": 1, ...}}}

def judge_documents_per_method(query, docs, context_name):
    """Judge a set of documents for a query (PER-METHOD version) - Process in chunks"""
    if not docs:
        print(f"  ⚠️ No documents to judge for {context_name}")
        return {}
    
    print(f"  📊 {context_name}: Judging {len(docs)} documents in chunks of {CHUNK_SIZE}")
    
    all_qrels = {}
    
    # Process documents in chunks
    for chunk_start in range(0, len(docs), CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, len(docs))
        chunk = docs[chunk_start:chunk_end]
        chunk_num = chunk_start // CHUNK_SIZE + 1
        total_chunks = (len(docs) + CHUNK_SIZE - 1) // CHUNK_SIZE
        
        print(f"    Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} documents)")
        
        # Create document summary for this chunk only
        document_summaries = []
        for d in chunk:
            # Get purpose
            purpose_text = d.get('purpose', '')
            if purpose_text:
                purpose_text = purpose_text[:500]
                if len(d.get('purpose', '')) > 500:
                    purpose_text += "..."
            
            # Get indications_and_usage 
            indications_text = d.get('indications_and_usage', '')
            if indications_text:
                indications_text = indications_text[:1000]
                if len(d.get('indications_and_usage', '')) > 1000:
                    indications_text += "..."
            
            # Get warnings
            warnings_text = d.get('warnings', '')
            if warnings_text:
                warnings_text = warnings_text[:500]
                if len(d.get('warnings', '')) > 500:
                    warnings_text += "..."
            
            # Build the summary line in order: PURPOSE, INDICATIONS, WARNINGS
            summary_parts = []
            if d.get('drug_id'):
                summary_parts.append(f"ID: {d['drug_id']}")
            if d.get('brand_name'):
                summary_parts.append(f"Name: {d['brand_name'][:50]}")
            
            # ADD PURPOSE FIRST
            if purpose_text:
                summary_parts.append(f"PURPOSE: {purpose_text}")
            
            # THEN INDICATIONS AND USAGE
            if indications_text:
                summary_parts.append(f"INDICATIONS: {indications_text}")
            
            # THEN WARNINGS
            if warnings_text:
                summary_parts.append(f"WARNINGS: {warnings_text}")
            
            document_summaries.append(" | ".join(summary_parts))
        
        summary = "\n".join(document_summaries)
        
        # Prompt for judging this chunk
        prompt = f"""
Instructions:
1. List ALL document IDs that are relevant to the query
2. Consider the PURPOSE first, then INDICATIONS AND USAGE, then WARNINGS information
3. Be generous - include any document that could be somewhat relevant, even if just a little.
4. Return ONLY the JSON, no other text

Query: "{query}"

Available Documents (Chunk {chunk_num}/{total_chunks}):
{summary}

Task: Return ONLY a JSON object with this exact structure:
{{"relevant_ids": ["drug_id1", "drug_id2", "drug_id3"]}}

JSON:
"""
        
        chunk_context_name = f"{context_name}-Chunk{chunk_num}"
        
        # --- NEW LOGIC: RETRY LOOP ---
        data = None
        for attempt in range(MAX_LLM_RETRIES):
            resp = query_ollama(prompt, chunk_context_name)
            print(f"    📥 Response for {chunk_context_name} (Attempt {attempt+1}): {resp[:200]}...")
            
            # Attempt to extract JSON
            data = extract_json_from_text(resp)
            
            if data is not None:
                # Success! Break the retry loop
                break
            else:
                print(f"    🔄 JSON Parse Failed (Attempt {attempt+1}/{MAX_LLM_RETRIES}). Retrying request...")
        
        # If data is STILL None after retries, then we fallback
        if data is None:
            print(f"    ❌ Could not parse JSON for {chunk_context_name} after {MAX_LLM_RETRIES} attempts.")
            # Fallback: mark first few as relevant for this chunk
            fallback_ids = [d['drug_id'] for d in chunk[:min(2, len(chunk))] if d.get('drug_id')]
            print(f"      Using fallback IDs: {fallback_ids}")
            for k in fallback_ids:
                all_qrels[str(k)] = 1
            continue
        
        # Extract relevant IDs from the JSON
        rel_ids = []
        if isinstance(data, dict):
            if "relevant_ids" in data:
                rel_ids = data["relevant_ids"]
            elif "ids" in data:
                rel_ids = data["ids"]
            else:
                for key, value in data.items():
                    if isinstance(value, list):
                        rel_ids = value
                        break
        elif isinstance(data, list):
            rel_ids = data
        
        # Create QRELS mapping for this chunk
        candidate_ids = [str(d['drug_id']) for d in chunk if d.get('drug_id')]  # Convert to string for consistency
        
        for id_val in rel_ids:
            try:
                id_str = str(id_val).strip()
                if id_str in candidate_ids:
                    all_qrels[id_str] = 1
            except:
                continue
    
    print(f"  ✅ {context_name}: Found {len(all_qrels)} relevant out of {len(docs)} documents (processed in {chunk_num} chunks)")
    return all_qrels

def collect_and_judge_query_per_method(i):
    """Collect and judge documents for EACH METHOD separately"""
    query = QUERIES_TEXT[i]
    print(f"\n🔍 PER-METHOD JUDGE Q{i}: '{query}'")
    
    query_qrels = {}
    
    # --- For EACH method, collect documents and judge them separately ---
    for vtype in QUERY_VECS:
        q_vec = QUERY_VECS[vtype][i]
        vector_docs = search_solr(vtype, q_vec, i)
        
        if vector_docs:
            # Store results
            RESULTS.append({"algo": "Solr-HNSW", "vtype": vtype, "q_idx": i, "docs": vector_docs})
            print(f"  📥 {vtype}: Found {len(vector_docs)} documents")
            
            # Judge documents for THIS METHOD ONLY (in chunks of 5)
            method_qrels = judge_documents_per_method(query, vector_docs, f"{vtype}-Q{i}")
            query_qrels[vtype] = method_qrels
        else:
            print(f"  ⚠️ {vtype}: No documents found")
            query_qrels[vtype] = {}
    
    return i, query_qrels

print("\n" + "="*80)
print("STARTING PER-METHOD JUDGING PROCESS")
print("="*80)

# Collect and judge all queries with PER-METHOD judgments
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    futures = [ex.submit(collect_and_judge_query_per_method, i) for i in range(len(QUERIES_TEXT))]
    for f in tqdm(concurrent.futures.as_completed(futures), total=len(QUERIES_TEXT)):
        i, method_qrels = f.result()
        METHOD_QRELS[i] = method_qrels

# Create UNIFIED QRELS from method QRELS (take union across all methods for each query)
UNIFIED_QRELS = {}
for query_idx, method_dict in METHOD_QRELS.items():
    unified = {}
    for vtype, qrels in method_dict.items():
        unified.update(qrels)  # Union of all relevant IDs across methods
    UNIFIED_QRELS[query_idx] = unified

# Summary
print("\n" + "="*80)
print("PER-METHOD JUDGING SUMMARY")
print("="*80)

for vtype in all_vtypes:
    total_relevant = sum(len(METHOD_QRELS[i].get(vtype, {})) for i in range(len(QUERIES_TEXT)))
    print(f"{vtype}: {total_relevant} relevant documents")

total_unified_relevant = sum(len(qrels) for qrels in UNIFIED_QRELS.values())
queries_with_relevant = sum(1 for qrels in UNIFIED_QRELS.values() if len(qrels) > 0)

print(f"\nTotal unified relevant documents: {total_unified_relevant}")
print(f"Queries with relevant docs: {queries_with_relevant}/{len(QUERIES_TEXT)}")

# --- METRICS CALCULATION (P@5 and MAP) using UNIFIED judgments ---
print("\n" + "="*80)
print("CALCULATING METRICS with PER-METHOD JUDGMENTS (P@5 and MAP)")
print("="*80)

metrics_data = []

# Store per-query metrics for each algorithm
per_query_metrics = {vtype: {} for vtype in all_vtypes}

for vtype in all_vtypes:
    algo_name = vtype
    
    # Initialize P@K lists
    p_at_k_scores_dict = {k: [] for k in P_AT_K_LIST}
    
    # MAP (Mean Average Precision) scores
    map_scores = []
    
    # Debug counters
    total_queries_processed = 0
    queries_with_results = 0
    
    for i, q in enumerate(QUERIES_TEXT):
        truth = UNIFIED_QRELS.get(i, {})
        
        # Find matching results for this algorithm
        for r in RESULTS:
            if r['q_idx'] == i and r['vtype'] == vtype:
                docs = r['docs']
                total_queries_processed += 1
                
                # --- Debug ---
                print(f"\n  Query {i}: '{q}'")
                print(f"  Truth has {len(truth)} relevant documents: {list(truth.keys())[:5]}...")
                print(f"  Found {len(docs)} documents for {vtype}")
                
                # Calculate P@K for each K
                p_at_k_scores = {}
                for k in P_AT_K_LIST:
                    top_k_docs = docs[:k]
                    top_k_ids = [str(d['drug_id']) for d in top_k_docs if d.get('drug_id')]
                    hits_at_k = len([doc_id for doc_id in top_k_ids if doc_id in truth])
                    p_at_k = hits_at_k / k if top_k_ids else 0
                    p_at_k_scores[k] = p_at_k
                    p_at_k_scores_dict[k].append(p_at_k)
                    print(f"  P@{k} = {p_at_k:.4f} (Top {k} hits: {hits_at_k})")
                
                # --- Calculate Average Precision (AP) for this query ---
                all_ids = [str(d['drug_id']) for d in docs if d.get('drug_id')]
                if not all_ids or not truth:
                    ap = 0
                    print(f"  AP = 0.000 (no docs or no truth)")
                else:
                    precisions = []
                    num_relevant_found = 0
                    for rank, doc_id in enumerate(all_ids, 1):
                        if doc_id in truth:
                            num_relevant_found += 1
                            precision_at_rank = num_relevant_found / rank
                            precisions.append(precision_at_rank)
                    ap = sum(precisions) / len(truth) if truth else 0
                    print(f"  AP = {ap:.4f} (sum of {len(precisions)} precisions / {len(truth)} relevant docs)")
                
                map_scores.append(ap)
                
                # Store metrics
                metrics_entry = {
                    "algo": r['algo'],
                    "vtype": r['vtype'],
                    "query_idx": i,
                    **{f"p_at_{k}": p_at_k_scores[k] for k in P_AT_K_LIST},
                    "ap": ap
                }
                metrics_data.append(metrics_entry)
                
                # Store per-query metrics
                per_query_metrics[vtype][i] = {**{f"p_at_{k}": p_at_k_scores[k] for k in P_AT_K_LIST}, "ap": ap}
                
                queries_with_results += 1
                break
    
    print(f"\n{algo_name.upper()}: Processed {total_queries_processed} queries, found results for {queries_with_results}")
    for k in P_AT_K_LIST:
        avg_p_at_k = np.mean(p_at_k_scores_dict[k]) if p_at_k_scores_dict[k] else 0
        print(f"  Average P@{k}: {avg_p_at_k:.4f} (from {len(p_at_k_scores_dict[k])} queries)")
    avg_map = np.mean(map_scores) if map_scores else 0
    print(f"  MAP (Mean Average Precision): {avg_map:.4f}")

# --- 11-POINT INTERPOLATED PRECISION-RECALL CURVES with PER-METHOD judgments ---
print("\n" + "="*80)
print("11-POINT INTERPOLATED PRECISION-RECALL CURVES (PER-METHOD)")
print("="*80)

# Calculate 11-point interpolated precision for each algorithm and query
def compute_11pt_precision_recall(scores, labels):
    """Compute 11-point interpolated precision-recall curve"""
    if not scores or not labels:
        return np.zeros(11), np.arange(0, 1.1, 0.1)
    
    # Sort by score descending
    sorted_indices = np.argsort(scores)[::-1]
    sorted_labels = np.array(labels)[sorted_indices]
    
    # Compute precision and recall at each rank
    precisions = []
    recalls = []
    relevant_count = np.sum(labels)
    
    if relevant_count == 0:
        return np.zeros(11), np.arange(0, 1.1, 0.1)
    
    cumulative_relevant = 0
    for rank, label in enumerate(sorted_labels, 1):
        if label == 1:
            cumulative_relevant += 1
        precision_at_rank = cumulative_relevant / rank
        recall_at_rank = cumulative_relevant / relevant_count
        
        precisions.append(precision_at_rank)
        recalls.append(recall_at_rank)
    
    # Interpolate precision at 11 recall levels
    recall_levels = np.arange(0, 1.1, 0.1)
    interp_precisions = []
    
    for r in recall_levels:
        # Find maximum precision where recall >= r
        precisions_at_or_above = [precisions[i] for i in range(len(recalls)) if recalls[i] >= r]
        if precisions_at_or_above:
            interp_precisions.append(max(precisions_at_or_above))
        else:
            interp_precisions.append(0)
    
    return np.array(interp_precisions), recall_levels

plt.figure(figsize=(10, 6))

# Colors for each algorithm
colors = {vtype: cm.tab10(i) for i, vtype in enumerate(all_vtypes)}


# Line styles for algorithms
line_styles_list = ['-', '--', '-.', ':']
line_styles = {vtype: line_styles_list[i % len(line_styles_list)] for i, vtype in enumerate(all_vtypes)}


# For each algorithm, plot ONLY the AVERAGE curve
for vtype in all_vtypes:
    algo_name = vtype
    
    # Collect all scores and labels for this algorithm
    all_scores = []
    all_labels = []
    
    for i, q in enumerate(QUERIES_TEXT):
        truth = UNIFIED_QRELS.get(i, {})
        for r in RESULTS:
            if r['q_idx'] == i and r['vtype'] == vtype:
                docs = r['docs']
                for doc in docs:
                    drug_id = doc.get('drug_id')
                    if drug_id:
                        all_scores.append(doc.get('score', 0))
                        all_labels.append(1 if str(drug_id) in truth else 0)
    
    if all_scores and sum(all_labels) > 0:
            # Compute average 11-point curve
            interp_precisions, recall_levels = compute_11pt_precision_recall(all_scores, all_labels)
            
            # Get average MAP
            map_scores_for_algo = [m["ap"] for m in metrics_data if m["vtype"] == vtype]
            avg_map = np.mean(map_scores_for_algo) if map_scores_for_algo else 0
            
            # --- NEW: Calculate Average for ALL P@K values (5, 10, 20) ---
            p_at_k_strings = []
            for k in P_AT_K_LIST:
                scores = [m[f"p_at_{k}"] for m in metrics_data if m["vtype"] == vtype]
                avg_score = np.mean(scores) if scores else 0
                p_at_k_strings.append(f"P@{k}={avg_score:.3f}")
            
            # Join them like "P@5=0.500, P@10=0.400, P@20=0.300"
            p_legend_str = ", ".join(p_at_k_strings)
            
            # Calculate 11-point average (AUC for interpolated curve)
            auc_11pt = np.mean(interp_precisions)
            
            # Plot with detailed label
            plt.plot(recall_levels, interp_precisions, 
                    drawstyle="steps-post",
                    label=f"{algo_name.upper()}: MAP={avg_map:.3f}, {p_legend_str}",
                    linewidth=3,
                    color=colors[vtype],
                    linestyle=line_styles[vtype],
                    markersize=8)
            
            print(f"{algo_name.upper()}: 11-pt Avg Precision = {auc_11pt:.3f}")

# Customize plot appearance
axis_kwargs = {
    "fontsize": 12,
    "verticalalignment": "baseline",
    "style": "italic",
}

plt.title(f"11-Point Interpolated Precision-Recall Curve\n({len(QUERIES_TEXT)} queries, P@{P_AT_K_LIST})", fontsize=14)
plt.xlabel("Recall", fontdict=axis_kwargs)
plt.ylabel("Precision", fontdict=axis_kwargs)
plt.xlim(-0.005, 1.005)
plt.ylim(-0.005, 1.005)
plt.legend(loc="lower left", prop={"size": 10})
plt.grid(True)
plt.grid(linestyle='--', linewidth=0.5)
plt.tight_layout()

# Save the PR curve
plt.savefig("precision_recall_curve_11pt_avg_only.png", dpi=150)
print("\n✅ 11-point interpolated Precision-Recall curve saved as 'precision_recall_curve_11pt_avg_only.png'.")
plt.show()

# --- FINAL RESULTS TABLE (MAP COMPARISON) with PER-METHOD judgments ---
print("\n" + "="*80)
print("🏆 FINAL RESULTS TABLE with PER-METHOD JUDGMENTS")
print("="*80)

# Create a DataFrame for the final table
table_data = []

for algo in all_vtypes:
    algo_metrics = [m for m in metrics_data if m["vtype"] == algo]
    if algo_metrics:
        table_row = {"Algorithm": algo.upper()}
        for k in P_AT_K_LIST:
            p_at_k_values = [m[f"p_at_{k}"] for m in algo_metrics]
            avg_p_at_k = np.mean(p_at_k_values)
            std_p_at_k = np.std(p_at_k_values)
            table_row[f"P@{k}"] = f"{avg_p_at_k:.3f} ± {std_p_at_k:.3f}"
        ap_values = [m["ap"] for m in algo_metrics]
        table_row["MAP"] = f"{np.mean(ap_values):.3f} ± {np.std(ap_values):.3f}"
        table_row["Num Queries"] = len(algo_metrics)
        table_data.append(table_row)

# Create and display the table
df_table = pd.DataFrame(table_data)
print(df_table.to_string(index=False))

# --- PER-QUERY RESULTS FOR DEBUGGING ---
print("\n" + "="*80)
print("📊 PER-QUERY RESULTS (PER-METHOD)")
print("="*80)

for algo in all_vtypes:
    print(f"\n{algo.upper()}:")
    algo_metrics = [m for m in metrics_data if m["vtype"] == algo]
    algo_metrics.sort(key=lambda x: x["query_idx"])
    
    for m in algo_metrics:
        p_at_k_str = ", ".join([f"P@{k}={m[f'p_at_{k}']:.3f}" for k in P_AT_K_LIST])
        print(f"  Q{m['query_idx']:02d}: {p_at_k_str}, AP={m['ap']:.3f}")

# Save final results
with open("final_results_per_method.json", "w") as f:
    json.dump({
        "config": {
            "top_k": TOP_K,
            "p_at_k_list": P_AT_K_LIST,
            "chunk_size": CHUNK_SIZE,
            "num_queries": len(QUERIES_TEXT),
            "judgment_method": "PER-METHOD-CHUNKED"
        },
        "queries": QUERIES_TEXT,
        "results_summary": [{"algo": r["algo"], "vtype": r["vtype"], "q_idx": r["q_idx"], 
                             "docs_count": len(r["docs"])} for r in RESULTS],
        "method_qrels": METHOD_QRELS,
        "unified_qrels": UNIFIED_QRELS,
        "metrics": metrics_data,
        "summary_table": table_data
    }, f, indent=2)

print("\n✅ Final results saved as 'final_results_per_method.json'.")
print("\n" + "="*80)
print("EVALUATION COMPLETE! (PER-METHOD JUDGMENTS - CHUNKED)")
print("="*80)