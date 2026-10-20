"""Text checks for every file type: language, model artefacts, placeholders, and the [checks] keys that work on the
whole text (topics, forbidden, names, count, words_min/max, values_present)."""

import bisect
import re

from .arithmetic import format_number, numbers_in_text
from .core import Context, Document
from .registry import SOFT
from .util import normalize

CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]")
# Other scripts that do not belong into a German business document (Cyrillic, Greek is left out: Δ, Σ, α are used).
FOREIGN = {"Cyrillic": "Ѐ-ӿ", "Arabic": "؀-ۿ", "Hebrew": "֐-׿", "Thai": "฀-๿", "Indic": "ऀ-ॿ"}
EN = re.compile(r"\b(the|and|with|for|of|to|is|are|this|that|will|be)\b", re.I)
DE = re.compile(r"\b(der|die|das|und|mit|für|ist|sind|von|zu|den|dem|ein|eine|wird|werden)\b", re.I)
CONTROL_TOKENS = re.compile(r"<\|[^|>]{0,20}\|>|<\|channel\|>|<\|im_(?:start|end)\|>")
MARKDOWN = {
    "**": re.compile(r"\*\*\S"),
    "##": re.compile(r"(?m)^#{1,6}[ \t]+\S"),
    "|---|": re.compile(r"(?m)^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*\|[ \t]*:?-{3,}"),
}
# Windows/UNC paths (\\nas01\backup, C:\neu\daten): their backslash-n is no literal line break.
PATH = re.compile(r"(?:\\\\|\b[A-Za-z]:\\|(?<![\w\\])\\)[\w.$-]{2,}(?:\\[\w.$ -]{2,})+")
# 'Protokollführer: KI-Assistent' – a placeholder for a person (paragraph or label | value in a table row).
AI_ROLE = re.compile(r"^(?:protokoll(?:führer(?:in)?|führung|ant(?:in)?)|erstellt von|verfasser(?:in)?|autor(?:in)?|"
                     r"schriftführer(?:in)?|moderation|leitung)$", re.I)
AI_NAME = re.compile(r"^(?:ein(?:e)?\s+)?(?:KI(?:-?Assistent(?:in)?)?|AI(?:-?Assistant)?|ChatGPT|Chatbot|Sprachmodell|"
                     r"(?:digitaler\s+)?Assistent(?:in)?)\.?$", re.I)
AI_PARAGRAPH = re.compile(r"(?:Protokoll(?:führer(?:in)?|führung)|Erstellt von|Verfasser(?:in)?|Schriftführer(?:in)?)"
                          r"\s*[:–-]\s*"
                          r"(?:ein(?:e)?\s+)?(?:KI(?:-?Assistent(?:in)?)?|AI|ChatGPT|Chatbot|Sprachmodell)\b", re.I)

# Capitalised words that are no first name in front of 'Beispiel' ('Zum Beispiel', 'Ein Beispiel').
_NO_FIRST_NAME = ("Zum|Als|Ein|Eine|Einem|Einen|Einer|Im|Das|Dem|Zur|Kein|Keine|Gutes|Konkretes|Praktisches|Weiteres|"
                  "Folgendes|Anschauliches|Typisches|Letztes|Erstes|Neues")
