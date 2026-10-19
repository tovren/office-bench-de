"""numbers_sourced: numbers, times and dates of a file that are neither in the prompt and attachments nor simply
derived from them. The notes below stand for a typical attachment; designed on synthetic files, the reference
solutions and runs of development tasks only (never on test tasks)."""

from datetime import date
from pathlib import Path

from officebench.checks.core import Context, Document, Table
from officebench.checks.sources import Source, check_numbers_sourced, readings, source_texts, unsourced
from officebench.tasks import Attachment, Checks, Task, TaskSpec, Turn, TurnSpec

NOTES = """Teamrunde Vertrieb – Mo 12.10.

1) Umsatz Q3
- 1,48 Mio € statt geplant 1,42 Mio, also ca. 4 % über Plan
- Messe: Budget 4.500 €, Stand 24 m²

2) Schulung am Do 22.10., 9–12 Uhr, Raum 2.14
- Rechnung vom 03.09. über 2.380,00 €, Zahlungsziel 30 Tage
- Umsatz Nord 480 und 576, Süd 680 und 663
"""


def sourced_task(text: str = "Mach mir daraus ein Protokoll.", attachment: str = NOTES,
                 file_type: str = "docx") -> Task:
    """A task with numbers_sourced = true whose only turn has the notes as attachment."""
    spec = TaskSpec(id="test", title="Test", version=1, kind="file", file_type=file_type,
                    turns=[TurnSpec(text=text)], checks=Checks(numbers_sourced=True))
    turn = Turn(text=text, expect="file", attachments=(Attachment(name="Notizen.docx", text=attachment),))
    return Task(spec=spec, turns=(turn,), path=Path("."), hash="")


def unsourced_texts(paragraphs, tables=(), constants=None, **kw) -> list[str]:
    q = Source(source_texts(sourced_task(**kw)), date(2026, 10, 13))
    doc = Document([(f"Absatz {i}", t) for i, t in enumerate(paragraphs, 1)], list(tables), constants=constants)
    return [f.text for f in unsourced(doc, q)]


def test_readings():
    assert readings("1.480.000") == [(1480000.0, 0)] and readings("2.380,00") == [(2380.0, 2)]
    assert readings("7,680") == [(7.68, 3), (7680.0, 0)] and readings("1,48") == [(1.48, 2)]
    assert readings("12.10.2026") == []


def test_copies_and_derivations():
    assert unsourced_texts([
        "Umsatz Q3: 1,48 Mio. € (Plan: 1,42 Mio. €), also 60.000 € oder 4,2 % über Plan.",  # pair in the source
        "Umsatz 1.480.000 €, rund 1,5 Mio.",  # copy in another unit; rounded at the written precision
        "Messebudget 4.500 €, Standfläche 24 m², Raum 2.14, 9:00–12:00 Uhr.",
        "Nord: 480 → 576 (+96 Tsd. €, +20 %), Süd: 680 → 663 (−17, −2,5 %).",  # derived in the same paragraph
        "Gesamt 1.160 → 1.239 Tsd. €; im Monat 375 €, also 4.500 € im Jahr.",  # sums; 4.500 / 12
        "Teamrunde am Montag, 12.10.2026; Schulung Do, 22.10.2026; Frist Fr, 16.10.; Fälligkeit 03.10.2026.",
        "Seit 2023, Folie 3 von 8, KW 43, Top-10-Kunden.",  # years, small numbers, calendar weeks
    ]) == []


def test_invented():
    found = unsourced_texts([
        "Beginn 14:30 Uhr, Ende 16:00 Uhr.",  # times not in the notes
        "Tel. 0711 98765, Budget 5.200 €.",
        "Nächste Teamrunde am 18.11.2026.",  # neither in the notes nor near the reference date
        "Lieferzeit 4,9 Tage.",
    ])
    assert found == ["14:30 Uhr", "16:00 Uhr", "0711", "98765", "5.200", "18.11.2026", "4,9"], found


def test_table_and_xlsx():
    rows = [["Position", "Betrag"], ["Rechnung 1", "2.380,00 €"], ["Rechnung 2", "1.190,00 €"],
            ["Summe", "3.570,00 €"]]
    tab = Table("Tabelle 1", rows)
    paragraphs = [(f"Tabelle 1, Zeile {r}", " ".join(z)) for r, z in enumerate(rows, 1)]
    q = Source(("Rechnungen über 2.380,00 € und 1.190,00 €.",), date(2026, 10, 13))
    assert unsourced(Document(paragraphs, [tab]), q) == []  # the total is the sum of the column
    # xlsx constants: a row 'Laptop | 6 | 1.149 | 6.894' derives the product from its own row
    q = Source(("6 Laptops", "Laptop 1.149 €, Rabatt 5 %"), date(2026, 10, 13))
    constants = [("Angebot!B2", 6.0, False), ("Angebot!C2", 1149.0, False), ("Angebot!D2", 6894.0, False),
                 ("Angebot!D3", 344.7, False), ("Angebot!D4", 0.05, True), ("Angebot!D5", 777.0, False)]
    assert [f.text for f in unsourced(Document([], [], constants=constants), q)] == ["777"]


def test_defect_and_metric():
    task = sourced_task()
    ctx = Context(task, date(2026, 10, 13))
    metrics = check_numbers_sourced(
        Document([("Absatz 1", "Budget 4.500 €, Beginn 14:30 Uhr"), ("Absatz 2", "14:30 Uhr")]), ctx)
    assert metrics == {"unsourced_numbers": 1} and len(ctx.defects) == 1
    m = ctx.defects[0]
    assert m.severity == "soft" and m.label == "number without source"
    assert m == "1 numbers or dates without a source in prompt or attachment: „14:30 Uhr“ (Absatz 1)"
    ctx = Context(task, date(2026, 10, 13))
    assert check_numbers_sourced(Document([("Absatz 1", "Budget 4.500 €")]), ctx) == {"unsourced_numbers": 0}
    assert not ctx.defects
