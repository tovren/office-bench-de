"""Checks of the newer vocabulary on small files built here with openpyxl, python-docx and python-pptx (no
LibreOffice): forbidden, topics_soft, values_present, chart_values / chart_series (pptx cache, xlsx references),
notes_min, sorted, groups, retained, side_by_side, last_slide_topics, slides_added, column_format, workdays,
numbers_sourced, and their validation in the task schema. Cases that need the recalculation (formulas across sheets,
percent scale in calculations) are in test_content_xlsx.py."""

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from docx import Document
from helpers import make_task, only
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Emu, Inches
from pydantic import ValidationError

from officebench.checks import content
from officebench.checks.content import check_file, check_files, check_one
from officebench.checks.core import Context
from officebench.tasks import Attachment, TaskError, Turn, load_task


def defects(path: Path, task=None, previous=None) -> list:
    """Defects of a docx/pptx (no recalculation needed) or of a xlsx with its stored values."""
    if path.suffix == ".xlsx":
        return check_one(path, Context(task, previous=previous), {}).defects
    return check_file(path, task, previous=previous)


# ---------------------------------------------------------------------------------------- fixtures --

def _docx(path: Path, paragraphs, cells=()) -> Path:
    d = Document()
    for text in paragraphs:
        d.add_paragraph(text)
    if cells:
        t = d.add_table(rows=len(cells), cols=len(cells[0]))
        for r, row in enumerate(cells):
            for c, text in enumerate(row):
                t.cell(r, c).text = text
    d.save(path)
    return path


MINUTES = ["Protokoll der Mitgliederversammlung", "TOP 1: Haushalt 2027", "TOP 3: Parkplatzsituation am Standort Nord",
           "Die Kosten betragen 1.234,56 € und es gibt eine Gutschrift von −200 €.",
           "Laut Satzung [1] ist das zulässig."]


@pytest.fixture(scope="module")
def folder(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("vocabulary")


@pytest.fixture(scope="module")
def minutes(folder) -> Path:
    return _docx(folder / "protokoll.docx", MINUTES, [["Punkt", "Stimmen"], ["Ja", "45"], ["Nein", "78"]])


def _slides(path: Path, chart: bool = True) -> Path:
    prs = Presentation()
    title = prs.slides.add_slide(prs.slide_layouts[0])
    title.shapes.title.text = "Schulung Datenschutz"
    title.notes_slide.notes_text_frame.text = "Kurz."
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Teilnehmer je Quartal"
    if chart:
        data = CategoryChartData()
        data.categories = ["Q1", "Q2", "Q3", "Q4"]
        data.add_series("Teilnehmer", (45, 78, 130, 112))
        data.add_series("Kosten (Tsd. €)", (1.2, 3.4, 2.2, 0.8))
        slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1.5), Inches(8), Inches(5), data)
    slide.notes_slide.notes_text_frame.text = "Hier erkläre ich die Zahlen der vier Quartale im Detail."
    prs.slides.add_slide(prs.slide_layouts[1]).shapes.title.text = "Fragen"
    prs.save(path)
    return path


@pytest.fixture(scope="module")
def slides(folder) -> Path:
    return _slides(folder / "folien.pptx")


