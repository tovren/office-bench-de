"""The office tool the models use, and how a tool call is executed.

office_documents.py is the Open WebUI tool "Office Documents" (https://github.com/tovren/open-webui-plugins, MIT),
version 0.3.0, copied unchanged from commit c90f89f. The model only fills in a JSON schema; fixed code builds the
file. Here it runs without Open WebUI: the file is captured instead of being attached to a chat. specs.json holds the
tool specs exactly as Open WebUI 0.11.4 generates them from the method signatures and docstrings
(open_webui.utils.tools.get_tool_specs, so the models see the same tool as in Open WebUI); tests/test_tool.py checks
that they still match the code.

Execution of a call (execute):
- arguments: JSON text; if that fails, a Python literal (some models write single quotes); anything else, or a
  value that is not an object, is sent back as an error the model can react to
- parameters that are not in the spec are dropped (and logged), like Open WebUI does
- the result text of the tool goes back to the model unchanged; "Done: …" means a file was built
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import office_documents as _tool

HERE = Path(__file__).resolve().parent
SOURCE_COMMIT = "c90f89f"
SPECS: list[dict] = json.loads((HERE / "specs.json").read_text(encoding="utf-8"))
FUNCTIONS = tuple(s["function"]["name"] for s in SPECS)
FILE_TYPES = {"create_word_file": "docx", "create_excel_file": "xlsx", "create_powerpoint_file": "pptx"}
VALVES = {"language": "de"}  # German texts inside the files (total row, page footer) and decimal comma

PARSE_ERROR = ("Error: the arguments of `{name}` could not be parsed. The model generated malformed or incomplete "
               "JSON. Please try again.")
NOT_OBJECT = "Error: the arguments of `{name}` must be a JSON object. Please try again."
NOT_FOUND = 'Error: tool "{name}" not found.'


def tool_hash() -> str:
    """Short hash of the tool code and specs (written into every run)."""
    h = hashlib.sha256((HERE / "office_documents.py").read_bytes() + (HERE / "specs.json").read_bytes())
    return h.hexdigest()[:12]


@dataclass
class BuiltFile:
    name: str
    data: bytes
    text: str  # the file's content as Markdown, as the tool describes it


@dataclass
class CallResult:
    content: str  # the text that goes back to the model
    status: str  # ok | parse_error | not_object | unknown_function | exception | extra_tool
    params: dict = field(default_factory=dict)
    dropped: list = field(default_factory=list)  # parameters not in the spec
    files: list[BuiltFile] = field(default_factory=list)

    @property
    def done(self) -> bool:
        return self.content.startswith("Done")


class _CapturingTools(_tool.Tools):
    """The tool with delivery replaced: the built file is kept in memory and reported as attached."""

    def __init__(self, valves: dict) -> None:
        super().__init__()
        self.valves = self.Valves(**{**VALVES, **valves})
        self.files: list[BuiltFile] = []

    async def _deliver(self, data: bytes, filename: str, mime: str, ctx: Any, text: str = "") -> str:
        self.files.append(BuiltFile(filename, data, text))
        return _tool.RESULT_ATTACHED


def parse_arguments(raw: Any) -> dict | None:
    """Arguments as a dict; None if they cannot be parsed; ValueError if they are not an object."""
    if raw is not None and not isinstance(raw, str):
        raw = json.dumps(raw)
    params: Any = {}
    if raw and raw.strip():
        try:
            params = json.loads(raw)
        except ValueError:
            try:
                params = ast.literal_eval(raw)
            except (ValueError, SyntaxError, MemoryError, RecursionError, TypeError):
                return None
    if not isinstance(params, dict):
        raise ValueError("arguments must be an object")
    return params


async def execute(name: str, raw_arguments: Any, extra_tools: dict[str, dict] | None = None,
                  valves: dict | None = None) -> CallResult:
    """Run one tool call. extra_tools: {name: {"spec", "result"}} of the task (canned answers)."""
    try:
        params = parse_arguments(raw_arguments)
    except ValueError:
        return CallResult(NOT_OBJECT.format(name=name), "not_object")
    if params is None:
        return CallResult(PARSE_ERROR.format(name=name), "parse_error")
    extra_tools = extra_tools or {}
    if name in extra_tools:
        allowed = extra_tools[name]["spec"]["function"].get("parameters", {}).get("properties", {})
        dropped = [k for k in params if k not in allowed]
        return CallResult(str(extra_tools[name]["result"]), "extra_tool", params, dropped)
    if name not in FUNCTIONS:
        return CallResult(NOT_FOUND.format(name=name), "unknown_function", params)
    spec = next(s["function"] for s in SPECS if s["function"]["name"] == name)
    allowed = spec.get("parameters", {}).get("properties", {})
    dropped = [k for k in params if k not in allowed]
    tools = _CapturingTools(valves or {})
    try:
        result = await getattr(tools, name)(**{k: v for k, v in params.items() if k in allowed})
    except Exception as e:  # noqa: BLE001 - the model gets the error, like in Open WebUI
        return CallResult(json.dumps({"error": str(e)}, ensure_ascii=False), "exception", params, dropped)
    return CallResult(str(result), "ok", params, dropped, tools.files)


def build(name: str, arguments: dict, valves: dict | None = None) -> CallResult:
    """Synchronous helper for tests and references: run a call with already parsed arguments."""
    import asyncio

    return asyncio.run(execute(name, json.dumps(arguments, ensure_ascii=False), valves=valves))
