# -*- coding: utf-8 -*-
"""
Voice Memory - RAG index for 012's voice/style corpus.

WSP Compliance:
    WSP 77: Agent Coordination (feeds Digital Twin)
    WSP 84: Code Reuse (follows HoloIndex patterns)
    WSP 91: DAE Observability (bracket logging)

Purpose:
    Build and query a vector index over 012's comments and transcripts.
    Supports local-first operation with FAISS or TF-IDF fallback.

    V0.2.0: HoloIndex Integration - queries video transcripts via VideoContentIndex
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _env_truthy(name: str, default: str = "false") -> bool:
    """Parse common truthy env values."""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


# Lazy import HoloIndex VideoContentIndex
_video_index = None


def _probe_chromadb_health(ssd_path: str = "E:/HoloIndex") -> bool:
    """Probe ChromaDB video_segments collection in a subprocess.

    A corrupt HNSW index causes a native segfault that cannot be caught
    in-process.  Running the probe in a child process lets us detect the
    crash without taking down the caller.

    Uses subprocess (not multiprocessing) to avoid Windows spawn/pickle issues.
    """
    import subprocess
    import sys

    script = (
        "import chromadb, sys; "
        f"c = chromadb.PersistentClient(path=r'{ssd_path}/vectors'); "
        "col = c.get_collection('video_segments'); "
        "n = col.count(); "
        "print(n); "
        "sys.exit(0)"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            logger.warning(
                f"[VOICE-MEMORY] ChromaDB probe crashed (exit {result.returncode}) "
                f"— HNSW index likely corrupt. stderr: {result.stderr[:200]}"
            )
            return False
        count = result.stdout.strip()
        logger.info(f"[VOICE-MEMORY] ChromaDB probe OK: {count} video segments")
        return True
    except subprocess.TimeoutExpired:
        logger.warning("[VOICE-MEMORY] ChromaDB probe timed out (15s)")
        return False
    except Exception as e:
        logger.warning(f"[VOICE-MEMORY] ChromaDB probe failed: {e}")
        return False


def _get_video_index(*, allow_cold_init: bool = True, cancel_event=None):
    """Reuse the owned cache; optionally forbid cold initialization."""
    global _video_index
    if cancel_event is not None and cancel_event.is_set():
        return None
    if _video_index is None:
        if not allow_cold_init:
            logger.debug('[VOICE-MEMORY] Cold optional video memory skipped (ready-only)')
            return None
        try:
            # Subprocess probe: detect HNSW corruption before loading in-process
            healthy = _probe_chromadb_health()
            if cancel_event is not None and cancel_event.is_set():
                return None
            if not healthy:
                logger.warning("[VOICE-MEMORY] Skipping VideoContentIndex — ChromaDB probe failed")
                _video_index = False
                return None
            from holo_index.core.video_search import VideoContentIndex
            if cancel_event is not None and cancel_event.is_set():
                return None
            _video_index = VideoContentIndex()
            logger.info("[VOICE-MEMORY] HoloIndex VideoContentIndex connected")
        except ImportError:
            if cancel_event is not None and cancel_event.is_set():
                return None
            logger.debug("[VOICE-MEMORY] HoloIndex not available")
            _video_index = False
        except Exception as e:
            if cancel_event is not None and cancel_event.is_set():
                return None
            logger.warning(f"[VOICE-MEMORY] HoloIndex connection failed: {e}")
            _video_index = False
    if cancel_event is not None and cancel_event.is_set():
        return None
    return _video_index if _video_index else None


class VoiceMemory:
    """
    RAG index for 012's voice/style corpus.
    
    Supports:
    - FAISS with sentence-transformers (if available)
    - TF-IDF with sklearn fallback (always available)
    
    Example:
        >>> vm = VoiceMemory()
        >>> vm.build_index("data/voice_corpus/", "data/voice_index/")
        >>> results = vm.query("Japan visa process", k=5)
    """
    
    def __init__(self, index_dir: Optional[str] = None, include_videos: bool = True):
        """
        Initialize voice memory.

        Args:
            index_dir: Directory containing built index (None to build fresh)
            include_videos: If True, also search HoloIndex video transcripts (default True)
        """
        self.index_dir = Path(index_dir) if index_dir else None
        self.documents: List[Dict[str, Any]] = []
        self.embeddings = None
        self.vectorizer = None
        self.index = None
        self._use_faiss = False
        self.include_videos = include_videos and _env_truthy("VOICE_MEMORY_VIDEO_INDEX", "true")

        # Try to load existing index
        if self.index_dir and self.index_dir.exists():
            self._load_index()
    
    def _detect_backend(self) -> str:
        """Detect available vector backend."""
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
            self._use_faiss = True
            return "faiss"
        except ImportError:
            self._use_faiss = False
            return "tfidf"
    
    def build_index(self, corpus_dir: str, index_dir: str) -> int:
        """
        Build vector index from corpus.
        
        Args:
            corpus_dir: Directory containing corpus files (JSON/TXT)
            index_dir: Directory to save index
            
        Returns:
            Number of documents indexed
        """
        corpus_path = Path(corpus_dir)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Load documents
        self.documents = []
        
        # Load JSON files
        for json_file in corpus_path.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Handle various formats
                if isinstance(data, list):
                    for item in data:
                        self._add_document(item, str(json_file))
                elif isinstance(data, dict):
                    self._add_document(data, str(json_file))
            except Exception as e:
                logger.warning(f"[VOICE-MEMORY] Failed to load {json_file}: {e}")
        
        # Load text files
        for txt_file in corpus_path.glob("*.txt"):
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                
                if text:
                    self.documents.append({
                        "text": text,
                        "source_id": txt_file.stem,
                        "source_type": "comment",
                        "file": str(txt_file),
                    })
            except Exception as e:
                logger.warning(f"[VOICE-MEMORY] Failed to load {txt_file}: {e}")
        
        if not self.documents:
            logger.warning("[VOICE-MEMORY] No documents found in corpus")
            return 0
        
        # Build index based on available backend
        backend = self._detect_backend()
        logger.info(f"[VOICE-MEMORY] Building index with {backend} backend")
        
        if self._use_faiss:
            self._build_faiss_index()
        else:
            self._build_tfidf_index()
        
        # Save metadata
        self._save_index()
        
        logger.info(f"[VOICE-MEMORY] Indexed {len(self.documents)} documents")
        return len(self.documents)
    
    def _add_document(self, item: Dict[str, Any], source_file: str) -> None:
        """Add a document from parsed JSON."""
        text = item.get("text") or item.get("content") or item.get("comment", "")
        if not text:
            return
        
        self.documents.append({
            "text": text,
            "source_id": item.get("id", item.get("video_id", source_file)),
            "source_type": item.get("type", "comment"),
            "video_id": item.get("video_id"),
            "timestamp": item.get("t_start") or item.get("timestamp"),
            "url": item.get("url"),
            "tags": item.get("tags", []),
            "file": source_file,
        })
    
    def _build_faiss_index(self) -> None:
        """Build FAISS index with sentence-transformers."""
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
        
        # Use lightweight model
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        texts = [doc["text"] for doc in self.documents]
        self.embeddings = model.encode(texts, show_progress_bar=True)
        
        # Build FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine
        
        # Normalize for cosine similarity
        faiss.normalize_L2(self.embeddings)
        self.index.add(self.embeddings)
        
        self._model = model
    
    def _build_tfidf_index(self) -> None:
        """Build TF-IDF index with sklearn."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        texts = [doc["text"] for doc in self.documents]
        
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words="english",
            ngram_range=(1, 2)
        )
        
        self.embeddings = self.vectorizer.fit_transform(texts)
    
    def _save_index(self) -> None:
        """Save index to disk."""
        if not self.index_dir:
            return
        
        # Save documents metadata
        meta_file = self.index_dir / "documents.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
        
        # Save vectorizer for TF-IDF
        if self.vectorizer:
            import pickle
            vec_file = self.index_dir / "vectorizer.pkl"
            with open(vec_file, "wb") as f:
                pickle.dump(self.vectorizer, f)
        
        logger.info(f"[VOICE-MEMORY] Index saved to {self.index_dir}")
    
    def _load_index(self) -> bool:
        """Load index from disk."""
        if not self.index_dir:
            return False
        
        meta_file = self.index_dir / "documents.json"
        if not meta_file.exists():
            return False
        
        # Load documents
        with open(meta_file, "r", encoding="utf-8") as f:
            self.documents = json.load(f)
        
        # Try to load vectorizer
        vec_file = self.index_dir / "vectorizer.pkl"
        if vec_file.exists():
            import pickle
            with open(vec_file, "rb") as f:
                self.vectorizer = pickle.load(f)
            
            # Rebuild embeddings
            texts = [doc["text"] for doc in self.documents]
            self.embeddings = self.vectorizer.transform(texts)
        
        logger.info(f"[VOICE-MEMORY] Loaded {len(self.documents)} documents")
        return True
    
    def query(self, text: str, k: int = 5, *, allow_cold_init: bool = True,
              cancel_event=None) -> List[Dict[str, Any]]:
        """
        Query voice memory for similar snippets (hybrid: local + HoloIndex).

        Args:
            text: Query text
            k: Number of results
            allow_cold_init: False reuses only an existing video index/model.
            cancel_event: Optional cooperative cancellation between stages.

        Returns:
            List of {text, source_id, source_type, score, ...}
        """
        if cancel_event is not None and cancel_event.is_set():
            return []
        results = []

        # 1. Query local corpus (comments)
        if self.documents:
            if self._use_faiss and hasattr(self, "_model"):
                results.extend(self._query_faiss(text, k))
            elif self.vectorizer:
                results.extend(self._query_tfidf(text, k))

        if cancel_event is not None and cancel_event.is_set():
            return []
        # 2. Query HoloIndex video transcripts (if enabled)
        if self.include_videos:
            if allow_cold_init and cancel_event is None:
                video_results = self._query_holoindex(text, k)
            else:
                video_results = self._query_holoindex(
                    text, k, allow_cold_init=allow_cold_init, cancel_event=cancel_event)
            results.extend(video_results)
        if cancel_event is not None and cancel_event.is_set():
            return []

        # 3. Sort by score and dedupe
        results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)

        # Dedupe by text (keep highest score)
        seen_texts = set()
        deduped = []
        for r in results:
            text_key = r.get("text", "")[:100]  # First 100 chars as key
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                deduped.append(r)

        final_results = deduped[:k]
        if final_results:
            source_types = [r.get("source_type", "?") for r in final_results]
            logger.info(f"[VOICE-MEMORY] Query returned {len(final_results)} results | sources: {set(source_types)}")

        return final_results

    def _query_holoindex(self, text: str, k: int, *, allow_cold_init: bool = True,
                         cancel_event=None) -> List[Dict[str, Any]]:
        """Query HoloIndex VideoContentIndex for video transcripts."""
        if allow_cold_init and cancel_event is None:
            video_index = _get_video_index()
        else:
            video_index = _get_video_index(allow_cold_init=allow_cold_init, cancel_event=cancel_event)
        if not video_index:
            return []
        if cancel_event is not None and cancel_event.is_set():
            return []

        try:
            if allow_cold_init and cancel_event is None:
                matches = video_index.search(text, k=k)
            else:
                matches = video_index.search(text, k=k, allow_cold_init=allow_cold_init,
                                             cancel_event=cancel_event)
            if cancel_event is not None and cancel_event.is_set():
                return []
            results = []
            for match in matches:
                results.append({
                    "text": match.content,
                    "source_id": match.video_id,
                    "source_type": "video_transcript",
                    "video_id": match.video_id,
                    "url": match.url,
                    "timestamp": match.start_time,
                    "speaker": match.speaker,
                    "topics": match.topics,
                    "channel": match.channel,
                    "score": match.similarity,
                })
            logger.debug(f"[VOICE-MEMORY] HoloIndex returned {len(results)} video segments")
            return results
        except Exception as e:
            logger.warning(f"[VOICE-MEMORY] HoloIndex query failed: {e}")
            return []
    
    def _query_faiss(self, text: str, k: int) -> List[Dict[str, Any]]:
        """Query using FAISS."""
        import faiss
        import numpy as np
        
        query_embedding = self._model.encode([text])
        faiss.normalize_L2(query_embedding)
        
        scores, indices = self.index.search(query_embedding, min(k, len(self.documents)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                doc = self.documents[idx].copy()
                doc["score"] = float(score)
                results.append(doc)
        
        return results
    
    def _query_tfidf(self, text: str, k: int) -> List[Dict[str, Any]]:
        """Query using TF-IDF cosine similarity."""
        from sklearn.metrics.pairwise import cosine_similarity
        
        query_vec = self.vectorizer.transform([text])
        similarities = cosine_similarity(query_vec, self.embeddings)[0]
        
        # Get top-k indices
        top_indices = similarities.argsort()[-k:][::-1]
        
        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc["score"] = float(similarities[idx])
            results.append(doc)
        
        return results
    
    def add_document(
        self,
        text: str,
        source_id: str,
        source_type: str = "comment",
        **metadata
    ) -> None:
        """Add a single document to the index."""
        doc = {
            "text": text,
            "source_id": source_id,
            "source_type": source_type,
            **metadata
        }
        self.documents.append(doc)
        
        # Rebuild index if vectorizer exists
        if self.vectorizer:
            texts = [d["text"] for d in self.documents]
            self.embeddings = self.vectorizer.fit_transform(texts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics (including HoloIndex if enabled)."""
        source_types = {}
        for doc in self.documents:
            st = doc.get("source_type", "unknown")
            source_types[st] = source_types.get(st, 0) + 1

        stats = {
            "total_documents": len(self.documents),
            "source_types": source_types,
            "backend": "faiss" if self._use_faiss else "tfidf",
            "index_dir": str(self.index_dir) if self.index_dir else None,
            "include_videos": self.include_videos,
        }

        # Add HoloIndex stats if enabled
        if self.include_videos:
            video_index = _get_video_index()
            if video_index:
                try:
                    stats["holoindex_segments"] = video_index.collection.count()
                    stats["holoindex_connected"] = True
                except Exception:
                    stats["holoindex_connected"] = False
            else:
                stats["holoindex_connected"] = False

        return stats


# =============================================================================
# Quick Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Voice Memory Test")
    print("=" * 60)
    
    import tempfile
    
    # Create test corpus
    with tempfile.TemporaryDirectory() as corpus_dir:
        with tempfile.TemporaryDirectory() as index_dir:
            # Write sample data
            sample = [
                {"text": "Japan visa requires a sponsor company.", "id": "c1"},
                {"text": "Starting a business in Japan needs capital.", "id": "c2"},
                {"text": "Tokyo is great for startups.", "id": "c3"},
            ]
            
            with open(f"{corpus_dir}/sample.json", "w") as f:
                json.dump(sample, f)
            
            # Build and query
            vm = VoiceMemory()
            count = vm.build_index(corpus_dir, index_dir)
            print(f"Indexed: {count} documents")
            
            results = vm.query("How do I get a visa for Japan?", k=2)
            print(f"Query results: {len(results)}")
            for r in results:
                print(f"  - {r['text'][:50]}... (score: {r['score']:.3f})")
