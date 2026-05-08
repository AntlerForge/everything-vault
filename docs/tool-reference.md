# Tool Reference

Eight plain Python scripts under `skill/tools/`. No external dependencies for the core (PyYAML optional). Most accept `--vault <path>` and fall back to the `EV_VAULT_PATH` environment variable; use `--help` on any tool for the full flag list.

## query.py

**Purpose.** Search the vault — articles, episodes, core memory, structured fields. The skill's default for any question.

**Path:** `skill/tools/query.py`

```bash
python3 skill/tools/query.py --question "When does my car insurance renew?"
python3 skill/tools/query.py --episodes --question "What happened with the boiler?"
python3 skill/tools/query.py --domain finance --keyword mortgage
```

**Notable flags.** `--question` (natural language) · `--keyword` · `--domain <slug>` · `--episodes` (events, not articles) · `--date-from` / `--date-to` · `--core` · `--stale --days 180` · `--structured --field renewal_date --within-days 60` · `--full`.

## ingest.py

**Purpose.** Create or update articles and episodes. Sub-command driven; the skill's WRITE primitive is mostly this tool.

**Path:** `skill/tools/ingest.py`

```bash
python3 skill/tools/ingest.py scan --query "car insurance"
python3 skill/tools/ingest.py write --path finance/car-insurance.md --content-file /tmp/article.md
python3 skill/tools/ingest.py episode --date 2026-05-07 --title "Boiler service done"
python3 skill/tools/ingest.py ripple --source car-insurance.md
```

**Sub-commands.** `scan` (find existing articles on a topic — run before writing), `write` (`--path`, `--content` / `--content-file`), `episode` (dated event record under `episodes/YYYY/YYYY-QN/`), `list` (`--domain`, `--object-type`), `ripple` (find articles affected by a change — `--source <filename>`).

## curate.py

**Purpose.** Find work that needs attention. Read-mostly: surfaces problems, never auto-fixes them.

**Path:** `skill/tools/curate.py`

```bash
python3 skill/tools/curate.py --stale --days 180
python3 skill/tools/curate.py --validate
python3 skill/tools/curate.py --renewals --within 90
```

**Notable flags.** `--stale` (older than `--days`) · `--holding-pen` (unfiled triage) · `--gaps` (under-populated domains) · `--renewals --within N` · `--validate` (frontmatter sanity) · `--sensitivity-audit` · `--episode-gaps`.

## consolidate.py

**Purpose.** Synthesis pass — find convergences, orphan episodes, resolved tasks, missing links, stale concepts. Surfaces patterns; you decide what to do.

**Path:** `skill/tools/consolidate.py`

```bash
python3 skill/tools/consolidate.py --check all
python3 skill/tools/consolidate.py --check convergence --save
python3 skill/tools/consolidate.py --load-cache
```

**Notable flags.** `--check <name>` (run one specific check or `all`) · `--save` (write results to `<project>/_cache/consolidation.json`) · `--load-cache` (print the saved results without re-running, useful for resuming a sweep across sessions).

## file_handler.py

**Purpose.** Bridge external documents into the vault — summarise a PDF/text file so the agent can write a synthesised article and land the original in the Source tier.

**Path:** `skill/tools/file_handler.py`

```bash
python3 skill/tools/file_handler.py --summarise ~/Downloads/quote.pdf
python3 skill/tools/file_handler.py --list-refs
```

**Notable flags.** `--summarise <file>` (extract text and key facts from a document) · `--list-refs` (list every article in the vault with a `source_ref` link, including a check that the source file still exists).

## index_builder.py

**Purpose.** Regenerate the per-domain `_index.md` files and the master `_index.md`. Run after batch edits or when adding/removing domains.

**Path:** `skill/tools/index_builder.py`

```bash
python3 skill/tools/index_builder.py
python3 skill/tools/index_builder.py --domain concepts
```

**Notable flags.** `--domain <slug>` (rebuild one domain's index instead of all of them; pass `episodes` to rebuild the episode index).

## board.py

**Purpose.** The only canonical writer for `vault/tasks/day-board.md`. Reading the board, assigning slots, editing slot fields, marking done, managing the today's-todos list.

**Path:** `skill/tools/board.py`

```bash
python3 skill/tools/board.py --vault $EV_VAULT_PATH read --json
python3 skill/tools/board.py --vault $EV_VAULT_PATH assign 3 my-project --type project
python3 skill/tools/board.py --vault $EV_VAULT_PATH set-field 3 next "Write the test"
python3 skill/tools/board.py --vault $EV_VAULT_PATH done 2
```

**Subcommands.** `read` · `init` · `assign <pos> <ref> [--type project|concept|task]` · `assign-todos <pos>` · `dismiss <pos>` · `done <pos>` · `set-field <pos> <recently_done|next|holding|notes> <value>` · `add-recent <pos> <line>` · `todos {add|remove|toggle} <pos> <ref> [--note ...]` · `tasks-done <ref>` (marks a T-row done in `todo-list.md`).

The `--vault` flag is required for `board.py` (unlike most other tools, it doesn't auto-detect).

## project_status.py

**Purpose.** Rule engine that infers project lifecycle transitions from `last_updated`, episodes, and work-log activity. Designed to run nightly.

**Path:** `skill/tools/project_status.py`

```bash
python3 skill/tools/project_status.py --vault $EV_VAULT_PATH                  # report only
python3 skill/tools/project_status.py --vault $EV_VAULT_PATH --apply --cache  # nightly job
python3 skill/tools/project_status.py --vault $EV_VAULT_PATH --threshold medium
```

**Notable flags.** `--apply` (rewrite `status:` on articles where the rule fires at or above `--threshold`) · `--cache` (write proposals to `<project>/_cache/project-status-proposals.json` for morning review) · `--threshold {high,medium,low}` (default `high`) · `--today YYYY-MM-DD` (override today's date for testing).

The skill's guidance is to never run `--apply` on demand. Use it only from the scheduled task — see [scheduled-tasks.md](scheduled-tasks.md).

## EV_VAULT_PATH

Every tool listed above (except `board.py`) accepts `--vault <path>` and falls back to the `EV_VAULT_PATH` environment variable. Set it once in your shell profile and you can drop `--vault` from every command:

```bash
export EV_VAULT_PATH=~/Documents/everything-vault/vault
```

The dashboard's `build_dashboard.py` honours the same variable.
