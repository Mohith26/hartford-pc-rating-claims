"""Tabular rating engine.

The factor chain for every coverage is fixed and documented:

    step 0: base rate (cents) for the coverage
    step 1: multiply by territory factor, round half up to a cent
    step 2: multiply by driver class factor, round half up to a cent
    step 3: multiply by tier factor, round half up to a cent
    step 4: multiply by the coverage level option factor, round half up

The rounding happens after every single multiplication, in that exact order,
so every intermediate is an integer cents amount you can check by hand. The
total premium is the plain sum of the per coverage premiums. Same input and
same tables always produce the same premium, byte for byte.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .money import apply_factor
from .rate_tables import COVERAGES, default_tables


@dataclass(frozen=True)
class QuoteInput:
    territory: str
    driver_class: str
    tier: str
    # coverage code -> option key, e.g. {"BI": "50/100", "COLL": "500"}
    coverages: Tuple[Tuple[str, str], ...]

    @staticmethod
    def make(territory: str, driver_class: str, tier: str, coverages: Dict[str, str]) -> "QuoteInput":
        ordered = tuple((c, coverages[c]) for c in COVERAGES if c in coverages)
        if len(ordered) != len(coverages):
            unknown = set(coverages) - set(COVERAGES)
            raise ValueError("unknown coverages: {}".format(sorted(unknown)))
        if not ordered:
            raise ValueError("a quote needs at least one coverage")
        return QuoteInput(territory, driver_class, tier, ordered)


@dataclass
class RatingStep:
    label: str
    factor_milli: int
    cents_after: int


@dataclass
class CoverageQuote:
    coverage: str
    option: str
    steps: List[RatingStep] = field(default_factory=list)

    @property
    def premium_cents(self) -> int:
        return self.steps[-1].cents_after


@dataclass
class Quote:
    quote_input: QuoteInput
    coverage_quotes: List[CoverageQuote]

    @property
    def total_cents(self) -> int:
        return sum(cq.premium_cents for cq in self.coverage_quotes)


def _lookup(table: dict, key: str, what: str) -> int:
    try:
        return table[key]
    except KeyError:
        raise ValueError("unknown {}: {!r}".format(what, key)) from None


def rate_quote(quote_input: QuoteInput, tables: dict = None) -> Quote:
    """Rate one policy. Every intermediate is exposed on the returned Quote."""
    if tables is None:
        tables = default_tables()

    territory_f = _lookup(tables["territory"], quote_input.territory, "territory")
    class_f = _lookup(tables["driver_class"], quote_input.driver_class, "driver class")
    tier_f = _lookup(tables["tier"], quote_input.tier, "tier")

    coverage_quotes = []
    for coverage, option in quote_input.coverages:
        base = _lookup(tables["base_rate_cents"], coverage, "coverage")
        option_f = _lookup(tables["coverage_options"][coverage], option, coverage + " option")

        steps = [RatingStep("base", 1000, base)]
        running = base
        for label, factor in (
            ("territory", territory_f),
            ("driver_class", class_f),
            ("tier", tier_f),
            ("option", option_f),
        ):
            running = apply_factor(running, factor)
            steps.append(RatingStep(label, factor, running))
        coverage_quotes.append(CoverageQuote(coverage, option, steps))

    return Quote(quote_input, coverage_quotes)
