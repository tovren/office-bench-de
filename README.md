# office-bench-de

How well do language models write German office documents through a tool call? 50 everyday office tasks in
German (offers, minutes, budgets, rotas, slides from a report, letters, follow-up changes), each answered by the
model with a Word, Excel or PowerPoint file built by the
[Office Documents](https://github.com/tovren/open-webui-plugins) tool for Open WebUI, or with a plain chat answer.

Every delivered file goes through a deterministic content check (Excel files are recalculated by LibreOffice first)
and, separately, a blind quality review on five criteria. Everything is public: tasks, reference solutions, checks,
run logs and grades.

## Results v0.2

50 tasks × 3 runs per model, run on 22 October 2026 through the Vercel AI Gateway, with Office Documents 0.3.0 as
the tool (v0.1: 0.1.0).

| Model | Success | pass^3 | Content ok | Cost of 150 runs | Success v0.1 |
|---|---:|---:|---:|---:|---:|
| Claude Haiku 5.5 (thinking medium) | 96 % (91–99) | 90 % | 96 % | $0.65 | 91 % |
| DeepSeek V4 Flash (thinking high) | 91 % (84–97) | 82 % | 92 % | $0.16 | 87 % |
| Qwen3.8-Flash (thinking medium) | 88 % (80–95) | 74 % | 88 % | $0.47 | 83 % |
| Nemotron 3.5 Super VL (thinking on) | 86 % (77–93) | 74 % | 85 % | $0.59 | 85 % |
| Qwen3.8-27B (thinking medium) | 79 % (69–87) | 56 % | 79 % | $0.30 | 84 % |
| Gemma 4 31B | 62 % (49–74) | 54 % | 58 % | $0.33 | 62 % |
| gpt-oss-120b (reasoning medium) | 60 % (49–71) | 36 % | 60 % | $0.45 | 66 % |

- **Success**: the run delivered what the task asks for (the file, every follow-up turn, no hard defect in the
  content check, reply and behavior checks where the task has them). 95 % intervals from a bootstrap over tasks.
- **pass^3**: chance that three fresh runs of a task all succeed: how reliable a model is, not just how good.
- **Content ok**: file tasks only (43 of 50): the delivered file has no hard defect.
- **Cost**: as reported by the gateway, for all 150 runs; prices depend on the provider.
- **Success v0.1**: the same tasks and checks with Office Documents 0.1.0 ([results/v0.1](results/v0.1/README.md)).

There is no blind quality review for v0.2. The quality grades of v0.1 (Claude Opus 5.5 agent sessions, 696 files)
are in [results/v0.1/README.md](results/v0.1/README.md): Haiku 4.30, DeepSeek 4.27, Nemotron 4.00,
Qwen3.8-Flash 3.92, Qwen3.8-27B 3.91, Gemma 3.63, gpt-oss-120b 3.57 (1–5).

Full report with per-task results, defects, tool errors and rejections:
[results/v0.2/report.md](results/v0.2/report.md).

### What stands out

- **The percent trap is gone.** Office Documents 0.3.0 says in its spec that a percent cell holds the fraction and
  sends back `/100` on a percent cell and `*100` in a percent column. In `anfrage` 10 of 21 runs now get the net
  and gross totals right (v0.1: 2 of 21); only 3 calls in the whole run were sent back for a percent error, so the
  models mostly follow the spec sentence.
- **The next trap: formulas in the rows of a formula column.** A column with a formula (`=C{row}*E{row}`) fills
  every row with it, and the tool drops what the model sends in that column without a word, including formulas
  like `=SUM(F2:F6)` in a total row below the items. Netto, MwSt and Brutto then show 0. This decides 15 failed
  runs (`preisaenderung` 6, `anfrage` 4, `bueromaterial` 4, `angebot` 1; 7 of them gpt-oss-120b, 3 Haiku) and
  happened about as often in v0.1. See [docs/open-issues.md](docs/open-issues.md).
- **The ranking is stable; most changes against v0.1 are run-to-run noise.** Paired by task, every model's
  change has a 95 % interval that includes zero or touches it (Qwen3.8-Flash +5 points, 0 to +11). Haiku leads,
  DeepSeek follows at a quarter of the cost, Qwen3.8-Flash, Nemotron and Qwen3.8-27B overlap, Gemma and gpt-oss
  are clearly behind.
- **Calling the tool is not the problem.** Every model ends with a file in 93–100 % of the file tasks, often after
  a rejected first call that the tool's message helped to fix. The failures are in the content: missing values
  and topics, wrong group sums, dates on the wrong weekday.
- **gpt-oss-120b** hits the limit of 8 tool rounds in 8 runs; only 73 of its 149 calls rejected by the tool's
  content validation are followed by a file.
- **Nemotron 3.5 Super** sent invalid JSON in 49 calls (v0.1: 20) and recovered from only 25 of them.
- **Qwen3.8-Flash** builds more files than needed in 36 of 150 runs (a new file for each small fix).

What is measured is always the combination of model, this tool and this harness (system prompt, attachment
template, round limit), not the model alone.

## Quick start

```sh
git clone https://github.com/tovren/office-bench-de && cd office-bench-de
uv sync                                   # Python >= 3.11
uv run obench tasks list                  # the 50 tasks

export AI_GATEWAY_API_KEY=...             # or any OpenAI-compatible endpoint, see configs/models/local-example.toml
uv run obench run configs/models/deepseek-v4-flash-high.toml --probe        # 2 tasks, 1 run: is the setup right?
uv run obench run configs/models/deepseek-v4-flash-high.toml --out runs/my-run
uv run obench report runs/my-run > runs/my-run/report.md                    # scores the runs, then reports
```

Scoring needs LibreOffice (`soffice`); the quality review also needs `pdftoppm` (poppler-utils). To compare your
model with the published results:

```sh
uv run obench report results/v0.2 runs/my-run
```

A full run of 150 task runs took 7 to 40 minutes per model through the gateway (4 at a time).

## How it works

| | |
|---|---|
| [docs/task-format.md](docs/task-format.md) | tasks: `task.toml`, attachments, reference solution, the checks a task can use |
| [docs/harness.md](docs/harness.md) | what the model is sent, how tool calls are executed, retries, the run log, model configs |
| [docs/scoring.md](docs/scoring.md) | success, content ok, pass^k, outages, the statistics behind the intervals |
| [docs/judge.md](docs/judge.md) | the blind quality review, by API or by agent sessions, and its calibration |
| [docs/mutants.md](docs/mutants.md) | 202 broken variants of the reference solutions that test the checks themselves |
| [docs/open-issues.md](docs/open-issues.md) | known limits and checks that are still missing |

- **Tasks** (`tasks/<id>/`): 43 tasks that end with a file (18 Excel, 16 Word, 9 PowerPoint), 6 of them follow-ups
  over several turns, and 7 tasks where the right answer is no file (a question, an e-mail text, an
  extra tool such as web search or a calendar entry). The reference date is Tuesday, 13 October 2026.
- **The tool** is vendored unchanged (`src/officebench/tool/`, Office Documents 0.3.1, plugin commit `0386886`),
  with the function specs frozen as Open WebUI 0.11.4 sends them. The model only fills in JSON arguments; fixed code builds the file.
- **The content check** has over 40 checks: required values and topics, formulas and their results after
  recalculation, total rows, weekdays and public holidays, numbers without a source, placeholders, retained
  content in follow-ups and more. A hard defect means the file is not usable as delivered; soft defects are
  reported but do not decide success. Each task's reference solution passes its checks; of 202 mutants the tool
  itself sends back or repairs 8, and the checks catch 178 of the other 194.
- **The quality review** grades blind: neutral ids, neutral file timestamps, one file per request.

## Data

`results/v0.2/` and `results/v0.1/` hold, per model, `meta.json` (model config, profile, tool and task hashes),
`log.jsonl` (every round: tokens, cost, provider, tool calls and their results; reasoning is not stored) and
`results.jsonl` (the scored runs), plus the report; `results/v0.1/grades.jsonl` has all 696 quality grades with
reasons, in German. The built files (the documents plus the raw arguments of every tool call) are release
downloads (`v0.2-files.zip`, `v0.1-files.zip`): unzip them into the matching folder to rerun the content check.

## License

MIT, see [LICENSE](LICENSE). The vendored Office Documents tool is MIT as well.
