# Open issues

Known gaps and design limits of the benchmark. They do not make the numbers wrong, but they say what the numbers
mean and where a single defect or a single rate should be read with care. Check names are those of
docs/task-format.md.

## What is measured

- **Model + tool + harness.** A result belongs to the combination of the model, this particular office tool (the
  vendored Open WebUI tool "Office Documents", docs/harness.md) and this harness (system prompt, attachment
  template, round limit). It does not measure Open WebUI itself, and it does not say how well a model writes office
  files with another tool, another schema or code execution.
- **Neutral attachment template.** Open WebUI's default RAG template asks the model to cite sources with markers
  like `[1]`, and models then also write those markers into documents and e-mails. The harness deliberately puts
  attachments in front of the message without any citation instruction. In an Open WebUI instance with the default
  template, models will produce such markers more often than here.
- **Percent columns of the tool.** The tool's spec says for a `percent` column "12.5 means 12.5 %" and stores the
  value as 0.125, as Excel does. It does not say that formulas then see 0.125. In `anfrage` (version 2, which asks
  for formulas) this goes wrong in two ways: models send 5 and write `(1-F2/100)` in the formula, or they send 0.05,
  which the tool turns into 0.05 %. Both give a discount of 0.05 % instead of 5 % and a wrong net total; only 2 of
  21 runs got net and gross right. The first way is a gap in the tool's description, the second a model error
  against it. The vendored tool is kept unchanged, so the task measures this as it would happen to a user; a
  sentence in the tool's spec ("formulas see 0.125, do not divide by 100") would probably remove most of it.
- **Saturated tasks.** About a third of the tasks are solved by all strong models in every run. They test the
  basics (a valid call, a correct simple table, a plain letter) and still separate weak setups from working ones;
  the differences between strong models come from the rest. A difference in overall success between two strong
  models comes from roughly two thirds of the tasks.
- **Quality grades.** The quality grades in the published results come from Claude Opus 5.5 agent sessions: the
  same prompt as the API judge (`obench judge --export` / `--import`), with the ability to check calculations with
  scripts. Grades from an API judge differ from these and from each other; the calibration is in docs/judge.md.
  Grades from different judges should not be compared directly.

## Heuristics and probable false alarms

- **`numbers_sourced` is a heuristic and a lower bound.** It cannot know which numbers a model invented; it reports
  numbers that neither appear in the source nor follow from it by one simple step. The more numbers a paragraph of
  the source has, the more numbers count as derivable by chance. In a sample with eleven invented figures inserted
  into the reference solutions, it reported only 5 to 6 in `vertrieb` and `mahnung` (dates, times, phone numbers,
  large amounts), 9 in `teamnotizen` and 11 in `zeugnis`. Read the metric "numbers without source" as a lower
  bound. It also errs the other way (soft defects only):
  - multi-step calculations are not derived: in `anfrage`, 3 of 18 files have 1 to 3 amounts of the form
    6 × 1.149 × 0,95 that are reported as without source;
  - sums of a group out of many numbers (a SUMIF result written as a constant; `auftragsdaten` has over 60 numbers
    in the source) are reported as without source; as formulas they are not checked;
  - deadlines in words ("in drei Wochen", "sechs Monate vor Ablauf") are not computed. `stellenanzeige` and
    `wartungsvertrag` are built so that the correct date is sourced anyway ("in zwei Wochen" lies within reference
    date ± 14 days; an attachment names the month of the correct date).
- **`total_row` looks only at the first sheet.** The same holds for `line_item_formula` and `data_rows_min`. In
  `kostenumlage`, one real run put a parameter sheet first; its total row was correct on the second sheet and was
  reported as a hard "no total row". Probably a false alarm.
- **`formula_empty` flags deliberately empty formulas.** A formula such as `=IF(…;"";…)` that leaves a cell empty
  on purpose is reported as a hard "formula without result". In `bueromaterial`, one real run built a column that
  only calculates in the total rows; the values were right. Probably a false alarm.
- **`share_over_100` does not exclude Diff/Plan/Soll/Ist/vs.** The original checker meant to skip columns whose
  header contains these words, but its pattern never matched them. The check is kept identical to the original on
  purpose, so verdicts stay comparable with earlier runs: a percent column "Anteil Plan" or "Quote Ist" is checked
  like any share column (with the words excluded as
  plain substrings, headers such as "Anteil verplant" or "Quote Liste" would no longer be checked either).
- **Placeholders.** The placeholder check does not yet know many words in square brackets, e.g. "[Raum]",
  "[Gebäude/Etage]", "[z. B. 20 %]", "[Pfad/Ablage]".

Changes to these checks should first be tried on tasks that are not part of the published set, so that published
numbers do not shift.

