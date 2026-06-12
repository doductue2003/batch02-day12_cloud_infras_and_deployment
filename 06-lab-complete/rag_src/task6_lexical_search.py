"""Task 6 - Lexical search with BM25-compatible local fallback."""

import math

from .task4_chunking_indexing import load_or_build_chunks, tokenize

CORPUS: list[dict] = []


class SimpleBM25:
    def __init__(self, tokenized_corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.tokenized_corpus = tokenized_corpus
        self.k1 = k1
        self.b = b
        self.doc_lens = [len(doc) for doc in tokenized_corpus]
        self.avgdl = sum(self.doc_lens) / max(len(self.doc_lens), 1)
        self.doc_freq: dict[str, int] = {}
        for doc in tokenized_corpus:
            for token in set(doc):
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1
        self.n_docs = len(tokenized_corpus)

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = []
        for doc, doc_len in zip(self.tokenized_corpus, self.doc_lens):
            tf: dict[str, int] = {}
            for token in doc:
                tf[token] = tf.get(token, 0) + 1

            score = 0.0
            for token in query_tokens:
                if token not in tf:
                    continue
                df = self.doc_freq.get(token, 0)
                idf = math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))
                freq = tf[token]
                denom = freq + self.k1 * (1 - self.b + self.b * doc_len / (self.avgdl or 1))
                score += idf * (freq * (self.k1 + 1)) / denom
            scores.append(score)
        return scores


def _load_corpus() -> list[dict]:
    global CORPUS
    if not CORPUS:
        CORPUS = [
            {"content": chunk["content"], "metadata": chunk.get("metadata", {})}
            for chunk in load_or_build_chunks(with_embeddings=False)
        ]
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    tokenized_corpus = [tokenize(doc["content"]) for doc in corpus]
    try:
        from rank_bm25 import BM25Okapi

        return BM25Okapi(tokenized_corpus)
    except Exception:
        return SimpleBM25(tokenized_corpus)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    corpus = _load_corpus()
    if not corpus:
        return []
    bm25 = build_bm25_index(corpus)
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)

    results = []
    for idx, score in ranked[:top_k]:
        if float(score) <= 0:
            continue
        results.append(
            {
                "content": corpus[idx]["content"],
                "score": float(score),
                "metadata": corpus[idx].get("metadata", {}),
            }
        )
    return results


if __name__ == "__main__":
    for result in lexical_search("Dieu 248 ma tuy", top_k=5):
        print(f"[{result['score']:.3f}] {result['content'][:100]}...")
