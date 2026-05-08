---
name: everything-vault
description: >
  Personal knowledge vault — the default starting point for anything about the
  user's life. For ANY question about the user's personal world, query the vault
  BEFORE reasoning from scratch or filesystem-grepping. Covers: health, family,
  finance, vehicles (MOT, insurance, renewals), household, work, pets, hobbies,
  holidays, legal, IT setup, purchases, ideas/concepts/projects, skills catalog,
  episodes, todos, the vault dashboard, and LLM/AI tooling selection. Trigger when
  the user mentions EV, vault, or the dashboard; asks "what's on my plate",
  "what's coming up", "remind me", "when does/what's my/where is X"; references
  family, their GP, their car, MOT, their house, their work, or any named
  person/thing likely in the vault; shares a fact, event, idea, or observation
  worth keeping; asks about todos, appointments, renewals; requests a sweep;
  asks which LLM or AI model to use for a task. Guardrail — never filesystem-grep
  the user's personal content; use query.py and the domain map first. Ideas are
  first-class — capture thinking aloud.
---

# Everything Vault — SKILL.md

## EV in 60 seconds

The Everything Vault is the user's structured personal knowledge base — markdown
files with YAML frontmatter in a folder hierarchy. It holds articles across life
domains, plus dated episodes, daily work logs, raw source material, and a focus
board. The vault is platform-independent: the data works with any LLM that can
read markdown.

An agent operates the vault using **five primitives**:

1. **Read** — query the vault, load articles, search episodes
2. **Write** — create or update articles, episodes, work-log entries
3. **Maintain** — curate, consolidate, validate, index
4. **File** — bridge external documents into the vault (Source tier + synthesised article)
5. **Execute** — launch tools (dashboard, project-status inference, board ops)

Higher-level workflows like **Sweep**, **Work Log**, **Day Board**, and **Project
Status** are pre-composed sequences of these primitives, named so the user can
invoke them in one phrase.

**Companion documents:**

- `SCHEMA.md` — the data contract: frontmatter, domain map, naming, sensitivity. Read
  whenever shape questions come up. Platform-independent.
- `PLATFORM-<name>.md` — host-specific plumbing (vault probing, dashboard launch,
  install/update, voice inbox wiring). One file per supported platform. Read only
  the one matching the active host:
  - `PLATFORM-CURSOR.md` — Cursor, Codex CLI, VS Code with MCP, similar IDE-style hosts
  - `PLATFORM-CLAUDE.md` — Claude Code, Cowork
  - Other platforms: write a sibling file mirroring the structure of these two.
- `CHANGELOG.md` — version history. Not auto-loaded.

**Per-capability detail** lives in `prompts/*.md` (one file per prompt), loaded on
demand by name. The prompts are platform-independent — anything platform-specific
they reference (a notes inbox, a scheduler) defers to `PLATFORM-<name>.md`.

**Platform neutrality is a design principle, not an accident.** This SKILL.md, the
SCHEMA.md, the prompts, and the Python tools work with any LLM that can read
markdown and follow instructions. The PLATFORM-*.md isolation ensures none of the
core behaviour assumes a particular host.


## Session start

Two steps, in order:

1. **Ensure vault access.** Probe for the vault on disk. If not found, follow the
   current host's access procedure in the matching `PLATFORM-<name>.md`. Hosts
   currently bundled: `PLATFORM-CURSOR.md` (Cursor, Codex CLI, VS Code, similar
   IDE-style hosts) and `PLATFORM-CLAUDE.md` (Claude Code, Cowork). For hosts
   without a bundled file, fall back to checking `EV_VAULT_PATH` and the common
   default locations (`~/Documents/everything-vault/vault/`, `~/everything-vault/
   vault/`).
2. **Load core memory.** Read every file in `vault/core/`:
   - `whoami.md` — identity and key details
   - `preferences.md` — how the user likes things done
   - `active-context.md` — current priorities and things in flight
   - `key-people.md` — important people in the user's life

   Always-load is an *instruction*, not magic — read these, then proceed.


