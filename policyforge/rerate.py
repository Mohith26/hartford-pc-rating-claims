"""Book of business re-rate impact tool.

Generates a seeded synthetic book of policies, rates each one under the
current tables and under a revised table set, and reports the distribution
of the premium change. Everything is deterministic for a given seed: the
book, the ordering, and every statistic.

Percent changes are computed in basis points as integers:
    change_bp = round_half_up((new - old) * 10000 / old)
so 125 basis points means +1.25%.

Run it directly to write results/rerate_scenario.json for the default
scenario (territory T3 1.275 -> 1.350, tier NONSTANDARD 1.450 -> 1.550):

    python -m policyforge.rerate
"""

import json
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .money import round_half_up_div
from .rate_tables import default_tables, revised_tables
from .rating import QuoteInput, rate_quote

DEFAULT_SEED = 20260824
DEFAULT_BOOK_SIZE = 10000

DEFAULT_SCENARIO = {
    ("territory", "T3"): 1350,
    ("tier", "NONSTANDARD"): 1550,
}


def generate_book(n: int = DEFAULT_BOOK_SIZE, seed: int = DEFAULT_SEED) -> List[QuoteInput]:
    """A seeded synthetic book. Same n and seed always give the same book."""
    rng = random.Random(seed)
    territories = ["T1", "T2", "T3"]
    classes = ["ADULT", "YOUTH", "SENIOR"]
    tiers = ["PREFERRED", "STANDARD", "NONSTANDARD"]
    bi_opts = ["25/50", "50/100", "100/300", "250/500"]
    pd_opts = ["25", "50", "100"]
    ded_opts = ["250", "500", "1000"]
    rent_opts = ["30/900", "50/1500"]

    book = []
    for _ in range(n):
        coverages: Dict[str, str] = {
            "BI": rng.choice(bi_opts),
            "PD": rng.choice(pd_opts),
        }
        if rng.random() < 0.75:
            coverages["COLL"] = rng.choice(ded_opts)
        if rng.random() < 0.70:
            coverages["COMP"] = rng.choice(ded_opts)
        if rng.random() < 0.40:
            coverages["RENT"] = rng.choice(rent_opts)
        book.append(QuoteInput.make(
            rng.choice(territories), rng.choice(classes), rng.choice(tiers), coverages))
    return book


def _signed_change_bp(old: int, new: int) -> int:
    """Signed premium change in basis points, rounded half up on magnitude."""
    if old <= 0:
        raise ValueError("old premium must be > 0")
    diff = new - old
    magnitude = round_half_up_div(abs(diff) * 10000, old)
    return magnitude if diff >= 0 else -magnitude


def _percentile_nearest_rank(sorted_values: List[int], pct: int) -> int:
    """Nearest rank percentile on a pre sorted list, pct in [1, 100]."""
    if not sorted_values:
        raise ValueError("empty list")
    rank = round_half_up_div(pct * len(sorted_values), 100)
    rank = max(1, min(rank, len(sorted_values)))
    return sorted_values[rank - 1]


@dataclass
class RerateResult:
    book_size: int
    seed: int
    total_old_cents: int
    total_new_cents: int
    changes_bp: Tuple[int, ...]  # per policy, in book order

    @property
    def stats(self) -> dict:
        s = sorted(self.changes_bp)
        n = len(s)
        increased = sum(1 for c in s if c > 0)
        decreased = sum(1 for c in s if c < 0)
        return {
            "book_size": self.book_size,
            "seed": self.seed,
            "total_old_cents": self.total_old_cents,
            "total_new_cents": self.total_new_cents,
            "book_change_bp": _signed_change_bp(self.total_old_cents, self.total_new_cents),
            "p50_change_bp": _percentile_nearest_rank(s, 50),
            "p95_change_bp": _percentile_nearest_rank(s, 95),
            "max_change_bp": s[-1],
            "min_change_bp": s[0],
            "pct_policies_increased_bp": round_half_up_div(increased * 10000, n),
            "pct_policies_decreased_bp": round_half_up_div(decreased * 10000, n),
            "pct_policies_unchanged_bp": round_half_up_div((n - increased - decreased) * 10000, n),
        }


def rerate_book(book: List[QuoteInput], old_tables: dict, new_tables: dict,
                seed: int = DEFAULT_SEED) -> RerateResult:
    total_old = 0
    total_new = 0
    changes = []
    for policy in book:
        old = rate_quote(policy, old_tables).total_cents
        new = rate_quote(policy, new_tables).total_cents
        total_old += old
        total_new += new
        changes.append(_signed_change_bp(old, new))
    return RerateResult(len(book), seed, total_old, total_new, tuple(changes))


def run_default_scenario(n: int = DEFAULT_BOOK_SIZE, seed: int = DEFAULT_SEED) -> dict:
    book = generate_book(n, seed)
    result = rerate_book(book, default_tables(), revised_tables(DEFAULT_SCENARIO), seed)
    payload = result.stats
    payload["scenario"] = {"/".join(k): v for k, v in DEFAULT_SCENARIO.items()}
    return payload


def main() -> None:  # pragma: no cover
    payload = run_default_scenario()
    with open("results/rerate_scenario.json", "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    main()
