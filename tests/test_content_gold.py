"""Gold tests: the content check against the second blind review (qualitaet-2, 80 files of the run of 13./14.10.2026).
Every expectation quotes the reviewer's report (qualitaet-2/gutachten/<task>.md); letters -> files via
qualitaet-2/zuordnung.json. Only objective findings are expected here, not the reviewers' judgement of content.

The review and the model files are private and not part of the repository: set OBENCH_GOLD_DIR to the folder of the
old benchmark (with bewertungen/qualitaet-2/zuordnung.json and testlauf/rohdaten/); without it the tests skip."""

import json
import os
import re
from pathlib import Path

import pytest

from officebench.checks.content import check_files

pytestmark = pytest.mark.slow

ROOT = Path(os.environ["OBENCH_GOLD_DIR"]) if os.environ.get("OBENCH_GOLD_DIR") else None
MAPPING = ROOT / "bewertungen" / "qualitaet-2" / "zuordnung.json" if ROOT else None
RAW = ROOT / "testlauf" / "rohdaten" if ROOT else None
BUILT = re.compile(r"^(?P<tag>[a-z][a-z0-9_]*-\d+)__r(?P<round>\d+)c(?P<index>\d+)__.+\.(docx|xlsx|pptx)$")


def _require_data():
    if MAPPING is None or not MAPPING.exists():
        pytest.skip("gold data missing (set OBENCH_GOLD_DIR to the old benchmark folder)")


def delivered_files(folder: Path) -> dict[str, Path]:
    """The file the user ends up with per task run (<id>-<n>): the last one the tool built (highest round, then
    call)."""
    runs: dict[str, list] = {}
    for path in folder.iterdir() if folder.is_dir() else []:
        if m := BUILT.match(path.name):
            runs.setdefault(m["tag"], []).append((int(m["round"]), int(m["index"]), path))
    return {tag: sorted(files)[-1][2] for tag, files in runs.items()}


@pytest.fixture(scope="module")
def findings() -> dict:
    _require_data()
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    entries = {(t, letter): RAW / e["lauf"] / e["datei"] for t, d in mapping.items() for letter, e in d.items()}
    result = check_files([(p, t) for (t, _), p in entries.items()])
    return {k: result[p] for k, p in entries.items()}


