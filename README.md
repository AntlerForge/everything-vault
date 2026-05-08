# Everything Vault

**A local-first personal knowledge management system built on plain markdown files. Works with any LLM. Your data stays yours.**

Everything Vault (EV) is a structured way to keep track of the bits of your life that LLMs are now smart enough to actually help you manage — health, finance, projects, ideas, household admin, hobbies, all of it. The vault is just markdown files with YAML frontmatter, organised by domain. The skill teaches any LLM how to query, update, and curate it through natural conversation. The dashboard gives you a visual view: kanban boards for your projects and ideas, a focus board for today, a timeline of what's happened, and stats on what's active.

It's not a notes app. It's a small, opinionated framework that turns "the kind of stuff you'd write in a notebook" into something an AI can actually be useful with — without your data ever leaving your machine.

Screenshot placeholders live in [docs/screenshots](docs/screenshots/README.md).

> **Adding screenshots:** drop PNGs into `docs/screenshots/` named `dashboard-preview.png`, `concepts-kanban.png`, `day-board.png`, `timeline.png`. The README and docs reference these paths but ship without images.

## Quick start

```bash
# 1. Clone
git clone https://github.com/AntlerForge/everything-vault.git
cd everything-vault

# 2. Run the interactive setup (asks where to put your vault, creates the structure)
./setup.sh

# 3. Launch the dashboard
./dashboard/ev-dash
```

That's it. The setup script offers to populate your vault with the included example data (the Alex Chen persona) so you can see every feature working before you write a single article of your own. When you're ready to start fresh, run `./purge-example-data.sh`.

If you'd rather not run shell scripts, the [Getting Started guide](docs/getting-started.md) walks through the manual steps.

## What you get

**Example data** — `example-vault/` is the standalone demo vault used by the quick-start commands. `example-project/` shows the fuller project-folder layout with a `vault/` plus sibling `_for-deletion/` and `_cache/` folders. Both use the fictional Alex Chen dataset so you can explore the system before writing your own articles.

**The skill** — `skill/SKILL.md` plus a schema, two platform-specific docs (Claude/Cowork and Cursor), and 11 prompt files that teach an LLM how to operate the vault. Drop the folder into Claude Code, Cursor, or use the prompts as ChatGPT custom instructions — any LLM that can read markdown can use it.

**Eight Python tools** — `query`, `ingest`, `curate`, `consolidate`, `file_handler`, `index_builder`, `board`, and `project_status`. No pip dependencies for the core (PyYAML optional). The skill's tools are also callable directly from the command line if you want to.

**A dashboard** — `dashboard/dashboard.html` is a single-file HTML/JS dashboard. The build script walks your vault, generates JSON, serves it over HTTP, and exposes mutation endpoints for moving cards between kanban columns, editing tasks, and updating the day board. Designed accessibly — the colour palette is red/green colour-blind safe by default.

**Setup and purge scripts** — `setup.sh` walks you through configuration. `purge-example-data.sh` clears the example content while preserving the structure, ready for your own data.

## Why this exists

Personal knowledge management has been a solved problem for forty years if you don't mind doing the work yourself. Notion, Obsidian, plain text in iCloud — any of them work fine. What changed is LLMs. They're now capable enough to do the dull half of PKM for you: finding the right article, capturing a quick fact in the right place, noticing that this new piece of info contradicts the old one, surfacing things going stale.

But the LLMs work best when the underlying data has *structure* — not so rigid you can't write freely, but enough that the LLM knows what's an article, what's an event, what's an idea, what's a renewal date. Everything Vault is the smallest amount of structure that makes that work, expressed in plain markdown so it never locks you in.

## Philosophy

**Local-first.** Your data is on your machine. No cloud, no telemetry, no tracking. Sync via any method you trust (iCloud, Dropbox, Syncthing, Git).

**Plain markdown + YAML.** The format outlives any tool. You can read your vault in any text editor; you can grep it from the command line; you can rsync it to another machine and keep working.

**Three tiers** — `Source` (raw originals, never touched), `Wiki` (synthesised articles, the durable knowledge), `Scratch` (working memory: episodes, work logs, the day board). Synthesised articles are always re-derivable from raw sources, so you can re-process them with a better model later.

**Five primitives, not fifty features** — Read, Write, Maintain, File, Execute. Higher-level workflows like Sweep and Work Log are pre-composed sequences of these primitives, named so you can invoke them in one phrase ("EV sweep", "close out today").

**Read-mostly maintenance.** The vault never auto-merges, auto-deletes, or auto-rewrites your core memory. Curation surfaces findings; you decide.

## How it works with LLMs

The skill folder is the contract. **SKILL.md** teaches an LLM the five primitives, the decision tree, and the workflow vocabulary — entirely platform-independent. **SCHEMA.md** defines the shape of the data — also platform-independent. Eleven prompt files in `skill/prompts/` provide per-capability detail loaded on demand. Anything that varies by LLM platform — how plugins install, how the dashboard launches, how a voice inbox is wired — lives in a `PLATFORM-<name>.md` companion file. Adding support for a new platform means writing one of those; the core never changes.

Integration paths bundled today:

- **Cursor / Codex CLI / VS Code with MCP / any IDE-style host:** symlink the skill folder, or wrap the tools as an MCP server. See [skill/PLATFORM-CURSOR.md](skill/PLATFORM-CURSOR.md).
- **Claude Code / Cowork:** the skill installs as a plugin. See [skill/PLATFORM-CLAUDE.md](skill/PLATFORM-CLAUDE.md).
- **ChatGPT, Gemini, local models, anything else:** point the model at SKILL.md and a few prompt files; ask it to follow them. The Python tools are still callable from the command line — the LLM just needs to know they exist. See [docs/skill-guide.md](docs/skill-guide.md) for the adaptation patterns.

Want a different platform supported first-class? Write a `PLATFORM-<NAME>.md` mirroring the structure of the two we ship — vault probing, dashboard launch, install/update, anything platform-specific. Pull requests welcome.

The skill knows how to introduce itself to an unfamiliar LLM: it reads SKILL.md, loads core memory (`whoami.md`, `preferences.md`, `active-context.md`, `key-people.md`), and is ready to answer questions about your life within seconds.

## Documentation

- [Getting Started](docs/getting-started.md) — first-run guide, step by step
- [Vault Structure](docs/vault-structure.md) — the three-tier model, domains, frontmatter, naming
- [Dashboard Guide](docs/dashboard-guide.md) — every view explained, mutation endpoints, mobile, remote access
- [Tool Reference](docs/tool-reference.md) — every CLI tool with examples
- [Skill Guide](docs/skill-guide.md) — using the skill with Claude, Cursor, and other LLMs
- [Customisation](docs/customisation.md) — adding domains, extending the schema, theming
- [Scheduled Tasks](docs/scheduled-tasks.md) — automated maintenance (work log, project status, LLM scores)
- [Example Session](docs/example-session.md) — a realistic transcript of working with EV
- [FAQ](docs/faq.md) — common questions and troubleshooting

## Origin

Everything Vault grew out of a personal knowledge management system built and refined over several months of daily use with Claude. It's been battle-tested across 150+ articles and dozens of composed workflows before being extracted, scrubbed of personal data, and published as a generic, public template. The original maintainer's vault stays private; this repo is the cleaned, generalised version anyone can clone and start using.

## Contributing

Issues and pull requests welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. The principles to keep in mind: stay local-first, stay simple, prefer plain markdown to fancy formats, and treat the user's data with respect.

## License

MIT — see [LICENSE](LICENSE).