## Missing checks

Points that tasks would need but no check covers yet. Until there is one, they are in the task's `[judge]`
checklist (blind review) or approximated.

| Missing | Where it matters | Workaround now |
|---|---|---|
| chart texts (axis titles, series names, categories) in the text that `topics` sees | `praesentation`: "Stunden pro Woche" often appears only as the unit in the chart and cannot be checked as a topic | judge checklist only |
| arguments of extra tools in `[behavior]` (e.g. date and attendees of a calendar event) | `termin`: whether the event is on Thursday 22.10.2026, 14:00–15:30, and whether the person who should not get a system invitation is left out of the attendees is only visible in the log | judge checklist; the date is checked by `[reply] topics` in the invitation text |
| text produced by formula cells (`=IF(…;"über Plan";"im Rahmen")`) in the text of an xlsx for `topics`/`count`; today only text constants count | `planist`: a rating column could only be checked if the model wrote text instead of a formula | `planist` asks for a percentage column instead (`calculations`) |

## Mutants the checks miss

`tasks/*/mutants.toml` holds 202 broken variants of the reference solutions, each with one typical model error
(docs/mutants.md). The content check catches 186. The other 16 are marked `gap` and run as strict xfail: the test
fails as soon as a check catches one. Three are left open on purpose, because a check would raise false alarms on
real runs or demand more than prompt and checklist do (`angebotsvergleich` / `installation_invented`,
`bueromaterial` / `cost_centre_totals_as_constants`, `handbuch` / `sick_note_from_third_day`); the others need a
new check. Defect and reason as in the files:

- **`angebotsvergleich` / `installation_invented`**: delivery and installation in the table at €725.00 instead of €350.00. Expected check: `numbers_sourced`.
  numbers_sourced is not enabled for angebotsvergleich, values_present only checks the final totals. With numbers_sourced = true, 725 would have no source, but the check (trial on 19.10.2026) flagged correct numbers in almost all 30 real runs: calculations over three steps (7,000 × €0.008 × 36 = €2,016), the correct final totals €15,066 and €14,792 and the difference €274. The task calculates too much for „jede Zahl aus dem Auftrag kommt“; values_present with 350 does not help either (the real run mentions 350 elsewhere). Fix: numbers_sourced would have to derive products of three numbers and sums of sourced numbers in the file.

- **`bueromaterial` / `cost_centre_totals_as_constants`**: totals per cost centre as fixed values 311 and 413.20 instead of SUMIF. Expected check: `formulas_min`, `calculations`.
  The values are right, and the task only checks the line item formula and the total row; only numbers_sourced reports 311 and 413.20 softly as „ohne Beleg“, by chance (the heuristic does not check sums of a selection). Caught by: formulas_min (reference 11 formulas, here 9) or a check that sums per group are formulas, e.g. `groups` with an option requiring the target values to be formulas; more robust: change quantities, recalculate and compare the group sums against the list (like the change-robustness check of the blind review). Deliberately left open: prompt and checklist ask for the sum per cost centre only „am besten mit SUMMEWENN“, i.e. not necessarily as a formula; a hard formulas_min = 10 would hit three real runs with correct fixed values.

- **`handbuch` / `sick_note_from_third_day`**: medical certificate required from the third calendar day (correct: on the fourth at the latest). Expected check: `topics`.
  A legal rule that no check key sees; only the blind review does. Caught by a forbidden pattern like 'ab dem (dritten|3\.) (kalender)?tag' (or topics 'vierten|4\. (kalender)?tag'). Deliberately left open: the checklist says „spätestens ab dem vierten Kalendertag“, and the employer may ask for the certificate earlier (§ 5 Abs. 1 Satz 3 EFZG); „ab dem dritten Tag“ as a company rule (about 25 real runs) is therefore not a sure error, and a topics pattern would also have to allow „länger als drei Tage“ or „ab dem ersten Tag“.

- **`inventar` / `empty_employee_cells`**: three devices without an assigned employee (empty cells). Expected check: `empty_table`.
  empty_table only checks Word and slide tables. Would catch it: an xlsx check for empty cells in data rows of text columns that are filled everywhere else (soft).

- **`schulung` / `partial_year_not_marked`**: category „2026*“ without explanation: nowhere on the slide does it say that 2026 only counts up to September. Expected check: `topics`, `chart_values`.
  chart_values checks only the values, not the categories; a topic 'bis (ende )?sep|jan.{0,4}sep|bis 30\.0?9' on the slide text without notes (or on the chart categories) would find the missing marking (the notes say „bis Ende September“, so a topic on the whole text is not enough)

