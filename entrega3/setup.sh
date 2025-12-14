#!/bin/sh

SOLR_URL="http://solr:8983/solr"
COLLECTION_NAME="drugs"

echo "--- Waiting for Solr core '$COLLECTION_NAME' to be ready..."

# Wait loop
while ! curl --output /dev/null --silent --head --fail "$SOLR_URL/$COLLECTION_NAME/admin/ping"; do
    printf "."
    sleep 3
done
echo ""
echo "Solr is ready."

# --- SCHEMA SETUP (Assumes these files exist) ---
echo "Configuring schema..."
curl -s -X POST -H "Content-Type: application/json" --data-binary @analysis.json "$SOLR_URL/$COLLECTION_NAME/schema"
curl -s -X POST -H "Content-Type: application/json" --data-binary @fields.json "$SOLR_URL/$COLLECTION_NAME/schema"
curl -s -X POST -H "Content-Type: application/json" --data-binary @copy_fields.json "$SOLR_URL/$COLLECTION_NAME/schema"

echo "Applying Vector Schema..."
curl -X POST -H 'Content-type: application/json' --data-binary "@vector-schema.json" "$SOLR_URL/$COLLECTION_NAME/schema"

# --- EMBEDDING GENERATION ---
# Logic moved to Python. We just call it.
# No pipes, no redirects. If it crashes, no broken file is created.
echo "Running Python Embedding Script..."
python3 get_embeddings.py

# Check if Python succeeded (file exists) before indexing
OUTPUT_FILE="data_with_vectors.json"

if [ -f "$OUTPUT_FILE" ]; then
    echo "Indexing data to Solr..."
    curl -s -X POST -H "Content-Type: application/json" \
      --data-binary @$OUTPUT_FILE \
      "$SOLR_URL/$COLLECTION_NAME/update?commit=true"
    
    echo "--- Solr setup complete! ---"
    echo "Access Solr Admin at http://localhost:8983/solr"
else
    echo "❌ Error: $OUTPUT_FILE was not generated. Check Python logs above."
    exit 1
fi