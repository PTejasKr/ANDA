"""
Vector Memory Module (Subsystem C)
Local vector memory and chunked RAG engine providing high-speed semantic retrieval.
Persistent storage, cosine distance ranking, and automatic text/row chunking.
"""

from __future__ import annotations
import hashlib
import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple


class VectorMemory:
    def __init__(self, storage_dir: Optional[str] = None, dim: int = 64):
        self.storage_dir = storage_dir or os.path.join("storage", "memory_store")
        self.index_file = os.path.join(self.storage_dir, "vector_index.json")
        self.dim = dim
        self.documents: List[Dict[str, Any]] = []
        os.makedirs(self.storage_dir, exist_ok=True)
        self.load_index()

    def _embed(self, text: str) -> List[float]:
        """
        Generates a normalized, deterministic dense embedding vector for the text.
        Preserves lexical and semantic keyword overlap with cosine distance.
        """
        vec = [0.0] * self.dim
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return vec

        for idx, token in enumerate(tokens):
            # Combined Murmur/MD5 hash projection across dimensions
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            pos = h % self.dim
            # Weight higher for unique / distinctive tokens
            weight = 1.0 + (math.log(len(token)) if len(token) > 2 else 0.5)
            vec[pos] += weight

            # Bi-gram capture for sequence context
            if idx + 1 < len(tokens):
                bigram = f"{token}_{tokens[idx+1]}"
                h_bi = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
                vec[h_bi % self.dim] += 1.5

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Computes dot product between two normalized vectors."""
        if len(v1) != len(v2) or not v1 or not v2:
            return 0.0
        return sum(a * b for a, b in zip(v1, v2))

    def chunk_text(self, text: str, chunk_size: int = 180, overlap: int = 30) -> List[str]:
        """Splits continuous text into sliding overlapping chunks."""
        words = text.split()
        if not words:
            return []
        chunks = []
        step = max(1, chunk_size - overlap)
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk: bool = True,
    ) -> int:
        """
        Chunks the document content, creates embedding vectors, and persists to index.
        Returns the number of indexed chunks.
        """
        metadata = metadata or {}
        chunks = self.chunk_text(content) if chunk else [content]
        indexed_count = 0

        for chunk_idx, chunk_text in enumerate(chunks):
            embedding = self._embed(chunk_text)
            entry = {
                "chunk_id": f"{doc_id}_c{chunk_idx}",
                "doc_id": doc_id,
                "text": chunk_text,
                "embedding": embedding,
                "metadata": {**metadata, "chunk_index": chunk_idx, "total_chunks": len(chunks)},
            }
            self.documents.append(entry)
            indexed_count += 1

        self.save_index()
        return indexed_count

    def index_spreadsheet_rows(self, doc_id: str, rows: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> int:
        """Indexes tabular spreadsheet records as individual searchable documents."""
        metadata = metadata or {}
        count = 0
        for idx, row in enumerate(rows):
            serialized = " | ".join(f"{k}: {v}" for k, v in row.items())
            embedding = self._embed(serialized)
            entry = {
                "chunk_id": f"{doc_id}_row{idx}",
                "doc_id": doc_id,
                "text": serialized,
                "embedding": embedding,
                "metadata": {**metadata, "row_index": idx, "data": row},
            }
            self.documents.append(entry)
            count += 1
        self.save_index()
        return count

    def query(self, query_text: str, top_k: int = 5, score_threshold: float = 0.05) -> List[Dict[str, Any]]:
        """Searches index using cosine similarity and returns top-k matching chunks."""
        q_vec = self._embed(query_text)
        scored_results: List[Tuple[float, Dict[str, Any]]] = []

        for item in self.documents:
            score = self._cosine_similarity(q_vec, item["embedding"])
            if score >= score_threshold:
                result_item = {
                    "score": round(score, 4),
                    "chunk_id": item["chunk_id"],
                    "doc_id": item["doc_id"],
                    "text": item["text"],
                    "metadata": item["metadata"],
                }
                scored_results.append((score, result_item))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in scored_results[:top_k]]

    def save_index(self) -> None:
        """Persists document vectors to disk."""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump({"dim": self.dim, "count": len(self.documents), "documents": self.documents}, f, indent=2)

    def load_index(self) -> None:
        """Loads index from disk if it exists."""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
            except Exception:
                self.documents = []
        else:
            self.documents = []

    def clear(self) -> None:
        """Resets the vector store."""
        self.documents = []
        self.save_index()
