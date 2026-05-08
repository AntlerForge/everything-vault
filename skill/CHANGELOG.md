# Everything Vault — Changelog

*Version history. **Not auto-loaded.** Human reference only — agents should not have
this in context unless explicitly asked about history.*

---

## v1.0.5 — Concept / project membership as checkboxes

Replaces the v1.0.4 "concept project vs. project project" framing with a
cleaner multi-membership model: an article can be tagged as `concepts`,
`projects`, or both — and appears in the corresponding kanban(s) accordingly.

- **`SCHEMA.md`** — section reframed as "Concept membership and project
  membership (two checkboxes, not two folders)". Same idea, but emphasises
  that the data model already supports both via the existing `domains:` list,
  and that toggling membership is a one-tick operation that doesn't move the
  file. Concept Promotion (file rehoming) stays as a separate, heavier
  workflow for when the primary deliverable shifts.
- **`SKILL.md`** — new *Category Tagging* workflow added BEFORE *Concept
  Promotion*. Tagging adjusts membership (no file move); promotion rehomes
  the file (when canonical primary shifts). Decision tree updated.
- **Dashboard** — new `/article/toggle-domain` POST endpoint that adds or
  removes a domain from an article's `domains:` list, then triggers a
  rebuild. Each card on the concepts and projects kanbans now shows two
  checkboxes ("concept" / "project") that POST to the new endpoint. Ticking
  a box on a concept-only article adds it to the projects kanban (and vice
  versa).
- **No tool changes required** — `ingest.py write` can already update
  frontmatter; the dashboard endpoint uses an inline frontmatter edit
  similar to `_move_concept` / `_move_project`.

**Migration:** None. Existing articles work unchanged. Articles already
tagged with both `concepts` and `projects` in `domains:` will now show up
in both kanbans (previously they only showed in whichever kanban the dashboard
filter ran first).

---

## v1.0.4 — Concept project vs. project project distinction

A `tier: project` article can live in either `concepts/` or `projects/`. Until
now the difference was implicit; this version makes it explicit.

- **`SCHEMA.md` § Concept projects vs. project projects.** New subsection
  under "Concepts Hierarchy" defining the distinction:
  - **Concept project** (`concepts/<slug>.md`) — deliverable is documentation,
    a framework, a way of thinking. No `code_path`/`github`.
  - **Project project** (`projects/<slug>.md`) — deliverable is functional:
    code, hardware, a skill bundle, a service.
  Same five-slot lifecycle for both; the difference is what counts as
  "shipped" — published documentation vs. working code/hardware.
- **`SKILL.md` § Concept Promotion.** New named workflow for moving an
  article from `concepts/` to `projects/` when its deliverable matures from
  documentation into something operational. Trigger phrases: "promote this
  concept", "this is a real project now", "graduate it". Slug stays stable
  across the move so existing cross-references keep resolving. Demotion
  works the same way in reverse but is rare — only on explicit request.
- **Decision tree** (in SKILL.md) updated to surface the trigger.

**Migration:** None — existing articles aren't touched. The change is purely
documentation of an existing pattern.

---

## v1.0.3 — Project-folder layout: operational metadata moves out of vault/

Refines the v1.0.2 soft-delete convention by moving operational folders OUT
of `vault/` and into the project folder as siblings:

```
<project>/
├── vault/             # pure knowledge content
├── _for-deletion/     # soft-delete bin (was vault/_for-deletion/)
└── _cache/            # runtime caches (was vault/_consolidation-cache.json etc.)
```

**Why:** `vault/` becomes a self-describing knowledge container — `tar`,
`grep`, `rsync`, and `git` of `vault/` produce only real content. Operational
metadata gets a proper home as siblings rather than polluting the vault.

**Changes:** `SKILL.md` and `SCHEMA.md` describe the new layout. `consolidate.py`
and `project_status.py` write caches to `<project>/_cache/`. The example
ships as `example-project/` with `vault/` + `_for-deletion/` + `_cache/`
inside, replacing the old `example-vault/` layout. `setup.sh` creates the
project folder structure. `purge-example-data.sh` handles siblings (with a
new `--project <path>` arg).

**Migration for existing users:** run

```bash
mv vault/_for-deletion ../_for-deletion
mkdir -p ../_cache
mv vault/_consolidation-cache.json ../_cache/consolidation.json 2>/dev/null || true
mv vault/_project-status-proposals.json ../_cache/project-status-proposals.json 2>/dev/null || true
```

Tools read legacy locations as a fallback during this release; the fallback
will be removed in a future version.

---

## v1.0.2 — `_for-deletion/` soft-delete convention

The vault now has an explicit **never-delete** policy. When the agent
supersedes, deduplicates, or retires an article, it moves the file to
`vault/_for-deletion/` rather than deleting it.

- **`SKILL.md` § Key behaviours.** New "Never delete files — move to
  `_for-deletion/`" rule alongside the existing "Never destroy to resolve a
  conflict" guardrail.
- **`SCHEMA.md` § Folder structure.** `_for-deletion/` added to the top-level
  layout. New section "The `_for-deletion/` soft-delete convention" explains
  why and how.
