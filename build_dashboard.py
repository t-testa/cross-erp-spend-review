"""Build output/dashboard.html: KPI tiles, savings and supplier views, the
executive memo and the quarantine log, in one self-contained page."""
import html
import json
import re
from pathlib import Path

import pandas as pd

OUT = Path("output")
m = json.loads((OUT / "metrics.json").read_text())
quarantine = pd.read_csv(OUT / "quarantine.csv")
memo_path = OUT / "exec_memo.md" if (OUT / "exec_memo.md").exists() else Path("examples/exec_memo_sample.md")


def money(v):
    return f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v / 1e3:.0f}K"


def hbar(rows, label_key, value_key, fmt, tip, ref=None, ref_label=""):
    """Horizontal single-series bar chart as inline SVG with per-bar hover tooltips."""
    W, LW, BH, GAP = 640, 210, 22, 8
    vmax = max(r[value_key] for r in rows) if ref is None else max(100, max(r[value_key] for r in rows))
    pw = W - LW - 70
    H = len(rows) * (BH + GAP) + 10
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" class="chart">']
    for i, r in enumerate(rows):
        y = 5 + i * (BH + GAP)
        w = max(2, pw * r[value_key] / vmax)
        out.append(f'<g class="bar"><title>{html.escape(tip(r))}</title>'
                   f'<rect x="0" y="{y - 3}" width="{W}" height="{BH + 6}" fill="transparent"/>'
                   f'<text x="{LW - 10}" y="{y + 15}" text-anchor="end" class="lbl">{html.escape(str(r[label_key]) if str(r[label_key]).startswith("LF-") else str(r[label_key]).title())}</text>'
                   f'<path d="M{LW},{y} h{w - 4} a4,4 0 0 1 4,4 v{BH - 8} a4,4 0 0 1 -4,4 h-{w - 4} z" class="mark"/>'
                   f'<text x="{LW + w + 6}" y="{y + 15}" class="val">{fmt(r[value_key])}</text></g>')
    if ref is not None:
        x = LW + pw * ref / vmax
        out.append(f'<line x1="{x}" x2="{x}" y1="0" y2="{H}" class="ref"/><text x="{x + 4}" y="{H - 2}" class="muted">{ref_label}</text>')
    out.append("</svg>")
    return "".join(out)


def table(rows, cols):
    head = "".join(f"<th>{c}</th>" for c in cols.values())
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r[k]))}</td>" for k in cols) + "</tr>" for r in rows)
    return f"<details><summary>Table view</summary><div class=\"scroll\"><table><tr>{head}</tr>{body}</table></div></details>"


def md_to_html(md):
    lines, out, in_list = md.splitlines(), [], False
    inline = lambda s: re.sub(r"`(.+?)`", r"<code>\1</code>", re.sub(r"\*(.+?)\*", r"<em>\1</em>", re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(s))))
    for ln in lines:
        if ln.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(ln[2:])}</li>"); continue
        if in_list:
            out.append("</ul>"); in_list = False
        if ln.startswith("## "):
            out.append(f"<h4>{inline(ln[3:])}</h4>")
        elif ln.startswith("# "):
            out.append(f"<h3>{inline(ln[2:])}</h3>")
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


pg, sc = m["price_gap"], m["scope"]
by_bu = pg["by_bu"]
parts = pd.read_csv(OUT / "lines_clean.csv")
part_rows = (parts.groupby(["part_id", "description"]).size().reset_index()[["part_id", "description"]])
top_parts = pg["top_parts"]
otd = m["otd_by_supplier"]
share = m["supplier_share"]

tiles = [
    ("Spend analyzed", money(m["total_spend_cad"]), f'{sc["po_lines_clean"]:,} PO lines, {sc["erp_sources"]} ERPs'),
    ("Price gap vs internal benchmark", money(pg["full_gap_cad"]), f'{pg["full_gap_pct_of_spend"]}% of spend'),
    ("Conservative savings", money(pg["conservative_savings_cad"]), f'closing {int(pg["capture_rate"] * 100)}% of the gap'),
    ("Rows quarantined", str(sc["po_lines_quarantined"]), f'{sc["supplier_spellings"]} supplier spellings resolved to {sc["suppliers_resolved"]}'),
]

