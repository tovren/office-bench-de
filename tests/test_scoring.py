"""scoring.py on hand-built task runs: file task, follow-up, task without a file, outages, round limit, reply and
behavior checks. Most tests replace the content check by a fake (verdict from the file name); the tests at the end
build real files from tasks/<id>/reference.json and run the real check."""

import json
from pathlib import Path

import pytest

from officebench import scoring
from officebench.checks.core import Defect, Findings
from officebench.cli import main as cli
from officebench.runs import MAX_LOGGED_TEXT, model_folders
from officebench.tasks import load_tasks
from officebench.tool import build

DONE = "Done: the file '{}' was created and is attached to your answer."
JSON_ERROR = ("The file was NOT created because the arguments are invalid:\n- blocks: the JSON is invalid at character "
              "12 (Expecting ',' delimiter), right after: ...abc\nFix these points and call create_word_file again.")
SCHEMA_ERROR = ("The file was NOT created because the arguments are invalid:\n- slides[2].title: Field required\n"
                "Fix these points and call create_powerpoint_file again.")
BAHNCARD = "Die BahnCard 50 kostet 259 €. Für zwei Außendienstler lohnt sie sich: Ersparnis 341 € im Jahr."


def rnd(calls=(), content="", turn=0, seconds=2.0, cost=None, **kw):
    return {"turn": turn, "seconds": seconds, "wait_seconds": 0.0, "usage": {"prompt_tokens": 1000,
            "completion_tokens": 100}, "cost": cost, "content": content, "calls": list(calls), **kw}


def office(file=None, result=None, name="create_word_file", status="ok"):
    """An office call: built `file` (done) or rejected with `result`."""
    c = {"name": name, "status": status, "done": file is not None, "arguments_chars": 10,
         "result": DONE.format(file) if file else result}
    if file:
        c["file"] = file
    return c


def extra(name, status="extra_tool", result="ok"):
    return {"name": name, "status": status, "done": False, "arguments_chars": 10, "result": result}


def rec(task, rep, rounds, ends=None, error=None, error_kind=None, task_hash=None):
    """A log record like the runner writes it; ends = end of every sent turn (default: one 'answer' per turn)."""
    turns = sorted({x["turn"] for x in rounds}) or [0]
    ends = ends or ["answer"] * (max(turns) + 1)
    r = {"format": 1, "task": task, "rep": rep, "task_hash": task_hash or load_tasks()[task].hash,
         "turns": [{"end": e, "rounds": sum(1 for x in rounds if x["turn"] == t)} for t, e in enumerate(ends)],
         "rounds": rounds, "outcome": ends[-1]}
    r["final_answer"] = rounds[-1]["content"][:MAX_LOGGED_TEXT] if r["outcome"] == "answer" else None
    if error:
        rounds[-1].update(error=error, error_kind=error_kind)
        r.update(error=error, error_kind=error_kind)
    return r


