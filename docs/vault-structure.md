# Vault Structure

This is the data model in depth. The canonical source is [`skill/SCHEMA.md`](../skill/SCHEMA.md) — read that for the precise contract. This doc is the friendlier version with examples and rationale.

## Project folder vs. vault folder

The vault lives inside a **project folder** along with two siblings that hold operational metadata. The split is deliberate: `vault/` is pure knowledge content, the siblings are runtime housekeeping.

```
<project>/                  # the project folder (e.g. ~/Documents/everything-vault/)
├── vault/                  # the actual vault — knowledge content
├── _for-deletion/          # soft-delete bin (sibling, not inside vault)
├── _cache/                 # runtime caches: consolidation, project-status proposals
└── _archive/               # (optional) user-managed long-term archive
```

Why siblings rather than children?

- **`vault/` stays self-describing.** `tar`, `grep`, `rsync`, or `git` of `vault/` produces only real articles — no soft-deleted bin, no cache files.
- **Operational metadata gets a proper home.** Caches and the soft-delete bin aren't knowledge; they don't belong in the same tree as articles.
- **Tools take `--vault <project>/vault`.** They locate siblings via `<vault>.parent`, so they keep working without any new flags.

The rest of this doc focuses on what's inside `vault/`.

## The three tiers

```
                  ┌─────────────────────────────────────────────┐
                  │  Source                                     │
                  │  vault/sources/                             │
                  │  Raw originals: PDFs, transcripts, pasted   │
                  │  text. Never edited. Sidecar .meta.yaml     │
                  │  files carry minimal metadata.              │
                  └────────────────┬────────────────────────────┘
                                   │ synthesised into
                                   ▼
                  ┌─────────────────────────────────────────────┐
                  │  Wiki                                       │
                  │  vault/<domain>/...                         │
                  │  Synthesised articles. The durable          │
                  │  knowledge tier. Articles can link back     │
                  │  to Source via source_ref.                  │
                  └────────────────┬────────────────────────────┘
                                   │ referenced by
                                   ▼
                  ┌─────────────────────────────────────────────┐
                  │  Scratch                                    │
                  │  vault/core/, episodes/, work-log/, tasks/  │
                  │  Working memory. Always-load context,       │
                  │  dated events, daily logs, focus board.     │
                  └─────────────────────────────────────────────┘
```

The point of three tiers: synthesised Wiki articles carry one model's interpretation of source material. If a better model comes along later, you can re-synthesise from Source. The Source tier is your immutable record; the Wiki is the queryable, editable layer.

The Scratch tier is faster-changing — it's where today's day-board lives, where end-of-day work logs land, and where dated event records (episodes) accumulate over time.

## Folder structure

**Inside `vault/` (knowledge content only):**

```
vault/
├── core/                # always-load context (whoami, preferences, active-context, key-people)
├── sources/             # raw ingested material (Source tier)
│   └── YYYY/
│       ├── YYYY-MM-DD-<slug>.<ext>
│       └── YYYY-MM-DD-<slug>.meta.yaml
├── episodes/            # dated event records
│   └── YYYY/
│       └── YYYY-QN/
│           └── YYYY-MM-DD-<slug>.md
├── work-log/            # daily structured work logs
│   └── YYYY/
│       └── YYYY-QN/
│           └── YYYY-MM-DD.md
├── tasks/               # todo-list.md, day-board.md
├── <domain>/            # one folder per domain
│   ├── _index.md        # auto-generated
│   └── *.md             # articles
├── ev-manifest.yaml     # machine-readable vault description
└── _index.md            # top-level index (also auto-generated)
```

**Sibling folders (operational metadata, alongside `vault/`):**

```
<project>/
├── vault/               # see above
├── _for-deletion/       # soft-delete bin (agent moves files here, you empty it)
├── _cache/              # runtime caches (consolidation.json, project-status-proposals.json)
└── _archive/            # (optional) user-managed long-term archive
```

### `_for-deletion/` — soft-delete (sibling of vault/)

The vault has a deliberate **never-delete** policy. When the agent supersedes, deduplicates, or retires an article, it moves the file to `<project>/_for-deletion/` — a **sibling** of `vault/`, not inside it. The convention is intentionally minimal:

- From inside the vault, that's `mv vault/path/to/article.md ../_for-deletion/path/to/article.md`. The `..` is because the agent works inside `vault/`.
- Every tool in `skill/tools/` and the dashboard build script walks only `vault/`, so the soft-delete bin never appears in indexing, queries, or rendering.
- The agent confirms before moving, just like any other write. It logs the move with a one-line `✓ Moved <path> → ../_for-deletion/`.
- The agent **never empties** the folder — that's your decision. Empty it periodically (a sweep is a natural moment) with `rm -rf <project>/_for-deletion/*` or via your file manager.

The benefit over hard-delete: every move is reversible. If the agent gets it wrong, you just move the file back. The cost is near-zero — the bin lives outside the vault entirely, so it cannot pollute queries or indexes.

There's also a **path-level safety net** inside the tools: any path that contains a folder beginning with `_` or `.` is skipped during a vault walk. So if you create stray `_*/` folders inside `vault/` (a `_scratch/` directory, a `_archive/` you forgot to put as a sibling, etc.), they're still excluded automatically.

## The default domain map

Sensible defaults that fit most lives. Add or remove via `ev-manifest.yaml`.