sections = [
    ("Where the price gap sits, by plant", "Amount paid above the best average price any plant achieved for the same part.",
     hbar(by_bu, "business_unit", "gap_cad", money, lambda r: f'{r["business_unit"]}: {money(r["gap_cad"])} gap, {r["gap_pct"]}% of {money(r["spend_cad"])} spend'),
     table(by_bu, {"business_unit": "Plant", "spend_cad": "Spend (CAD)", "gap_cad": "Gap (CAD)", "gap_pct": "Gap %"})),
    ("Top parts by price gap", "Bars show gap in CAD. Hover for the spread between cheapest and most expensive plant and supplier pair.",
     hbar([dict(r, label=f'{r["part_id"]} {r["description"]}') for r in top_parts], "label", "gap_cad", money,
          lambda r: f'{r["part_id"]}: {money(r["gap_cad"])} gap on {money(r["spend_cad"])}, {r["price_spread"] * 100:.0f}% spread'),
     table(top_parts, {"part_id": "Part", "description": "Description", "spend_cad": "Spend", "gap_cad": "Gap", "price_spread": "Spread"})),
    ("Supplier share of spend", f'Top three suppliers hold {m["concentration"]["top3_share_pct"]}% of spend. HHI {m["concentration"]["hhi"]:,}. {m["concentration"]["single_source_parts"]} parts have a single supplier.',
     hbar(share, "supplier_id", "share_pct", lambda v: f"{v}%", lambda r: f'{r["supplier_id"].title()}: {r["share_pct"]}% ({money(r["spend_cad"])})'),
     table(share, {"supplier_id": "Supplier", "spend_cad": "Spend", "share_pct": "Share %"})),
    ("On-time delivery by supplier", "Share of deliveries received on or before the promised date. Dashed line marks 90% for reference.",
     hbar(otd, "supplier_id", "otd_pct", lambda v: f"{v}%", lambda r: f'{r["supplier_id"].title()}: {r["otd_pct"]}% on time over {r["deliveries"]} deliveries, late ones {r["avg_days_late"]} days late on average', ref=90, ref_label="90%"),
     table(otd, {"supplier_id": "Supplier", "deliveries": "Deliveries", "otd_pct": "On time %", "avg_days_late": "Avg days late"})),
]

q_rows = quarantine[["source", "source_row", "po_id", "failed_rule"]].to_dict("records")
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cross-ERP Spend Review</title>
<style>
:root{{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--mark:#2a78d6;--mark-hover:#1c5cab}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--mark:#3987e5;--mark-hover:#6da7ec}}}}
:root[data-theme="dark"]{{--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--mark:#3987e5;--mark-hover:#6da7ec}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:980px;margin:0 auto;padding:24px 16px 48px}}h1{{font-size:24px;margin:0 0 4px}}.sub{{color:var(--ink2);margin:0 0 20px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:20px}}
.tile,.card{{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:16px}}
.tile .k{{color:var(--ink2);font-size:13px}}.tile .v{{font-size:28px;font-weight:650;margin:2px 0}}.tile .n{{color:var(--muted);font-size:13px}}
.card{{margin-bottom:16px}}.card h2{{font-size:16px;margin:0 0 2px}}.card p.d{{color:var(--ink2);margin:0 0 10px;font-size:13px}}
.chart{{width:100%;height:auto}}.chart .lbl,.chart .val,.chart .muted{{font-size:12px}}.chart .lbl{{fill:var(--ink2)}}.chart .val{{fill:var(--ink)}}.chart .muted{{fill:var(--muted)}}
.chart .mark{{fill:var(--mark)}}.chart .bar:hover .mark{{fill:var(--mark-hover)}}.chart .ref{{stroke:var(--muted);stroke-dasharray:4 3}}
details{{margin-top:8px;font-size:13px}}summary{{cursor:pointer;color:var(--ink2)}}table{{border-collapse:collapse;width:100%;margin-top:6px}}
td,th{{text-align:left;padding:4px 8px;border-bottom:1px solid var(--grid)}}th{{color:var(--ink2);font-weight:600}}
code{{word-break:break-word}}.scroll{{overflow-x:auto}}.memo h3{{margin-top:0}}.memo h4{{margin:14px 0 4px}}.memo ul{{padding-left:20px}}code{{font-size:12px}}
</style></head><body><main>
<h1>Cross-ERP Spend Review</h1>
<p class="sub">Laurentide Fabrication (fictional), three plants on three ERPs. Synthetic data for a prototype.</p>
<div class="tiles">{"".join(f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div><div class="n">{n}</div></div>' for k, v, n in tiles)}</div>
{"".join(f'<section class="card"><h2>{t}</h2><p class="d">{d}</p>{c}{tb}</section>' for t, d, c, tb in sections)}
<section class="card memo">{md_to_html(memo_path.read_text())}</section>
<section class="card"><h2>Quarantine log</h2><p class="d">Rows that failed a quality rule. Kept with the rule and source row so they can be fixed at source, never silently dropped.</p>
<div class="scroll"><table><tr><th>Source</th><th>Row</th><th>PO</th><th>Rule</th></tr>{"".join(f'<tr><td>{r["source"]}</td><td>{r["source_row"]}</td><td>{r["po_id"]}</td><td>{r["failed_rule"]}</td></tr>' for r in q_rows)}</table></div></section>
</main></body></html>"""
(OUT / "dashboard.html").write_text(page)
print("output/dashboard.html written")
