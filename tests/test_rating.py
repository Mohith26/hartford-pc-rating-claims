import pytest

from policyforge.rate_tables import default_tables, revised_tables
from policyforge.rating import QuoteInput, rate_quote


def _simple_input(**overrides):
    kwargs = dict(territory="T2", driver_class="ADULT", tier="STANDARD",
                  coverages={"BI": "25/50", "PD": "25"})
    kwargs.update(overrides)
    return QuoteInput.make(**kwargs)


def test_determinism_same_input_same_premium():
    qi = _simple_input()
    premiums = {rate_quote(qi).total_cents for _ in range(50)}
    assert len(premiums) == 1


def test_total_is_sum_of_coverage_premiums():
    q = rate_quote(_simple_input(coverages={"BI": "50/100", "PD": "50", "COLL": "500"}))
    assert q.total_cents == sum(cq.premium_cents for cq in q.coverage_quotes)


def test_every_intermediate_exposed_in_order():
    q = rate_quote(_simple_input())
    for cq in q.coverage_quotes:
        labels = [s.label for s in cq.steps]
        assert labels == ["base", "territory", "driver_class", "tier", "option"]
        assert all(isinstance(s.cents_after, int) for s in cq.steps)


def test_factor_chain_hand_check_single_coverage():
    # BI, T2 (1.100), YOUTH (1.600), STANDARD (1.000), 50/100 (1.180):
    # 24000 -> 26400 -> 42240 -> 42240 -> 49843 (49843.2 rounds down)
    q = rate_quote(QuoteInput.make("T2", "YOUTH", "STANDARD", {"BI": "50/100"}))
    (bi,) = q.coverage_quotes
    assert [s.cents_after for s in bi.steps] == [24000, 26400, 42240, 42240, 49843]
    assert q.total_cents == 49843


@pytest.mark.parametrize("territory,expected", [("T1", 950), ("T2", 1100), ("T3", 1275)])
def test_territory_factor_applied(territory, expected):
    q = rate_quote(QuoteInput.make(territory, "ADULT", "STANDARD", {"BI": "25/50"}))
    assert q.coverage_quotes[0].steps[1].factor_milli == expected


@pytest.mark.parametrize("tier,factor", [("PREFERRED", 850), ("STANDARD", 1000), ("NONSTANDARD", 1450)])
def test_tier_factor_applied(tier, factor):
    q = rate_quote(QuoteInput.make("T1", "ADULT", tier, {"PD": "25"}))
    assert q.coverage_quotes[0].steps[3].factor_milli == factor


def test_coverage_order_is_canonical():
    qi = QuoteInput.make("T1", "ADULT", "STANDARD",
                         {"RENT": "30/900", "BI": "25/50", "COLL": "500"})
    assert [c for c, _ in qi.coverages] == ["BI", "COLL", "RENT"]


@pytest.mark.parametrize("field,value", [
    ("territory", "T9"),
    ("driver_class", "TEEN"),
    ("tier", "ULTRA"),
])
def test_unknown_rating_keys_raise(field, value):
    with pytest.raises(ValueError):
        rate_quote(_simple_input(**{field: value}))


def test_unknown_coverage_option_raises():
    with pytest.raises(ValueError):
        rate_quote(_simple_input(coverages={"BI": "999/999"}))


def test_unknown_coverage_code_raises():
    with pytest.raises(ValueError):
        QuoteInput.make("T1", "ADULT", "STANDARD", {"UMBRELLA": "1"})


def test_empty_coverages_raise():
    with pytest.raises(ValueError):
        QuoteInput.make("T1", "ADULT", "STANDARD", {})


def test_revised_tables_only_changes_target_cell():
    revised = revised_tables({("territory", "T3"): 1350})
    base = default_tables()
    assert revised["territory"]["T3"] == 1350
    assert revised["territory"]["T1"] == base["territory"]["T1"]
    assert revised["tier"] == base["tier"]
    # and the original defaults were not mutated
    assert default_tables()["territory"]["T3"] == 1275


def test_revised_tables_rejects_unknown_path():
    with pytest.raises(KeyError):
        revised_tables({("territory", "T99"): 1000})


def test_rating_with_revised_tables_moves_premium():
    qi = QuoteInput.make("T3", "ADULT", "STANDARD", {"BI": "25/50"})
    old = rate_quote(qi, default_tables()).total_cents
    new = rate_quote(qi, revised_tables({("territory", "T3"): 1350})).total_cents
    assert new > old
