"""stats.py on known values."""

import math
from itertools import product

import pytest

from officebench import stats


@pytest.mark.parametrize("k, n, low, high", [
    (17, 20, 0.6396, 0.9476),  # Newcombe (1998), Wilson score interval
    (0, 10, 0.0, 0.2775),
    (5, 10, 0.2366, 0.7634),
    (20, 20, 0.8389, 1.0),
    (8, 20, 0.2188, 0.6134),
])
def test_wilson(k, n, low, high):
    lo, hi = stats.wilson(k, n)
    assert lo == pytest.approx(low, abs=5e-5) and hi == pytest.approx(high, abs=5e-5)


def test_wilson_bounds():
    assert stats.wilson(0, 0) == (0.0, 1.0)
    for n in range(1, 30):
        assert stats.wilson(0, n)[0] == 0.0 and stats.wilson(n, n)[1] == 1.0, n  # exact end points
        for k in range(n + 1):
            lo, hi = stats.wilson(k, n)
            assert 0.0 <= lo <= k / n + 1e-12 and k / n - 1e-12 <= hi <= 1.0


def test_bootstrap_estimate_is_mean_of_task_means():
    # unequal numbers of runs: each task weighs the same (not each run)
    point, lo, hi = stats.cluster_bootstrap({"a": [1, 1, 1, 1], "b": [0]})
    assert point == 0.5 and lo == 0.0 and hi == 1.0
    assert stats.cluster_bootstrap({"a": [True] * 5, "b": [1.0, 1.0]}) == (1.0, 1.0, 1.0)


def test_bootstrap_properties():
    values = {"a": [1, 1, 0, 1], "b": [0, 0, 1, 0], "c": [1, 1, 1, 1], "d": [0, 1, 0, 1], "e": [1, 0, 1, 1]}
    point, lo, hi = stats.cluster_bootstrap(values)
    assert point == pytest.approx(0.65) and lo < point < hi and 0 <= lo and hi <= 1
    assert stats.cluster_bootstrap(values) == (point, lo, hi)  # fixed seed: reproducible
    # one task: the interval only comes from the runs of that task
    p1, lo1, hi1 = stats.cluster_bootstrap({"a": [1, 0, 1, 0, 1, 0, 1, 0]})
    assert p1 == 0.5 and lo1 < 0.5 < hi1
    # more tasks with the same spread -> narrower interval
    wide = stats.cluster_bootstrap({i: [1, 0] for i in "ab"})
    narrow = stats.cluster_bootstrap({i: [1, 0] for i in "abcdefghijklmnop"})
    assert narrow[2] - narrow[1] < wide[2] - wide[1]
    assert all(math.isnan(x) for x in stats.cluster_bootstrap({}))
    assert all(math.isnan(x) for x in stats.cluster_bootstrap({"a": []}))


def test_bootstrap_wider_than_independent_runs():
    # every task either always or never solved: 3 runs per task add no information, the interval must show it
    values = {i: [i % 2] * 3 for i in range(10)}
    _, lo, hi = stats.cluster_bootstrap(values)
    w_lo, w_hi = stats.wilson(15, 30)
    assert hi - lo > 0.8 * (w_hi - w_lo)


def test_pass_k():
    assert stats.pass_k({"a": [True, True, False, False]}, 2) == pytest.approx(1 / 6)  # C(2,2)/C(4,2)
    assert stats.pass_k({"a": [True, True, True, False]}, 3) == pytest.approx(1 / 4)  # C(3,3)/C(4,3)
    # k = 1 is the mean of the task means
    assert stats.pass_k({"a": [1, 0, 1, 1], "b": [0, 0, 1, 0]}, 1) == pytest.approx((0.75 + 0.25) / 2)
    # tasks with fewer than k runs are skipped
    assert stats.pass_k({"a": [True] * 4, "b": [False]}, 2) == 1.0
    assert math.isnan(stats.pass_k({"a": [True]}, 2))
    # unbiased: equals the mean over all k-subsets of the runs
    runs = [True, False, True, True, False]
    subsets = [all(runs[i] for i in idx) for idx in product(range(5), repeat=2) if idx[0] < idx[1]]
    assert stats.pass_k({"a": runs}, 2) == pytest.approx(sum(subsets) / len(subsets))


def test_paired_comparison_known_values():
    a = {t: [1, 1] for t in "abcde"}
    b = {t: [0, 0] for t in "abcde"}
    v = stats.paired_comparison(a, b)
    # all five differences +1: only "all +" and "all −" of the 2^5 sign flips reach |mean| = 1
    assert v["tasks"] == 5 and v["diff"] == 1.0 and v["p"] == pytest.approx(2 / 32)
    assert v["low"] == 1.0 and v["high"] == 1.0
    same = stats.paired_comparison(a, a)
    assert same["diff"] == 0.0 and same["p"] == 1.0
    reverse = stats.paired_comparison(b, a)
    assert reverse["diff"] == -1.0 and reverse["p"] == v["p"]


def test_paired_comparison_mixed():
    a = {"a": [1, 1], "b": [1, 0], "c": [0, 0], "only_a": [1]}
    b = {"a": [0, 0], "b": [1, 0], "c": [0, 0], "only_b": [0]}
    v = stats.paired_comparison(a, b)
    # differences 1, 0, 0 on the shared tasks: every sign flip gives |mean| = 1/3, so p = 1
    assert v["tasks"] == 3 and v["diff"] == pytest.approx(1 / 3) and v["p"] == 1.0
    assert v["low"] <= v["diff"] <= v["high"]
    empty = stats.paired_comparison({"a": [1]}, {"b": [1]})
    assert empty["tasks"] == 0 and math.isnan(empty["diff"]) and math.isnan(empty["p"])


def test_paired_comparison_many_tasks():
    # more than 16 tasks: Monte Carlo p-value, never 0
    v = stats.paired_comparison({i: [1] for i in range(20)}, {i: [0] for i in range(20)}, n=2000)
    assert v["diff"] == 1.0 and 0 < v["p"] <= 2 / 2000 + 1e-9
    none = stats.paired_comparison({i: [i % 2] for i in range(20)}, {i: [(i + 1) % 2] for i in range(20)}, n=2000)
    assert none["diff"] == 0.0 and none["p"] == 1.0
