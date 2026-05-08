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

This file lives in `_for-deletion/`. It exists to show two things:

1. **The exclusion works.** Run `python3 skill/tools/query.py --vault example-vault --keyword "soft-delete-demo"` from the project root and this article does **not** appear in the results — every tool excludes paths inside underscore-prefixed folders.

2. **The folder is preserved across resets.** The `purge-example-data.sh` script wipes the example data but keeps `_for-deletion/` (and its README) so the convention stays in place when you start your own vault.

Delete this file whenever you like — it has no purpose beyond demonstrating the soft-delete bin. A plain `rm vault/_for-deletion/test-soft-deleted.md` from a terminal removes it; the included `purge-example-data.sh` script will also clear it on reset.