- **Tools and dashboard.** All `rglob` walk sites in the eight Python tools
  and the dashboard build script now skip any path that contains a directory
  beginning with `_` or `.`. A shared `_is_under_dot_or_underscore()` helper
  enforces this consistently. Underscore-prefixed top-level folders (e.g.
  `_archive/`, `_scratch/`) are now reliably out-of-band — useful for any
  internal-metadata folders the user adds.
- **Setup and purge scripts.** `setup.sh` creates `_for-deletion/` as part of
  the default folder structure. `purge-example-data.sh` clears the folder's
  contents but preserves the folder + a one-paragraph README explaining its
  role.
- **Example vault.** `_for-deletion/README.md` ships in the example vault so
  cloners see the convention in place. `core/preferences.md` documents the
  soft-delete rule as part of how the user wants the vault operated.
- **Docs.** `docs/vault-structure.md` and `docs/faq.md` cover the convention.

**Migration:** None — older vaults work unchanged. Add an empty
`_for-deletion/` folder if you want the agent to start using soft-delete.

---

## v1.0.1 — Storage convention + applies_to field

Two small additions ported from the upstream knowledge-vault project this version
was extracted from:

- **`SKILL.md` § Project storage convention.** New section laying out the
  four-pillar default rule: runnable code → `~/Developer/`, non-code project
  artefacts → `~/Documents/Projects/`, life admin → `~/Documents/Admin/`,
  session-generated files → `~/Documents/Outputs/` (inbox, not permanent home).
  Adjustable in `core/preferences.md`.
- **`SCHEMA.md` — new `applies_to` field.** Optional concepts-domain field with
  values `work | personal | both` for scoping a concept's applicability. The
  dashboard build script already reads this field; the schema simply documents it.
- Example vault updated: `core/preferences.md` now demonstrates the four-pillar
  rule explicitly; three concepts (`small-bets-portfolio`, `async-client-comms`,
  `kanji-mnemonics-method`) gain `applies_to` values to demonstrate the field.

**Migration:** None — both additions are optional. Existing vaults work unchanged.

---

## v1.0.0 — Initial public release

The first published version of Everything Vault. Extracted from a personal knowledge
management system that has been battle-tested across 150+ articles, dozens of
composed workflows, and several months of daily use before being generalised for
public release.

**What you get:**

- **The skill.** SKILL.md, SCHEMA.md, PLATFORM-CLAUDE.md, PLATFORM-CURSOR.md,
  CHANGELOG.md — the agent-behaviour and data-contract docs that any LLM can read
  to operate the vault.
- **Eight Python CLI tools.** Query, ingest, curate, consolidate, file, index_builder,
  board, project_status. No external dependencies for core functionality (PyYAML
  optional but recommended).
- **The dashboard.** A single-file HTML dashboard with concepts kanban, projects
  kanban, day board, task management, timeline, and stats. Served by a Python build
  script that walks the vault and generates JSON. Accessible by default — designed
  with red/green colour-blind safety in mind.
- **Eleven prompt files** covering query, ingest, episode, sweep, curate,
  consolidation, file, autoresearch, concept-refinement, work-log, and llm-selector
  workflows.
- **An example vault** populated with a fictional persona ("Alex Chen" — freelance
  software developer in Bristol) so you can explore every feature before committing
  your own data.
- **Setup and purge scripts.** `setup.sh` walks you through first-run configuration.
  `purge-example-data.sh` clears the example content while preserving the structure.
- **Comprehensive documentation** in `docs/` covering getting started, vault
  structure, dashboard features, tool reference, skill usage, customisation,
  scheduled tasks, and FAQ.

**Design principles:**

- **Local-first.** Your data stays on your machine. No cloud, no telemetry, no
  tracking. Sync via any file-sync method you already trust (iCloud, Dropbox,
  Syncthing, Git).
- **Plain markdown + YAML.** The format outlives any tool. You can read your vault
  in any text editor; you can grep it from the command line; you can rsync it to
  another machine and keep working.
- **Three tiers** (Source / Wiki / Scratch) so synthesised articles are always
  re-derivable from raw originals.
- **Five primitives** (Read / Write / Maintain / File / Execute) plus pre-composed
  workflows that any LLM can invoke through natural conversation.
- **Read-mostly maintenance.** The vault never auto-merges, auto-deletes, or
  auto-rewrites your core memory. Curation surfaces findings; you decide.

**License:** MIT.

---

## Pre-1.0 history

Everything Vault grew out of a personal knowledge management system built and refined
over several months of daily use. The pre-public versions of the underlying system
are documented in the original maintainer's vault but are not part of this public
project's history. Version 1.0.0 here represents the first generic, publishable
extraction — a clean rewrite of the skill files, scrubbed of personal data, with a
fictional example vault and full user documentation added.

---

## Versioning policy

- **Major** (`X.0.0`) — breaking schema changes that require migration
- **Minor** (`X.Y.0`) — new features, additional frontmatter fields, new tools or
  workflows. Backwards compatible.
- **Patch** (`X.Y.Z`) — bug fixes, documentation, minor tool improvements.

Schema changes are documented under the version that introduces them, with explicit
migration notes if existing vaults need updating.
