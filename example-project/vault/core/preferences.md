---
title: "Vault preferences"
domains: [core]
type: reference
sensitivity: normal
retrieval_default: always_load
created: 2026-01-15
last_updated: 2026-04-28
last_verified: 2026-05-07
confidence: high
source: manual
tags: [preferences, conventions]
---

<!-- EXAMPLE: This article demonstrates how the user encodes their working preferences for any agent operating the vault. -->

# How I like the vault operated

## Communication style

- Concise, no fluff. Skip the throat-clearing and the "great question" preamble.
- If you're unsure, say so once, then propose a plan. Don't ask three questions
  in a row.
- British English spelling.

## Domain conventions

- Anything cross-domain (e.g. kitchen renovation that touches both household
  and projects) lists both slugs in `domains`.
- Concepts use the four-tier ladder: `insight` → `concept` → `idea` → `project`.
- I keep most ideas as `tier: idea, status: ideas` for a while before committing
  to project status.

## Tagging style

- Lowercase, hyphenated, sparing. A handful per article — not thirty.
- Reuse existing tags rather than inventing close synonyms.

## Files and code — storage convention

The four-pillar rule, easy to remember:

- **Runnable code** → `~/Developer/` (local SSD, GitHub remote). Personal
  projects under `~/Developer/personal/`, client work under `~/Developer/clients/`.
- **Non-code project artefacts** (planning docs, drafts, design files) →
  `~/Documents/Projects/<project-slug>/`.
- **Life admin** (the vault itself, scanned PDFs, receipts) →
  `~/Documents/Admin/`.
- **Session-generated files** (output from a coding/agent session that's not
  yet sorted) → `~/Documents/Outputs/`. This is an inbox, not a permanent
  home — empty it weekly.

Project articles in the vault use `code_path:` to record where the code lives
and `github:` for the remote. Inbox-style scratch in the vault starts in
`holding-pen/` and gets triaged weekly.

## Soft-delete: never delete, move to `_for-deletion/`

When something needs to go — superseded, duplicate, no longer wanted — move
the file to `<project>/_for-deletion/` (a SIBLING of `vault/`, not inside it)
instead of deleting. From inside the vault that's
`mv vault/path.md ../_for-deletion/path.md`. It's safer (I can move it back),
tidier (the folder is outside the vault, so tools never walk it), and works
the same way on every host. I empty the folder myself periodically, usually
as part of a sweep.

For drafts and uncertain content, mark them `confidence: low` and leave them
in place — I'd rather review a flagged draft than discover a deleted one.
