"""Statistics for the report: intervals that respect that the runs of one task are not independent.

A model that fails a task usually fails it in every run, so 50 tasks × 3 runs are far fewer than 150 independent
attempts; an interval that treats them as independent is too narrow. The estimand is therefore the mean over tasks
of the per-task mean (every task weighs the same, however many runs it has), and the intervals resample tasks.

    wilson(k, n)                       Wilson 95 % interval for k of n (only valid for independent attempts)
    cluster_bootstrap({task: [values]}) (estimate, low, high): resample tasks, then runs within each drawn task
    pass_k({task: [bools]}, k)         chance that k fresh runs of a task all succeed, mean over tasks
    paired_comparison(a, b)            difference of two models on the tasks both ran: estimate, interval, p-value
"""

from __future__ import annotations

import math
import random
import statistics

SEED = 20261014


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    # k = 0 and k = n have exact end points; the formula only reaches them up to rounding
    return (0.0 if k == 0 else max(0.0, centre - half)), (1.0 if k == n else min(1.0, centre + half))


def _mean_of_means(groups: list[list[float]]) -> float:
    return statistics.fmean(statistics.fmean(g) for g in groups)


def cluster_bootstrap(values: dict, n: int = 4000, seed: int = SEED, level: float = 0.95) -> tuple[float, float, float]:
    """Two-stage bootstrap: draw tasks with replacement, then runs within each drawn task with replacement (the
    second stage keeps the run-to-run spread of a task in the interval).

    values: {task: [float or bool, ...]}; empty tasks are ignored. Returns (estimate, low, high), nan without data;
    with a single task the interval only reflects the runs of that task.
    """
    groups = [[float(v) for v in runs] for runs in values.values() if runs]
    if not groups:
        return math.nan, math.nan, math.nan
    point = _mean_of_means(groups)
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        drawn = [rng.choice(groups) for _ in groups]
        samples.append(_mean_of_means([[rng.choice(g) for _ in g] for g in drawn]))
    samples.sort()
    a = (1 - level) / 2
    return point, samples[int(a * (n - 1))], samples[int((1 - a) * (n - 1))]


def pass_k(successes: dict, k: int) -> float:
    """pass^k: probability that k runs of a task all succeed, unbiased per task (C(c, k) / C(n, k) for c successes in
    n runs), mean over tasks. It shows reliability: a model at 50 % that solves half the tasks always has pass^3 50 %,
    one that solves every task half the time 12.5 %.

    Tasks with fewer than k runs are skipped; nan if none is left.
    """
    per_task = []
    for runs in successes.values():
        n, c = len(runs), sum(bool(x) for x in runs)
        if n >= k:
            per_task.append(math.comb(c, k) / math.comb(n, k))
    return statistics.fmean(per_task) if per_task else math.nan


def paired_comparison(a: dict, b: dict, n: int = 10000, seed: int = SEED) -> dict:
    """Model a minus model b on the tasks both have: mean of the per-task differences, bootstrap interval over tasks,
    two-sided sign-flip permutation p-value (exact for up to 16 tasks, else Monte Carlo). Pairing by task removes
    the task difficulty from the comparison, which makes it much sharper than comparing two separate intervals.

    Returns {"tasks", "diff", "low", "high", "p"} (nan without shared tasks).
    """
    shared = [t for t in a if t in b and a[t] and b[t]]
    diffs = [statistics.fmean(map(float, a[t])) - statistics.fmean(map(float, b[t])) for t in shared]
    if not diffs:
        return {"tasks": 0, "diff": math.nan, "low": math.nan, "high": math.nan, "p": math.nan}
    point = statistics.fmean(diffs)
    rng = random.Random(seed)
    boot = sorted(statistics.fmean(rng.choice(diffs) for _ in diffs) for _ in range(n))
    observed = abs(point) - 1e-12
    if len(diffs) <= 16:
        hits = sum(abs(statistics.fmean(d if (mask >> i) & 1 else -d for i, d in enumerate(diffs))) >= observed
                   for mask in range(2 ** len(diffs)))
        p = hits / 2 ** len(diffs)
    else:
        hits = sum(abs(statistics.fmean(d * rng.choice((1, -1)) for d in diffs)) >= observed for _ in range(n))
        p = (hits + 1) / (n + 1)
    return {"tasks": len(diffs), "diff": point, "low": boot[int(0.025 * (n - 1))], "high": boot[int(0.975 * (n - 1))],
            "p": p}
