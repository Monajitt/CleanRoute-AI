"""
Alias management command for initializing/ingesting the RAG knowledge base.
Usage:
    python manage.py init_rag [--force]
"""

from django.core.management.base import BaseCommand
from rag.ingest import ingest_knowledge_base


class Command(BaseCommand):
    help = "Initializes local ChromaDB vector store from tracked Markdown knowledge base."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reset existing vector collection before re-indexing",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        self.stdout.write("Initializing CleanRoute AI RAG knowledge base...")
        result = ingest_knowledge_base(force=force)
        if result.get("success"):
            docs = result.get("documents_read", 0)
            chunks = result.get("chunks_indexed", 0)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully initialized RAG: {docs} documents ({chunks} chunks indexed)."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR("Failed to initialize RAG knowledge base.")
            )
