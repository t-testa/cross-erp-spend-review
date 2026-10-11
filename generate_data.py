"""Generate synthetic purchase-order exports from three ERPs for a fictional
manufacturer (Laurentide Fabrication, three business units).

Each ERP uses its own schema, date format, currency and part numbering, and
supplier names are typed inconsistently, the way real exports look. A small
number of deliberately bad rows are injected so the quality rules have
something to catch. Everything is seeded and reproducible. No real data.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
RAW = Path("data/raw")
REF = Path("data/reference")
USD_CAD = 1.37

# canonical supplier -> spellings seen across ERPs, plus price level and reliability
SUPPLIERS = {
    "PRECISION MACHINING CANADA": (["Precision Machining Canada Inc.", "PRECISION MACHINING CANADA", "PMC"], 1.00, 0.93),
    "BOREAL METAL WORKS": (["Boreal Metal Works Ltd", "BOREAL METAL WORKS LTD.", "Boreal Metalworks"], 1.08, 0.88),
    "LAKESHORE CASTINGS": (["Lakeshore Castings LLC", "LAKESHORE CASTINGS"], 0.95, 0.71),
    "VALLEY SHEET METAL": (["Valley Sheet Metal Co.", "VALLEY SHEET METAL"], 1.02, 0.90),
    "SAINT-LAURENT USINAGE": (["Saint-Laurent Usinage Ltee", "St-Laurent Usinage", "SAINT-LAURENT USINAGE LTEE"], 1.15, 0.95),
    "GREAT LAKES FASTENING": (["Great Lakes Fastening Corp", "GREAT LAKES FASTENING CORP."], 0.98, 0.91),
    "NORTHSHORE PLASTICS": (["Northshore Plastics Inc", "NORTHSHORE PLASTICS INC."], 1.05, 0.85),
}

CATEGORIES = {
    "Machined bracket": ("PRECISION MACHINING CANADA", "SAINT-LAURENT USINAGE", "BOREAL METAL WORKS"),
    "Sheet metal enclosure": ("VALLEY SHEET METAL", "BOREAL METAL WORKS"),
    "Aluminum casting": ("LAKESHORE CASTINGS", "BOREAL METAL WORKS"),
    "Fastener kit": ("GREAT LAKES FASTENING",),
    "Molded housing": ("NORTHSHORE PLASTICS",),
}

# canonical parts
PARTS = []
n = 1
for cat, sups in CATEGORIES.items():
    for _ in range(8):
        base = round(random.uniform(8, 60) if cat == "Fastener kit" else random.uniform(40, 900), 2)
        PARTS.append({"part_id": f"LF-{n:04d}", "desc": f"{cat} {chr(64 + (n % 26) + 1)}{n}", "base_cad": base, "suppliers": sups})
        n += 1

# each BU tends to use its own preferred supplier for a category -> price fragmentation
BU_PREF = {
    "MTL": {"Machined bracket": "SAINT-LAURENT USINAGE"},
    "OHIO": {"Machined bracket": "PRECISION MACHINING CANADA", "Aluminum casting": "LAKESHORE CASTINGS"},
    "ONT": {"Sheet metal enclosure": "BOREAL METAL WORKS", "Aluminum casting": "BOREAL METAL WORKS"},
}
BU_PREMIUM = {"MTL": 1.06, "OHIO": 0.98, "ONT": 1.03}  # negotiated price levels differ by plant


def pick_supplier(bu, part):
    cat = part["desc"].rsplit(" ", 1)[0]
    pref = BU_PREF[bu].get(cat)
    if pref and random.random() < 0.8:
        return pref
    return random.choice(part["suppliers"])


def gen_lines(bu, count):
    lines = []
    start = date(2025, 10, 1)
    for i in range(count):
        part = random.choice(PARTS)
        sup = pick_supplier(bu, part)
        names, price_lvl, otd = SUPPLIERS[sup]
        price = part["base_cad"] * price_lvl * BU_PREMIUM[bu] * random.uniform(0.97, 1.04)
        qty = random.randint(5, 120) if "Fastener" not in part["desc"] else random.randint(50, 800)
        od = start + timedelta(days=random.randint(0, 300))
        promised = od + timedelta(days=random.randint(14, 45))
        late = random.random() > otd
        received = promised + timedelta(days=random.randint(1, 20)) if late else promised - timedelta(days=random.randint(0, 5))
        lines.append(dict(po=f"{bu}-PO{10000 + i}", part=part, supplier_name=random.choice(names),
                          price_cad=price, qty=qty, od=od, promised=promised, received=received))
    return lines


def write_sap_mtl(lines):
    """Montreal plant: SAP-style export, German field names, CAD, YYYYMMDD."""
    with open(RAW / "erp_sap_montreal.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["EBELN", "MATNR", "TXZ01", "LIFNR_NAME", "NETPR", "MENGE", "WAERS", "BEDAT", "EINDT", "WE_DATE"])
        for l in lines:
            w.writerow([l["po"], l["part"]["part_id"], l["part"]["desc"], l["supplier_name"], f"{l['price_cad']:.2f}",
                        l["qty"], "CAD", l["od"].strftime("%Y%m%d"), l["promised"].strftime("%Y%m%d"), l["received"].strftime("%Y%m%d")])
        # injected problems
        w.writerow(["MTL-PO99001", "LF-0003", "Machined bracket C3", "PMC", "", 20, "CAD", "20260115", "20260201", "20260130"])  # missing price
        w.writerow(["MTL-PO99002", "LF-0010", "Sheet metal enclosure K10", "VALLEY SHEET METAL", "310.00", -5, "CAD", "20260120", "20260210", "20260209"])  # negative qty
        first = lines[0]
        w.writerow([first["po"], first["part"]["part_id"], first["part"]["desc"], first["supplier_name"], f"{first['price_cad']:.2f}",
                    first["qty"], "CAD", first["od"].strftime("%Y%m%d"), first["promised"].strftime("%Y%m%d"), first["received"].strftime("%Y%m%d")])  # duplicate


def write_epicor_ohio(lines):
    """Ohio plant: Epicor-style export, own part numbers, USD, MM/DD/YYYY."""
    with open(RAW / "erp_epicor_ohio.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["PONum", "PartNum", "PartDescription", "VendorName", "UnitCost", "OrderQty", "CurrencyCode", "OrderDate", "DueDate", "ReceiptDate"])
        for l in lines:
            w.writerow([l["po"], "OH-" + l["part"]["part_id"][3:], l["part"]["desc"], l["supplier_name"], f"{l['price_cad'] / USD_CAD:.2f}",
                        l["qty"], "USD", l["od"].strftime("%m/%d/%Y"), l["promised"].strftime("%m/%d/%Y"), l["received"].strftime("%m/%d/%Y")])
        w.writerow(["OHIO-PO99003", "OH-0021", "Aluminum casting V21", "Lakeshore Castings LLC", "412.00", 30, "MXN", "02/03/2026", "03/01/2026", "03/02/2026"])  # unknown currency
        w.writerow(["OHIO-PO99004", "OH-0005", "Machined bracket F5", "PMC", "88.10", 40, "USD", "13/45/2026", "03/01/2026", "03/02/2026"])  # bad date


def write_excel_ont(lines):
    """Ontario plant: spreadsheet export, free-text headers, CAD implied, ISO dates."""
    with open(RAW / "erp_excel_ontario.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["PO #", "Item", "Description", "Vendor", "Price", "Qty", "Date", "Promised", "Received"])
        for l in lines:
            w.writerow([l["po"], "ON" + l["part"]["part_id"][3:], l["part"]["desc"], l["supplier_name"], f"{l['price_cad']:.2f}",
                        l["qty"], l["od"].isoformat(), l["promised"].isoformat(), l["received"].isoformat()])
        w.writerow(["ONT-PO99005", "ON0099", "Unknown widget", "Boreal Metal Works Ltd", "55.00", 10, "2026-02-10", "2026-03-01", "2026-03-01"])  # part not in crosswalk


def write_reference():
    with open(REF / "part_crosswalk.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "local_part", "part_id"])
        for p in PARTS:
            num = p["part_id"][3:]
            w.writerow(["sap_montreal", p["part_id"], p["part_id"]])
            w.writerow(["epicor_ohio", "OH-" + num, p["part_id"]])
            w.writerow(["excel_ontario", "ON" + num, p["part_id"]])
    with open(REF / "supplier_aliases.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alias", "supplier_id"])
        w.writerow(["PMC", "PRECISION MACHINING CANADA"])
        w.writerow(["ST-LAURENT USINAGE", "SAINT-LAURENT USINAGE"])
        w.writerow(["BOREAL METALWORKS", "BOREAL METAL WORKS"])


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)
    write_sap_mtl(gen_lines("MTL", 620))
    write_epicor_ohio(gen_lines("OHIO", 540))
    write_excel_ont(gen_lines("ONT", 480))
    write_reference()
    print("synthetic exports written to data/raw and data/reference")
