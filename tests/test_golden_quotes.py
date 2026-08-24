import json
import os

import pytest

from policyforge.rating import QuoteInput, rate_quote

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "..", "fixtures", "golden_quotes.json")

with open(FIXTURE_PATH) as f:
    GOLDEN = json.load(f)["quotes"]

IDS = [g["name"] for g in GOLDEN]


def _rate(golden):
    qi = QuoteInput.make(golden["territory"], golden["driver_class"],
                         golden["tier"], golden["coverages"])
    return rate_quote(qi)


@pytest.mark.parametrize("golden", GOLDEN, ids=IDS)
def test_golden_total(golden):
    assert _rate(golden).total_cents == golden["expected_total_cents"]


@pytest.mark.parametrize("golden", GOLDEN, ids=IDS)
def test_golden_per_coverage(golden):
    quote = _rate(golden)
    got = {cq.coverage: cq.premium_cents for cq in quote.coverage_quotes}
    assert got == golden["expected_coverage_cents"]


@pytest.mark.parametrize("golden", GOLDEN, ids=IDS)
def test_golden_bi_intermediates(golden):
    quote = _rate(golden)
    bi = next(cq for cq in quote.coverage_quotes if cq.coverage == "BI")
    assert [s.cents_after for s in bi.steps] == golden["bi_intermediates"]


@pytest.mark.parametrize("golden", GOLDEN, ids=IDS)
def test_golden_total_consistency(golden):
    assert sum(golden["expected_coverage_cents"].values()) == golden["expected_total_cents"]
