"""Markdown report of one or more scored runs (stdout).

    obench report RUN_FOLDER... [--compare A B] [--grades FILE...] [--rescore]

RUN_FOLDER is a model folder (runs/<run>/<model>/) or a run folder with model folders; results.jsonl is read, or
written first if it is missing or older than the log (officebench.scoring). A and B are model names as they appear
in the report. Rates: estimate (mean over tasks) with a 95 % cluster bootstrap over tasks, plus the raw count
(officebench.stats). The definitions of every column are in officebench.scoring and docs/scoring.md.

Judge grades (--grades): JSON lines {"model", "task", "rep", "file", "judge", "grades": {criterion: 1–5}, "mean"};
a file counts once (mean over judges), the model mean is the mean over tasks with a bootstrap over tasks.
"""

from __future__ import annotations

import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from officebench.runs import OUTAGE, model_folders, read_jsonl, read_meta
from officebench.scoring import CATEGORIES, Result, load_results, reply_ok
from officebench.stats import cluster_bootstrap, paired_comparison, pass_k, wilson

# (field, heading, only file tasks)
RATES = (
    ("file_first_call", "file at 1st call", True),
    ("file_at_end", "file at end", True),
    ("content_ok", "content ok", True),
    ("clean", "clean", True),
    ("success", "success", False),
)
CRITERIA = ("language", "content", "completeness", "structure", "usefulness")  # ids in judge/criteria.toml
FOOTNOTE = (
    "Rates: estimate = mean over tasks of the per-task rate, 95 % interval from a cluster bootstrap over tasks (runs "
    "of one task are not independent), then the raw count. When the interval has zero width (all values equal), the "
    "Wilson interval is added (it treats runs as independent). File columns only count tasks that ask for a file; "
    "success counts all. Success = file at end, every turn fulfilled and content ok (no hard defect), plus the reply "
    "check and the behavior check where the task has them; without a file: no office call, a final answer with every "
    "required topic and nothing forbidden. Not scored: runs that a provider or network failure ended before the "
    "outcome was settled, and task runs without a log line. Server errors of the model's own server count as "
    "failures. pass^k: chance that k fresh runs of a task all succeed (mean over tasks). Details: docs/scoring.md.")


def num(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}"


def per_task(results, name: str, file_only: bool = False) -> dict:
    """{task: [bool]} of the scored results; None values (not determinable) are left out."""
    out = defaultdict(list)
    for r in results:
        if not r.scored or (file_only and not r.file_task):
            continue
        value = getattr(r, name)
        if value is not None:
            out[r.task].append(bool(value))
    return dict(out)


def rate_cell(values: dict) -> str:
    """Bootstrap estimate and interval over tasks plus k/n; Wilson too when the bootstrap interval is degenerate."""
    n = sum(len(v) for v in values.values())
    if not n:
        return "–"
    k = sum(sum(v) for v in values.values())
    point, lo, hi = cluster_bootstrap(values)
    interval = f"{100 * lo:.0f}–{100 * hi:.0f}"
    if lo == hi:
        w_lo, w_hi = wilson(k, n)
        interval += f"; Wilson {100 * w_lo:.0f}–{100 * w_hi:.0f}"
    return f"{100 * point:.0f} % ({interval}) · {k}/{n}"


def pass_cells(values: dict) -> tuple[str, str]:
    """pass^2 and pass^k for the largest k at which every task still counts (smallest number of runs)."""
    lengths = [len(v) for v in values.values() if v]
    if not lengths or min(lengths) < 2:
        return "–", "–"
    k = min(lengths)
    return f"{100 * pass_k(values, 2):.0f} %", (f"k={k}: {100 * pass_k(values, k):.0f} %" if k > 2 else "–")


def median_text(values: list, unit: str = " s") -> str:
    return f"{statistics.median(values):.0f}{unit}" if values else "–"


def table(head: list, rows: list) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + [
        "| " + " | ".join(str(x) for x in row) + " |" for row in rows]


# ----------------------------------------------------------------------------------------------------- sections --

