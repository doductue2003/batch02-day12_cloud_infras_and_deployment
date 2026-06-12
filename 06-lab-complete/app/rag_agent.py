"""Adapter đưa Day08 RAG pipeline vào API production của Lab 12."""

from __future__ import annotations

import sys
from pathlib import Path


RAG_PROJECT_DIR = Path(__file__).resolve().parent.parent / "Day08_RAG_pipeline_cohort2"
RAG_SRC_DIR = RAG_PROJECT_DIR / "src"

for path in (RAG_PROJECT_DIR, RAG_SRC_DIR):
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)

from src.task10_generation import generate_with_citation  # noqa: E402


def ask_rag_agent(question: str) -> dict:
    """Chạy RAG pipeline và trả về answer + metadata nguồn."""
    result = generate_with_citation(question, top_k=5, use_llm=True)
    sources = []
    for source in result.get("sources", [])[:5]:
        metadata = source.get("metadata", {})
        sources.append(
            {
                "source": metadata.get("source", "unknown"),
                "path": metadata.get("path", ""),
                "type": metadata.get("type", ""),
                "score": round(float(source.get("score", 0.0)), 4),
                "retrieval_source": source.get("source", result.get("retrieval_source", "hybrid")),
            }
        )

    return {
        "answer": result.get("answer", ""),
        "sources": sources,
        "used_llm": bool(result.get("used_llm", False)),
        "generation_mode": result.get("generation_mode", "unknown"),
        "retrieval_source": result.get("retrieval_source", "unknown"),
        "api_error": result.get("api_error"),
    }
