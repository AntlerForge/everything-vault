# `_for-deletion/` — soft-delete bin

This folder is the soft-delete bin for the vault. It lives as a SIBLING of
`vault/` (not inside it), so `vault/` stays purely knowledge content.

When the agent supersedes, deduplicates, or retires an article, it moves the
file here instead of deleting. That's safer (the move is reversible), tidier
(the folder is outside the vault, so tools never walk it), and
platform-independent (a plain `mv` works on every host).

From inside the vault the agent does:

```bash
mv vault/path/to/article.md ../_for-deletion/path/to/article.md
```

The `..` is because the agent's working directory is `vault/`; the relative
path to this folder is `../_for-deletion/`.

The agent **never empties this folder.** That's your decision. When you're
satisfied nothing in here is needed:

```bash
rm -rf <project>/_for-deletion/*
```

…or just empty it through Finder / your file manager.

There's also a path-level safety net inside the tools: any path containing a
folder beginning with `_` or `.` is skipped during a vault walk. So if you
create stray `_*/` folders inside `vault/` (a `_scratch/`, an `_archive/` you
forgot to put as a sibling), they're still excluded automatically.

This README is the only file you'll find here on a fresh project. After a
sweep or two, expect to see retired articles starting to accumulate.
