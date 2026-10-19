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


def _run(args) -> int:
    from officebench.config import load_model, load_profile
    from officebench.harness.client import ConfigError
    from officebench.harness.runner import run_sync

    profile = load_profile(args.profile)
    tasks = task_registry.select(args.tasks)
    repeats = args.repeats
    if args.probe:
        tasks, repeats = tasks[:2], 1
    for path in args.model:
        model = load_model(path)
        try:
            folder = run_sync(model, profile, tasks, repeats, Path(args.out), retry_failed=args.retry_failed,
                              progress=lambda m: print(m, flush=True))
        except ConfigError as e:
            print(f"error: {model.name}: {e}", file=sys.stderr)
            return 2
        print(f"{model.name}: done, see {folder}")
    return 0


def _check(args) -> int:
    from officebench.checks.content import main as check_main

    return check_main(args.rest)


def _score(args) -> int:
    from officebench.scoring import main as score_main

    try:
        return score_main(args.folders)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _report(args) -> int:
    from officebench.report import main as report_main

    try:
        return report_main(args.folders, args.compare, args.grades, args.rescore)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _judge(args) -> int:
    import asyncio

    from officebench.config import load_model
    from officebench.judge import grade

    if args.import_dir:
        r = grade.import_grades(Path(args.import_dir), Path(args.out), args.judge_name)
        print(f"imported {r['imported']}, missing {len(r['missing'])}, invalid {len(r['invalid'])}: "
              f"{', '.join(r['missing'] + r['invalid'])[:500]}")
        return 0 if not r["invalid"] else 1
    folders = []
    for f in map(Path, args.runs):
        folders += [f] if (f / "meta.json").exists() else sorted(p.parent for p in f.glob("*/meta.json"))
    items = grade.select_items(folders, args.samples)
    if args.export:
        r = grade.export_items(items, Path(args.export), args.package_size)
        print(f"exported {r['items']} items in {r['packages']} packages to {args.export}")
        return 0
    if not args.judge:
        print("error: give --judge CONFIG, --export DIR or --import DIR", file=sys.stderr)
        return 2
    progress = lambda m: print(m, flush=True)  # noqa: E731
    asyncio.run(grade.judge_items(items, load_model(args.judge), Path(args.out), progress=progress))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="obench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("tasks", help="list or validate tasks, print the task.toml JSON schema")
    p.add_argument("action", choices=["list", "validate", "schema"])
    p.add_argument("--select", default="all", help='"all", ids, "tag:<tag>", "type:<docx|xlsx|pptx>", "kind:<kind>"')
    p.add_argument("--dir", default=str(task_registry.TASKS_DIR), help="tasks folder")
    p.set_defaults(func=_tasks)

    p = sub.add_parser("run", help="run tasks against one or more models")
    p.add_argument("model", nargs="+", help="model config(s), e.g. configs/models/qwen3.8-27b-medium.toml")
    p.add_argument("--tasks", default="all", help="task selection (see `obench tasks list --help`)")
    p.add_argument("--repeats", type=int, default=3, help="runs per task (default 3)")
    p.add_argument("--profile", default="default", help="profile name or path (default: configs/profiles/default)")
    p.add_argument("--out", default="runs/latest", help="run folder; one subfolder per model (default runs/latest)")
    p.add_argument("--probe", action="store_true", help="quick probe: the first 2 selected tasks, 1 run each")
    p.add_argument("--retry-failed", action="store_true", help="rerun task runs that ended in a provider/network error")
    p.set_defaults(func=_run)

    p = sub.add_parser("check", help="content check of files (see `obench check -- --help`)", add_help=False)
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p.set_defaults(func=_check)

    p = sub.add_parser("score", help="score runs: write results.jsonl into every model folder")
    p.add_argument("folders", nargs="+", help="model folder(s) runs/<run>/<model> or run folder(s) holding them")
    p.set_defaults(func=_score)

    p = sub.add_parser("report", help="Markdown report of scored runs (stdout)")
    p.add_argument("folders", nargs="+", help="model folder(s) or run folder(s); scored first if needed")
    p.add_argument("--compare", nargs=2, metavar=("A", "B"), help="paired comparison of two models (names as shown)")
    p.add_argument("--grades", nargs="+", type=Path, help="JSONL file(s) with judge grades")
    p.add_argument("--rescore", action="store_true", help="score again even if results.jsonl is up to date")
    p.set_defaults(func=_report)

    p = sub.add_parser("judge", help="grade delivered files with an LLM judge (API, or export/import for agents)")
    p.add_argument("runs", nargs="*", help="run folders (a model folder or a folder with model subfolders)")
    p.add_argument("--judge", help="judge config, e.g. configs/judges/claude-sonnet-5.5.toml")
    p.add_argument("--samples", type=int, default=2, help="graded runs per model and task (default 2)")
    p.add_argument("--out", default="grades.jsonl", help="grades file (appended; default grades.jsonl)")
    p.add_argument("--export", help="write the prompts for agent graders to this folder instead of calling an API")
    p.add_argument("--package-size", type=int, default=8, help="items per agent package (with --export)")
    p.add_argument("--import", dest="import_dir", help="read agent grades from an export folder")
    p.add_argument("--judge-name", default="agent", help="judge name for imported grades")
    p.set_defaults(func=_judge)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
