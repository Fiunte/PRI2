from typing import List, Optional, Any, Dict, Tuple
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
import requests
import re
import torch 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

# --- CONFIGURATION ---
SOLR_URL = os.getenv("SOLR_URL", "http://localhost:8983/solr")
COLLECTION = "drugs" 
VECTOR_FIELD = "vector"
BM25_FIELD = "text_bm25"
RRF_K = 20
ALPHA = 0.5 # 50/50 Split

# --- DEVICE CONFIGURATION ---
device = 'cpu'
if torch.cuda.is_available():
    device = 'cuda'
elif torch.backends.mps.is_available():
    device = 'mps'

print(f"⏳ Loading PubMedBERT model on {device.upper()}...")
# Updated to the model used in your evaluation script
model = SentenceTransformer('NeuML/pubmedbert-base-embeddings', device=device)
print("✅ Model loaded.")

ID_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")

ID_FIELDS = [
    "product_ndc", 
    "primary_ndc", 
    "package_ndc", 
    "drug_id", 
    "set_id", 
    "unii"
]

SNIPPET_FIELDS = [
    "purpose",
    "indications_and_usage"
]

# --- HELPER: OPTIMIZED SNIPPETS ---

def generate_semantic_snippets(results: List[Dict[str, Any]], query_embedding: List[float]):
    """
    Optimized: Collects ALL sentences from ALL items and encodes them in a SINGLE batch.
    """
    if not query_embedding:
        return results

    query_tensor = torch.tensor(query_embedding).to(model.device)    
    # 1. Collection Phase
    batch_candidates: List[Tuple[str, Dict[str, Any]]] = []

    def collect_from_item(item: Dict[str, Any]):
        count = 0
        for field in SNIPPET_FIELDS:
            text = item.get(field)
            if text and isinstance(text, str):
                sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
                for sent in sentences:
                    if count >= 20: break 
                    batch_candidates.append((sent, item))
                    count += 1
            if count >= 20: break

    for result in results:
        collect_from_item(result)
        if result.get("is_cluster") and result.get("variants"):
            for variant in result["variants"]:
                collect_from_item(variant)

    if not batch_candidates:
        return results

    # 2. Batch Inference Phase
    all_texts = [x[0] for x in batch_candidates]
    all_embeddings = model.encode(all_texts, convert_to_tensor=True)

    # 3. Scoring Phase
    all_scores = util.cos_sim(query_tensor, all_embeddings)[0]

    # 4. Distribution Phase
    for i, score_tensor in enumerate(all_scores):
        score = score_tensor.item()
        if score > 0.40: # Threshold
            sentence, item_ref = batch_candidates[i]
            current_best = item_ref.get("match_score", -1)
            if score > current_best:
                item_ref["match_snippet"] = sentence
                item_ref["match_score"] = score

    return results

# --- HELPER: CLUSTERING ---

