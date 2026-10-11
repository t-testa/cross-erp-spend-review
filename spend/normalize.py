"""Map three ERP exports onto one canonical purchase-line schema.

Every row either lands in the clean table or in the quarantine table with the
rule it broke. Nothing is silently dropped.

Rules
  R1  unit price present and > 0
  R2  quantity > 0
  R3  order, promised and received dates parse
  R4  currency is known (CAD, USD)
  R5  local part number maps to a canonical part in the crosswalk
  R6  no duplicate (source, po_id, part_id) line
"""
import re
from pathlib import Path

import pandas as pd

FX_TO_CAD = {"CAD": 1.0, "USD": 1.37}  # fixed planning rate, documented in README
CANONICAL = ["source", "po_id", "local_part", "description", "supplier_raw", "unit_price", "qty",
             "currency", "order_date", "promised_date", "received_date"]
SUFFIXES = r"\b(INC|LTD|LTEE|CORP|CO|LLC|LIMITED|CORPORATION)\b"

SOURCES = {
    "sap_montreal": dict(
        file="erp_sap_montreal.csv", datefmt="%Y%m%d",
        cols={"EBELN": "po_id", "MATNR": "local_part", "TXZ01": "description", "LIFNR_NAME": "supplier_raw",
              "NETPR": "unit_price", "MENGE": "qty", "WAERS": "currency", "BEDAT": "order_date",
              "EINDT": "promised_date", "WE_DATE": "received_date"}),
    "epicor_ohio": dict(
        file="erp_epicor_ohio.csv", datefmt="%m/%d/%Y",
        cols={"PONum": "po_id", "PartNum": "local_part", "PartDescription": "description", "VendorName": "supplier_raw",
              "UnitCost": "unit_price", "OrderQty": "qty", "CurrencyCode": "currency", "OrderDate": "order_date",
              "DueDate": "promised_date", "ReceiptDate": "received_date"}),
    "excel_ontario": dict(
        file="erp_excel_ontario.csv", datefmt="%Y-%m-%d", default_currency="CAD",
        cols={"PO #": "po_id", "Item": "local_part", "Description": "description", "Vendor": "supplier_raw",
              "Price": "unit_price", "Qty": "qty", "Date": "order_date", "Promised": "promised_date",
              "Received": "received_date"}),
}


def supplier_key(name: str) -> str:
    """Uppercase, strip punctuation and legal suffixes, collapse spaces."""
    s = str(name).upper().replace(".", " ").replace(",", " ")
    s = re.sub(SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_source(name: str, raw_dir: Path) -> pd.DataFrame:
    spec = SOURCES[name]
    df = pd.read_csv(raw_dir / spec["file"], dtype=str).rename(columns=spec["cols"])
    if "currency" not in df:
        df["currency"] = spec["default_currency"]
    df["source"] = name
    df = df[CANONICAL].copy()
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
    for c in ("order_date", "promised_date", "received_date"):
        df[c] = pd.to_datetime(df[c], format=spec["datefmt"], errors="coerce")
    return df


def normalize(raw_dir: Path, ref_dir: Path):
    lines = pd.concat([load_source(s, raw_dir) for s in SOURCES], ignore_index=True)
    lines["source_row"] = lines.groupby("source").cumcount() + 2  # +2: header row, 1-based
    xwalk = pd.read_csv(ref_dir / "part_crosswalk.csv", dtype=str)
    aliases = pd.read_csv(ref_dir / "supplier_aliases.csv", dtype=str)
    alias_map = dict(zip(aliases["alias"].map(supplier_key), aliases["supplier_id"]))

    lines = lines.merge(xwalk, on=["source", "local_part"], how="left")
    keys = lines["supplier_raw"].map(supplier_key)
    lines["supplier_id"] = keys.map(lambda k: alias_map.get(k, k))

    checks = [
        ("R1_price", ~(lines["unit_price"] > 0)),
        ("R2_qty", ~(lines["qty"] > 0)),
        ("R3_dates", lines[["order_date", "promised_date", "received_date"]].isna().any(axis=1)),
        ("R4_currency", ~lines["currency"].isin(list(FX_TO_CAD))),
        ("R5_part_crosswalk", lines["part_id"].isna()),
        ("R6_duplicate", lines.duplicated(["source", "po_id", "part_id"], keep="first")),
    ]
    lines["failed_rule"] = None
    for rule, mask in checks:  # first failing rule wins
        lines.loc[mask & lines["failed_rule"].isna(), "failed_rule"] = rule

    quarantine = lines[lines["failed_rule"].notna()].copy()
    clean = lines[lines["failed_rule"].isna()].drop(columns="failed_rule").copy()
    clean["unit_price_cad"] = (clean["unit_price"] * clean["currency"].map(FX_TO_CAD)).round(2)
    clean["spend_cad"] = (clean["unit_price_cad"] * clean["qty"]).round(2)
    clean["on_time"] = clean["received_date"] <= clean["promised_date"]
    clean["business_unit"] = clean["source"].map({"sap_montreal": "Montreal", "epicor_ohio": "Ohio", "excel_ontario": "Ontario"})
    return clean.reset_index(drop=True), quarantine.reset_index(drop=True)
