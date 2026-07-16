"""Manifest helper for NPC/location tables; materialization uses ingest_tables.py."""
import json
import subprocess
import sys
from pathlib import Path

from src.ingest_manifest import manifest_path

D4_COL = [
    {"name": "d4", "role": "index", "position": 0},
    {"name": "result", "role": "result", "position": 1},
]
D6_COL = [
    {"name": "d6", "role": "index", "position": 0},
    {"name": "result", "role": "result", "position": 1},
]
RESULT_COL = [
    {"name": "index", "role": "index", "position": 0},
    {"name": "result", "role": "result", "position": 1},
]


def _d4_index():
    return {"type": "d6", "values": [1, 2, 3, 4]}


def _entry(
    name: str,
    pages: str,
    columns: list,
    header: str,
    index: dict,
    *,
    min_rows: int,
    max_rows: int,
    stop_before: list | None = None,
    dotted: bool = False,
    phase: int = 3,
    parent_bundle: str | None = None,
    note: str | None = None,
) -> dict:
    spec: dict = {
        "name": name,
        "phase": phase,
        "instance_of": "LookupTable",
        "source_ref": "MÖRK BORG BARE BONES EDITION.pdf",
        "pages": pages,
        "columns": columns,
        "acceptance_rows": [],
        "pdf_extract": {
            "status": "verified",
            "header_patterns": [header],
            "index": index,
            "min_rows": min_rows,
            "max_rows": max_rows,
            "stop_before": stop_before or [],
            "multi_table_page": True,
        },
    }
    if dotted:
        spec["pdf_extract"]["dotted_index"] = True
    if parent_bundle:
        spec["parent_bundle"] = parent_bundle
    if note:
        spec["note"] = note
    return spec