def make_run(root: Path, records, files=(), tasks=None, repeats=1, name="m") -> Path:
    folder = root / "run" / name
    (folder / "files").mkdir(parents=True)
    tasks = tasks or sorted({r["task"] for r in records})
    meta = {"model": {"name": name, "label": f"Model {name}"}, "profile": {"name": "default", "today": "2026-10-13"},
            "tasks": tasks, "repeats": repeats, "tool_hash": "x", "harness": "test"}
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (folder / "log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    for f in files:
        data = f[1] if isinstance(f, tuple) else b""
        (folder / "files" / (f[0] if isinstance(f, tuple) else f)).write_bytes(data)
    return folder


@pytest.fixture
def fake_check(monkeypatch):
    """Content check from the file name: 'bad' gives a hard defect, 'soft' a soft one; records the entries."""
    seen = []

    def check(entries, today=None):
        seen.append((today, [(Path(p).name, t.id, prev and Path(prev).name) for p, t, prev in entries]))
        out = {}
        for p, *_ in entries:
            defects = []
            if "bad" in Path(p).name:
                defects.append(Defect("no formula", "no formula", "hard", "formulas_min"))
            if "soft" in Path(p).name:
                defects.append(Defect("weekday", "weekday does not fit", "soft", "dates"))
            out[Path(p)] = Findings(defects, {"words": 42})
        return out

    monkeypatch.setattr(scoring, "check_files", check)
    return seen


def by_tag(results):
    return {f"{r.task}-{r.rep}": r for r in results}


def test_file_task(tmp_path, fake_check):
    a = "aushang-{}__r{}c{}__Aushang{}.docx"
    folder = make_run(tmp_path, [
        rec("aushang", 0, [rnd([office(a.format(0, 0, 0, ""))], cost=0.002, seconds=5.0),
                           rnd(content="Fertig! Der Aushang ist angehängt.", cost=0.001)]),
        # rejected first, then two calls in one round: rejected, built (soft defect)
        rec("aushang", 1, [rnd([office(result=JSON_ERROR)], seconds=4.0),
                           rnd([office(result=SCHEMA_ERROR), office(a.format(1, 1, 1, " soft"))], seconds=6.0),
                           rnd(content="Fertig.")]),
        rec("aushang", 2, [rnd([office(a.format(2, 0, 0, " bad"))]), rnd(content="Fertig.")]),
        # never a file; claims one
        rec("aushang", 3, [rnd([office(result=SCHEMA_ERROR)]), rnd(content="Ich habe die Word-Datei erstellt.")]),
    ], [a.format(0, 0, 0, ""), a.format(1, 1, 1, " soft"), a.format(2, 0, 0, " bad")], repeats=4)
    z = by_tag(scoring.score_run(folder))
    r0 = z["aushang-0"]
    assert (r0.run, r0.model, r0.kind, r0.file_type, r0.title) == ("run", "m", "file", "docx",
                                                                   "Tea kitchen notice (vague)")
    assert r0.file_first_call and r0.file_at_end and r0.rounds_to_file == 1 and r0.seconds_to_file == 5.0
    assert r0.cost == pytest.approx(0.003) and (r0.tokens_in, r0.tokens_out) == (2000, 200) and r0.seconds == 7.0
    assert r0.final_answer and r0.content_ok and r0.clean and r0.success and r0.scored and r0.metrics == {"words": 42}
    assert r0.delivered_file == a.format(0, 0, 0, "") and r0.previous_file is None and not r0.notes

    r1 = z["aushang-1"]
    assert not r1.file_first_call and r1.file_at_end and r1.rounds_to_file == 2 and r1.seconds_to_file == 10.0
    assert [(x["category"], x["file_after"]) for x in r1.rejections] == [("json", True), ("schema", True)]
    assert r1.recovered and r1.content_ok and not r1.clean and r1.soft_defects == ["weekday"] and r1.success
    assert r1.cost is None and r1.rejections[1]["text"] == "slides[2].title: Field required"

    r2 = z["aushang-2"]
    assert r2.content_ok is False and r2.hard_defects == ["no formula"] and r2.success is False

    r3 = z["aushang-3"]
    assert r3.file_at_end is False and r3.delivered_file is None and r3.content_ok is False and r3.success is False
    assert r3.claims_file and r3.recovered is False and r3.scored
    # one content-check call for all delivered files, with the profile's reference date
    assert len(fake_check) == 1 and fake_check[0][0] == "2026-10-13" and len(fake_check[0][1]) == 3


def test_follow_up_and_previous_file(tmp_path, fake_check):
    f0, f2 = "versammlung-0__r0c0__E.docx", "versammlung-0__r1c0__E.docx"
    g0 = "versammlung-1__r0c0__E.docx"
    folder = make_run(tmp_path, [
        rec("versammlung", 0, [rnd([office(f0)]), rnd(content="Erledigt."),
                               rnd([office(f2)], turn=1), rnd(content="Geändert.", turn=1)]),
        # second turn answered without a new file, but claims one
        rec("versammlung", 1, [rnd([office(g0)]), rnd(content="Erledigt."),
                               rnd(content="Ich habe das Dokument aktualisiert und gespeichert.", turn=1)]),
    ], [f0, f2, g0], repeats=2)
    z = by_tag(scoring.score_run(folder))
    r0, r1 = z["versammlung-0"], z["versammlung-1"]
    assert [t["fulfilled"] for t in r0.turns] == [True, True] and r0.turns_ok and r0.file_at_end and r0.success
    assert r0.delivered_file == f2 and r0.previous_file == f0 and r0.files_built == 2 and not r0.extra_files
    assert [t["fulfilled"] for t in r1.turns] == [True, False] and not r1.file_at_end and r1.success is False
    assert r1.delivered_file == g0 and r1.previous_file is None and r1.claims_file
    assert sorted(fake_check[0][1]) == [(f2, "versammlung", f0), (g0, "versammlung", None)]


def test_no_file_reply_and_behavior(tmp_path, fake_check):
    search, mail = extra("web_search"), extra("send_email")
    folder = make_run(tmp_path, [
        rec("bahncard", 0, [rnd([search]), rnd(content=BAHNCARD)]),
        rec("bahncard", 1, [rnd(content=BAHNCARD)]),  # no search
        rec("bahncard", 2, [rnd([search]), rnd([mail]), rnd(content=BAHNCARD)]),  # forbidden tool
        rec("bahncard", 3, [rnd([search]), rnd(content="Kostet 259 €. Siehe [hier](https://bahn.de/bc50).")]),
        # an office call: unnecessary; a failed extra-tool call is not an office call
        rec("bahncard", 4, [rnd([extra("web_search", "parse_error", "Error: …")]), rnd([office("bahncard-4__x.docx")]),
                            rnd(content=BAHNCARD)]),
        rec("bahncard", 5, [rnd([search]), rnd([office(result="Error: tool \"create_wort\" not found.",
                                                       name="create_wort", status="unknown_function")]),
                            rnd(content=BAHNCARD)]),
    ], repeats=6)
    z = by_tag(scoring.score_run(folder))
    s0, s1, s2, s3, s4, s5 = (z[f"bahncard-{i}"] for i in range(6))
    assert (s0.missing_tools, s0.unwanted_tools, s0.missing_reply_topics, s0.success) == ([], [], [], True)
    assert s0.unnecessary_call is False and s0.content_ok is None and s0.extra_tools_offered == ["web_search",
                                                                                                  "send_email"]
    assert s1.missing_tools == ["web_search"] and s1.success is False
    assert {"label": "tool not called", "severity": "hard", "check": "tools_expected",
            "text": "expected tool not called: web_search"} in s1.other_defects
    assert s2.unwanted_tools == ["send_email"] and s2.extra_tools_called == ["web_search", "send_email"]
    assert s2.success is False
    assert s3.missing_reply_topics == ["Empfehlung", "Ersparnis"] and s3.success is False
    assert s3.invented_links == ["https://bahn.de/bc50"]
    assert [d["label"] for d in s3.other_defects] == ["missing topic in reply"]
    assert s4.unnecessary_call and s4.success is False and s4.extra_calls == 1 and s4.office_calls == 1
    assert s4.extra_tools_called == ["web_search"] and s4.rejections == []
    # a misspelt office function is still an (unnecessary) office attempt
    assert s5.unnecessary_call and [x["category"] for x in s5.rejections] == ["wrong_function"]
    assert not fake_check[0][1]  # nothing to check


def test_reply_check_of_file_task(tmp_path, fake_check):
    files = [f"zeiterfassung-{i}__r0c0__Z.xlsx" for i in range(3)]
    long = "Fertig. " + "x" * MAX_LOGGED_TEXT
    folder = make_run(tmp_path, [
        rec("zeiterfassung", 0, [rnd([office(files[0], name="create_excel_file")]),
                                 rnd(content="Ein Makro geht leider nicht, aber die Tabelle ist fertig.")]),
        rec("zeiterfassung", 1, [rnd([office(files[1], name="create_excel_file")]), rnd(content="Fertig.")]),
        rec("zeiterfassung", 2, [rnd([office(files[2], name="create_excel_file")]), rnd(content=long)]),
    ], files, repeats=3)
    z = by_tag(scoring.score_run(folder))
    assert z["zeiterfassung-0"].success and z["zeiterfassung-0"].missing_reply_topics == []
    assert z["zeiterfassung-1"].content_ok and z["zeiterfassung-1"].success is False
    r2 = z["zeiterfassung-2"]
    assert r2.reply_truncated and r2.success is None  # the cut part could hold the topic


def test_outages_and_server_errors(tmp_path, fake_check):
    f = "aushang-{}__r0c0__A.docx"
    folder = make_run(tmp_path, [
        rec("aushang", 0, [rnd([office(f.format(0))]), rnd()], ["error"], "HTTP 503", "provider"),  # file there
        rec("aushang", 1, [rnd([office(f.format(1) + " bad")]), rnd()], ["error"], "HTTP 503", "provider"),
        rec("aushang", 2, [rnd()], ["error"], "ReadError", "network"),  # before any file
        rec("aushang", 3, [rnd()], ["error"], "HTTP 500: failed to parse tool call", "server"),
        rec("bahncard", 0, [rnd()], ["error"], "HTTP 503", "provider"),
        rec("bahncard", 1, [rnd([office("bahncard-1__r0c0__B.docx")]), rnd()], ["error"], "HTTP 503", "provider"),
    ], [f.format(0), f.format(1) + " bad", "bahncard-1__r0c0__B.docx"], tasks=["aushang", "bahncard", "termin"],
        repeats=4)
    z = by_tag(scoring.score_run(folder))
    assert (z["aushang-0"].scored, z["aushang-0"].success) == (True, True)  # outcome settled before the outage
    assert (z["aushang-1"].scored, z["aushang-1"].success) == (True, False)  # ... whatever the content
    assert not z["aushang-2"].scored and z["aushang-2"].error_kind == "network"
    a3 = z["aushang-3"]
    assert (a3.scored, a3.success, a3.error_kind, a3.outcome) == (True, False, "server", "error")
    assert "no final answer" not in a3.notes and a3.notes[-1].startswith("error (server)")
    assert not z["bahncard-0"].scored and z["bahncard-1"].scored and z["bahncard-1"].success is False
    # the selection of the run: missing log lines are not scored
    missing = [r for r in z.values() if r.outcome == "missing"]
    assert {f"{r.task}-{r.rep}" for r in missing} == {"bahncard-2", "bahncard-3"} | {f"termin-{i}" for i in range(4)}
    assert all(not r.scored and r.success is None for r in missing)


def test_round_limit(tmp_path, fake_check):
    limit = rnd([office(result=JSON_ERROR)], content="Ich versuche es noch einmal.",
                not_executed=[{"name": "create_word_file", "arguments_chars": 50}])
    limit["calls"] = []
    folder = make_run(tmp_path, [
        rec("aushang", 0, [rnd([office(result=JSON_ERROR)]), rnd([office("aushang-0__r1c0__A.docx")]), limit],
            ["round_limit"]),
        rec("aushang", 1, [rnd([office("aushang-1__r0c0__A.docx")]), rnd(content="")]),
        rec("versammlung", 0, [rnd([office("versammlung-0__r0c0__V.docx")]), {**limit, "turn": 0},
                               rnd([office("versammlung-0__r1c0__V.docx")], turn=1), rnd(content="Fertig.", turn=1)],
            ["round_limit", "answer"]),
    ], ["aushang-0__r1c0__A.docx", "aushang-1__r0c0__A.docx", "versammlung-0__r0c0__V.docx",
        "versammlung-0__r1c0__V.docx"], repeats=2, tasks=["aushang", "versammlung"])
    z = by_tag(scoring.score_run(folder))
    a0, a1, v0 = z["aushang-0"], z["aushang-1"], z["versammlung-0"]
    assert a0.round_limit and not a0.final_answer and a0.file_at_end and a0.success
    assert "no final answer" not in a0.notes and "round limit reached, hence no final answer" in a0.notes
    assert not a1.round_limit and "no final answer" in a1.notes and a1.success  # no answer: not part of success
    assert not v0.round_limit and v0.final_answer and "turn 1: round limit reached" in v0.notes


def test_lost_file_and_changed_task(tmp_path, fake_check):
    folder = make_run(tmp_path, [
        rec("aushang", 0, [rnd([office("aushang-0__r0c0__A.docx")]), rnd(content="Fertig.")], task_hash="old"),
        rec("aushang", 1, [rnd([office("aushang-1__r0c0__A.docx")]), rnd(content="Fertig.")]),  # not in files/
    ], ["aushang-0__r0c0__A.docx"], repeats=2)
    z = by_tag(scoring.score_run(folder))
    assert z["aushang-0"].task_changed and z["aushang-0"].success
    r1 = z["aushang-1"]
    assert r1.content_ok is None and r1.success is None and r1.scored
    assert "file of the last done call not in files/" in r1.notes


@pytest.mark.parametrize("status, text, expected", [
    ("ok", JSON_ERROR, "json"),
    ("ok", SCHEMA_ERROR, "schema"),
    ("ok", "The file was NOT created …:\n- sheets[0]: the arguments are garbled here (a key …)", "garbled"),
    ("ok", "The file was NOT created …:\n- sheets[0].columns[4] ('Netto'): the total needs values", "validation"),
    ("ok", "The file could not be created because of an internal error. Tell the user to try again later.",
     "exception"),
    ("parse_error", "Error: the arguments of `x` could not be parsed.", "json"),
    ("not_object", "Error: the arguments of `x` must be a JSON object.", "not_object"),
    ("unknown_function", 'Error: tool "create_excel_workboard" not found.', "wrong_function"),
    ("exception", '{"error": "Tools.create_word_file() missing 1 required positional argument: \'blocks\'"}', "schema"),
    ("exception", '{"error": "division by zero"}', "exception"),
    ("ok", "Something else entirely", "other"),
])
def test_categories(status, text, expected):
    assert scoring.category(status, text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Ich habe dir die Excel-Datei erstellt.", True),
    ("Die Präsentation steht zum Download bereit.", True),
    ("Das Dokument wurde erfolgreich erstellt!", True),
    ("Leider konnte die Datei nicht erstellt werden.", False),
    ("Ich habe ein ausführliches Konzept erstellt. Da es bei der Datei zu Fehlern kam, hier der Text.", False),
    ("Sobald die Datei erstellt ist, melde ich mich.", False),
    ("Hier ist eine Übersicht in Textform.", False),
])
def test_claims_file(text, expected):
    assert scoring.claims_file(text) is expected


