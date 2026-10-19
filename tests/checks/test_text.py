"""Text checks on short texts: foreign script, placeholders, markdown and other model artefacts, empty tables, topic
matching, forbidden content and the two-level words_min."""

from datetime import date
from pathlib import Path

import pytest

from officebench.checks.core import Context, Document, Table
from officebench.checks.text import (
    check_forbidden,
    check_tables_general,
    check_text_general,
    check_text_task,
    forbidden_found,
    missing_topics,
)
from officebench.tasks import Checks, Task, TaskSpec, TurnSpec


def make_task(file_type: str | None = "docx", dates_from: date | None = None, **checks) -> Task:
    """A task with these [checks] (validated like a task file)."""
    spec = TaskSpec(id="test", title="Test", version=1, kind="file" if file_type else "no_file", file_type=file_type,
                    turns=[TurnSpec(text="Test")], dates_from=dates_from, checks=Checks(**checks))
    return Task(spec=spec, turns=(), path=Path("."), hash="")


def text_defects(paragraphs, tables=(), **checks) -> list:
    """Defects of the general text and table checks for paragraphs [(where, text)] or strings."""
    ctx = Context(make_task(None, **checks) if checks else None)
    doc = Document([(f"Absatz {i}", a) if isinstance(a, str) else a for i, a in enumerate(paragraphs, 1)],
                   list(tables))
    check_text_general(doc, ctx)
    check_tables_general(doc, ctx)
    return ctx.defects


def only(defects, check: str) -> list:
    return [m for m in defects if m.check == check]


def test_missing_topics_semantics():
    topics = {"Zeitplan": "zeitplan|meilenstein",
              "To-do": ["to-?do", {"pattern": r"^\s*(Anna|Ben)\s*[:-]", "min": 2}], "Ist-Zustand": "ist-zustand"}
    assert missing_topics("ZEITPLAN\nTodo: x\nIst–Zustand", topics) == []  # case, en dash
    assert missing_topics("Meilenstein\nAnna: a\nBen – b", topics) == ["Ist-Zustand"]
    assert missing_topics("Anna: nur eine Zeile", topics) == ["Zeitplan", "To-do", "Ist-Zustand"]


@pytest.mark.parametrize("topics", [
    {"Ziele": "ziel(?!gruppe)"}, {"Anmeldung": "anmeld|meldet (euch|sie sich|ihr)"},
])
def test_relaxed_patterns(topics):
    texts = {"Ziele": ["Zielsetzung", "Kernziele des Projekts", "Projektziele"],
             "Anmeldung": ["Bitte meldet euch bis Freitag an"]}
    for name, pattern in topics.items():
        for t in texts[name]:
            assert not missing_topics(t, {name: pattern}), t
    assert missing_topics("Zielgruppe sind alle Mitarbeitenden", {"Ziele": "ziel(?!gruppe)"}) == ["Ziele"]


# ----------------------------------------------------------------------------------------- language --

@pytest.mark.parametrize("text, expected", [
    ("Die Rolle eine直观e Anbindung", "foreign script"),
    ("Absprache единоAnna gestern", "other foreign script"),
    ("Δ Vorjahr und Σ Kosten", None),  # Greek letters are used in German business texts
])
def test_foreign_script(text, expected):
    labels = [m.label for m in only(text_defects([text]), "foreign_script")]
    assert labels == ([expected] if expected else [])
    assert all(m.hard for m in only(text_defects([text]), "foreign_script"))


@pytest.mark.parametrize("text, hit", [
    ("Protokoll: [Name eintragen]", "[Name eintragen]"),
    ("Konzept für [Firmenname]", "[Firmenname]"),
    ("Pilotphase mit Team X starten", "Team X"),
    ("Einführung von System X im Dezember", "System X"),
    ("Ansprechpartner: Max Mustermann", "Max Mustermann"),
    ("Mitarbeiterin Anna Beispiel", "Anna Beispiel"),
    ("Termin: TT.MM.JJJJ", "TT.MM.JJJJ"),
    ("Budget: XX €", "XX €"),
    ("Verantwortlich: TBD", "TBD"),
    ("Kosten (bitte ergänzen)", "(bitte ergänzen)"),
    ("Euer Betriebsrat [Unterschrift]", "[Unterschrift]"),
    ("Rückfragen: [Kontaktdaten]", "[Kontaktdaten]"),
    ("auf unser Konto (IBAN [ ] · BIC [ ])", "IBAN [ ]"),
    ("Budgeterhöhung um [ ] Tsd. €", "um [ ] Tsd."),
    ("Kundennummer: [ ]", "Kundennummer: [ ]"),
    ("Meldeadresse security@firma.de | IT-Desk 0000", "IT-Desk 0000"),
    ("Personalabteilung (Tel. 0000 1234)", "Tel. 0000"),
])
def test_placeholders(text, hit):
    m = only(text_defects([text]), "placeholders")
    assert len(m) == 1 and hit in m[0] and m[0].severity == "soft"


