# RAG_mul

Enterprise-style **RAG** (Retrieval-Augmented Generation) service built with **FastAPI**. It ingests **Word (.docx)** documents, indexes text in Elasticsearch and embeddings in ChromaDB , merges results with RRF, and generates answers via LLM api. **MySQL** stores document registry and related metadata.

## Features

- **Dual retrieval**: Chroma (semantic) + Elasticsearch (lexical), fused at the application layer with RRF.
- **Ingestion pipeline**: `.docx` parsing, chunking, embedding, dual-write to ES + Chroma, MySQL `document_registry` status tracking.
- **Q&A**: Hybrid retrieval → evidence packing → chat completion with citation-style prompts (Chinese-oriented system prompt; configurable models).

## Architecture

```
Client → FastAPI
           ├─ MySQL (document_registry, user profile tables, …)
           ├─ ChromaDB (vectors + chunk text in collection)
           ├─ Elasticsearch (BM25 on chunk text, `rag_chunks` index)
           └─ OpenAI-compatible API (embeddings + chat)
```

## Prerequisites

- **Docker** and **Docker Compose** (for MySQL, Elasticsearch, Chroma)
- **Python 3.11+** (3.13 is fine; project tested with venv)
- An **OpenAI API key** (or any OpenAI-compatible provider exposing `/v1/embeddings` and `/v1/chat/completions`)

## Quick start

### 1. Start infrastructure

From the repository root:

```bash
docker compose up -d
```

This starts:

| Service        | Default port | Purpose                          |
|----------------|-------------|-----------------------------------|
| MySQL 8.4      | 3306        | Registry, profiles, memory tables |
| Elasticsearch 8.14 | 9200   | Lexical index `rag_chunks`       |
| Chroma         | 8000        | Vector collection `rag_chunks`   |

MySQL runs initialization scripts in [`database/mysql/init/`](database/mysql/init/) **only on first volume creation**. To re-apply SQL after changing files, remove the MySQL volume or run migrations manually.

### 2. Create the Elasticsearch index

After Elasticsearch is healthy, create the index (idempotent):

**Windows (PowerShell)**

```powershell
.\scripts\init_elasticsearch.ps1
```

**Linux / macOS**

```bash
chmod +x scripts/init_elasticsearch.sh
./scripts/init_elasticsearch.sh
```

Optional: set `ES_URL` if Elasticsearch is not on `http://127.0.0.1:9200`.

### 3. Configure the application

Copy the example env file and set at least `OPENAI_API_KEY`:

```bash
cp .env.example .env
# Edit .env — see Environment variables below
```

### 4. Install Python dependencies

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Run the API

From the repository root (so `app` is importable):

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Environment variables

Loaded via **pydantic-settings** (`.env` in the project root). Common variables:

| Variable            | Description                                      | Default                    |
|---------------------|--------------------------------------------------|----------------------------|
| `MYSQL_HOST`        | MySQL host                                       | `127.0.0.1`                |
| `MYSQL_PORT`        | MySQL port                                       | `3306`                     |
| `MYSQL_USER`        | MySQL user                                       | `rag`                      |
| `MYSQL_PASSWORD`    | MySQL password                                   | `ragpass`                  |
| `MYSQL_DATABASE`    | Database name                                    | `rag_db`                   |
| `ES_URL`            | Elasticsearch base URL                           | `http://127.0.0.1:9200`    |
| `CHROMA_HOST`       | Chroma server host                               | `127.0.0.1`                |
| `CHROMA_PORT`       | Chroma server port                               | `8000`                     |
| `OPENAI_API_KEY`    | Required for ingest + RAG query                  | _(empty)_                  |
| `OPENAI_BASE_URL`   | OpenAI-compatible base URL                       | `https://api.openai.com/v1` |
| `EMBEDDING_MODEL`   | Embeddings model name                            | `text-embedding-3-small`  |
| `CHAT_MODEL`        | Chat model name                                  | `gpt-4o-mini`              |

Optional tuning (env names match [`app/config.py`](app/config.py) fields in `UPPER_SNAKE_CASE`): `CHUNK_MAX_CHARS`, `CHUNK_OVERLAP`, `RETRIEVE_K_VECTOR`, `RETRIEVE_K_LEXICAL`, `RRF_K`, `FUSION_TOP_N`, `CONTEXT_TOP_N`, `ES_INDEX`, `CHROMA_COLLECTION`.

## HTTP API

| Method | Path               | Description |
|--------|--------------------|---------------|
| `GET`  | `/`                | Service info and link to `/docs` |
| `GET`  | `/v1/health`       | Elasticsearch + Chroma checks; whether OpenAI key is set |
| `POST` | `/v1/ingest/word` | Multipart: `file` (`.docx`), optional form field `doc_id` |
| `POST` | `/v1/rag/query`   | JSON: `{ "question": "...", "doc_id": null }` — scope search to one document when `doc_id` is set |

Ingest and RAG endpoints return **503** if `OPENAI_API_KEY` is missing (embeddings and chat are required for the current implementation).

## Project layout

```
app/
  main.py              # FastAPI app + lifespan
  config.py            # Settings
  deps.py              # DB session + RAG orchestrator DI
  db/                  # SQLAlchemy session + models
  routers/             # health, ingest, rag
  schemas/             # Pydantic request/response models
  services/            # parsing, chunking, ES, Chroma, RRF, orchestration
database/
  mysql/init/          # SQL bootstrap for MySQL
  es/rag_chunks.index.json  # ES index definition used by init scripts
scripts/
  init_elasticsearch.ps1
  init_elasticsearch.sh
docker-compose.yml
requirements.txt
.env.example
```

## Operational notes

- **Embedding dimension** must stay consistent for a given Chroma collection. If you change `EMBEDDING_MODEL`, recreate the Chroma collection / re-index from scratch.
- **Elasticsearch analyzers**: the default index uses a simple `standard`-style analyzer. For better Chinese tokenization, add the IK plugin and update the index mapping, then reindex.
- **Chroma client vs server**: `docker-compose.yml` pins a Chroma server image; the Python `chromadb` client should be compatible with that server line. Upgrade both together if you hit API mismatches.

## License

Specify your license here (e.g. MIT) if you publish this repository.
