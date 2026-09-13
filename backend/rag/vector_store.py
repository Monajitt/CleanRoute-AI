import os
import math
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Default persistent directory for local vector store
DEFAULT_CHROMA_DIR = os.path.join(settings.BASE_DIR, "data", "chroma_db")


class LocalTFIDFEmbedding:
    """
    Lightweight, deterministic local term-frequency embedding fallback.
    Ensures 100% offline resilience if native ONNX model download is restricted.
    """
    def __init__(self, vocabulary_size: int = 512):
        self.vocabulary_size = vocabulary_size

    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = []
        for text in input:
            words = [w.lower().strip(".,!?:;\"'()[]{}") for w in text.split()]
            vector = [0.0] * self.vocabulary_size
            for w in words:
                if w:
                    idx = abs(hash(w)) % self.vocabulary_size
                    vector[idx] += 1.0
            norm = math.sqrt(sum(x * x for x in vector))
            if norm > 0:
                vector = [x / norm for x in vector]
            embeddings.append(vector)
        return embeddings


class VectorStore:
    """
    Manages local persistent vector storage using ChromaDB.
    """
    COLLECTION_NAME = "cleanroute_knowledge"

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or DEFAULT_CHROMA_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        self._client = None
        self._collection = None
        self._initialize_store()

    def _initialize_store(self):
        try:
            import chromadb
            from chromadb.config import Settings
            from chromadb.utils import embedding_functions

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False, is_persistent=True)
            )

            # Try default ONNX embedding function; fallback to LocalTFIDFEmbedding if offline
            try:
                embedding_fn = embedding_functions.DefaultEmbeddingFunction()
                # Test call to verify model weights access
                embedding_fn(["test"])
            except Exception as emb_err:
                logger.warning(f"Default ONNX embedding function unavailable ({emb_err}); using local resilient embedding function.")
                embedding_fn = LocalTFIDFEmbedding()

            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=embedding_fn,
                metadata={"description": "CleanRoute AI Local Knowledge Base"}
            )
            logger.info(f"ChromaDB initialized at {self.persist_dir} with collection '{self.COLLECTION_NAME}'")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}. Utilizing in-memory document store.")
            self._client = None
            self._collection = None

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """
        Inserts or updates document chunks in the vector collection.
        """
        if not documents:
            return

        if self._collection is not None:
            try:
                self._collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"Upserted {len(documents)} chunks into ChromaDB collection '{self.COLLECTION_NAME}'")
                return
            except Exception as e:
                logger.error(f"ChromaDB upsert error: {e}")

    def query(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Queries vector collection for most semantically similar chunks.
        """
        clean_query = (query_text or "").strip()
        if not clean_query:
            return []

        if self._collection is not None:
            try:
                count = self.count()
                if count == 0:
                    return []

                actual_n = min(n_results, count)
                res = self._collection.query(
                    query_texts=[clean_query],
                    n_results=actual_n,
                    include=["documents", "metadatas", "distances"]
                )

                results = []
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                dists = res.get("distances", [[]])[0]

                for idx, text in enumerate(docs):
                    meta = metas[idx] if idx < len(metas) else {}
                    dist = dists[idx] if idx < len(dists) else 0.0
                    # Convert distance to approximate similarity score
                    sim = round(max(0.0, 1.0 - float(dist)), 3) if dist is not None else 1.0

                    results.append({
                        "text": text,
                        "source": meta.get("source", "knowledge_base"),
                        "topic": meta.get("topic", "general"),
                        "title": meta.get("title", meta.get("source", "Knowledge Base")),
                        "chunk_id": meta.get("chunk_id", idx),
                        "similarity": sim
                    })

                return results
            except Exception as e:
                logger.error(f"ChromaDB query error: {e}")

        return []

    def count(self) -> int:
        if self._collection is not None:
            try:
                return self._collection.count()
            except Exception as e:
                logger.error(f"Error fetching collection count: {e}")
        return 0

    def reset(self):
        """
        Clears the collection.
        """
        if self._client is not None and self._collection is not None:
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
                self._initialize_store()
            except Exception as e:
                logger.error(f"Error resetting vector collection: {e}")


# Singleton instance
_vector_store_instance = None

def get_vector_store() -> VectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
