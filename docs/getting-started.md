# Getting Started

This is the first-run guide. By the end of it you'll have a working vault, a dashboard you can open, and enough understanding to point an LLM at it and start asking questions.

## Prerequisites

- macOS or Linux (tested on macOS; Linux should work but the dashboard launcher uses `open` which is macOS-specific — Linux users get `xdg-open` automatically).
- Python 3.8 or later. Check: `python3 --version`.
- A modern browser (any).
- An LLM you can paste markdown into. Claude Code, Cursor, ChatGPT, Gemini, or anything similar. The vault works without an LLM, but the LLM is the point.

PyYAML is **optional** — the tools fall back to a lightweight YAML parser if it isn't installed. Install it with `pip3 install pyyaml --user` if you want slightly faster parsing on large vaults.

## The five-minute path

```bash
git clone https://github.com/AntlerForge/everything-vault.git
cd everything-vault
./setup.sh
```

`setup.sh` is interactive and will:

1. Ask where to put your **project folder**. Default: `~/Documents/everything-vault/`. The script creates `<project>/vault/` (the actual vault), plus two siblings — `_for-deletion/` (soft-delete bin) and `_cache/` (runtime caches). The paths are remembered in a tiny `.ev-config` file at the project root.
2. Offer to copy the example data (the Alex Chen persona). Say yes the first time — it's the easiest way to see every feature working.
3. Build the initial indexes.
4. Offer to launch the dashboard. Say yes — it'll open in your browser at `http://localhost:8077`.

If anything goes wrong, the script prints clear errors. Re-running is safe; it won't overwrite existing data without asking.

## What you get

Once setup completes, you have:

- A populated vault at the path you chose
- A dashboard server running on `localhost:8077` showing your articles, projects, day board, tasks, and timeline
- An `.ev-config` file at the project root recording your vault path

## The manual path

If you'd rather not run a shell script, here's the equivalent:

```bash
# 1. Decide where the project folder lives
export EV_PROJECT_PATH="$HOME/Documents/everything-vault"
export EV_VAULT_PATH="$EV_PROJECT_PATH/vault"
mkdir -p "$EV_VAULT_PATH" "$EV_PROJECT_PATH/_for-deletion" "$EV_PROJECT_PATH/_cache"

# 2. (Optional) copy the example project into it.
#    example-project/ ships vault/, _for-deletion/, and _cache/ as siblings.
cp -R example-project/. "$EV_PROJECT_PATH/"

# 3. Build the indexes (point --vault at <project>/vault, not <project>)
python3 skill/tools/index_builder.py --vault "$EV_VAULT_PATH"

# 4. Launch the dashboard
./dashboard/ev-dash
```

That's it. Setting `EV_VAULT_PATH` once means you can drop `--vault` from every subsequent command.

## Trying it with an LLM

The whole point is that the vault becomes useful when an LLM can read and update it for you. Everything Vault is platform-neutral — `SKILL.md` and `SCHEMA.md` work with any model that can read markdown. Only the install path varies:

### Cursor / Codex CLI / VS Code with MCP / similar

Read [skill/PLATFORM-CURSOR.md](../skill/PLATFORM-CURSOR.md). The short version: symlink the skill folder into your IDE's skills location, or wrap the tools as an MCP server.

### Claude Code or Cowork

Read [skill/PLATFORM-CLAUDE.md](../skill/PLATFORM-CLAUDE.md). The short version: zip the `skill/` folder into a `.plugin` file (the doc shows the script) and present it to Cowork via `mcp__cowork__present_files`. The skill auto-loads on the next session.

### ChatGPT, Gemini, local models, anything else

Open `skill/SKILL.md` and paste it into the model's custom instructions or system prompt. The model will read the five-primitive structure and start operating the vault. For specific capabilities (queries, ingest, sweeps), point it at the relevant `skill/prompts/<capability>-prompt.md` file. The Python tools are still callable from the command line — the LLM just needs to know they exist. See [skill-guide.md](skill-guide.md) for adaptation patterns.

### Adding a new platform

If your LLM platform isn't covered above, add a `skill/PLATFORM-<NAME>.md` mirroring the structure of the two we ship — covering vault probing, dashboard launch, and install/update for that platform. Nothing in `SKILL.md`, `SCHEMA.md`, or the prompt files needs to change.

## Try a query

With the example data in place:

```bash
python3 skill/tools/query.py --vault "$EV_VAULT_PATH" --question "recipe manager"
```

You should see eight matching results — articles, episodes, and an active project. That's the same query an LLM would make if you asked "what's the status on the recipe manager?".

Try a few more:

```bash
python3 skill/tools/query.py --vault "$EV_VAULT_PATH" --question "kitchen renovation"
python3 skill/tools/query.py --vault "$EV_VAULT_PATH" --episodes --question "japanese"
python3 skill/tools/query.py --vault "$EV_VAULT_PATH" --domain projects
```

## Create your first article

Two ways. The "let the tool do it" way:

```bash
python3 skill/tools/ingest.py write --vault "$EV_VAULT_PATH" \
  --title "My first article" \
  --domain projects \
  --type fact \
  --body "This is the body of the article."
```

The "do it yourself" way: open `$EV_VAULT_PATH/projects/my-first-article.md` in any editor, paste a YAML frontmatter block (copy the shape from any example article), write the body. The tools will pick it up next time you query.

After either approach, rebuild indexes:

```bash
python3 skill/tools/index_builder.py --vault "$EV_VAULT_PATH"
```

## Going further

- [Vault Structure](vault-structure.md) — the schema in depth
- [Dashboard Guide](dashboard-guide.md) — every view explained
- [Tool Reference](tool-reference.md) — the full CLI surface
- [Skill Guide](skill-guide.md) — using the skill with various LLMs
- [Example Session](example-session.md) — what working with EV looks like in practice
- [FAQ](faq.md) — common questions

## When you're ready to start fresh

The example vault is fictional. When you want it gone:

```bash
./purge-example-data.sh
```

This clears every example article, episode, and source, but preserves the folder structure and resets `core/` to placeholder templates. Your vault is then ready for your own content.