| Slug | What goes here |
|------|----------------|
| `core` | Identity, preferences, current priorities, key people. Always loaded. |
| `concepts` | Ideas, insights, design principles — the thinking pipeline |
| `projects` | Active and past projects (with code, deliverables, or scope) |
| `health` | Personal medical, fitness, GP, prescriptions |
| `finance` | Budgets, bank accounts, taxes, mortgages |
| `hobbies` | Personal interests and activities |
| `household` | Property, utilities, maintenance, appliances |
| `it-setup` | Computers, networks, automation, dev environment |
| `work` | Employment, freelance, client work |
| `vehicles` | Cars, bikes, MOT, insurance |
| `pets` | Pet health, vet, vaccinations |
| `holidays` | Trips — one subfolder per trip |
| `family` | Family members, contacts, shared arrangements |
| `legal` | Wills, contracts, legal correspondence |
| `purchases` | Subscriptions, receipts, warranties, renewals |
| `professional` | Qualifications, CV, certifications, training |
| `skills-catalog` | Reusable LLM skill definitions |

To customise: see [customisation.md](customisation.md).

## Article frontmatter

Every article opens with YAML frontmatter. Minimal required fields:

```yaml
---
title: "Human-readable title"
domains: [primary-domain, secondary-domain]
type: fact | account | how-to | reference | log | contact
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
last_verified: YYYY-MM-DD
confidence: high | medium | low
source: conversation | upload | filed-document | manual
---
```

Optional fields, used when relevant:

```yaml
sensitivity: normal | sensitive | credential   # default: normal
retrieval_default: searchable | always_load | on_explicit_request | never
related: [slug1, slug2]
relationships:
  - ref: another-article
    type: supports | extends | supersedes | contradicts | refines | implements | inspires

# Concepts only
tier: insight | concept | idea | project
status: ideas | prototype | under-development | delivered-and-operational | delivered-and-parked
parent: <slug-of-parent-concept>
applies_to: work | personal | both        # scope of applicability

# Projects with code
code_path: "~/Developer/personal/MyApp"
github: "git@github.com:user/MyApp.git"
development_platform: cursor | claude-code | xcode | vscode | ...

# Time-varying facts
renewal_date: YYYY-MM-DD
cost: 110
provider: "Service provider name"

# Files brought in via the File primitive
source_ref: "sources/YYYY/YYYY-MM-DD-slug.pdf"
```

The full schema with every field documented is in [`skill/SCHEMA.md`](../skill/SCHEMA.md).

## Naming conventions

- **Slugs:** lowercase, hyphen-separated, descriptive. Stable across title changes.
- **Article files:** `<domain>/<slug>.md`
- **Episode files:** `episodes/YYYY/YYYY-QN/YYYY-MM-DD-<slug>.md`
- **Work-log files:** `work-log/YYYY/YYYY-QN/YYYY-MM-DD.md` (one per active day)
- **Source files:** `sources/YYYY/YYYY-MM-DD-<slug>.<ext>` plus a `<filename>.meta.yaml` sidecar

The date-stamping convention on episodes and sources gives you natural temporal organisation without extra metadata.

## Sensitivity model

| Level | Meaning | Retrieval |
|-------|---------|-----------|
| `normal` | General personal info | Searchable by default |
| `sensitive` | Medical, legal, financial | Searchable, flagged when surfaced. Excluded from workspace packs unless requested. |
| `credential` | Passwords, recovery codes, API keys | **Never loaded by default.** Only on explicit request. Never in exports. |

The skill respects these levels — see [`skill/SKILL.md`](../skill/SKILL.md) § Sensitivity Model.

## Index files

Each domain folder has an `_index.md` that lists its articles. These are **auto-generated** by `index_builder.py` — don't hand-edit them. If you have a hand-curated index, add the literal string `_Hand-maintained_` somewhere in the file and the generator will skip it.

Run the indexer whenever you add or rename articles:

```bash
python3 skill/tools/index_builder.py --vault $EV_VAULT_PATH
```

## Episodes

Episodes record events that happened. They live in `episodes/YYYY/YYYY-QN/`. The frontmatter schema:

```yaml
---
title: "Short description of what happened"
domains: [<domain>, episodes]
type: log
object_type: episode
date: YYYY-MM-DD
actors: [user]
entity_refs: []
article_refs: [<related-article-slugs>]
outcomes:
  - What resulted from this event
follow_up: null
sensitivity: normal
created: YYYY-MM-DD
confidence: high
---
```

Use episodes for: medication changes, document submissions, project milestones, decisions, conversations worth remembering. Don't use them for: things that are just facts (those go in articles), trivial events ("checked the post").

The work-log composition workflow generates a daily-summary episode automatically per active day.

## Cross-references

Three ways articles connect:

- **`related: []`** — simple "see also" list. Use when the connection isn't worth typing.
- **`relationships: []`** — typed list. Use when the *kind* of connection matters (e.g., "this concept supports that other one"). Types are documented in `skill/SCHEMA.md`.
- **`parent:`** — for `concepts` only, points up the hierarchy.

The dashboard shows relationships visually on the Concepts kanban; queries follow them when scoring relevance.

## Manifest

Every vault has an `ev-manifest.yaml` at the root. Minimal shape:

```yaml
vault_name: "Your Vault Name"
schema_version: "1.0"
ev_version: "1.0.0"
created: YYYY-MM-DD
domains: [...]
```

Generated automatically by setup; edit to record the domains you actually use. The manifest is read by export tooling and is the canonical "what does this vault contain" answer.