def _inventory(path: Path, overview: list) -> Path:
    """Sheet 1: list of devices with a total row; sheet 2: the overview rows given, a bar chart of the count."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventar"
    ws.append(["Inventarnummer", "Gerätetyp", "Kaufpreis (€)", "Raum"])
    for i, (kind, price) in enumerate([("Laptop", 1000), ("Laptop", 1200), ("Monitor", 200), ("Monitor", 250),
                                       ("Monitor", 150), ("Drucker", 500)], 1):
        ws.append([f"INV-{i:03d}", kind, price, "Raum 2.04"])
    ws.append(["Summe", None, "=SUM(C2:C7)"])
    ws["E2"], ws["E3"] = 0.125, "1.500 €"
    ws["E2"].number_format = "0.0%"
    ws2 = wb.create_sheet("Übersicht")
    ws2.append(["Gerätetyp", "Anzahl", "Gesamtwert je Typ (€)"])
    for row in overview:
        ws2.append(row)
    ws2.append(["Gesamt", "=SUM(B2:B4)", "=SUM(C2:C4)"])
    chart = BarChart()
    chart.add_data(Reference(ws2, min_col=2, min_row=1, max_row=1 + len(overview)), titles_from_data=True)
    ws2.add_chart(chart, "E2")
    wb.save(path)
    return path


GROUPS = [{"name": "Übersicht je Gerätetyp", "source": {"sheet": 1, "group": "typ|kategorie", "value": "preis|wert"},
           "target": {"sheet": "übersicht", "group": "typ|kategorie", "count": "anzahl|stück",
                      "value": "wert|summe|gesamt"}}]


@pytest.fixture(scope="module")
def inventory(folder) -> dict:
    return {"good": _inventory(folder / "gut.xlsx", [["Laptops", 2, 2200], ["Monitor", 3, 600], ["Drucker", 1, 500]]),
            "wrong": _inventory(folder / "falsch.xlsx", [["Laptop", 2, 2000], ["Monitore", 2, 600],
                                                          ["Telefon", 4, 400]])}


# ----------------------------------------------------------------------------------------- forbidden --

def test_forbidden_with_quote_and_location(minutes):
    m = only(defects(minutes, make_task("docx", forbidden={
        "Parkplatz": "parkplatz", "Quellenmarker": r"\[\d+\]", "Kosten zweimal": [{"pattern": "kosten", "min": 2}],
        "Bahnhof": "bahnhof"})), "forbidden")
    assert len(m) == 2 and all(x.hard and x.label == "forbidden content" for x in m)
    assert m[0] == "forbidden content „Parkplatz“: „TOP 3: Parkplatzsituation am Standort Nor…“ (paragraph 3)"
    assert m[1] == "forbidden content „Quellenmarker“: „Laut Satzung [1] ist das zulässig.“ (paragraph 5)"


def test_topics_soft(minutes):
    task = make_task("docx", topics={"Haushalt": "haushalt"}, topics_soft={"Kasse": "kasse", "Satzung": "satzung"})
    m = only(defects(minutes, task), "topics_soft")
    assert [(x.label, x.hard) for x in m] == [("missing topic", False)] and "Kasse" in m[0] and "Satzung" not in m[0]
    assert only(defects(minutes, task), "topics") == []


# ---------------------------------------------------------------------------------- values_present --

def test_values_present_docx(minutes):
    m = only(defects(minutes, make_task("docx", values_present=[1234.56, -200, 45, 78, 999, 12.5, 3])),
             "values_present")
    assert len(m) == 1 and m[0].hard and m[0].label == "missing value"
    assert "2 of 7 required values not in the file: 999; 12,50" in m[0]  # TOP 3: the 3 is there
    many = only(defects(minutes, make_task("docx", values_present=[101, 102, 103, 104, 105, 106])), "values_present")
    assert "6 of 6" in many[0] and "101; 102; 103; 104; 105 …" in many[0]


def test_values_present_pptx_from_chart(slides):
    assert not only(defects(slides, make_task("pptx", values_present=[130, 3.4])), "values_present")
    m = only(defects(slides, make_task("pptx", values_present=[131, 4])), "values_present")  # 'Q4' is no number
    assert "2 of 2 required values not in the file: 131; 4" in m[0]


def test_values_present_xlsx_cell_values_only(inventory):
    task = make_task("xlsx", values_present=[1200, 12.5, 0.125, 1500, 2.04])
    m = only(defects(inventory["good"], task), "values_present")
    # percent cell counts as 0.125 and 12.5, number stored as text counts, a number inside a text cell does not
    assert len(m) == 1 and "1 of 5 required values not in the file: 2,04" in m[0]


def test_values_present_with_alternatives(minutes):
    # the minutes have −200 and 1.234,56: one of the alternatives is enough
    assert not only(defects(minutes, make_task("docx", values_present=[[200, -200], [1234.56]])), "values_present")
    m = only(defects(minutes, make_task("docx", values_present=[[-2.5, 2.5], 45])), "values_present")
    assert len(m) == 1 and m[0].hard and "1 of 2 required values not in the file: -2,50 or 2,50" in m[0]


# --------------------------------------------------------------------------------- charts and notes --

def test_pptx_chart_values(slides):
    good = make_task("pptx", chart_values=[[45, 78, 130, 112], [4500, 7800, 13000, 11200],
                                           [0.1233, 0.2137, 0.3562, 0.3068], [1.2, 3.4, 2.2, 0.8]])
    assert not only(defects(slides, good), "chart_values")
    m = only(defects(slides, make_task("pptx", chart_values=[[45, 78, 150, 112], [45, 78, 130], [112, 130, 78, 45]])),
             "chart_values")
    assert len(m) == 3 and all(x.hard and x.label == "wrong chart values" for x in m)
    assert "45; 78; 150; 112 (most similar series „Teilnehmer“: 45; 78; 130; 112)" in m[0]
    assert "45; 78; 130 (most similar series „Teilnehmer“" in m[1]  # length differs
    assert "112; 130; 78; 45" in m[2]  # categories Q1–Q4 have a fixed order: no reversed or sorted comparison


def test_pptx_chart_series_and_type(slides):
    assert not only(defects(slides, make_task("pptx", chart_series=["teilnehmer", "kosten"], chart_type="column")),
                    "chart_series")
    m = only(defects(slides, make_task("pptx", chart_series=["teilnehmer", "umsatz"], chart_type="line")),
             "chart_series")
    assert len(m) == 2 and all(x.label == "missing chart series" and x.hard for x in m)
    assert "„teilnehmer“ only in a chart of type column (expected line)" in m[0]
    assert "no chart series „umsatz“ (series: „Teilnehmer“ (column), „Kosten (Tsd. €)“ (column))" in m[1]


def test_without_chart_one_defect(folder):
    path = _slides(folder / "ohne.pptx", chart=False)
    m = defects(path, make_task("pptx", chart_values=[[1, 2]], chart_series=["x"]))
    assert [(x.check, str(x)) for x in m if x.check.startswith("chart")] == [("chart", "no chart")]


def test_notes_min(slides):
    m = only(defects(slides, make_task("pptx", notes_min=2)), "notes_min")
    assert len(m) == 1 and m[0].hard and m[0].label == "too few speaker notes" and "only 1 slides" in m[0]
    assert not only(defects(slides, make_task("pptx", notes_min=1)), "notes_min")
    assert check_files([(slides, None)])[slides].metrics["notes"] == 1


def test_xlsx_chart_from_cell_references(inventory):
    """openpyxl writes only the reference ('Übersicht'!$B$2:$B$4): values and name come from the cells."""
    task = make_task("xlsx", chart_values=[[2, 3, 1]], chart_series=["^anzahl$"], chart_type="column")
    assert not [x for x in defects(inventory["good"], task) if x.check.startswith("chart")]
    m = only(defects(inventory["wrong"], task), "chart_values")
    assert "most similar series „Anzahl“: 2; 2; 4" in m[0]


# -------------------------------------------------------------------------------------------- sorted --

def _sales(path: Path, values) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Filialen"
    ws.append(["Filiale", "Umsatz (€)", "Rang"])
    for i, v in enumerate(values, 1):
        ws.append([f"Filiale {i}", v, i])
    ws.append(["Summe", sum(values), None])  # total row: not part of the order
    wb.save(path)
    return path


def test_sorted(folder):
    path = _sales(folder / "ab.xlsx", [500, 400, 400, 100])
    assert not only(defects(path, make_task("xlsx", sorted={"column": "umsatz", "descending": True})), "sorted")
    assert not only(defects(path, make_task("xlsx", sorted={"column": "rang"})), "sorted")
    m = only(defects(path, make_task("xlsx", sorted={"column": "umsatz"})), "sorted")
    assert len(m) == 1 and m[0].hard and m[0].label == "not sorted"
    assert "„Umsatz (€)“ not sorted ascending: Filialen!B3 = 400 after B2 = 500" in m[0]
    soft = only(defects(path, make_task("xlsx", sorted={"column": "gewinn"})), "sorted")
    assert soft[0].severity == "soft" and "not checkable" in soft[0]


# -------------------------------------------------------------------------------------------- groups --

def test_groups_match(inventory):
    assert not only(defects(inventory["good"], make_task("xlsx", groups=GROUPS)), "groups")


def test_groups_differ(inventory):
    m = only(defects(inventory["wrong"], make_task("xlsx", groups=GROUPS)), "groups")
    assert len(m) == 1 and m[0].hard and m[0].label == "summary does not match"
    assert ("summary „Übersicht je Gerätetyp“ does not match Inventar: Laptop: value 2.000 (Übersicht!C2), per "
            "Inventar 2.200; Monitore: count 2 (Übersicht!B3), per Inventar 3; „Drucker“ missing") in m[0]
    count_only = [{**GROUPS[0], "source": {"sheet": 1, "group": "typ"},
                   "target": {"sheet": 2, "group": "typ", "count": "anzahl"}}]
    m = only(defects(inventory["wrong"], make_task("xlsx", groups=count_only)), "groups")
    assert "Laptop:" not in m[0] and "Monitore: count 2" in m[0]


def test_groups_not_checkable(inventory):
    for g in ({**GROUPS[0], "target": {**GROUPS[0]["target"], "sheet": 3}},
              {**GROUPS[0], "target": {**GROUPS[0]["target"], "count": "stückzahl"}}):
        m = only(defects(inventory["good"], make_task("xlsx", groups=[g])), "groups")
        assert len(m) == 1 and m[0].severity == "soft" and "not checkable" in m[0], m


# ------------------------------------------------------------------------------------------ retained --

def test_retained_docx(folder):
    old = _docx(folder / "alt.docx", MINUTES[:4] + [f"Beschluss {i}: Antrag angenommen" for i in range(1, 7)])
    new = _docx(folder / "neu.docx", MINUTES[:2] + ["TOP 3: Parkplatzsituation am Standort Nord (vertagt)",
                                                     "Neuer Punkt: Sommerfest"]
                + [f"Beschluss {i}: Antrag angenommen" for i in range(1, 7)])
    f = check_files([(new, make_task("docx", retained=0.95), old)])[new]
    m = only(f.defects, "retained")
    # 10 units: 'TOP 3 …' changed a little (kept), the cost sentence was dropped
    assert f.metrics["retained"] == "90 %" and len(m) == 1 and m[0].hard and m[0].label == "content not retained"
    assert ("only 90 % of the previous file's content retained (1 of 10 units missing, expected ≥ 95 %), "
            "e.g. „Die Kosten betragen 1.234,56 € und es g…“") in m[0]
    soft = only(defects(new, make_task("docx", retained={"hard": 0.5, "soft": 0.95}), old), "retained")
    assert soft[0].severity == "soft"
    assert not only(defects(new, make_task("docx", retained=0.9), old), "retained")


def test_retained_pptx_and_xlsx(folder, slides):
    more = Presentation(slides)
    more.slides.add_slide(more.slide_layouts[1]).shapes.title.text = "Zusammenfassung"
    more.save(folder / "mehr.pptx")
    f = check_files([(folder / "mehr.pptx", make_task("pptx", retained=1.0), slides)])[folder / "mehr.pptx"]
    assert f.metrics["retained"] == "100 %" and not only(f.defects, "retained")
    # xlsx: an inserted column shifts the formulas; only text and constants count
    old, new = folder / "budget_alt.xlsx", folder / "budget_neu.xlsx"
    for path, column in ((old, False), (new, True)):
        wb = Workbook()
        ws = wb.active
        ws.append(["Monat", "Einnahmen", "Ausgaben"] + (["Sonstiges"] if column else []) + ["Saldo"])
        for i, month in enumerate(["Januar", "Februar", "März"], 2):
            ws.append([month, 3200, 2800] + ([0] if column else []) + [f"=B{i}-C{i}" + (f"-D{i}" if column else "")])
        wb.save(path)
    f = check_one(new, Context(make_task("xlsx", retained=1.0), previous=old), {})
    assert f.metrics["retained"] == "100 %" and not only(f.defects, "retained")


def test_retained_without_previous_file(folder, minutes):
    for previous in (None, folder / "fehlt.docx"):
        m = only(defects(minutes, make_task("docx", retained=0.8), previous), "retained")
        assert len(m) == 1 and m[0].severity == "soft" and "not checkable" in m[0], m


def test_cli_previous(folder, minutes, monkeypatch, capsys):
    task = make_task("docx", retained=0.8)
    monkeypatch.setattr(content, "load_tasks", lambda: {"folge": task})
    new = _docx(folder / "cli.docx", MINUTES[:3])
    content.main([str(new), "--task", "folge", "--previous", str(minutes)])
    out = capsys.readouterr().out
    assert "retained 38 %" in out and "[hard] only 38 % of the previous" in out  # 3 of 8 units left


# ---------------------------------------------------------------------------------- slide structure --

def _comparison(path: Path, layout: str, closing: bool = False) -> Path:
    """Title slide, a slide 'Tun und Lassen' as two text boxes side by side ('columns'), one above the other
    ('stacked'), as a table ('table') or as two slides ('separate'); optionally a closing slide."""
    prs = Presentation()
    width = prs.slide_width
    prs.slides.add_slide(prs.slide_layouts[0]).shapes.title.text = "Phishing erkennen"
    left, right = "Tun: Absender prüfen, Link-Ziel ansehen", "Lassen: Anhänge öffnen, Passwort eingeben"
    if layout == "separate":
        for text in (left, right):
            s = prs.slides.add_slide(prs.slide_layouts[5])
            s.shapes.title.text = text.split(":")[0]
            s.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(3)).text_frame.text = text
    else:
        s = prs.slides.add_slide(prs.slide_layouts[5])
        s.shapes.title.text = "Tun und Lassen"
        if layout == "table":
            t = s.shapes.add_table(3, 2, Inches(1), Inches(2), Inches(8), Inches(2)).table
            for r, (a, b) in enumerate([("Tun", "Lassen"), ("Absender prüfen", "Anhänge öffnen"),
                                        ("Link-Ziel ansehen", "Passwort eingeben")]):
                t.cell(r, 0).text, t.cell(r, 1).text = a, b
        elif layout == "columns":
            s.shapes.add_textbox(Inches(0.5), Inches(2), Emu(int(width * 0.4)), Inches(3)).text_frame.text = left
            s.shapes.add_textbox(Emu(int(width * 0.52)), Inches(2), Emu(int(width * 0.4)),
                                 Inches(3)).text_frame.text = right
            # a page number next to the footer is no second column
            s.shapes.add_textbox(Emu(int(width * 0.9)), Inches(7), Inches(0.5), Inches(0.3)).text_frame.text = "2"
        else:
            s.shapes.add_textbox(Inches(1), Inches(1.5), Inches(8), Inches(1.5)).text_frame.text = left
            s.shapes.add_textbox(Inches(1), Inches(3.5), Inches(8), Inches(1.5)).text_frame.text = right
    summary = prs.slides.add_slide(prs.slide_layouts[1])
    summary.shapes.title.text = "Zusammenfassung und nächste Schritte"
    summary.placeholders[1].text_frame.text = "Verdacht sofort der IT melden"
    if closing:
        prs.slides.add_slide(prs.slide_layouts[0]).shapes.title.text = "Vielen Dank! Fragen?"
    prs.save(path)
    return path


DO_DONT = {"Tun": r"\btun\b", "Lassen": "lassen"}


@pytest.mark.parametrize("layout, ok", [("columns", True), ("table", True), ("stacked", False), ("separate", False)])
def test_side_by_side(folder, layout, ok):
    m = only(defects(_comparison(folder / f"vergleich_{layout}.pptx", layout), make_task("pptx", side_by_side=DO_DONT)),
             "side_by_side")
    assert (not m) == ok, m
    if not ok:
        assert m[0].severity == "soft" and m[0].label == "no side-by-side comparison"
        assert "no slide sets „Tun“ and „Lassen“ side by side in two columns or a table" in m[0]
        assert ("the topics are on slide 2" in m[0]) == (layout == "stacked")


def test_last_slide_topics(folder):
    topics = {"Zusammenfassung": "zusammenfassung|fazit", "Nächste Schritte": "nächste schritte"}
    for closing in (False, True):  # a closing slide 'Vielen Dank! Fragen?' after the summary is skipped
        path = _comparison(folder / f"letzte_{closing}.pptx", "columns", closing)
        assert not only(defects(path, make_task("pptx", last_slide_topics=topics)), "last_slide_topics")
    m = only(defects(_comparison(folder / "letzte.pptx", "separate"), make_task("pptx", last_slide_topics={
        "Zusammenfassung": "zusammenfassung", "Lassen": "lassen"})), "last_slide_topics")
    assert len(m) == 1 and m[0].severity == "soft" and m[0].label == "not on the last slide"
    assert m[0] == "missing on the last slide (slide 4: „Zusammenfassung und nächste Schritte Verdacht sof…“): Lassen"


def test_slides_added(folder):
    old = _comparison(folder / "dazu_alt.pptx", "table")  # 3 slides
    new = _comparison(folder / "dazu_neu.pptx", "table", closing=True)  # 4 slides
    assert not only(defects(new, make_task("pptx", slides_added=1), old), "slides_added")
    assert not only(defects(new, make_task("pptx", slides_added=[0, 2]), old), "slides_added")
    m = only(defects(old, make_task("pptx", slides_added=1), old), "slides_added")
    assert len(m) == 1 and m[0].severity == "soft" and m[0] == "3 slides after 3 in the previous file (+0, expected +1)"
    m = only(defects(new, make_task("pptx", slides_added=1)), "slides_added")
    assert m[0].severity == "soft" and "not checkable" in m[0]


# ------------------------------------------------------------------------------ column_format, workdays --

def _plan(path: Path) -> Path:
    """A project plan with dates, a serial number as end date, a percent column and a text date."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Plan"
    ws.append(["Arbeitspaket", "Start", "Ende", "Fortschritt"])
    rows = [("Planung", datetime(2026, 10, 19), datetime(2026, 10, 30), 0),
            ("Umzugsfirma", datetime(2026, 10, 24), 46330, 0),  # Saturday; 46330 = 05.11.2026 without format
            ("IT", datetime(2026, 12, 28), datetime(2027, 1, 6), 0.5),  # 06.01.2027: Heilige Drei Könige
            ("Packen", "11.01.2027", datetime(2027, 1, 15), 0)]
    for row in rows:
        ws.append(list(row))
    for r in range(2, 6):
        ws.cell(r, 2).number_format = ws.cell(r, 3).number_format = "DD.MM.YYYY"
        ws.cell(r, 4).number_format = "0%" if r != 5 else "General"
    ws.cell(3, 3).number_format = "General"
    wb.save(path)
    return path


