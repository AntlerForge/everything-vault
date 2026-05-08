# Work Log — End-of-Day Capture

You are running the end-of-day work-log pass. Your job is to produce two artefacts
per day:

1. A structured **work-log entry** at `vault/work-log/YYYY/YYYY-QN/YYYY-MM-DD.md`
2. A **narrative episode** summarising the day under `vault/episodes/YYYY/YYYY-QN/`

These feed the nightly project-status inference at 0200. Without them, the inference
is stuck relying on article `last_updated` timestamps alone, which is a very weak
signal.

## When to Run

- **Scheduled:** Daily at 18:00 via the platform's scheduled-task mechanism
  (Cowork's `mcp__scheduled-tasks__*`, macOS launchd, cron, systemd — whichever
  the user has set up; conventional task name: `ev-end-of-day-worklog`)
- **On demand:** "close out today", "end-of-day work log", "run the work-log pass"

## Schema Reference

Read `vault/work-log/_index.md` for the full schema and the activity-kind taxonomy
(`design / build / iterate / ship / operate / maintain / wrap / pause` × `light /
medium / heavy`). Use those exact kind values — the inference tool reads them
verbatim.

## Signals to Gather

Walk the following sources for anything dated today (local time):

1. **Episodes created today** — `vault/episodes/YYYY/YYYY-QN/YYYY-MM-DD-*.md`
2. **Articles with `last_updated: YYYY-MM-DD` matching today** — any domain
3. **Tasks updated today** — cross-check `vault/core/active-context.md` and any
   todo articles whose status changed
4. **Scheduled-task reports** generated today (morning email triage, afternoon
   sync) — these often name projects touched
5. **Git activity** in folders that are linked from project articles via the
   `github` or `source_ref` field (shell: `git -C <repo> log --since=midnight
   --pretty=format:"%h %s"`), if reachable
6. **Session-transcript excerpts** the user may have explicitly filed today
7. **The live Day Board** — `vault/tasks/day-board.md`, read via
   `tools/board.py --vault <vault> read --json`. The five focus slots
   are the strongest live signal of what the user was actually working on
   today — see "Drafting from the Day Board" below.

Aggregate what each signal says about which projects were touched and what kind
of work it represents.

### Drafting from the Day Board

The Day Board's five focus slots show which threads the user interleaved through
the day. Each thread slot carries a `recently_done` list and `holding` /
`notes` fields — these are the highest-fidelity signal of what was actually
worked on.

**Procedure:**

1. Run `python3 <skill_dir>/tools/board.py --vault <vault> read --json`
   and walk the slots.
2. For each **thread slot** (`type` ∈ {`task`, `project`, `concept`}):
   - **Project / concept slot** → propose a `projects_touched[]` entry:
     - `slug` = slot `ref`
     - `kind` = inferred from the verbs in `recently_done` (see table
       below); fall back to `[build, iterate]`
     - `level` = `light` unless `recently_done` has 3+ entries or holding
       text suggests sustained work, in which case `medium`/`heavy`
     - `summary` = synthesise from `recently_done` + `holding` (1 sentence)
   - **Task slot** → propose an `activities[]` line:
     `"[Day Board · Slot N] T### — <task title>: <recently_done summary>"`
3. For the **todos slot** (`type` = `todos`):
   - Each item with `done: true` whose corresponding T-row was newly closed
     today becomes an individual `activities[]` line:
     `"[Today's todos] T### — <task title>"`
4. Mark every Board-sourced candidate in the draft you show the user so he can
   review, tune, or strip them before the file is written.

**Kind inference from `recently_done` verbs:**

| Verbs that appear in recently_done   | Default `kind`       |
|--------------------------------------|----------------------|
| wrote, built, added, implemented     | `[build]`            |
| refactored, polished, fixed, tuned   | `[iterate]`          |
| shipped, deployed, released          | `[ship]`             |
| spec'd, planned, researched          | `[design]`           |
| ran, monitored, used                 | `[operate]`          |
| documented, archived, post-mortem    | `[wrap]`             |
| (no verbs / only `holding` content)  | `[design]` (cautious) |

