"""text_arithmetic on short texts and Word/slide tables: German number readings, amount cells, calculations in
running text, products in table rows and total rows."""

import pytest

from officebench.checks.arithmetic import (
    amount,
    check_text_arithmetic,
    expressions,
    number_values,
    numbers_in_text,
    spaced_numbers,
    table_sums,
)
from officebench.checks.core import Context, Document, Table


def arithmetic_defects(paragraphs, tables=()) -> list:
    """Defects of text_arithmetic for paragraph strings and tables (no task: every general check is on)."""
    ctx = Context()
    check_text_arithmetic(Document([(f"Absatz {i}", a) for i, a in enumerate(paragraphs, 1)], list(tables)), ctx)
    return [m for m in ctx.defects if m.check == "text_arithmetic"]


@pytest.mark.parametrize("s, values", [
    ("7.680", [7680.0]), ("1.234,56", [1234.56]), ("0,2", [0.2]), ("7,680", [7.68, 7680.0]), ("1,500.25", [1500.25]),
    ("12.10.2026", []), ("1.2.3", []),
])
def test_number_values_german(s, values):
    assert number_values(s) == values


def test_numbers_in_text():
    assert numbers_in_text("1.234,56 € und −200 €, 15-30 Plätze, 45,78,130") == [1234.56, -200, 15, 30, 45, 78, 130]
    assert numbers_in_text("am 12.10.2026, Version 1.2.3, KW42") == []


def test_spaced_numbers():
    assert spaced_numbers("143 200 €, 1\u202f736,5 und Q3 2026") == [143200, 1736.5]
    assert spaced_numbers("Top 5 Kunden, 12 Monate, 2025 380") == []
    assert numbers_in_text("7,680") == [7.68, 7680]


def test_amount_cells():
    assert amount("23.000 – 39.000") == (23000, 39000)
    assert amount("30.000 bis 72.000") == (30000, 72000)
    assert amount("ca. 43.700 EUR") == (43700, 43700)
    assert amount("9.750 (intern)") == (9750, 9750)
    assert amount("–") == (0, 0) and amount("pauschal") is None


@pytest.mark.parametrize("text", [
    "Alle Mitarbeiter: 80 × 8 € × 12 = 7.860 €", "18.500 − 15.150 = 3.450", "15.000 € + 10.080 € = 26.080 €",
    "17.700 € × 10 % = 1.700 €", "4 × 8,5 Stunden + 5,25 Stunden = 39 Stunden",
    "4 × 8,5 Stunden + 5,25 Stunden = 39,75 Stunden",
])
def test_wrong_calculation_in_text(text):
    m = arithmetic_defects([text])
    assert len(m) == 1 and m[0].severity == "soft"


@pytest.mark.parametrize("text", [
    "80 × 8 € × 12 = 7.680 €", "18.500 − 15.150 = 3.350", "3 × 33,33 € = 100 €", "10 T€ + 5 T€ = 15.000 €",
    "15–30 € × 5–10 Agenten × 12 = 900–3.600 €", "1 = gering, 3 = hoch", "Score >= 4,2/5", "Tel. +49 30 1234-5678",
    "ca. 160 h × 55 € ≈ 9.000 €", "Version 1.2.3 = neu", "Termin 10:00 - 11:00 = 1 Stunde",
    "4 × 8,5 Stunden + 5,25 Stunden = 39,25 Stunden", "40 h / 6 = 6,67 h", "3 × 1.199,99 € = 3.600 €",
])
def test_right_or_no_calculation_in_text(text):
    assert not arithmetic_defects([text])


def test_calculation_in_table_row():
    tab = Table("Tabelle 7", [["Position", "Berechnung", "Betrag (€)"],
                              ["Wartung", "0,2 PT/Woche × 48 × 85 EUR", "4.080"],
                              ["Lizenzen", "8 × 65 EUR/Monat × 12", "6.240"],
                              ["Software", "80 Nutzer à 8 € pro Monat", "7.680"],  # monthly rate, yearly amount
                              ["Schulung", "2 × 90 Min.", "1.500"]])  # no currency in the product
    m = arithmetic_defects([], [tab])
    assert len(m) == 1 and "gives 816" in m[0] and "Tabelle 7, row 2" in m[0] and "Lizenzen" not in m[0]


def test_total_row_in_word_table():
    right = Table("Tabelle 1", [["Position", "Einmalig (€)", "Jährlich (€)"], ["Lizenz", "0", "7.680"],
                                ["Einrichtung", "12.000", "–"], ["Schulung", "3.000", "–"],
                                ["Gesamt", "15.000", "7.680"]])
    span = Table("Tabelle 2", [["Kostenart", "Schätzung (EUR)"], ["Lizenzen", "30.000 bis 72.000"],
                               ["Einrichtung", "24.000 bis 32.000"], ["Reserve", "4.300 bis 5.600"],
                               ["Gesamtkosten", "58.300 bis 109.600"]])
    cumulative = Table("Tabelle 3", [["Position", "Betrag (€)"], ["Beratung", "7.200 €"], ["Integration", "3.600 €"],
                                     ["Zwischensumme", "10.800 €"], ["Reserve (10 %)", "1.080 €"],
                                     ["Summe einmalig", "11.880 €"]])
    text = Table("Tabelle 4", [["Kriterium", "Variante A"], ["Einstieg", "niedrig"], ["Betrieb", "minimal"],
                               ["Gesamtkosten 3 Jahre", "ca. 43.700 EUR"]])
    subtotal = Table("Tabelle 6", [["Position", "Betrag"], ["Einmalig: Geräte", "6.900,00 €"],
                                   ["Monatlich: Service", "79,00 €"], ["Monatlich: Seiten", "48,00 €"],
                                   ["Monatlich: Farbe", "82,50 €"], ["Monatliche Kosten gesamt", "209,50 €"]])
    count = Table("Tabelle 7", [["Position", "Kosten"], ["Lizenz", "500 €"], ["SW-Seiten (288.000 gesamt)", "1.728 €"],
                                ["Farbe", "2.970 €"], ["Gesamtkosten", "5.198 €"]])
    assert not arithmetic_defects([], [right, span, cumulative, text, subtotal, count])
    at_end = Table("Tabelle 8", [["Posten", "Tsd. €"], ["Transporter", "180"], ["Regale", "95"], ["Software", "80"],
                                 ["Investitionsbudget gesamt", "420"]])
    assert "„Investitionsbudget gesamt“ = 420" in arithmetic_defects([], [at_end])[0]
    wrong = Table("Tabelle 5", [["Kostenart", "Schätzung (EUR)"], ["Lizenzen", "30.000 bis 72.000"],
                                ["Einrichtung", "24.000 bis 32.000"], ["Gesamtkosten", "54.000 bis 94.000"]])
    m = arithmetic_defects([], [wrong])
    assert len(m) == 1 and "54.000–104.000" in m[0]


def test_expression_with_units():
    a = expressions("Lizenzen: 10 Bearbeiter × 30 € × 12 Monate = 3.600 €")[0]
    assert a.ops == ["×", "×"] and a.rhs == (3600.0,) and a.results() == [3600.0] and a.currency


def test_empty_tables_do_not_crash():
    assert table_sums(Table("T", [[], ["a"], [], ["Summe", "1"]])) == []
    check_text_arithmetic(Document([], [Table("T", [[], [], [], [], ["Gesamt"]])]), Context())
