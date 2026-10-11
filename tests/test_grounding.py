from spend.grounding import check

METRICS = {"total": 45663085, "gap_pct": 8.3, "spread": 0.258, "lines": 1640}


def test_rounded_figures_in_any_unit_pass():
    memo = "Spend was $45.7M, a gap of 8.3%, with a 26% spread across 1,640 lines."
    assert check(memo, METRICS)["ungrounded"] == []


def test_invented_figure_is_flagged():
    memo = "Spend was $45.7M and savings could reach $5.2M."
    assert check(memo, METRICS)["ungrounded"] == ["$5.2M"]


def test_wrong_rounding_is_flagged():
    assert check("Spend was $45.9M.", METRICS)["ungrounded"] == ["$45.9M"]


def test_part_numbers_are_not_treated_as_figures():
    assert check("Part LF-0007 leads.", METRICS)["checked"] == 0