def test_column_format(folder):
    path = _plan(folder / "plan.xlsx")
    task = make_task("xlsx", column_format={"start": "date", r"\bende": "date", "fortschritt": "percent",
                                            "kosten": "euro"})
    m = only(defects(path, task), "column_format")
    assert [x.severity for x in m] == ["soft"] * 4
    assert m[0] == "„Start“ not in date format: 1 of 4 values, e.g. Plan!B5 = „11.01.2027“ as text"
    assert m[1] == "„Ende“ not in date format: 1 of 4 values, e.g. Plan!C3 = 46330 (format „General“)"
    assert m[2] == "„Fortschritt“ not in percent format: 1 of 4 values, e.g. Plan!D5 = 0 (format „General“)"
    assert "not checkable: no column „kosten“" in m[3]


def test_workdays(folder):
    path = _plan(folder / "plan_werktage.xlsx")
    m = only(defects(path, make_task("xlsx", workdays=True)), "workdays")
    # the serial number 46330 counts as a date in a column 'Ende'; text dates are not read
    assert len(m) == 1 and m[0].severity == "soft" and m[0].label == "date not on a workday"
    assert m[0] == "1 of 7 dates on a weekend: Plan!B3 = 24.10.2026 (Samstag)"
    m = only(defects(path, make_task("xlsx", workdays="BW")), "workdays")
    assert m[0] == ("2 of 7 dates on a weekend or public holiday: Plan!B3 = 24.10.2026 (Samstag), "
                    "Plan!C4 = 06.01.2027 (Heilige Drei Könige)")


