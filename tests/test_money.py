import pytest

from policyforge.money import apply_factor, fmt_cents, round_half_up_div


@pytest.mark.parametrize("n,d,expected", [
    (0, 1000, 0),
    (12112500, 1000, 12113),   # exactly half rounds up
    (12112499, 1000, 12112),   # just under half rounds down
    (12112501, 1000, 12113),
    (20081250, 1000, 20081),   # 0.25 of a cent rounds down
    (40162500, 1000, 40163),   # 0.50 of a cent rounds up
    (7, 2, 4),
    (5, 5, 1),
])
def test_round_half_up_div(n, d, expected):
    assert round_half_up_div(n, d) == expected


def test_round_half_up_div_rejects_bad_inputs():
    with pytest.raises(ValueError):
        round_half_up_div(-1, 1000)
    with pytest.raises(ValueError):
        round_half_up_div(1, 0)


@pytest.mark.parametrize("cents,factor,expected", [
    (24000, 1100, 26400),
    (42240, 1180, 49843),  # 49843.2 rounds down
    (14250, 850, 12113),   # 12112.5 rounds up
    (100, 1000, 100),      # identity factor
    (100, 0, 0),           # zero factor
])
def test_apply_factor(cents, factor, expected):
    assert apply_factor(cents, factor) == expected


def test_apply_factor_rejects_negative():
    with pytest.raises(ValueError):
        apply_factor(-1, 1000)
    with pytest.raises(ValueError):
        apply_factor(1, -1)


@pytest.mark.parametrize("cents,expected", [
    (158611, "$1586.11"),
    (0, "$0.00"),
    (5, "$0.05"),
    (-2500, "-$25.00"),
])
def test_fmt_cents(cents, expected):
    assert fmt_cents(cents) == expected
