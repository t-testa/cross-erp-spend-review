-- All views read from the clean `lines` table produced by spend/normalize.py.
-- Each view is plain SQL so it can be pointed at Metabase or any BI tool unchanged.

-- Spend by business unit
CREATE OR REPLACE VIEW v_spend_by_bu AS
SELECT business_unit, ROUND(SUM(spend_cad), 0) AS spend_cad, COUNT(*) AS po_lines
FROM lines GROUP BY business_unit ORDER BY spend_cad DESC;

-- Supplier concentration: share of total spend and HHI (0 to 10,000)
CREATE OR REPLACE VIEW v_supplier_share AS
SELECT supplier_id,
       ROUND(SUM(spend_cad), 0) AS spend_cad,
       ROUND(100.0 * SUM(spend_cad) / (SELECT SUM(spend_cad) FROM lines), 1) AS share_pct
FROM lines GROUP BY supplier_id ORDER BY spend_cad DESC;

CREATE OR REPLACE VIEW v_concentration AS
SELECT ROUND(SUM(share_pct * share_pct), 0) AS hhi,
       (SELECT ROUND(SUM(share_pct), 1) FROM (SELECT share_pct FROM v_supplier_share ORDER BY share_pct DESC LIMIT 3)) AS top3_share_pct
FROM v_supplier_share;

-- Price benchmark per part: lowest average unit price achieved by any
-- business unit + supplier pair with at least 3 purchase lines (avoids one-off quotes)
CREATE OR REPLACE VIEW v_part_pairs AS
SELECT part_id, business_unit, supplier_id, AVG(unit_price_cad) AS avg_price, COUNT(*) AS n
FROM lines GROUP BY part_id, business_unit, supplier_id;

CREATE OR REPLACE VIEW v_part_benchmark AS
SELECT part_id, MIN(avg_price) AS benchmark_price_cad,
       ROUND(MAX(avg_price) / MIN(avg_price) - 1, 3) AS price_spread
FROM v_part_pairs WHERE n >= 3 GROUP BY part_id;

-- Parts bought from only one supplier anywhere in the company
CREATE OR REPLACE VIEW v_single_source AS
SELECT part_id FROM lines GROUP BY part_id HAVING COUNT(DISTINCT supplier_id) = 1;

-- Price-harmonization gap: what was paid above the internal benchmark
CREATE OR REPLACE VIEW v_price_gap_lines AS
SELECT l.*, b.benchmark_price_cad, b.price_spread,
       GREATEST(l.unit_price_cad - b.benchmark_price_cad, 0) * l.qty AS gap_cad
FROM lines l JOIN v_part_benchmark b USING (part_id);

CREATE OR REPLACE VIEW v_savings_by_part AS
SELECT part_id, ANY_VALUE(description) AS description,
       ROUND(SUM(spend_cad), 0) AS spend_cad, ROUND(SUM(gap_cad), 0) AS gap_cad,
       ANY_VALUE(price_spread) AS price_spread
FROM v_price_gap_lines GROUP BY part_id ORDER BY gap_cad DESC;

CREATE OR REPLACE VIEW v_savings_by_bu AS
SELECT business_unit, ROUND(SUM(spend_cad), 0) AS spend_cad, ROUND(SUM(gap_cad), 0) AS gap_cad,
       ROUND(100.0 * SUM(gap_cad) / SUM(spend_cad), 1) AS gap_pct
FROM v_price_gap_lines GROUP BY business_unit ORDER BY gap_cad DESC;

CREATE OR REPLACE VIEW v_gap_by_bu_supplier AS
SELECT business_unit, supplier_id, ROUND(SUM(spend_cad), 0) AS spend_cad, ROUND(SUM(gap_cad), 0) AS gap_cad
FROM v_price_gap_lines GROUP BY business_unit, supplier_id ORDER BY gap_cad DESC;

-- On-time delivery by supplier
CREATE OR REPLACE VIEW v_otd_by_supplier AS
SELECT supplier_id, COUNT(*) AS deliveries,
       ROUND(100.0 * AVG(CASE WHEN on_time THEN 1 ELSE 0 END), 1) AS otd_pct,
       ROUND(AVG(CASE WHEN NOT on_time THEN DATE_DIFF('day', promised_date, received_date) END), 1) AS avg_days_late
FROM lines GROUP BY supplier_id ORDER BY otd_pct;
