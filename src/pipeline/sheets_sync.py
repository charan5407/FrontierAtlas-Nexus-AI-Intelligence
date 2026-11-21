"""
Google Sheets Sync & Cloud Publisher for FrontierAtlas Nexus.
Enables direct programmatic publishing of the 6 tabs into a live Google Sheet
using gspread or Google Service Account credentials, or generates Google Sheets
import instructions with verified public CSV URLs.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
from config.settings import EXPORTS_DIR

logger = logging.getLogger("FrontierAtlas.SheetsSync")


class GoogleSheetsSync:
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    def upload_to_google_sheet(self, spreadsheet_title: str = "FrontierAtlas_Data_Output"):
        """
        Uploads all 6 CSV exports into a single multi-tab Google Sheet using gspread.
        """
        try:
            import gspread
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                logger.warning("No Google Service Account credentials found. Run manual upload or set GOOGLE_APPLICATION_CREDENTIALS.")
                self.print_manual_import_instructions()
                return None

            gc = gspread.service_account(filename=self.credentials_path)
            sh = gc.create(spreadsheet_title)
            sh.share("", which="anyone", role="reader")  # Public link

            tabs = [
                ("Startups", EXPORTS_DIR / "startups.csv"),
                ("Products", EXPORTS_DIR / "products.csv"),
                ("Research Papers", EXPORTS_DIR / "research_papers.csv"),
                ("Jobs", EXPORTS_DIR / "jobs.csv"),
                ("News", EXPORTS_DIR / "news.csv"),
                ("Entity Mapping Log", EXPORTS_DIR / "entity_mapping_log.csv"),
            ]

            import csv
            for name, path in tabs:
                if not path.exists():
                    continue
                with open(path, "r", encoding="utf-8") as f:
                    reader = list(csv.reader(f))
                try:
                    worksheet = sh.worksheet(name)
                except Exception:
                    worksheet = sh.add_worksheet(title=name, rows=len(reader) + 50, cols=len(reader[0]) + 5)
                worksheet.update(reader)

            logger.info(f"Google Sheet published successfully: {sh.url}")
            return sh.url
        except Exception as e:
            logger.error(f"Google Sheets API upload error: {e}")
            self.print_manual_import_instructions()
            return None

    @staticmethod
    def print_manual_import_instructions():
        xlsx_file = EXPORTS_DIR / "FrontierAtlas_Data_Output.xlsx"
        print("\n" + "=" * 70)
        print("GOOGLE SHEETS SUBMISSION INSTRUCTIONS (Zero-Friction Import)")
        print("=" * 70)
        print("A pre-styled 6-tab multi-sheet workbook has been generated at:")
        print(f"-> {xlsx_file.resolve()}\n")
        print("To create your public submission link in 30 seconds:")
        print("1. Open Google Sheets (https://sheets.new)")
        print("2. Click 'File' -> 'Import' -> 'Upload'")
        print(f"3. Select: {xlsx_file.resolve()}")
        print("4. Select 'Replace spreadsheet' and click 'Import data'")
        print("5. Click 'Share' (top right) -> Change to 'Anyone with the link can view'")
        print("6. Paste that Google Sheet URL into your assessment submission form!")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    syncer = GoogleSheetsSync()
    syncer.upload_to_google_sheet()

