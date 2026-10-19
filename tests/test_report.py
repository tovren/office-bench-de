"""report.py: the cells and sections on hand-made results, the whole report on hand-built runs (content check
replaced by the fake of test_scoring), judge grades."""

import json

import pytest
from test_scoring import BAHNCARD, fake_check, make_run, office, rec, rnd  # noqa: F401  (fake_check: fixture)

from officebench import report
from officebench.cli import main as cli
from officebench.scoring import Result


def res(task="a", rep=0, success=True, kind="file", **kw):
    base = {"file_first_call": True, "file_at_end": True, "outcome": "answer", "final_answer": True}
    return Result(run="r", model="M", task=task, rep=rep, title=task.upper(), kind=kind, success=success,
                  **{**base, **kw})


def row(lines: list[str], index: int = 2) -> dict:
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    return dict(zip(head, (c.strip() for c in lines[index].strip("|").split("|")), strict=True))


def test_rate_and_pass_cells():
    assert report.rate_cell({}) == "–"
    assert report.rate_cell({"a": [True, True], "b": [True, False]}).endswith("· 3/4")
    # degenerate bootstrap interval (all equal): Wilson as well
    assert report.rate_cell({"a": [True] * 20, "b": [True] * 20}) == "100 % (100–100; Wilson 91–100) · 40/40"
    assert report.pass_cells({"a": [True] * 4, "b": [True, True, False, False]}) == ("58 %", "k=4: 50 %")
    assert report.pass_cells({"a": [True]}) == ("–", "–")


def test_per_task_cell_marks_undeterminable_runs():
    def cell(rs):
        return report.section_per_task(rs, {"M": rs})[2].split("|")[2].strip()

    assert cell([res(rep=0), res(rep=1, success=False)]) == "2·2·1/2"
    assert cell([res(rep=0), res(rep=1, success=None), res(rep=2, success=False)]) == "3·3·1+1?/3"
    assert cell([res(rep=0, success=None), res(rep=1, success=None)]) == "2·2·?/2"
    assert cell([res(rep=0, success=None, kind="no_file"), res(rep=1, kind="no_file")]) == "–·–·1+1?/2"
    assert cell([res(rep=0, scored=False)]) == ""  # not scored: left out


def test_unscored_and_undeterminable_are_left_out_of_rates():
    rs = [res(rep=0), res(rep=1, success=None), res(rep=2, success=False, scored=False, error_kind="provider")]
    assert report.per_task(rs, "success") == {"a": [True]}
    assert report.per_task([res(kind="no_file")], "file_at_end", file_only=True) == {}


def test_operations():
    rs = [res(rep=0, round_limit=True, final_answer=False), res(rep=1, final_answer=False),
          res(rep=2, outcome="error", error_kind="server", final_answer=False, success=False),
          res(rep=3, outcome="error", error_kind="network", scored=False, success=None, final_answer=False),
          res(rep=4, outcome="missing", scored=False, success=None, final_answer=False),
          res(rep=5, claims_file=True, invented_links=["sandbox:/x"], extra_files=True, cost=0.5, seconds_to_file=10,
              rounds_to_file=2)]
    r = row(report.section_operations({"M": rs}))
    assert r["no final answer"] == "2" and r["round limit"] == "1" and r["server errors"] == "1"
    assert r["outages (not scored)"] == "1" and r["missing (no log line)"] == "1"
    assert (r["claims file without file"], r["links in the reply"], r["more files than needed"]) == ("1", "1", "1")
    assert r["cost total"] == "$ 0.500" and r["median time to file"] == "10 s" and r["mean rounds to file"] == "2.00"


def test_rejections_and_defects():
    rej = [{"round": 0, "index": 0, "turn": 0, "category": "json", "text": "x", "file_after": True},
           {"round": 1, "index": 0, "turn": 0, "category": "schema", "text": "x", "file_after": False}]
    rs = [res(rep=0, rejections=rej, recovered=True, content_ok=True, delivered_file="f", hard_defects=[],
              soft_defects=["weekday"], metrics={"unsourced_numbers": 2}),
          res(rep=1, content_ok=False, delivered_file="g", hard_defects=["no formula"],
              metrics={"unsourced_numbers": 0},
              other_defects=[{"label": "tool not called", "severity": "hard", "check": "tools_expected", "text": "…"},
                             {"label": "markdown in reply", "severity": "soft", "check": "no_markdown", "text": "…"}])]
    r = row(report.section_rejections({"M": rs}))
    assert r["runs with a rejection: file after it"] == "1/1" and r["invalid JSON"] == "1/1"
    assert r["schema / required field"] == "0/1"
    r = row(report.section_defects({"M": rs}))
    assert r["files checked"] == "2" and r["hard defects (runs)"] == "no formula (1), tool not called (1)"
    assert r["soft defects (runs)"] == "weekday (1), markdown in reply (1)"
    assert r["numbers without source"] == "1.0 · 1/2"
    assert report.section_rejections({"M": [res()]}) == ["No rejected tool calls."]