def test_workdays_calendar_and_days_off(folder):
    wb = Workbook()
    ws = wb.active
    ws.append(["Tag", "Mitarbeiter"])
    for i in range(10):  # a day-by-day calendar has weekends by nature
        ws.append([datetime(2026, 12, 21) + timedelta(days=i), "Anna"])
    ws2 = wb.create_sheet("Urlaub")
    ws2.append(["Mitarbeiter", "Urlaub von", "Urlaub bis", "Bemerkung"])
    ws2.append(["Ben", datetime(2026, 12, 26), datetime(2026, 12, 27), "Betriebsurlaub, Feiertage"])
    ws2.append(["Carla", datetime(2027, 2, 1), datetime(2027, 2, 5), ""])
    wb.save(folder / "urlaub.xlsx")
    assert not only(defects(folder / "urlaub.xlsx", make_task("xlsx", workdays="BW")), "workdays")


# ---------------------------------------------------------------------------------- numbers_sourced --

NOTES = """Teamrunde Vertrieb – Mo 12.10.

1) Umsatz Q3
- 1,48 Mio € statt geplant 1,42 Mio, also ca. 4 % über Plan
- Messe: Budget 4.500 €, Stand 24 m²

2) Schulung am Do 22.10., 9–12 Uhr, Raum 2.14
- Rechnung vom 03.09. über 2.380,00 €, Zahlungsziel 30 Tage
- Umsatz Nord 480 und 576, Süd 680 und 663
"""


