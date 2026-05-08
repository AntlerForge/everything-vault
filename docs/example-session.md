# Example Session

A realistic, annotated transcript of working with Everything Vault through an LLM. The user is Alex Chen — the fictional persona shipped with the example vault. The agent ("EV") is whichever LLM has the skill installed.

This walks through the most common operations in order: session start, query, ingest, board operation, sweep, and file. Read it once before installing the skill so you know what working with the vault actually looks like.

> 💡 The italicised callout blocks explain what's happening under the hood — which tool ran, what the skill decided, and why.

---

## Session start

**User:** What's on my plate today?

> 💡 The skill is auto-loaded by the LLM platform when the user references "my" — a personal-fact pattern. Before answering, the skill probes for the vault on disk, finds it at `~/Documents/everything-vault/vault/`, and reads every file in `vault/core/`. That's `whoami.md`, `preferences.md`, `active-context.md`, and `key-people.md` — about 600 words total. The skill now knows the user is Alex (freelance dev in Bristol), is mid-kitchen-renovation, has Japanese N4 in July, and is working on the recipe-manager v0.2 release.

**EV:** Three things active right now:

- **recipe-manager v0.2** — import-from-URL polish + duplicate detection. Target tag-and-announce by end of May.
- **kitchen renovation** — week 3 of 8, plumber expected Wednesday.
- **Japanese N4** — exam in July, ~30 min/day Anki review keeping pace.

Today's day-board has the recipe-manager in slot 1 with "polish the error states for malformed URLs" as the next action. Slot 2 is the kitchen reno (next: chase plumber). Want me to pull anything up?

> 💡 The "what's on my plate" phrase routed to a Read primitive, which loaded `core/active-context.md` plus the day-board. The skill noticed the day-board's next-action field was non-empty for slot 1 and surfaced it directly. The user didn't ask for the day-board explicitly — but the skill anticipates that "what's on my plate" answers always benefit from including it.

---

## Query — when does X happen

**User:** When does my car MOT expire?

> 💡 Temporal personal-fact question. The skill runs `python3 skill/tools/query.py --question "car MOT" --vault $EV_VAULT_PATH`.

**EV:** Your car's MOT renewal date is 30 September 2026 — about 4 months away. The article is at `vehicles/car.md`, last verified 2026-04-12, with confidence: high. Provider is the local garage. Cost £65 last time.

> 💡 The query returned `vehicles/car.md` as the top hit (renewal_date field matched, plus "car" and "MOT" keywords in the title and tags). The skill formatted the answer with source attribution, the verification date, and the renewal cost from frontmatter — exactly the pattern in `skill/prompts/query-prompt.md`. If `last_verified` had been more than 6 months old, the skill would have flagged it as potentially stale.

---

## Ingest — capture a new fact + event

**User:** I just signed up for a pottery class, starts next Thursday.

> 💡 The user is sharing a fact (pottery class exists, recurring) plus an event (the signup happened today). The skill runs `ingest.py scan` first to spot any existing articles on the same topic.

**EV:** No existing pottery article — this is new. I'll capture it as:

- **Article:** `hobbies/pottery-class.md` — domains: [hobbies], type: account, schedule: weekly Thursdays 19:00, starts 2026-05-14.
- **Episode:** `episodes/2026/2026-Q2/2026-05-07-pottery-class-signed-up.md` — recording today's enrolment.

Anything to add — name of the studio, class duration, total cost?

**User:** Six-week course, £180 total. Studio is "Bristol Clayworks" near Stokes Croft.

**EV:** Got it. Confirming:

```yaml
title: "Pottery class — Bristol Clayworks"
domains: [hobbies]
type: account
provider: "Bristol Clayworks"
cost: 180
schedule: "Thursdays 19:00, 6-week course starting 2026-05-14"
```

Plus an episode logging today's signup. Going ahead?

**User:** Yes.

**EV:** ✓ Article: `hobbies/pottery-class.md`
✓ Episode: `episodes/2026/2026-Q2/2026-05-07-pottery-class-signed-up.md`
✓ Indexes rebuilt for `hobbies/` and `episodes/`

The class shows up on your timeline and on the upcoming events list.

> 💡 The Write primitive ran twice — once for the article, once for the episode. Then `index_builder.py` rebuilt the affected domain indexes. The skill's principle is "facts in articles, events in episodes" — a single conversation can produce both. Notice the skill *confirmed before writing* — that's a core behaviour from `skill/SKILL.md` § Key behaviours.

---

## Day Board — board operation

**User:** Put the recipe-manager on slot 1.

> 💡 Board slot edit. The skill calls `python3 skill/tools/board.py --vault $EV_VAULT_PATH assign 1 recipe-manager --type project`.

**EV:** ✓ Slot 1 → recipe-manager (project)

The board shows it now. Want me to set the "next" field too? Right now it's blank.

**User:** Yeah, put "polish import error states".

**EV:** ✓ Slot 1 next → "polish import error states"

> 💡 Two small tool calls (`assign`, then `set-field next`). The board.py tool is the only canonical writer for `tasks/day-board.md` — direct file edits are forbidden in the skill's guardrails because the file's slot structure has to stay parseable. The dashboard, if open in a browser, will refresh its day-board view on the next reload — the build script regenerates `ev-data.json` after every board mutation.