def test_special_section():
    rs = [res(task="b", kind="no_file", extra_tools_offered=["web_search", "send_email"],
              extra_tools_called=["web_search"], missing_reply_topics=[], unnecessary_call=False),
          res(task="b", rep=1, kind="no_file", extra_tools_offered=["web_search", "send_email"], extra_tools_called=[],
              missing_reply_topics=["Preis"], unnecessary_call=True),
          res(task="f", kind="follow_up", turns_ok=True),
          res(task="z", missing_reply_topics=["Makro"], content_ok=True)]
    r = row(report.section_special({"M": rs}))
    assert r["extra tool called (runs / offered)"] == "web_search 1/2, send_email 0/2"
    assert r["no file: unnecessary office call"] == "1/2" and r["no file: reply topics there"] == "1/2"
    assert r["follow-up: all turns fulfilled"] == "1/1" and r["with file: reply check passed"] == "0/1"
    assert report.section_special({"M": [res()]}) == []


def grade(task, rep, judge, mean, model="M", file=None):
    return {"model": model, "task": task, "rep": rep, "file": file or f"{task}-{rep}.docx", "judge": judge,
            "grades": {k: mean for k in report.CRITERIA}, "mean": mean}


def test_grades():
    # several judges per file: the file counts once (mean over judges); a judge twice on a file is averaged first
    text = "\n".join(report.section_grades([
        grade("budget", 0, "claude", 4.0), grade("budget", 1, "claude", 2.0), grade("budget", 1, "gpt", 2.0),
        grade("budget", 1, "gpt", 2.0)], None))
    assert "| M | 2 | 1 | 3.00 (" in text and "claude (2 grades), gpt (2 grades)" in text
    # (5 + 3) / 2 per judge for one file, then over judges: ((5+3)/2 + 1) / 2 = 2.5
    vals = report.grade_values([grade("a", 0, "j", 5.0), grade("a", 0, "j", 3.0), grade("a", 0, "k", 1.0)])
    assert vals["M"]["a"] == [2.5]
    # per criterion and the gap to the next model
    gs = [grade(t, 0, "j", 4.0, "A") for t in "xyz"] + [grade(t, 0, "j", 3.0, "B") for t in "xyz"]
    gs[0]["grades"]["language"] = 1.0
    text = "\n".join(report.section_grades(gs, {"A", "B"}))
    assert text.index("| A |") < text.index("| B |") and "| A − B | 1.00 (1.00 to 1.00) | 0.250 | 3 |" in text
    assert "| A | 3 | 3 | 4.00 (4.00–4.00) | 3.00 | 4.00 |" in text
    # grades of other models only: say so instead of showing everything
    text = "\n".join(report.section_grades([grade("budget", 0, "j", 4.0, model="other")], {"M"}))
    assert "No judge grades for the models of this report (grades exist for: other)" in text and "| other |" not in text


def test_whole_report(tmp_path, fake_check, capsys):  # noqa: F811
    a = "aushang-{}__r0c0__A{}.docx"
    make_run(tmp_path, [
        rec("aushang", 0, [rnd([office(a.format(0, ""))]), rnd(content="Fertig.")]),
        rec("aushang", 1, [rnd([office(a.format(1, " bad"))]), rnd(content="Fertig.")]),
        rec("bahncard", 0, [rnd([{"name": "web_search", "status": "extra_tool", "done": False, "result": "…"}]),
                            rnd(content=BAHNCARD)]),
    ], [a.format(0, ""), a.format(1, " bad")], tasks=["aushang", "bahncard"], repeats=2, name="good")
    folder = make_run(tmp_path / "x", [
        rec("aushang", 0, [rnd()], ["error"], "HTTP 500", "server"),
        rec("aushang", 1, [rnd([office(a.format(1, ""))]), rnd(content="Fertig.")]),
    ], [a.format(1, "")], tasks=["aushang"], repeats=2, name="weak")
    grades = tmp_path / "grades.jsonl"
    grades.write_text("".join(json.dumps(g) + "\n" for g in [grade("aushang", 0, "j", 4.0, "good"),
                                                              grade("aushang", 1, "j", 2.0, "weak")]), encoding="utf-8")
    text = report.report([tmp_path / "run", folder], compare=["good", "weak"], grades=[grades])
    for heading in ("## Rates", "## Operations", "## Tool rejections", "## Follow-ups, tasks without a file",
                    "## Most common defects", "## Per task", "## Comparison", "## Judge grades"):
        assert heading in text, heading
    assert "- `good` (" in text and "Model good" in text and "2 tasks × 2" in text
    assert "> 1 task runs have no log line" in text  # bahncard-1 of "good"
    assert "| aushang: Tea kitchen notice (vague) | 2·2·1/2 | 1·1·1/2 |" in text  # server error: scored, failed
    assert "| success | " in text and "Not compared (only in one arm): bahncard" in text
    assert "web_search 1/1, send_email 0/1" in text
    with pytest.raises(SystemExit, match="unknown model"):
        report.report([tmp_path / "run"], compare=["good", "nope"])
    # the same model name in two runs: keys with the run name, or the path if the run names agree too
    other = make_run(tmp_path / "y", [rec("aushang", 0, [rnd(content="Nein.")])], name="good")
    other.parent.rename(tmp_path / "y" / "run2")
    groups, _ = report.load_groups([tmp_path / "run", tmp_path / "y" / "run2", folder])
    assert list(groups) == ["run/good", "run2/good", "weak"]
    same = make_run(tmp_path / "z", [rec("aushang", 0, [rnd(content="Nein.")])], name="good")
    groups, _ = report.load_groups([tmp_path / "run", same])
    assert list(groups) == [str(tmp_path / "run" / "good"), str(same)]
    assert cli(["report", str(folder)]) == 0 and "| weak |" in capsys.readouterr().out
