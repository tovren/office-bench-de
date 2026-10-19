"""retained: normalised text units and the share of the previous file's units kept in the new one."""

from officebench.checks.retained import compare, units


def test_units_and_compare():
    assert units(["  Parkplatz-Situation:  ", "„Parkplatz–Situation“", "12", "ab", "123", "Ja"]) == {
        "parkplatz-situation": "Parkplatz-Situation:", "123": "123"}
    share, lost, n = compare(["Haushalt 2027 beschließen", "Parkplatzsituation klären", "Kassenbericht"],
                             ["HAUSHALT 2027 beschliessen.", "Kassenbericht", "Neuer Punkt"])
    assert (round(share, 2), lost, n) == (0.67, ["Parkplatzsituation klären"], 3)  # ß/ss: 96 % similar
    assert compare([], ["x"])[0] is None
