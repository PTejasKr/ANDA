"""
Deterministic Execution Script: Generate Mock Multimodal Artifacts
Generates 5 realistic mock receipt images and 1 financial audit PDF report in storage/ingest/.
"""

import os
from PIL import Image, ImageDraw
import fitz  # PyMuPDF


def generate_artifacts(dest_dir: str = "storage/ingest"):
    os.makedirs(dest_dir, exist_ok=True)

    receipts = [
        ("receipt_aws_cloud_infra.png", "AWS Cloud Services", 482.50),
        ("receipt_github_enterprise.png", "GitHub Enterprise AI", 210.00),
        ("receipt_microelectronics_lab.png", "Shenzhen Hardware Labs", 1250.00),
        ("receipt_datacenter_cooling.png", "CryoCool Facilities", 840.20),
        ("receipt_office_ergonomics.png", "ErgoWorkstation Co.", 315.75),
    ]

    for filename, vendor, amount in receipts:
        filepath = os.path.join(dest_dir, filename)
        img = Image.new("RGB", (440, 320), color=(248, 250, 252))
        draw = ImageDraw.Draw(img)

        # Border & Header
        draw.rectangle([10, 10, 430, 310], outline=(30, 41, 59), width=2)
        draw.rectangle([10, 10, 430, 50], fill=(30, 41, 59))
        draw.text((20, 20), "OFFICIAL TAX INVOICE & RECEIPT", fill=(255, 255, 255))

        # Details
        draw.text((25, 75), f"Vendor: {vendor}", fill=(15, 23, 42))
        draw.text((25, 110), f"Item: Enterprise Systems Procurement", fill=(71, 85, 105))
        draw.text((25, 145), f"Subtotal: ${amount * 0.9:.2f}", fill=(71, 85, 105))
        draw.text((25, 175), f"Tax (10%): ${amount * 0.1:.2f}", fill=(71, 85, 105))
        draw.text((25, 215), f"TOTAL CHARGED: ${amount:.2f}", fill=(14, 165, 233))
        draw.text((25, 260), "Status: PAID IN FULL - VISA *** 4892", fill=(16, 185, 129))

        img.save(filepath)
        print(f"[+] Generated receipt: {filepath}")

    # Generate PDF
    pdf_path = os.path.join(dest_dir, "financial_audit_q4_consolidated.pdf")
    doc = fitz.open()
    page = doc.new_page()
    content = (
        "Q4 CONSOLIDATED ENTERPRISE FINANCIAL AUDIT REPORT\n\n"
        "1. Revenue Overview:\n"
        "Total Enterprise Operating Revenue reached $4,850,000 for the fiscal quarter.\n"
        "EBITDA margins expanded by 14.2% driven by autonomous agent pipeline efficiencies.\n\n"
        "2. R&D & Systems Expenditure:\n"
        "Capital expenditure for autonomous OS infrastructure and local vector inference servers: $310,000.\n"
        "Procurement of secure cryptographic hardware tokens: $45,000.\n\n"
        "3. Audit Attestation:\n"
        "All balance sheets and ledger transactions have been verified by human-in-the-loop oversight."
    )
    page.insert_text((50, 72), content, fontsize=11)
    doc.save(pdf_path)
    doc.close()
    print(f"[+] Generated PDF report: {pdf_path}")


if __name__ == "__main__":
    generate_artifacts()