def section_rates(groups: dict) -> list[str]:
    head = ["model", "scored runs", *(t for _, t, _ in RATES), "pass^2 (success)", "pass^k (success)"]
    rows = []
    for key, rs in groups.items():
        scored = [r for r in rs if r.scored]
        p2, pk = pass_cells(per_task(rs, "success"))
        rows.append([key, f"{len(scored)} ({len({r.task for r in scored})} tasks)",
                     *(rate_cell(per_task(rs, f, only)) for f, _, only in RATES), p2, pk])
    return table(head, rows)


def section_operations(groups: dict) -> list[str]:
    head = ["model", "median time to file", "mean rounds to file", "mean tokens in / out", "cost total",
            "cost per success", "server errors", "outages (not scored)", "missing (no log line)", "no final answer",
            "round limit", "claims file without file", "links in the reply", "more files than needed"]
    rows = []
    for key, rs in groups.items():
        g = [r for r in rs if r.scored]
        logged = [r for r in g if r.outcome != "missing"]
        rounds = [r.rounds_to_file for r in g if r.rounds_to_file is not None]
        costs = [r.cost for r in g if r.cost is not None]
        wins = sum(1 for r in g if r.success)
        tokens = (f"{statistics.fmean(r.tokens_in for r in logged):.0f} / "
                  f"{statistics.fmean(r.tokens_out for r in logged):.0f}") if logged else "–"
        rows.append([
            key, median_text([r.seconds_to_file for r in g if r.seconds_to_file is not None]),
            num(statistics.fmean(rounds)) if rounds else "–", tokens,
            f"$ {num(sum(costs), 3)}" if costs else "–", f"$ {num(sum(costs) / wins, 4)}" if costs and wins else "–",
            sum(1 for r in g if r.error_kind == "server"),
            sum(1 for r in rs if not r.scored and r.error_kind in OUTAGE),
            sum(1 for r in rs if r.outcome == "missing"),
            sum(1 for r in logged if not r.final_answer and not r.round_limit),
            sum(1 for r in logged if r.round_limit),
            sum(1 for r in g if r.claims_file), sum(1 for r in g if r.invented_links),
            sum(1 for r in g if r.extra_files),
        ])
    return table(head, rows) + ["", "Time to file: model time (sum of the round durations without retry pauses) up to "
                                    "the first built file. Costs as reported by the API (missing for local servers)."]


def section_rejections(groups: dict) -> list[str]:
    counts = {}
    for key, rs in groups.items():
        c = defaultdict(lambda: [0, 0])
        for r in rs:
            if r.scored:
                for a in r.rejections:
                    c[a["category"]][0] += 1
                    c[a["category"]][1] += bool(a.get("file_after"))
        counts[key] = c
    cats = [k for k in CATEGORIES if any(k in c for c in counts.values())]
    if not cats:
        return ["No rejected tool calls."]
    rows = []
    for key, rs in groups.items():
        with_rej = [r for r in rs if r.scored and r.rejections]
        rows.append([key, f"{sum(1 for r in with_rej if r.recovered)}/{len(with_rej)}" if with_rej else "–",
                     *((f"{counts[key][k][1]}/{counts[key][k][0]}" if k in counts[key] else "–") for k in cats)])
    return table(["model", "runs with a rejection: file after it", *(CATEGORIES[k] for k in cats)], rows) + [
        "", "Cell per category: rejected calls after which a file came in the same turn / all rejected calls."]


