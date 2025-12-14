#!/bin/sh

SOLR_URL="http://solr:8983/solr"
COLLECTION_NAME="drugs"

echo "--- Waiting for Solr core '$COLLECTION_NAME' to be ready at $SOLR_URL/$COLLECTION_NAME/admin/ping ---"

while ! curl --output /dev/null --silent --head --fail $SOLR_URL/$COLLECTION_NAME/admin/ping ; do
    printf "."
    sleep 3
done
echo ""
echo "Solr core '$COLLECTION_NAME' is ready. Starting setup."

echo "Configuring analysis (tokenizers & filters) using analysis.json..."
curl -s -X POST -H "Content-Type: application/json" \
  --data-binary @/analysis.json \
  "$SOLR_URL/$COLLECTION_NAME/schema"

echo "Defining schema fields using fields.json..."
curl -s -X POST -H "Content-Type: application/json" \
  --data-binary @/fields.json \
  "$SOLR_URL/$COLLECTION_NAME/schema"

echo "Defining copy fields using copy_fields.json..."
curl -s -X POST -H "Content-Type: application/json" \
  --data-binary @/copy_fields.json \
  "$SOLR_URL/$COLLECTION_NAME/schema"

echo "Adding initial data using data.json..."
curl -s -X POST -H "Content-Type: application/json" \
  --data-binary @/data.json \
  "$SOLR_URL/$COLLECTION_NAME/update?commit=true"

echo "--- Solr setup for collection '$COLLECTION_NAME' complete! ---"
echo "You can access Solr Admin UI at http://localhost:8983/solr"
