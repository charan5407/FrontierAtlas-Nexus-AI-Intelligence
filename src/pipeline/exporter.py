"""
Data Exporter for FrontierAtlas Nexus.
Generates the 6-tab multi-sheet workbook and individual CSV files strictly matching
the canonical evaluation schemas for Google Sheets submission.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from config.settings import EXPORTS_DIR, PROCESSED_DATA_DIR
from src.llm.schemas import (
    StartupEntity,
    ProductEntity,
    ResearchPaperEntity,
    JobEntity,
    NewsEntity,
    EntityMappingLogEntry
)

logger = logging.getLogger("FrontierAtlas.Exporter")


class DataExporter:
    def __init__(self, export_dir: Path = EXPORTS_DIR):
        self.export_dir = export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        startups: List[StartupEntity],
        products: List[ProductEntity],
        papers: List[ResearchPaperEntity],
        jobs: List[JobEntity],
        news: List[NewsEntity],
        mapping_logs: List[EntityMappingLogEntry],
        file_prefix: str = "FrontierAtlas_Data_Output"
    ) -> Dict[str, str]:
        """
        Exports all 6 dataset tabs into:
        1. A unified multi-sheet Excel file (.xlsx)
        2. Individual CSV files for each tab
        """
        logger.info("Formatting datasets for 6-tab Google Sheets deliverable...")

        # Convert to flat dictionaries conforming to schema
        df_startups = pd.DataFrame([s.to_flat_dict() for s in startups])
        df_products = pd.DataFrame([p.to_flat_dict() for p in products])
        df_papers = pd.DataFrame([r.to_flat_dict() for r in papers])
        df_jobs = pd.DataFrame([j.to_flat_dict() for j in jobs])
        df_news = pd.DataFrame([n.to_flat_dict() for n in news])
        df_mapping = pd.DataFrame([m.to_flat_dict() for m in mapping_logs])

        # Write individual CSVs
        csv_files = {
            "Startups": self.export_dir / "startups.csv",
            "Products": self.export_dir / "products.csv",
            "Research Papers": self.export_dir / "research_papers.csv",
            "Jobs": self.export_dir / "jobs.csv",
            "News": self.export_dir / "news.csv",
            "Entity Mapping Log": self.export_dir / "entity_mapping_log.csv",
        }

        df_startups.to_csv(csv_files["Startups"], index=False, encoding="utf-8")
        df_products.to_csv(csv_files["Products"], index=False, encoding="utf-8")
        df_papers.to_csv(csv_files["Research Papers"], index=False, encoding="utf-8")
        df_jobs.to_csv(csv_files["Jobs"], index=False, encoding="utf-8")
        df_news.to_csv(csv_files["News"], index=False, encoding="utf-8")
        df_mapping.to_csv(csv_files["Entity Mapping Log"], index=False, encoding="utf-8")

        # Write unified multi-tab Excel file with professional formatting
        xlsx_path = self.export_dir / f"{file_prefix}.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df_startups.to_excel(writer, sheet_name="Startups", index=False)
            df_products.to_excel(writer, sheet_name="Products", index=False)
            df_papers.to_excel(writer, sheet_name="Research Papers", index=False)
            df_jobs.to_excel(writer, sheet_name="Jobs", index=False)
            df_news.to_excel(writer, sheet_name="News", index=False)
            df_mapping.to_excel(writer, sheet_name="Entity Mapping Log", index=False)

        # Style the Excel sheets
        self._style_workbook(xlsx_path)

        # Save JSON dumps into processed data directory
        json_dump_path = PROCESSED_DATA_DIR / "dataset_summary.json"
        summary_meta = {
            "counts": {
                "startups": len(startups),
                "products": len(products),
                "research_papers": len(papers),
                "jobs": len(jobs),
                "news": len(news),
                "entity_mapping_log": len(mapping_logs),
            },
            "exported_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "xlsx_path": str(xlsx_path),
            "csv_paths": {k: str(v) for k, v in csv_files.items()}
        }
        with open(json_dump_path, "w", encoding="utf-8") as f:
            json.dump(summary_meta, f, indent=2)

        logger.info(f"Successfully generated Google Sheets multi-tab workbook: {xlsx_path}")
        return {
            "xlsx": str(xlsx_path),
            "startups_csv": str(csv_files["Startups"]),
            "products_csv": str(csv_files["Products"]),
            "papers_csv": str(csv_files["Research Papers"]),
            "jobs_csv": str(csv_files["Jobs"]),
            "news_csv": str(csv_files["News"]),
            "mapping_csv": str(csv_files["Entity Mapping Log"]),
        }

    def _style_workbook(self, xlsx_path: Path):
        """Applies headers, font, alternating colors, and column width adjustments."""
        from openpyxl import load_workbook

        wb = load_workbook(xlsx_path)
        header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")  # Navy Blue
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0")
        )

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            # Style header row
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            ws.row_dimensions[1].height = 28

            # Auto-adjust column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    if cell.row == 1:
                        max_len = max(max_len, len(val_str) + 4)
                    else:
                        cell.border = thin_border
                        max_len = max(max_len, min(len(val_str), 45))
                ws.column_dimensions[col_letter].width = max(max_len + 2, 12)

        wb.save(xlsx_path)


default_exporter = DataExporter()