# (task, letter, check, severity, text in the defect, quote from the report)
EXPECTED = [
    ("angebot", "M", "formula_as_text", "hard", "=C2*D2",
     "E2:E6 und E8 enthalten die **Formeln als Text** („=C2\\*D2“, „=SUM(E2:E6)“, im Bild sichtbar)."),
    ("angebot", "M", "sheets_min", "hard", "second sheet", "**Das zweite Blatt fehlt.**"),
    ("angebot", "A", "total_row", "hard", "total row", "Die **Netto-Summe fehlt ganz** (richtig wären 15.740 €)."),
    ("angebot", "H", "total_row", "hard", "total row", "aber es gibt **keine Netto-Summe** (wäre 9.600 €)."),
    ("angebot", "N", "total_row", "hard", "total row", "aber es gibt **keine Netto-Summe** (wäre 13.640 €)"),
    ("angebot", "O", "total_row", "hard", "total row", "und es gibt **keine Netto-Summe** (wäre 22.750 €)."),
    ("angebot", "P", "total_row", "hard", "total row", "aber es gibt **keine Netto-Summe** (wäre 11.670 €)"),
    ("angebot", "O", "empty_table", "soft", "empty header cell above column 4", "Spalte D hat **keine Überschrift**"),
    ("angebot", "H", "placeholders", "soft", "Max Mustermann",
     "Blatt 2 nutzt Platzhalternamen („Max Mustermann“, „Anna Beispiel“, „Peter Tech“)"),
    ("angebot", "B", "sum_range", "soft", "AVERAGE",
     "Auf Blatt 2 steht in B7 „Summe“, die Zelle rechnet aber `=AVERAGE(B2:B6)` → 107 €. Das ist irreführend."),
    ("angebot", "L", "sum_range", "soft", "AVERAGE",
     "Auf Blatt 2 heißt C7 „Summe“, rechnet aber `=AVERAGE(C2:C6)` → 95 €."),
    ("budget", "C", "formula_as_text", "hard", '"=SUM(B3:B4)"',
     "Alle Formeln sind als Text mit Anführungszeichen gespeichert (`\"=SUM(B3:B4)\"`, `\"=B5-B14\"`), nichts wird "
     "berechnet."),
    ("budget", "I", "formula_as_text", "hard", "B4:G4", "In B4:G4 steht der Text `=B2-B3`, keine Formel"),
    ("budget", "I", "calculations", "hard", "H4 = 0, expected 4.550",
     "Deshalb zeigt H4 `=SUM(B4:G4)` den Wert 0 statt 4.550."),
    ("budget", "I", "chart", "hard", "no chart", "Es gibt kein Diagramm und kein €-Format."),
    ("budget", "B", "formulas_min", "hard", "no formula",
     "Aber alle Gesamt- und Saldozellen sind feste Zahlen ohne eine einzige Formel."),
    ("budget", "B", "chart", "hard", "no chart", "Es fehlen die Halbjahressumme (…) und das Diagramm."),
    ("budget", "F", "calculations", "soft", "D8", "Aber D8 ist leer, die Saldo-Summe von 3.100 fehlt."),
    ("budget", "H", "calculations", "soft", "B8, C8", "B8 und C8 sind aber leer, es fehlen 17.400 und 13.900."),
    ("budget", "L", "calculations", "soft", "B8, C8", "B8 und C8 sind leer, es fehlen 19.550 und 14.880."),
    ("budget", "N", "calculations", "soft", "B8, C8", "B8 und C8 sind leer, es fehlen 19.350 und 16.791,85."),
    ("konzept", "A", "toc", "hard", "table of contents", "Das geforderte Inhaltsverzeichnis fehlt."),
    ("konzept", "I", "topics", "hard", "Anforderungen, Zeitplan, Kosten, Risiken",
     "Bricht nach der Ausgangslage ab. Ziele, Anforderungen, Zeitplan, Kosten und Risiken fehlen"),
    ("konzept", "B", "topics", "hard", "Risiken", "Das Kapitel Risiken fehlt komplett."),
    ("konzept", "E", "text_arithmetic", "soft", "gives 816",
     "Rechenfehler: 0,2 PT × 48 × 85 € = 816 €, nicht 4.080 €."),
    ("konzept", "M", "text_arithmetic", "soft", "137.350",
     "Die Obergrenze ist falsch addiert: 137.350 € statt der angegebenen 127.350 €."),
    ("konzept", "P", "text_arithmetic", "soft", "gives 4.800",
     "Rechnung: 2,5 FTE-Monate × 1.920 € = 4.800 €, nicht 14.400 €."),
    ("konzept", "P", "foreign_script", "hard", "类似", "Sprache: chinesische Zeichen („oder 类似“)"),
    ("konzept", "P", "past_dates", "soft", "KW 19/2026",
     "Zeitplan: Start in KW 19/2026, also fünf Monate in der Vergangenheit"),
    ("konzept", "N", "calendar_week", "soft", "KW 1-6 (Dezember 2026 - Januar 2027)",
     "Falsche Kalenderwochen: „KW 1–6 (Dezember 2026 – Januar 2027)“, KW 49–53 fehlen."),
    ("protokoll", "A", "weekday", "hard", "Dienstag, 26. Oktober 2026",
     "Termine: „Dienstag, 26. Oktober 2026“ ist ein Montag."),
    ("protokoll", "L", "weekday", "hard", "Dienstag, 26. Oktober", "„Dienstag, 26. Oktober“ ist ein Montag."),
    ("protokoll", "O", "weekday", "hard", "Mittwoch, 03. November 2026",
     "Der Kopf nennt „Dienstag, 12. Oktober 2026“, der Fuß „Mittwoch, 03. November“ – beides falsche Wochentage."),
    ("protokoll", "O", "weekday", "hard", "Dienstag, 12. Oktober 2026",
     "O nennt sogar die Sitzung selbst einen Dienstag."),
    ("protokoll", "O", "foreign_script", "hard", "единоAnna", "Kyrillisches Fragment „единоAnna“."),
    ("protokoll", "K", "foreign_script", "hard", "直观", "Chinesisches Einsprengsel „eine直观e Anbindung“."),
    ("protokoll", "H", "placeholders", "soft", "[Name eintragen]", "Platzhalter „[Name eintragen]“."),
    ("protokoll", "J", "placeholders", "soft", "[Termin eintragen]",
     "Zwei Platzhalter („[Name eintragen]“, „[Termin eintragen]“)."),
    ("protokoll", "G", "placeholders", "soft", "Team X", "Platzhalter „Pilotphase mit Team X starten“"),
    ("protokoll", "N", "placeholders", "soft", "System X", "Platzhalter „Einführung von System X im Dezember“."),
    ("protokoll", "E", "topics", "hard", "To-do-Liste",
     "Die To-do-Liste fehlt ganz, damit gibt es keine Verantwortlichen."),
    ("protokoll", "P", "empty_table", "soft", "only the header row",
     "Die Beschlusstabelle ist leer, es gibt nur die Kopfzeile."),
    ("praesentation", "L", "foreign_script", "hard", "季度",
     "in der Tabelle auf F4 stehen chinesische Zeichen („季度-Reviews“)"),
    ("praesentation", "E", "empty_table", "soft", "empty header cell",
     "Die Tabelle auf F4 hat eine leere vierte Kopfzelle"),
]


