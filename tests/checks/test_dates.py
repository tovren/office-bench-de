"""Date checks in running text and tables: weekday, calendar_week, past_dates, weekend (checks/dates.py)."""
from datetime import date
from pathlib import Path

import pytest

from officebench.checks.core import CRASHED, Context, Document, Table
from officebench.checks.dates import check_dates, dates_in
from officebench.checks.util import norm
from officebench.tasks import Attachment, Task, TaskSpec, Turn

# ------------------------------------------------------------------------------------------ helpers --


def task(file_type: str | None = "docx", dates_from: str | None = None, turns: tuple = (), **checks) -> Task:
    """A task with these [checks] (validated like a task file); `turns` are the loaded turns the checks read."""
    spec = TaskSpec.model_validate({"id": "test", "title": "Test", "version": 1,
                                    "kind": "file" if file_type else "no_file", "file_type": file_type,
                                    "dates_from": dates_from, "turns": [{"text": "Test"}], "checks": checks})
    return Task(spec=spec, turns=turns, path=Path("test"), hash="test")


def date_defects(paragraphs, tables=(), today=date(2026, 10, 13), **kw) -> list:
    """Defects of check_dates for paragraphs [(where, text)] or strings (only it reports the date checks)."""
    ctx = Context(task(None, **kw) if kw else None, today)
    doc = Document([(f"paragraph {i}", p) if isinstance(p, str) else p for i, p in enumerate(paragraphs, 1)],
                   list(tables))
    check_dates(doc, ctx)
    return ctx.defects


def only(defects, check: str) -> list:
    return [m for m in defects if m.check == check]


def test_disable_switches_general_check_off():
    ctx = Context(task(None, disable=["placeholders", "weekday"]))
    check_dates(Document([("paragraph 1", "System X am Dienstag, 12.10.2026")]), ctx)
    assert ctx.defects == []


# --------------------------------------------------------------------------------------- weekdays --

@pytest.mark.parametrize("text, severity", [
    ("Nächstes Treffen: Dienstag, 26. Oktober 2026, 10:00 Uhr.", "hard"),
    ("| Datum | Dienstag, 12. Oktober 2026 |", "hard"),
    ("Mittwoch, 03.11.2026", "hard"),
    ("12.10.2026 (Mittwoch)", "hard"),
    ("Rückmeldung bis Fr., 21.10.", "soft"),  # no year: year from the context (13.10.2026)
    ("Frist Di., 04.01.", "soft"),  # January after October: next year, 04.01.2027 is a Monday
])
def test_weekday_wrong(text, severity):
    m = only(date_defects([text]), "weekday")
    assert len(m) == 1 and m[0].severity == severity, m


@pytest.mark.parametrize("text", [
    "Teambesprechung am Montag, 12. Oktober 2026", "Montag, 12.10.2026", "Mo., 12.10.", "Frist Mo., 04.01.",
    "Supportzeiten Mo–Fr, 08:00–17:00 Uhr", "Mo-Fr 12.10.-16.10.2026", "Montag bis Freitag, 13.10.",
    "jeden Montag, 9 Uhr", "Version 1.2.3 vom Montag", "Tel. 0711 12.34.56, Montag erreichbar",
    "Freitag, 13. November 2026",
])
def test_weekday_right_or_no_pair(text):
    assert not only(date_defects([text]), "weekday")


def test_weekday_year_from_context():
    # 13.10.2027 is a Wednesday: the year comes from the last date with a year
    assert not only(date_defects(["Projektstart 01.09.2027", "Workshop am Mi., 13.10."]), "weekday")
    assert only(date_defects(["Workshop am Mi., 13.10."]), "weekday")  # 13.10.2026 is a Tuesday


def test_weekday_in_table_row():
    tab = Table("table 1", [["Aufgabe", "Tag", "Datum"], ["Test", "Di", "26.10.2026"], ["Abnahme", "Fr", "06.11.2026"]])
    m = only(date_defects([], [tab]), "weekday")
    assert len(m) == 1 and "26.10.2026 is a Monday" in m[0] and "row 2" in m[0]


# ---------------------------------------------------------------------------------- calendar weeks --

@pytest.mark.parametrize("text", [
    "Implementation | KW 1‑6 (Dezember 2026 – Januar 2027)",
    "KW 44 (02.11.2026)", "Demo am 26.10.2026 (KW 45)", "KW 53/2027", "KW 54",
])
def test_calendar_week_wrong(text):
    m = only(date_defects([text]), "calendar_week")
    assert len(m) == 1 and m[0].severity == "soft", m


