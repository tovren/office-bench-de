"""Broken variants of the reference solutions (tasks/<id>/mutants.toml, format: docs/mutants.md): every variant
carries one typical model error, and the content check must report it. test_references.py shows that a good solution
raises no false alarm; this file shows that the checks catch real errors.

Operations run in the order set, replace, number, remove, each on the arguments of the last call (a follow-up task
keeps its `previous` file unchanged). The tool must accept the variant, and it must differ from the reference. A
mutant with `gap` is a known blind spot of the checks, one with `prevented` an error the tool itself sends back or
repairs: both are a strict xfail, so they fail once a check catches the defect in a built file.
"""

import copy
import json
import re
import tomllib

import pytest

from officebench.checks.content import check_files
from officebench.checks.registry import GENERAL_CHECKS, HARD, SOFT, TASK_CHECKS
from officebench.tasks import load_tasks
from officebench.tool import build

KEYS = {"name", "defect", "set", "replace", "number", "remove", "expected", "severity", "gap", "prevented"}
CHECKS = set(TASK_CHECKS) | set(GENERAL_CHECKS) | {"unreadable", "wrong_file_type"}


def load_mutants() -> list:
    """[(task id, mutant dict)] of all tasks with a mutants.toml."""
    out = []
    for task_id, task in load_tasks().items():
        if task.mutants_path.exists():
            for m in tomllib.loads(task.mutants_path.read_text(encoding="utf-8")).get("mutant", []):
                out.append((task_id, m))
    return out


ALL = load_mutants()


def reference(task_id: str) -> dict:
    return json.loads(load_tasks()[task_id].reference_path.read_text(encoding="utf-8"))


def _steps(path: str) -> list:
    return [int(t) if t.isdigit() else t for t in path.split(".")]


def _nodes(root, steps: list, new: bool = False) -> list:
    """All (container, key) pairs the path points to; * expands over list elements or dict values. new: the last key
    may be missing from a dict (set adds it)."""
    current = [root]
    for s in steps[:-1]:
        following = []
        for k in current:
            if s == "*":
                following += list(k.values()) if isinstance(k, dict) else list(k)
            elif isinstance(k, dict) and s in k or isinstance(k, list) and isinstance(s, int) and s < len(k):
                following.append(k[s])
        current = following
    last = steps[-1]
    pairs = []
    for k in current:
        if last == "*":
            pairs += [(k, i) for i in (list(k) if isinstance(k, dict) else range(len(k)))]
        elif isinstance(k, dict) and (last in k or new) or isinstance(k, list) and isinstance(last, int) \
                and last < len(k):
            pairs.append((k, last))
    return pairs


def _leaves(value, fn):
    """Apply fn to every leaf (strings and numbers); returns (new value, number of changed leaves)."""
    if isinstance(value, dict):
        n = 0
        for k, v in value.items():
            value[k], m = _leaves(v, fn)
            n += m
        return value, n
    if isinstance(value, list):
        n = 0
        for i, v in enumerate(value):
            value[i], m = _leaves(v, fn)
            n += m
        return value, n
    new = fn(value)
    return new, int(new != value or type(new) is not type(value))


def mutate(arguments: dict, m: dict) -> dict:
    a = copy.deepcopy(arguments)
    for path, value in m.get("set", []):
        pairs = _nodes(a, _steps(path), new=True)
        assert pairs, f"set: path {path} matches nothing"
        for k, i in pairs:
            k[i] = value
    for old, new in m.get("replace", []):
        a, n = _leaves(a, lambda v, old=old, new=new: v.replace(old, new) if isinstance(v, str) else v)
        assert n, f"replace: {old!r} does not occur"
    for old, new in m.get("number", []):
        a, n = _leaves(a, lambda v, old=old, new=new: new if isinstance(v, (int, float)) and not isinstance(v, bool)
                       and v == old else v)
        assert n, f"number: {old} does not occur"
    for path in m.get("remove", []):
        pairs = _nodes(a, _steps(path))
        assert pairs, f"remove: path {path} matches nothing"
        for k, i in sorted(pairs, key=lambda p: p[1] if isinstance(p[1], int) else 0, reverse=True):
            del k[i]
    return a


