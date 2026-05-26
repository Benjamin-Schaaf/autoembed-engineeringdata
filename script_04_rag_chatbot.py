#!/usr/bin/env python3
"""
Script 4 — RAG chatbot over simulation data using Ollama + MongoDB auto-embedding.

Flow:
  1. User asks a question
  2. MongoDB auto-embeds the query and runs $vectorSearch
  3. Retrieved simulation context is sent to Ollama for a grounded answer

Usage:
  python script_04_rag_chatbot.py
  python script_04_rag_chatbot.py --question "What CFD simulations do we have?"
"""

from __future__ import annotations

import argparse
import sys

import requests
from pymongo import MongoClient

from config import (
    DATABASE_NAME,
    EMBEDDING_MODEL,
    OLLAMA_MODEL,
    VECTOR_INDEX_NAME,
    ollama_chat_base_url,
    validate_mongodb_config,
)
from embeddings import vector_search


SYSTEM_PROMPT = """You are a helpful engineering simulation assistant.
Answer the user's question using ONLY the simulation context provided below.
If the context does not contain enough information, say so clearly.
Cite simulation names and IDs when relevant. Be concise and technical."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RAG chatbot: Ollama LLM + MongoDB auto-embedding vector search."
    )
    parser.add_argument(
        "--version",
        choices=["v1", "v2"],
        default=None,
        help="Schema version (default: SCHEMA_VERSION from .env)",
    )
    parser.add_argument(
        "--question",
        default=None,
        help="Single question mode (omit for interactive chat)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Number of simulations to retrieve for context",
    )
    return parser.parse_args()


def _field(doc: dict, key: str, default: str = "") -> str:
    if key in doc:
        return str(doc[key])
    return str(doc.get("data", {}).get(key, default))


def format_context(doc: dict, score: float) -> str:
    return (
        f"- simulation_id: {_field(doc, 'simulation_id')}\n"
        f"  name: {_field(doc, 'name')}\n"
        f"  domain: {_field(doc, 'domain')}\n"
        f"  status: {_field(doc, 'status')}\n"
        f"  relevance_score: {score:.4f}\n"
        f"  description: {_field(doc, 'description')}"
    )


def retrieve_context(collection, question: str, embed_path: str, top_k: int) -> str:
    hits = vector_search(
        collection,
        index_name=VECTOR_INDEX_NAME,
        embed_path=embed_path,
        query_text=question,
        embedding_model=EMBEDDING_MODEL,
        limit=top_k,
    )
    if not hits:
        return "No matching simulations found in the database."

    blocks = []
    for hit in hits:
        doc = collection.find_one({"_id": hit["_id"]})
        if doc:
            blocks.append(format_context(doc, hit["score"]))
    return "\n\n".join(blocks)


def ask_ollama(question: str, context: str) -> str:
    user_message = f"Context:\n{context}\n\nQuestion: {question}"
    response = requests.post(
        f"{ollama_chat_base_url()}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def answer_question(collection, embed_path: str, question: str, top_k: int) -> str:
    context = retrieve_context(collection, question, embed_path, top_k)
    return ask_ollama(question, context)


def main() -> int:
    from config import MONGODB_URI, schema_settings

    args = parse_args()
    validate_mongodb_config()

    settings = schema_settings(args.version)
    client = MongoClient(MONGODB_URI)
    collection = client[DATABASE_NAME][settings["collection"]]
    embed_path = settings["embed_path"]

    print("AutoEmbed RAG Chatbot")
    print(f"  MongoDB : {DATABASE_NAME}.{settings['collection']}")
    print(f"  Ollama  : {ollama_chat_base_url()} (model={OLLAMA_MODEL})")
    print(f"  Index   : {VECTOR_INDEX_NAME} on {embed_path}")
    print("Type 'exit' or 'quit' to stop.\n")

    def handle(question: str) -> None:
        question = question.strip()
        if not question:
            return
        try:
            answer = answer_question(collection, embed_path, question, args.top_k)
            print(f"\nAssistant: {answer}\n")
        except requests.RequestException as exc:
            print(f"\nOllama error: {exc}", file=sys.stderr)
            print(
                f"Ensure Ollama is running at {ollama_chat_base_url()} and model "
                f"{OLLAMA_MODEL!r} is pulled (ollama pull {OLLAMA_MODEL}).\n",
                file=sys.stderr,
            )

    if args.question:
        handle(args.question)
        return 0

    while True:
        try:
            question = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if question.strip().lower() in {"exit", "quit"}:
            print("Bye.")
            break
        handle(question)

    return 0


if __name__ == "__main__":
    sys.exit(main())
