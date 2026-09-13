import logging
from typing import List, Dict, Any
from .vector_store import get_vector_store
from .ingest import ingest_knowledge_base

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """
    Handles semantic similarity retrieval against the CleanRoute AI local vector store.
    """
    def __init__(self):
        self.vector_store = get_vector_store()
        self._ensure_knowledge_loaded()

    def _ensure_knowledge_loaded(self):
        """
        Auto-ingests knowledge base if vector collection is currently empty.
        """
        try:
            if self.vector_store.count() == 0:
                logger.info("Vector store is empty; auto-ingesting knowledge base markdown files...")
                ingest_knowledge_base()
        except Exception as e:
            logger.error(f"Error ensuring knowledge base is loaded: {e}")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most relevant knowledge chunks matching user query.
        """
        clean_query = (query or "").strip()
        if not clean_query:
            return []

        self._ensure_knowledge_loaded()

        try:
            results = self.vector_store.query(clean_query, n_results=top_k)
            return results
        except Exception as e:
            logger.error(f"Retriever error for query '{query}': {e}")
            return []


# Module helper
def retrieve_relevant_chunks(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    retriever = KnowledgeRetriever()
    return retriever.retrieve(query, top_k=top_k)