## The five primitives

### READ — query the vault

**When:** The user is asking a question. Before saying "I don't know", search the
vault. Even when they don't mention the vault, check first if it's a personal-fact
question.

**Tools:**

```bash
python3 <skill_dir>/tools/query.py --question "<question>"
python3 <skill_dir>/tools/query.py --episodes --question "<question>"   # temporal
```

**Quick flow:**

1. Load core memory if not already loaded this session
2. Run `query.py`. For temporal questions ("when did I…", "what happened with…")
   pass `--episodes` first
3. If results found: answer with **source attribution**, **confidence/staleness note**,
   and **sensitivity flag**
4. If no results: say so, offer to capture the answer if the user provides it

**Read for full strategy:** `prompts/query-prompt.md`.

**Special reads:**
- Day Board: `tools/board.py read --json` (see *Composed: Day Board* below)
- Skills catalog: read `vault/skills-catalog/_index.md` first, then per-skill `README.md`

**Guardrails:**
- **Never filesystem-grep the user's personal content.** The vault knows where things
  are — use `query.py` and the domain map first.
- Surface staleness: flag `last_verified` > 6 months or `renewal_date` past.
- Respect sensitivity (see `SCHEMA.md` § Sensitivity Model). Never surface
  `credential` items unless explicitly asked. Flag `sensitive` items when citing.


### WRITE — create or update articles, episodes, work-log entries

**When:** The user is sharing facts, events, or thinking. Even without "save this",
proactively offer to capture if it's the kind of thing they'd want to look up later.

**Tools:**

```bash
# Article
python3 <skill_dir>/tools/ingest.py write    [...flags]

# Episode
python3 <skill_dir>/tools/ingest.py episode --vault <vault> --date YYYY-MM-DD --title "<title>"

# Pre-write conflict scan
python3 <skill_dir>/tools/ingest.py scan --vault <vault> --query "<key topic words>"

# Post-write ripple scan (find articles affected by new info)
python3 <skill_dir>/tools/ingest.py --vault <vault> ripple --source <article_filename.md>

# Work-log entry (end-of-day)
# (handled by the Work Log composed workflow below)
```

**Quick flow:**

1. Identify what's being shared (facts vs. event vs. thinking)
2. Run `ingest.py scan` to spot existing articles on the same topic
3. Determine domain(s) from `SCHEMA.md` § Domain Map
4. **Check for conflicts** — if new info contradicts existing, route to
   *Composed: Conflict Resolution*. Don't silently overwrite.
5. Create or update the article with `ingest.py write`
6. **If a real-world event occurred**, also create an episode
7. **If a time-varying fact changed**, append to that article's `## Change History` table
8. Run `ingest.py … ripple` to find articles affected by the new info
9. Rebuild indexes: `python3 <skill_dir>/tools/index_builder.py <domain>`
10. Confirm: `✓ [Title] → [domain(s)]`

**Read for full guidance:** `prompts/ingest-prompt.md`, `prompts/episode-prompt.md`.

**Key behaviours:**
- **Always confirm before writing.** Summarise the proposed change; let the user
  correct before committing.
- **Prefer updating over creating.** Enrich an existing article rather than spawn a
  duplicate.
- **One copy of everything** (sole exception: install bundles in `skills-catalog/<slug>/install/`).
- **When unsure of domain, use `holding-pen/`.** Tell the user.


### MAINTAIN — curate, consolidate, validate, index

**When:** The user asks "review", "clean up", "what needs attention", "what
patterns", "anything converging?", or after a heavy ingestion session.

**Tools:**

```bash
# Curate (find work)
python3 <skill_dir>/tools/curate.py --stale
python3 <skill_dir>/tools/curate.py --holding-pen
python3 <skill_dir>/tools/curate.py --gaps
python3 <skill_dir>/tools/curate.py --validate
python3 <skill_dir>/tools/curate.py --sensitivity-audit

# Consolidate (synthesis)
python3 <skill_dir>/tools/consolidate.py --vault <vault> --check all

# Indexes
python3 <skill_dir>/tools/index_builder.py <domain>
```