- **`schulung` / `doubled_instead_of_tripled`**: note: rise from 45 to 130 „fast verdoppelt“, actually 2.89 times. Expected check: `text_arithmetic`.
  text_arithmetic checks only written-out calculations (a × b = c, total rows); factor words like „verdoppelt/verdreifacht“ between two numbers of a paragraph (von 45 … auf 130) are checked by nothing

- **`servicebericht` / `target_invented`**: invented target „Erstlösungsquote 83 % bis Ende 2027“, not in the report. Expected check: `numbers_sourced`.
  numbers_sourced considers almost every two-digit number derivable: the report has paragraphs with many numbers (topics 34/22/18/15/11 %, key figures) whose partial sums, differences and percentage changes give 78, 80, 83, 87, 93 …; invented percentage targets thus go undetected (partial sums and percentage pairs only for numbers of the same unit, or only when the sentence in the file refers to the same thing)

- **`sparquote` / `amounts_reinvented`**: file rebuilt in the follow-up, income and expenses of every month invented anew. Expected check: `retained`.
  retained counts units (texts and constants once each): months and headers stay, all nine distinct amounts are missing, that is 55 % retained and only soft (hard below 50 %). Fix: judge number constants in xlsx separately (e.g. hard when fewer than half of the previous file's numbers come back) or the task sets values_present with the amounts of the first version

- **`teamnotizen` / `meeting_time_invented`**: invented time 10:00 for the meeting on 12.10. (10 o'clock only applies to the next meeting). Expected check: `numbers_sourced`.
  numbers_sourced only checks whether the time appears anywhere in the source (next team meeting at 10 o'clock), not in which context; only matching time and date of the same occurrence could catch it

- **`transkript` / `ad_missing_from_tasks`**: task „Anzeige im Amtsblatt aufgeben, bis Mo 02.11.“ missing from the task table. Expected check: `topics`.
  The topic „Anzeigenschluss 02.11.“ already matches the decision text under advertising; nothing checks whether every deadline is also a row of the task table (extension: restrict topics to a table, e.g. topics_table)

- **`urlaubsplanung` / `calendar_days_not_workdays`**: days = to − from + 1 counts calendar days including weekends and public holidays (Ben 22.03.–02.04.2027: 12 instead of 8). Expected check: `workdays`.
  no check recounts the workdays between from and to; calculations only knows + - * / (would need a function like workdays(from, to) or NETWORKDAYS in calculations.formula, then as [[checks.calculations]] with columns from/to/days)

- **`urlaubsplanung` / `plan_in_the_past`**: vacation plan for 2026: seven of nine vacations lie before 13.10.2026 and are still requested/planned. Expected check: `past_dates`.
  past_dates only checks with dates_from; the vague task does not set it (vacation in January 2026 can also be a review in October). Fix: dates_from = 2026-10-13 only for rows with status planned/requested, or soft when all dates lie before the reference date

- **`vertrieb` / `hagemann_revenue_invented`**: invented Hagemann revenue „≈ 45 Tsd. € im Jahr (geschätzt)“ on the Süd slide. Expected check: `numbers_sourced`.
  45 counts as sourced because two numbers of the prompt happen to give 45 (663 − 618, Süd 2026 minus West 2026); differences across different regions and years can almost always be found among ten revenues. Fix: pairs only from numbers that stand next to each other in the prompt (value pair per region), or report numbers marked „geschätzt/≈“ separately

- **`workshop` / `brainstorming_end_time_wrong`**: brainstorming „11:20–12:20“ with „70 Min.“: the end time matches neither the duration nor the start of lunch. Expected check: `topics`, `text_arithmetic`.
  The topics only require that each time appears somewhere (12:30 is there at lunch); nothing checks whether in an agenda table end − start = duration and each block starts where the previous one ends (extension of text_arithmetic for time spans „hh:mm–hh:mm“ with „n Min.“ in the same row)

- **`workshop` / `total_duration_wrong`**: organisation slide: „Beginn 9:00 Uhr, Ende 16:30 Uhr, insgesamt 6 Stunden 40 Minuten“, actually 7.5 hours (6 hours without breaks and lunch). Expected check: `text_arithmetic`.
  text_arithmetic only recognises calculations that are written out; a duration in hours and minutes next to a time span „von 9:00 bis 16:30“ in the same sentence is not recalculated

- **`zeiterfassung` / `day_fraction_without_time_format`**: working time as a fraction of a day without time format: 0.33 per day and total 7 instead of 8 or 168 hours. Expected check: `column_format`, `values_present`.
  column_format only knows percent/date/euro, no hours or [h]:mm format; values_present is not set (and would have to accept 7 as an [h]:mm value). Fix: a column_format kind „hours“ (time format [h]:mm or decimal hours, i.e. values > 1 for 8-hour days) for 'arbeitszeit|stunden'
