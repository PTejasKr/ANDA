"""
Data Extractor Module (Subsystem A)
Transforms multimodal JSON outputs into professionally styled .xlsx files using openpyxl and pandas.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class DataExtractor:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join("storage", "staging", "spreadsheets")
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_to_excel(
        self,
        records: List[Dict[str, Any]],
        filename: str,
        sheet_title: str = "Extracted_Data",
        report_title: str = "Multimodal Synthesis Report",
    ) -> str:
        """
        Converts a list of dictionary records to a formatted Excel file.
        Returns the absolute path to the generated .xlsx file.
        """
        if not records:
            raise ValueError("Records list cannot be empty for Excel synthesis.")

        file_path = os.path.join(self.output_dir, filename)
        if not file_path.endswith(".xlsx"):
            file_path += ".xlsx"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title

        # Theme Colors (Huemint inspired: deep slate header, muted accents)
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        title_fill = PatternFill(start_color="0EA5E9", end_color="0EA5E9", fill_type="solid")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        total_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

        title_font = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        regular_font = Font(name="Segoe UI", size=10)
        bold_font = Font(name="Segoe UI", size=10, bold=True)

        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )
        double_bottom = Border(
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="double", color="1E293B"),
        )

        headers = list(records[0].keys())
        num_cols = len(headers)

        # 1. Title Row
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
        title_cell = ws.cell(row=1, column=1, value=report_title)
        title_cell.font = title_font
        title_cell.fill = title_fill
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 36

        # Blank spacing row
        ws.row_dimensions[2].height = 10

        # 2. Table Headers
        header_row = 3
        ws.row_dimensions[header_row].height = 26
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col_idx, value=header.replace("_", " ").title())
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        # 3. Data Rows
        numeric_columns = set()
        for r_idx, record in enumerate(records, start=header_row + 1):
            ws.row_dimensions[r_idx].height = 20
            is_even = (r_idx % 2 == 0)
            for c_idx, header in enumerate(headers, start=1):
                val = record.get(header)
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if is_even:
                    cell.fill = zebra_fill

                # Format inference based on key and value type
                if isinstance(val, (int, float)):
                    numeric_columns.add(c_idx)
                    header_lower = header.lower()
                    if any(k in header_lower for k in ("price", "cost", "total", "amount", "tax", "subtotal")):
                        cell.number_format = '$#,##0.00'
                        cell.alignment = Alignment(horizontal="right")
                    else:
                        cell.number_format = '#,##0'
                        cell.alignment = Alignment(horizontal="right")
                else:
                    cell.alignment = Alignment(horizontal="left")

        # 4. Summary / Total Row if numeric columns exist
        total_row = header_row + len(records) + 1
        ws.row_dimensions[total_row].height = 24
        label_cell = ws.cell(row=total_row, column=1, value="Total Summary")
        label_cell.font = bold_font
        label_cell.fill = total_fill
        label_cell.border = double_bottom

        for c_idx in range(2, num_cols + 1):
            cell = ws.cell(row=total_row, column=c_idx)
            cell.fill = total_fill
            cell.border = double_bottom
            if c_idx in numeric_columns:
                col_letter = get_column_letter(c_idx)
                start_cell = f"{col_letter}{header_row + 1}"
                end_cell = f"{col_letter}{total_row - 1}"
                cell.value = f"=SUM({start_cell}:{end_cell})"
                cell.font = bold_font
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = '$#,##0.00'

        # 5. Auto-fit column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row == 1:
                    continue
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        wb.save(file_path)
        return os.path.abspath(file_path)
