# File Staging & RAG Ingestion SOP

## 1. Objective
Orchestrate multimodal document ingestion, category-based directory staging, structured Excel synthesis with `openpyxl`, and semantic chunk indexing into local shared vector memory.

## 2. Ingestion Pipeline
1. **Multimodal Ingestion**:
   - Accepts images (receipts, screenshots), PDF documents (financial statements), and raw text.
   - Converts structured item extracts into typed Python dictionaries.
2. **Directory Staging**:
   - Monitors `storage/ingest/`.
   - Categorizes files based on MIME type and semantic keywords into:
     - `storage/staging/receipts/`
     - `storage/staging/financial_reports/`
     - `storage/staging/spreadsheets/`
     - `storage/staging/general/`
3. **Excel Synthesis**:
   - Compiles parsed transaction records into `.xlsx` using `openpyxl`.
   - Applies styling: Title headers, bold column titles, cell number formats (Currency, Dates), alternating row fills, and automated SUM totals formulas.
4. **Shared Vector Memory**:
   - Splits document text into 256-token overlapping chunks.
   - Computes normalized vector embeddings.
   - Stores payload with source metadata, allowing top-K cosine similarity RAG retrieval.
