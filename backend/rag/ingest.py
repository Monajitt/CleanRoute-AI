import os
import re
import logging
from typing import List, Dict, Any, Tuple
from django.conf import settings
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE_BASE_DIR = os.path.join(settings.BASE_DIR, "knowledge_base")


class KnowledgeBaseIngester:
    """
    Parses Markdown knowledge base documents, generates semantic chunks with metadata,
    and indexes them into the local vector store.
    """
    def __init__(self, kb_dir: str = None):
        self.kb_dir = kb_dir or DEFAULT_KNOWLEDGE_BASE_DIR
        self.vector_store = get_vector_store()

    def parse_markdown_file(self, file_path: str) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        Extracts document title, topic, and chunks from a markdown file.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        rel_path = os.path.relpath(file_path, self.kb_dir)
        parts = rel_path.replace("\\", "/").split("/")
        topic = parts[0] if len(parts) > 1 else "general"
        filename = parts[-1]

        # Extract primary title (# Title)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        doc_title = title_match.group(1).strip() if title_match else filename.replace(".md", "").replace("_", " ").title()

        # Split content by markdown section headers (## Section)
        raw_sections = re.split(r"(?m)(?=^##\s+)", content)
        chunks = []
        chunk_counter = 0

        for section in raw_sections:
            sec_text = section.strip()
            if not sec_text:
                continue

            # Check if section has a subsection title
            sub_match = re.search(r"^##\s+(.+)$", sec_text, re.MULTILINE)
            section_title = sub_match.group(1).strip() if sub_match else doc_title

            # Clean markdown formatting headers for plain text indexing while preserving content
            clean_text = sec_text
            # If section is very long (> 1500 chars), subdivide into paragraphs
            paragraphs = clean_text.split("\n\n")
            current_chunk = []
            current_len = 0

            for p in paragraphs:
                p_str = p.strip()
                if not p_str:
                    continue
                current_chunk.append(p_str)
                current_len += len(p_str)

                if current_len >= 500:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append({
                        "id": f"{filename.replace('.md', '')}_{chunk_counter}",
                        "text": chunk_text,
                        "metadata": {
                            "source": filename,
                            "rel_path": rel_path.replace("\\", "/"),
                            "topic": topic,
                            "title": doc_title,
                            "section": section_title,
                            "chunk_id": chunk_counter
                        }
                    })
                    chunk_counter += 1
                    current_chunk = []
                    current_len = 0

            if current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append({
                    "id": f"{filename.replace('.md', '')}_{chunk_counter}",
                    "text": chunk_text,
                    "metadata": {
                        "source": filename,
                        "rel_path": rel_path.replace("\\", "/"),
                        "topic": topic,
                        "title": doc_title,
                        "section": section_title,
                        "chunk_id": chunk_counter
                    }
                })
                chunk_counter += 1

        return filename, topic, chunks

    def ingest_all(self, force: bool = False) -> Dict[str, Any]:
        """
        Scans knowledge base directory and indexes all markdown files into vector store.
        """
        if not os.path.exists(self.kb_dir):
            logger.warning(f"Knowledge base directory {self.kb_dir} does not exist.")
            return {"success": False, "documents_read": 0, "chunks_indexed": 0}

        if force:
            self.vector_store.reset()

        all_documents = []
        all_metadatas = []
        all_ids = []
        doc_count = 0

        for root, _, files in os.walk(self.kb_dir):
            for file in sorted(files):
                if file.endswith(".md"):
                    full_path = os.path.join(root, file)
                    doc_count += 1
                    try:
                        filename, topic, chunks = self.parse_markdown_file(full_path)
                        for c in chunks:
                            all_documents.append(c["text"])
                            all_metadatas.append(c["metadata"])
                            all_ids.append(c["id"])
                    except Exception as e:
                        logger.error(f"Failed parsing knowledge file {full_path}: {e}")

        if all_documents:
            self.vector_store.add_documents(
                documents=all_documents,
                metadatas=all_metadatas,
                ids=all_ids
            )

        total_indexed = len(all_documents)
        logger.info(f"Knowledge base ingestion completed: {doc_count} docs read, {total_indexed} chunks indexed.")

        return {
            "success": True,
            "documents_read": doc_count,
            "chunks_indexed": total_indexed
        }


def ingest_knowledge_base(force: bool = False) -> Dict[str, Any]:
    ingester = KnowledgeBaseIngester()
    return ingester.ingest_all(force=force)
