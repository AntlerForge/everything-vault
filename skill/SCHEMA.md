# Everything Vault — Schema

*The data contract. Platform-independent. Any LLM, any agent framework, any text editor that
understands markdown + YAML frontmatter can read and write this vault.*

This document describes the **shape** of the vault. For agent **behaviour** see `SKILL.md`.
For platform plumbing see `PLATFORM-CLAUDE.md` (Claude/Cowork) or `PLATFORM-CURSOR.md`
(Cursor). For version history see `CHANGELOG.md`.

---

## Three tiers of content

The vault stores knowledge in three tiers, each with a distinct purpose and lifecycle.
This three-tier separation matches what most durable personal-knowledge systems
converge on.

| Tier        | Folder              | What it holds                                              | Re-synthesisable |
|-------------|---------------------|-------------------------------------------------------------|------------------|
| **Source**  | `sources/`          | Raw ingested material, untouched (PDFs, transcripts, pasted text) | n/a (it IS the source) |
| **Wiki**    | domain folders      | Synthesised articles and entities                          | yes — from Source |
| **Scratch** | `core/`, `episodes/`, `work-log/`, `tasks/` | Working memory, dated events, daily logs, focus board | partial          |

### Source tier (`sources/`)

Raw, unprocessed material with minimal metadata. When something enters the vault from
outside (a PDF, a chat transcript, a pasted email, a voice memo), the original lands
in `sources/` and a synthesised Wiki article links back to it.

**Layout:**

```
sources/
├── YYYY/
│   └── YYYY-MM-DD-<short-slug>.<ext>     # the original file
├── YYYY/
│   └── YYYY-MM-DD-<short-slug>.meta.yaml # tiny sidecar with origin/date/one-line desc
└── _index.md                              # generated index
```

**Sidecar `*.meta.yaml` schema:**

```yaml
date: YYYY-MM-DD          # when the source was captured
origin: pdf | transcript | paste | email | voice | web
title: "One-line description"
linked_articles: []        # slugs of Wiki articles synthesised from this source
sensitivity: normal        # normal | sensitive | credential
```

Wiki articles synthesised from a source link back via the existing `source_ref` field:

```yaml
source: filed-document
source_ref: "sources/2026/2026-04-26-renovation-quote.pdf"
```

**Why a Source tier matters:** synthesised articles carry one agent's interpretation.
Keeping the original means a future "deep reindex" can re-process all sources with a
better model or different synthesis strategy, and verification against the original is
always possible.

### Wiki tier (domain folders)

Synthesised, durable knowledge articles and entities. One markdown file per topic with
YAML frontmatter. This is the largest tier. See **Domain Map**, **Article Frontmatter
Schema**, and **Naming Conventions** below.

### Scratch tier

Working memory the agent and user use day-to-day. Smaller, faster-changing, often dated:

- `core/` — always-load context (whoami, preferences, active-context, key-people)
- `episodes/YYYY/YYYY-QN/` — dated event records ("what happened, when, with what outcome")
- `work-log/YYYY/YYYY-QN/` — one file per active day (`projects_touched[].kind` is the
  signal that drives project-status inference)
- `tasks/` — todo-list, day-board

---

## Folder structure (top-level)

The vault lives inside a **project folder** alongside two siblings that hold
operational metadata. `vault/` itself is pure knowledge content — `tar`,
`grep`, `rsync`, or `git` of `vault/` produces only real articles, never
soft-deleted bins or runtime caches.

**Inside `vault/` (knowledge content only):**

```
vault/
├── core/                # always-load context (4-5 small files)
├── sources/             # raw ingested material (Source tier)
├── episodes/            # dated event records
├── work-log/            # daily structured work logs
├── tasks/               # todo-list.md, day-board.md
├── exports/             # generated handoff bundles (regenerated each time)
├── <domain>/            # one folder per domain (see Domain Map)
└── ev-manifest.yaml     # portable machine-readable description of the vault
```

**Sibling folders (operational metadata):**

```
<project>/
├── vault/               # the vault (above)
├── _for-deletion/       # soft-delete bin (agent moves files here; user empties)
├── _cache/              # runtime caches (consolidation, project-status proposals)
└── _archive/            # (optional) user-managed long-term archive
```

The siblings sit next to `vault/` rather than inside it so that the vault stays
self-describing: anything under `vault/` is real knowledge content, anything
under a sibling is operational. Tools take `--vault <project>/vault` and find
the siblings via `<vault>.parent`.

### The `_for-deletion/` soft-delete convention

The agent **never deletes files**. When an article is superseded, duplicate, or
no longer wanted, it gets moved to `<project>/_for-deletion/` instead — a
**sibling** of `vault/`, not inside it. This is:

- **Safe** — moves are reversible; deletes are not. If the agent gets it wrong,
  the user just moves the file back.
