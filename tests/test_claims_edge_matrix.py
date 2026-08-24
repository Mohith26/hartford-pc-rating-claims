"""Exhaustive hand computed edge matrix for the settlement calculators.

Every expected value in this file was worked out by hand from the documented
settlement rules: losses below, at, and just above the deductible, at and
above the ACV or limit, occurrence caps that bind exactly, and the largest
remainder pro rata split.
"""

import pytest

from policyforge.claims import (settle_bi, settle_coinsurance, settle_collision,
                                settle_pd, settle_rental)

# Collision: ACV $20,000 (2000000 cents), deductible $500 (50000 cents).
COLLISION_MATRIX = [
    (0, 2000000, 50000, 0),          # no loss
    (49999, 2000000, 50000, 0),      # just below deductible
    (50000, 2000000, 50000, 0),      # exactly at deductible
    (50001, 2000000, 50000, 1),      # one cent above deductible
    (500000, 2000000, 50000, 450000),
    (1999999, 2000000, 50000, 1949999),  # one cent below ACV
    (2000000, 2000000, 50000, 1950000),  # exactly at ACV
    (2500000, 2000000, 50000, 1950000),  # above ACV, capped
    (100, 2000000, 0, 100),          # zero deductible passes loss through
]


@pytest.mark.parametrize("loss,acv,ded,expected", COLLISION_MATRIX)
def test_collision_matrix(loss, acv, ded, expected):
    s = settle_collision(loss, acv, ded)
    assert s.payment_cents == expected
    assert s.covered_loss_cents == min(loss, acv)


# PD: limit $25,000 (2500000 cents).
PD_MATRIX = [
    (0, 2500000, 0),
    (2499999, 2500000, 2499999),  # one cent below limit
    (2500000, 2500000, 2500000),  # exactly at limit
    (2500001, 2500000, 2500000),  # one cent above limit, capped
]


@pytest.mark.parametrize("loss,limit,expected", PD_MATRIX)
def test_pd_matrix(loss, limit, expected):
    assert settle_pd(loss, limit).payment_cents == expected


# BI: per person $25,000 (2500000), per occurrence $50,000 (5000000)
# unless stated otherwise.
def test_bi_single_claimant_below_limit():
    s = settle_bi([1000000], 2500000, 5000000)
    assert s.payments_cents == (1000000,)


def test_bi_single_claimant_capped_at_per_person():
    s = settle_bi([3000000], 2500000, 5000000)
    assert s.payments_cents == (2500000,)


def test_bi_zero_loss_claimant():
    s = settle_bi([0], 2500000, 5000000)
    assert s.payments_cents == (0,)


def test_bi_occurrence_limit_binding_exactly_no_reduction():
    # Two claimants capped to 2500000 each sums to exactly the occurrence limit.
    s = settle_bi([3000000, 3000000], 2500000, 5000000)
    assert s.payments_cents == (2500000, 2500000)
    assert s.total_cents == 5000000


def test_bi_pro_rata_equal_claimants_largest_remainder():
    # Three claimants capped at 2500000 each, demand 7500000 against 5000000.
    # Floor share is 1666666 with equal remainders, so the first two claimants
    # by index each pick up one leftover cent.
    s = settle_bi([2500000, 2500000, 2500000], 2500000, 5000000)
    assert s.payments_cents == (1666667, 1666667, 1666666)
    assert s.total_cents == 5000000


def test_bi_pro_rata_unequal_claimants_hand_computed():
    # Capped demand [2500000, 1000000] = 3500000 against occurrence 3000000.
    # Floors: 2142857 (rem 500000) and 857142 (rem 3000000). The one leftover
    # cent goes to claimant 1 which has the larger remainder.
    s = settle_bi([4000000, 1000000], 2500000, 3000000)
    assert s.payments_cents == (2142857, 857143)
    assert s.total_cents == 3000000


def test_bi_intermediate_caps_exposed():
    s = settle_bi([4000000, 1000000], 2500000, 3000000)
    assert s.capped_cents == (2500000, 1000000)


@pytest.mark.parametrize("bad_call", [
    lambda: settle_bi([], 2500000, 5000000),
    lambda: settle_bi([-1], 2500000, 5000000),
    lambda: settle_bi([100], 5000000, 2500000),  # per occ < per person
    lambda: settle_bi([100], 0, 5000000),
])
def test_bi_invalid_inputs_raise(bad_call):
    with pytest.raises(ValueError):
        bad_call()


# Rental: per day cap $30 (3000), aggregate cap $900 (90000).
RENTAL_MATRIX = [
    (4500, 12, 3000, 90000, 36000),   # daily rate above per day cap
    (2500, 10, 3000, 90000, 25000),   # daily rate below per day cap
    (4500, 30, 3000, 90000, 90000),   # exactly hits aggregate cap
    (4500, 40, 3000, 90000, 90000),   # above aggregate cap
    (4500, 0, 3000, 90000, 0),        # zero days
]


@pytest.mark.parametrize("rate,days,day_cap,agg_cap,expected", RENTAL_MATRIX)
def test_rental_matrix(rate, days, day_cap, agg_cap, expected):
    assert settle_rental(rate, days, day_cap, agg_cap).payment_cents == expected


def test_rental_negative_days_raise():
    with pytest.raises(ValueError):
        settle_rental(4500, -1, 3000, 90000)


# Coinsurance: property value $40,000 (4000000), 80% clause (800 per mille),
# so the required amount is 3200000 cents.
def test_coinsurance_underinsured_hand_computed():
    # Carried 2400000 < required 3200000, penalty 2400000/3200000 = 0.75.
    # Loss 1000000 scales to 750000, minus deductible 100000 gives 650000.
    s = settle_coinsurance(1000000, 4000000, 800, 2400000, 100000)
    assert s.required_cents == 3200000
    assert s.scaled_loss_cents == 750000
    assert s.payment_cents == 650000


def test_coinsurance_fully_insured_no_penalty():
    s = settle_coinsurance(1000000, 4000000, 800, 3200000, 100000)
    assert s.scaled_loss_cents == 1000000
    assert s.payment_cents == 900000


def test_coinsurance_rounding_half_up_on_scaling():
    # 999999 * 2400000 / 3200000 = 749999.25, rounds down to 749999.
    s = settle_coinsurance(999999, 4000000, 800, 2400000, 100000)
    assert s.scaled_loss_cents == 749999
    assert s.payment_cents == 649999


def test_coinsurance_capped_at_carried_limit():
    # Total loss: scaled 3000000, minus deductible 2900000, capped at 2400000.
    s = settle_coinsurance(4000000, 4000000, 800, 2400000, 100000)
    assert s.payment_cents == 2400000


def test_coinsurance_loss_below_deductible_pays_zero():
    s = settle_coinsurance(100000, 4000000, 800, 2400000, 100000)
    assert s.scaled_loss_cents == 75000
    assert s.payment_cents == 0


def test_coinsurance_invalid_percentage_raises():
    with pytest.raises(ValueError):
        settle_coinsurance(100, 4000000, 0, 2400000, 0)
    with pytest.raises(ValueError):
        settle_coinsurance(100, 4000000, 1001, 2400000, 0)