---

## Sweep — quick maintenance pass

**User:** Quick EV sweep.

> 💡 "Quick sweep" is a composed workflow. The skill loads `skill/prompts/sweep-prompt.md` for the full flow. The quick variant skips the consolidate pass and runs only: session promotion + active-context delta + stale check + holding-pen check.

**EV:** Three findings:

1. **Stale article:** `health/annual-checkup.md` last verified 2025-11-08 (6 months ago). Want me to flag it for review or update it now?
2. **Active-context drift:** you mentioned "pottery class" today but `core/active-context.md` doesn't list hobbies-in-progress. Want me to add a one-line entry?
3. **Holding pen:** empty. Nothing to triage.

What would you like to action?

**User:** Update active-context with the pottery line. Skip the checkup for now.

**EV:** ✓ `core/active-context.md` updated — added "Pottery class running Thursdays through 2026-06-25 (Bristol Clayworks)".

The stale checkup is parked — I'll re-flag it next sweep. Done.

> 💡 The skill ran `curate.py --stale` (returned the checkup), checked active-context against the session's mentions (caught the pottery class), and ran `curate.py --holding-pen` (came back empty). Findings were presented as a numbered list with proposed actions — the user picked which to apply. The skill never auto-applied — it's read-mostly maintenance, every change confirmed before commit. This is the central principle from SKILL.md § Key behaviours.

---

## File — bring in an external document

**User:** File this PDF.

*[User drags renovation_quote_revised.pdf into the chat]*

> 💡 The File primitive lands a copy of the original in `vault/sources/YYYY/`, writes a sidecar `.meta.yaml`, then synthesises a Wiki article that links back via `source_ref`. The skill loads `skill/prompts/file-prompt.md` and runs `file_handler.py --summarise <path>`.

**EV:** Summarised. This is a revised renovation quote dated 2026-05-07 from Riverside Builders — total £19,200, up from £18,000 in the original quote. Itemised: tiling +£800, plumbing +£400.

I'll do this:

1. Copy the PDF to `sources/2026/2026-05-07-renovation-quote-revised.pdf`
2. Write a sidecar `.meta.yaml` (origin: pdf, sensitivity: normal)
3. Update the existing `finance/renovation-budget.md` article — add the new quote total, add a Change History row recording the +£1,200 revision
4. Episode: `episodes/2026/2026-Q2/2026-05-07-renovation-quote-revised.md`

Going ahead?

**User:** Go.

**EV:** ✓ `sources/2026/2026-05-07-renovation-quote-revised.pdf`
✓ `sources/2026/2026-05-07-renovation-quote-revised.meta.yaml`
✓ `finance/renovation-budget.md` updated, Change History row added
✓ `episodes/2026/2026-Q2/2026-05-07-renovation-quote-revised.md`
✓ Indexes rebuilt for `finance/` and `episodes/`, plus `sources/_index.md`

Total renovation budget is now £19,200 (was £18,000). Spent so far is still £6,400, so remaining rises to £12,800.

> 💡 The File primitive demonstrated the three-tier model in action. The original PDF lives in Source — it's never edited. The Wiki article (`renovation-budget.md`) was *updated*, not duplicated, with a Change History row recording the delta. The episode marks the event of receiving the revised quote. If the user later wonders "when did the quote change?", the episode answers; if they ask "what's the current budget?", the article does.

---

## Closing the session

**User:** Thanks. End of day in a couple of hours — anything I should clear before then?

**EV:** Slot 4 still has T001 (recipe-manager import flow) but no progress noted today. If you want to flush slot 1's recently-done into the article before the 18:00 work-log scheduled task fires, I can do that now. Otherwise the work-log will pick up everything from today's episodes and the board state automatically.

**User:** Flush slot 1.

**EV:** ✓ `projects/recipe-manager.md` — appended Progress Log entry for 2026-05-07 with today's recently-done items. Slot 1's recently-done cleared. The 18:00 work-log will see fresh activity for the recipe-manager.

> 💡 The flush is a Day Board operation that calls the dashboard server's `/board/flush-to-article` endpoint, which appends the slot's `recently_done` items into the article's `## Progress Log` section, dated. This is the bridge between the Scratch tier (day-board) and the Wiki tier (project article) — captured progress now lives durably. The 18:00 scheduled task will read the day's episodes and work-log entries to compose the structured work-log for today; with the flush done, the recipe-manager's project status engine has clean signal.

---

## What you just saw

- **Session start.** Vault probe, core memory load, contextual answer.
- **Query.** Personal-fact question → query.py → sourced answer with confidence and verification date.
- **Ingest.** Article + episode written from a single conversation, with confirmation before commit.
- **Board.** Two small tool calls to assign a project and set its next-action field.
- **Sweep.** Composed workflow surfacing findings, user picks what to action, skill applies only what's approved.
- **File.** External document landed in Source, synthesised into Wiki, episode created — three-tier model in one operation.

Everything was a small, transparent tool call. The user spoke casually; the skill kept the work-track structured. The vault now has six new artefacts (article, two episodes, source file, sidecar, updated article body) and the day-board is in a clean state for the end-of-day work-log.

This is what the system feels like once it's installed and the vault has shape. The first week is mostly capturing things; after that you spend more time querying than writing, because the LLM remembers what you wrote down.