PLACEHOLDERS = [
    # [Name eintragen], <Datum>, {Firmenname}; not markdown links [Text](url) and not check boxes [ ]
    re.compile(r"[\[<{][^\]\[<>{}\n]{0,40}?(?:name|vorname|nachname|datum|termin|firma|unternehmen|adresse|betrag|"
               r"anzahl|abteilung|ansprechpartner|telefon|e-?mail|kunde|kundin|projekt|produkt|uhrzeit|nummer|"
               r"unterschrift|kontakt|durchwahl|bankverbindung|bankdaten|\biban\b|\bbic\b|\braum\b|gebäude|"
               r"\betage\b|\bpfad\b|\bablage\b|\bz\.\s?b\.|"
               r"einfügen|eintragen|ergänzen|einsetzen|angeben|platzhalter|hier|xx|tbd|ort\b)"
               r"[^\]\[<>{}\n]{0,40}?[\]>}](?!\()", re.I),
    re.compile(r"\((?:bitte\s+)?(?:\w+\s+){0,3}(?:einfügen|eintragen|ergänzen)\)", re.I),
    re.compile(r"\b(?:System|Team|Firma|Projekt|Abteilung|Kunde|Produkt|Tool|Anbieter|Software|Lösung|Plattform|"
               r"Dienstleister|Hersteller|Standort|Unternehmen)\s+(?:X|Y|Z|XY|XYZ)\b"),
    re.compile(rf"\b(?!(?:{_NO_FIRST_NAME})\b)[A-ZÄÖÜ][a-zäöüß]+\s+(?:Mustermann|Musterfrau|Muster|Beispiel)\b"
               r"|\bMuster(?:mann|frau|firma|straße|str\.|stadt|GmbH|AG)\b|\bBeispiel\s?(?:GmbH|AG)\b"
               r"|\bJ(?:ohn|ane) Doe\b|\b[Ll]orem ipsum\b"),
    re.compile(r"\bTT\.MM\.(?:JJJJ|JJ)\b|\bXX\.XX\.(?:XXXX|20\d\d)\b|\b(?:TBD|TODO|t\.b\.d\.)(?!\w)"
               r"|(?<![\w.])N\.\s?N\.(?!\w)|\?{3,}"),
    re.compile(r"(?<![\w.,])X{2,}(?:[.,]X+)?\s?(?:€|EUR\b|Euro\b|%)|(?:€|EUR)\s?X{2,}\b"),
    # 'IT-Desk 0000', 'Tel. 0000 5678': a phone number of zeros only (no German number starts with 0000)
    re.compile(r"\b(?:Durchwahl|Telefon|Tel\.|Hotline|Rufnummer|Fax|Mobil|Nr\.|[\w-]*Desk|telefonisch unter)"
               r"\s*:?\s*0{3,}(?!\d)"),
]
# An empty pair of brackets: a check box at the start of a line ('[ ] Sicherung prüfen'), at its end after the item
# ('Backup gestartet [ ]') or between answer options ('[ ] ja [ ] nein'); a placeholder after a field label or inside
# a sentence ('IBAN [ ] · BIC [ ]', 'um [ ] Tsd. €', 'Kundennummer: [ ]').
EMPTY_BRACKETS = re.compile(r"\[[ \t\u00a0]{0,3}\]")
_BULLET = re.compile(r"^[\s•*·\-–—>\d.)]*$")
_ANSWER = re.compile(r"(?:^|\s)(?:ja|nein|erledigt|offen|ok|teilweise|trifft zu)\s*$", re.I)


def empty_placeholders(paragraph: str) -> list[str]:
    """Empty bracket pairs used as placeholders in one paragraph or cell, each with its neighbouring words."""
    out = []
    for m in EMPTY_BRACKETS.finditer(paragraph):
        line_start = paragraph.rfind("\n", 0, m.start()) + 1
        line_end = paragraph.find("\n", m.end())
        before = paragraph[line_start:m.start()]
        after = paragraph[m.end():line_end if line_end >= 0 else len(paragraph)]
        if _BULLET.match(before) or before.endswith("["):
            continue  # check box at the start of the line
        if EMPTY_BRACKETS.match(before.lstrip(" \t•*-–")) or _ANSWER.search(before):
            continue  # answer options of a check-box line
        if not after.strip() and not before.rstrip().endswith(":"):
            continue  # check box at the end of an item
        word_before = before.split()[-1].lstrip("([{\"„") if before.split() else ""
        word_before = word_before if any(c.isalnum() for c in word_before) else ""
        word_after = after.split()[0] if after.split() and after.split()[0][:1].isalnum() else ""
        out.append(" ".join(x for x in (word_before, m.group(0), word_after) if x))
    return out


def words(text: str) -> int:
    return len(text.split())


def _matches(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, re.I | re.M))


def missing_topics(text: str, topics: dict) -> list[str]:
    """Names of the topics of a `topics` block (docs/task-format.md) that do not occur in the text.

    A topic is a regex or a list of alternatives; an alternative is a regex or {"pattern": regex, "min": n}
    (at least n matches). Case does not matter, dash variants are equal, ^/$ match at every line.
    """
    text = normalize(text)
    missing = []
    for name, value in topics.items():
        alternatives = value if isinstance(value, list) else [value]
        found = False
        for alt in alternatives:
            if isinstance(alt, dict):
                found = _matches(alt["pattern"], text) >= int(alt.get("min", 1))
            else:
                found = re.search(alt, text, re.I | re.M) is not None
            if found:
                break
        if not found:
            missing.append(name)
    return missing