**Curate flow:** run the relevant scan, present findings, ask the user what to action.

**Consolidate flow:** run the synthesis pass, present findings conversationally
(convergence, orphan episodes, resolved tasks, missing links, stale concepts), propose
an action per finding, wait for approval, execute, rebuild indexes.

**Read for full guidance:** `prompts/curate-prompt.md`, `prompts/consolidation-prompt.md`.

**Key behaviour: read-mostly.** Surface findings, propose, let the user decide. Never
auto-merge, auto-delete, or auto-rewrite core memory.


### FILE — bridge external documents into the vault

**When:** The user uploads a document, says "file this", "add this to the vault",
"what's in this PDF".

**Tools:**

```bash
python3 <skill_dir>/tools/file_handler.py --summarise <path>
```

**Quick flow:**

1. Read / summarise the document
2. **Land the original in the Source tier:** copy to
   `vault/sources/YYYY/YYYY-MM-DD-<short-slug>.<ext>` and write a sidecar
   `.meta.yaml` (see `SCHEMA.md` § Source tier)
3. Suggest domain, title, key facts extracted
4. On the user's approval: WRITE a synthesised article with `source_ref` pointing into
   the Source tier
5. **If the document marks an event** (submission, receipt, confirmation), also create
   an episode
6. Don't move the original off-disk unless explicitly asked
7. Rebuild indexes (including `sources/_index.md`)

**Read for full guidance:** `prompts/file-prompt.md`.

**Why land the original?** Synthesised articles carry one agent's interpretation.
Keeping the source means future re-synthesis with a better model is always possible,
and verification is one click away. See `SCHEMA.md` § Three tiers.


### EXECUTE — run side-effecting tools

**When:** The user asks the agent to *do* a thing — open the dashboard, refresh project
status, edit a board slot, install a skill.

**Common executes:**

| Phrase | Action |
|--------|--------|
| "Open the dashboard" / "refresh the dashboard" | Dashboard launcher (see active platform doc) |
| "Run a project-status pass" | `project_status.py` (see *Composed: Project Status*) |
| "Put X on slot N" / board edits | `board.py` (see *Composed: Day Board*) |
| "Install / update this skill" | Platform-specific install (see active platform doc) |

Execute is the layer where platform-specific calls happen. The primitive itself is
agent-neutral; platform hooks live in `PLATFORM-<name>.md`.

**Guardrails:**
- **Never run write-mode tools on demand without explicit consent** (e.g.
  `project_status.py --apply` is reserved for the nightly scheduled task).
- Confirm to the user with the tool's own output (the helpers print `✓` lines —
  surface those, don't synthesise).


## Composed workflows

These are pre-composed sequences of the five primitives, named so the user can
invoke them in one phrase.

### Sweep

**Trigger phrases:** "EV sweep", "run a sweep", "sweep the vault", "quick sweep",
"deep sweep", "sweep concepts", "sweep last week", "sweep inbox".

**Composition:**

1. Voice inbox sweep (READ + WRITE — see active platform doc; skip silently if
   unavailable)
2. Session Promotion for the current conversation (offer to capture session items)
3. Active-context delta — propose edits to `core/active-context.md` if priorities shifted
4. Conflict sweep — adjudicate contradictions surfaced this session
5. MAINTAIN: curate pass (stale, holding-pen, gaps, validate, sensitivity audit)
6. MAINTAIN: consolidate pass (convergence, orphans, resolved tasks, missing links,
   stale concepts)
7. Rebuild indexes for touched domains
8. Present a grouped report with a numbered list of proposed next actions
9. WRITE: record the sweep as an episode under `episodes/YYYY/YYYY-QN/`

**Scope variants:**

