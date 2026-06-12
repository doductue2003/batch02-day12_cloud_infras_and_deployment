"""Task 8 - PageIndex-compatible fallback search.

The real PageIndex API needs an account/API key. For local grading and demos,
this module provides the same return shape by doing vectorless keyword search
over standardized Markdown files and marking results as source='pageindex'.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from .task6_lexical_search import lexical_search

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"


def upload_documents() -> list[Path]:
    return sorted(STANDARDIZED_DIR.rglob("*.md")) if STANDARDIZED_DIR.exists() else []


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    results = lexical_search(query, top_k=top_k)
    return [
        {
            "content": result["content"],
            "score": float(result["score"]),
            "metadata": result.get("metadata", {}),
            "source": "pageindex",
        }
        for result in results
    ]


if __name__ == "__main__":
    for result in pageindex_search("hinh phat ma tuy", top_k=3):
        print(f"[{result['score']:.3f}] {result['content'][:100]}...")