def test_links():
    assert scoring.links("Siehe [Datei](sandbox:/mnt/data/a.xlsx) und https://x.de/a.") == [
        "sandbox:/mnt/data/a.xlsx", "https://x.de/a."]
    assert scoring.links("Keine Links hier.") == []


def test_results_file_and_cli(tmp_path, fake_check, capsys):
    folder = make_run(tmp_path, [rec("aushang", 0, [rnd([office("aushang-0__r0c0__A.docx")]),
                                                    rnd(content="Fertig.")])], ["aushang-0__r0c0__A.docx"])
    make_run(tmp_path, [rec("bahncard", 0, [rnd(content=BAHNCARD)])], name="n")
    assert model_folders([folder.parent]) == [folder, folder.parent / "n"]
    assert model_folders([folder]) == [folder]
    with pytest.raises(FileNotFoundError):
        model_folders([tmp_path])
    assert cli(["score", str(folder.parent)]) == 0
    assert "1 task runs, 1 scored, 1 successful" in capsys.readouterr().out
    lines = [json.loads(x) for x in (folder / scoring.RESULTS).read_text().splitlines()]
    assert len(lines) == 1 and {"task", "success", "rejections", "turns", "defects"} <= set(lines[0])
    assert not {"file_path", "previous_path", "answer_text", "file_lost", "unknown_task"} & set(lines[0])
    loaded = scoring.load_results(folder)
    assert loaded[0].to_dict() == lines[0] and len(fake_check) == 2  # read back, not scored again
    (folder / "log.jsonl").touch()  # a newer log: scored again
    scoring.load_results(folder)
    assert len(fake_check) == 3