def section_special(groups: dict) -> list[str]:
    """Follow-ups, tasks without a file, extra tools and the reply check of file tasks; only if such runs exist."""
    rows = []
    for key, rs in groups.items():
        g = [r for r in rs if r.scored]
        follow = [r for r in g if r.kind == "follow_up"]
        nofile = [r for r in g if r.kind == "no_file"]
        extra = [r for r in g if r.extra_tools_offered]
        reply = [x for r in g if r.file_task and r.has_reply_check and (x := reply_ok(r)) is not None]
        if not (follow or nofile or extra or reply):
            continue
        topics = [r for r in nofile if r.missing_reply_topics is not None]
        names = list(dict.fromkeys(t for r in extra for t in r.extra_tools_offered))
        tools = ", ".join(f"{t} {sum(t in r.extra_tools_called for r in extra if t in r.extra_tools_offered)}/"
                          f"{sum(t in r.extra_tools_offered for r in extra)}" for t in names)
        rows.append([key,
                     f"{sum(bool(r.turns_ok) for r in follow)}/{len(follow)}" if follow else "–",
                     f"{sum(bool(r.unnecessary_call) for r in nofile)}/{len(nofile)}" if nofile else "–",
                     f"{sum(not r.missing_reply_topics for r in topics)}/{len(topics)}" if topics else "–",
                     f"{sum(reply)}/{len(reply)}" if reply else "–",
                     tools or "–", sum(1 for r in g if r.reply_truncated and r.has_reply_check)])
    if not rows:
        return []
    return table(["model", "follow-up: all turns fulfilled", "no file: unnecessary office call",
                  "no file: reply topics there", "with file: reply check passed",
                  "extra tool called (runs / offered)", "reply truncated"], rows) + [
        "", "Unnecessary office call: the office tool was called in a turn that expects no file. Whether an extra "
            "tool should be called is set per task ([behavior]). Reply check: [reply] topics there and nothing "
            "forbidden in the final answer. Reply truncated: the log keeps 4000 characters; counted for tasks with a "
            "reply check."]


def _labels(r: Result, hard: bool) -> list:
    own = r.hard_defects if hard else r.soft_defects
    other = {d["label"] for d in r.other_defects if (d["severity"] == "hard") == hard}
    return [*own, *sorted(other - set(own))]


def section_defects(groups: dict) -> list[str]:
    """Defects of the content check plus those of the reply and behavior checks, counted in runs; a column with the
    unsourced numbers if a task has numbers_sourced."""
    sourced = any("unsourced_numbers" in r.metrics for rs in groups.values() for r in rs)
    rows = []
    for key, rs in groups.items():
        g = [r for r in rs if r.scored]
        hard = Counter(x for r in g for x in _labels(r, True))
        soft = Counter(x for r in g for x in _labels(r, False))
        row = [key, sum(1 for r in g if r.content_ok is not None and r.delivered_file),
               ", ".join(f"{k} ({v})" for k, v in hard.most_common(6)) or "–",
               ", ".join(f"{k} ({v})" for k, v in soft.most_common(6)) or "–"]
        if sourced:
            vals = [r.metrics["unsourced_numbers"] for r in g if "unsourced_numbers" in r.metrics]
            row.append(f"{num(statistics.fmean(vals), 1)} · {sum(1 for v in vals if v)}/{len(vals)}" if vals else "–")
        rows.append(row)
    head = ["model", "files checked", "hard defects (runs)", "soft defects (runs)"]
    foot = ["", "Defects of the content check, the reply and the behavior checks; per label the number of runs."]
    if sourced:
        head.append("numbers without source")
        foot[1] += (" Numbers without source (numbers_sourced): mean per checked file · files with at least one / "
                    "checked files.")
    return table(head, rows) + foot


def section_per_task(results, groups: dict) -> list[str]:
    tasks = sorted(dict.fromkeys(r.task for r in results))
    titles = {r.task: (f"{r.title} ({r.kind})" if r.kind != "file" else r.title) or r.task for r in results}
    rows = []
    for t in tasks:
        cells = [f"{t}: {titles[t]}" if titles[t] != t else t]
        for rs in groups.values():
            g = [r for r in rs if r.task == t and r.scored]
            if not g:
                cells.append("")
                continue
            wins = sum(1 for r in g if r.success)
            open_ = sum(1 for r in g if r.success is None)
            # "2+1?": two successes, one run whose success is not determinable
            text = "?" if open_ == len(g) else f"{wins}+{open_}?" if open_ else str(wins)
            if g[0].file_task:
                cells.append(f"{sum(1 for r in g if r.file_first_call)}·{sum(1 for r in g if r.file_at_end)}·"
                             f"{text}/{len(g)}")
            else:
                cells.append(f"–·–·{text}/{len(g)}")
        rows.append(cells)
    return table(["task", *groups], rows) + [
        "", "Cell: file at 1st call · file at end · success / scored runs (? = success not determinable, e.g. the "
            "file of the last call is missing)."]


