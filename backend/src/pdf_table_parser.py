"""Extract lookup tables from PDF using ingest-manifest pdf_extract signatures.

Modes:

- default — sequential index+remainder on the flattened ``get_text()`` stream
- ``aligned_columns`` — N cells per visual row from word x-coordinates
  (``pdf_extract.column_x_cuts``). Needed when the book is a 3-column list
  and ``get_text()`` stacks each cell on its own line.
  ``visual_columns`` + ``keep_columns`` project a wider visual row onto
  the spec columns (roll-twice lists that share a face but must not pack
  both words into one ``HAS_ENTRY``). ``require_index`` skips lead-in
  rows whose first kept cell is not a numeric face.
  ``require_index_columns`` skips a row unless those kept cells are
  numeric faces (d4×d6 matrix: require d6 so indented nested lists are
  not packed). ``carry_index_columns`` copies a blank index from the
  previous kept row (d4 printed only on the first row of each group).
- ``split_italic`` — sequential index keys, then split the remainder into two
  result columns from PDF span italic (roman → column 1, italic → column 2).
  Requires ``pdf_path``. Flattened ``get_text()`` cannot do this.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from fitz import open as fitz_open
from langchain_core.documents import Document

from src.ingest_manifest import column_names, load_ingest_manifest, lookup_table_specs, spec_by_name

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f]+")
_MAX_LABEL_LEN = 2000
# PyMuPDF TEXT_FONT_ITALIC. Font-name fallback covers truncated subset names.
_TEXT_FONT_ITALIC = 2
_ITALIC_FONT_RE = re.compile(r"itali", re.IGNORECASE)


def _skip_pdf_extract(spec: dict[str, Any]) -> bool:
    return bool((spec.get("hand_authored") or {}).get("skip_pdf_extract"))


def _clean_label(raw: str) -> str:
    return " ".join(_CONTROL_CHAR_RE.sub(" ", raw).split())


def _normalize_range_key(key: str) -> str:
    return key.replace("\u2013", "-").strip()


def _index_keys(index_type: str, index_cfg: dict) -> list[str]:
    if index_cfg.get("values"):
        return [_normalize_range_key(str(v)) for v in index_cfg["values"]]
    if index_type == "dr_set":
        return [str(v) for v in index_cfg.get("values") or []]
    if index_type == "d12":
        return [str(i) for i in range(1, 13)]
    if index_type == "d10":
        return [str(i) for i in range(1, 11)]
    if index_type == "d8":
        return [str(i) for i in range(1, 9)]
    if index_type == "d6":
        return [str(i) for i in range(1, 7)]
    if index_type == "d4":
        return [str(i) for i in range(1, 5)]
    if index_type == "d20":
        return [str(i) for i in range(1, 21)]
    if index_type == "d100":
        return [str(i) for i in range(1, 101)]
    if index_type == "d100_pairs":
        return [f"{i}-{i + 1}" for i in range(1, 99, 2)] + ["99-00"]
    return []


def _key_boundary_pattern(key: str, *, dotted: bool = False) -> re.Pattern:
    key = _normalize_range_key(key)
    if "-" in key:
        parts = key.split("-", 1)
        key_expr = rf"{re.escape(parts[0])}[\-–]{re.escape(parts[1])}"
    else:
        key_expr = re.escape(key)
    suffix = r"(?:[\s\t]+|\.)" if dotted else r"(?:[\s\t]+)"
    return re.compile(rf"(?:^|[\s\t]){key_expr}{suffix}", re.IGNORECASE)


def _parse_rows_sequential(
    body: str,
    keys: list[str],
    index_type: str,
    *,
    dotted: bool = False,
    row_stop_before: list[str] | None = None,
) -> list[list[Any]]:
    """Parse rows in key order so digits inside prose are not mistaken for row indices."""
    if not keys:
        return []

    rows: list[list[Any]] = []
    search_from = 0
    for i, key in enumerate(keys):
        match = _key_boundary_pattern(key, dotted=dotted).search(body, search_from)
        if not match:
            break
        start = match.end()
        if i + 1 < len(keys):
            next_match = _key_boundary_pattern(keys[i + 1], dotted=dotted).search(body, start)
            end = next_match.start() if next_match else len(body)
        else:
            end = len(body)
        for pat in row_stop_before or []:
            if not pat:
                continue
            nested = re.search(pat, body[start:end], _STREAM_REGEX_FLAGS)
            if nested:
                end = start + nested.start()
                break
        label = _clean_label(body[start:end])
        if not label or len(label) > _MAX_LABEL_LEN:
            continue
        rows.append([_parse_index_value(key, index_type), label])
        search_from = end
    return rows


def _page_span(spec: dict[str, Any]) -> list[int]:
    pages = spec.get("pages")
    if not pages or pages == "TBD":
        return []
    if isinstance(pages, int):
        return [pages]
    text = str(pages)
    if "-" in text:
        start, end = text.split("-", 1)
        return list(range(int(start.strip()), int(end.strip()) + 1))
    try:
        return [int(text.strip())]
    except ValueError:
        return []


_STREAM_REGEX_FLAGS = re.IGNORECASE | re.DOTALL | re.MULTILINE


def _find_header(text: str, patterns: list[str]) -> re.Match | None:
    """Search header_patterns in a multi-line span. ``^`` / ``$`` are line anchors."""
    for pat in patterns:
        match = re.search(pat, text, _STREAM_REGEX_FLAGS)
        if match:
            return match
    return None


def _slice_body(text: str, start: int, stop_before: list[str]) -> str:
    body = text[start:]
    if not stop_before:
        return body
    earliest = len(body)
    for pat in stop_before:
        match = re.search(pat, body, _STREAM_REGEX_FLAGS)
        if match:
            earliest = min(earliest, match.start())
    return body[:earliest]


def page_span(spec: dict[str, Any]) -> list[int]:
    """Public alias for manifest page span (single page or inclusive range)."""
    return _page_span(spec)


def _parse_index_value(raw: str, index_type: str) -> Any:
    raw = raw.strip()
    if index_type == "dr_set":
        try:
            return int(raw)
        except ValueError:
            return raw
    if index_type in ("d12", "d10", "d8", "d6", "d4", "d20", "d100"):
        try:
            return int(raw)
        except ValueError:
            return raw
    if index_type in ("d100_pairs", "range_list"):
        return _normalize_range_key(raw)
    if index_type == "d66":
        if "–" in raw or "-" in raw:
            return raw.replace("–", "-").strip()
        try:
            return int(raw)
        except ValueError:
            return raw
    return raw


def _clean_pdf_heading(raw: str) -> str:
    return " ".join(_CONTROL_CHAR_RE.sub(" ", raw).split()).strip()


def table_display_title(
    spec: dict[str, Any],
    *,
    matched_header: str | None = None,
) -> str:
    """
    Human/PDF-facing title for a lookup table.

    Priority: manifest ``title`` → matched PDF heading → technical ``name``.
    Stable graph id remains ``spec["name"]`` (e.g. TrapsTable).
    """
    explicit = str(spec.get("title") or "").strip()
    if explicit:
        return explicit
    if matched_header:
        cleaned = _clean_pdf_heading(matched_header)
        if cleaned:
            return cleaned
    return str(spec.get("name") or "table")


def _aligned_column_index(x0: float, cuts: list[float]) -> int:
    """cuts are left edges of columns 1..n-1. x < cuts[0] → column 0."""
    for i, cut in enumerate(cuts):
        if x0 < cut:
            return i
    return len(cuts)


def cells_from_aligned_words(
    words: list[tuple[float, str]], cuts: list[float], n_cols: int
) -> list[str]:
    """Split one visual row's (x0, text) words into n_cols cells."""
    buckets: list[list[str]] = [[] for _ in range(n_cols)]
    for x0, text in words:
        idx = _aligned_column_index(x0, cuts)
        if idx >= n_cols:
            idx = n_cols - 1
        token = _clean_label(text)
        if token:
            buckets[idx].append(token)
    return [" ".join(part) for part in buckets]


