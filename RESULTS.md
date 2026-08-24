# Results

My benchmark and validation notes. Everything below came from actual runs on
my machine: Apple silicon (arm64), Python 3.9.6, single thread. Reproduce
commands are next to each number. Machine specific numbers will differ on
other hardware.

## Correctness

### Golden quotes

Three full policies hand computed on paper against the default tables, stored
in `fixtures/golden_quotes.json` with per coverage premiums and the full BI
intermediate chain. All 12 golden assertions (3 totals, 3 per coverage maps,
3 intermediate chains, 3 internal consistency checks) pass.

```
.venv/bin/python -m pytest tests/test_golden_quotes.py --color=no -q
```

Result: 12 passed.

### Edge matrix

Hand computed settlement matrix: collision (9 cases including at deductible,
one cent above, at ACV, above ACV), PD (4 cases around the limit), BI (7
scenarios including exact occurrence cap and two largest remainder pro rata
splits), rental (5 cases), coinsurance (5 cases including the 0.25 cent
rounding case). Every expected value in the test file is a literal I worked
out by hand from the documented rules.

```
.venv/bin/python -m pytest tests/test_claims_edge_matrix.py --color=no -q
```

Result: 36 passed.

### Property sweeps

100,000 seeded random cases per settlement type, 300,000 total, checking:
payment never negative, never above the applicable limit, deductible applied
exactly once, BI total equals the occurrence limit exactly whenever capped
demand exceeds it.

```
.venv/bin/python -m policyforge.property_checks
```

Result (also committed as `results/property_checks.json`): collision 100000
cases 0 violations, BI 100000 cases 0 violations, coinsurance 100000 cases
0 violations. Total violations: 0 out of 300,000.

## Re-rate scenario

Seeded 10,000 policy book (seed 20260824), scenario: territory T3 factor
1.275 to 1.350, nonstandard tier 1.450 to 1.550.

```
.venv/bin/python -m policyforge.rerate
```

Result (committed as `results/rerate_scenario.json`):

* book premium: $11,906,611.47 to $12,551,561.16, +542 bp (+5.42%)
* per policy change: p50 +588 bp, p95 +1319 bp, max +1319 bp, min 0
* 56.18% of policies increased, 43.82% unchanged, 0% decreased

Deterministic: reran and got byte identical JSON.

## Throughput

Best of 3 passes, wall clock via time.perf_counter, single thread.

```
.venv/bin/python -m policyforge.bench
```

Result (committed as `results/bench.json`):

* rating: 20,000 quotes in 0.4399 s, about 45,460 quotes/sec
* settlements: 100,000 mixed settlements (50k collision, 50k multi claimant
  BI) in 0.0707 s, about 1,414,145 settlements/sec

The settlement number is much higher than the rating number because a
settlement is a handful of integer min/max operations while a quote walks a
5 step chain for up to 5 coverages with object construction per step. I am
reporting both as measured rather than pretending they are comparable.

## Test suite

```
.venv/bin/python -m pytest --color=no --cov=policyforge --cov-report=term
```

Result: 109 passed in about 2.2 s, coverage 99% (357 statements, 5 missed;
the missed lines are defensive branches in the sweep helpers and one
validation raise in the re-rate percent math).