NPC_LOCATION_TABLES = [
    _entry("BrokenTable", "29", D4_COL, r"Broken\s*\(d4\)", _d4_index(), min_rows=4, max_rows=4),
    _entry(
        "InitiativeTable",
        "30",
        D6_COL,
        r"Initiative\s*\(d6\)",
        {"type": "range_list", "values": ["1-3", "4-6"]},
        min_rows=2,
        max_rows=2,
        stop_before=[r"Agility \+ d6"],
        note="d6 range pairs, not six separate rows.",
    ),
    _entry(
        "FoulPsychopompSummonTable",
        "35",
        D6_COL,
        r"Foul Psychompomp:?\s*Summon\s*\(d6\)",
        {"type": "d6"},
        min_rows=6,
        max_rows=6,
        stop_before=[r"The Basilisks Demand"],
    ),
    _entry(
        "ToLeaveTable",
        "45",
        D4_COL,
        r"To leave\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
        stop_before=[r"Optional Classes"],
        dotted=True,
    ),
    _entry(
        "GutterbornSpecialtyTable",
        "49",
        D6_COL,
        r"one specialty\s*\(d6\)",
        {"type": "d6"},
        min_rows=6,
        max_rows=6,
        stop_before=[r"Eldritch Origins"],
        parent_bundle="GutterbornScum",
    ),
    _entry(
        "EsotericHermitEquipmentTable",
        "51",
        D6_COL,
        r"begin with one of the following\s*\(d6\)",
        {"type": "d6"},
        min_rows=6,
        max_rows=6,
        stop_before=[r"Things were going"],
        parent_bundle="EsotericHermit",
    ),
    _entry(
        "HereticalPriestEquipmentTable",
        "55",
        D6_COL,
        r"You begin with one of the following\s*\(d6\)",
        {"type": "d6"},
        min_rows=5,
        max_rows=6,
        stop_before=[r"Abilities"],
        parent_bundle="HereticalPriest",
    ),
    _entry("WieldsTable", "59", D4_COL, r"Wields\s*\(d4\)", _d4_index(), min_rows=4, max_rows=4),
    _entry(
        "NpcTraitTable64",
        "64",
        D4_COL,
        r"Trait\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
        stop_before=[r"Specialit", r"Specialty"],
    ),
    _entry(
        "NpcSpecialtyTable64",
        "64",
        D4_COL,
        r"Speciality\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
        stop_before=[r"Values\s*\(d6\)"],
    ),
    _entry(
        "NpcValuesTable64",
        "64",
        D6_COL,
        r"Values\s*\(d6\)",
        {"type": "d6"},
        min_rows=6,
        max_rows=6,
    ),
    _entry(
        "NpcTraitTable65",
        "65",
        D4_COL,
        r"Trait\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
        stop_before=[r"Specialty\s*\(d4\)"],
    ),
    _entry(
        "NpcSpecialtyTable65",
        "65",
        D4_COL,
        r"Specialty\s*\(d4\)",
        {"type": "range_list", "values": ["1-2", "3", "4"]},
        min_rows=3,
        max_rows=3,
        stop_before=[r"Values\s*\(d6\)"],
    ),
    _entry(
        "NpcValuesTable65",
        "65",
        D6_COL,
        r"Values\s*\(d6\)",
        {"type": "d6"},
        min_rows=6,
        max_rows=6,
    ),
    _entry(
        "NpcTraitTable66",
        "66",
        D4_COL,
        r"Trait\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
        stop_before=[r"Specialit"],
    ),
    _entry(
        "NpcSpecialtyTable66",
        "66",
        D4_COL,
        r"Speciality\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
        stop_before=[r"Values\s*\(d6\)"],
    ),
    _entry(
        "NpcValuesTable66",
        "66",
        D6_COL,
        r"Values\s*\(d6\)",
        {"type": "d6"},
        min_rows=6,
        max_rows=6,
    ),
    _entry(
        "NpcTraitTable67",
        "67",
        D4_COL,
        r"Traits?\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
        stop_before=[r"Specialit"],
    ),
    _entry(
        "NpcSpecialtyTable67",
        "67",
        D4_COL,
        r"Speciality\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
        stop_before=[r"Values\s*\(d6\)"],
    ),
    _entry(
        "NpcValuesTable67",
        "67",
        D6_COL,
        r"Values\s*\(d6\)",
        {"type": "d6"},
        min_rows=6,
        max_rows=6,
    ),
    _entry(
        "StatusTable",
        "71",
        D6_COL,
        r"Status\s*\(d6\)",
        {"type": "range_list", "values": ["1-2", "3-6"]},
        min_rows=2,
        max_rows=2,
        note="Row 3-6 means inactive; use InactiveBecauseTable for the d4 sub-roll.",
    ),
    _entry(
        "InactiveBecauseTable",
        "71",
        D4_COL,
        r"Inactive, because\s*\(d4\)",
        _d4_index(),
        min_rows=4,
        max_rows=4,
    ),
    _entry(
        "InscriptionMotifsTable",
        "73",
        D6_COL,
        r"motifs are\s*\(d6\)",
        {"type": "d6"},
        min_rows=6,
        max_rows=6,
        stop_before=[r"Bloodied beds"],
        note="Nested under Sample rooms d4/d6 matrix on p.73.",
    ),
    _entry(
        "ShelvesWithTable",
        "74",
        D4_COL,
        r"Shelves with\s*\(d4\)",
        {"type": "range_list", "values": ["1-2", "3-4"]},
        min_rows=2,
        max_rows=2,
        stop_before=[r"4\s+Abyssal pits"],
        note="Sub-table when Sample rooms d6 roll is 3 on certain d4 rows.",
    ),
    _entry(
        "SacrificialAltarTable",
        "74",
        D4_COL,
        r"Sacrificial altar\s*\(d4\)",
        {"type": "range_list", "values": ["1-2", "3-4"]},
        min_rows=2,
        max_rows=2,
        stop_before=[r"4\s+Remains of a throne"],
        note="Sub-table when Sample rooms d6 roll is 3 on d4 row 4.",
    ),
]


def merge_manifest():
    path = manifest_path()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    existing = {t["name"] for t in manifest["lookup_tables"]}
    added = [t for t in NPC_LOCATION_TABLES if t["name"] not in existing]
    if not added:
        print("add_npc_location_tables: manifest already has all entries")
        return []
    manifest["lookup_tables"].extend(added)
    manifest["version"] = "0.3.3"
    manifest["verified_date"] = "2026-07-15"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"add_npc_location_tables: added {len(added)} manifest entries")
    return [t["name"] for t in added]


def main():
    added = merge_manifest()
    script = Path(__file__).resolve().parent / "ingest_tables.py"
    cmd = [sys.executable, str(script)]
    if not added:
        cmd.extend(["--tables", *[t["name"] for t in NPC_LOCATION_TABLES]])
    else:
        print("add_npc_location_tables: manifest entries added:", added)
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
