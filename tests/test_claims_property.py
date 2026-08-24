"""Property style sweeps: 100k random cases per settlement type, 0 violations.

These call the same sweep functions that python -m policyforge.property_checks
uses to write results/property_checks.json, so the committed numbers and the
test suite are the same code path.
"""

from policyforge.claims import settle_bi, settle_collision
from policyforge.property_checks import check_bi, check_coinsurance, check_collision

CASES = 100000
SEED = 424242


def test_collision_invariants_100k_random_cases():
    result = check_collision(CASES, SEED)
    assert result["cases"] == CASES
    assert result["violations"] == 0


def test_bi_invariants_100k_random_cases():
    result = check_bi(CASES, SEED + 1)
    assert result["cases"] == CASES
    assert result["violations"] == 0


def test_coinsurance_invariants_100k_random_cases():
    result = check_coinsurance(CASES, SEED + 2)
    assert result["cases"] == CASES
    assert result["violations"] == 0


def test_sweeps_are_seed_deterministic():
    a = check_collision(1000, 7)
    b = check_collision(1000, 7)
    assert a == b


def test_settlement_determinism_spot_check():
    for _ in range(10):
        assert settle_collision(123456, 2000000, 50000).payment_cents == 73456
        assert settle_bi([2500000, 2500000, 2500000], 2500000, 5000000).payments_cents \
            == (1666667, 1666667, 1666666)
