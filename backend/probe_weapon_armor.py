"""Find and probe weapon/armor tables in mork-borg.pdf."""
from pathlib import Path

import fitz

from src.pdf_table_parser import extract_table_from_text, _find_header, _slice_body, _index_keys, _parse_rows_sequential

pdf = Path(__file__).resolve().parents[1] / "mork-borg.pdf"
out_dir = Path(__file__).resolve().parent

doc = fitz.open(pdf)
for page_num in range(1, min(25, len(doc) + 1)):
    text = doc[page_num - 1].get_text()
    low = text.lower()
    if any(k in low for k in ("weapons", "weapon (", "armor (", "armour (", "armor table", "weapon table")):
        path = out_dir / f"probe_page_{page_num}.txt"
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.name} ({len(text)} chars)")

doc.close()

# Trial extraction patterns on saved pages
trials = [
    ("WeaponTable", r"Weapons?\s*\(d\d+\)", "d8", 8),
    ("WeaponTable_d10", r"Weapons?\s*\(d10\)", "d10", 10),
    ("WeaponTable_d6", r"Weapons?\s*\(d6\)", "d6", 6),
    ("ArmorTable", r"Armor\s*\(d\d+\)", "d6", 6),
    ("ArmorTable_d2", r"Armor\s*\(d2\)", "d2", 2),
    ("ArmorTable_d6", r"Armor\s*\(d6\)", "d6", 6),
]

for probe_file in sorted(out_dir.glob("probe_page_*.txt")):
    text = probe_file.read_text(encoding="utf-8")
    page = int(probe_file.stem.split("_")[-1])
    print(f"\n=== {probe_file.name} (book page {page}) ===")
    for label, hdr, idx_type, max_rows in trials:
        spec = {
            "name": label,
            "columns": [{"name": "d8" if "d8" in idx_type else idx_type.replace("d", "d"), "role": "index"}, {"name": "result", "role": "result"}],
            "pdf_extract": {
                "status": "verified",
                "header_patterns": [hdr],
                "index": {"type": idx_type} if idx_type != "d2" else {"type": "d6", "values": ["1", "2"]},
                "min_rows": max_rows if idx_type != "d2" else 2,
                "max_rows": max_rows if idx_type != "d2" else 2,
            },
        }
        # fix column name for d10/d6
        col = idx_type if idx_type != "d2" else "d2"
        spec["columns"][0]["name"] = col
        t = extract_table_from_text(text, spec, page_number=page)
        if t:
            print(f"  OK {label}: {len(t['rows'])} rows — first: {t['rows'][0]}")
        else:
            h = _find_header(text, [hdr])
            if h:
                body = _slice_body(text, h.end(), [])
                keys = _index_keys(spec["pdf_extract"]["index"]["type"], spec["pdf_extract"]["index"])
                if idx_type == "d2":
                    keys = ["1", "2"]
                rows = _parse_rows_sequential(body, keys, idx_type if idx_type != "d2" else "d6")
                print(f"  hdr {label}: keys={len(keys)} parsed={len(rows)}")
