"""
Minimal DeepSeek evaluation test script
------------------------------------
This script isolates the *evaluation / judging logic* that uses DeepSeek
and prints the model's answers for inspection.

It is intentionally similar in structure/style to your main evaluation code,
but:
- No Solr
- No embeddings
- No metrics
- No chunk unions

Purpose: *debug and observe DeepSeek judgments only*
"""

import os
import json
import re
import requests
from typing import List, Dict

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL_NAME = "deepseek-r1"
CHUNK_SIZE = 5
MAX_LLM_RETRIES = 3

# ---------------------------------------------------------------------
# OLLAMA HELPERS
# ---------------------------------------------------------------------
def ensure_ollama_model():
    print(f"🦙 Checking Ollama model '{MODEL_NAME}'...")
    r = requests.get(f"{OLLAMA_URL}/api/tags")
    models = [m["name"] for m in r.json().get("models", [])]
    if f"{MODEL_NAME}:latest" not in models and MODEL_NAME not in models:
        print(f"⬇️ Pulling {MODEL_NAME}...")
        requests.post(f"{OLLAMA_URL}/api/pull", json={"name": MODEL_NAME})
    print("✅ Model ready")


def query_ollama(prompt: str, context: str = "DeepSeek", json_mode: bool = True) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json" if json_mode else "",
    }

    print(f"\n--- PROMPT ({context}) ---")
    print(prompt)
    print("-------------------------")

    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
    text = r.json().get("response", "")

    # Remove DeepSeek thinking traces
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    print(f"--- RESPONSE ({context}) ---")
    print(clean)
    print("---------------------------")

    return clean


# ---------------------------------------------------------------------
# JSON EXTRACTION (same logic as main code)
# ---------------------------------------------------------------------
def extract_json_from_text(text: str):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass

    try:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass

    try:
        return json.loads(text)
    except:
        return None


# ---------------------------------------------------------------------
# CORE JUDGING LOGIC (ISOLATED)
# ---------------------------------------------------------------------
def judge_documents(query: str, docs: List[Dict]):
    print(f"\n⚖️ Judging {len(docs)} docs for query: '{query}'")

    qrels = {}

    for start in range(0, len(docs), CHUNK_SIZE):
        chunk = docs[start:start + CHUNK_SIZE]
        chunk_id = start // CHUNK_SIZE + 1

        summaries = []
        for d in chunk:
            parts = [
                f"ID: {d['drug_id']}",
                f"Name: {d.get('brand_name', '')}",
                f"PURPOSE: {d.get('purpose', '')[:300]}",
                f"INDICATIONS: {d.get('indications_and_usage', '')[:600]}",
                f"WARNINGS: {d.get('warnings', '')[:300]}"
            ]
            summaries.append(" | ".join(parts))

        prompt = f"""
Instructions:
1. List ALL document IDs that are relevant to the query
2. Be generous
3. Return ONLY JSON

Query: "{query}"

Documents:
{chr(10).join(summaries)}

Return format:
{{"relevant_ids": ["id1", "id2"]}}

JSON:
"""

        data = None
        for attempt in range(MAX_LLM_RETRIES):
            resp = query_ollama(prompt, f"Chunk-{chunk_id}")
            data = extract_json_from_text(resp)
            if data:
                break
            print(f"⚠️ Retry {attempt+1}/{MAX_LLM_RETRIES}")

        if not data:
            print("❌ Failed to parse JSON – skipping chunk")
            continue

        rel_ids = data.get("relevant_ids", []) if isinstance(data, dict) else data

        for rid in rel_ids:
            qrels[str(rid)] = 1

    print(f"✅ Relevant IDs: {list(qrels.keys())}")
    return qrels


# ---------------------------------------------------------------------
# TEST DATA (FAKE SOLR RESULTS)
# ---------------------------------------------------------------------
TEST_DOCS = [
    {
        "drug_id": "D1",
        "brand_name": "PainAway",
        "purpose": "Pain relief",
        "indications_and_usage": "Used for mild to moderate pain",
        "warnings": "Liver risk"
    },
    {
        "drug_id": "D2",
        "brand_name": "ColdFree",
        "purpose": "Cold and flu",
        "indications_and_usage": "Relieves congestion and fever",
        "warnings": "Not for pregnancy"
    },
    {
        "drug_id": "D3",
        "brand_name": "HeartSafe",
        "purpose": "Blood pressure",
        "indications_and_usage": "Hypertension treatment",
        "warnings": "Consult physician"
    },
]


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    ensure_ollama_model()

    QUERY = "pain relief safe for liver"

    qrels = judge_documents(QUERY, TEST_DOCS)

    print("\n🧪 FINAL OUTPUT")
    print(json.dumps(qrels, indent=2))