def section_compare(groups: dict, a: str, b: str) -> list[str]:
    ra, rb = groups[a], groups[b]
    out = [f"A = {a}, B = {b}. Paired over the shared tasks (mean of the per-task differences, bootstrap interval "
           "over tasks, sign-flip permutation test).", ""]
    rows = []
    for name, title, only in RATES:
        va, vb = per_task(ra, name, only), per_task(rb, name, only)
        v = paired_comparison(va, vb)
        if not v["tasks"]:
            rows.append([title, rate_cell(va), rate_cell(vb), "–", "–", 0])
            continue
        rows.append([title, rate_cell(va), rate_cell(vb),
                     f"{100 * v['diff']:+.0f} pts ({100 * v['low']:+.0f} to {100 * v['high']:+.0f})",
                     num(v["p"], 3), v["tasks"]])
    out += table(["rate", "A", "B", "difference A − B (95 %)", "p", "shared tasks"], rows)
    only = sorted({r.task for r in ra} ^ {r.task for r in rb})
    if only:
        out += ["", f"Not compared (only in one arm): {', '.join(only)}"]
    return out


# -------------------------------------------------------------------------------------------------- grades --

def read_grades(paths) -> list[dict]:
    return [g for path in paths for g in read_jsonl(path)]


def _grade(g: dict, criterion: str | None):
    if criterion is None:
        return g["mean"] if g.get("mean") is not None else statistics.fmean(g["grades"].values())
    return (g.get("grades") or {}).get(criterion)


def grade_values(grades: list[dict], criterion: str | None = None) -> dict:
    """{model: {task: [file score]}}: a file (model, task, rep, file) counts once; its score is the mean over judges
    (several lines of one judge for a file are averaged first, so a judge that ran twice does not weigh double)."""
    units = defaultdict(lambda: defaultdict(list))
    for g in grades:
        value = _grade(g, criterion)
        if value is not None:
            units[(g["model"], g["task"], g.get("rep"), g.get("file"))][g.get("judge") or "?"].append(float(value))
    out = defaultdict(lambda: defaultdict(list))
    for (model, task, *_), judges in sorted(units.items(), key=lambda x: tuple(map(str, x[0]))):
        out[model][task].append(statistics.fmean(statistics.fmean(v) for v in judges.values()))
    return out


def section_grades(grades: list[dict], models: set | None) -> list[str]:
    if models:
        matching = [g for g in grades if g.get("model") in models]
        if not matching:
            present = ", ".join(sorted({str(g.get("model")) for g in grades})) or "none"
            return [f"No judge grades for the models of this report (grades exist for: {present})."]
        grades = matching
    overall = grade_values(grades)
    per_criterion = {k: grade_values(grades, k) for k in CRITERIA}

    def mean_of_means(values: dict) -> str:
        means = [statistics.fmean(v) for v in values.values() if v]
        return num(statistics.fmean(means), 2) if means else "–"

    ranked = sorted(overall, key=lambda m: -cluster_bootstrap(overall[m])[0])
    rows = []
    for m in ranked:
        point, lo, hi = cluster_bootstrap(overall[m])
        rows.append([m, sum(len(v) for v in overall[m].values()), len(overall[m]),
                     f"{num(point)} ({num(lo)}–{num(hi)})",
                     *(mean_of_means(per_criterion[k].get(m, {})) for k in CRITERIA)])
    out = table(["model", "files", "tasks", "mean (95 %, bootstrap over tasks)", *CRITERIA], rows)
    gaps = []
    for a, b in zip(ranked, ranked[1:], strict=False):
        v = paired_comparison(overall[a], overall[b])
        if v["tasks"]:
            gaps.append([f"{a} − {b}", f"{num(v['diff'])} ({num(v['low'])} to {num(v['high'])})", num(v["p"], 3),
                         v["tasks"]])
    if gaps:
        out += ["", "Gap to the next model (paired over shared tasks):", ""]
        out += table(["models", "difference (95 %)", "p", "shared tasks"], gaps)
    judges = Counter(g.get("judge") or "?" for g in grades)
    out += ["", f"Judges: {', '.join(f'{j} ({n} grades)' for j, n in judges.most_common())}. Mean = average of the "
                "five criteria (grades 1–5) per file, averaged over judges; estimate = mean over tasks, interval: "
                "bootstrap over tasks. Do not mix grades from different judge instructions."]
    return out


