"""Checks of the final answer ([reply]) and of the tool calls ([behavior])."""

from officebench.checks.reply import check_behavior, reply_defects
from officebench.tasks import Behavior, Reply


def test_reply_and_behavior_defects():
    text = "**Betreff:** Wartung\n\n## Hallo zusammen\n\nam Freitag ab 14 Uhr …"
    m = reply_defects(text, {"words_max": 5, "no_markdown": True})
    assert [(x.label, x.severity) for x in m] == [("reply too long", "soft"), ("markdown in reply", "soft")]
    assert m[0] == "reply too long: 11 words (expected ≤ 5)" and "(**, ##, 2×)" in m[1]
    assert reply_defects("Betreff: Wartung", {"words_max": 5, "no_markdown": True}) == []
    missing, unwanted, m = check_behavior(["email_senden"], {"tools_expected": ["websuche"],
                                                             "tools_forbidden": ["email_senden", "kalender_eintrag"]})
    assert (missing, unwanted) == (["websuche"], ["email_senden"]) and all(x.hard for x in m)
    assert [str(x) for x in m] == ["expected tool not called: websuche", "unwanted tool called: email_senden"]
    assert check_behavior(["websuche"], {"tools_expected": ["websuche"]})[:2] == ([], [])


def test_task_sections_as_models():
    assert reply_defects("eins zwei drei", Reply(words_max=2)) == ["reply too long: 3 words (expected ≤ 2)"]
    assert reply_defects("**fett**", Reply()) == []
    assert check_behavior([], Behavior(tools_expected=["websuche"]))[0] == ["websuche"]
