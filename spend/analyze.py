"""Run the SQL views over the clean lines and collect the metrics that feed
the dashboard and the executive memo. Every number the memo is allowed to use
comes from metrics.json."""
import json
from pathlib import Path

import duckdb
import pandas as pd

SQL = Path(__file__).resolve().parent.parent / "sql" / "analysis.sql"
CAPTURE_RATE = 0.5  # conservative scenario: close half of the gap


def analyze(clean: pd.DataFrame, quarantine: pd.DataFrame) -> dict:
    con = duckdb.connect()
    con.register("lines", clean)
    con.execute(SQL.read_text())
    q = lambda v: con.execute(f"SELECT * FROM {v}").df()

    total = float(clean["spend_cad"].sum())
    by_part = q("v_savings_by_part")
    gap = float(by_part["gap_cad"].sum())
    conc = q("v_concentration").iloc[0]
    otd = q("v_otd_by_supplier")
    share = q("v_supplier_share")
    return {
        "scope": {
            "business_units": int(clean["business_unit"].nunique()),
            "erp_sources": int(clean["source"].nunique()),
            "po_lines_clean": int(len(clean)),
            "po_lines_quarantined": int(len(quarantine)),
            "quarantine_by_rule": quarantine["failed_rule"].value_counts().sort_index().to_dict(),
            "supplier_spellings": int(clean["supplier_raw"].nunique()),
            "suppliers_resolved": int(clean["supplier_id"].nunique()),
            "parts": int(clean["part_id"].nunique()),
        },
        "total_spend_cad": round(total),
        "spend_by_bu": q("v_spend_by_bu").to_dict("records"),
        "supplier_share": share.to_dict("records"),
        "concentration": {"hhi": int(conc["hhi"]), "top3_share_pct": float(conc["top3_share_pct"]),
                          "single_source_parts": int(len(q("v_single_source")))},
        "price_gap": {
            "full_gap_cad": round(gap),
            "full_gap_pct_of_spend": round(100 * gap / total, 1),
            "capture_rate": CAPTURE_RATE,
            "conservative_savings_cad": round(gap * CAPTURE_RATE),
            "top_parts": by_part.head(5).to_dict("records"),
            "by_bu": q("v_savings_by_bu").to_dict("records"),
            "top_bu_supplier_gaps": q("v_gap_by_bu_supplier").head(3).to_dict("records"),
            "parts_with_spread_over_10pct": int((by_part["price_spread"] > 0.10).sum()),
        },
        "otd_by_supplier": otd.to_dict("records"),
    }


def save(metrics: dict, out: Path):
    out.write_text(json.dumps(metrics, indent=2, default=str))