- *Default:* session-aware full sweep
- *Quick sweep:* session + active-context + stale + holding-pen only (skip consolidate)
- *Deep sweep:* full + flag autoresearch candidates (never auto-run)
- *Domain-scoped* ("sweep concepts"): curate + consolidate limited to that domain
- *Time-scoped* ("sweep last week"): stale/orphan/holding-pen limited to that window
- *"Sweep inbox":* voice inbox sweep only (step 1)

**Read:** `prompts/sweep-prompt.md` for the full flow and reporting format.

**Key principle:** Read-mostly. Surface, propose, let the user decide.


### Work Log

**When:** Automatically by the 18:00 `ev-end-of-day-worklog` scheduled task. On demand
when the user says "close out today", "end-of-day work log", "run the work-log pass".

**Two artefacts per active day:**

1. Structured work-log at `vault/work-log/YYYY/YYYY-QN/YYYY-MM-DD.md` with
   `projects_touched[].{slug, kind, level, summary}` — this is the signal the
   project-status rule engine reads.
2. Narrative daily-summary episode at
   `vault/episodes/YYYY/YYYY-QN/YYYY-MM-DD-daily-summary.md` whose `article_refs`
   link to every project touched.

**Activity taxonomy** (use the smallest set of kinds that describes the work):

| Kind | Meaning |
|------|---------|
| `design` | Thinking, speccing, research |
| `build` | Writing new code / content |
| `iterate` | Polishing, refactoring, bug-fixing |
| `ship` | Deploying, releasing, installing |
| `operate` | Running, monitoring, using in production |
| `maintain` | Production fixes / updates to live things |
| `wrap` | Documenting, post-mortem, archiving |
| `pause` | Explicitly putting a project down |

**Levels:** `light` (<1h), `medium` (1–3h), `heavy` (multi-hour focus).

**Read:** `prompts/work-log-prompt.md` for schema, signal-gathering order, and
guardrails. Don't fabricate; never mark `pause` unless the user explicitly said so;
update-in-place on re-runs; skip both artefacts on quiet days.


### Day Board

A five-slot focus board at `vault/tasks/day-board.md`. Each slot is one of:
`empty`, `task`, `project`, `concept`, or `todos`.

**EXECUTE: edit a slot.** `board.py` is the only canonical writer — don't edit
`day-board.md` directly with `Edit`/`Write`.

```bash
# Assignment
python3 <skill_dir>/tools/board.py --vault <vault> assign 3 my-project --type project
python3 <skill_dir>/tools/board.py --vault <vault> assign 4 T075
python3 <skill_dir>/tools/board.py --vault <vault> assign-todos 5

# Field edits
python3 <skill_dir>/tools/board.py --vault <vault> set-field 3 next "Write the test"
python3 <skill_dir>/tools/board.py --vault <vault> set-field 1 holding "Agent running, back at lunch"
python3 <skill_dir>/tools/board.py --vault <vault> add-recent 2 "Shipped the parser"

# Done / dismiss
python3 <skill_dir>/tools/board.py --vault <vault> done 2
python3 <skill_dir>/tools/board.py --vault <vault> dismiss 4

# Todos slot
python3 <skill_dir>/tools/board.py --vault <vault> todos add 5 T018
python3 <skill_dir>/tools/board.py --vault <vault> todos remove 5 T029
python3 <skill_dir>/tools/board.py --vault <vault> todos toggle 5 T018
```

**READ: query the board.** "What's on the board?", "what's in slot 3?", "what's my
next on this project?", "where did I leave that thing?", "what's on Today's todos?".

```bash
python3 <skill_dir>/tools/board.py --vault <vault> read --json
```

Then resolve each slot's `ref` against `tasks[]` (for tasks) or `articles[]` (for
project/concept) and render a compact summary. For specific-slot questions, show only
that slot.

