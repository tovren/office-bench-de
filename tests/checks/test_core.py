"""Core types of the checks: Defect is a str with label/severity/check, Findings sorts defects by severity."""

import pickle

from officebench.checks.core import Defect, Findings


def test_defect_is_str_with_severity():
    m = Defect("formula error", "formula error #REF! in A!B2", "hard", "formula_errors")
    assert m == "formula error #REF! in A!B2" and m.label == "formula error" and m.hard
    copy = pickle.loads(pickle.dumps(m))
    assert (copy, copy.label, copy.severity, copy.check) == (m, m.label, m.severity, m.check)
    assert Defect("x", "y").severity == "hard"  # two-argument form


def test_findings_ok_clean():
    assert Findings([Defect("placeholder", "p", "soft")]).ok
    assert not Findings([Defect("placeholder", "p", "soft")]).clean
    f = Findings([Defect("formula error", "f", "hard"), Defect("placeholder", "p", "soft")])
    assert not f.ok and f.hard == ["f"] and f.soft == ["p"]
