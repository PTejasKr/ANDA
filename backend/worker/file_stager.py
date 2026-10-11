"""
File Stager Module (Subsystem A)
Monitors incoming ingest paths, determines semantic file classification,
and stages files into categorized directories with forensic metadata.
"""

from __future__ import annotations
import os
import shutil
import time
from typing import Dict, List, Optional, Tuple


class FileStager:
    CATEGORIES = {
        "receipts": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"],
        "financial_reports": [".pdf"],
        "spreadsheets": [".xlsx", ".xls", ".csv", ".tsv"],
        "general": [".txt", ".json", ".md", ".log"],
    }

    def __init__(self, base_storage_dir: Optional[str] = None):
        self.base_dir = base_storage_dir or "storage"
        self.ingest_dir = os.path.join(self.base_dir, "ingest")
        self.staging_dir = os.path.join(self.base_dir, "staging")
        
        # Ensure category folders exist
        for cat in self.CATEGORIES.keys():
            os.makedirs(os.path.join(self.staging_dir, cat), exist_ok=True)
        os.makedirs(self.ingest_dir, exist_ok=True)

    def classify_file(self, filename: str, content_peek: bytes = b"") -> str:
        """Determines destination category based on extension and semantic tags."""
        name_lower = filename.lower()
        ext = os.path.splitext(name_lower)[1]

        # Semantic keywords override
        if any(term in name_lower for term in ("receipt", "invoice", "bill", "ticket")):
            return "receipts"
        if any(term in name_lower for term in ("financial", "report", "quarter", "10-k", "balance", "earnings")):
            return "financial_reports"
        if ext in (".xlsx", ".csv", ".tsv"):
            return "spreadsheets"

        # Content-based inspection
        try:
            content_str = content_peek[:1024].decode("utf-8", errors="ignore").lower()
            if any(term in content_str for term in ("subtotal", "tax", "payment method", "store #", "total usd")):
                return "receipts"
            if any(term in content_str for term in ("consolidated statement", "ebitda", "fiscal year", "audit report")):
                return "financial_reports"
        except Exception:
            pass

        # Extension-based fallback
        for cat, extensions in self.CATEGORIES.items():
            if ext in extensions:
                return cat

        return "general"

    def stage_file(self, src_path: str) -> Dict[str, str]:
        """
        Moves or copies a single file from source path to its categorized destination.
        Returns the staging record.
        """
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"File {src_path} not found.")

        filename = os.path.basename(src_path)
        with open(src_path, "rb") as f:
            peek = f.read(2048)

        category = self.classify_file(filename, peek)
        dest_folder = os.path.join(self.staging_dir, category)
        dest_path = os.path.join(dest_folder, filename)

        # Move file safely
        shutil.move(src_path, dest_path)

        return {
            "original_name": filename,
            "category": category,
            "destination_path": os.path.abspath(dest_path),
            "size_bytes": os.path.getsize(dest_path),
            "staged_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def process_ingest_directory(self) -> List[Dict[str, str]]:
        """Scans the ingest directory and stages all files present."""
        results = []
        if not os.path.exists(self.ingest_dir):
            return results

        for entry in os.listdir(self.ingest_dir):
            full_path = os.path.join(self.ingest_dir, entry)
            if os.path.isfile(full_path):
                rec = self.stage_file(full_path)
                results.append(rec)

        return results
