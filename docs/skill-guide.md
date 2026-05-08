# Skill Guide

The "skill" is what teaches an LLM how to operate the vault. It's a folder of markdown and Python:

```
skill/
├── SKILL.md             # behaviour spec — primitives, workflows, decision tree
├── SCHEMA.md            # data contract — frontmatter, domains, naming, sensitivity
├── PLATFORM-CLAUDE.md   # Claude / Cowork plumbing
├── PLATFORM-CURSOR.md   # Cursor plumbing
├── CHANGELOG.md         # version history
├── prompts/             # per-capability detail, loaded on demand
└── tools/               # eight Python scripts (see tool-reference.md)
```

`SKILL.md` is the contract. It teaches the agent the five primitives, the decision tree, the workflow vocabulary, and where to look for more detail. `SCHEMA.md` defines the shape of the data so the agent knows what counts as an article vs. an episode, what frontmatter is required, what sensitivity levels mean.

**The split matters.** `SKILL.md` and `SCHEMA.md` are entirely platform-independent — any LLM that can read markdown can use them. The `PLATFORM-*.md` files isolate everything that varies per host: vault probing, dashboard launch, plugin install, voice-inbox wiring. To support a new platform you write a new `PLATFORM-<NAME>.md`; you never edit the core. Today there are two: `PLATFORM-CURSOR.md` (covers Cursor, Codex CLI, VS Code with MCP, and similar IDE-style hosts) and `PLATFORM-CLAUDE.md` (Claude Code and Cowork). Adding more is just file authorship.

## The five primitives

Everything the agent does decomposes into five operations:

- **Read** — query the vault (`query.py`, board reads, core memory)
- **Write** — create or update articles, episodes, work-log entries (`ingest.py`)
- **Maintain** — surface stale, missing, broken, or convergent content (`curate.py`, `consolidate.py`, `index_builder.py`)
- **File** — bridge an external document into the Source tier and write a synthesised article (`file_handler.py`)
- **Execute** — run a side-effecting tool (open the dashboard, infer project status, edit the day board)

## Composed workflows

Higher-level sequences that the user can invoke in one phrase:

- **Sweep** — voice-inbox + active-context delta + curate + consolidate + reindex + report.
- **Work Log** — end-of-day pass that writes a structured work-log file and a daily-summary episode.
- **Day Board** — the focus board: assign slots, edit slot fields, mark done, manage today's todos.
- **Project Status** — nightly rule engine that infers `prototype` / `under-development` / `delivered-and-parked` transitions from activity signals.
- **LLM Selector** — given a task, recommend which model to use, scored from `vault/it-setup/llm-selector/llm-scores.yaml`.

## Decision tree (in brief)

A question routes to **Read**. A fact, event, or thought routes to **Write** (with a scan first to avoid duplicates, and a ripple scan after). A document routes to **File**. A "review / clean up / what's converging" phrase routes to **Maintain**. Slot edits, dashboard launches, and status passes route to **Execute**.

The full version with phrasing and edge cases lives in `skill/SKILL.md` § Decision tree. The skill loads it on session start.

## Installing the skill

The platform-specific files in `skill/PLATFORM-*.md` are the canonical install instructions for each host. The summaries below are the one-paragraph version.

### Cursor / Codex CLI / VS Code with MCP / similar IDE-style hosts

These hosts don't have plugin loaders; the integration patterns are symlink-the-folder or wrap-the-tools-as-MCP. Practical options:

```bash
# Symlink the skill folder into a convention location (Cursor example)
ln -s ~/Documents/everything-vault/skill ~/.cursor/skills/everything-vault
```

Or use the host's workspace settings to make the skill folder always part of context. For deeper integration, wrap the tools as an MCP server — the Python scripts have no external dependencies, so it's a one-file server, not a project. The same pattern works for Codex CLI, VS Code with MCP support, and other IDE-style hosts. See `skill/PLATFORM-CURSOR.md` for the full picture.

### Claude Code or Cowork

The skill installs as a `.plugin` zip. Build it with the script in `PLATFORM-CLAUDE.md` § 6, then present the file via Cowork's `mcp__cowork__present_files`. The user clicks **Install / Update** on the resulting card. For the Cowork-specific plumbing — manifest format, validator gotchas, the `.skill` fallback when validation fails — read `skill/PLATFORM-CLAUDE.md` carefully; it's been hard-won from real install attempts.

For Cowork specifically, you can also drop the unpacked skill folder directly into the Cowork plugins location instead of building a zip — useful during development.

For Claude Code without Cowork, a built `.plugin` file installs via the CLI:

```bash
claude plugin install /path/to/everything-vault-1.0.0.plugin
```

### ChatGPT, Gemini, local models, anything else

Any LLM that can read markdown and follow instructions can use the vault. The integration is just paste:

1. Paste `skill/SKILL.md` and `skill/SCHEMA.md` as custom instructions or a system prompt.
2. Paste the relevant `prompts/*.md` files when triggering specific workflows (e.g. paste `prompts/sweep-prompt.md` before asking for a sweep).
3. The Python tools are still callable from the command line — the LLM just needs to know they exist and what flags they take.

If you can run the tools yourself from a terminal and paste the output back, you can get most of the value. The skill is designed for graceful degradation, not magic.

## Adapting for a read-only or restricted LLM

The skill is designed to degrade across capability tiers:

**No file access.** Paste the relevant article text into the chat, work on it textually, copy the result back to disk yourself. You lose the scan/ripple/index automation, but the conversation logic still works.

**No shell access.** Run the tools yourself, paste the output. The agent reads the JSON or text, suggests next actions, you commit them. This is how it works on chat-only platforms like ChatGPT or Gemini's web UI today — slightly more friction than a host with native shell access, still useful.

**No tool calling at all.** The schema is plain markdown + YAML, so even a chat-only LLM can produce well-formed articles by reading `SCHEMA.md`. You drop them into the right folder yourself.

The lowest-common-denominator workflow — "paste, edit, commit" — works on every LLM. Anything beyond that is automation on top.

## Where to read more

- The decision tree, primitive specs, and full workflow definitions: `skill/SKILL.md`
- Frontmatter, domain map, sensitivity, naming: `skill/SCHEMA.md`
- Per-capability detail (one prompt per workflow): `skill/prompts/*.md`
- Per-tool CLI: [tool-reference.md](tool-reference.md)
- Customisation: [customisation.md](customisation.md)
