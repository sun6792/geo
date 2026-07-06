"""ChromaDB vector store integration for knowledge base semantic search."""

import uuid
from typing import Optional

from app.config import settings


class ChromaStore:
    """ChromaDB HTTP client wrapper for knowledge base embedding management.

    One collection per customer for tenant isolation.
    Collection naming: `kb_{customer_id}`
    """

    def __init__(self):
        self._host = settings.CHROMA_HOST
        self._port = settings.CHROMA_PORT
        self._client = None

    @property
    def client(self):
        """Lazy-init ChromaDB HTTP client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
                self._client = chromadb.HttpClient(
                    host=self._host, port=self._port,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            except Exception:
                # Fallback to in-memory client for development without Chroma server
                import chromadb
                self._client = chromadb.Client()
        return self._client

    def _collection_name(self, customer_id: uuid.UUID) -> str:
        return f"kb_{customer_id.hex}"

    def get_or_create_collection(self, customer_id: uuid.UUID):
        """Get or create a Chroma collection for a customer."""
        name = self._collection_name(customer_id)
        try:
            return self.client.get_collection(name)
        except Exception:
            return self.client.create_collection(
                name=name,
                metadata={"customer_id": str(customer_id), "hnsw:space": "cosine"},
            )

    async def add_asset_chunks(self, customer_id: uuid.UUID, asset_id: uuid.UUID,
                                asset_version: int, chunks: list[str],
                                embedding_model: str = "text-embedding-3-small") -> list[str]:
        """Add text chunks from an asset to the vector store.

        Returns list of Chroma document IDs for later reference.
        """
        collection = self.get_or_create_collection(customer_id)

        doc_ids = []
        metadatas = []
        for i, chunk_text in enumerate(chunks):
            doc_id = f"{asset_id.hex}_v{asset_version}_chunk{i}"
            doc_ids.append(doc_id)
            metadatas.append({
                "asset_id": str(asset_id),
                "asset_version": asset_version,
                "chunk_index": i,
                "embedding_model": embedding_model,
            })

        # Chroma handles embedding automatically when documents are added
        collection.add(
            documents=chunks,
            ids=doc_ids,
            metadatas=metadatas,
        )
        return doc_ids

    async def search(self, customer_id: uuid.UUID, query: str,
                      top_k: int = 10, threshold: float = 0.3) -> list[dict]:
        """Semantic search across the customer's knowledge base.

        Returns list of {asset_id, chunk_index, text, score, metadata}
        """
        collection = self.get_or_create_collection(customer_id)

        results = collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        items = []
        if results and results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                # Convert cosine distance to similarity score (0-1)
                similarity = 1 - distance if distance else 1.0
                if similarity >= threshold:
                    items.append({
                        "asset_id": metadata.get("asset_id", ""),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "text": doc,
                        "score": round(similarity, 4),
                        "metadata": metadata,
                    })
        return items

    async def delete_asset_chunks(self, customer_id: uuid.UUID, asset_id: uuid.UUID,
                                   asset_version: int, chunk_count: int = 100) -> None:
        """Remove all chunks for a specific asset version from the vector store.

        Args:
            chunk_count: Number of chunks to delete. Pass the actual count to ensure
                         all chunks are removed. Defaults to 100 for small assets.
        """
        collection = self.get_or_create_collection(customer_id)
        try:
            # Build IDs for known chunk count, with 50% buffer for safety
            max_chunks = max(chunk_count + 50, 200)
            doc_ids = [f"{asset_id.hex}_v{asset_version}_chunk{i}" for i in range(max_chunks)]
            collection.delete(ids=doc_ids)
        except Exception:
            pass  # Chroma handles non-existent IDs gracefully

    async def delete_collection(self, customer_id: uuid.UUID) -> None:
        """Delete entire vector collection for a customer."""
        try:
            self.client.delete_collection(self._collection_name(customer_id))
        except Exception:
            pass


# ── Text Chunking Utility ───────────────────────────────────────


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for embedding.

    Uses a simple recursive character split strategy:
    1. Split by double newlines (paragraphs)
    2. If still too long, split by single newlines
    3. If still too long, split by sentences
    4. If still too long, split by character count
    """
    if not text or not text.strip():
        return []

    chunk_size = chunk_size or settings.EMBEDDING_CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.EMBEDDING_CHUNK_OVERLAP

    # Step 1: Split by paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If a single paragraph exceeds chunk_size, split it further
            if len(para) > chunk_size:
                sub_chunks = _split_long_text(para, chunk_size, chunk_overlap)
                chunks.extend(sub_chunks)
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split a long text into overlapping character-level chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to break at a sentence boundary
        if end < len(text):
            # Look for sentence-ending punctuation within the last 100 chars
            search_start = max(end - 100, start)
            for punct in ["。", "！", "？", ".", "!", "?", "\n"]:
                pos = text.rfind(punct, search_start, end)
                if pos > search_start:
                    end = pos + 1
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > start else end

    return chunks


# Singleton instance
chroma_store = ChromaStore()