# -------------------------------------------------------------------------------- real files, real check --

def built(task: str, key: str | None, folder: Path, name: str) -> tuple[str, Path]:
    call = json.loads((load_tasks()[task].reference_path).read_text(encoding="utf-8"))
    call = call[key] if key else call
    result = build(call["function"], call["arguments"])
    path = folder / f"{name}{Path(result.files[-1].name).suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result.files[-1].data)
    return path.name, path


def test_real_follow_up_docx(tmp_path):
    files = tmp_path / "run" / "m" / "files"
    first, _ = built("versammlung", "previous", files, "versammlung-0__r0c0__Einladung")
    second, _ = built("versammlung", None, files, "versammlung-0__r1c0__Einladung")
    old, _ = built("versammlung", "previous", files, "versammlung-1__r1c0__Einladung")
    first1, _ = built("versammlung", "previous", files, "versammlung-1__r0c0__Einladung")
    runs = [rec("versammlung", rep, [rnd([office(a)]), rnd(content="Erledigt."), rnd([office(b)], turn=1),
                                     rnd(content="Geändert.", turn=1)])
            for rep, (a, b) in enumerate([(first, second), (first1, old)])]
    folder = tmp_path / "run" / "m"
    (folder / "meta.json").write_text(json.dumps({"model": {"name": "m"}, "profile": {"today": "2026-10-13"},
                                                  "tasks": ["versammlung"], "repeats": 2}), encoding="utf-8")
    (folder / "log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    z = by_tag(scoring.score_run(folder))
    good, unchanged = z["versammlung-0"], z["versammlung-1"]
    assert good.content_ok and good.success and good.previous_file == first and "retained" in good.metrics
    # the first version delivered again: the old date and the dropped agenda item are still in it
    assert unchanged.file_at_end and unchanged.content_ok is False and unchanged.success is False
    assert "forbidden content" in unchanged.hard_defects


@pytest.mark.slow
def test_real_follow_up_xlsx(tmp_path):
    files = tmp_path / "run" / "m" / "files"
    first, _ = built("sparquote", "previous", files, "sparquote-0__r0c0__Budget")
    second, _ = built("sparquote", None, files, "sparquote-0__r1c0__Budget")
    log = [rec("sparquote", 0, [rnd([office(first, name="create_excel_file")]), rnd(content="Fertig."),
                                rnd([office(second, name="create_excel_file")], turn=1),
                                rnd(content="Fertig.", turn=1)])]
    folder = tmp_path / "run" / "m"
    (folder / "meta.json").write_text(json.dumps({"model": {"name": "m"}, "profile": {"today": "2026-10-13"},
                                                  "tasks": ["sparquote"], "repeats": 1}), encoding="utf-8")
    (folder / "log.jsonl").write_text(json.dumps(log[0]) + "\n", encoding="utf-8")
    (r,) = scoring.score_run(folder)
    assert r.content_ok and r.success and r.previous_file == first and int(r.metrics["retained"].rstrip(" %")) >= 80
