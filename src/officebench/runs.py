"""The run folder runs/<run>/<model>/: names and readers shared by the harness that writes it and the scorer, the
report and the judge that read it (layout and log format: docs/harness.md).

    meta.json   model config, profile, hashes, task selection    read_meta(folder)
    log.jsonl   one line per finished task run; the last counts  read_log(path) -> {(task, rep): record}
    files/      <task>-<rep>__r<round>c<index>__<name>           file_prefix(…), FILE_NAME, delivered_files(folder)

model_folders(paths) finds the model folders among model and run folders; read_jsonl(path) reads any JSON lines file
(results.jsonl, grades).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

LOG_FORMAT = 1
MAX_LOGGED_TEXT = 4000  # texts in the log are cut to this length
OUTAGE = {"provider", "network"}  # error kinds the model cannot help; server errors count against the model setup
FILE_NAME = re.compile(r"^(?P<task>[a-z][a-z0-9_]*)-(?P<rep>\d+)__r(?P<round>\d+)c(?P<index>\d+)__(?P<name>.+)$")
OFFICE_SUFFIXES = (".docx", ".xlsx", ".pptx")


def file_prefix(task: str, rep: int, round_no: int, index: int) -> str:
    """Prefix of the files of one tool call; the round counts across turns, so the highest (round, index) is the
    file the user ends up with."""
    return f"{task}-{rep}__r{round_no}c{index}__"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def read_log(path: Path) -> dict[tuple[str, int], dict]:
    """Last log line per (task, rep) ({} before the first one): a rerun (--retry-failed) appends a new line."""
    return {(rec["task"], rec["rep"]): rec for rec in read_jsonl(path)} if Path(path).exists() else {}


def read_meta(folder: Path) -> dict:
    return json.loads((Path(folder) / "meta.json").read_text(encoding="utf-8"))


def model_folders(paths) -> list[Path]:
    """Model folders (with meta.json) among the paths: each path is a model folder or a run folder holding them."""
    out = []
    for p in map(Path, paths):
        found = [p] if (p / "meta.json").is_file() else sorted(
            q for q in p.iterdir() if (q / "meta.json").is_file()) if p.is_dir() else []
        if not found:
            raise FileNotFoundError(f"{p}: neither a model folder (meta.json) nor a run folder with model folders")
        out += found
    return list(dict.fromkeys(out))


def delivered_files(folder: Path) -> dict[tuple[str, int], Path]:
    """Per (task, rep) the office file the user ended up with: the highest (round, index) in files/."""
    best: dict[tuple[str, int], tuple] = {}
    files = Path(folder) / "files"
    for p in files.iterdir() if files.is_dir() else []:
        m = FILE_NAME.match(p.name)
        if m and p.suffix.lower() in OFFICE_SUFFIXES:
            key, rank = (m["task"], int(m["rep"])), (int(m["round"]), int(m["index"]))
            if key not in best or rank > best[key][0]:
                best[key] = (rank, p)
    return {k: p for k, (_, p) in best.items()}