**Done semantics:**
- Task slot → writes `✅ done` into the corresponding T-row in `tasks/todo-list.md`
- Project / concept slot → just clears the slot. Lifecycle status is **not** touched
  (that's the nightly inference's job)
- Todos toggle → writes `✅ done` to the corresponding T-row in `tasks/todo-list.md`

Removing from the todos slot does **not** delete from the master list.

**Personal and Work mix freely.** No scope toggle. No episode needed for board moves —
the 18:00 Work Log consolidates a day's board activity into the permanent record.


### Project Status

**When:** Automatically by the 02:02 nightly consolidation. On demand when the user
says "what's the status on my projects?", "anything changed recently?", "run a project
status pass", "what should be parked / promoted / delivered?".

**Inference signals:**

1. `last_updated` on the project article
2. `vault/episodes/**/*.md` with matching `article_refs`
3. `vault/work-log/**/*.md` with matching `projects_touched[].slug`

**Rules:**

| # | From | To | Trigger | Confidence |
|---|------|----|---------|------------|
| R1 | any non-delivered-* | `delivered-and-parked` | No activity in 60+ days | high |
| R2 | `delivered-and-parked` | `under-development` | Forward-motion activity in last 14 days (excludes `pause`/`wrap`) | high |
| R4 | `ideas` | `prototype` | `ship` activity in last 30 days | medium |
| R5 | `prototype` | `under-development` | 3+ `operate` kinds in 30d with no new `build` in 14d | high |
| R6 | `under-development` | `delivered-and-operational` | `wrap` activity with no `build`/`ship` in 30d | medium |

Plus a data-quality fix: invalid legacy `completed` is corrected to
`delivered-and-operational`.

**Confidence policy:** only `high`-confidence proposals are auto-applied. Medium
proposals land in `<project>/_cache/project-status-proposals.json` for morning
review.

**EXECUTE:**

```bash
python3 <skill_dir>/tools/project_status.py --vault <vault>              # report only
python3 <skill_dir>/tools/project_status.py --vault <vault> --apply      # apply high-conf
python3 <skill_dir>/tools/project_status.py --vault <vault> --cache      # write cache
```

When `--apply` rewrites a project's status it prepends a row to that article's
`## Change History` table with source `Nightly project-status inference` and
confidence `High`. The dashboard surfaces these in "Recent transitions" with an `auto`
badge.

**Guardrails:**
- **Never run `--apply` on demand.** Only the scheduled nightly consolidation auto-applies.
- For ad-hoc review: run without `--apply`, hand proposals to the user for approval.
- `pause` and `wrap` activity kinds are excluded from "forward motion" — declaring
  pause in a work-log doesn't immediately reactivate a parked project.


### Skills Catalog

**Catalog this skill / Update this skill / Install this skill.**

The full catalog workflow (copy source, write README, update index, prepare install
artefact) lives in the active platform doc. The relevant primitives are WRITE
(catalog files into `vault/skills-catalog/<slug>/`), MAINTAIN (update `_index.md`),
and EXECUTE (install/update delivery).

**Read for the catalog query pattern:** "what skills do I have?", "is there a skill for
X?". Read `vault/skills-catalog/_index.md` first; then per-skill `README.md`.


### LLM Selector

**Trigger phrases:** "Which LLM should I use for…", "what's the best model for…",
"what AI tooling for…", "model comparison", "which Claude / GPT / Gemini for…",
or any question where the answer depends on LLM capability differences — including
implicit ones like "I need to do X" where choosing the right model matters.

**Composition:**

1. **READ:** Load `vault/it-setup/llm-selector/llm-scores.yaml` (always fresh — other
   sessions may update it)
2. Decompose the user's task into the 14 scored use cases (see prompt for the mapping table)
3. Pull per-model scores for the relevant use cases, weight by task importance
4. Check the curated `recommendations:` block for a matching task category
5. Present top 2–3 models with reasoning, access notes, and any relevant caveats
6. If `meta.last_updated` is >6 weeks old, flag staleness

