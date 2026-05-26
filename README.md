# AutoEmbed — MongoDB Automated Embedding Demo

This demo showcases how to build a semantic search and RAG workflow on MongoDB Atlas using **Automated Embedding** (Voyage AI models managed by MongoDB). It uses sample engineering simulation data (CFD, FEA, thermal, Monte Carlo, etc.) and four standalone Python scripts you can run in sequence.

## What you'll see

| Step | Script | What it demonstrates |
|------|--------|----------------------|
| 1 | `script_01_create_sample_data.py` | Load sample simulation documents into MongoDB |
| 2 | `script_02_create_auto_embed_index.py` | Create a Vector Search index with `autoEmbed` |
| 3 | `script_03_insert_and_search.py` | Insert a new doc, verify embedding, run vector search |
| 4 | `script_04_rag_chatbot.py` | RAG chatbot using Ollama + MongoDB semantic retrieval |

MongoDB generates and stores embeddings automatically — no manual embedding pipeline required. See the [Automated Embedding overview](https://www.mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/) and [Vector Search quick start](https://www.mongodb.com/docs/vector-search/tutorials/quick-start/?deployment-type=atlas&embedding=auto&interface=mongosh).

---

## Prerequisites

### MongoDB Atlas

- An Atlas cluster with **Vector Search** and **Automated Embedding** enabled (M0, Flex, or M10+).
- A database user and connection string with read/write access.
- Your IP address allowed in the Atlas access list.
- A **Model API Key** created in Atlas under **Model API Keys** (keys start with `al-`).

### Local tools

- Python 3.10+
- [Ollama](https://ollama.com/) (for script 4 only)

---

## Setup

### 1. Clone or copy the project

```bash
cd autoembed
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | Atlas connection string |
| `VOYAGE_API_KEY` | Model API key from Atlas → Model API Keys |
| `VOYAGE_EMBEDDINGS_URL` | Embedding REST endpoint (default: `https://ai.mongodb.com/v1/embeddings`) |
| `DATABASE_NAME` | Target database (default: `autoembed`) |
| `SCHEMA_VERSION` | `v1` (flat docs) or `v2` (nested under `data`) |
| `EMBEDDING_MODEL` | Voyage model for auto-embed index (default: `voyage-4`) |
| `VECTOR_INDEX_NAME` | Name of the Vector Search index |
| `OLLAMA_BASE_URL` | Ollama host (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Ollama model name (default: `llama3.2`) |

### 5. Start Ollama (for script 4)

```bash
ollama pull llama3.2
ollama serve
```

---

## Schema versions

Both layouts are supported. Pick one and use the same `--version` flag (or set `SCHEMA_VERSION` in `.env`) for all scripts.

### v1 — Flat documents (default)

Fields live at the root of each document. Auto-embed path: `description`.

```json
{
  "simulation_id": "SIM-001",
  "name": "Turbine Blade CFD",
  "description": "Computational fluid dynamics study of ...",
  "domain": "fluid_dynamics",
  "status": "completed"
}
```

Collection: `simulations_flat`

### v2 — Nested under `data`

All simulation fields are nested under a top-level `data` object. Auto-embed path: `data.description`.

```json
{
  "data": {
    "simulation_id": "SIM-001",
    "name": "Turbine Blade CFD",
    "description": "Computational fluid dynamics study of ...",
    "domain": "fluid_dynamics",
    "status": "completed"
  }
}
```

Collection: `simulations_nested`

---

## Run the demo

Run the scripts **in order**. Replace `v1` with `v2` if using the nested schema.

### Step 1 — Load sample data

Inserts six engineering simulation documents.

```bash
python script_01_create_sample_data.py --version v1 --drop
```

| Flag | Purpose |
|------|---------|
| `--version v1\|v2` | Schema layout (overrides `SCHEMA_VERSION` in `.env`) |
| `--drop` | Drop the collection before inserting (clean re-run) |

### Step 2 — Create the auto-embed index

Creates a Vector Search index with type `autoEmbed`. MongoDB will generate Voyage AI embeddings for the description field on all existing and future documents.

```bash
python script_02_create_auto_embed_index.py --version v1
```

The script waits until the index status is **READY**. Initial sync can take a few minutes depending on document count and rate limits.

| Flag | Purpose |
|------|---------|
| `--skip-wait` | Create the index but don't wait for READY |

**Index definition created:**

```json
{
  "fields": [
    {
      "type": "autoEmbed",
      "modality": "text",
      "path": "description",
      "model": "voyage-4"
    },
    {
      "type": "filter",
      "path": "simulation_id"
    },
    {
      "type": "filter",
      "path": "status"
    }
  ]
}
```

For v2, paths become `data.description`, `data.simulation_id`, and `data.status`.

### Step 3 — Insert, verify embedding, and search

Inserts a new hypersonic heat-shield simulation, checks whether MongoDB generated an embedding, and runs a natural-language vector search.

```bash
python script_03_insert_and_search.py --version v1
```

Custom query example:

```bash
python script_03_insert_and_search.py \
  --version v1 \
  --query "Which simulation models hypersonic re-entry and heat shield ablation?"
```

What happens:

1. A new simulation document is inserted (embeddings are generated automatically).
2. `has_embedding()` checks the internal `__mdb_internal_search` store.
3. A `$vectorSearch` query runs using **query text** — no manual embedding code.

### Step 4 — RAG chatbot

Interactive chatbot that retrieves relevant simulations via auto-embedding, then asks Ollama to answer using that context.

```bash
python script_04_rag_chatbot.py --version v1
```

Single-question mode:

```bash
python script_04_rag_chatbot.py \
  --version v1 \
  --question "What CFD simulations do we have for wind or airflow?"
```

Type `exit` or `quit` to leave interactive mode.

---

## Project structure

```
autoembed/
├── .env.example              # Environment variable template
├── config.py                 # Shared configuration
├── sample_data.py            # Sample simulation documents
├── embeddings.py             # Auto-embed helpers (search, embedding check, REST API)
├── script_01_create_sample_data.py
├── script_02_create_auto_embed_index.py
├── script_03_insert_and_search.py
├── script_04_rag_chatbot.py
├── requirements.txt
└── README.md
```

---

## Configuration reference

All scripts read from `.env` via `python-dotenv`. You can override the schema version per run with `--version v1|v2`.

### Embedding API (optional direct calls)

The helper `create_embeddings_via_api()` in `embeddings.py` calls the MongoDB embedding REST API directly:

```bash
POST https://ai.mongodb.com/v1/embeddings
Authorization: Bearer <VOYAGE_API_KEY>
Content-Type: application/json

{
  "input": "Sample text",
  "model": "voyage-4"
}
```

Atlas model keys (`al-...`) route to `ai.mongodb.com`. See [Accessing Voyage AI Models](https://www.mongodb.com/docs/voyageai/api-and-clients/).

Automated Embedding in scripts 2–4 does **not** require calling this API yourself — MongoDB handles embedding generation at index-time and query-time.

---

## Troubleshooting

### Index not READY / vector search returns no results

- Wait for script 2 to finish, or check index status in the Atlas UI under **Search Indexes**.
- Ensure script 1 ran against the same `--version` as script 2.
- Initial sync for auto-embed indexes can take several minutes.

### `VOYAGE_API_KEY` warning

- Create a Model API Key in Atlas and add it to `.env`.
- The key must also be valid for your cluster's Automated Embedding setup.

### Embedding not found after insert (script 3)

- Embeddings are generated asynchronously. The script polls for up to 120 seconds (`--embedding-timeout`).
- Vector search may still work for previously indexed documents even if the new doc's embedding is pending.

### Ollama connection error (script 4)

- Confirm Ollama is running: `ollama serve`
- Pull the model: `ollama pull llama3.2`
- Check `OLLAMA_BASE_URL` in `.env` (default: `http://localhost:11434`)

### Rate limits

Automated Embedding is subject to Atlas rate limits (tokens per minute / requests per minute). Large collections or frequent queries may be throttled. See [Rate Limits](https://www.mongodb.com/docs/vector-search/crud-embeddings/automated-embedding/).

---

## Re-running the demo

To start fresh with v1:

```bash
python script_01_create_sample_data.py --version v1 --drop
python script_02_create_auto_embed_index.py --version v1
python script_03_insert_and_search.py --version v1
python script_04_rag_chatbot.py --version v1
```

To try the nested schema instead, swap `v1` for `v2` consistently across all commands and set `SCHEMA_VERSION=v2` in `.env`.
