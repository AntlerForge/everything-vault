# FAQ

### Can I use this without an LLM?

Yes. The vault is just markdown — open any file in any text editor and you've got everything. The Python tools in `skill/tools/` are usable from the command line on their own (see [tool-reference.md](tool-reference.md)). You'll do day-to-day capture and querying more slowly than with an LLM, but nothing is locked behind one.

### Does my data leave my machine?

No. There's no telemetry, no cloud sync, no analytics. The skill runs locally inside whatever LLM client you use. The dashboard runs on `localhost:8077`. The Python tools touch your filesystem only. Tailscale Funnel (opt-in) is the only network-facing piece — see [dashboard-guide.md](dashboard-guide.md).

### Can I sync across devices?

Yes — any sync method that handles a folder of markdown: iCloud, Dropbox, Syncthing, Git, rsync. The dashboard's `ev-data.json` is regenerated on each device, so no merge conflicts on the cache file.

Git is the most common pattern — free history, easy rollback. Add `dashboard/ev-data.json` and the `<project>/_cache/` folder to `.gitignore` since they're generated.

### Which LLMs work?

Any LLM that can read markdown and follow instructions. Best-tested with Claude (Opus/Sonnet); works with GPT-5, Gemini Pro, and capable local models. The capability gap shows up most in nuanced curation and consolidation — bigger models notice subtler convergence patterns and write better Change History rows. Straight read/write is fine on any frontier model.

### How big can the vault get?

The original system has run with 150+ articles, 50+ episodes — no performance issues. Linear scans (`query.py`, `curate.py`, `consolidate.py`) get noticeably slower past a few thousand articles; at that point add an index file or move to a real search backend.

### What if the YAML frontmatter is wrong?

The lightweight parser in `dashboard/build_dashboard.py` is forgiving but skips files it can't parse — they just don't appear in `ev-data.json`. Run

```bash
python3 skill/tools/curate.py --validate
```

to find broken frontmatter. The validate pass reports missing required fields, malformed YAML, and inconsistent values.

### How do I back up?

Same as any folder of markdown. Git is the most common pattern — the diff history doubles as a Change History audit trail. Time Machine, restic, or rsync all work too. There's no special vault format to worry about.

### What if the agent deletes something I wanted to keep?

It can't — the agent never deletes. When something is superseded, duplicated, or retired, it gets moved to `<project>/_for-deletion/` instead. That folder is a **sibling** of `vault/` (not inside it) and lives outside the vault's walk path entirely, so the file is "gone" from the vault's point of view but still on disk. Move it back to its original folder if the agent got it wrong. You empty `_for-deletion/` yourself periodically; the agent never does. See `docs/vault-structure.md` § "`_for-deletion/` — soft-delete (sibling of vault/)" for the full convention.

### Can I use Obsidian alongside this?

Yes. The vault is just markdown, and Obsidian opens any folder of markdown. You'll want to disable Obsidian's wikilink-creation features so it doesn't try to "fix" relative-path references in the vault — the EV schema uses plain relative paths, not `[[wiki-style]]` links. Obsidian's graph view, search, and editor all work fine on top.

### Why YAML instead of TOML or JSON for frontmatter?

YAML is the standard for markdown frontmatter — Jekyll, Hugo, MkDocs, Pandoc, Obsidian, GitHub all use it. It's the path of least surprise and means any existing tool that reads markdown frontmatter Just Works on the vault.

### What's the deal with episodes vs. articles?

Articles hold facts that are true now. Episodes record events that happened. If you change medication, both happen — the article (current prescription) is updated, and an episode (the event of changing) is written. The article answers "what am I taking?"; the episode answers "when did I switch?". They link via `article_refs:` in the episode frontmatter.

The split is what lets the project-status rule engine work — it counts activity from episodes and work-log entries while the article holds the current state. See `skill/SCHEMA.md` § Three tiers.

### Is there a search?

Three layers: `query.py` (keyword + frontmatter scoring, the agent's default), the dashboard's in-page filter, and `ripgrep` for full-text — `rg "term" ~/Documents/everything-vault/vault` covers anything the others miss. There's no built-in full-text index; if you want one, point ripgrep at the vault folder.

### What if I want to start over?

Run `./purge-example-data.sh` to clear the included example content while keeping the folder structure (vault/ + sibling _for-deletion/ + _cache/). Or delete the project folder entirely and re-run `./setup.sh`.

### How do I extend it?

Most extensions are markdown edits — new domains, new prompt files, custom frontmatter. See [customisation.md](customisation.md). For deeper changes (new dashboard views, mutation endpoints, tools), the codebase is small enough to read end-to-end in an afternoon.
