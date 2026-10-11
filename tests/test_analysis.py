import pandas as pd

from spend.analyze import analyze


def _line(bu, supplier, part, price, qty):
    d = pd.Timestamp("2026-01-01")
    return dict(source=bu, business_unit=bu, po_id=f"{bu}{supplier}{price}", part_id=part, description=part,
                supplier_raw=supplier, supplier_id=supplier, unit_price_cad=price, qty=qty,
                spend_cad=price * qty, order_date=d, promised_date=d, received_date=d, on_time=True)


def test_gap_is_measured_against_cheapest_pair_with_three_lines():
    rows = [_line("A", "S1", "P1", 100, 10) for _ in range(3)]      # benchmark 100
    rows += [_line("B", "S2", "P1", 120, 10) for _ in range(3)]     # pays 20 more per unit
    rows += [_line("C", "S3", "P1", 50, 10)]                        # one-off quote, ignored as benchmark
    m = analyze(pd.DataFrame(rows), pd.DataFrame(columns=["failed_rule"]))
    assert m["price_gap"]["full_gap_cad"] == 3 * 20 * 10
    assert m["price_gap"]["conservative_savings_cad"] == 300