# ---------------------------------------------------------------------------------------------------- report --

def load_groups(paths, rescore: bool = False) -> tuple[dict, list[tuple[Path, dict]]]:
    """{model key: [Result]} and the (folder, meta) list; the key is the model name, "run/model" if two folders of
    the report have the same model name, the folder path if that is not unique either."""
    folders = model_folders(paths)
    metas = [(f, read_meta(f)) for f in folders]
    names = Counter(f.name for f in folders)
    runs = Counter((f.parent.name, f.name) for f in folders)
    groups = {}
    for f, _ in metas:
        key = (f.name if names[f.name] == 1 else f"{f.parent.name}/{f.name}" if runs[f.parent.name, f.name] == 1
               else str(f))
        groups[key] = load_results(f, rescore)
    return groups, metas


def report(paths, compare: list[str] | None = None, grades: list | None = None, rescore: bool = False) -> str:
    groups, metas = load_groups(paths, rescore)
    out = [f"# Report ({date.today():%Y-%m-%d})", "", "Runs:"]
    for (folder, meta), (key, rs) in zip(metas, groups.items(), strict=True):
        m = meta.get("model") or {}
        out.append(f"- `{key}` ({folder}): {m.get('label') or m.get('model', '?')}, {len(rs)} task runs, "
                   f"{len({r.task for r in rs})} tasks × {meta.get('repeats', '?')}, profile "
                   f"{(meta.get('profile') or {}).get('name', '?')} (today {(meta.get('profile') or {}).get('today')}),"
                   f" tool {meta.get('tool_hash', '?')}, harness {meta.get('harness', '?')}")
    out.append("")
    results = [r for rs in groups.values() for r in rs]
    changed = sorted({r.task for r in results if r.task_changed})
    if changed:
        out += [f"> Tasks changed since the run (the checks of the current version apply): {', '.join(changed)}", ""]
    missing = sum(1 for r in results if r.outcome == "missing")
    if missing:
        out += [f"> {missing} task runs have no log line (run aborted or still going); they are not scored.", ""]
    if compare:
        unknown = [c for c in compare if c not in groups]
        if unknown:
            raise SystemExit(f"--compare: unknown model {', '.join(unknown)}; known: {', '.join(groups)}")

    out += ["## Rates", ""] + section_rates(groups)
    out += ["", "## Operations", ""] + section_operations(groups)
    out += ["", "## Tool rejections and recovery", ""] + section_rejections(groups)
    special = section_special(groups)
    if special:
        out += ["", "## Follow-ups, tasks without a file, extra tools", ""] + special
    out += ["", "## Most common defects", ""] + section_defects(groups)
    out += ["", "## Per task", ""] + section_per_task(results, groups)
    if compare:
        out += ["", "## Comparison", ""] + section_compare(groups, *compare)
    if grades:
        models = {r.model for r in results} | set(groups)
        out += ["", "## Judge grades", ""] + section_grades(read_grades(grades), models)
    out += ["", "---", "", FOOTNOTE]
    return "\n".join(out) + "\n"


def main(paths, compare=None, grades=None, rescore: bool = False) -> int:
    sys.stdout.write(report(paths, compare, grades, rescore))
    return 0
