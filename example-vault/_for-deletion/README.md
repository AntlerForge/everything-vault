# `_for-deletion/` — soft-delete bin

This folder is the soft-delete bin for the vault.

When the agent supersedes, deduplicates, or retires an article, it moves the
file here instead of deleting. That's safer (the move is reversible), tidier
(every tool excludes this folder from indexing, queries, and the dashboard),
and platform-independent (a plain `mv` works on every host).

The agent **never empties this folder.** That's your decision. When you're
satisfied nothing in here is needed:

```bash
rm -rf vault/_for-deletion/*
```

…or just empty it through Finder / your file manager.

The underscore prefix is what makes the exclusion work — every tool in
`skill/tools/` and the dashboard build script skip any path that contains a
folder beginning with `_` or `.`. If you create your own internal folders
(caches, scratch, archives) and want them ignored too, prefix them the same
way (`_archive/`, `_scratch/`, etc.).

This README is the only file you'll find here on a fresh vault. After a
sweep or two, expect to see retired articles starting to accumulate.
