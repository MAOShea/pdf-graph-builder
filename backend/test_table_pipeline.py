"""Tests for unified lookup table pipeline."""
import unittest
from pathlib import Path

from src.ingest_manifest import _project_root
from src.table_pipeline import load_pdf_text_by_page, resolve_pdf_path


class TestTablePipeline(unittest.TestCase):
    def test_resolve_pdf_at_repo_root(self):
        root = _project_root()
        pdf = root / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        resolved = resolve_pdf_path("mork-borg.pdf")
        self.assertEqual(resolved, pdf.resolve())

    def test_load_pdf_text_has_page_keys(self):
        root = _project_root()
        pdf = root / "mork-borg.pdf"
        if not pdf.is_file():
            self.skipTest("mork-borg.pdf not at repo root")
        by_page = load_pdf_text_by_page(pdf)
        self.assertIn(1, by_page)
        self.assertTrue(len(by_page[1]) > 0)


if __name__ == "__main__":
    unittest.main()