def _aligned_cell_is_index_face(text: str) -> bool:
    return bool(re.fullmatch(r"\d{1,3}", (text or "").strip()))


def _aligned_require_index_columns(
    cells: list[str], pdf_extract: dict[str, Any]
) -> bool:
    """False → drop this visual row (nested indent or non-face junk)."""
    raw = pdf_extract.get("require_index_columns")
    if raw is None:
        return True
    for i in raw:
        idx = int(i)
        if idx >= len(cells) or not _aligned_cell_is_index_face(cells[idx]):
            return False
    return True


def _aligned_carry_index_columns(
    cells: list[str], prev: list[Any] | None, pdf_extract: dict[str, Any]
) -> list[str]:
    raw = pdf_extract.get("carry_index_columns")
    if not raw or not prev:
        return cells
    out = list(cells)
    for i in raw:
        idx = int(i)
        if idx < len(out) and not str(out[idx]).strip() and idx < len(prev):
            out[idx] = prev[idx]
    return out


def is_aligned_continuation_row(cells: list[str]) -> bool:
    """Wrapped notes: leading columns empty, last column filled.

    Empty first column alone is not a wrap (e.g. shop ammo indented into
    the name column).
    """
    if len(cells) < 2:
        return False
    leading = [c.strip() for c in cells[:-1]]
    last = cells[-1].strip()
    return (not any(leading)) and bool(last)


