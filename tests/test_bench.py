"""Smoke tests for the benchmark harness with tiny workloads.

These exist to make sure the harness itself is correct (positive timings,
stable checksums), not to measure anything. Real numbers come from
python -m policyforge.bench and live in results/bench.json.
"""

from policyforge.bench import bench_quotes, bench_settlements


def test_bench_quotes_smoke():
    r = bench_quotes(n=50, seed=7, passes=1)
    assert r["n"] == 50
    assert r["best_seconds"] > 0
    assert r["quotes_per_sec"] > 0
    assert r["checksum_total_cents"] > 0


def test_bench_quotes_checksum_deterministic():
    a = bench_quotes(n=50, seed=7, passes=1)
    b = bench_quotes(n=50, seed=7, passes=1)
    assert a["checksum_total_cents"] == b["checksum_total_cents"]


def test_bench_settlements_smoke():
    r = bench_settlements(n=100, seed=11, passes=1)
    assert r["n"] == 100
    assert r["best_seconds"] > 0
    assert r["settlements_per_sec"] > 0


def test_bench_settlements_checksum_deterministic():
    a = bench_settlements(n=100, seed=11, passes=1)
    b = bench_settlements(n=100, seed=11, passes=1)
    assert a["checksum_total_cents"] == b["checksum_total_cents"]
