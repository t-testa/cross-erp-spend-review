from pathlib import Path

import pandas as pd

from spend.normalize import normalize, supplier_key

ROOT = Path(__file__).resolve().parent.parent


def test_supplier_key_strips_case_punctuation_and_suffixes():
    assert supplier_key("Boreal Metal Works Ltd") == "BOREAL METAL WORKS"
    assert supplier_key("BOREAL METAL WORKS LTD.") == "BOREAL METAL WORKS"
    assert supplier_key("Saint-Laurent Usinage Ltee") == "SAINT-LAURENT USINAGE"
    assert supplier_key("Great Lakes Fastening Corp.") == "GREAT LAKES FASTENING"


def test_every_raw_row_is_either_clean_or_quarantined():
    clean, quarantine = normalize(ROOT / "data/raw", ROOT / "data/reference")
    raw_rows = sum(len(pd.read_csv(f)) for f in (ROOT / "data/raw").glob("*.csv"))
    assert len(clean) + len(quarantine) == raw_rows


def test_each_injected_problem_is_caught_by_its_rule():
    _, quarantine = normalize(ROOT / "data/raw", ROOT / "data/reference")
    by_po = dict(zip(quarantine["po_id"], quarantine["failed_rule"]))
    assert by_po["MTL-PO99001"] == "R1_price"
    assert by_po["MTL-PO99002"] == "R2_qty"
    assert by_po["OHIO-PO99004"] == "R3_dates"
    assert by_po["OHIO-PO99003"] == "R4_currency"
    assert by_po["ONT-PO99005"] == "R5_part_crosswalk"
    assert "R6_duplicate" in set(quarantine["failed_rule"])


def test_aliases_resolve_and_usd_converts_to_cad():
    clean, _ = normalize(ROOT / "data/raw", ROOT / "data/reference")
    assert "PMC" not in set(clean["supplier_id"])
    assert clean["supplier_id"].nunique() == 7
    ohio = clean[clean["source"] == "epicor_ohio"].iloc[0]
    assert round(ohio["unit_price"] * 1.37, 2) == ohio["unit_price_cad"]
