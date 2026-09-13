"""
Django management command to ingest tracked Markdown knowledge base files
into the local ChromaDB vector store.
Usage:
    python manage.py ingest_knowledge [--force]
"""

from django.core.management.base import BaseCommand
from rag.ingest import ingest_knowledge_base


class Command(BaseCommand):
    help = "Indexes Markdown knowledge base into the local vector store for RAG."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reset existing vector collection before re-indexing",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        self.stdout.write("Starting CleanRoute AI knowledge base ingestion...")
        
        result = ingest_knowledge_base(force=force)
        
        if result.get("success"):
            docs = result.get("documents_read", 0)
            chunks = result.get("chunks_indexed", 0)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully ingested {docs} markdown documents ({chunks} semantic chunks indexed)."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR("Knowledge base ingestion failed. Check application logs for details.")
            )
