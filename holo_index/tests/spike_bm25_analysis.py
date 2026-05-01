# -*- coding: utf-8 -*-
"""HIA5: BM25 Hybrid Retrieval Analysis Spike

Test-only analysis to determine if BM25 would help failing sentinel queries.
NOT a production implementation - spike for decision-making only.

WSP 97: Truthful analysis of BM25 viability.
"""

import math
from collections import Counter
from typing import Dict, List, Tuple


def tokenize(text: str) -> List[str]:
    """Simple tokenizer for BM25 analysis."""
    import re
    return [t.lower() for t in re.findall(r'[a-z0-9_]+', text.lower()) if t]


class SimpleBM25:
    """Minimal BM25 implementation for analysis spike.

    Standard BM25 parameters:
    - k1 = 1.5 (term frequency saturation)
    - b = 0.75 (document length normalization)
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: List[List[str]] = []
        self.doc_freqs: Dict[str, int] = {}
        self.avg_dl: float = 0.0
        self.n_docs: int = 0
        self.idf_cache: Dict[str, float] = {}

    def fit(self, documents: List[str]) -> "SimpleBM25":
        """Fit BM25 on a corpus of documents."""
        self.corpus = [tokenize(doc) for doc in documents]
        self.n_docs = len(self.corpus)

        # Calculate document frequencies
        self.doc_freqs = {}
        total_len = 0
        for doc_tokens in self.corpus:
            total_len += len(doc_tokens)
            unique_tokens = set(doc_tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_dl = total_len / max(1, self.n_docs)

        # Pre-compute IDF values
        self.idf_cache = {}
        for token, df in self.doc_freqs.items():
            # IDF with smoothing
            self.idf_cache[token] = math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1)

        return self

    def score(self, query: str, doc_idx: int) -> float:
        """Compute BM25 score for a query against a specific document."""
        query_tokens = tokenize(query)
        doc_tokens = self.corpus[doc_idx]
        doc_len = len(doc_tokens)

        tf = Counter(doc_tokens)

        score = 0.0
        for token in query_tokens:
            if token not in self.idf_cache:
                continue  # OOV token

            idf = self.idf_cache[token]
            term_freq = tf.get(token, 0)

            # BM25 TF component with length normalization
            numerator = term_freq * (self.k1 + 1)
            denominator = term_freq + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_dl))

            score += idf * (numerator / denominator)

        return score

    def get_idf(self, token: str) -> float:
        """Get IDF for a token (for analysis)."""
        return self.idf_cache.get(token.lower(), 0.0)


def analyze_failing_queries():
    """Analyze whether BM25 would help the two failing HIA4B queries."""

    print("=" * 70)
    print("HIA5: BM25 Hybrid Retrieval Analysis Spike")
    print("=" * 70)

    # Simulate mini-corpus representing symbol collection paths/titles
    # These are representative documents that BM25 would score
    mini_corpus = [
        # Document 0: holoindex_plugin.py (correct target for query 2)
        "holoindex_plugin semantic code navigation HoloIndex integration plugin wre_master_orchestrator",

        # Document 1: openclaw_codebase_agent.py (current top-1 for query 2)
        "openclaw_codebase_agent codebase navigation code agent ai_gateway semantic search",

        # Document 2: search_engine.py (NOT INDEXED - correct target for query 1)
        "search_engine query execution search pipeline vector lexical holo_index core",

        # Document 3: holoindex_plugin (alternative)
        "holoindex holoindex_plugin wre plugin integration",

        # Document 4: random file
        "demurrage economics simulator tokens distribution",
    ]

    bm25 = SimpleBM25().fit(mini_corpus)

    print("\n1. IDF Analysis (rare terms get higher IDF)")
    print("-" * 50)
    key_terms = ["holoindex", "semantic", "code", "navigation", "search", "engine", "query", "execution"]
    for term in key_terms:
        idf = bm25.get_idf(term)
        df = bm25.doc_freqs.get(term.lower(), 0)
        print(f"  '{term}': IDF={idf:.3f}, DF={df}/{bm25.n_docs}")

    print("\n2. Query 2: 'HoloIndex semantic code navigation'")
    print("-" * 50)
    query2 = "HoloIndex semantic code navigation"
    scores = [(i, bm25.score(query2, i)) for i in range(len(mini_corpus))]
    scores.sort(key=lambda x: x[1], reverse=True)
    for idx, score in scores:
        doc_preview = mini_corpus[idx][:50] + "..."
        print(f"  Doc {idx}: BM25={score:.3f} | {doc_preview}")

    print("\n3. Query 1: 'search engine query execution'")
    print("-" * 50)
    query1 = "search engine query execution"
    scores = [(i, bm25.score(query1, i)) for i in range(len(mini_corpus))]
    scores.sort(key=lambda x: x[1], reverse=True)
    for idx, score in scores:
        doc_preview = mini_corpus[idx][:50] + "..."
        print(f"  Doc {idx}: BM25={score:.3f} | {doc_preview}")

    print("\n4. Analysis Summary")
    print("-" * 50)
    print("""
    Query 1 ("search engine query execution"):
    - Target: search_engine.py
    - Issue: search_engine.py is NOT in symbol index
    - BM25 Impact: NONE - cannot find unindexed documents
    - Fix: Index holo_index/core/ files

    Query 2 ("HoloIndex semantic code navigation"):
    - Target: holoindex_plugin.py
    - Issue: openclaw_codebase_agent.py ranks higher via semantic similarity
    - BM25 Analysis:
      * "holoindex" has high IDF (rare term)
      * BM25 correctly ranks holoindex_plugin.py higher
      * BUT: Current keyword scoring already gives +1.0 for path match
      * Real issue: Semantic similarity gap outweighs keyword boost
    - Alternatives:
      1. Increase path/title boost (simpler)
      2. Add exact name match boost like WSP number boost
      3. Gemma reranking for top-5 to top-1 promotion
    """)

    return {
        "query1_bm25_helps": False,  # Indexing issue
        "query2_bm25_helps": "partial",  # BM25 helps but simpler alternatives exist
        "recommended_action": "DEFER_BM25",
        "alternatives": [
            "Index holo_index/core/ in symbol collection",
            "Increase path/title keyword boost",
            "Add exact path substring boost for technical terms",
            "Consider Gemma reranking for top-5 to top-1"
        ]
    }


if __name__ == "__main__":
    result = analyze_failing_queries()
    print("\n5. Decision")
    print("-" * 50)
    print(f"  Recommended: {result['recommended_action']}")