@pytest.mark.parametrize("text", [
    "Zum Beispiel Jira oder Zendesk", "Siehe [Projektplan](https://example.org)", "[ ] Sicherung prüfen",
    "Anbieter A ist günstiger als Anbieter B", "Größe XXL", "Windows 11 und Office 365", "Ziel: 4,2/5 Punkte",
    "Backup gestartet [ ]", "1. [ ] Protokoll gelesen\n[ ] Passwort geändert", "Teilnahme: ja [ ] nein [ ]",
    "Rechnungs-Nr. 0001234", "Quelle [1]",
])
def test_no_placeholder(text):
    assert not only(text_defects([text]), "placeholders")


def test_ai_assistant_as_minute_taker():
    assert "KI-Assistent" in only(text_defects(["Protokollführer: KI-Assistent"]), "placeholders")[0]
    table = Table("Tabelle 1", [["Datum", "12.10.2026"], ["Protokollführung", "KI-Assistent"]])
    assert "Protokollführung | KI-Assistent" in only(text_defects([], [table]), "placeholders")[0]
    assert not only(text_defects(["Der KI-Assistent hilft bei Routineaufgaben.", "Protokollführung: Anna"]),
                    "placeholders")


def test_markdown_control_tokens_literal_newline_english():
    m = text_defects(["**Fett** am Anfang", "## Überschrift", "a\\nb", "<|channel|>",
                      "This is the plan and it will be done for the team with the tools to be used"])
    checks = {x.check: x for x in m}
    assert "**" in checks["markdown"] and "##" in checks["markdown"]
    assert checks["literal_newline"].hard and checks["control_tokens"].hard
    assert checks["english"].severity == "soft"


@pytest.mark.parametrize("text, n", [
    (r"Ziel: \\nas01\backup\monatlich", 0), (r"Ablage unter \nas01\backup\logs ablegen", 0), (r"C:\neu\daten", 0),
    (r"Zeile 1\nZeile 2", 1), (r"a\n\nb", 1),
])
def test_literal_newline_not_in_paths(text, n):
    assert len(only(text_defects([text]), "literal_newline")) == n


def test_disable_switches_general_check_off():
    # the old test also switched off weekday (dates.py); here only the text part
    ctx = Context(make_task(None, disable=["placeholders", "weekday"]))
    check_text_general(Document([("Absatz 1", "System X am Dienstag, 12.10.2026")]), ctx)
    assert ctx.defects == []


# ------------------------------------------------------------------------------------------- tables --

def test_empty_table():
    empty = Table("Tabelle 1", [["Thema", "Beschluss"]])
    kv = Table("Tabelle 2", [["Ort", "Raum 2.04"]])  # one key-value row is no empty table
    head = Table("Folie 4, Tabelle", [["Phase", "Monat", ""], ["Pilot", "1", "Vertrieb"]])
    corner = Table("Tabelle 3", [["", "Jahr 1", "Jahr 2"], ["Lizenz", "1.000", "1.000"]])  # empty corner is fine
    m = only(text_defects([], [empty, kv, head, corner]), "empty_table")
    assert len(m) == 1 and "Tabelle 1 has only the header row" in m[0] and "column 3" in m[0]
    assert "Tabelle 3" not in m[0]


# ------------------------------------------------------------------------------------- task checks --

@pytest.mark.parametrize("n_words, expected", [(100, ("hard", "very short")), (300, ("soft", "rather short")),
                                               (600, None)])
def test_words_min_two_levels(n_words, expected):
    ctx = Context(make_task("docx", words_min={"hard": 250, "soft": 500}))
    check_text_task(Document([("A", "Wort " * n_words)]), ctx)
    assert [(m.severity, m.label) for m in ctx.defects] == ([expected] if expected else [])


def test_forbidden_match_count_and_dashes():
    ctx = Context(make_task(None, forbidden={"Kick-off": "kick-off"}))
    check_forbidden(Document([("Absatz 1", "Kick–off am Montag"), ("Absatz 2", "zweites Kick‐off")]), ctx)
    assert len(ctx.defects) == 1 and "2 matches" in ctx.defects[0] and "(Absatz 1)" in ctx.defects[0]
    assert forbidden_found("Siehe Quelle [2].", {"Quellenmarker": r"\[\d+\]", "Parkplatz": "parkplatz"}) == [
        "Quellenmarker"]
    long = "Einleitung. " * 10 + "Die Parkplatzsituation bleibt angespannt, " + "weiter im Text. " * 10
    ctx = Context(make_task(None, forbidden={"Parkplatz": "parkplatz"}))
    check_forbidden(Document([("Folie 2", long)]), ctx)
    assert "„…leitung. Einleitung. Die Parkplatzsituation bleibt angespan…“ (Folie 2)" in ctx.defects[0]
