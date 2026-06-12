"""Task 7 - Local reranking utilities."""

from .task4_chunking_indexing import cosine_similarity, text_to_embedding, tokenize


def _lexical_overlap(query: str, text: str) -> float:
    q_tokens = set(tokenize(query))
    if not q_tokens:
        return 0.0
    text_tokens = set(tokenize(text))
    return len(q_tokens & text_tokens) / len(q_tokens)


def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Offline cross-encoder stand-in using dense similarity + keyword overlap."""
    query_embedding = text_to_embedding(query)
    reranked = []
    for candidate in candidates:
        content = candidate.get("content", "")
        dense = cosine_similarity(query_embedding, text_to_embedding(content))
        overlap = _lexical_overlap(query, content)
        prior = float(candidate.get("score", 0.0))
        score = 0.55 * dense + 0.35 * overlap + 0.10 * prior
        reranked.append({**candidate, "score": float(score)})
    return sorted(reranked, key=lambda item: item["score"], reverse=True)[:top_k]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    selected: list[int] = []
    remaining = list(range(len(candidates)))
    embeddings = [
        candidate.get("embedding") or text_to_embedding(candidate.get("content", ""))
        for candidate in candidates
    ]

    while remaining and len(selected) < top_k:
        best_idx = remaining[0]
        best_score = float("-inf")
        for idx in remaining:
            relevance = cosine_similarity(query_embedding, embeddings[idx])
            diversity_penalty = max(
                (cosine_similarity(embeddings[idx], embeddings[sel]) for sel in selected),
                default=0.0,
            )
            score = lambda_param * relevance - (1 - lambda_param) * diversity_penalty
            if score > best_score:
                best_score = score
                best_idx = idx
        selected.append(best_idx)
        remaining.remove(best_idx)

    return [{**candidates[idx], "score": float(candidates[idx].get("score", 0.0))} for idx in selected]


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    rrf_scores: dict[str, float] = {}
    content_map: dict[str, dict] = {}
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item.get("content", "")
            if not key:
                continue
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            content_map[key] = item

    results = []
    for content, score in sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)[:top_k]:
        item = content_map[content].copy()
        item["score"] = float(score)
        results.append(item)
    return results


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "cross_encoder",
) -> list[dict]:
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    if method == "mmr":
        return rerank_mmr(text_to_embedding(query), candidates, top_k)
    if method == "rrf":
        return rerank_rrf([candidates], top_k)
    raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    demo = [
        {"content": "Dieu 248: Toi tang tru trai phep chat ma tuy", "score": 0.8, "metadata": {}},
        {"content": "Python programming", "score": 0.4, "metadata": {}},
    ]
    print(rerank("hinh phat ma tuy", demo))