**Read for full guidance:** `prompts/llm-selector-prompt.md`.

**Key behaviours:**
- Lead with the recommendation, not a table dump
- If the task splits naturally across models (e.g. "write in Sonnet, review in Gemini"),
  say so — task routing is the correct architecture
- Factor in what the user actually has access to (subscriptions, IDE-only models)
- Keep it conversational


### Category Tagging (concept ↔ project membership)

**When:** the user wants an article to appear in both the Concepts kanban
and the Projects kanban (or remove a membership without rehoming the file).

**Trigger phrases:** "tag this as a concept too", "this is also a project",
"add concept membership", "show this in projects too", "untag from concepts".

**The distinction:** see `SCHEMA.md` § *Concept membership and project
membership*. `concepts` membership = documents a way of thinking;
`projects` membership = ships a functional deliverable; many articles are
both. The membership is just the presence of the corresponding slug in the
article's `domains:` list.

**Steps:**

1. Identify the article. Read its current `domains:` list.
2. Add or remove `concepts` / `projects` from `domains:`. Preserve any
   other secondary domains (e.g. `health`, `hobbies`).
3. Bump `last_updated`.
4. **Don't move the file.** This is membership tagging, not rehoming. The
   file stays at its canonical home (which still matches the primary —
   first — domain in the list).
5. Rebuild indexes for whichever domains gained or lost the article.
6. Confirm: `✓ Tagged <slug>: domains now [<list>]`.

**Done in the dashboard:** each card on the concepts and projects kanbans
shows two checkboxes — `concept` and `project`. Ticking a box adds the
corresponding domain; unticking removes it. POSTs to `/article/toggle-domain`.

**Done programmatically (e.g. via this skill in chat):**

```bash
python3 <skill_dir>/tools/ingest.py write \
  --vault <vault> --path <existing-path> \
  --add-domain concepts \
  --add-domain projects
```

(or `--remove-domain` for the opposite). If `ingest.py` doesn't yet support
`--add-domain` / `--remove-domain`, fall back to a direct frontmatter edit
followed by `index_builder.py` for the touched domains.

**Read for the schema rationale:** `SCHEMA.md` § *Concept membership and
project membership*.


### Concept Promotion (concept project → project project)

**When:** An article in `concepts/` has reached `tier: project` and is now
producing something operational — code, hardware, a skill bundle, a deployment
— rather than just documentation.

**Trigger phrases:** "promote this concept", "this is becoming a real project",
"move this to projects", "ship this concept", "graduate this concept".

**The distinction:** see `SCHEMA.md` § *Concept projects vs. project projects*.
A concept project's deliverable is conceptual (framework, taxonomy, way of
thinking). A project project's deliverable is functional (code, hardware,
service). Same five-slot lifecycle; different output kinds.

**Steps:**

1. **Confirm the criteria.** Article currently lives in `concepts/`. `tier:
   project`. The deliverable is operational, not just documentation. If the
   user is unsure, surface what's in the article (status, recent activity,
   any `code_path`/`github` already set) and ask.
2. **Move the file.** `mv vault/concepts/<slug>.md vault/projects/<slug>.md`.
   The slug stays the same — that's deliberate, so every existing
   `related: [<slug>]`, `relationships[].ref: <slug>`, and `article_refs:
   [<slug>]` keeps resolving across the move.
3. **Update frontmatter:**
   - `domains:` from `[concepts]` (or `[concepts, ...]`) to `[projects]` (or
     `[projects, ...]` retaining other secondary domains, but drop `concepts`
     unless the article still genuinely covers conceptual ground).
   - If a code repo / hardware / bundle just landed, set `code_path:` and
     `github:` accordingly.
   - Bump `last_updated`.
4. **Add a Change History row.** Format: `Promoted concept project →
   project project. Now lives in projects/.` plus the trigger reason
   (e.g. "code repo created", "hardware shipped", "skill bundled").
