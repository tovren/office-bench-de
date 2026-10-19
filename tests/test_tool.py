"""The vendored tool, its frozen specs and the execution of calls."""

import asyncio
import inspect
import json

from officebench import tool
from officebench.tool import office_documents as od


def test_specs_match_the_tool_code():
    methods = {n for n, f in inspect.getmembers(od.Tools, inspect.iscoroutinefunction) if not n.startswith("_")}
    assert set(tool.FUNCTIONS) == methods
    for spec in tool.SPECS:
        fn = spec["function"]
        method = getattr(od.Tools, fn["name"])
        params = [p for p in inspect.signature(method).parameters if p != "self" and not p.startswith("__")]
        assert list(fn["parameters"]["properties"]) == params, fn["name"]
        first_line = inspect.getdoc(method).splitlines()[0]
        assert first_line in fn["description"], fn["name"]


def test_execute_builds_a_file():
    args = {"title": "Test", "sheets": [{"name": "A", "columns": [{"header": "x", "type": "number"}],
                                         "rows": [[1], [2]]}]}
    r = tool.build("create_excel_file", args)
    assert r.done and r.status == "ok" and r.files[0].name == "Test.xlsx" and r.files[0].data[:2] == b"PK"


def test_execute_errors_go_back_to_the_model():
    run = asyncio.run
    assert run(tool.execute("create_word_file", "{nope")).status == "parse_error"
    assert run(tool.execute("create_word_file", "[1, 2]")).status == "not_object"
    assert run(tool.execute("make_file", "{}")).status == "unknown_function"
    r = run(tool.execute("create_word_file", json.dumps({"blocks": "kein Array", "extra": 1})))
    assert r.status == "ok" and not r.done and r.dropped == ["extra"]  # the tool itself rejects invalid blocks


def test_python_literal_arguments_are_accepted():
    r = asyncio.run(tool.execute("create_word_file", "{'title': 'T', 'blocks': [{'type': 'paragraph', 'text': 'x'}]}"))
    assert r.done


def test_extra_tool_returns_canned_answer():
    extras = {"send_email": {"spec": {"function": {"name": "send_email", "parameters": {"properties": {"to": {}}}}},
                             "result": "Gesendet."}}
    r = asyncio.run(tool.execute("send_email", json.dumps({"to": "a", "cc": "b"}), extras))
    assert r.status == "extra_tool" and r.content == "Gesendet." and r.dropped == ["cc"]
