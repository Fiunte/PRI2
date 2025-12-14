#!/bin/sh
set -e  # Exit immediately if any command fails

SOLR_URL="http://solr:8983/solr"
COLLECTION_NAME="drugstest"

echo "--- Waiting for Solr at $SOLR_URL ---"
# Loop until Solr responds successfully
until curl -sf "$SOLR_URL/$COLLECTION_NAME/admin/ping" > /dev/null; do
    echo "Waiting for Solr core '$COLLECTION_NAME'..."
    sleep 3
done

echo "--- Solr is up. Applying Schema ---"

# We perform these sequentially with small pauses to ensure Solr processes them
echo "Applying Analysis..."
curl -X POST -H "Content-Type: application/json" --data-binary @analysis.json "$SOLR_URL/$COLLECTION_NAME/schema"
echo "" # New line for readability
sleep 1

echo "Applying Fields..."
curl -X POST -H "Content-Type: application/json" --data-binary @fields.json "$SOLR_URL/$COLLECTION_NAME/schema"
echo ""
sleep 1

echo "Applying Copy Fields..."
curl -X POST -H "Content-Type: application/json" --data-binary @copy_fields.json "$SOLR_URL/$COLLECTION_NAME/schema"
echo ""
sleep 1

echo "Applying Multi-Vector Schema..."
curl -X POST -H 'Content-type: application/json' --data-binary "@vector-schema-multi.json" "$SOLR_URL/$COLLECTION_NAME/schema"
echo ""
sleep 1

# --- Data Processing ---
echo "Running Python Generator/Indexer..."
# This will now STOP the script if it crashes, so you don't get a fake "Success" message
python3 generate_embeddings_multi.py 

echo "--- Setup Complete! Solr Core '$COLLECTION_NAME' is ready. ---"