5. **Run a ripple scan** on the new path to surface articles that reference
   the slug — those continue to resolve, but the user may want to review
   whether their context still reads well.
6. **Rebuild indexes:** `python3 <skill_dir>/tools/index_builder.py concepts projects`.
7. **Confirm:** `✓ Promoted <slug>: concepts/ → projects/`.

**Demotion (rare):** the reverse move is valid when a project project
becomes purely documentation work — code archived, hardware retired, skill
deprecated. Same recipe, opposite direction. Don't propose demotion
proactively; only on explicit request.

**Read for the schema rationale:** `SCHEMA.md` § *Concept projects vs. project projects*.

### Other named workflows

- **Conflict Resolution.** When new info contradicts the vault: surface both values,
  ask the user to adjudicate, preserve provenance for both. Never destroy information
  to resolve a conflict.
- **Concept Refinement.** When a query surfaces a concept stuck at `ideas` for 30+
  days, *offer* to refine using 2–3 prompts from `prompts/concept-refinement-prompt.md`.
  Never interrupt other work to offer; only when the concept is already in context.
- **Session Promotion.** End of substantial session — review what was discussed, offer:
  "We discussed X and Y today. Want me to file any of this?" An *offer*, not automatic.
- **Workspace Pack Generation.** The user asks for a context pack on a topic. Gather
  related articles + recent episodes + open follow-ups + key sources. Generate fresh
  each time; don't store.
- **Autoresearch.** Web-enrichment for concept articles. **Never auto-trigger.** Always
  requires explicit request. Read `prompts/autoresearch-prompt.md` for guard rails.
- **Export.** Migrate / share / back up. JSON, markdown handoff, or CSV. `credential`
  always excluded; `sensitive` excluded unless explicitly requested. All exports
  include `ev-manifest.yaml`.


## Decision tree

```
User input arrives
       │
       ├── Asking a question ─────────────────────► READ
       │   ("when does…", "what's…", "who is…")
       │     - Temporal? → query.py --episodes first
       │     - Stale ideas concept hit? → offer Concept Refinement
       │     - About the day board? → board.py read --json
       │
       ├── Sharing facts/info/thinking ───────────► WRITE
       │   ("my insurance is…", "the new GP is…")
       │     - Concepts domain? → set tier (insight/concept/idea/project)
       │       "Add an insight" → tier: insight (not concept!)
       │     - Real-world event? → also create an episode
       │     - Conflicts existing? → Conflict Resolution
       │     - After write: ripple scan + rebuild indexes
       │
       ├── Uploading / pointing at a document ────► FILE
       │   ("file this", "what's in this PDF")
       │     - Lands original in Source tier + writes synthesised article
       │     - Marks an event? → also create an episode
       │
       ├── "Review", "what needs attention",  ────► MAINTAIN
       │   "what's converging", "patterns"
       │     - Curate or Consolidate per phrasing
       │
       ├── "Open the dashboard" / install skill ──► EXECUTE
       │   / put X on a slot / project status
       │     - Routes via PLATFORM-<name>.md or composed workflows below
       │
       ├── "EV sweep" / "quick sweep" / etc. ─────► Composed: Sweep
       ├── "Close out today" / 18:00 trigger ─────► Composed: Work Log
       ├── Slot edits or "what's on the board" ──► Composed: Day Board
       ├── "What changed?" / nightly trigger ─────► Composed: Project Status
       ├── "Catalog / install / update" skill ────► Composed: Skills Catalog
       ├── "Which model for…" / AI tooling ──────► Composed: LLM Selector
       ├── End of substantial session ────────────► Composed: Session Promotion (offer)
       ├── "Research this concept" ──────────────► Composed: Autoresearch (explicit only)
       ├── "Tag as concept too" / "this is also a ──► Category Tagging
       │     project" / "show in both kanbans"        (toggle domains membership; no file move)
       ├── "Promote this concept" / "this is a   ──► Concept Promotion
       │     real project now" / "graduate it"        (concept project → project project)
       │
       └── Contradictory information surfaces ────► Composed: Conflict Resolution
```


