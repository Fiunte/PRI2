import requests
import json

# --- Configuration ---
SOLR_URL = "http://localhost:8983/solr/drugs/select"
ROWS_TO_FETCH = 20 # For the initial pooling step
QRELS_TEMPLATE_FILE = "qrels.txt"
CONTENT_OUTPUT_FILE = "content.json"

# Fields to fetch for the LLM/Manual evaluation (essential for relevance judgment)
FIELDS_FOR_JUDGMENT = "id,purpose,warnings,active_ingredients,route,product_type,effective_time"

RELEVANCE_CRITERIA = """
Assign a binary relevance score of 1 (Relevant) or 0 (Irrelevant) to the provided document based on the following specific user need: A pregnant woman requires a safe, oral, over-the-counter (OTC) medication for fever or headache, with product information updated between 2023 and 2025. To be marked Relevant (1), the document must satisfy all five conditions: it explicitly indicates treatment for fever or headache, specifies an oral administration route (e.g., tablet, liquid), is classified as OTC, includes a date within the 2023-2025 range, and does not strictly contraindicate use during pregnancy. Mark as Irrelevant (0) if the product treats different symptoms, is non-oral (e.g., topical, nasal), requires a prescription, is outdated, or explicitly forbids use during pregnancy. Treat standard regulatory warnings like "consult a health professional before use" as acceptable for relevant items.
"""

# -------------------------------------------------------------------------------------------------

# --- Setup 1 (Baseline) Parameters ---
SETUP_1_PARAMS = {
    "q": "fever headache pregnancy oral OTC",
    "defType": "edismax",
    "qf": "text_all^1",
}

# -------------------------------------------------------------------------------------------------

# --- Setup 2 (Advanced) Parameters ---
SETUP_2_PARAMS = {
    "q": "(fever^4 headache^3)",
    "defType": "edismax",
    "qf": "purpose^4.0 warnings^3.0 text_all",
    "fq": [
        'product_type:("OTC")',
        'route:ORAL',
        'effective_time:[2022-01-01T00:00:00Z TO NOW]',
    ],
    "bq": [
        'warnings:"safe for pregnancy"~5^3.0'
    ],
    "pf": "warnings^2.0"
}

def fetch_solr_results(system_name, params):
    """Executes a query against Solr and returns a list of doc IDs (for pooling)."""

    # Common parameters (rows, writer type, and fields to return)
    common_params = {
        "rows": ROWS_TO_FETCH,
        "wt": "json",
        "fl": "id",  # Only need the document ID for pooling
        "indent": "true"
    }

    # Merge query-specific and common parameters
    query_params = {**params, **common_params}

    try:
        response = requests.get(SOLR_URL, params=query_params)
        response.raise_for_status() # Raise an exception for bad status codes

        data = response.json()
        doc_ids = [doc['id'] for doc in data.get('response', {}).get('docs', [])]

        print(f"✅ {system_name} retrieved {len(doc_ids)} documents for pooling.")
        return doc_ids

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching results for {system_name} (pooling): {e}")
        print("Please check SOLR_URL and ensure your Solr instance is running.")
        return []

