import unittest

from langchain_core.documents import Document

from src.create_chunks import CreateChunksofDocument
from src.document_sources.local_file import filter_pages_by_range


def _pdf_page(n: int, text: str = "x") -> Document:
    return Document(page_content=text, metadata={"page": n - 1, "source": "test.pdf"})


class TestPageFilter(unittest.TestCase):
    def test_filter_inclusive_range(self):
        pages = [_pdf_page(i) for i in range(1, 11)]
        out = filter_pages_by_range(pages, 27, 31)
        self.assertEqual([], out)

        subset = filter_pages_by_range(pages, 3, 5)
        self.assertEqual([3, 4, 5], [p.metadata["page_number"] for p in subset])

    def test_filter_start_only(self):
        pages = [_pdf_page(i) for i in range(1, 6)]
        out = filter_pages_by_range(pages, 4, None)
        self.assertEqual([4, 5], [p.metadata["page_number"] for p in out])

    def test_filter_end_only(self):
        pages = [_pdf_page(i) for i in range(1, 6)]
        out = filter_pages_by_range(pages, None, 2)
        self.assertEqual([1, 2], [p.metadata["page_number"] for p in out])

    def test_invalid_range_raises(self):
        with self.assertRaises(ValueError):
            filter_pages_by_range([_pdf_page(1)], 10, 5)

    def test_chunks_keep_book_page_numbers_after_filter(self):
        pages = filter_pages_by_range([_pdf_page(i, f"p{i}") for i in range(25, 32)], 27, 31)
        chunks = CreateChunksofDocument(pages, graph=None).split_file_into_chunks(512, 0)
        self.assertEqual([27, 28, 29, 30, 31], [c.metadata["page_number"] for c in chunks])


if __name__ == "__main__":
    unittest.main()