@pytest.mark.parametrize("task, letter, check, severity, text, quote", EXPECTED,
                         ids=[f"{t}-{b}-{c}" for t, b, c, *_ in EXPECTED])
def test_finding_as_in_review(findings, task, letter, check, severity, text, quote):
    defects = [m for m in findings[(task, letter)].defects if m.check == check and m.severity == severity]
    assert any(text in m for m in defects), (quote, [str(m) for m in findings[(task, letter)].defects])


# Files the reviewers found free of the objective mistakes the check looks for.
CLEAN = [
    ("budget", b, "„Korrekt“ / „Alles korrekt“ – Note 5,0 (Gutachten Budget, Rangfolge 1.–7.: „Sie sind fehlerfrei "
                  "und erfüllen die Aufgabe vollständig.“)") for b in "ADGJKOP"
]


@pytest.mark.parametrize("task, letter, quote", CLEAN, ids=[f"{t}-{b}" for t, b, _ in CLEAN])
def test_clean_files(findings, task, letter, quote):
    f = findings[(task, letter)]
    assert f.clean, (quote, [str(m) for m in f.defects])


NO_FINDING = [
    ("konzept", "C", "text_arithmetic",
     "Alle Rechnungen stimmen (80 × 8 € × 12 = 7.680 €; Summen 15.000 €/10.080 €)"),
    ("konzept", "H", "text_arithmetic",
     "Alle Zahlen sind korrekt (19.470 €, 43.470 €, 5.060/9.060 €, Gesamtkosten über 3 Jahre 70.650 €)."),
    ("konzept", "G", "text_arithmetic", "Gesamtsumme 76.810 € korrekt"),
    ("konzept", "K", "text_arithmetic", "Agentenlizenzen 8 × 29 €, Summe über 3 Jahre 43.732 € korrekt"),
    ("konzept", "K", "calendar_week", "34 Wochen (KW 42/2026–KW 22/2027) stimmen"),
    ("protokoll", "H", "weekday",
     "Der Wochentag stimmt („Montag, 12. Oktober 2026“), alle Fristen sind Freitage."),
    ("protokoll", "J", "weekday", "Sauber, der Wochentag stimmt („Montag, 12.10.2026“)"),
    ("angebot", "J", "calculations", "F2:F6 = C×E und F7 → 37.750 € sind richtig."),
    ("angebot", "D", "calculations", "G2:G6 = D×F und G7 → 32.900 € sind richtig."),
]


@pytest.mark.parametrize("task, letter, check, quote", NO_FINDING, ids=[f"{t}-{b}-{c}" for t, b, c, _ in NO_FINDING])
def test_no_false_alarm(findings, task, letter, check, quote):
    defects = [str(m) for m in findings[(task, letter)].defects if m.check == check]
    assert not defects, (quote, defects)


def test_best_offers_without_hard_defects(findings):
    # "1. J (4,8) 2. I (4,6) 3. D (4,4) 4. F (4,4) 5. C (4,4)" – no hard defect in the five best offers
    for b in "JIDFC":
        assert findings[("angebot", b)].ok, (b, [str(m) for m in findings[("angebot", b)].defects])


def test_all_files_readable(findings):
    assert not [k for k, f in findings.items()
                if any(m.check in ("unreadable", "not_recalculated") for m in f.defects)]


def test_two_full_runs_without_crash():
    _require_data()
    entries = [(p, None) for run in ("g-qwen27b", "g-gemma26b-lokal") for p in delivered_files(RAW / run).values()]
    found = check_files(entries)
    assert len(found) == len(entries) > 60
    assert not [p for p, f in found.items() if any(m.check == "unreadable" for m in f.defects)]