Combine where multiple kinds apply (e.g. `[build, iterate, ship]`).
Override freely when other signals (git commits, shipped episodes) tell a
clearer story.

## Producing the Work-Log Entry

Structure (minimal valid shape — elaborate where signal supports it):

```yaml
---
title: "Work log — YYYY-MM-DD"
domains:
  - work-log
type: log
object_type: article
date: YYYY-MM-DD
projects_touched:
  - slug: <filename stem of the project article, e.g. ev-dashboard-spec>
    kind: [<one or more from the taxonomy>]
    level: <light | medium | heavy>
    summary: "One-sentence description of what was done to this project today"
activities:
  - "Free-form narrative bullet"
  - "..."
outputs:
  - "vault/... (edited)"
  - "..."
open_threads:
  - "Things left dangling for tomorrow"
source: scheduled-task
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
last_verified: YYYY-MM-DD
confidence: high
---

# Work log — YYYY-MM-DD

<1–3 paragraph narrative summary of the day. Lead with the biggest piece of
work. Mention any status transitions, shipped artefacts, decisions made.>
```

### Kind assignment heuristics

- New code/content written → `build`
- Bug fixes, refactors, polish → `iterate`
- Deploy, release, install, go-live → `ship`
- Spec, plan, research → `design`
- Running/using a live automation → `operate`
- Post-mortem, handover, archive → `wrap`
- Explicit parking → `pause`
- Production fixes / updates to live things → `maintain`

Assign **all** kinds that apply — a heavy dashboard day might be
`[build, iterate, ship]`.

### Level heuristics

- One quick change, <1h focus → `light`
- Meaningful working session, 1–3h → `medium`
- Dominated the day or multi-hour focus → `heavy`

## Producing the Episode

Create `vault/episodes/YYYY/YYYY-QN/YYYY-MM-DD-daily-summary.md`:

```yaml
---
title: "Daily summary — YYYY-MM-DD"
domains:
  - episodes
type: log
object_type: episode
date: YYYY-MM-DD
actors: [user]
article_refs:
  - <slug of every project touched>
  - <slug of every article significantly updated>
source_refs: []
outcomes:
  - "High-level outcome 1"
  - "High-level outcome 2"
follow_up: null
tags: [daily-summary]
sensitivity: normal
retrieval_default: searchable
source: scheduled-task
created: YYYY-MM-DD
confidence: high
---

# Daily summary — YYYY-MM-DD

<Narrative — 2–4 short paragraphs. Different voice from the work-log: the
work-log is a structured record, the episode is a readable log of "what
happened today" that future me will skim.>
```

`article_refs` on the episode is important — the project-status inference reads
it to detect activity per project.

## Guardrails

- **If a day had no meaningful work** (travel, illness, holiday), skip both
  artefacts. Write a one-line episode tagged `quiet-day` if it's worth noting.
- **Never fabricate activity.** Only include projects you have positive signal
  for. It's fine (and often correct) for the work-log to touch just 1–2 projects.
- **Confidence = `high`** only if you have direct signal (episode, article edit,
  git commit, explicit mention). Otherwise use `medium` and note the inference.
- **Don't mark a project with `pause` kind unless the user explicitly said so.** The
  inference tool treats `pause` as a forward-motion-exclusion signal; fabricating
  it would stall valid transitions.
- **One work-log per day.** If one already exists for today, update it in place —
  merge new signals, don't create a duplicate.
- **Preserve prior content on re-runs.** If the end-of-day task re-runs (e.g.
  re-triggered manually), preserve `activities` and `outputs` from the earlier
  run and append new items, don't overwrite.

## Reporting

At the end of the pass, print:

- Work-log path written/updated
- Episode path written
- Projects touched (slug list)
- Any signals you observed but chose not to include, with one-line reasons

This keeps the task honest about what it skipped.