def test_numbers_sourced_in_content_check(folder):
    turn = Turn(text="Mach mir daraus ein Protokoll.", expect="file",
                attachments=(Attachment(name="Notizen.docx", text=NOTES),))
    task = make_task("docx", numbers_sourced=True, turns=(turn,))
    path = _docx(folder / "belegt.docx", ["Protokoll der Teamrunde vom 12.10.2026", "Budget 4.500 €, Stand 37 m²"])
    f = check_files([(path, task)], today=date(2026, 10, 13))[path]
    assert f.metrics["unsourced_numbers"] == 1 and "„37“ (paragraph 2)" in only(f.defects, "numbers_sourced")[0]


# ------------------------------------------------------------------------------------------ validation --

@pytest.mark.parametrize("file_type, checks", [
    ("docx", {"forbidden": {"x": "("}}),
    ("docx", {"values_present": []}),
    ("docx", {"values_present": [1, "2"]}),
    ("docx", {"values_present": [True]}),
    ("xlsx", {"chart_values": [1, 2]}),
    ("xlsx", {"chart_values": [[]]}),
    ("xlsx", {"chart_series": "sparquote"}),
    ("pptx", {"chart_series": ["("]}),
    ("docx", {"retained": 1.5}),
    ("docx", {"retained": {"medium": 0.5}}),
    ("pptx", {"notes_min": -1}),
    ("docx", {"notes_min": 3}),
    ("docx", {"sorted": {"column": "x"}}),
    ("xlsx", {"sorted": {"column": "("}}),
    ("xlsx", {"sorted": {"column": "x", "descending": "ja"}}),
    ("xlsx", {"sorted": [{"column": "x"}]}),
    ("xlsx", {"groups": {"name": "x"}}),
    ("xlsx", {"groups": [{**GROUPS[0], "target": {"sheet": 2, "group": "typ"}}]}),
    ("xlsx", {"groups": [{**GROUPS[0], "source": {"sheet": 1, "group": "typ"}}]}),
    ("xlsx", {"groups": [{**GROUPS[0], "source": {"sheet": 0, "group": "typ", "value": "preis"}}]}),
    ("xlsx", {"groups": [{**GROUPS[0], "target": {**GROUPS[0]["target"], "color": "rot"}}]}),
    ("docx", {"values_present": [[1, "2"]]}),
    ("docx", {"values_present": [[]]}),
    ("docx", {"side_by_side": {"Tun": "tun"}}),
    ("pptx", {"side_by_side": {}}),
    ("pptx", {"side_by_side": {"Tun": "("}}),
    ("pptx", {"last_slide_topics": ["fazit"]}),
    ("pptx", {"slides_added": "1"}),
    ("pptx", {"slides_added": [2, 1]}),
    ("pptx", {"slides_added": True}),
    ("xlsx", {"column_format": {"ende": "uhrzeit"}}),
    ("xlsx", {"column_format": {"(": "date"}}),
    ("xlsx", {"column_format": {}}),
    ("docx", {"column_format": {"ende": "date"}}),
    ("xlsx", {"workdays": "NRW"}),
    ("docx", {"workdays": True}),
    ("docx", {"numbers_sourced": "ja"}),
])
def test_invalid_checks(file_type, checks):
    with pytest.raises(ValidationError):
        make_task(file_type, **checks)


