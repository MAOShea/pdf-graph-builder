"""One-off: merge missing lookup_tables entries from _manifest_snapshot.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUR = ROOT / "games/mork-borg/ingest-manifest.json"
OLD = Path(__file__).resolve().parent / "_manifest_snapshot.json"

ADD_ORDER = [
    "TrapsTable",
    "WeatherTable",
    "OccultTreasuresTable",
    "NameTable",
    "BasilisksDemandTable",
    "ArcaneCatastrophesTable",
    "AdventureSparkTable",
    "WanderTable",
    "DwellsHereTable",
    "ImminentDangerTable",
    "DistinctiveFeatureTable",
]


def patch(spec: dict) -> dict:
    spec = json.loads(json.dumps(spec))
    name = spec["name"]
    spec["source_ref"] = "MÖRK BORG BARE BONES EDITION.pdf"

    if name == "NameTable":
        spec["pages"] = "2"
        spec["hand_authored"] = {
            "file": "games/mork-borg/hand-authored-overrides/name-table.json",
            "skip_pdf_extract": True,
        }
        spec["pdf_extract"] = {
            "status": "hand-authored",
            "header_patterns": ["d6\\s+d8\\s+Name", "Name table"],
            "index": {"type": "d6_x_d8"},
            "min_rows": 48,
            "max_rows": 48,
            "multi_table_page": False,
        }
        spec["note"] = (
            "d6×d8 name grid — hand-authored from name-table.json; "
            "PDF side-by-side layout not reliably parseable."
        )
        return spec

    pe = dict(spec.get("pdf_extract") or {})
    pe["status"] = "verified"

    if name == "BasilisksDemandTable":
        pe.setdefault("min_rows", 20)
        pe.setdefault("max_rows", 20)
    elif name == "ArcaneCatastrophesTable":
        spec["pages"] = "43-45"
        pe["min_rows"] = 20
        pe["max_rows"] = 20
    elif name == "AdventureSparkTable":
        spec["pages"] = "69-70"
        pe["index"] = {"type": "d100_pairs"}
        pe["min_rows"] = 50
        pe["max_rows"] = 50
    elif name == "WanderTable":
        pe["min_rows"] = 12
        pe["max_rows"] = 12
    elif name in ("DwellsHereTable", "DistinctiveFeatureTable"):
        pe["min_rows"] = 12
        pe["max_rows"] = 12
    elif name == "ImminentDangerTable":
        pe["min_rows"] = 10
        pe["max_rows"] = 10

    spec["pdf_extract"] = pe
    return spec


def main():
    cur = json.loads(CUR.read_text(encoding="utf-8"))
    old_by = {t["name"]: t for t in json.loads(OLD.read_text(encoding="utf-8"))["lookup_tables"]}
    existing = {t["name"] for t in cur["lookup_tables"]}

    early_names = {"TrapsTable", "WeatherTable", "OccultTreasuresTable", "NameTable"}
    to_add = [patch(old_by[n]) for n in ADD_ORDER if n not in existing]
    if not to_add:
        print("merge_lookup_tables: nothing to add")
        return

    lt = cur["lookup_tables"]
    idx = next(i for i, t in enumerate(lt) if t["name"] == "CorpsePlunderTable") + 1
    early = [t for t in to_add if t["name"] in early_names]
    late = [t for t in to_add if t["name"] not in early_names]
    lt[idx:idx] = early
    lt.extend(late)

    cur["version"] = "0.3.2"
    cur["verified_date"] = "2026-07-15"
    CUR.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("merge_lookup_tables: added", [t["name"] for t in to_add])


if __name__ == "__main__":
    main()
