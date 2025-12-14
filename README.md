# Drug Search Engine (Native Backend)

This project uses a Hybrid Search approach (Vector Search + Keyword Search) with Solr and a Python FastAPI backend.
The backend is configured to run **natively** on your machine (supporting Mac MPS/CPU) while Solr and the Frontend run in Docker.

## Prerequisites

1. **Docker & Docker Compose**: For Solr and Frontend.
2. **Python 3.9+**: For the backend and embedding generation.
3. **Data Files**: Ensure `data.json` is present (and not a Git LFS pointer).

## 🚀 Quick Start (Automated)

We have provided a script to automate the entire startup process:

```bash
cd entrega3
chmod +x run_native.sh
./run_native.sh
```

This script will:
1. Start Solr and Frontend containers.
2. Install Python dependencies (if missing).
3. Run `setup.sh` to generate embeddings and index data.
4. Start the Python Backend API.

---

## 🛠 Manual Setup

If you prefer to run step-by-step:

### 1. Start Infrastructure
```bash
cd entrega3
docker-compose up -d
```
*Wait for Solr to be ready (approx 10-20s).*

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### 3. Index Data
This generates embeddings (using your local GPU/CPU) and sends them to Solr.
```bash
./setup.sh
```

### 4. Run Backend
```bash
cd backend
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

## 🌐 Access Points

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API File**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Solr Admin**: [http://localhost:8983/solr](http://localhost:8983/solr)

## Cleaning Up
To stop Docker containers:
```bash
docker-compose down
```