def _column_x_cuts_for_page(
    pdf_extract: dict[str, Any], page_number: int
) -> list[float] | None:
    raw = pdf_extract.get("column_x_cuts")
    if raw is None:
        return None
    if isinstance(raw, dict):
        vals = raw.get(str(page_number), raw.get(page_number))
        if not isinstance(vals, list) or not vals:
            return None
        return [float(x) for x in vals]
    if isinstance(raw, list) and raw:
        return [float(x) for x in raw]
    return None


def _row_text_matches(text: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat and re.search(pat, text, re.IGNORECASE | re.DOTALL):
            return True
    return False


def _apply_strip_inline(text: str, text_filters: dict[str, Any] | None) -> str:
    line = text
    for pat in (text_filters or {}).get("strip_inline_patterns") or []:
        if pat:
            line = re.sub(pat, " ", line, flags=re.IGNORECASE)
    return _clean_label(line)


def _drop_spatial_row(
    text: str, text_filters: dict[str, Any] | None, page_number: int
) -> bool:
    stripped = _apply_strip_inline(text, text_filters)
    if not stripped:
        return True
    for pat in (text_filters or {}).get("drop_line_patterns") or []:
        if pat and re.fullmatch(pat, stripped, re.IGNORECASE):
            return True
    if (text_filters or {}).get("drop_edge_page_number") and stripped == str(
        page_number
    ):
        return True
    return False


def _group_words_by_row(
    page_words: list[tuple[float, float, str]],
) -> list[list[tuple[float, str]]]:
    """Group (x0, y0, text) into visual rows (same rounded y), left-to-right."""
    buckets: dict[int, list[tuple[float, str]]] = {}
    for x0, y0, text in page_words:
        key = int(round(y0))
        buckets.setdefault(key, []).append((x0, text))
    rows: list[list[tuple[float, str]]] = []
    for y in sorted(buckets):
        row = sorted(buckets[y], key=lambda item: item[0])
        if row:
            rows.append(row)
    return rows


def extract_table_aligned_columns(
    spec: dict[str, Any],
    pdf_path: str | Path,
    *,
    text_filters: dict[str, Any] | None = None,
) -> dict | None:
    """Parse an N-column aligned list from PDF word coordinates."""
    pdf_extract = spec.get("pdf_extract") or {}
    if pdf_extract.get("status") == "todo" or _skip_pdf_extract(spec):
        return None
    if pdf_extract.get("mode") != "aligned_columns":
        return None

    cols = column_names(spec)
    if len(cols) < 2:
        return None
    n_cols = len(cols)
    keep_raw = pdf_extract.get("keep_columns")
    keep_idx: list[int] | None = None
    visual_n = n_cols
    if keep_raw is not None:
        keep_idx = [int(i) for i in keep_raw]
        if len(keep_idx) != n_cols:
            logging.warning(
                "aligned_columns %s: keep_columns length %s != spec columns %s",
                spec.get("name"),
                len(keep_idx),
                n_cols,
            )
            return None
        visual_n = int(
            pdf_extract.get("visual_columns")
            or (max(keep_idx) + 1 if keep_idx else n_cols)
        )
    header_patterns = pdf_extract.get("header_patterns") or []
    stop_before = pdf_extract.get("stop_before") or []
    span = _page_span(spec)
    if not header_patterns or not span:
        return None

    path = Path(pdf_path)
    if not path.is_file():
        return None

    doc = fitz_open(path)
    try:
        started = False
        matched_header = ""
        rows: list[list[Any]] = []
        for page_number in span:
            cuts = _column_x_cuts_for_page(pdf_extract, page_number)
            if not cuts or len(cuts) != visual_n - 1:
                logging.warning(
                    "aligned_columns %s: missing or wrong-length column_x_cuts for page %s",
                    spec.get("name"),
                    page_number,
                )
                return None
            page_index = page_number - 1
            if page_index < 0 or page_index >= len(doc):
                return None
            page = doc[page_index]
            page_words = [
                (float(w[0]), float(w[1]), str(w[4]))
                for w in page.get_text("words")
            ]
            for row_words in _group_words_by_row(page_words):
                line = _clean_label(" ".join(tok for _, tok in row_words))
                if not line:
                    continue
                if _drop_spatial_row(line, text_filters, page_number):
                    continue
                if not started:
                    if _row_text_matches(line, header_patterns):
                        started = True
                        matched_header = line
                    continue
                if stop_before and _row_text_matches(line, stop_before):
                    return _aligned_table_result(
                        spec, cols, rows, pdf_extract, matched_header
                    )
                cells = cells_from_aligned_words(row_words, cuts, visual_n)
                if keep_idx is not None:
                    cells = [
                        cells[i] if i < len(cells) else "" for i in keep_idx
                    ]
                if not any(c.strip() for c in cells):
                    continue
                if pdf_extract.get("require_index") and not re.fullmatch(
                    r"\d{1,3}", (cells[0] or "").strip()
                ):
                    continue
                if not _aligned_require_index_columns(cells, pdf_extract):
                    continue
                cells = _aligned_carry_index_columns(
                    cells, rows[-1] if rows else None, pdf_extract
                )
                if rows and is_aligned_continuation_row(cells):
                    prev = rows[-1]
                    prev[-1] = _clean_label(f"{prev[-1]} {cells[-1]}")
                    continue
                rows.append(cells)
        if not started:
            return None
        return _aligned_table_result(spec, cols, rows, pdf_extract, matched_header)
    finally:
        doc.close()


def _aligned_table_result(
    spec: dict[str, Any],
    cols: list[str],
    rows: list[list[Any]],
    pdf_extract: dict[str, Any],
    matched_header: str,
) -> dict | None:
    min_rows = pdf_extract.get("min_rows") or 1
    if len(rows) < min_rows:
        return None
    max_rows = pdf_extract.get("max_rows")
    if max_rows is not None and len(rows) > max_rows:
        rows = rows[:max_rows]
    pdf_heading = _clean_pdf_heading(matched_header)
    return {
        "manifest_name": spec["name"],
        "title": table_display_title(spec, matched_header=pdf_heading),
        "pdf_heading": pdf_heading,
        "lead_in": str(spec["lead_in"]).strip() if spec.get("lead_in") else "",
        "columns": cols,
        "rows": rows,
    }


def _span_is_italic(span: dict[str, Any]) -> bool:
    flags = int(span.get("flags") or 0)
    font = str(span.get("font") or "")
    return bool(flags & _TEXT_FONT_ITALIC) or bool(_ITALIC_FONT_RE.search(font))


def _iter_page_spans(page) -> list[dict[str, Any]]:
    """Reading-order spans; newline between visual lines (row index tokens live there)."""
    out: list[dict[str, Any]] = []
    first_line = True
    for block in page.get_text("dict").get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            line_spans = [
                span
                for span in (line.get("spans") or [])
                if span.get("text")
            ]
            if not line_spans:
                continue
            if not first_line:
                out.append({"text": "\n", "italic": False})
            first_line = False
            for span in line_spans:
                out.append(
                    {
                        "text": span.get("text") or "",
                        "italic": _span_is_italic(span),
                    }
                )
    return out


def _fill_italic_sandwich(
    pieces: list[tuple[str, bool]],
) -> list[tuple[str, bool]]:
    """Italic-neighbor fill for Regular glyph islands (d4, HP) inside italic.

    The book's outcome split is italic vs roman. PDF subsets often switch to
    Regular for a die token or ``HP`` in the middle of an italic sentence.
    Those spans are not a second roman outcome — they sit between italic
    neighbors and inherit italic.
    """
    if len(pieces) < 3:
        return list(pieces)
    out = list(pieces)

    def _neighbor_italic(idx: int, step: int) -> bool | None:
        j = idx + step
        while 0 <= j < len(out):
            if _clean_label(out[j][0]):
                return out[j][1]
            j += step
        return None

    for i, (_text, italic) in enumerate(out):
        if italic:
            continue
        prev = _neighbor_italic(i, -1)
        nxt = _neighbor_italic(i, 1)
        if prev is True and nxt is True:
            out[i] = (out[i][0], True)
    return out


def _split_immediate_unrealized(pieces: list[tuple[str, bool]]) -> tuple[str, str]:
    immediate_parts: list[str] = []
    unrealized_parts: list[str] = []
    for text, italic in _fill_italic_sandwich(pieces):
        (unrealized_parts if italic else immediate_parts).append(text)
    return _clean_label("".join(immediate_parts)), _clean_label(
        "".join(unrealized_parts)
    )


def _join_span_texts(
    spans: list[dict[str, Any]],
) -> tuple[str, list[tuple[int, int, dict[str, Any]]]]:
    parts: list[str] = []
    ranges: list[tuple[int, int, dict[str, Any]]] = []
    pos = 0
    for span in spans:
        text = span["text"]
        parts.append(text)
        ranges.append((pos, pos + len(text), span))
        pos += len(text)
    return "".join(parts), ranges


def _pieces_overlapping(
    full: str,
    ranges: list[tuple[int, int, dict[str, Any]]],
    start: int,
    end: int,
) -> list[tuple[str, bool]]:
    pieces: list[tuple[str, bool]] = []
    for a, b, span in ranges:
        if b <= start or a >= end:
            continue
        lo = max(a, start)
        hi = min(b, end)
        frag = full[lo:hi]
        if frag:
            pieces.append((frag, bool(span.get("italic"))))
    return pieces


def extract_table_split_italic(
    spec: dict[str, Any],
    pdf_path: str | Path,
    *,
    text_filters: dict[str, Any] | None = None,
) -> dict | None:
    """Sequential index keys; remainder split by PDF italic into two result columns."""
    pdf_extract = spec.get("pdf_extract") or {}
    if pdf_extract.get("status") == "todo" or _skip_pdf_extract(spec):
        return None
    if pdf_extract.get("mode") != "split_italic":
        return None

    cols = column_names(spec)
    if len(cols) != 3:
        logging.warning(
            "split_italic %s: need 3 columns (index, roman, italic); got %s",
            spec.get("name"),
            cols,
        )
        return None

    header_patterns = pdf_extract.get("header_patterns") or []
    stop_before = pdf_extract.get("stop_before") or []
    span = _page_span(spec)
    if not header_patterns or not span:
        return None

    path = Path(pdf_path)
    if not path.is_file():
        return None

    index_cfg = pdf_extract.get("index") or {}
    index_type = index_cfg.get("type") or ""
    keys = _index_keys(index_type, index_cfg)
    if not keys:
        return None

    doc = fitz_open(path)
    try:
        kept: list[dict[str, Any]] = []
        started = False
        for page_number in span:
            page_index = page_number - 1
            if page_index < 0 or page_index >= len(doc):
                return None
            if started and kept and kept[-1].get("text") != "\n":
                kept.append({"text": "\n", "italic": False})
            for raw in _iter_page_spans(doc[page_index]):
                if raw["text"] == "\n" or not _clean_label(raw["text"]):
                    if started:
                        kept.append(raw)
                    continue
                line = _clean_label(raw["text"])
                if _drop_spatial_row(raw["text"], text_filters, page_number):
                    continue
                if started and _row_text_matches(line, header_patterns):
                    continue
                kept.append(raw)
                if not started and _row_text_matches(line, header_patterns):
                    started = True
    finally:
        doc.close()

    if not started:
        return None

    full, ranges = _join_span_texts(kept)
    header = _find_header(full, header_patterns)
    if not header:
        return None
    body = _slice_body(full, header.end(), stop_before)
    if not body:
        return None
    body_start = header.end()
    body_end = body_start + len(body)
    body_full = full[body_start:body_end]
    body_ranges: list[tuple[int, int, dict[str, Any]]] = []
    for a, b, sp in ranges:
        if b <= body_start or a >= body_end:
            continue
        lo = max(a, body_start)
        hi = min(b, body_end)
        frag = full[lo:hi]
        if not frag:
            continue
        body_ranges.append(
            (
                lo - body_start,
                hi - body_start,
                {"text": frag, "italic": bool(sp.get("italic"))},
            )
        )

    dotted = bool(pdf_extract.get("dotted_index"))
    rows: list[list[Any]] = []
    search_from = 0
    for i, key in enumerate(keys):
        match = _key_boundary_pattern(key, dotted=dotted).search(body_full, search_from)
        if not match:
            break
        start = match.end()
        if i + 1 < len(keys):
            next_match = _key_boundary_pattern(keys[i + 1], dotted=dotted).search(
                body_full, start
            )
            end = next_match.start() if next_match else len(body_full)
        else:
            end = len(body_full)
        for pat in pdf_extract.get("row_stop_before") or []:
            if not pat:
                continue
            nested = re.search(pat, body_full[start:end], _STREAM_REGEX_FLAGS)
            if nested:
                end = start + nested.start()
                break
        pieces = _pieces_overlapping(body_full, body_ranges, start, end)
        immediate, unrealized = _split_immediate_unrealized(pieces)
        if not immediate and not unrealized:
            search_from = end
            continue
        if len(immediate) > _MAX_LABEL_LEN or len(unrealized) > _MAX_LABEL_LEN:
            search_from = end
            continue
        rows.append(
            [_parse_index_value(key, index_type), immediate, unrealized]
        )
        search_from = end

    min_rows = pdf_extract.get("min_rows") or 1
    if len(rows) < min_rows:
        return None
    max_rows = pdf_extract.get("max_rows")
    if max_rows is not None and len(rows) > max_rows:
        rows = rows[:max_rows]

    pdf_heading = _clean_pdf_heading(header.group(0))
    return {
        "manifest_name": spec["name"],
        "title": table_display_title(spec, matched_header=pdf_heading),
        "pdf_heading": pdf_heading,
        "lead_in": str(spec["lead_in"]).strip() if spec.get("lead_in") else "",
        "columns": cols,
        "rows": rows,
        "italic_columns": [cols[2]],
    }


def extract_lookup_table(
    spec: dict[str, Any],
    *,
    text: str | None = None,
    pdf_path: str | Path | None = None,
    page_number: int | None = None,
    allow_multi_page: bool = False,
    text_filters: dict[str, Any] | None = None,
) -> dict | None:
    """Dispatch pdf_extract.mode (aligned_columns / split_italic / sequential)."""
    pdf_extract = spec.get("pdf_extract") or {}
    if pdf_extract.get("mode") == "aligned_columns":
        if not pdf_path:
            return None
        return extract_table_aligned_columns(
            spec, pdf_path, text_filters=text_filters
        )
    if pdf_extract.get("mode") == "split_italic":
        if not pdf_path:
            return None
        return extract_table_split_italic(
            spec, pdf_path, text_filters=text_filters
        )
    if not text:
        return None
    return extract_table_from_text(
        text,
        spec,
        page_number=page_number,
        allow_multi_page=allow_multi_page,
    )


def extract_table_from_text(
    text: str,
    spec: dict[str, Any],
    *,
    page_number: int | None = None,
    allow_multi_page: bool = False,
) -> dict | None:
    """Parse one lookup table from chunk text per manifest pdf_extract block."""
    if not text:
        return None

    pdf_extract = spec.get("pdf_extract") or {}
    if pdf_extract.get("mode") in ("aligned_columns", "split_italic"):
        return None
    if pdf_extract.get("status") == "todo" or _skip_pdf_extract(spec):
        return None

    if len(_page_span(spec)) >= 2 and not allow_multi_page:
        return None

    prefer_page = pdf_extract.get("prefer_page")
    if prefer_page is not None and page_number is not None and page_number != prefer_page:
        return None

    header_patterns = pdf_extract.get("header_patterns") or []
    if not header_patterns:
        return None

    header = _find_header(text, header_patterns)
    if not header:
        return None

    pdf_heading = _clean_pdf_heading(header.group(0))
    body = _slice_body(text, header.end(), pdf_extract.get("stop_before") or [])
    index_cfg = pdf_extract.get("index") or {}
    index_type = index_cfg.get("type") or ""
    keys = _index_keys(index_type, index_cfg)
    if not keys:
        return None

    cols = column_names(spec)
    if len(cols) < 2:
        return None

    rows = _parse_rows_sequential(
        body,
        keys,
        index_type,
        dotted=bool(pdf_extract.get("dotted_index")),
        row_stop_before=pdf_extract.get("row_stop_before"),
    )

    min_rows = pdf_extract.get("min_rows") or 1
    if len(rows) < min_rows:
        return None

    max_rows = pdf_extract.get("max_rows")
    if max_rows is not None and len(rows) > max_rows:
        rows = rows[:max_rows]

    return {
        "manifest_name": spec["name"],
        "title": table_display_title(spec, matched_header=pdf_heading),
        "pdf_heading": pdf_heading,
        "lead_in": str(spec["lead_in"]).strip() if spec.get("lead_in") else "",
        "columns": cols,
        "rows": rows,
    }


def extract_all_tables_from_text(
    text: str,
    *,
    page_number: int | None = None,
    game: str = "mork-borg",
) -> list[dict]:
    tables: list[dict] = []
    for spec in lookup_table_specs(game):
        table = extract_table_from_text(text, spec, page_number=page_number)
        if table:
            tables.append(table)
    return tables


def _is_pdf_chunk(meta: dict) -> bool:
    if meta.get("source_format") == "structured-json":
        return False
    return meta.get("page_number") is not None or meta.get("block_type") is None


def _parse_tables_from_metadata(meta: dict) -> list[dict]:
    raw = meta.get("table_json")
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [raw]
    return []


def _attach_table_to_chunk(meta: dict, chunk_doc: Document, tables: list[dict]) -> None:
    if len(tables) == 1:
        meta["table_json"] = json.dumps(tables[0])
        meta["block_title"] = tables[0].get("title", tables[0].get("manifest_name"))
    else:
        meta["table_json"] = json.dumps(tables)
        meta["block_title"] = ", ".join(t.get("manifest_name", "?") for t in tables)
    meta["block_type"] = "table"
    meta["source_format"] = meta.get("source_format") or "pdf"
    chunk_doc.metadata = meta


def enrich_pdf_chunks_with_tables(
    chunk_list: list[dict],
    *,
    game: str = "mork-borg",
    force: bool = False,
) -> dict[str, int]:
    """Scan PDF chunks; attach extracted table_json (one object or array) per chunk."""
    stats = {"chunks_scanned": 0, "tables_found": 0}
    manifest = load_ingest_manifest(game)

    sorted_items = sorted(
        chunk_list,
        key=lambda item: (item.get("chunk_doc") or Document(page_content="")).metadata.get(
            "page_number", 9999
        )
        or 9999,
    )

    page_to_item: dict[int, dict] = {}
    chunks_by_page: dict[int, str] = {}
    for item in sorted_items:
        chunk_doc: Document = item.get("chunk_doc")
        if chunk_doc is None:
            continue
        page = (chunk_doc.metadata or {}).get("page_number")
        if page is not None:
            page_to_item[page] = item
            chunks_by_page[page] = chunk_doc.page_content or ""

    materialized_on_chunk: set[str] = set()

    for item in sorted_items:
        chunk_doc: Document = item.get("chunk_doc")
        if chunk_doc is None:
            continue

        meta = chunk_doc.metadata or {}
        if not force and (meta.get("table_json") or not _is_pdf_chunk(meta)):
            continue
        if not _is_pdf_chunk(meta):
            continue

        stats["chunks_scanned"] += 1
        page = meta.get("page_number")
        tables = extract_all_tables_from_text(
            chunk_doc.page_content,
            page_number=page,
            game=game,
        )
        for table in tables:
            materialized_on_chunk.add(table.get("manifest_name", ""))
        if not tables:
            if force:
                meta.pop("table_json", None)
                meta.pop("block_type", None)
                meta.pop("block_title", None)
                chunk_doc.metadata = meta
            continue

        _attach_table_to_chunk(meta, chunk_doc, tables)
        stats["tables_found"] += len(tables)
        logging.info(
            "pdf table parser: found %s table(s) on page %s: %s",
            len(tables),
            page,
            [t.get("manifest_name") for t in tables],
        )

    for spec in manifest.get("lookup_tables") or []:
        name = spec.get("name")
        if not name or name in materialized_on_chunk or _skip_pdf_extract(spec):
            continue
        pdf_status = (spec.get("pdf_extract") or {}).get("status")
        if pdf_status in ("todo", "hand-authored"):
            continue
        span = _page_span(spec)
        if len(span) < 2:
            continue
        merged_text = " ".join(chunks_by_page.get(p, "") for p in span)
        table = extract_table_from_text(
            merged_text, spec, page_number=span[0], allow_multi_page=True
        )
        if not table:
            continue
        anchor = page_to_item.get(span[0])
        if not anchor:
            continue
        anchor_doc: Document = anchor.get("chunk_doc")
        if anchor_doc is None:
            continue
        anchor_meta = anchor_doc.metadata or {}
        existing = _parse_tables_from_metadata(anchor_meta)
        if any(t.get("manifest_name") == name for t in existing):
            prior = next(t for t in existing if t.get("manifest_name") == name)
            if len(prior.get("rows") or []) >= len(table.get("rows") or []):
                continue
            existing = [t for t in existing if t.get("manifest_name") != name]
        _attach_table_to_chunk(anchor_meta, anchor_doc, existing + [table])
        materialized_on_chunk.add(name)
        stats["tables_found"] += 1
        logging.info(
            "pdf table parser: multi-page %s from pages %s (%s rows)",
            name,
            span,
            len(table.get("rows") or []),
        )

    return stats


def persist_chunk_table_metadata(graph, chunk_list: list[dict]) -> int:
    """Write table_json / block_type back onto :Chunk nodes (layer C evidence)."""
    updated = 0
    for item in chunk_list:
        chunk_id = item.get("chunk_id")
        chunk_doc: Document = item.get("chunk_doc")
        if not chunk_id or chunk_doc is None:
            continue

        meta = chunk_doc.metadata or {}
        table_json = meta.get("table_json")
        if not table_json:
            continue

        try:
            graph.query(
                """
                MATCH (c:Chunk {id: $chunk_id})
                SET c.table_json = $table_json,
                    c.block_type = $block_type,
                    c.block_title = $block_title,
                    c.source_format = coalesce(c.source_format, $source_format)
                """,
                {
                    "chunk_id": chunk_id,
                    "table_json": table_json,
                    "block_type": meta.get("block_type", "table"),
                    "block_title": meta.get("block_title"),
                    "source_format": meta.get("source_format", "pdf"),
                },
            )
            updated += 1
        except Exception as e:
            logging.error("pdf table parser: failed to persist chunk %s: %s", chunk_id, e)

    return updated


def tables_from_chunk_metadata(meta: dict) -> list[dict]:
    """Return table dict(s) from chunk metadata table_json."""
    return _parse_tables_from_metadata(meta)
