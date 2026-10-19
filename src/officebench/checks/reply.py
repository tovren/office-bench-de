"""Checks of the final answer ([reply] words_max, no_markdown) and of the behaviour in the log ([behavior]
tools_expected, tools_forbidden); used by the result evaluation, not by the file check. topics/forbidden of [reply]
are in text.py (missing_topics, forbidden_found).

Both take the task's section as a pydantic model (task.spec.reply, task.spec.behavior) or as the plain dict of its
set keys, which is what the checks below read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .core import Defect
from .registry import BEHAVIOR_CHECKS, REPLY_CHECKS
from .text import MARKDOWN, words

if TYPE_CHECKING:
    from ..tasks import Behavior, Reply


def _data(section) -> dict:
    return section.model_dump(exclude_none=True) if hasattr(section, "model_dump") else section


def reply_defects(text: str, reply: Reply | dict) -> list[Defect]:
    """words_max: more words than allowed (soft); no_markdown: **bold**, ## heading or a table separator in an
    answer the user pastes elsewhere, e.g. into Outlook (soft: in the chat it is rendered, and copying the rendered
    text keeps the formatting; only the copy button gives the raw asterisks)."""
    reply = _data(reply)
    out = []
    if "words_max" in reply and (n := words(text)) > reply["words_max"]:
        label, severity = REPLY_CHECKS["words_max"]
        out.append(Defect(label, f"reply too long: {n} words (expected ≤ {reply['words_max']})", severity,
                          "words_max"))
    if reply.get("no_markdown"):
        counts = {mark: len(rx.findall(text)) for mark, rx in MARKDOWN.items()}
        if sum(counts.values()):
            label, severity = REPLY_CHECKS["no_markdown"]
            kinds = ", ".join(z for z, n in counts.items() if n)
            out.append(Defect(label, f"markdown in the reply ({kinds}, {sum(counts.values())}×), ends up as literal "
                                     f"characters when copied", severity, "no_markdown"))
    return out


def check_behavior(called: list, behavior: Behavior | dict) -> tuple[list, list, list[Defect]]:
    """(expected tools not called, unwanted tools called, defects) from the decoy tools called in the log."""
    behavior = _data(behavior)
    missing = [t for t in behavior.get("tools_expected", []) if t not in called]
    unwanted = [t for t in behavior.get("tools_forbidden", []) if t in called]
    defects = []
    if missing:
        label, severity = BEHAVIOR_CHECKS["tools_expected"]
        defects.append(Defect(label, f"expected tool not called: {', '.join(missing)}", severity, "tools_expected"))
    if unwanted:
        label, severity = BEHAVIOR_CHECKS["tools_forbidden"]
        defects.append(Defect(label, f"unwanted tool called: {', '.join(unwanted)}", severity, "tools_forbidden"))
    return missing, unwanted, defects
