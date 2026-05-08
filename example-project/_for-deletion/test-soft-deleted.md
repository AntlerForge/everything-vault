---
title: "Example soft-deleted article (delete me whenever)"
domains: [holding-pen]
type: reference
sensitivity: normal
created: 2026-05-07
last_updated: 2026-05-07
last_verified: 2026-05-07
confidence: low
source: manual
tags: [example, soft-delete-demo]
---

<!-- EXAMPLE: This file demonstrates what a soft-deleted article looks like.
     The agent moved it here instead of deleting it. Notice it doesn't show
     up in the dashboard, in queries, or in any indexes — every tool excludes
     paths under `_*/` folders. -->

# Example soft-deleted article

This file lives in `<project>/_for-deletion/` — a SIBLING of `vault/`, not inside it. It exists to show two things:

1. **The exclusion works.** Run `python3 skill/tools/query.py --vault example-project/vault --keyword "soft-delete-demo"` from the project root and this article does **not** appear in the results — tools walk only `vault/`, so this folder is invisible to them by definition.

2. **The folder is preserved across resets.** The `purge-example-data.sh` script wipes the example data but keeps `_for-deletion/` (and its README) so the convention stays in place when you start your own project.

Delete this file whenever you like — it has no purpose beyond demonstrating the soft-delete bin. A plain `rm <project>/_for-deletion/test-soft-deleted.md` from a terminal removes it; the included `purge-example-data.sh` script will also clear it on reset.