def forbidden_matches(paragraphs, forbidden: dict) -> list[tuple[str, str, str, int]]:
    """Hits of a `forbidden` block (same format and matching as `topics`) in [(where, text)] or a plain text:
    [(name, short quote around the first hit, its location, number of hits)]."""
    if isinstance(paragraphs, str):
        paragraphs = [("", paragraphs)]
    starts, pos = [], 0
    for _, t in paragraphs:
        starts.append(pos)
        pos += len(t) + 1
    text = normalize("\n".join(t for _, t in paragraphs))  # same length: offsets stay valid
    out = []
    for name, value in forbidden.items():
        for alt in value if isinstance(value, list) else [value]:
            pattern, at_least = (alt["pattern"], int(alt.get("min", 1))) if isinstance(alt, dict) else (alt, 1)
            hits = list(re.finditer(pattern, text, re.I | re.M))
            if len(hits) < max(at_least, 1):
                continue
            m = hits[0]
            i = max(0, bisect.bisect_right(starts, m.start()) - 1)
            lo, hi = starts[i], starts[i] + len(paragraphs[i][1])
            a, e = max(lo, m.start() - 25), min(hi, max(m.end(), m.start() + 1) + 25)
            quote = ("…" if a > lo else "") + " ".join(text[a:e].split()) + ("…" if e < hi else "")
            out.append((name, quote, paragraphs[i][0], len(hits)))
            break
    return out


def forbidden_found(text: str, forbidden: dict) -> list[str]:
    """Names of a `forbidden` block that occur in the text (for [reply].forbidden)."""
    return [name for name, *_ in forbidden_matches(text, forbidden)]


def check_forbidden(doc: Document, ctx: Context) -> None:
    """forbidden: every hit is a hard defect (one per name, with a quote and the location)."""
    for name, quote, where, n in forbidden_matches(doc.paragraphs, ctx.checks.get("forbidden") or {}):
        ctx.report("forbidden", f"forbidden content „{name}“: „{quote}“" + (f" ({where})" if where else "")
                   + (f", {n} matches" if n > 1 else ""))


def check_values(doc: Document, ctx: Context) -> None:
    """values_present: every number occurs in the file (xlsx: cell values; docx/pptx: numbers in the text; pptx also
    chart values), tolerance 0.005; an entry that is a list of numbers is met by any of them (−2,5 or 2,5)."""
    wanted = ctx.checks.get("values_present") or []
    present = sorted(doc.numbers if doc.numbers is not None else numbers_in_text(doc.text))

    def there(x) -> bool:
        i = bisect.bisect_left(present, x - 0.005)
        return i < len(present) and present[i] <= x + 0.005

    missing = [x for x in wanted if not any(there(y) for y in (x if isinstance(x, list) else [x]))]
    if missing:
        ctx.report("values_present", f"{len(missing)} of {len(wanted)} required values not in the file: "
                   + "; ".join(" or ".join(format_number(float(y)) for y in (x if isinstance(x, list) else [x]))
                               for x in missing[:5]) + (" …" if len(missing) > 5 else ""))


def _examples(found: list, n: int = 3) -> str:
    """„a“ (where), „b“ (where) … for [(text, where)], each text once."""
    seen, parts = set(), []
    for t, where in found:
        if t in seen:
            continue
        seen.add(t)
        parts.append(f"„{t}“" + (f" ({where})" if where else ""))
    rest = f" and {len(seen) - n} more" if len(seen) > n else ""
    return ", ".join(parts[:n]) + rest


def check_text_general(doc: Document, ctx: Context) -> None:
    """foreign_script, english, control_tokens, literal_newline, markdown, placeholders."""
    text = doc.text
    if ctx.enabled("foreign_script"):
        chars = CJK.findall(text)
        if chars:
            cjk_words = re.findall(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]+", text)
            ctx.report("foreign_script", f"{len(chars)} Chinese/Japanese/Korean characters (e.g. „{cjk_words[0]}“)")
        for name, block in FOREIGN.items():
            hits = re.findall(rf"[{block}]", text)
            if hits:
                word = re.search(rf"\S*[{block}]+\S*", text).group(0)[:30]
                ctx.report("foreign_script", f"{len(hits)} {name} characters (e.g. „{word}“)",
                           label="other foreign script")
    if ctx.enabled("english"):
        en, de = len(EN.findall(text)), len(DE.findall(text))
        if en > 5 and en > de:
            ctx.report("english", f"text mostly English ({en} English vs. {de} German function words)")
    if ctx.enabled("control_tokens") and (m := CONTROL_TOKENS.search(text)):
        ctx.report("control_tokens", f"model control tokens in the text („{m.group(0)}“)")
    if ctx.enabled("literal_newline") and (n := PATH.sub(" ", text).count("\\n")) > 0:
        ctx.report("literal_newline", f"literal \\n in the text ({n}×)")
    if ctx.enabled("markdown"):
        counts = {mark: len(rx.findall(text)) for mark, rx in MARKDOWN.items()}
        if sum(counts.values()):
            kinds = ", ".join(z for z, n in counts.items() if n)
            ctx.report("markdown", f"markdown remnants ({kinds}) in the text ({sum(counts.values())}×)")
    if ctx.enabled("placeholders"):
        found = []
        for where, paragraph in doc.paragraphs:
            spans = []
            for rx in PLACEHOLDERS + [AI_PARAGRAPH]:
                spans += [m.span() for m in rx.finditer(paragraph)]
            # a hit inside another one ('Telefon 0000' in '[Telefon 0000 000-0]') counts once
            found += [(paragraph[a:e].strip(), where) for a, e in spans
                      if not any(a2 <= a and e <= e2 and (a2, e2) != (a, e) for a2, e2 in spans)]
            found += [(t, where) for t in empty_placeholders(paragraph)]
        for table in doc.tables:
            for r, row in enumerate(table.rows, 1):
                cells = [(z or "").strip() for z in row]
                found += [(f"{a} | {b}", f"{table.where}, row {r}") for a, b in zip(cells, cells[1:], strict=False)
                          if AI_ROLE.match(a.rstrip(":")) and AI_NAME.match(b)]
        if found:
            ctx.report("placeholders", f"placeholders instead of content: {_examples(found)}"
                       + (f" ({len(found)}×)" if len(found) > 1 else ""))


