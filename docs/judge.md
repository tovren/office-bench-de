# Quality judge

The content check (docs/scoring.md) decides whether a file does what the task asks. It cannot tell whether the German
reads well, whether a plan makes sense or how much rework a file needs. For that, a judge grades the delivered files
blind on five criteria.

## What the judge sees

Per model and task the judge grades the first runs that delivered something (default: two). For each it gets:

- the user's message(s) as the model got them, the full text of attached files and the reference date,
- what was expected (a Word/Excel/PowerPoint file, the last file of a conversation, or a chat answer),
- the task's checklist: concrete points that make a 5 (`[judge] checklist` in task.toml, German),
- the five criteria with anchor descriptions for 1, 3 and 5 (`src/officebench/judge/criteria.toml`),
- the file as Markdown text (Excel with row and column headers, formulas and the results recalculated by LibreOffice)
  and images of up to 12 rendered pages, or the final chat answer for tasks without a file.

Files are copied with neutral timestamps before rendering, and nothing in the request names the model. Each file is
graded in its own request, so a grade does not depend on the other files. The prompt is in
`src/officebench/judge/grade.py`.

| Criterion | Question |
|---|---|
| Language | Is the German correct, natural and in a fitting tone? |
| Content and calculations | Is what it says correct: numbers, formulas, dates, weekdays, logic, plausibility? |
| Completeness | Is everything there that the task asks for? |
| Structure and form | Outline, formatting, layout: is it easy to read and to work on? |
| Usefulness | How much rework does it need before it can be used in a company? |

A file's grade is the mean of the five criteria.

## Two ways to run it

**Through an API** (any OpenAI-compatible endpoint with vision):

```sh
obench judge runs/my-run --judge configs/judges/claude-sonnet-5.5.toml --out runs/my-run/grades.jsonl
obench report runs/my-run --grades runs/my-run/grades.jsonl
```

**By agent sessions** (e.g. Claude Code subagents), which can also check calculations and dates with small scripts:

```sh
obench judge runs/my-run --export runs/my-run/judging        # material/<id>/prompt.md, page images, packages/*.md
# one agent per package: "Read runs/my-run/judging/packages/P001.md and do what it says."
obench judge --import runs/my-run/judging --judge-name claude-opus-5.5-agent --out runs/my-run/grades.jsonl
```

The export uses the same prompt as the API judge. Items get neutral ids; the mapping to models is in `mapping.json`,
which the agents are told not to open.

## Calibration

Grades from different judges are not interchangeable: they differ in strictness, and a mean of 4.2 from one judge is
not a 4.2 from another. Compare models only with grades from the same judge.

Before the first results, API judges were compared with 40 files that Claude Opus 5.5 agent sessions had graded with
the same criteria in an earlier version of this benchmark (spread over 29 tasks and grades 2.2 to 5.0):

| Judge (API, reasoning high) | Pearson r with Opus agents | Mean abs. difference | Bias | Cost per file |
|---|---:|---:|---:|---:|
| Claude Sonnet 5.5 | 0.89 | 0.25 | +0.12 | $0.026 |
| Gemini 3 Flash | 0.69 | 0.78 | +0.78 | $0.013 |

For scale: files that the Opus agents graded twice (in different packages) differ by 0.35 on average. Sonnet 5.5 is a
good stand-in for the agent grades; Gemini 3 Flash is too lenient. Per criterion, Sonnet agrees least on "structure"
(r = 0.55) and most on content and completeness (r = 0.82–0.83).

## Noise

A single grade is noisy: earlier rounds showed a spread of about ±0.2 per file between two gradings of the same file,
and about half of the variance between runs of one task comes from the files themselves (the same model writes a
better or worse file each time). Differences between models are therefore reported with confidence intervals from a
bootstrap over tasks, and as paired differences over the same tasks (docs/scoring.md).
