"""
Test Case 3: Multimodal Pipeline & RAG Benchmark
Action: Drop 5 mock receipts (images) and 1 financial report (PDF) into the ingest folder.
Expected Result: Pipeline chunks data, updates shared vector memory, creates categorized folders,
and generates a summary Excel sheet within 5 seconds.
"""

import os
import time
import pytest
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
from backend.worker.file_stager import FileStager
from backend.worker.data_extractor import DataExtractor
from backend.worker.vector_memory import VectorMemory


def generate_mock_receipt_image(path: str, title: str, total_usd: float):
    img = Image.new("RGB", (400, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 290], outline=(30, 41, 59), width=2)
    draw.text((20, 25), "RECEIPT / TAX INVOICE", fill=(15, 23, 42))
    draw.text((20, 60), f"Vendor: {title}", fill=(51, 65, 85))
    draw.text((20, 100), f"Subtotal: ${total_usd * 0.9:.2f}", fill=(51, 65, 85))
    draw.text((20, 130), f"Tax (10%): ${total_usd * 0.1:.2f}", fill=(51, 65, 85))
    draw.text((20, 170), f"Total USD: ${total_usd:.2f}", fill=(14, 165, 233))
    draw.text((20, 220), "Payment: CORPORATE VISA **** 4892", fill=(100, 116, 139))
    img.save(path)


def generate_mock_pdf_report(path: str):
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Q4 CONSOLIDATED FINANCIAL REPORT\n\n"
        "Executive Summary:\n"
        "Total Enterprise Operating Revenue reached $4,850,000.\n"
        "Total R&D expenditures amounted to $1,240,000 with EBITDA margin expanding by 14%.\n"
        "Capital expenditure for autonomous OS infrastructure and local vector inference servers: $310,000.\n"
        "Cash reserves remain fully sufficient to sustain multi-agent operational scaling."
    )
    page.insert_text((50, 72), text, fontsize=12)
    doc.save(path)
    doc.close()


def test_multimodal_pipeline_benchmark(tmp_path):
    storage_base = tmp_path / "bench_storage"
    ingest_dir = storage_base / "ingest"
    ingest_dir.mkdir(parents=True)

    # 1. Generate 5 mock receipt images and 1 financial report PDF
    receipt_data = [
        ("receipt_aws_cloud.png", "AWS Cloud Services", 450.25),
        ("receipt_github_enterprise.png", "GitHub Copilot Enterprise", 210.00),
        ("receipt_office_depot.png", "Office Depot Equipment", 185.50),
        ("receipt_hardware_lab.png", "Shenzhen Hardware Microelectronics", 1250.00),
        ("receipt_catering_summit.png", "Summit Executive Catering", 320.75),
    ]

    for filename, vendor, amount in receipt_data:
        generate_mock_receipt_image(str(ingest_dir / filename), vendor, amount)

    pdf_filename = "financial_report_q4_audit.pdf"
    generate_mock_pdf_report(str(ingest_dir / pdf_filename))

    assert len(list(ingest_dir.iterdir())) == 6

    # Start timing benchmark
    start_time = time.perf_counter()

    # Initialize subsystems
    stager = FileStager(base_storage_dir=str(storage_base))
    extractor = DataExtractor(output_dir=str(storage_base / "staging" / "spreadsheets"))
    memory = VectorMemory(storage_dir=str(storage_base / "memory_store"))

    # A. Staging incoming files
    staged_records = stager.process_ingest_directory()
    assert len(staged_records) == 6

    # Verify directory categorization
    receipts_folder = storage_base / "staging" / "receipts"
    reports_folder = storage_base / "staging" / "financial_reports"
    assert len(list(receipts_folder.iterdir())) == 5
    assert len(list(reports_folder.iterdir())) == 1

    # B. Synthesize Summary Excel Sheet
    structured_rows = []
    for filename, vendor, amount in receipt_data:
        structured_rows.append({
            "receipt_id": filename.replace(".png", ""),
            "vendor": vendor,
            "category": "Technology & Procurement",
            "amount": amount,
            "tax": round(amount * 0.1, 2),
            "net_total": round(amount * 1.1, 2),
        })

    excel_path = extractor.extract_to_excel(
        records=structured_rows,
        filename="financial_summary_consolidated.xlsx",
        report_title="Multimodal Receipt & Audit Synthesis",
    )
    assert os.path.exists(excel_path)

    # C. Chunking & Indexing into Vector Memory
    # Index PDF text
    pdf_doc = fitz.open(str(reports_folder / pdf_filename))
    pdf_text = "".join(p.get_text() for p in pdf_doc)
    chunks_indexed = memory.add_document("q4_financial_audit", pdf_text, metadata={"type": "financial_report"})
    assert chunks_indexed > 0

    # Index spreadsheet records
    rows_indexed = memory.index_spreadsheet_rows("financial_summary", structured_rows)
    assert rows_indexed == 5

    # Verify RAG query works
    query_results = memory.query("capital expenditure autonomous infrastructure")
    assert len(query_results) > 0
    assert "autonomous OS infrastructure" in query_results[0]["text"]

    elapsed_time = time.perf_counter() - start_time

    # Performance Gate: Must complete under 5 seconds
    print(f"\n[BENCHMARK] Multimodal pipeline execution time: {elapsed_time:.3f} seconds")
    assert elapsed_time < 5.0, f"Pipeline exceeded 5.0s threshold! Took {elapsed_time:.3f}s"