def test_mutate_operations():
    args = {"sheets": [{"columns": [{"header": "A", "total": "sum", "w": 220}, {"header": "B", "w": 220.0}],
                        "chart": {"type": "column"}}]}
    m = {"set": [["sheets.0.chart.type", "bar"], ["sheets.0.chart.title", "Neu"]],
         "replace": [["A", "AA"]], "number": [[220, 250]], "remove": ["sheets.0.columns.*.total", "sheets.0.columns.1"]}
    assert mutate(args, m) == {"sheets": [{"columns": [{"header": "AA", "w": 250}],
                                           "chart": {"type": "bar", "title": "Neu"}}]}
    assert args["sheets"][0]["chart"] == {"type": "column"}  # the reference stays unchanged
    for bad in ({"set": [["sheets.0.nope.x", 1]]}, {"replace": [["ZZ", "x"]]}, {"number": [[999, 1]]},
                {"remove": ["sheets.3"]}):
        with pytest.raises(AssertionError):
            mutate(args, bad)


def test_mutants_well_formed():
    names = set()
    for task_id, m in ALL:
        task = load_tasks()[task_id]
        assert task.reference_path.exists(), f"no reference for {task_id}"
        assert set(m) <= KEYS, f"{task_id}: unknown keys {set(m) - KEYS}"
        assert re.fullmatch(r"[a-z0-9_]+", m["name"]) and (task_id, m["name"]) not in names, f"{task_id}: {m['name']}"
        names.add((task_id, m["name"]))
        assert m.get("defect") and m.get("expected"), f"{task_id}-{m['name']}: defect and expected are required"
        assert set(m["expected"]) <= CHECKS, f"{task_id}-{m['name']}: unknown check {set(m['expected']) - CHECKS}"
        assert m.get("severity", HARD) in (HARD, SOFT)
        assert not (m.get("gap") and m.get("prevented")), f"{task_id}-{m['name']}: gap or prevented, not both"
        assert any(m.get(k) for k in ("set", "replace", "number", "remove")), f"{task_id}-{m['name']}: no change"


@pytest.fixture(scope="module")
def findings(tmp_path_factory) -> dict:
    """(id, name) -> (CallResult, Findings or None): every variant built and checked in one content-check run (one
    LibreOffice call). File names like the harness writes them: <id>-0__r<round>c0__<name>."""
    folder = tmp_path_factory.mktemp("mutants")
    built, previous = {}, {}

    def build_file(call: dict, stem: str):
        result = build(call["function"], call["arguments"])
        path = None
        if result.files:
            f = result.files[-1]
            path = folder / f"{stem}__{f.name}"
            path.write_bytes(f.data)
        return result, path

    for task_id, m in ALL:
        ref = reference(task_id)
        if "previous" in ref and task_id not in previous:
            previous[task_id] = build_file(ref["previous"], f"{task_id}-0__r0c0")[1]
        arguments = mutate(ref["arguments"], m)
        assert arguments != ref["arguments"], f"{task_id}-{m['name']}: variant equals the reference"
        built[task_id, m["name"]] = build_file({"function": ref["function"], "arguments": arguments},
                                               f"{task_id}-0__r2c0__{m['name']}")
    entries = [(path, task_id, previous.get(task_id)) for (task_id, _), (_, path) in built.items() if path is not None]
    result = check_files(entries)
    return {k: (r, result.get(p) if p is not None else None) for k, (r, p) in built.items()}


def _param(task_id, m):
    reason = m.get("gap") or m.get("prevented")
    marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
    return pytest.param(task_id, m, id=f"{task_id}-{m['name']}", marks=marks)


@pytest.mark.slow
@pytest.mark.parametrize("task_id, m", [_param(i, m) for i, m in ALL])
def test_check_catches_defect(task_id, m, findings):
    result, found = findings[task_id, m["name"]]
    assert result.done and found is not None, f"the tool rejects the variant: {result.content[:500]}"
    severity = m.get("severity", HARD)
    hits = [x for x in found.defects if x.check in m["expected"] and (severity == SOFT or x.hard)]
    listing = "\n".join(f"[{x.severity}] {x.check}: {x}" for x in found.defects) or "no defects"
    assert hits, f"{m['defect']}: not reported by {m['expected']} ({severity}). Findings:\n{listing}"