@pytest.mark.parametrize("text", [
    "KW 42‑44 (Oktober 2026)", "KW 7–10 (Februar 2027)", "KW 52–1 (Dezember 2026 – Januar 2027)",
    "KW 53 (28.12.2026–03.01.2027)", "KW 53/2026", "KW 44 (26.10.–30.10.2026)", "Demo am 26.10.2026 (KW 44)",
    "KW 44/45 Pilot", "KW 45: Juni-Termine abstimmen", "Start: KW 44/2026, Go-live: Ende Januar 2027",
    "KW 1-6", "Woche 1-3 Analyse", "KW 44 (Anfang November)", "KW 1 (04.01.2027)",
])
def test_calendar_week_right_or_without_date(text):
    assert not only(date_defects([text]), "calendar_week")


def test_calendar_week_in_table_row():
    tab = Table("table 2", [["Phase", "KW", "Start"], ["Pilot", "KW 44", "26.10.2026"],
                            ["Rollout", "KW 46", "06.11.2026"]])
    m = only(date_defects([], [tab]), "calendar_week")
    assert len(m) == 1 and "KW 46" in m[0] and "row 3" in m[0]


def test_calendar_week_column_and_text_in_table_row():
    # KW column as a number against start and end; a week of the start, the end or between fits
    plan = Table("Plan", [["Rufbereitschaft"], ["KW", "Erster Tag", "Letzter Tag", "Name"],
                          ["45", "02.11.2026", "06.11.2026", "Keller"], ["45", "09.11.2026", "13.11.2026", "Brandt"],
                          ["46-47", "09.11.2026", "20.11.2026", "Lehmann"]], calc=False)
    m = only(date_defects([], [plan]), "calendar_week")
    assert len(m) == 1 and "KW 45 | 09.11.2026 … 13.11.2026" in m[0] and "row 4" in m[0] and "row 3" not in m[0], m
    # a week in running text: against Start/Ende, not against a deadline or a plan date
    project = Table("Projektplan", [["Arbeitspaket", "Start", "Ende"],
                                    ["Kick-off in KW 42", "19.10.2026", "30.10.2026"],
                                    ["Umzug in KW 2", "11.01.2027", "15.01.2027"]], calc=False)
    m = only(date_defects([], [project]), "calendar_week")
    assert len(m) == 1 and "KW 42" in m[0] and "KW 2" not in m[0], m
    deadline = Table("table 2", [["Maßnahme", "Frist"], ["Schulungstermin (KW 46) koordinieren", "30.10.2026"]])
    assert not only(date_defects([], [deadline]), "calendar_week")


def test_week_in_heading():
    doc = [("title", "Protokoll der Teambesprechung vom 12.10.2026"), ("paragraph 1", "Teambesprechung – Woche 41")]
    m = only(date_defects(doc), "calendar_week")
    assert len(m) == 1 and "Woche 41" in m[0] and "KW 42" in m[0]
    assert not only(date_defects([doc[0], ("paragraph 1", "Teambesprechung KW 42")]), "calendar_week")


# ------------------------------------------------------------------------------------------- dates --

def test_past_dates_before_dates_from():
    m = only(date_defects(["Der Start ist für KW 19/2026 vorgesehen.", "Kick-off am 01.10.2026.",
                           "Go-live am 01.02.2027."], dates_from="2026-10-13"), "past_dates")
    assert len(m) == 1 and "KW 19/2026" in m[0] and "01.10.2026" in m[0] and "01.02.2027" not in m[0]


@pytest.mark.parametrize("text", [
    "Stand: 01.10.2026", "Protokoll der Besprechung vom 12.10.2026", "Seit 01.03.2025 nutzen wir E-Mail.",
    "Laufzeit 01.10.2026 – 31.03.2027.", "Termin am 13.10.2026", "Frist bis 15.03.",  # no year: not counted
])
def test_no_past_dates(text):
    assert not only(date_defects([text], dates_from="2026-10-13"), "past_dates")


