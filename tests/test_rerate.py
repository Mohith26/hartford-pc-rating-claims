import pytest

from policyforge.rate_tables import default_tables, revised_tables
from policyforge.rating import QuoteInput
from policyforge.rerate import (DEFAULT_SCENARIO, _percentile_nearest_rank,
                                _signed_change_bp, generate_book, rerate_book,
                                run_default_scenario)


def test_generate_book_is_seed_deterministic():
    a = generate_book(200, seed=5)
    b = generate_book(200, seed=5)
    assert a == b


def test_generate_book_different_seeds_differ():
    assert generate_book(200, seed=5) != generate_book(200, seed=6)


def test_generate_book_size_and_required_coverages():
    book = generate_book(500, seed=1)
    assert len(book) == 500
    for policy in book:
        codes = [c for c, _ in policy.coverages]
        assert "BI" in codes and "PD" in codes


@pytest.mark.parametrize("old,new,expected", [
    (10000, 10500, 500),
    (10000, 9500, -500),
    (10000, 10000, 0),
    (30600, 32400, 588),  # 588.23 bp rounds down
])
def test_signed_change_bp(old, new, expected):
    assert _signed_change_bp(old, new) == expected


def test_signed_change_bp_rejects_zero_old():
    with pytest.raises(ValueError):
        _signed_change_bp(0, 100)


def test_percentile_nearest_rank():
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert _percentile_nearest_rank(values, 50) == 50
    assert _percentile_nearest_rank(values, 95) == 100
    assert _percentile_nearest_rank(values, 1) == 10
    assert _percentile_nearest_rank([42], 50) == 42


def test_rerate_single_policy_hand_computed():
    # T3 ADULT STANDARD, BI 25/50 only: old 24000 x 1.275 = 30600 cents.
    # Scenario bumps T3 to 1.350: new 32400 cents, +588 bp (588.23 rounds down).
    book = [QuoteInput.make("T3", "ADULT", "STANDARD", {"BI": "25/50"})]
    result = rerate_book(book, default_tables(),
                         revised_tables({("territory", "T3"): 1350}))
    assert result.total_old_cents == 30600
    assert result.total_new_cents == 32400
    assert result.changes_bp == (588,)
    stats = result.stats
    assert stats["p50_change_bp"] == 588
    assert stats["p95_change_bp"] == 588
    assert stats["pct_policies_increased_bp"] == 10000


def test_rerate_unaffected_policy_is_zero_change():
    book = [QuoteInput.make("T1", "ADULT", "STANDARD", {"BI": "25/50"})]
    result = rerate_book(book, default_tables(),
                         revised_tables(DEFAULT_SCENARIO))
    assert result.changes_bp == (0,)
    assert result.stats["pct_policies_unchanged_bp"] == 10000


def test_rerate_default_scenario_deterministic_and_directional():
    a = run_default_scenario(n=1000, seed=99)
    b = run_default_scenario(n=1000, seed=99)
    assert a == b
    # Both scenario changes are increases, so nothing can decrease.
    assert a["pct_policies_decreased_bp"] == 0
    assert a["total_new_cents"] >= a["total_old_cents"]
    assert a["min_change_bp"] >= 0


def test_rerate_stats_percentages_sum_to_10000_bp():
    stats = run_default_scenario(n=500, seed=3)
    total = (stats["pct_policies_increased_bp"]
             + stats["pct_policies_decreased_bp"]
             + stats["pct_policies_unchanged_bp"])
    # Each share rounds independently so allow 1 bp of rounding slack.
    assert abs(total - 10000) <= 1
