import json
import os
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
import requests
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. CONFIGURATION & DYNAMIC LOADING ---

# Define path to shared/categories.json
# Logic: Go up one level from this file (backend/) into shared/
BASE_DIR = Path(__file__).resolve().parent
SHARED_DATA_PATH = BASE_DIR.parent / "shared" / "categories.json"

CATEGORY_MAP = {}

def load_categories():
    """Loads categories from the shared JSON file."""
    if not SHARED_DATA_PATH.exists():
        print(f"WARNING: Could not find categories.json at {SHARED_DATA_PATH}")
        return

    try:
        with open(SHARED_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Populate the map
        for field, values in data.items():
            for v in values:
                if v and v.strip():
                    CATEGORY_MAP[v.lower()] = (field, v)
        
        print(f"Successfully loaded {len(CATEGORY_MAP)} categorical terms from shared JSON.")
        
    except Exception as e:
        print(f"Error loading categories: {e}")

# Load immediately on startup
load_categories()

# Pre-compile regex
# We check if map is populated to avoid errors if file is missing
if CATEGORY_MAP:
    sorted_keys = sorted(CATEGORY_MAP.keys(), key=len, reverse=True)
    pattern_str = r'\b(' + '|'.join(map(re.escape, sorted_keys)) + r')\b'
    FILTER_PATTERN = re.compile(pattern_str, re.IGNORECASE)
else:
    FILTER_PATTERN = re.compile(r'(?!x)x') # Matches nothing if no data

# --- 2. LOAD MODEL ---

print("Loading model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")

SOLR_URL = "http://solr:8983/solr"
COLLECTION = "drugs"

# --- 3. HELPER FUNCTION ---

def rewrite_query(user_query: str):
    """
    Extracts known categories from the query string using the shared JSON data.
    """
    filters = []
    
    def replace_callback(match):
        text = match.group(0).lower()
        if text in CATEGORY_MAP:
            field, value = CATEGORY_MAP[text]
            filters.append(f'{field}:"{value}"')
            return ""
        return match.group(0)

    cleaned_query = FILTER_PATTERN.sub(replace_callback, user_query)
    cleaned_query = " ".join(cleaned_query.split())
    
    return cleaned_query, filters

# --- 4. ENDPOINT ---

@app.get("/search")
def search_drugs(
    query: Optional[str] = None, 
    fq: List[str] = Query(None)
):
    if not query and not fq:
        return []
    
    try:
        # Initialize default Solr params
        solr_params = {
            "rows": 10,
            "fl": "*,score",
            "wt": "json"
        }

        # List to collect all filters (from frontend + extracted from query)
        final_filters = []
        if fq:
            final_filters.extend(fq)

        clean_text = query

        # If a query exists, try to extract more filters (Backend Fallback)
        # This handles cases where API is called directly without frontend logic
        if query:
            extracted_text, extracted_filters = rewrite_query(query)
            # Only apply backend extraction if it found something AND the query wasn't already cleaned by frontend
            # (Simple heuristic: if frontend passed FQ, we assume they handled it, but this adds safety)
            if extracted_filters:
                final_filters.extend(extracted_filters)
                clean_text = extracted_text

        # Apply collected filters to Solr params
        if final_filters:
            solr_params["fq"] = final_filters

        # Construct Main Query (q)
        if clean_text and clean_text.strip():
            embedding = model.encode(clean_text, convert_to_tensor=False).tolist()
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            solr_params["q"] = f"{{!knn f=vector topK=10}}{embedding_str}"
        else:
            # If query is empty (or became empty after extraction), verify we have filters
            if final_filters:
                solr_params["q"] = "*:*"
            else:
                return [] # Nothing to search

        # Execute
        response = requests.post(
            f"{SOLR_URL}/{COLLECTION}/select", 
            data=solr_params, 
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        
        return response.json().get("response", {}).get("docs", [])

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))