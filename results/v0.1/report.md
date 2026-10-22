# Report (2026-10-22)

Runs:
- `claude-haiku-5.5-medium` (results/v0.1/claude-haiku-5.5-medium): Claude Haiku 5.5, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 96ea6b2d45ac, harness 0.1.0+41aa661-dirty
- `deepseek-v4-flash-high` (results/v0.1/deepseek-v4-flash-high): DeepSeek V4 Flash 0731, thinking high, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 96ea6b2d45ac, harness 0.1.0+41aa661-dirty
- `gemma-4-31b` (results/v0.1/gemma-4-31b): Gemma 4 31B, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 96ea6b2d45ac, harness 0.1.0+41aa661-dirty
- `gpt-oss-120b-medium` (results/v0.1/gpt-oss-120b-medium): gpt-oss-120b, reasoning medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 96ea6b2d45ac, harness 0.1.0+41aa661-dirty
- `nemotron-3.5-super` (results/v0.1/nemotron-3.5-super): Nemotron 3.5 Super VL, thinking on, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 96ea6b2d45ac, harness 0.1.0+41aa661-dirty
- `qwen3.8-27b-medium` (results/v0.1/qwen3.8-27b-medium): Qwen3.8-27B, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 96ea6b2d45ac, harness 0.1.0+41aa661-dirty
- `qwen3.8-flash-medium` (results/v0.1/qwen3.8-flash-medium): Qwen3.8-Flash, thinking medium, 150 task runs, 50 tasks × 3, profile default (today 2026-10-13), tool 96ea6b2d45ac, harness 0.1.0+41aa661-dirty

> Tasks changed since the run (the checks of the current version apply): richtlinie, wartungsmail, zeiterfassung

## Rates

| model | scored runs | file at 1st call | file at end | content ok | clean | success | pass^2 (success) | pass^k (success) |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 150 (50 tasks) | 78 % (66–88) · 100/129 | 99 % (97–100) · 128/129 | 90 % (82–97) · 116/129 | 45 % (32–58) · 58/129 | 91 % (84–97) · 137/150 | 85 % | k=3: 80 % |
| deepseek-v4-flash-high | 150 (50 tasks) | 88 % (79–95) · 113/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 90 % (81–97) · 116/129 | 59 % (46–72) · 76/129 | 88 % (79–95) · 132/150 | 83 % | k=3: 80 % |
| gemma-4-31b | 150 (50 tasks) | 73 % (61–84) · 94/129 | 99 % (97–100) · 128/129 | 59 % (45–73) · 76/129 | 32 % (19–44) · 41/129 | 65 % (52–77) · 97/150 | 59 % | k=3: 56 % |
| gpt-oss-120b-medium | 150 (50 tasks) | 91 % (82–98) · 117/129 | 94 % (86–100) · 121/129 | 68 % (56–80) · 88/129 | 40 % (27–53) · 52/129 | 68 % (56–79) · 102/150 | 56 % | k=3: 48 % |
| nemotron-3.5-super | 150 (50 tasks) | 89 % (82–95) · 115/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 86 % (76–95) · 111/129 | 49 % (36–62) · 63/129 | 86 % (77–94) · 129/150 | 79 % | k=3: 76 % |
| qwen3.8-27b-medium | 150 (50 tasks) | 80 % (70–88) · 103/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 86 % (77–95) · 111/129 | 51 % (39–64) · 66/129 | 85 % (77–93) · 128/150 | 77 % | k=3: 70 % |
| qwen3.8-flash-medium | 150 (50 tasks) | 81 % (72–90) · 105/129 | 100 % (100–100; Wilson 97–100) · 129/129 | 82 % (72–91) · 106/129 | 56 % (43–69) · 72/129 | 83 % (75–91) · 125/150 | 73 % | k=3: 66 % |

## Operations