def test_past_dates_label_in_table_row():
    # the label cell left of the date ('Datum') marks the document's own date; a deadline in the next row still counts
    ctx = Context(task(None, dates_from="2026-10-13"))
    check_dates(Document([("table 1, row 2", "Datum"), ("table 1, row 2", "Montag, 12. Oktober 2026"),
                          ("table 1, row 3", "Frist"), ("table 1, row 3", "Freitag, 9. Oktober 2026")]), ctx)
    m = only(ctx.defects, "past_dates")
    assert len(m) == 1 and "9. Oktober" in m[0] and "12. Oktober" not in m[0]


def test_past_dates_only_with_dates_from():
    assert not only(date_defects(["Kick-off am 01.10.2026."]), "past_dates")
    title = Context(task(None, dates_from="2026-10-13"))
    check_dates(Document([("title", "Konzept vom 01.10.2026")]), title)
    assert not title.defects


@pytest.mark.parametrize("text, year", [
    ("Freitag, 11.12. 17:00 Uhr", None), ("bis Freitag, 27.11. 12 Uhr", None), ("24.12. 18h", None),
    ("12.10.26", 2026), ("12.10. 2026", 2026), ("12.10.2026 17:00", 2026), ("Stand 31.03.2027.", 2027),
])
def test_time_is_no_year(text, year):
    assert [f.year for f in dates_in(norm(text))] == [year]


def test_year_out_of_range_without_crash():
    ctx = Context()
    check_dates(Document([("A", "KW 44 (Dezember 9999)"), ("B", "am 01.01.9999 und 31.12.0001")]), ctx)
    assert all(m.label != CRASHED for m in ctx.defects)


# ------------------------------------------------------------------------------------------ weekend --

@pytest.mark.parametrize("text, expected", [
    ("Abgabe bis 17.10.2026.", True), ("Frist: 18.10.", True), ("Kick-off am 01.11.2026", True),
    ("Abgabe bis Samstag, 17.10.2026.", False),  # weekday written out: intended (weekday checks the pair)
    ("Urlaub vom 17.10. bis 25.10.", False), ("Ab 1. November 2026 gilt die Regelung.", False),
    ("Die Weihnachtsfeier findet am 12.12. statt", False), ("Termin am 11.12.2026", False),
    ("Am 17.10.–18.10. Messe", False),
    ("Entscheidung bis 25.10.2026, damit das Angebot noch gilt.", True),  # 'gilt' after the date: still a deadline
    ("Bestehende Vereinbarungen gelten bis zum 31.10.2026 weiter.", False), ("Angebot gültig bis 31.10.2026.", False),
])
def test_weekend(text, expected):
    m = only(date_defects([text]), "weekend")
    assert bool(m) == expected and all(x.severity == "soft" for x in m), m


def test_weekend_in_deadline_column_not_for_given_or_purchase_date():
    tab = Table("table 1", [["Aufgabe", "Frist", "Kaufdatum", "Garantie bis"],
                            ["A", "17.10.2026", "17.10.2026", "18.10.2026"], ["B", "19.10.2026", "18.10.2026", "x"],
                            ["C", "01.11.2026", "", ""]])
    m = only(date_defects([], [tab]), "weekend")
    assert len(m) == 1 and "17.10.2026" in m[0] and "row 2" in m[0] and "01.11.2026" in m[0]
    ctx = Context(task("docx", turns=(Turn(text="Ab 1. November 2026 gilt die neue Regelung.", expect="file"),)))
    check_dates(Document([], [tab]), ctx)
    assert "01.11.2026" not in only(ctx.defects, "weekend")[0]  # the date comes from the prompt


def test_weekend_date_from_attachment():
    """A weekend date that already stands in an attached file is no mistake of the model either."""
    tab = Table("table 1", [["Aufgabe", "Frist"], ["A", "17.10.2026"], ["B", "18.10."]])
    attachment = Attachment(name="Notizen.docx", text="Frist für A: 17.10.2026\nB bis 18.10.")
    turn = Turn(text="Mach daraus eine Aufgabenliste.", expect="file", attachments=(attachment,))
    ctx = Context(task("docx", turns=(turn,)))
    check_dates(Document([], [tab]), ctx)
    assert not only(ctx.defects, "weekend")
    ctx = Context(task("docx", turns=(Turn(text="Mach daraus eine Aufgabenliste.", expect="file"),)))
    check_dates(Document([], [tab]), ctx)
    assert "17.10.2026" in only(ctx.defects, "weekend")[0] and "18.10." in only(ctx.defects, "weekend")[0]