def check_text_task(doc: Document, ctx: Context) -> dict:
    """topics, topics_soft, names, count, words_min, words_max; returns metrics."""
    text = doc.text
    p = ctx.checks
    n_words = words(text)
    if "topics" in p and (missing := missing_topics(text, p["topics"])):
        ctx.report("topics", f"points asked for in the prompt not found: {', '.join(missing)}")
    if "topics_soft" in p and (missing := missing_topics(text, p["topics_soft"])):
        ctx.report("topics_soft", f"expected points not found: {', '.join(missing)}")
    if "names" in p:
        missing = [n for n in p["names"] if not re.search(rf"(?<!\w){re.escape(n)}(?!\w)", text)]
        if missing:
            ctx.report("names", f"names asked for are missing in the text: {', '.join(missing)}")
    if "count" in p:
        lines = normalize(text).splitlines()
        for c in p["count"]:
            n = sum(1 for line in lines if re.search(c["pattern"], line, re.I))
            if "min" in c and n < c["min"]:
                ctx.report("count", f"only {n}× „{c['name']}“ found (expected ≥ {c['min']})",
                           label=f"too few {c['name']}")
            if "max" in c and n > c["max"]:
                ctx.report("count", f"{n}× „{c['name']}“ found (expected ≤ {c['max']})", label=f"too many {c['name']}",
                           severity=SOFT)
    if "words_min" in p:  # a number (hard) or {hard = 250, soft = 500}
        levels = p["words_min"] if isinstance(p["words_min"], dict) else {"hard": p["words_min"]}
        if "hard" in levels and n_words < levels["hard"]:
            ctx.report("words_min", f"very short: {n_words} words (expected ≥ {levels.get('soft', levels['hard'])}, "
                                    f"at least {levels['hard']})" if "soft" in levels else
                       f"very short: {n_words} words (expected ≥ {levels['hard']})")
        elif "soft" in levels and n_words < levels["soft"]:
            ctx.report("words_min", f"rather short: {n_words} words (expected ≥ {levels['soft']})",
                       label="rather short", severity=SOFT)
    if "words_max" in p and n_words > p["words_max"]:
        ctx.report("words_max", f"too long: {n_words} words (expected ≤ {p['words_max']})")
    return {"words": n_words}


_HEADER_CELL = re.compile(r"^[^\d\n,;:]{1,30}$")  # short label without digits or lists ('Anna, Ben' is content)


def check_tables_general(doc: Document, ctx: Context) -> None:
    """empty_table: a table with only its header row, or an empty header cell above a column with values."""
    if not ctx.enabled("empty_table"):
        return
    found = []
    for table in doc.tables:
        rows = [[(z or "").strip() for z in row] for row in table.rows if any((z or "").strip() for z in row)]
        if not rows:
            continue
        head, body = rows[0], rows[1:]
        if not body:
            # a single row of short labels is a header without data ('Thema | Beschluss'), not a key-value row
            if len(head) >= 2 and all(_HEADER_CELL.match(z) and len(z.split()) <= 4 for z in head) and table.calc:
                found.append(f"{table.where} has only the header row („{' | '.join(head)[:50]}“)")
            continue
        empty_above_values = [c for c in range(1, len(head)) if not head[c] and any(c < len(z) and z[c] for z in body)]
        if empty_above_values:
            found.append(f"{table.where}: empty header cell above column "
                         f"{', '.join(str(c + 1) for c in empty_above_values)}")
    if found:
        ctx.report("empty_table", "incomplete table: " + "; ".join(found[:3])
                   + (f" and {len(found) - 3} more" if len(found) > 3 else ""))
