"""Micro benchmarks: quotes per second and settlements per second.

Single threaded, pure Python. Run with:

    python -m policyforge.bench

Writes results/bench.json. Numbers are wall clock over the whole batch,
measured with time.perf_counter, best of 3 passes.
"""

import json
import platform
import random
import time

from .claims import settle_bi, settle_collision
from .rating import rate_quote
from .rerate import generate_book


def bench_quotes(n: int = 20000, seed: int = 7, passes: int = 3) -> dict:
    book = generate_book(n, seed)
    best = None
    for _ in range(passes):
        start = time.perf_counter()
        total = 0
        for policy in book:
            total += rate_quote(policy).total_cents
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)
    return {"n": n, "best_seconds": best, "quotes_per_sec": n / best,
            "checksum_total_cents": total}


def bench_settlements(n: int = 100000, seed: int = 11, passes: int = 3) -> dict:
    rng = random.Random(seed)
    coll_cases = [(rng.randrange(0, 3000000), 2000000, 50000) for _ in range(n // 2)]
    bi_cases = []
    for _ in range(n - n // 2):
        k = rng.randrange(1, 4)
        bi_cases.append([rng.randrange(0, 8000000) for _ in range(k)])
    best = None
    for _ in range(passes):
        start = time.perf_counter()
        checksum = 0
        for loss, acv, ded in coll_cases:
            checksum += settle_collision(loss, acv, ded).payment_cents
        for losses in bi_cases:
            checksum += settle_bi(losses, 2500000, 5000000).total_cents
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)
    return {"n": n, "best_seconds": best, "settlements_per_sec": n / best,
            "checksum_total_cents": checksum}


def main() -> None:  # pragma: no cover
    payload = {
        "machine": platform.machine(),
        "python": platform.python_version(),
        "note": "single thread, best of 3 passes, wall clock",
        "quotes": bench_quotes(),
        "settlements": bench_settlements(),
    }
    with open("results/bench.json", "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    main()
