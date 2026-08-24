"""Property style invariant sweeps over random settlement inputs.

For each settlement type this module throws a large seeded random input set
at the calculator and counts invariant violations. The test suite asserts
the counts are zero, and running the module directly writes the counts to
results/property_checks.json:

    python -m policyforge.property_checks

Invariants checked:
  * collision: 0 <= payment <= max(0, acv - deductible), payment <= loss,
    and the deductible is applied exactly once (payment == covered - ded
    whenever covered > ded).
  * BI: each payment >= 0, each payment <= per person limit, each payment
    <= that claimant's loss, and total <= per occurrence limit, with the
    total exactly equal to the occurrence limit whenever the capped demand
    exceeds it.
  * coinsurance: 0 <= payment <= carried limit and payment <= scaled loss.
"""

import json
import random

from .claims import settle_bi, settle_coinsurance, settle_collision


def check_collision(cases: int, seed: int) -> dict:
    rng = random.Random(seed)
    violations = 0
    for _ in range(cases):
        acv = rng.randrange(1, 5000001)
        ded = rng.choice([0, 25000, 50000, 100000])
        loss = rng.randrange(0, acv + 1000000)
        s = settle_collision(loss, acv, ded)
        ok = (0 <= s.payment_cents <= max(0, acv - ded)
              and s.payment_cents <= loss
              and (s.covered_loss_cents <= ded or
                   s.payment_cents == s.covered_loss_cents - ded))
        if not ok:
            violations += 1
    return {"cases": cases, "seed": seed, "violations": violations}


def check_bi(cases: int, seed: int) -> dict:
    rng = random.Random(seed)
    violations = 0
    for _ in range(cases):
        per_person = rng.randrange(1, 10000001)
        per_occ = per_person * rng.randrange(1, 4)
        k = rng.randrange(1, 6)
        losses = [rng.randrange(0, per_person * 3 + 1) for _ in range(k)]
        s = settle_bi(losses, per_person, per_occ)
        capped_demand = sum(min(l, per_person) for l in losses)
        ok = (all(0 <= p <= per_person for p in s.payments_cents)
              and all(p <= l for p, l in zip(s.payments_cents, losses))
              and s.total_cents <= per_occ
              and (capped_demand <= per_occ or s.total_cents == per_occ))
        if not ok:
            violations += 1
    return {"cases": cases, "seed": seed, "violations": violations}


def check_coinsurance(cases: int, seed: int) -> dict:
    rng = random.Random(seed)
    violations = 0
    for _ in range(cases):
        value = rng.randrange(1, 10000001)
        pct = rng.choice([500, 800, 900, 1000])
        carried = rng.randrange(1, value + 1)
        ded = rng.choice([0, 50000, 100000, 250000])
        loss = rng.randrange(0, value + 1)
        s = settle_coinsurance(loss, value, pct, carried, ded)
        ok = (0 <= s.payment_cents <= carried
              and s.payment_cents <= s.scaled_loss_cents)
        if not ok:
            violations += 1
    return {"cases": cases, "seed": seed, "violations": violations}


def run_all(cases_each: int = 100000, seed: int = 424242) -> dict:
    return {
        "collision": check_collision(cases_each, seed),
        "bi": check_bi(cases_each, seed + 1),
        "coinsurance": check_coinsurance(cases_each, seed + 2),
        "total_cases": cases_each * 3,
    }


def main() -> None:  # pragma: no cover
    payload = run_all()
    payload["total_violations"] = sum(
        payload[k]["violations"] for k in ("collision", "bi", "coinsurance"))
    with open("results/property_checks.json", "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    main()
