# Harness

How a run works: what the model is sent, how its tool calls are executed, what is retried, what is logged, and how
to run the benchmark on your own model. The code is `src/officebench/harness/client.py` (one streamed request),
`src/officebench/harness/runner.py` (the chat loop and the run folder), `src/officebench/config.py` (model and
profile configs) and `src/officebench/tool/__init__.py` (execution of a tool call).

Every model gets the same tasks, the same system prompt, the same tool and the same limits. The model only fills in
the tool's JSON arguments; fixed code builds the file. What is measured is therefore the combination of model, this
tool and this harness (see docs/open-issues.md).

```
obench run configs/models/<model>.toml --out runs/<run>     # run all tasks, 3 times each
obench score runs/<run>                                      # content checks -> results.jsonl
obench report runs/<run>                                     # Markdown report
```

## Installation

```
uv sync                       # Python >= 3.11; creates .venv with the package and the obench command
uv run obench tasks validate  # all task files load
```

Run the commands with `uv run obench …` or activate `.venv` first.

| Step | Needs |
|---|---|
| `obench run` | network access to the model's endpoint; nothing else |
| `obench score`, `obench report`, `obench check` | LibreOffice (`soffice` on `PATH`, the macOS app bundle, or `/usr/bin/soffice`): every xlsx is recalculated before it is checked |
| `obench judge` | LibreOffice and `pdftoppm` (poppler-utils): files are converted to PDF and rendered as page images |

## Model config

One TOML file per model **and setting** (a thinking level is a setting: `qwen3.8-27b-medium` and a
`qwen3.8-27b-high` would be two configs). Examples are in `configs/models/`, including `local-example.toml`.

```toml
name = "qwen3.8-27b-medium"             # id in results and name of the model folder
label = "Qwen3.8-27B, thinking medium"  # shown in reports
base_url = "https://ai-gateway.vercel.sh/v1"
model = "alibaba/qwen3.8-27b"
api_key_env = "AI_GATEWAY_API_KEY"      # or api_key_file = "~/.config/…"; neither for a local server
concurrency = 4                         # parallel task runs (default 4)

[params]                                # merged into every request body as given
max_tokens = 32000
reasoning = { effort = "medium" }
temperature = 1.0
top_p = 0.95
top_k = 20

[info]                                  # facts for the report, free keys
open_weights = true
parameters = "27B"
```

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | `[a-z0-9][a-z0-9._-]*`; the folder `runs/<run>/<name>/` and the model's id in results |
| `label` | yes | display name in reports |
| `base_url` | yes | OpenAI-compatible endpoint including `/v1`; requests go to `<base_url>/chat/completions` |
| `model` | yes | the model name sent in the request |
| `api_key_env` | no | name of an environment variable holding the key; the run stops if it is not set |
| `api_key_file` | no | path to a file holding the key (`~` is expanded, whitespace stripped) |
| `params` | no | table merged at the top level into every request body, unchanged. Anything the endpoint accepts can go here (`max_tokens`, `temperature`, `reasoning`, `top_k`, `providerOptions` …). Not allowed: `messages`, `tools`, `stream`, `model` |
| `info` | no | free keys for the report (`open_weights`, `parameters`, `weights_gb` …); not sent to the model |
| `concurrency` | no | how many task runs of this model run at the same time (default 4, minimum 1). One task run sends its requests one after another |

`api_key_env` and `api_key_file` exclude each other. With neither, no `Authorization` header is sent. The key is
never written to the run folder: `meta.json` holds the config as written, i.e. the variable name or file path.

Unknown keys are an error, so a typo cannot silently drop a setting.

## Profile

The profile fixes everything around the model that the benchmark holds constant. Results are comparable only within
one profile; the published results use `configs/profiles/default.toml`. `--profile` takes a name in
`configs/profiles/` or a path.

```toml
name = "default"
today = 2026-10-13
system_prompt = "Heute ist Dienstag, 13. Oktober 2026. Antworte auf Deutsch."
max_rounds = 8
attachment_message = """Angehängte Dateien (extrahierter Text):

{files}

{message}"""
attachment_file = """<file name="{name}">
{text}
</file>"""

[valves]
language = "de"
```