def cluster_results(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clusters = {}
    ungrouped = []

    for doc in docs:
        # Normalize score if it exists, otherwise default to 0
        if 'score' not in doc: doc['score'] = 0.0

        unii_list = doc.get("unii")
        if unii_list and isinstance(unii_list, list) and len(unii_list) > 0:
            key = tuple(sorted(unii_list))
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(doc)
        else:
            ungrouped.append(doc)

    final_results = []

    for unii_tuple, items in clusters.items():
        if len(items) == 1:
            final_results.append(items[0])
        else:
            # Sort by RRF score descending
            items.sort(key=lambda x: x.get("score", 0), reverse=True)
            representative = items[0]
            max_score = representative.get("score", 0)

            cluster_id = f"cluster_{'_'.join(unii_tuple)}"
            cluster_obj = {
                "id": cluster_id,
                "is_cluster": True,
                "cluster_count": len(items),
                "score": max_score, 
                "variants": items,
                "brand_name": representative.get("brand_name"),
                "generic_name": representative.get("generic_name"), 
                "unii": list(unii_tuple),
                "manufacturer": "Multiple Manufacturers",
                "purpose": representative.get("purpose"), 
                "indications_and_usage": representative.get("indications_and_usage")
            }
            final_results.append(cluster_obj)

    final_results.extend(ungrouped)
    final_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    return final_results

# --- HELPER: HYBRID SEARCH EXECUTION ---

def execute_solr_query(params):
    try:
        r = requests.post(
            f"{SOLR_URL}/{COLLECTION}/select",
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        r.raise_for_status()
        return r.json().get('response', {}).get('docs', [])
    except Exception as e:
        print(f"Solr Request Error: {e}")
        return []

# --- MAIN ENDPOINT ---

@app.get("/search")
def search_drugs(
    query: Optional[str] = None, 
    fq: List[str] = Query(None) 
):
    if not query and not fq:
        return []
    
    try:
        base_params = { "rows": 50, "fl": "*,score", "wt": "json" }
        if fq: base_params["fq"] = fq

        # --- BRANCH 1: STRICT ID SEARCH (No Hybrid needed) ---
        if query and query.strip() and ID_PATTERN.match(query.strip()):
            clean_q = query.strip()
            id_clauses = [f'{field}:"{clean_q}"' for field in ID_FIELDS]
            id_params = base_params.copy()
            id_params["q"] = " OR ".join(id_clauses)
            
            docs = execute_solr_query(id_params)
            if docs:
                for d in docs: d['score'] = 1.0
                return cluster_results(docs)

        # --- BRANCH 2: HYBRID SEARCH (PubMedBERT + BM25) ---
        query_embedding = None
        final_docs_map = {} # drug_id -> doc (with RRF score)
        
        if query and query.strip():
            # 1. Encode Query
            query_embedding = model.encode(query, convert_to_tensor=False).tolist()
            
            # 2. Vector Search (PubMedBERT)
            vec_str = "[" + ",".join(map(str, query_embedding)) + "]"
            vec_params = base_params.copy()
            vec_params["q"] = f"{{!knn f={VECTOR_FIELD} topK=50}}{vec_str}"
            vector_docs = execute_solr_query(vec_params)

            # 3. Text Search (BM25)
            bm25_params = base_params.copy()
            # Construct standard BM25 query
            bm25_params["q"] = f"{BM25_FIELD}:{query}" 
            bm25_docs = execute_solr_query(bm25_params)

            # 4. RRF FUSION (50/50 Split)
            # RRF Logic: score = alpha * (1 / (k + rank)) + (1-alpha) * (1 / (k + rank))
            
            fused_scores = {} # drug_id -> RRF Score

            def apply_rrf(docs, rank_weight):
                for rank, doc in enumerate(docs, 1):
                    doc_id = str(doc.get('drug_id'))
                    if not doc_id: continue
                    
                    # Store doc content if not seen
                    if doc_id not in final_docs_map:
                        final_docs_map[doc_id] = doc
                    
                    # Calculate RRF component
                    rr = 1 / (RRF_K + rank)
                    score_contrib = rank_weight * rr
                    
                    fused_scores[doc_id] = fused_scores.get(doc_id, 0) + score_contrib

            # Apply Vector Ranks (Alpha = 0.5)
            apply_rrf(vector_docs, ALPHA)
            
            # Apply BM25 Ranks (1 - Alpha = 0.5)
            apply_rrf(bm25_docs, (1 - ALPHA))

            # Calculate the theoretical maximum score (Rank 1 in both)
            # Max = 1 / (20 + 1) = 1/21 ≈ 0.0476
            max_possible_score = 1 / (RRF_K + 1)

            # 5. Assign Final Scores (Normalized)
            for doc_id, raw_score in fused_scores.items():
                if doc_id in final_docs_map:
                    # Normalize: Divide by max so the perfect score is 1.0
                    normalized_score = raw_score / max_possible_score
                    
                    # Optional: Cap it at 1.0 just in case of floating point weirdness
                    final_docs_map[doc_id]['score'] = min(normalized_score, 1.0)
            
            # --- NEW CODE ENDS HERE ---
            
            raw_docs = list(final_docs_map.values())

        else:
            # Fallback for empty query / just filters
            base_params["q"] = "*:*"
            raw_docs = execute_solr_query(base_params)
        
        # 6. Cluster Results
        clustered = cluster_results(raw_docs)
        
        # 7. Slice Top 10
        final_page = clustered[:10]

        # 8. Generate Snippets (using the same PubMedBERT model)
        if query_embedding:
            final_page = generate_semantic_snippets(final_page, query_embedding)
        
        return final_page

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- MORE LIKE THIS ENDPOINT (Relevance Feedback) ---

@app.get("/more-like-this")
def more_like_this(id: str = Query(...)):
    """
    Returns documents similar to the given document ID using Solr's MLT (MoreLikeThis) feature.
    This implements 'Relevance Feedback' where the user selects a relevant result to find similar ones.
    """
    try:
        # MLT Params
        params = {
            "q": f'id:"{id}"',
            "mlt": "true",
            "mlt.fl": "active_ingredients,purpose,indications_and_usage,generic_name",
            "mlt.mindf": "1",
            "mlt.mintf": "1",
            "mlt.count": "5",
            "rows": "5",
            "fl": "*,score",
            "wt": "json"
        }
        
        # We need to parse raw solr response to get the MLT section usually, 
        # but if we query q=id:X & mlt=true, the 'response' has the doc X, and 'moreLikeThis' has the neighbors.
        # Alternatively, we can use the mlt handler.
        # Let's use the select handler with mlt=true.
        
        r = requests.post(
            f"{SOLR_URL}/{COLLECTION}/select",
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        r.raise_for_status()
        data = r.json()
        
        # Solr MLT response structure:
        # { "response": { "docs": [THE_SOURCE_DOC] }, "moreLikeThis": { "SOURCE_ID": { "docs": [...] } } }
        
        mlt_data = data.get("moreLikeThis", {})
        similar_docs = []
        if id in mlt_data:
            similar_docs = mlt_data[id].get("docs", [])
            
        # Fallback: if id needs escaping or looked different (e.g. quotes in key), try the first key
        if not similar_docs and mlt_data:
            first_key = list(mlt_data.keys())[0]
            similar_docs = mlt_data[first_key].get("docs", [])

        # Clean up lists (optional, similar to main search)
        cleaned = []
        for doc in similar_docs:
             # Basic cleanup if needed
             cleaned.append(doc)
             
        return cleaned

    except Exception as e:
        print(f"MLT Error: {e}")
        # Return empty list gracefully
        return []