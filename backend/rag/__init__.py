"""
CleanRoute AI — Local RAG (Retrieval-Augmented Generation) Module
"""

from .vector_store import VectorStore, get_vector_store
from .ingest import ingest_knowledge_base, KnowledgeBaseIngester
from .retriever import KnowledgeRetriever, retrieve_relevant_chunks
from .services import RAGService

__all__ = [
    "VectorStore",
    "get_vector_store",
    "ingest_knowledge_base",
    "KnowledgeBaseIngester",
    "KnowledgeRetriever",
    "retrieve_relevant_chunks",
    "RAGService"
]