| model | median time to file | mean rounds to file | mean tokens in / out | cost total | cost per success | server errors | outages (not scored) | missing (no log line) | no final answer | round limit | claims file without file | links in the reply | more files than needed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 13 s | 1.30 | 16795 / 6123 | $ 0.711 | $ 0.0052 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 4 |
| deepseek-v4-flash-high | 19 s | 1.19 | 11153 / 5445 | $ 0.173 | $ 0.0013 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| gemma-4-31b | 11 s | 1.38 | 10077 / 3977 | $ 0.383 | $ 0.0039 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 |
| gpt-oss-120b-medium | 7 s | 1.04 | 10270 / 2793 | $ 0.364 | $ 0.0036 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 |
| nemotron-3.5-super | 7 s | 1.17 | 10762 / 4761 | $ 0.501 | $ 0.0039 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| qwen3.8-27b-medium | 11 s | 1.23 | 11737 / 3690 | $ 0.273 | $ 0.0021 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 14 |
| qwen3.8-flash-medium | 22 s | 1.21 | 15357 / 4719 | $ 0.463 | $ 0.0037 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 |

Time to file: model time (sum of the round durations without retry pauses) up to the first built file. Costs as reported by the API (missing for local servers).

## Tool rejections and recovery

| model | runs with a rejection: file after it | invalid JSON | schema / required field | garbled arguments | tool's content validation |
|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 29/30 | 26/26 | – | – | 14/15 |
| deepseek-v4-flash-high | 23/24 | 3/3 | 1/1 | – | 29/30 |
| gemma-4-31b | 36/37 | 22/30 | 3/3 | 13/13 | 15/15 |
| gpt-oss-120b-medium | 9/17 | 0/3 | – | – | 12/73 |
| nemotron-3.5-super | 20/20 | 20/20 | 2/2 | – | 10/10 |
| qwen3.8-27b-medium | 29/29 | 15/15 | 2/2 | – | 16/16 |
| qwen3.8-flash-medium | 29/30 | 12/12 | 2/2 | – | 20/21 |

Cell per category: rejected calls after which a file came in the same turn / all rejected calls.

## Follow-ups, tasks without a file, extra tools

| model | follow-up: all turns fulfilled | no file: unnecessary office call | no file: reply topics there | with file: reply check passed | extra tool called (runs / offered) | reply truncated |
|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 18/18 | 0/21 | 21/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| deepseek-v4-flash-high | 18/18 | 4/21 | 21/21 | 2/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| gemma-4-31b | 18/18 | 0/21 | 21/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| gpt-oss-120b-medium | 18/18 | 0/21 | 15/21 | 2/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 1 |
| nemotron-3.5-super | 18/18 | 2/21 | 19/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| qwen3.8-27b-medium | 18/18 | 1/21 | 18/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |
| qwen3.8-flash-medium | 18/18 | 1/21 | 20/21 | 3/3 | web_search 3/3, send_email 0/9, create_calendar_event 3/6 | 0 |

Unnecessary office call: the office tool was called in a turn that expects no file. Whether an extra tool should be called is set per task ([behavior]). Reply check: [reply] topics there and nothing forbidden in the final answer. Reply truncated: the log keeps 4000 characters; counted for tasks with a reply check.

## Most common defects

| model | files checked | hard defects (runs) | soft defects (runs) | numbers without source |
|---|---|---|---|---|
| claude-haiku-5.5-medium | 128 | missing value (4), wrong calculation (3), no chart (2), missing topic (2), too few sheets (1), too few rows (1) | placeholder (19), missing topic (9), number without source (9), markdown in reply (9), date on a weekend (8), share over 100 % (6) | 0.9 · 9/57 |
| deepseek-v4-flash-high | 129 | missing value (6), very short (3), no total row (2), forbidden content (2), formula error (1), missing prices (1) | missing topic (12), number without source (10), markdown in reply (9), date on a weekend (7), placeholder (5), rather short (5) | 0.8 · 10/57 |
| gemma-4-31b | 128 | missing value (24), missing topic (16), no total row (13), no chart (8), no formula (7), summary does not match (5) | missing topic (15), rather short (11), markdown in reply (9), placeholder (9), date on a weekend (8), number without source (6) | 0.6 · 6/56 |
| gpt-oss-120b-medium | 121 | missing value (11), missing topic (8), very short (8), missing topic in reply (7), wrong chart values (2), summary does not match (2) | missing topic (20), date on a weekend (13), number without source (10), markdown in reply (9), rather short (7), date not on a workday (7) | 0.8 · 10/56 |
| nemotron-3.5-super | 129 | very short (6), missing value (5), missing topic (4), missing topic in reply (2), no formula (2), summary does not match (2) | missing topic (15), placeholder (12), number without source (10), markdown in reply (9), date on a weekend (7), date as text (5) | 0.7 · 10/57 |
| qwen3.8-27b-medium | 129 | missing value (6), missing topic (5), missing topic in reply (3), wrong weekday (3), no total row (2), no line item formula (1) | date on a weekend (17), number without source (12), missing topic (11), markdown in reply (8), incomplete sum range (5), rather short (5) | 1.2 · 12/57 |
| qwen3.8-flash-medium | 129 | forbidden content (6), missing value (5), foreign script (4), wrong calculation (4), wrong weekday (3), missing topic (2) | number without source (14), date on a weekend (13), incomplete sum range (9), markdown in reply (9), placeholder (6), share over 100 % (5) | 1.1 · 14/57 |