def fetch_document_content(doc_ids):
    """Fetches the content of all pooled documents for manual/LLM evaluation."""
    if not doc_ids:
        return []

    # Solr query to retrieve specific fields for a set of IDs
    params = {
        "q": f"id:({' OR '.join(doc_ids)})",
        "wt": "json",
        "fl": FIELDS_FOR_JUDGMENT,
        "rows": len(doc_ids) # Ensure all pooled docs are returned
    }

    try:
        response = requests.get(SOLR_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('response', {}).get('docs', [])

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching document content: {e}")
        return []

# --- NEW FUNCTION FOR RUN FILE GENERATION ---

def execute_search_and_save_runfile(query_id, system_name, params, run_filename, rows=100):
    """
    Executes a query against Solr and saves the results in TREC run file format.
    Fetches the top 'rows' results, including their 'id' and 'score'.
    """

    # Parameters for fetching ID and score for the run file
    run_params = {
        "rows": rows,
        "wt": "json",
        "fl": "id,score", # We need id and score for the run file
        "indent": "true"
    }

    # Merge query-specific parameters (params) with run file parameters (run_params)
    query_params = {**params, **run_params}

    print(f"\n--- Generating Run File for {system_name} ---")
    print(f"Query ID: {query_id}, Rows: {rows}, File: {run_filename}")

    try:
        response = requests.get(SOLR_URL, params=query_params)
        response.raise_for_status() # Raise an exception for bad status codes

        data = response.json()
        docs = data.get('response', {}).get('docs', [])

        if not docs:
            print(f"⚠️ Warning: {system_name} returned 0 documents for {query_id}.")

        with open(run_filename, 'w') as f:
            # Write header
            f.write(f"# Run file for {system_name} (Query: {query_id})\n")
            f.write(f"# Format: Q_ID iteration Doc_ID Rank Score System_Name\n")

            # Iterate and write in TREC format
            for rank, doc in enumerate(docs, start=1):
                q_id = query_id
                iteration = "0" # Standard iteration string
                doc_id = doc.get('id', 'MISSING_ID')
                score = doc.get('score', 0.0)

                # Format: Q_ID iteration Doc_ID Rank Score System_Name
                f.write(f"{q_id} {iteration} {doc_id} {rank} {score} {system_name}\n")

        print(f"✅ {system_name} run file saved to {run_filename} ({len(docs)} results).")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching results for {system_name} (run file): {e}")
        print("Please check SOLR_URL and ensure your Solr instance is running.")
        return False

# --- Execution and Pooling (Original Script) ---

print(f"--- Starting Pooling Process (Top {ROWS_TO_FETCH} from each system) ---")

# 1. Execute Setup 1 (Baseline)
s1_docs = fetch_solr_results("Setup 1 (Baseline)", SETUP_1_PARAMS)

# 2. Execute Setup 2 (Advanced)
s2_docs = fetch_solr_results("Setup 2 (Advanced)", SETUP_2_PARAMS)

# 3. Pool the Results
pooled_doc_ids = sorted(list(set(s1_docs) | set(s2_docs)))

print("\n--- Pooling Summary ---")
print(f"Total Unique Documents in Pool: {len(pooled_doc_ids)}")


# 4. Save Pooled IDs to Qrels Template File
# Note: This step is still useful to ensure you have a qrels.txt file.
# You will need to *manually* fill this file with relevance judgments.
with open(QRELS_TEMPLATE_FILE, 'w') as f:
    f.write(f"# Doc_ID Relevance (1=Relevant, 0=Irrelevant)\n")
    f.write(f"# Total Documents to Judge: {len(pooled_doc_ids)}\n")
    for doc_id in pooled_doc_ids:
        # Using a placeholder query 'Q1' as qrels format is: Q_ID 0 Doc_ID Relevance
        f.write(f"Q1 0 {doc_id} [0 or 1]\n")

print(f"✅ Qrels template (IDs) saved to: {QRELS_TEMPLATE_FILE}")
print(f"ℹ️  Remember to manually edit '{QRELS_TEMPLATE_FILE}' with 0 or 1 judgments.")


# 5. Fetch and Save Document Content for LLM/Manual Judgment
pooled_content = fetch_document_content(pooled_doc_ids)

# Prepare the data structure for JSON output, including instructions
evaluation_data = {
    "relevance_criteria": RELEVANCE_CRITERIA,
    "documents_to_judge": pooled_content
}

with open(CONTENT_OUTPUT_FILE, 'w') as f:
    json.dump(evaluation_data, f, indent=4)

print(f"✅ Document content for judgment saved to: {CONTENT_OUTPUT_FILE}")


# --- NEW: Execution for Generating Run Files ---

print("\n\n" + "="*50)
print("--- Starting Experiment: Generating Run Files ---")
print("="*50)

# Define the query set
# As per instructions, we only have Q1
QUERY_SET = {
    "Q1": "fever headache pregnancy safe" # Descriptive text, actual query is in PARAMS
}

# Define run file names
RUN_FILE_SETUP_1 = "setup1_run.txt"
RUN_FILE_SETUP_2 = "setup2_run.txt"
ROWS_FOR_RUN = 100 # As per instructions

for q_id, q_text in QUERY_SET.items():
    # --- Generate Run File for Setup 1 ---
    # We pass SETUP_1_PARAMS which contains the correct 'q' and 'qf'
    execute_search_and_save_runfile(
        query_id=q_id,
        system_name="Setup1",
        params=SETUP_1_PARAMS,
        run_filename=RUN_FILE_SETUP_1,
        rows=ROWS_FOR_RUN
    )

    # --- Generate Run File for Setup 2 ---
    # We pass SETUP_2_PARAMS which contains the correct 'q', 'qf', and 'bq'
    execute_search_and_save_runfile(
        query_id=q_id,
        system_name="Setup2",
        params=SETUP_2_PARAMS,
        run_filename=RUN_FILE_SETUP_2,
        rows=ROWS_FOR_RUN
    )

print("\n--- Run File Generation Complete ---")
print(f"Files created: {RUN_FILE_SETUP_1}, {RUN_FILE_SETUP_2}")


# --- Original Next Steps ---
print("\n--- Next Steps ---")
print(f"1. Manually review {CONTENT_OUTPUT_FILE} (using {QRELS_TEMPLATE_FILE}) to create the final qrels.")
print(f"2. Once '{QRELS_TEMPLATE_FILE}' is complete, you will have all three files:")
print(f"   - {QRELS_TEMPLATE_FILE} (completed)")
print(f"   - {RUN_FILE_SETUP_1}")
print(f"   - {RUN_FILE_SETUP_2}")
print("3. Use these files with an evaluation tool like pytrec_eval to calculate metrics.")
