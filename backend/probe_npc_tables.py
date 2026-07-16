"""Probe NPC/location table extraction from mork-borg.pdf."""
import sys
from pathlib import Path

from fitz import open as fitz_open

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.pdf_table_parser import extract_table_from_text

PDF = Path(__file__).resolve().parents[1] / "mork-borg.pdf"


def d4_index():
    return {"type": "d6", "values": [1, 2, 3, 4]}


def trial(name, pages, header, index_cfg, min_r, max_r, stop=None):
    spec = {
        "name": name,
        "pages": str(pages[0]) if len(pages) == 1 else f"{pages[0]}-{pages[-1]}",
        "columns": [
            {"name": "index", "role": "index"},
            {"name": "result", "role": "result"},
        ],
        "pdf_extract": {
            "status": "verified",
            "header_patterns": [header],
            "index": index_cfg,
            "min_rows": min_r,
            "max_rows": max_r,
            "stop_before": stop or [],
        },
    }
    doc = fitz_open(PDF)
    text = " ".join(doc[p - 1].get_text() for p in pages)
    doc.close()
    table = extract_table_from_text(
        text, spec, page_number=pages[0], allow_multi_page=len(pages) > 1
    )
    rows = len(table["rows"]) if table else 0
    status = "OK" if rows == max_r else ("PARTIAL" if rows else "MISS")
    print(f"{status:7} {name:32} p{pages} rows={rows}/{max_r}")
    if table and rows and rows <= 2:
        for row in table["rows"]:
            print(f"        {row[0]}: {str(row[1])[:70]}")
    return table


def main():
    d4 = d4_index()
    d6 = {"type": "d6"}

    # --- rules / powers ---
    trial("BrokenTable", [29], r"Broken\s*\(d4\)", d4, 4, 4)
    trial("InitiativeTable", [30], r"Initiative\s*\(d6\)", d6, 6, 6)
    trial(
        "FoulPsychopompSummonTable",
        [35],
        r"Foul Psychompomp:?\s*Summon\s*\(d6\)",
        d6,
        6,
        6,
        stop=[r"The Basilisks Demand"],
    )
    trial(
        "ToLeaveTable",
        [45],
        r"To leave\s*\(d4\)",
        d4,
        4,
        4,
        stop=[r"Optional Classes"],
    )

    # --- optional class equipment (not yet in manifest) ---
    trial(
        "GutterbornSpecialtyTable",
        [49],
        r"one specialty\s*\(d6\)",
        d6,
        6,
        6,
        stop=[r"Eldritch Origins"],
    )
    trial(
        "EsotericHermitEquipmentTable",
        [51],
        r"begin with one of the following\s*\(d6\)",
        d6,
        6,
        6,
        stop=[r"Things were going"],
    )
    trial(
        "HereticalPriestEquipmentTable",
        [55],
        r"begin with one of the following\s*\(d6\)",
        d6,
        6,
        6,
        stop=[r"Abilities"],
    )
    trial("WieldsTable", [59], r"Wields\s*\(d4\)", d4, 4, 4)

    # --- NPC generators (4 spreads pp.64-67) ---
    for page, tag in [(64, "A"), (65, "B"), (66, "C"), (67, "D")]:
        trial(
            f"NpcTraitTable{tag}",
            [page],
            r"Traits?\s*\(d4\)",
            d4,
            4,
            4,
            stop=[r"Specialit", r"Specialty"],
        )
        trial(
            f"NpcSpecialtyTable{tag}",
            [page],
            r"Specialit(?:y|ies)\s*\(d4\)",
            d4,
            4,
            4,
            stop=[r"Values\s*\(d6\)"],
        )
        trial(
            f"NpcValuesTable{tag}",
            [page],
            r"Values\s*\(d6\)",
            d6,
            6,
            6,
        )

    # --- adventure/location (remaining) ---
    trial("StatusTable", [71], r"Status\s*\(d6\)", d6, 6, 6, stop=[r"Inactive"])
    trial(
        "InactiveBecauseTable",
        [71],
        r"Inactive, because\s*\(d4\)",
        d4,
        4,
        4,
    )
    trial(
        "FloodingWithTable",
        [72],
        r"slowly flooding with\s*\(d4\)",
        d4,
        4,
        4,
        stop=[r"Who or what dwells"],
    )
    trial(
        "InscriptionMotifsTable",
        [73],
        r"motifs are\s*\(d6\)",
        d6,
        6,
        6,
        stop=[r"Shelves with"],
    )
    trial(
        "ShelvesWithTable",
        [74],
        r"Shelves with\s*\(d4\)",
        d4,
        4,
        4,
        stop=[r"Sacrificial altar"],
    )
    trial("SacrificialAltarTable", [74], r"Sacrificial altar\s*\(d4\)", d4, 4, 4)


if __name__ == "__main__":
    main()
