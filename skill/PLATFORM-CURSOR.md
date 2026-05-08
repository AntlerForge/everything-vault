# Everything Vault — Platform Hooks: Cursor

*Everything in this file is Cursor-specific. The agent-behaviour and schema documents
(`SKILL.md`, `SCHEMA.md`) stay platform-independent.*

The hooks covered here:

1. Session start — finding the vault in a Cursor workspace
2. Workspace selection — what to do when EV isn't open
3. Dashboard launch via Cursor's terminal
4. Skill install / update flow
5. Bash tool access for tools

---

## 1. Session start: find the vault

Cursor opens one or more workspace folders. The vault may be one of them, a
subfolder of one, or not present at all. Check in this order:

1. **Workspace root.** If a workspace folder ends in `everything-vault/`, the vault is
   at `<that-folder>/vault/`.
2. **Workspace subfolder.** Glob for `**/everything-vault/vault/` from each open
   workspace root.
3. **Common local paths.** `~/Documents/everything-vault/vault/`, `~/everything-vault/vault/`.
4. **`EV_VAULT_PATH` environment variable.** If set, use that path directly.

Use a shell probe (`ls` / `test -d` via the Bash tool) — don't rely on memory of
where the vault was in a previous session.

When reporting paths to the user, use the human-readable host path (`~/Documents/...`)
rather than absolute system paths.

---

## 2. Workspace selection

If no vault path resolves, the user hasn't opened the EV folder in Cursor (or hasn't
run setup yet). In that case:

1. **Tell the user clearly.** Don't silently fail.
2. **Suggest the fix.** "I can't find your Everything Vault. Either open the
   `everything-vault` folder as a workspace in Cursor, or run `./setup.sh` from the
   project root if you haven't yet."
3. **If the user names a path**, accept it and probe again.

There is no equivalent to Cowork's `request_cowork_directory` in Cursor — the user
opens folders themselves via File → Open Folder. Don't try to mount or open folders
programmatically.

---

## 3. Dashboard launch

The Execute primitive's most-used target. The user says "open the dashboard", "show
me the dashboard", "EV dashboard", "launch the dashboard", "refresh the dashboard".

**Single shell call (via Bash tool):**

```bash
~/Documents/everything-vault/dashboard/ev-dash
```

If the path is different on the user's machine, substitute it. The `ev-dash` script
is fire-and-forget:

1. Kills any running dashboard server on port 8077
2. Rebuilds `ev-data.json` from the current vault state (always a fresh view)
3. Starts a new HTTP server detached in the background (`nohup` + `disown`)
4. Opens `http://localhost:8077` in the default browser
5. Returns immediately

Server log: `/tmp/ev-dashboard.log`. PID: `/tmp/ev-dashboard-server.pid`.

**Variants:**

- `ev-dash --stop` — kill the running server without relaunching
- `ev-dash --foreground` — blocking behaviour, stays attached
- `ev-dash --no-open` — rebuild + serve without opening the browser

**Why a script, not direct Python:** the script kills the previous server before
relaunching, so calling it twice in a row doesn't leave port 8077 occupied. Don't
manually start `python3 -m http.server` — `dashboard.html` needs the build server's
JSON endpoint.

If Cursor's Bash tool can't run shell scripts directly, invoke as
`bash ~/Documents/everything-vault/dashboard/ev-dash`.

---

## 4. Skill install / update — Cursor doesn't have a plugin loader

Cursor doesn't have an equivalent to Cowork's `mcp__cowork__present_files` for skill
installation. EV in a Cursor session is just a set of markdown files and Python
scripts the agent reads on demand — there's nothing to "install".

If the user wants to make EV available across all Cursor projects without re-opening
the folder each time, the practical options are:

1. **Workspace symlink.** Symlink the skill folder into Cursor's workspace settings
   so it's always part of context.
2. **Skill convention folder.** If the user has a `~/.cursor/skills/` convention,
   copy or symlink the skill folder there:

   ```bash
   ln -s ~/Documents/everything-vault/skill ~/.cursor/skills/everything-vault
   ```

3. **MCP server (advanced).** Wrap the skill's tools as an MCP server and configure
   it in Cursor's MCP settings. This exposes `query`, `ingest`, `curate`, etc. as
   first-class tool calls. The skill folder includes plain Python scripts that an MCP
   server wrapper can call directly. (See `docs/customisation.md` for guidance on
   building such a wrapper if needed.)

For most users, option 1 or 2 is enough — Cursor's agent reads the skill files when
the conversation context references them.

**Updates** are just `git pull` (if the user cloned the repo) or re-running setup.

---

## 5. Bash tool access

Cursor's Bash tool runs on the user's host machine, so:

- All shell commands work normally
- The `~` expansion resolves to the user's home directory
- The dashboard launcher can open the browser directly (no osascript wrapper needed)
- Python tools can be called by their full path:
  ```bash
  python3 ~/Documents/everything-vault/skill/tools/query.py --question "<q>"
  ```

If the user has set `EV_VAULT_PATH`, the tools' `--vault` argument is optional (they
read the env var). Otherwise pass `--vault <path>` explicitly:

```bash
python3 .../skill/tools/query.py --vault ~/Documents/everything-vault/vault \
    --question "When does my car insurance renew?"
```

---

## 6. File operations

Cursor's Edit and Write tools have direct access to the user's filesystem. Operating
on the vault is straightforward:

- Read articles with the standard Read tool
- Edit existing articles with the Edit tool (preserves formatting)
- Create new articles with the Write tool, but **prefer using `ingest.py`** — it
  handles frontmatter scaffolding, slug generation, and index updates automatically

The skill's tools are designed to be the primary interface for write operations.
Direct file edits work but bypass the validation and indexing the tools provide.

---

## 7. Differences from Cowork at a glance

| Feature | Cowork | Cursor |
|---------|--------|--------|
| Vault access | `mcp__cowork__request_cowork_directory` | Open folder via File → Open Folder |
| Sandbox model | Linux VM with mounts | Direct host filesystem |
| Dashboard launch | `osascript do shell script ".../ev-dash"` | Direct `ev-dash` via Bash |
| Skill install | `mcp__cowork__present_files` | Symlink / git clone / MCP wrapper |
| Browser access | Via osascript on host | Direct `open` command |
| Voice inbox | Apple Notes MCP if available | Not currently supported |

Most workflows are identical once the vault path resolves — the platform differences
are mostly in plumbing, not in agent behaviour.