## Key behaviours (carry through every primitive)

- **Always confirm before writing.** Summarise, then commit.
- **Prefer updating over creating.** Scan first; enrich existing articles.
- **Never destroy to resolve a conflict.** Preserve both claims with provenance.
- **Never delete files — move to `_for-deletion/`.** When an article is
  superseded, duplicate, or no longer wanted, `mv` it to
  `<project>/_for-deletion/` (a SIBLING of `vault/`, not inside it). From
  inside the vault that's `mv vault/path/to/article.md ../_for-deletion/path/to/article.md`.
  This is safe (every move is reversible), tidy (the folder is outside the
  vault, so tools never walk it), and platform-independent (`mv` works on
  every host). The user empties the folder periodically — the agent never
  does. Confirm the move with a one-line `✓ Moved <path> → ../_for-deletion/`.
  See `SCHEMA.md` § "The `_for-deletion/` soft-delete convention" for the
  full rule.
- **Source attribution matters.** Every answer cites where it came from and when last
  verified.
- **Proactive capture.** If something worth keeping passes by, *offer* to capture even
  when not asked.
- **Capture events as episodes.** Facts in articles, events in episodes.
- **Respect sensitivity.** Never broad-search `credential`; flag `sensitive`.
- **Read-mostly maintenance.** Surface, propose, wait for approval. No auto-merge,
  auto-delete, auto-rewrite of core, or auto-autoresearch.
- **Filesystem-grep guardrail.** For the user's personal content, use `query.py` and
  the domain map. Don't grep `~/Documents/...`.


## Tools

```
tools/
├── ingest.py         # Create/update articles and episodes (write, episode, scan, ripple)
├── query.py          # Search the vault (articles, episodes, core)
├── curate.py         # Maintain quality, validate, audit sensitivity
├── consolidate.py    # Synthesis pass: convergence, orphans, patterns
├── file_handler.py   # File documents into the vault (Source tier + synth)
├── index_builder.py  # Rebuild domain and episode indexes
├── board.py          # Day Board reader/writer (only canonical writer for day-board.md)
└── project_status.py # Project-status rule engine
```

Call them like: `python3 <skill_dir>/tools/ingest.py --help`


## Project storage convention (one-liner)

A common confusion when capturing project work is *where* the actual files live —
inside the vault, somewhere in `~/Documents/`, in `~/Developer/`, or in some
session-output folder. Keep the rule simple and consistent so the agent doesn't have
to ask every time. The full convention belongs in `core/preferences.md` (the
canonical home) — load that at session start and the rule is in context.

Default decision rule (adjust to taste in your `core/preferences.md`):

> Runnable code → `~/Developer/` (local SSD, GitHub remote). Non-code project
> artefacts → `~/Documents/Projects/`. Life admin → `~/Documents/Admin/`.
> Session-generated files → `~/Documents/Outputs/` (inbox, not permanent home).

Per-pillar bucket layouts: `core/preferences.md`. The `code_path:` field in project
articles records the on-disk location of runnable code; `github:` records the remote;
`source_ref:` points at the Source tier for ingested raw material. See `SCHEMA.md`
§ "Provenance fields — disambiguation" for the precise rule.


## Platform hooks

Everything that varies by platform — vault probing, install delivery, dashboard launch,
voice inbox handling — lives in `PLATFORM-<name>.md` companion docs. Currently bundled:

- `PLATFORM-CURSOR.md` — Cursor, Codex CLI, VS Code with MCP, and similar IDE-style hosts
- `PLATFORM-CLAUDE.md` — Claude Code, Cowork

Core behaviour in this `SKILL.md` plus `SCHEMA.md` stays platform-independent. Adding
support for a new platform is purely a matter of writing a new `PLATFORM-<NAME>.md`
that mirrors the structure of the two above — nothing in the core needs to change.
