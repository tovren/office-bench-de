# Scoring and statistics

How a task run becomes a result, what counts as success, what is left out, and how the intervals in the report are
computed. The code is `src/officebench/scoring.py` (definitions in its docstring), `stats.py` and `report.py`.

```
obench score runs/<run>                     # results.jsonl in every model folder
obench report runs/<run> [runs/<other>/<model> ...] [--compare A B] [--grades grades.jsonl]
```

Both take model folders (`runs/<run>/<model>/`) or run folders holding them. `report` scores a folder first if its
`results.jsonl` is missing or older than the log (`--rescore` forces it). Scoring always uses the current task
files; a task that changed since the run (other hash in the log) is marked in the report.

## One task run

A task run is one task with all its user messages (turns), as logged in `log.jsonl`. The scorer reads it together
with the files the tool built (`files/`) and runs the content check once over all delivered files of the model
folder (one LibreOffice start for all spreadsheets).

| Term | Meaning |
|---|---|
| office call | a call of the office tool: every call whose name is not one of the task's extra tools, including a misspelt function name (the model tried the office tool). Calls of extra tools never count, even when their arguments are broken. |
| file built ("done") | an office call whose result starts with "Done": the tool built a file. |
| file at 1st call | the first office call of the run built a file. Shows how often a model gets the arguments right without help from the tool's error messages. |
| turn fulfilled | the turn was sent and, depending on what it expects: a file was built in it (`file`), the office tool was not called (`no_file`), or anything (`any`). |
| file at end | file tasks: a file was built in the last turn that expects one. For a follow-up, a file from an earlier turn does not count: the user asked for a change. |
| delivered file | the file of the last successful office call, the one the user ends up with. The content check runs on it. |
| previous file | follow-ups: the file last built in an earlier turn; the check `retained` compares the delivered file with it. |
| content ok / clean | content check of the delivered file: no hard defect / no defect at all. Without a file: not ok. Defects and their severity are described in docs/task-format.md. |
| final answer | the text of the model's last message if the run ended with an answer (a message without tool calls). An empty text is no final answer. |
| reply check | tasks with `[reply].topics` / `forbidden`: every topic is in the final answer and nothing forbidden is. `words_max` and `no_markdown` only give soft defects. |
| behavior check | tasks with `[behavior]`: every expected extra tool was called and no forbidden one. |
| rejection | an office call that did not build a file, with a category: invalid JSON, schema / required field, garbled arguments, the tool's content validation, wrong function, not a JSON object, exception in the tool, other. "File after it" = a file still came in the same turn. |
| round limit | the profile allows `max_rounds` rounds with tool calls per user message. If the model still calls tools after that, the calls are not executed and the turn ends without a final answer (like Open WebUI's tool-call limit). That missing final answer is not counted as "no final answer". |
| claims file | a message of a turn without a built file says a file was created or is ready (German pattern; sentences with negations or conditions do not count). |
| links | Markdown links, URLs and `sandbox:` paths in the model's messages: the file is attached by the tool, so any link is invented. |
| unnecessary call | the office tool was called in a turn that expects no file. |

## Success

**File tasks** (`file`, `follow_up`): file at end, every turn fulfilled and content ok; for tasks with a reply
check that check too, for tasks with a behavior check that check too. The final answer itself is not required: the
file is what the user asked for.

**Tasks without a file** (`no_file`): no office call in a turn that expects no file, a final answer, the reply check
and the behavior check.

Success is **not determinable** (left out of the rates, shown as `?` in the per-task table) when the file of the last
successful call is missing from `files/`, or when the reply check depends on text the log cut off (the log keeps
4000 characters of every message; a topic missing in the kept part could follow in the cut part).

## What is not scored

A run is **not scored** when a failure the model cannot help ended it before its outcome was settled:

- `provider` (overload, rate limit, outage of a remote API) or `network` (connection errors, timeouts, broken
  streams) after all retries, **and**
- for file tasks: no file was built yet in the last turn that expects one; for tasks without a file: no final
  answer yet (and no unnecessary office call that already decided the run).

Whether the file was good does not matter for this: a run with a bad file that then lost its connection is scored
(and failed), so outages cannot hide failures. Also not scored are task runs of the run's selection that have no
log line (the run was aborted or is still going); the report counts them.

A **server error** (an error from the model's own server, e.g. HTTP 500 from llama.cpp or vLLM on a tool call it
cannot parse) is scored as a failed run: in a chat front end the user would see the chat break, so it is a failure
of the model setup, not bad luck.

## Rates and intervals

All rates count only scored runs with a known value. File columns (file at 1st call, file at end, content ok,
clean) count only tasks that ask for a file; success counts all tasks.

**Estimate.** The mean over tasks of each task's rate. Every task weighs the same, however many of its runs were
scored.

**Interval.** Runs of the same task are not independent: a model that fails a task usually fails it every time. 50
tasks × 3 runs are therefore much less information than 150 independent attempts, and an interval that pretends
otherwise (Wilson, normal approximation over runs) is too narrow. The report uses a two-stage **cluster bootstrap**:
draw the tasks with replacement, then the runs within each drawn task with replacement, compute the estimate, repeat
4000 times; the 2.5th and 97.5th percentiles give the 95 % interval. With a fixed seed the numbers are reproducible.
When the interval has zero width (all values equal, e.g. 40/40) the Wilson interval is shown as well, as a reminder
that 100 % on 40 runs is not certainty.

**pass^k.** The chance that k fresh runs of the same task all succeed, mean over tasks (per task C(c, k) / C(n, k)
for c successes in n runs, which is unbiased). It shows reliability: a model that solves half the tasks always and
the other half never has success 50 % and pass^3 50 %; one that solves every task half the time has success 50 % but
pass^3 12.5 %. The report gives pass^2 and pass^k with k = the smallest number of scored runs per task.

**Comparing two models** (`--compare A B`). Paired over the tasks both have: per task the difference of the two
rates, the mean of these differences, a bootstrap interval over tasks and a two-sided sign-flip permutation test
(exact up to 16 tasks, else 10,000 random flips). Pairing removes the task difficulty from the comparison, so it is
much sharper than checking whether two separate intervals overlap. Tasks only one model ran are listed and left out.

## Operations

- **time to file**: model time (sum of the request durations, without retry pauses) up to the first built file;
  median over runs.
- **tokens**: prompt and completion tokens as reported by the API, mean per run.
- **cost**: as reported by the API or gateway (missing for local servers); cost per success = total cost of the
  scored runs / number of successes.

## Judge grades

`--grades FILE` adds grades of an LLM judge, one JSON line per graded file:

```json
{"model": "qwen3.8-27b-medium", "task": "budget", "rep": 0, "file": "budget-0__r0c0__Budget.xlsx",
 "judge": "…", "grades": {"language": 4, "content": 3, "completeness": 4, "structure": 5, "usefulness": 4}, "mean": 4.0}
```

A file counts once: its grade is the mean over judges (several lines of the same judge for a file are averaged
first). The model's mean is the mean over tasks of the per-task mean, with the same cluster bootstrap; the report
also gives the mean per criterion and, for models next to each other in the ranking, the paired difference with its
interval and p-value. Grades from different judge instructions should not be mixed in one file.