| Key | Meaning |
|---|---|
| `name`, `description` | for meta.json and reports |
| `today` | reference date of the run, Tuesday 13 October 2026. Written to meta.json; the date checks use it ("today", dates without a year, past dates) |
| `system_prompt` | the only system message. It states the reference date and the answer language and nothing else: no instructions on files, tools, style or citations |
| `attachment_message` | how a user message with attachments is built; must use exactly `{files}` and `{message}` |
| `attachment_file` | how one attachment is rendered inside `{files}`; must use exactly `{name}` and `{text}` |
| `valves` | settings of the office tool (see below) |
| `max_rounds` | rounds with tool calls per user message (default 8) |

**Attachments.** A task's attachments are the text a document loader would extract from the uploaded files. As in
a chat front end, this text goes in front of the user's message, in the same user message: each file as
`<file name="…">…</file>`, joined by a blank line, under the line "Angehängte Dateien (extrahierter Text):", then a
blank line and the message itself. A message without attachments is sent as written.

**No citation instruction.** Retrieval templates of chat front ends (Open WebUI's default among them) ask the model
to cite its sources with markers like `[1]`. Models then also write these markers into the documents and e-mails
they produce, which is a defect in a letter or a protocol. The benchmark is about the documents, so the profile uses
a neutral template. Tasks with attachments still check for leftover source markers (`forbidden` with
`\[\d{1,2}\]`).

Every field of the profile goes into `profile_hash`; a resumed run refuses a changed profile.

## The tool

`src/officebench/tool/office_documents.py` is the Open WebUI tool "Office Documents"
(https://github.com/tovren/open-webui-plugins, MIT), copied **unchanged** from commit `641df3a`. It offers three
functions: `create_word_file`, `create_excel_file`, `create_powerpoint_file`. The model sends the content as JSON
(headings, paragraphs, tables, cells with formulas, charts, slides …); the tool validates it and builds the file.

- **Specs.** `specs.json` holds the three tool specs exactly as Open WebUI 0.11.4 generates them from the method
  signatures and docstrings, so the model sees the same tool as in Open WebUI. They are frozen; `tests/test_tool.py`
  checks that they still match the code.
- **Delivery.** In Open WebUI the tool attaches the file to the chat. Here the delivery step is replaced: the file
  is kept and saved to the run folder, and the model gets the same result text it would get in Open WebUI
  ("Done: the file '…' was created and is attached to your answer … Do not add a link …").
- **Language.** The valve `language = "de"` makes the texts the tool itself writes into files German (label of the
  total row, page footer) and uses the decimal comma. The tool's messages to the model stay English.
- **Hash.** `tool_hash` (code and specs) and `tool_commit` are written to meta.json; a resumed run refuses a changed
  tool.

## The chat loop

A **task run** is one task with all its user messages (turns). A **round** is one request to the model.

1. The history starts with the system prompt.
2. For each turn: the user message (with attachments, if any) is appended.
3. A round: the request body is `model`, the history as `messages`, `tools` = the three office specs plus the
   task's extra tools, then everything in `params`; the client adds `stream: true` and
   `stream_options: {include_usage: true}`. No `tool_choice` is sent (the endpoint's default, normally `auto`).
4. The stream is assembled the way chat front ends do it: text deltas are concatenated; reasoning comes from
   `reasoning_content`, `reasoning` or `<think>…</think>` inside the text (removed from the text); tool-call deltas
   are merged by their `index` (a server that omits it: a new `id` starts a new call). Usage and cost are taken from
   any chunk that carries them. A server that ignores `stream: true` and returns one JSON response is accepted too.
5. The assistant message is appended to the history: its text (or `null`) and its tool calls. **Reasoning is not
   sent back**: later rounds see only the text and the tool calls of earlier rounds.
6. No tool calls: the turn ends with an answer. Tool calls: they are executed in the order given, each result goes
   back as a `tool` message with the call's `tool_call_id`, and the next round starts.
7. **Round limit.** Per user message the model gets at most `max_rounds` = 8 rounds whose tool calls are executed.
   If the model still calls tools in the round after that (the 9th), those calls are **not executed**, the turn
   ends without a final answer (`end = "round_limit"`), and the calls are logged as `not_executed`. This mirrors
   Open WebUI's limit on tool-call rounds. The scorer does not count this missing answer as "no final answer".
8. **Follow-up turns** (`kind = "follow_up"`): after a turn has ended, the next user message is appended to the
   same history and the loop continues. The round limit applies per user message.
9. An error that survives the retries ends the task run (`end = "error"`); later turns are not sent.

**Extra tools.** Some tasks offer further tools (`extra_tools/<name>.json`: `web_search`,
`create_calendar_event`, `send_email`). Each file holds an OpenAI tool spec and a canned answer. A call of an extra
tool is not executed: the canned answer goes back as the tool result, whatever the arguments. Arguments that cannot
be parsed still get the parse error (see below). The calls are logged like office calls, so `[behavior]` checks can
see which tools were called.

### What the model gets back from a tool call

| Case | `status` | Text sent back to the model |
|---|---|---|
| file built | `ok` | the tool's result: "Done: the file '…' was created and is attached to your answer …" |
| the tool rejects the content (its own validation) | `ok` | the tool's message: "The file was NOT created because the arguments are invalid: … Fix these points and call … again with the complete, corrected content." |
| arguments are neither JSON nor a Python literal | `parse_error` | "Error: the arguments of `<name>` could not be parsed. The model generated malformed or incomplete JSON. Please try again." |
| arguments parse but are not an object | `not_object` | "Error: the arguments of `<name>` must be a JSON object. Please try again." |
| function name not offered | `unknown_function` | `Error: tool "<name>" not found.` |
| the tool raised an exception | `exception` | `{"error": "<message>"}` |
| extra tool | `extra_tool` | the canned answer |

Arguments are parsed as JSON first, then as a Python literal (some models write single quotes). Parameters that are
not in the spec are dropped before the call and logged (`dropped`), as Open WebUI does. `done` in the log means the
result starts with "Done", i.e. a file was built; `status = ok` alone does not mean that.

## Errors

The client classifies every failed request, because the kinds are scored differently (docs/scoring.md, "What is
not scored").

| Kind | When | Retried | Scored |
|---|---|---|---|
| `provider` | HTTP 429, 502, 503, 504, 529 from any endpoint; from a remote endpoint also any other 5xx, an error text matching overload/rate limit/capacity/unavailable, or an error object inside the stream | yes, up to 20 times, 30 s apart | not scored if it ended the run before the outcome was settled |
| `network` | connection errors, timeouts, invalid JSON in the stream, a stream that ends without a finish reason or `[DONE]` | yes, up to 20 times, waiting 2 s × attempt (at most 30 s) | as `provider` |
| `server` | any other HTTP error (400, 422 …); from a **local** endpoint also HTTP 500 and other 5xx, and an error object inside the stream unless its text reads like overload | no | counted as a failed run |
| (config) | HTTP 401, 403, 404 (wrong key, URL or model name); not a logged kind | no | the whole `obench run` stops with exit code 2; finished task runs stay in the log |

**Local endpoints** are `localhost`, `*.local`, host names without a dot (`llm`, `gpu-box`) and private, loopback
or link-local IP addresses. A local server that refuses connections is retried only 3 times, at most 10 s apart.
The distinction exists because a remote API that fails under load is bad luck, while a local server that answers a
tool call with HTTP 500 (e.g. llama.cpp or vLLM failing to parse the model's tool call) is what the user of that
setup would see: the chat breaks. That is a failure of the model setup, not of the provider.

HTTP timeouts: 30 s to connect, 600 s between two reads of the stream, 60 s to send.

## Resuming and `--retry-failed`

The run folder is `<out>/<name>/`. Starting `obench run` again with the same `--out` resumes it:

- `meta.json` is compared with the new run: a different model config, `profile_hash` or `tool_hash` stops with an
  error ("use a new run name"). The task selection and `--repeats` may change; meta.json is rewritten with the
  latest ones.
- Every (task, rep) that already has a line in `log.jsonl` is skipped. A task run writes its line only when it has
  finished, so runs interrupted with Ctrl-C are simply started again.
- `--retry-failed` also reruns every (task, rep) whose last log line ended with a `provider` or `network` error,
  whether or not the scorer would have counted it. `server` errors are not rerun: they are results.
- A rerun first deletes the task run's old files in `files/` and appends a new log line; readers use the **last**
  line per (task, rep).

## Run folder

```
runs/<run>/<model>/
  meta.json      model config (without key), profile, hashes, task selection, harness version
  log.jsonl      one line per finished task run
  files/         raw arguments of every tool call and every file the tool built
  results.jsonl  written by `obench score` (docs/scoring.md)
```

**meta.json**

| Field | Meaning |
|---|---|
| `model` | the model config as loaded (with `api_key_env`/`api_key_file`, never the key) |
| `profile` | the full profile |
| `profile_hash` | short SHA-256 of the profile |
| `tool_hash` | short SHA-256 of `office_documents.py` and `specs.json` |
| `tool_commit` | the upstream commit the tool was copied from (`641df3a`) |
| `tasks` | task ids of the selection |
| `task_selection_hash` | short SHA-256 over the ids and hashes of the selected tasks |
| `repeats` | runs per task |
| `harness` | package version, plus `git describe` of the checkout if available |
| `started` | time of the first start of this folder |

**files/** — for every executed tool call, with `<n>` = the number of tool rounds executed before it in this task
run (counted across turns, from 0) and `<i>` = its position in the round:

- `<task>-<rep>__r<n>c<i>__<function>.json`: the arguments exactly as the model sent them (may be invalid JSON);
  the function name is URL-encoded.
- `<task>-<rep>__r<n>c<i>__<file name>`: the file the call built, with the name the tool gave it (`/`, `\` and
  control characters replaced by `_`).

The built file with the highest `(n, i)` is the one the user ends up with ("delivered file").

### Log record

One JSON object per line. Texts are cut to 4000 characters.

| Field | Type | Meaning |
|---|---|---|
| `format` | int | log format version, currently 1 |
| `task` | str | task id |
| `rep` | int | repetition, from 0 |
| `task_hash` | str | hash of the task files at run time; scoring marks tasks that changed since |
| `started`, `finished` | str | ISO 8601 local time with offset |
| `turns` | list | one entry per turn that was sent: `{"end": …, "rounds": n}` |
| `turns[].end` | str | `answer` (a message without tool calls), `round_limit`, `error` |
| `turns[].rounds` | int | requests in this turn, including a failed one |
| `rounds` | list | every request of the task run, in order (fields below) |
| `outcome` | str | `end` of the last turn that was sent |
| `final_answer` | str or null | text of the last round if `outcome` is `answer`, else null; may be empty |
| `error` | str | only on `outcome = error`: the error message (at most 1000 characters) |
| `error_kind` | str | only on `outcome = error`: `provider`, `network` or `server` |

**`rounds[]`**

| Field | Type | Meaning |
|---|---|---|
| `turn` | int | index of the turn the round belongs to |
| `seconds` | float | duration of the successful attempt (0 for a failed round) |
| `ttft` | float or null | seconds until the first delta with text, reasoning or a tool call |
| `attempts` | int | attempts including retries |
| `wait_seconds` | float | sum of the pauses before retries (not in `seconds`) |
| `finish_reason` | str or null | as reported (`stop`, `tool_calls`, `length` …) |
| `usage` | object | the usage object of the stream as reported (`prompt_tokens`, `completion_tokens`, provider extras); `{}` if none |
| `cost` | float or null | `usage.cost` or the gateway's `provider_metadata.gateway.cost`; null for local servers |
| `model` | str or null | model name reported by the server (can differ from the requested one) |
| `provider` | object | provider fields of chunks and deltas (keys containing "provider", `system_fingerprint`); `served_by` = the provider that answered, if the gateway says so. Values longer than 2000 characters are stored as a cut JSON string |
| `content` | str | the assistant text, `<think>` parts removed, stripped |
| `reasoning_chars` | int | length of the reasoning text (the reasoning itself is not logged) |
| `calls` | list | executed tool calls of this round (fields below) |
| `not_executed` | list | only at the round limit: `{"name", "arguments_chars"}` of the calls that were not executed |
| `error`, `error_kind` | str | only on a failed round |

**`rounds[].calls[]`**

| Field | Type | Meaning |
|---|---|---|
| `name` | str | function name as sent by the model |
| `status` | str | `ok`, `parse_error`, `not_object`, `unknown_function`, `exception`, `extra_tool` |
| `done` | bool | the result starts with "Done": a file was built |
| `arguments_chars` | int | length of the raw arguments (the arguments are in `files/`) |
| `result` | str | the text sent back to the model |
| `dropped` | list | only if any: parameters not in the spec, dropped before the call |
| `file` | str | only if a file was built: its name in `files/` |

## Commands

```
obench run MODEL.toml [MODEL.toml ...] [--tasks SEL] [--repeats 3] [--profile default] [--out runs/latest]
                                       [--probe] [--retry-failed]
```

Runs the selected tasks (`--tasks`: `all`, ids, `tag:<tag>`, `type:<docx|xlsx|pptx>`, `kind:<kind>`, separated by
commas) `--repeats` times against each model, one model after the other, into `<out>/<name>/`. Progress goes to
stdout, one line per finished task run with its outcome. Exit code 2 on a config error (the following models are
not run).

```
obench run MODEL.toml --probe --out runs/probe
```

Quick probe: the first 2 tasks of the selection, 1 run each. Use it to see that the endpoint, key, model name, tool
calling and streaming work before starting a full run. Use a separate `--out`, since a probe folder is resumed like
any other.

```
obench score runs/<run> [runs/<other>/<model> ...]
obench report runs/<run> [...] [--compare A B] [--grades grades.jsonl] [--rescore]
```

`score` writes `results.jsonl` into every model folder; `report` prints a Markdown report and scores first where
needed. Both take model folders or run folders holding them. Definitions: docs/scoring.md.

```
obench check FILE_OR_FOLDER ... [--task ID] [--only-defects] [--today YYYY-MM-DD] [--previous FILE]
```

Content check of single files, e.g. a file from `files/` or one built by hand. The task is taken from the file name
(`budget-3__…`) unless `--task` is given; without a task only the general checks run. `--previous` is the earlier
file of a follow-up task (for `retained`). `obench check --help` shows the options.

## Testing your own local model

Any server with an OpenAI-compatible `/v1/chat/completions` endpoint, streaming and tool calls works. Start from
`configs/models/local-example.toml`:

```toml
name = "my-model-q4"            # one config per model, quantisation and setting
label = "My model, Q4_K_M"
base_url = "http://127.0.0.1:8080/v1"
model = "local-model"
concurrency = 1

[params]
max_tokens = 16000
temperature = 0.7               # the sampling values of the model card
```

| Server | `base_url` | `model` | Tool calling |
|---|---|---|---|
| llama.cpp `llama-server` | `http://127.0.0.1:8080/v1` | any (the loaded model answers) | start with `--jinja` |
| vLLM | `http://127.0.0.1:8000/v1` | the served model name | `--enable-auto-tool-choice --tool-call-parser <parser>`, plus `--reasoning-parser <parser>` for thinking models |
| LM Studio | `http://127.0.0.1:1234/v1` | the model identifier shown in LM Studio | needs a model whose chat template supports tools |
| Ollama | `http://127.0.0.1:11434/v1` | the model tag | needs a model whose chat template supports tools |

```
uv run obench run configs/models/my-model-q4.toml --probe --out runs/probe
uv run obench run configs/models/my-model-q4.toml --out runs/mine
uv run obench report runs/mine runs/v0.1           # next to the published models
```

Points to watch:

- **Context.** The first request of a task is about 2,000 to 15,000 prompt tokens (tool specs, attachments); in the
  published runs the longest request had about 28,000. Add `max_tokens` for the answer: a context of 48k tokens or
  more avoids cut-off runs.
- **Concurrency.** Keep `concurrency` at the number of parallel slots the server really has (llama.cpp
  `--parallel`), otherwise requests queue and may hit the 600 s read timeout.
- **Errors count.** A local server's HTTP 500 or 400 on a tool call it cannot parse is scored as a failed run, not
  retried. This is intended: it is what the user of that setup would see. If the server is reached through a host
  name with a dot that does not resolve to a private address, it is treated as remote and such errors are retried.
- **Reasoning.** Thinking text in `reasoning_content` or in `<think>` tags is recognised and kept out of the answer
  text; it is not sent back in later rounds.
- **Thinking level.** Pass it in `params` as the server expects it (e.g. `chat_template_kwargs` for vLLM and
  llama.cpp, `reasoning` for gateways); make one config per setting.
