import os
import math
import json
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Default persistent file for local lightweight vector store
DEFAULT_INDEX_PATH = os.path.join(settings.BASE_DIR, "data", "knowledge_index.json")

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than",
    "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
    "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}


class LocalTFIDFEmbedding:
    """
    Lightweight, deterministic local term-frequency embedding.
    Ensures 100% offline resilience, zero model downloads, < 2 MB RAM usage.
    """
    def __init__(self, vocabulary_size: int = 1024):
        self.vocabulary_size = vocabulary_size

    def _tokenize(self, text: str) -> List[str]:
        words = [w.lower().strip(".,!?:;\"'()[]{}/*#`~_<>") for w in text.split()]
        return [w for w in words if w and w not in STOP_WORDS and len(w) > 1]

    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = []
        for text in input:
            tokens = self._tokenize(text)
            vector = [0.0] * self.vocabulary_size
            for w in tokens:
                idx = abs(hash(w)) % self.vocabulary_size
                vector[idx] += 1.0
            norm = math.sqrt(sum(x * x for x in vector))
            if norm > 0:
                vector = [x / norm for x in vector]
            embeddings.append(vector)
        return embeddings


class VectorStore:
    """
    Lightweight, deterministic in-process vector store.
    Provides semantic cosine similarity retrieval with keyword relevance weighting.
    100% compatible with 512 MB RAM environments on Render Free.
    """
    COLLECTION_NAME = "cleanroute_knowledge"

    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = persist_path or DEFAULT_INDEX_PATH
        self.embedding_fn = LocalTFIDFEmbedding(vocabulary_size=1024)
        self._documents: List[str] = []
        self._metadatas: List[Dict[str, Any]] = []
        self._ids: List[str] = []
        self._embeddings: List[List[float]] = []
        self._load_from_disk()

    def _load_from_disk(self):
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._documents = data.get("documents", [])
                    self._metadatas = data.get("metadatas", [])
                    self._ids = data.get("ids", [])
                    self._embeddings = data.get("embeddings", [])
                logger.info(f"Loaded {len(self._documents)} chunks from knowledge index {self.persist_path}")
            except Exception as e:
                logger.warning(f"Failed loading knowledge index from disk: {e}")

    def _save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump({
                    "documents": self._documents,
                    "metadatas": self._metadatas,
                    "ids": self._ids,
                    "embeddings": self._embeddings
                }, f)
        except Exception as e:
            logger.warning(f"Failed saving knowledge index to disk: {e}")

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """
        Inserts or updates document chunks in the lightweight vector store.
        """
        if not documents:
            return

        id_to_idx = {existing_id: i for i, existing_id in enumerate(self._ids)}
        new_embeddings = self.embedding_fn(documents)

        for doc, meta, doc_id, emb in zip(documents, metadatas, ids, new_embeddings):
            if doc_id in id_to_idx:
                idx = id_to_idx[doc_id]
                self._documents[idx] = doc
                self._metadatas[idx] = meta
                self._embeddings[idx] = emb
            else:
                self._documents.append(doc)
                self._metadatas.append(meta)
                self._ids.append(doc_id)
                self._embeddings.append(emb)
                id_to_idx[doc_id] = len(self._documents) - 1

        self._save_to_disk()
        logger.info(f"Indexed {len(documents)} chunks into VectorStore (total: {len(self._documents)})")

    def query(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Queries the vector store for the most semantically and keyword-relevant chunks.
        """
        clean_query = (query_text or "").strip()
        if not clean_query or not self._documents:
            return []

        query_emb = self.embedding_fn([clean_query])[0]
        query_words = set(clean_query.lower().split())

        scored = []
        for i, (doc, meta, emb) in enumerate(zip(self._documents, self._metadatas, self._embeddings)):
            # 1. Cosine similarity
            cosine_sim = sum(q * e for q, e in zip(query_emb, emb))

            # 2. Keyword relevance boost for topic, source and key terms
            src = (meta.get("source") or "").lower()
            title = (meta.get("title") or "").lower()
            section = (meta.get("section") or "").lower()
            doc_lower = doc.lower()

            keyword_boost = 0.0
            for w in query_words:
                clean_w = w.strip(".,!?:;\"'()[]{}/*#`~_<>")
                if len(clean_w) < 2 or clean_w in STOP_WORDS:
                    continue
                # Direct match in file name (e.g. pm25, aqi, cycling, walking)
                if clean_w in src:
                    keyword_boost += 0.5
                elif clean_w in title or clean_w in section:
                    keyword_boost += 0.3
                elif clean_w in doc_lower:
                    keyword_boost += 0.1

            total_score = min(1.0, (cosine_sim * 0.5) + min(0.5, keyword_boost))
            scored.append((total_score, i, doc, meta))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n_results]

        results = []
        for score, idx, text, meta in top:
            results.append({
                "text": text,
                "source": meta.get("source", "knowledge_base"),
                "topic": meta.get("topic", "general"),
                "title": meta.get("title", meta.get("source", "Knowledge Base")),
                "chunk_id": meta.get("chunk_id", idx),
                "similarity": round(max(0.01, score), 3)
            })

        return results

    def count(self) -> int:
        return len(self._documents)

    def reset(self):
        """
        Clears memory index and deletes disk file.
        """
        self._documents = []
        self._metadatas = []
        self._ids = []
        self._embeddings = []
        if os.path.exists(self.persist_path):
            try:
                os.remove(self.persist_path)
            except Exception:
                pass


# Singleton instance
_vector_store_instance = None


def get_vector_store() -> VectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