Defects of the content check, the reply and the behavior checks; per label the number of runs. Numbers without source (numbers_sourced): mean per checked file · files with at least one / checked files.

## Per task

| task | claude-haiku-5.5-medium | deepseek-v4-flash-high | gemma-4-31b | gpt-oss-120b-medium | nemotron-3.5-super | qwen3.8-27b-medium | qwen3.8-flash-medium |
|---|---|---|---|---|---|---|---|
| anfrage: Quote for a customer inquiry (attachment) | 2·3·0/3 | 0·3·0/3 | 3·3·0/3 | 3·3·0/3 | 3·3·1/3 | 3·3·0/3 | 2·3·1/3 |
| angebot: Quote calculation | 3·3·3/3 | 2·3·3/3 | 3·3·0/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 | 2·3·2/3 |
| angebotsvergleich: Decision paper from two offers (attachments) | 2·3·3/3 | 3·3·3/3 | 3·3·0/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| anweisung: Work instruction | 3·3·3/3 | 3·3·3/3 | 0·3·2/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 |
| arbeitstage: Question: working days in Excel (no_file) | –·–·3/3 | –·–·1/3 | –·–·3/3 | –·–·3/3 | –·–·1/3 | –·–·2/3 | –·–·3/3 |
| auftragsdaten: Q3 order analysis from an export (attachment) | 1·3·2/3 | 3·3·3/3 | 3·3·0/3 | 2·3·1/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 |
| aushang: Tea kitchen notice (vague) | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 | 3·3·3/3 |
| bahncard: Question with web search: BahnCard (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·2/3 | –·–·3/3 | –·–·2/3 | –·–·2/3 |
| befragung: Employee survey (follow-up) (follow_up) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| budget: Budget | 1·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 | 3·3·3/3 |
| bueromaterial: Office supplies order list (follow-up) (follow_up) | 1·3·3/3 | 3·3·1/3 | 3·3·0/3 | 3·3·2/3 | 3·3·1/3 | 3·3·1/3 | 2·3·3/3 |
| einladung: Christmas party invitation | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 | 3·3·2/3 | 2·3·2/3 | 3·3·3/3 |
| filialumsatz: Branch revenue from an email (copying data) | 2·3·3/3 | 2·3·3/3 | 3·3·0/3 | 3·3·2/3 | 2·3·3/3 | 2·3·2/3 | 2·3·3/3 |
| handbuch: Onboarding handbook (long) | 3·3·3/3 | 3·3·3/3 | 1·3·0/3 | 3·3·0/3 | 3·3·2/3 | 1·3·3/3 | 1·3·3/3 |
| homeoffice: Circular email from a long works agreement (attachment, no file) (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·2/3 | –·–·3/3 | –·–·3/3 | –·–·2/3 |
| inventar: IT inventory list (long) | 1·3·3/3 | 3·3·3/3 | 3·3·0/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| jahresbericht: Slides from a long annual report with correction (attachment) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·2·1/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 |
| konzept: Concept paper | 3·3·3/3 | 2·3·3/3 | 0·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 1·3·2/3 |
| kostenumlage: Allocate building costs (two keys) | 3·3·3/3 | 3·3·3/3 | 0·3·3/3 | 2·3·3/3 | 2·3·2/3 | 2·3·3/3 | 3·3·3/3 |
| kundenantwort: Reply to a complaint (attachment, no file) (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·1/3 | –·–·3/3 | –·–·2/3 | –·–·3/3 |
| leasing: Question: lease or buy (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 |
| mahnung: Payment reminder (overdue only) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| planist: Plan vs. actual per cost centre (follow-up, three rounds) (follow_up) | 2·3·2/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·1/3 |
| praesentation: Presentation | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 0·0·0/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 |
| preisaenderung: Quote with price list and price change (two attachments) | 2·3·3/3 | 1·3·2/3 | 3·3·0/3 | 2·3·1/3 | 3·3·0/3 | 2·3·2/3 | 3·3·3/3 |
| projektplan: Project plan for an office move | 1·3·3/3 | 2·3·3/3 | 2·3·2/3 | 3·3·2/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 |
| projektstatus: ERP project status | 3·3·2/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 |
| protokoll: Meeting minutes | 3·3·3/3 | 2·3·2/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·1/3 | 3·3·3/3 |
| provision: Sales commission statement with tiers and bonus | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| quartal: Quarterly presentation | 2·2·2/3 | 3·3·3/3 | 3·3·3/3 | 2·2·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 |
| reisekosten: Travel expenses | 3·3·3/3 | 2·3·3/3 | 2·3·0/3 | 3·3·3/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 |
| richtlinie: Remote work policy (two change rounds) (follow_up) | 3·3·3/3 | 3·3·2/3 | 1·3·3/3 | 3·3·0/3 | 3·3·1/3 | 3·3·3/3 | 3·3·3/3 |
| rufbereitschaft: On-call rota November/December (holidays, substitute) | 1·3·2/3 | 3·3·3/3 | 1·3·0/3 | 3·3·0/3 | 3·3·1/3 | 3·3·2/3 | 3·3·1/3 |
| rundschreiben: Staff circular | 3·3·3/3 | 2·3·3/3 | 1·3·3/3 | 3·3·3/3 | 2·3·3/3 | 2·3·3/3 | 2·3·2/3 |
| schulung: Phishing training | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 0·0·0/3 | 3·3·3/3 | 1·3·3/3 | 2·3·3/3 |
| servicebericht: Slides from a report (attachment) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 2·3·3/3 | 3·3·3/3 | 2·3·3/3 |
| sparquote: Budget with savings rate (follow-up) (follow_up) | 0·3·1/3 | 3·3·3/3 | 1·3·1/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 | 2·3·1/3 |
| stellenanzeige: Job ad for a service technician (AGG-compliant) | 3·3·3/3 | 3·3·3/3 | 2·3·0/3 | 3·3·2/3 | 3·3·3/3 | 2·3·3/3 | 3·3·3/3 |
| teamnotizen: Minutes from notes (attachment) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 2·3·3/3 | 3·3·3/3 | 3·3·2/3 |
| termin: Calendar entry and an invitation to send yourself (no_file) | –·–·3/3 | –·–·1/3 | –·–·3/3 | –·–·1/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 |
| transkript: Decision minutes from a transcript (attachment) | 3·3·3/3 | 3·3·3/3 | 0·3·0/3 | 3·3·0/3 | 3·3·3/3 | 3·3·2/3 | 3·3·0/3 |
| urlaubsplanung: Vacation planning (vague) | 0·3·2/3 | 2·3·3/3 | 3·3·3/3 | 2·3·2/3 | 3·3·3/3 | 0·3·3/3 | 0·3·2/3 |
| vergleich: Laptop comparison | 2·3·3/3 | 3·3·3/3 | 2·3·2/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 |
| versammlung: Staff meeting (follow-up) (follow_up) | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 | 3·3·3/3 |
| vertrieb: Revenue by region (year-on-year) | 3·3·3/3 | 3·3·3/3 | 3·3·1/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 3·3·3/3 |
| wartungsmail: Server maintenance email (no_file) | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·3/3 | –·–·2/3 | –·–·2/3 | –·–·3/3 |
| wartungsvertrag: Overview of a long maintenance contract (attachment) | 3·3·2/3 | 2·3·1/3 | 1·2·0/3 | 3·3·1/3 | 3·3·3/3 | 2·3·1/3 | 3·3·2/3 |
| workshop: Workshop agenda with times | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·3/3 | 3·3·2/3 | 2·3·3/3 | 3·3·2/3 |
| zeiterfassung: Time sheet with macro request | 0·3·3/3 | 1·3·2/3 | 0·3·3/3 | 3·3·2/3 | 3·3·3/3 | 3·3·3/3 | 1·3·3/3 |
| zeugnis: Employment reference (grade good) | 3·3·2/3 | 3·3·0/3 | 3·3·2/3 | 3·3·0/3 | 3·3·0/3 | 1·3·0/3 | 3·3·0/3 |

Cell: file at 1st call · file at end · success / scored runs (? = success not determinable, e.g. the file of the last call is missing).

## Judge grades

| model | files | tasks | mean (95 %, bootstrap over tasks) | language | content | completeness | structure | usefulness |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5.5-medium | 100 | 50 | 4.30 (4.11–4.47) | 4.59 | 4.07 | 4.43 | 4.36 | 4.03 |
| deepseek-v4-flash-high | 100 | 50 | 4.27 (4.12–4.40) | 4.62 | 4.05 | 4.39 | 4.27 | 4.00 |
| nemotron-3.5-super | 100 | 50 | 4.00 (3.85–4.17) | 4.43 | 3.75 | 4.06 | 4.13 | 3.65 |
| qwen3.8-flash-medium | 100 | 50 | 3.92 (3.74–4.08) | 4.04 | 3.50 | 4.41 | 4.05 | 3.58 |
| qwen3.8-27b-medium | 100 | 50 | 3.91 (3.73–4.08) | 4.02 | 3.47 | 4.28 | 4.24 | 3.52 |
| gemma-4-31b | 100 | 50 | 3.63 (3.45–3.81) | 4.20 | 3.42 | 3.43 | 3.92 | 3.19 |
| gpt-oss-120b-medium | 96 | 48 | 3.57 (3.38–3.76) | 4.20 | 3.15 | 3.52 | 3.90 | 3.08 |

Gap to the next model (paired over shared tasks):

| models | difference (95 %) | p | shared tasks |
|---|---|---|---|
| claude-haiku-5.5-medium − deepseek-v4-flash-high | 0.03 (-0.11 to 0.16) | 0.708 | 50 |
| deepseek-v4-flash-high − nemotron-3.5-super | 0.26 (0.13 to 0.39) | 0.000 | 50 |
| nemotron-3.5-super − qwen3.8-flash-medium | 0.09 (-0.07 to 0.26) | 0.328 | 50 |
| qwen3.8-flash-medium − qwen3.8-27b-medium | 0.01 (-0.16 to 0.17) | 0.929 | 50 |
| qwen3.8-27b-medium − gemma-4-31b | 0.27 (0.09 to 0.46) | 0.006 | 50 |
| gemma-4-31b − gpt-oss-120b-medium | 0.06 (-0.13 to 0.25) | 0.540 | 48 |

Judges: claude-opus-5.5-agent (696 grades). Mean = average of the five criteria (grades 1–5) per file, averaged over judges; estimate = mean over tasks, interval: bootstrap over tasks. Do not mix grades from different judge instructions.

---

Rates: estimate = mean over tasks of the per-task rate, 95 % interval from a cluster bootstrap over tasks (runs of one task are not independent), then the raw count. When the interval has zero width (all values equal), the Wilson interval is added (it treats runs as independent). File columns only count tasks that ask for a file; success counts all. Success = file at end, every turn fulfilled and content ok (no hard defect), plus the reply check and the behavior check where the task has them; without a file: no office call, a final answer with every required topic and nothing forbidden. Not scored: runs that a provider or network failure ended before the outcome was settled, and task runs without a log line. Server errors of the model's own server count as failures. pass^k: chance that k fresh runs of a task all succeed (mean over tasks). Details: docs/scoring.md.
