"""Task 5 - Semantic search over local hashed embeddings."""

from .task4_chunking_indexing import cosine_similarity, load_or_build_chunks, text_to_embedding


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    query_embedding = text_to_embedding(query)
    chunks = load_or_build_chunks(with_embeddings=True)
    results = []
    for chunk in chunks:
        embedding = chunk.get("embedding") or text_to_embedding(chunk["content"])
        score = cosine_similarity(query_embedding, embedding)
        if score > 0:
            results.append(
                {
                    "content": chunk["content"],
                    "score": float(score),
                    "metadata": chunk.get("metadata", {}),
                }
            )
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    for result in semantic_search("hinh phat ma tuy", top_k=5):
        print(f"[{result['score']:.3f}] {result['content'][:100]}...")