- **Tidy** — the folder is outside the vault, so tools never walk it. Indexes,
  queries, and the dashboard all see only `vault/` content; soft-deleted files
  disappear from the vault's behaviour entirely.
- **Frictionless** — no shell scripts, no permission dance, no
  platform-specific deletion APIs. A plain `mv` works on every host the vault
  runs on.

The agent works inside `vault/`, so a soft-delete is typically:

```bash
mv vault/path/to/article.md ../_for-deletion/path/to/article.md
```

(The `..` because the agent's working directory is the vault. The relative
path from inside the vault is `../_for-deletion/`.)

The user empties `<project>/_for-deletion/` periodically — typically as part of
a sweep, or via Finder / `rm -rf` from a terminal. The agent never empties it;
that's the user's decision.

When the agent moves something, it logs the move with a one-line confirmation:
`✓ Moved projects/old-stub.md → ../_for-deletion/`. The move is treated like
any other write — confirm before doing it, present the change, then commit.

The dashboard files live alongside the vault but outside it (in the project
repo's `dashboard/` folder).

---

## Domain Map

The default domain map ships sensible categories that work for most people. Add or
remove domains in `ev-manifest.yaml` to fit your life.

| Slug             | What goes here                                                                  |
|------------------|----------------------------------------------------------------------------------|
| `core`           | **Always-load context.** Identity, preferences, active priorities, key people.  |
| `concepts`       | Ideas → projects, the user's thinking pipeline (see Concepts Hierarchy below)   |
| `projects`       | Active and past projects (with code, deliverables, or scope)                    |
| `health`         | Personal medical, fitness, GP, prescriptions                                    |
| `finance`        | Mortgages, taxes, bank accounts, budgeting                                      |
| `hobbies`        | Personal interests and activities                                               |
| `household`      | Property, utilities, maintenance, appliances                                    |
| `it-setup`       | Home network, computers, automation, remote access                              |
| `work`           | Employment, current role, freelance / client work                               |
| `vehicles`       | Cars, vans, MOT, breakdown, vehicle tech                                        |
| `pets`           | Pet health, vet, prescriptions, insurance                                       |
| `holidays`       | Trips — one subfolder per trip (e.g. `holidays/seville-2026/`)                  |
| `family`         | Family members, contacts, shared arrangements                                   |
| `legal`          | Wills, contracts, legal correspondence                                          |
| `purchases`      | Subscriptions, receipts, warranties, renewals                                   |
| `professional`   | Qualifications, CV, certifications, training                                    |
| `skills-catalog` | Portable repository of installable LLM skills (source + README + install bundle) |
| `episodes`       | Dated event records (Scratch tier)                                              |
| `work-log`       | Daily record of work done (Scratch tier)                                        |
| `holding-pen`    | Not yet classified — triage later                                               |

Cross-domain items use multiple slugs in `domains:` list. Example: a smart-home laser
cutter article might live under `[hobbies, it-setup]`.

### Concepts Hierarchy

The `concepts` domain captures the user's thinking pipeline as a four-tier ladder:

```
insight   →  An observation, pattern, or nugget worth noting
concept   →  A crystallised principle or design approach
idea      →  A specific possibility with enough shape to explore
project   →  Something with scope, intent, and (often) code
```

Items are promoted up the ladder over time via the `tier` field. Link child items to
parents via `parent`.

**Project lifecycle statuses (five-slot pipeline):** `ideas` · `prototype` ·
`under-development` · `delivered-and-operational` · `delivered-and-parked`.

Legacy values coerced to the current slot: `seed` → `ideas`, `developing` →
`under-development`, `active` → `under-development`, `delivered` →
`delivered-and-operational`, `delivered-and-retired` & `parked` → `delivered-and-parked`.

### Concept membership and project membership (two checkboxes, not two folders)

An article with `tier: project` can appear in the **Concepts kanban**, the
**Projects kanban**, or both — controlled by which categories are listed in
its `domains:` field. The two memberships represent different kinds of
deliverable:

- **`concepts` membership** — the article documents thinking, a framework,
  a taxonomy, or a way of working. Output: reports, articles, principles,
  design notes.
- **`projects` membership** — the article tracks a functional deliverable.
  Output: code, hardware, a skill bundle, a service.

**Many articles are both.** A skill that ships with a SKILL.md (documenting
a way of thinking) AND a runnable code implementation is genuinely both a
concept project and a project project — tag it with both, and it appears in
both kanbans simultaneously. The status in each kanban is shared (one
`status:` field), so a single move-to action keeps both views in sync.

**File location follows the primary (first) domain.** If `domains: [concepts,
projects]`, the file lives at `concepts/<slug>.md` because `concepts` is
first. Reorder the list to flip the canonical home. The slug stays stable
across any rehoming so cross-references resolve.

**Toggling membership is a one-tick operation.** The dashboard's project and
concept cards each show two checkboxes — "concept" and "project" — that
add or remove the corresponding domain from the article's `domains:` list.
Behind the scenes it's a small frontmatter edit; the file doesn't move.
**Rehoming** the file (a heavier operation, used when the primary deliverable
shifts) is still the *Concept Promotion* workflow in `SKILL.md`.

---

## Article Frontmatter Schema

```yaml
---
title: "Human-readable title"
domains:
  - primary-domain
  - secondary-domain
type: fact | account | how-to | reference | log | contact

# Object identity (optional — defaults shown):
object_type: article           # article | entity | episode
id: null                       # Optional stable slug for cross-referencing

# Sensitivity (see Sensitivity Model below):
sensitivity: normal            # normal | sensitive | credential
retrieval_default: searchable  # always_load | searchable | on_explicit_request | never

# Linkage:
entity_refs: []                # Slugs/IDs of related entities, e.g. ["sam", "maria"]
relationships: []              # Typed links — see Relationship Types below
related: []                    # Simple "see also" links (no type)
parent: null                   # concepts domain only: slug of parent article

# Concepts-specific:
tier: null                     # insight | concept | idea | project
status: null                   # ideas | prototype | under-development | delivered-and-operational | delivered-and-parked
applies_to: null               # work | personal | both — scope of applicability (concepts domain)
development_platform: null     # tier:project only — see Development Platforms table

# Entity-specific (when object_type: entity):
entity_type: null              # person | account | vehicle | device | organisation | project
aliases: []

# Provenance:
source: conversation | upload | filed-document | manual
source_ref: "sources/YYYY/YYYY-MM-DD-slug.ext"   # ONLY for paths into the Source tier (raw ingested material)
code_path: null                                  # tier:project only — local code dir, e.g. "~/Developer/personal/MyApp"
github: null                                     # tier:project only — GitHub remote URL
location: null                                   # { lat, lng, label } for map-bearing articles
map_fav: false

# Timeline:
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
last_verified: YYYY-MM-DD
confidence: high | medium | low

# Domain-specific:
renewal_date: null
cost: null
provider: null

# Account-specific:
login_method: null             # email-password | apple | google | email-otp | authenticator-otp
password_manager: null
login_email: null

# Skills-catalog README fields (when domains includes skills-catalog):
skill_name: null
skill_version: null
skill_status: null             # active | archived | draft | deprecated
skill_install: null            # Relative path to install bundle

tags: []
---
```

### Type values

`fact` (dates, numbers, policy details) · `account` (service with login) ·
`how-to` (step-by-step) · `reference` (background info) · `log` (chronological) ·
`contact` (person/org details).

### Confidence values

`high` (verified from document) · `medium` (from conversation, believed correct) ·
`low` (uncertain, from memory, needs checking).

### Staleness rule

Flag as potentially stale if `last_verified` is more than 6 months ago, or if
`renewal_date` has passed.

---

## Episode Frontmatter Schema

```yaml
---
title: "Short description of what happened"
domains: [<relevant-domain>, episodes]
type: log
object_type: episode
date: YYYY-MM-DD
actors: [user]                  # Who was involved (entity slugs)
entity_refs: []                 # Entities this relates to
article_refs: []                # Related Wiki articles (slugs or paths)
source_refs: []                 # Files in Source tier this episode references
outcomes:
  - What resulted from this event
follow_up: null                 # Next action if any, or "Chase by YYYY-MM-DD"
tags: []
sensitivity: normal             # normal | sensitive
retrieval_default: searchable
source: conversation
created: YYYY-MM-DD
confidence: high | medium | low
---
```

---

## Relationship Types

Used in the `relationships` field to express how articles connect semantically:

| Type          | Meaning                                  | Typical use                                |
|---------------|------------------------------------------|---------------------------------------------|
| `supports`    | Provides evidence or foundation for      | Insight → concept it underpins              |
| `extends`     | Builds on, takes further                 | Idea that expands an existing concept       |
| `supersedes`  | Replaces, makes obsolete                 | New approach replacing an old one           |
| `contradicts` | Conflicts with — both claims preserved   | Conflicting evidence or advice              |
| `refines`     | Clarifies, improves, narrows             | Sharpened understanding of a concept        |
| `implements`  | Concrete realisation of                  | Project that implements an idea             |
| `inspires`    | Loosely influenced by                    | One concept that sparked another            |

Relationships are **directional** — if A `supports` B, B does not automatically support A.

Use `related` for simple "see also" links where type doesn't matter. Use `relationships`
when the nature of the connection is meaningful.

```yaml
relationships:
  - ref: capability-composability
    type: supports
  - ref: post-solve-knowledge-capture
    type: extends
```

---

## Sensitivity Model

| Level        | Meaning                                    | Retrieval                                                           |
|--------------|--------------------------------------------|---------------------------------------------------------------------|
| `normal`     | General personal info                      | Searchable by default                                               |
| `sensitive`  | Medical, legal, financial, identity docs   | Searchable but flagged. Excluded from workspace packs unless requested. |
| `credential` | Passwords, recovery codes, API keys        | **Never loaded by default.** Only on explicit request. Never in exports. |

Default: `normal`. Only tag `sensitive` or `credential` when genuinely warranted.

---

## Change History Pattern

When a fact changes over time (medications, providers, addresses, subscriptions), keep
frontmatter for the current state and add a Change History table in the body:

```markdown
## Change History

| Date       | Change                                          | Source                | Confidence |
|------------|-------------------------------------------------|-----------------------|------------|
| 2026-04-25 | Stopped previous medication after GP review     | GP appointment        | High       |
| 2026-01-01 | Started on current dose                         | Filed prescription    | High       |
```

**Use Change History for:** medications, address changes, provider changes, subscription
state changes, insurance policy changes, device ownership, project status transitions.

**Don't use it for:** static reference text, how-to guides, contact details that simply
get corrected rather than changing over time.

---

## Naming Conventions

File names are lowercase, hyphen-separated, descriptive slugs.

| Object              | Path                                                                      |
|---------------------|---------------------------------------------------------------------------|
| Article             | `<vault>/<primary-domain>/<filename>.md`                                  |
| Article (sub-folder)| `<vault>/<domain>/<sub-folder>/<filename>.md`                             |
| Article (holiday)   | `<vault>/holidays/<trip-slug>/<filename>.md`                              |
| Episode             | `<vault>/episodes/YYYY/YYYY-QN/YYYY-MM-DD-short-description.md`           |
| Work log entry      | `<vault>/work-log/YYYY/YYYY-QN/YYYY-MM-DD.md`                             |
| Source file         | `<vault>/sources/YYYY/YYYY-MM-DD-short-slug.<ext>`                        |
| Skills catalog      | `<vault>/skills-catalog/<skill-slug>/` (folder)                           |

**Slug rule:** lowercase, hyphen-separated, meaningful (working codename, not slot
name), stable across title changes.

---

## Development Platforms

`development_platform` is a single lowercase-hyphenated value set on `tier: project`
articles. Open vocabulary, but the dashboard's filter chips read this list — keep it
tidy and add new platforms here when needed.

| Slug             | Tool                                |
|------------------|-------------------------------------|
| `claude-code`    | Claude Code CLI                     |
| `claude-cowork`  | Cowork                              |
| `claude-desktop` | Claude.ai chat                      |
| `cursor`         | Cursor IDE                          |
| `chatgpt`        | ChatGPT chat / Custom GPT           |
| `codex`          | OpenAI Codex CLI                    |
| `xcode`          | Apple Xcode                         |
| `arduino-ide`    | Arduino IDE                         |
| `platformio`     | PlatformIO in VS Code               |
| `vscode`         | VS Code (no specialised extensions) |
| `fusion360`      | Autodesk Fusion 360                 |
| `onshape`        | Onshape                             |
| `freecad`        | FreeCAD                             |
| `jupyter`        | Jupyter notebook                    |
| `home-assistant` | Home Assistant frontend / YAML      |
| `mixed`          | Multiple platforms                  |
| `unknown`        | No signal (use sparingly)           |

Estimate from: explicit mentions → `source_ref` folder convention →
project type → ask the user.

---

## Provenance fields — disambiguation

`source_ref`, `code_path`, and `github` are easy to confuse. Use exactly one:

| Field | Use for | Example |
|-------|---------|---------|
| `source_ref` | Path into the Source tier — a raw ingested file the article was synthesised from | `"sources/2026/2026-04-26-renovation-quote.pdf"` |
| `code_path` | `tier: project` only — local code directory the project's working copy lives in | `"~/Developer/personal/MyApp"` |
| `github` | `tier: project` only — GitHub remote URL for the project | `"git@github.com:username/MyApp.git"` |

**Rules of thumb:**

- An article synthesised from a PDF/transcript/paste → `source_ref` points into `sources/`
- A project article whose code lives on disk → `code_path` (and `github` if there's a remote)
- A project article that's purely planning/content (no runnable code) → neither `code_path` nor `github`
- **Never** put free-text descriptions in `source_ref`. If the source isn't a real file path,
  put the description in the article body (e.g. under a `## Provenance` heading) and leave
  `source_ref: null`.

## Backwards compatibility

All fields beyond title/domains/type are optional. Articles without them work fine.
Defaults:

- Missing `object_type` → `article`
- Missing `sensitivity` → `normal`
- Missing `retrieval_default` → `searchable`
- Missing `relationships` → empty list