def test_valid_checks():
    make_task("xlsx", forbidden={"Quellenmarker": r"\[\d+\]",
                                 "Parkplatz": ["parkplatz", {"pattern": "stellpl", "min": 2}]},
              values_present=[45, 7.5, -3], chart_values=[[45, 78], [0.5, 0.5]], chart_series=["sparquote"],
              retained={"hard": 0.5, "soft": 0.8}, sorted={"column": "umsatz", "descending": True}, groups=GROUPS)
    make_task("pptx", notes_min=7, retained=0.8, chart_values=[[1, 2]])
    make_task("xlsx", values_present=[[-2.5, 2.5], 7.5],
              column_format={"quote": "percent", r"\bende": "date", "x": "euro"}, workdays="BW", numbers_sourced=True)
    make_task("pptx", side_by_side=DO_DONT, last_slide_topics={"Fazit": ["fazit", {"pattern": "x", "min": 1}]},
              slides_added=[1, 2], numbers_sourced=False)


def _write(folder: Path, body: str) -> Path:
    task = folder / "x"
    task.mkdir(exist_ok=True)
    (task / "task.toml").write_text('id = "x"\ntitle = "X"\nversion = 1\n' + body, encoding="utf-8")
    return task


def test_reply_forbidden_at_load_time(tmp_path):
    head = 'kind = "file"\nfile_type = "docx"\n[[turns]]\ntext = "Schreib was."\n'
    task = _write(tmp_path, head + "[reply.forbidden]\nQuellenmarker = '\\[\\d+\\]'\n")
    assert load_task(task).spec.reply.forbidden == {"Quellenmarker": r"\[\d+\]"}
    _write(tmp_path, head + "[reply.forbidden]\nKaputt = '('\n")
    with pytest.raises(TaskError, match="invalid regex"):
        load_task(task)


