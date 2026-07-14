import unittest

from src.pdf_table_parser import extract_dr_table_from_text

SAMPLE = (
    "Difficulty Ratings (DR) 6\t so simple people laugh at you for failing "
    "8\t routine but some chance of failure 10\t pretty simple but not simple enough to not roll "
    "12\t normal 14\t difficult 16\t really hard 18\t should not be possible "
    "Carrying Capacity You can carry Strength+8"
)


class TestPdfDrTableParser(unittest.TestCase):
    def test_extracts_seven_rows(self):
        table = extract_dr_table_from_text(SAMPLE)
        self.assertIsNotNone(table)
        self.assertEqual(table["columns"], ["DR", "label"])
        self.assertEqual(len(table["rows"]), 7)

    def test_exact_rulebook_labels(self):
        table = extract_dr_table_from_text(SAMPLE)
        by_dr = {r[0]: r[1] for r in table["rows"]}
        self.assertEqual(by_dr[12], "normal")
        self.assertIn("routine", by_dr[8])

    def test_no_match_without_header(self):
        self.assertIsNone(extract_dr_table_from_text("Carrying Capacity only"))


if __name__ == "__main__":
    unittest.main()
