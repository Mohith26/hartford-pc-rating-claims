# PolicyForge

I wanted to understand how personal auto insurance pricing and claims payouts
actually work at the arithmetic level, so I built the whole thing from scratch:
a tabular rating engine, a claims settlement calculator, and a small tool that
answers "if we change this rate factor, what happens to the whole book?"

The rule I held myself to the entire time: money is integer cents, factors are
integers scaled by 1000, and rounding is half up at documented points only.
There is not a single float anywhere in the money path, which is what makes
every quote and every settlement exactly reproducible and checkable by hand.

## How a quote is priced

Each coverage (bodily injury, property damage, collision, comprehensive,
rental) starts from a base rate in cents and walks a fixed factor chain:

```
base -> x territory -> x driver class -> x tier -> x coverage option
```

with a round half up to the cent after every multiplication, in that exact
order. The `Quote` object exposes every intermediate step, so you can sit down
with the rate tables and a piece of paper and reproduce any premium. I did
exactly that for three full policies and committed them as golden fixtures in
`fixtures/golden_quotes.json`; the tests assert the engine matches my hand
arithmetic to the cent, including the intermediates.

Rating the same input twice always gives the same premium. That sounds
obvious, but it is a tested property, not an assumption.

## How a claim is settled

`policyforge/claims.py` implements the payout math per coverage:

* Bodily injury applies the per person cap to each claimant, and if the capped
  total still exceeds the per occurrence limit it scales everyone down pro
  rata using the largest remainder method in integer cents, so the payments
  sum to exactly the occurrence limit with no lost or invented cents.
* Collision caps the loss at the vehicle's actual cash value, then subtracts
  the deductible once, floored at zero.
* Property damage is a plain min(loss, limit).
* Rental caps the daily rate, then caps the aggregate.
* A property style coverage applies a coinsurance penalty (scale the loss by
  carried over required), then the deductible, then the limit cap, in that
  fixed order.

Three invariants hold everywhere: a payment is never negative, never exceeds
its limit, and a deductible is applied exactly once. I verify this two ways.
First, a hand computed edge matrix in `tests/test_claims_edge_matrix.py`
covering losses below, at, and one cent above every deductible, limit, and
cap. Second, randomized sweeps: 100,000 seeded random cases per settlement
type (300,000 total) with zero invariant violations. The sweep numbers in
`results/property_checks.json` come from the same code the tests run.

## The re-rate tool

`python -m policyforge.rerate` builds a seeded 10,000 policy synthetic book,
rates it under the current tables and under a revised set (the default
scenario bumps territory T3 from 1.275 to 1.350 and the nonstandard tier from
1.450 to 1.550), and reports the premium change distribution in basis points.
On the committed scenario: median policy change +588 bp, 95th percentile
+1319 bp, 56.2 percent of policies increased, book level premium +542 bp.
Same seed, same numbers, every run.

## Running it

```
python3 -m venv .venv && .venv/bin/pip install -U pip pytest pytest-cov
.venv/bin/python -m pytest --cov=policyforge
.venv/bin/python -m policyforge.property_checks
.venv/bin/python -m policyforge.rerate
.venv/bin/python -m policyforge.bench
```

Measured numbers and exact reproduce commands live in `RESULTS.md` and the
`results/` folder.

## Limitations

The rate tables are invented. I picked numbers that look plausible for a six
month personal auto term, but they are not filed rates from any insurer or
regulator, and nothing here prices real insurance. Real rating plans also use
far more variables (driving record points, vehicle symbols, credit based
scores where allowed, telematics) and are built on fitted models, not a five
factor chain. The claims side handles the arithmetic of limits, deductibles,
and coinsurance, not the adjusting judgment that produces the loss number in
the first place. The pro rata occurrence rule is one reasonable convention;
real carriers may settle sequentially or by negotiation. The synthetic book
is uniform-ish random, so the re-rate distribution describes my generated
book, not any real portfolio. Benchmarks are single threaded pure Python on
Apple silicon and the settlement path is much lighter than the rating path,
which is why the throughput numbers differ by 30x.
