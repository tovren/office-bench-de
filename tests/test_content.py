"""The content check as a whole (officebench.checks.content): the check tables, task detection from file names, and
Word/PowerPoint files built by the real tool from tests/fixtures/content/*.json (no LibreOffice needed: xlsx here
only without recalculation). The single checks on short texts are in tests/checks/; xlsx with recalculation in
test_content_xlsx.py; agreement with the blind review in test_content_gold.py."""

from datetime import date
from pathlib import Path

import pytest
from helpers import build_fixture, make_task, only

from officebench.checks import content
from officebench.checks.content import check_file, check_files, check_one, task_from_path
from officebench.checks.core import Context, Document
from officebench.checks.dates import check_dates
from officebench.checks.registry import FILE_TYPES, GENERAL_CHECKS, TASK_CHECKS
from officebench.tasks import load_tasks

PROTOKOLL = dict(tables_min=1, names=["Anna", "Ben", "Carla", "David"],
                 topics={"Projektstand": "projektstand", "Urlaubsplanung": "urlaub", "Ticketsystem": "ticket",
                         "To-do-Liste": ["to-?do|aufgaben|verantwortlich",
                                         {"pattern": r"^\s*(Anna|Ben|Carla|David)\s*[:–-]", "min": 2}]})


@pytest.fixture(scope="module")
def folder(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("content")


# ------------------------------------------------------------------------------------------- basics --

def test_check_tables():
    for name, (label, severity, description) in GENERAL_CHECKS.items():
        assert label and severity in ("hard", "soft") and description, name
    for name, (label, severity, file_types) in TASK_CHECKS.items():
        assert set(file_types) <= set(FILE_TYPES), name
        assert name == "disable" or (label and severity in ("hard", "soft")), name


def test_no_task_branches_in_code():
    # all task-specific checks come from [checks]; no 'if task == "budget"' left
    for path in sorted(Path(content.__file__).parent.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for task_id in load_tasks():
            assert f'== "{task_id}"' not in text and f"== '{task_id}'" not in text, (path.name, task_id)


def test_task_from_path():
    assert task_from_path(Path("x/budget-3__r0c0__Haushalt.xlsx")) == "budget"
    assert task_from_path(Path("projektplan-12__r1c0__Plan.xlsx")) == "projektplan"
    assert task_from_path(Path("unknown-1__r0c0__Plan.xlsx")) is None
    assert task_from_path(Path("ziel/sonstwas/datei.docx")) is None


def test_task_from_path_with_underscore(monkeypatch):
    tasks = {"budget": make_task("xlsx"), "budget_quer": make_task("xlsx")}
    monkeypatch.setattr(content, "load_tasks", lambda: tasks)
    assert task_from_path(Path("budget_quer-2__r0c0__X.xlsx")) == "budget_quer"
    assert task_from_path(Path("budget-2__r0c0__X.xlsx")) == "budget"


# --------------------------------------------------------------------------- Word and PowerPoint --

def test_docx_protokoll_with_errors(folder):
    path = build_fixture("protokoll_errors", folder)
    f = check_files([(path, make_task("docx", header_contains="Team Nord", numbered_list=True, **PROTOKOLL))])[path]
    p = {m.check: m for m in f.defects if m.check != "weekday"}
    assert p["foreign_script"].hard and "直观" in p["foreign_script"]
    hard, soft = (only(f.defects, "weekday", s) for s in ("hard", "soft"))
    assert "„Dienstag, 12. Oktober 2026“" in hard[0] and "Dienstag | 26.10.2026" in hard[0]
    assert "Fr., 21.10." in soft[0]  # no year written: soft
    assert "KW 46" in p["calendar_week"]
    assert "System X" in p["placeholders"] and "[Name eintragen]" in p["placeholders"]
    assert "only the header row" in p["empty_table"]
    assert "numbered_list" in p and "header_contains" not in p
    assert "topics" not in p and "names" not in p and "tables_min" not in p
    assert not f.ok


def test_docx_protokoll_clean(folder):
    path = build_fixture("protokoll_good", folder)
    f = check_files([(path, make_task("docx", numbered_list=True, headings_min=5, **PROTOKOLL))])[path]
    assert f.clean, [str(m) for m in f.defects]
    missing = check_file(path, make_task("docx", header_contains="Personalabteilung", toc=True, words_max=50,
                                         tables_min=2, count=[{"name": "Fragen", "pattern": r"\?\s*$", "min": 5}]))
    assert {m.check for m in missing} == {"header_contains", "toc", "words_max", "tables_min", "count"}
    assert [m.severity for m in missing if m.check == "words_max"] == ["soft"]


def test_docx_konzept_calculations_and_calendar(folder):
    path = build_fixture("konzept_calculation", folder)
    m = check_file(path, make_task("docx", dates_from="2026-10-13", toc=True))
    p = {x.check: x for x in m}
    assert set(p) == {"calendar_week", "past_dates", "text_arithmetic"}, [str(x) for x in m]
    assert "KW 1-6 (Dezember 2026 - Januar 2027)" in p["calendar_week"] and "KW 52" not in p["calendar_week"]
    assert "KW 19/2026" in p["past_dates"] and "01.10.2026" not in p["past_dates"]  # 01.10.2026 starts a period
    assert "7.860" in p["text_arithmetic"] and "816" in p["text_arithmetic"] and "15.564" in p["text_arithmetic"]
    assert all(x.severity == "soft" for x in m)


def test_pptx_slides_chart_table(folder):
    path = build_fixture("praesentation", folder)
    good = check_file(path, make_task("pptx", slides=[5, 8], chart=True, chart_type="line", tables_min=1,
                                      topics={"Chancen": "chance", "Risiken": "risik"}))
    assert [m.check for m in good] == ["empty_table"]  # empty third header cell of the timeline table
    bad = check_file(path, make_task("pptx", slides=[6, 8], chart_type=["bar", "column"], chart_series_min=2,
                                     tables_min=2))
    assert {m.check for m in bad} >= {"slides", "chart_type", "chart_series_min", "tables_min"}
    assert all(m.hard for m in bad if m.check != "empty_table")


def test_wrong_and_unknown_file_type(folder, tmp_path):
    path = build_fixture("praesentation", folder)
    m = check_file(path, make_task("docx"))
    assert m[0].check == "wrong_file_type" and m[0].hard
    txt = tmp_path / "x.txt"
    txt.write_text("x")
    assert [x.label for x in check_file(txt)] == ["unknown_file_type"]
    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"kein zip")
    assert [x.label for x in check_file(broken)] == ["unreadable"]


def test_xlsx_structure_without_recalculation(folder):
    """Checks that need no recalculation (LibreOffice is skipped: recalculated = {})."""
    path = build_fixture("reisekosten", folder)
    ctx = Context(make_task("xlsx", data_rows_min=6,
                            columns=["datum", "ziel", "anlass|zweck", r"kilometer|\bkm\b", "verpflegung"],
                            dates_between=["2026-10-01", "2026-10-31"], months=[10, 10], sheets_min=2, chart=True,
                            value_ranges=[{"column": "bewertung", "min": 1, "max": 5}]))
    f = check_one(path, ctx, {})
    p = {m.check: m for m in f.defects}
    assert "not_recalculated" in p
    assert "only 4 data rows" in p["data_rows_min"] and "„verpflegung“" in p["columns"]
    assert "Fahrten!A5 = 02.11.2026" in p["dates_between"] and "months" not in p
    assert "Fahrten!F5 = 7" in p["value_ranges"] and "no second sheet" in p["sheets_min"] and "chart" in p


def test_today_as_text_and_cli(folder, capsys):
    # dates without a year take the year of `today` when the text gives none: 13.10.2027 is a Wednesday
    ctx = Context(None, date(2027, 10, 13))
    check_dates(Document([("paragraph 1", "Workshop am Mi., 13.10.")]), ctx)
    assert not only(ctx.defects, "weekday")
    path = build_fixture("protokoll_errors", folder)
    m = check_file(path, "protokoll", today="2027-10-13")  # 'today' as text, like in the run log
    assert any("12.10.2026 is a Monday" in x for x in m if x.check == "weekday")
    content.main([str(path), "--task", "protokoll", "--today", "2026-10-13"])
    out = capsys.readouterr().out
    assert "[hard] weekday does not match" in out and "[soft] placeholders instead of content" in out
    assert "NOT ok" in out
