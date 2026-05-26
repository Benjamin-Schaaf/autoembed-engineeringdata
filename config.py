"""Shared configuration loaded from environment variables."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your values.", file=sys.stderr)
        sys.exit(1)
    return value


MONGODB_URI = os.getenv("MONGODB_URI", "")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
VOYAGE_EMBEDDINGS_URL = os.getenv(
    "VOYAGE_EMBEDDINGS_URL", "https://ai.mongodb.com/v1/embeddings"
).rstrip("/")

DATABASE_NAME = os.getenv("DATABASE_NAME", "autoembed")
SCHEMA_VERSION = os.getenv("SCHEMA_VERSION", "v1").lower()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-4")
VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "simulation_auto_embed_index")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def ollama_chat_base_url() -> str:
    """Return Ollama host base URL (without /v1) for native /api/chat calls."""
    base = OLLAMA_BASE_URL.rstrip("/")
    if base.endswith("/v1"):
        return base[:-3]
    return base

MV_DATABASE = "__mdb_internal_search"


def schema_settings(version: str | None = None) -> dict[str, str]:
    """Return collection name and auto-embed field path for a schema version."""
    version = (version or SCHEMA_VERSION).lower()
    if version == "v2":
        return {
            "version": "v2",
            "collection": os.getenv("COLLECTION_NAME", "simulations_nested"),
            "embed_path": "data.description",
        }
    if version != "v1":
        raise ValueError(f"Unsupported schema version: {version!r}. Use 'v1' or 'v2'.")
    return {
        "version": "v1",
        "collection": os.getenv("COLLECTION_NAME", "simulations_flat"),
        "embed_path": "description",
    }


def validate_mongodb_config() -> None:
    _require("MONGODB_URI")


def validate_voyage_config() -> None:
    if not VOYAGE_API_KEY:
        print(
            "Warning: VOYAGE_API_KEY is not set. Automated Embedding requires a "
            "model API key from Atlas (Model API Keys).",
            file=sys.stderr,
        )
    if not VOYAGE_EMBEDDINGS_URL:
        print("Warning: VOYAGE_EMBEDDINGS_URL is not set.", file=sys.stderr)


# Backwards-compatible alias
validate_voyage_key_present = validate_voyage_config
