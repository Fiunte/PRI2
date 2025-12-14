#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "🚀 Starting Drag & Drop Search Engine (Native Backend Mode)..."

# 1. Start Infrastructure (Solr + Frontend)
echo ""
echo "📦 Starting Docker containers (Solr + Frontend)..."
if ! command_exists docker; then
    echo "❌ Error: Docker is not installed."
    exit 1
fi

docker-compose up -d

# Wait for Solr to be ready
echo "⏳ Waiting for Solr to initialize..."
until curl -s -I http://localhost:8983/solr/admin/info/system >/dev/null; do
    printf "."
    sleep 2
done
echo ""
echo "✅ Solr is ready!"

# 2. Check Python Dependencies
echo ""
echo "🐍 Checking Python dependencies..."
# Simple check for a key package, otherwise install
if ! python3 -c "import sentence_transformers" >/dev/null 2>&1; then
    echo "⚠️  Dependencies not found. Installing..."
    pip install -r requirements.txt
    pip install -r backend/requirements.txt
else
    echo "✅ Python dependencies look good."
fi

# 3. Run Data Setup (Indexing)
echo ""
echo "⚙️  Running Setup (Indexing Data)..."
if [ ! -f "data_with_vectors.json" ]; then
    echo "   (This may take a while as it generates embedding vectors on your CPU/MPS)"
fi
chmod +x setup.sh
./setup.sh

# 4. Start Backend
echo ""
echo "🔥 Starting Backend API..."
echo "   - API:      http://localhost:8000"
echo "   - Docs:     http://localhost:8000/docs"
echo "   - Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop."
echo ""

cd backend
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