NO_FILE = 'kind = "no_file"\n'


@pytest.mark.parametrize("body, error", [
    ('extra_tools = ["web_search"]\n[[turns]]\ntext = "Such mal."\n[behavior]\ntools_expected = ["web_search"]\n',
     None),
    ('extra_tools = ["web_search", "send_email"]\n[[turns]]\ntext = "Such mal."\n[behavior]\n'
     'tools_forbidden = ["send_email"]\n', None),
    ('extra_tools = ["web_search"]\n[[turns]]\ntext = "x"\n[behavior]\ntools_expected = "web_search"\n',
     "valid list"),
    ('extra_tools = ["web_search"]\n[[turns]]\ntext = "x"\n[behavior]\ntools_expected = ["web_search"]\n'
     'tools_forbidden = ["web_search"]\n', "both expected and forbidden"),
    ('[[turns]]\ntext = "x"\n[behavior]\ntools = ["web_search"]\n', "Extra inputs are not permitted"),
    ('[[turns]]\ntext = "x"\n[reply]\nwords_max = 150\nno_markdown = true\n', None),
    ('[[turns]]\ntext = "x"\n[reply]\nwords_max = "kurz"\n', "valid integer"),
    ('[[turns]]\ntext = "x"\n[reply]\nno_markdown = 1\n', "valid boolean"),
])
def test_behavior_and_reply_at_load_time(tmp_path, body, error):
    task = _write(tmp_path, NO_FILE + body)
    if error is None:
        spec = load_task(task).spec
        assert spec.behavior.tools_expected or spec.behavior.tools_forbidden or spec.reply.words_max
    else:
        with pytest.raises(TaskError, match=error):
            load_task(task)
