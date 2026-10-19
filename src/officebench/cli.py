"""Command line: ``obench <command>``. Run ``obench --help`` for the list of commands."""

import argparse
import json
import sys
from pathlib import Path

from officebench import tasks as task_registry


def _tasks(args) -> int:
    if args.action == "schema":
        print(json.dumps(task_registry.json_schema(), indent=2, ensure_ascii=False))
        return 0
    try:
        selected = task_registry.select(args.select, Path(args.dir))
    except task_registry.TaskError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.action == "list":
        for t in selected:
            s = t.spec
            print(f"{s.id:18} {s.kind:10} {s.file_type or '-':5} {s.difficulty or '-':7} {t.hash}  {s.title}")
    print(f"{len(selected)} tasks valid, selection hash {task_registry.selection_hash(selected)}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="obench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("tasks", help="list or validate tasks, print the task.toml JSON schema")
    p.add_argument("action", choices=["list", "validate", "schema"])
    p.add_argument("--select", default="all", help='"all", ids, "tag:<tag>", "type:<docx|xlsx|pptx>", "kind:<kind>"')
    p.add_argument("--dir", default=str(task_registry.TASKS_DIR), help="tasks folder")
    p.set_defaults(func=_tasks)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
