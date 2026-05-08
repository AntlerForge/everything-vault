# Everything Vault — Platform Hooks: Claude / Cowork

*Everything in this file is Claude/Cowork-specific. Porting EV to Codex, Cursor, or
ChatGPT means writing a sibling file (e.g. `PLATFORM-CODEX.md`) that covers the same
hooks in that platform's idiom. The agent-behaviour and schema documents stay identical.*

The hooks covered here:

1. Session start — finding the vault
2. Mounting the vault if it isn't accessible
3. Voice inbox via Apple Notes
4. Dashboard launch via osascript
5. Plugin install / update via `mcp__cowork__present_files`
6. Plugin bundle build (zip layout + `plugin.json` manifest)

---

## 1. Session start: find the vault

Before loading core memory or doing any work, verify the vault is accessible. If it
isn't, request the directory immediately — don't ask permission, just call the tool.

The skill cannot function without the vault mounted. In a fresh Cowork session the
user may not yet have selected a workspace folder, or may have selected a different
folder. Silently failing because `vault/` can't be found is the wrong default — the
skill must actively acquire access.

### Probe path order

Check these paths in order; first that exists is the vault. Use a shell probe (`ls` /
`test -d` via Bash) — don't rely on memory of where the vault was in a previous session:

1. `/sessions/*/mnt/vault/` — Cowork with the vault folder directly mounted
2. `/sessions/*/mnt/everything-vault/vault/` — Cowork with the project folder mounted
3. `/sessions/*/mnt/*/everything-vault/vault/` — Cowork with a parent folder mounted
4. `~/Documents/everything-vault/vault/` — local install
5. `~/everything-vault/vault/` — alternative local location

Also glob any other `/sessions/*/mnt/**/everything-vault/vault/` paths — the user may
have mounted a different parent folder. If one exists, use it.

When reporting paths to the user, use the human-readable host path (`~/Documents/...`),
not the sandbox path.

---

## 2. Mounting the vault if no path found

Call `mcp__cowork__request_cowork_directory` with:

```
path: "~/Documents/everything-vault"
```

Mount the project parent, **not** `everything-vault/vault` — the parent gives access
to `vault/`, the dashboard, and any install bundles without a second request later.

If the call returns an error about the path not existing (e.g. case mismatch on the
user's filesystem), retry once with capitalised variants (`~/Documents/Everything-Vault`).

After approval, re-run the probe and resolve the sandbox path under `/sessions/*/mnt/...`.
That's the path to use for all subsequent file ops.

**No user-facing question required.** The vault is the whole point of this skill —
requesting access is not interrupting; it's the standard Cowork file-access flow and
the user sees a clear approval card. Do **not** ask "may I request access to your vault
folder?" as a chat question — just call `mcp__cowork__request_cowork_directory` and let
Cowork render the approval prompt.

Only ask a clarifying question if the request is declined or if multiple plausible paths
exist (e.g. the user has two different vault folders on-disk).

---

## 3. Voice inbox via Apple Notes (optional)

If the user has an "EV Inbox" Apple Note configured for voice capture, the sweep
workflow's first step is to drain it.

### How to read

If the Apple Notes MCP is available (tools named `mcp__Read_and_Write_Apple_Notes__*`),
call:

```
mcp__Read_and_Write_Apple_Notes__get_note_content(name: "EV Inbox")
```

Parse the body for timestamped entries. Format varies — most users write free-form,
often with HH:MM stamps or date headers.

### How to process

For each entry: classify intent (idea, concept, event, task completion, episode,
reminder), propose how to ingest it, and present for the user's approval. After
processing, clear ingested entries by writing the note back with the processed entries
removed (`mcp__Read_and_Write_Apple_Notes__update_note_content`).

### If the MCP is unavailable

Skip the voice-inbox step silently. Don't try to fall back to filesystem grep — there is
no filesystem path for Apple Notes content.

---

## 4. Dashboard launch

The Execute primitive's most-used target. The user says "open the dashboard", "show me
the dashboard", "EV dashboard", "launch the dashboard", "refresh the dashboard".

**Single shell call:**

```
osascript -e 'do shell script "~/Documents/everything-vault/dashboard/ev-dash"'
```

`ev-dash` (in `dashboard/`) is a fire-and-forget launcher that:

1. Kills any running dashboard server on port 8077
2. Rebuilds `ev-data.json` from the current vault state (always a fresh view)
3. Starts a new HTTP server detached in the background (`nohup` + `disown`)
4. Opens `http://localhost:8077` in the default browser
5. Returns immediately (safe to call again — it re-launches cleanly)

Server log: `/tmp/ev-dashboard.log`. PID: `/tmp/ev-dashboard-server.pid`.

**Variants:**

- `ev-dash --stop` — kill the running server without relaunching
- `ev-dash --foreground` — blocking behaviour, stays attached (Ctrl-C to stop)
- `ev-dash --no-open` — rebuild + serve without opening the browser

**Why osascript (not bash):** the sandbox `bash` tool runs in a Linux VM that can't open
the host Mac's browser or hit host paths. `osascript do shell script` runs on the host,
so `open` and `webbrowser.open` both work.

**Don't:** manually start `python3 -m http.server`, don't `cd` into the dashboard folder
and run `build_dashboard.py` directly, don't try to open `dashboard.html` as a `file://`
URL — it needs the server for the JSON fetch. Just call `ev-dash`.

**After launch:** confirm with the URL (`http://localhost:8077`). If the user wants to
stop it later: `ev-dash --stop`.

---

## 5. Plugin install / update — `mcp__cowork__present_files`

**Authoritative method — read this every time before attempting an install.**

When the user says any of: "install this skill", "install the plugin", "install it",
"update the skill", "update the plugin", "push the update", "install the bundle",
"deploy the skill" — the single action is to present the bundle file via Cowork's
`mcp__cowork__present_files` tool. Cowork renders the file as a card with an
Install/Update button the user clicks. One tool call.

### Correct invocation

```
mcp__cowork__present_files({
  "files": [
    { "file_path": "<absolute path to .plugin file>" }
  ]
})
```

The `files` parameter is an **array of objects**, each with a `file_path` key.

A bare string produces `Expected array, received string`; a bare array of strings
produces the same error. Get the schema right on the first call.

### File format choice

- **`.plugin` files** (preferred) render with an **Install / Update** button. Standard
  format for catalog skills — zip with `.claude-plugin/plugin.json` + `skills/<slug>/`
  layout. Build per § 6, including the **lean** plugin.json and lean SKILL.md
  frontmatter described there. **Validation is strict** — see § 6 "Validator gotchas".
- **`.skill` files** render with a **Save skill** button. A flatter zip of the skill
  folder contents (`SKILL.md`, `prompts/`, `tools/`, etc.) directly at the root, no
  `.claude-plugin/` wrapper. This is the right fallback when `.plugin` validation fails
  despite a clean lean rebuild.

### What NOT to do

These paths have all been tried and don't work reliably:

- **Double-clicking the `.plugin` file in Finder.** macOS does not have `.plugin`
  registered as a known file type — the OS shows a "There is no application set to
  open the document" dialog. This is NOT a misconfiguration to fix; it's just not the
  right delivery path.
- **`claude plugin install <path>` in Terminal.** Requires Claude Code CLI on PATH,
  switches the user out of Cowork, and Terminal is tier-"click" in computer-use so
  Claude can't type the command anyway.
- **Copying into `.local-plugins/cache/`.** The cache is read-only from the sandbox;
  plugins are managed by Cowork's plugin loader, not by file-drop.

If the user explicitly asks for one of these alternative paths ("install via the CLI
instead"), then and only then pivot — otherwise present the file.

### After presentation

The user clicks Install/Update, Cowork unpacks and registers the plugin, the skill
becomes live in the next session (or sometimes immediately, depending on the plugin).
Then:

1. Confirm the presentation happened (`present_files` returned the file path)
2. Note the version now live, e.g. "✓ everything-vault 1.0.0 presented — click
   Install/Update to apply"
3. If part of a catalog-update flow, log the episode and bump catalog metadata

---

## 6. Plugin bundle build

A `.plugin` file is a zip archive. Cowork and Claude Code both validate the layout on
install — a flat zip of skill source **will be rejected**. Required shape:

```
<slug>-<version>.plugin  (zip)
├── .claude-plugin/
│   └── plugin.json              ← manifest (required)
├── skills/
│   └── <slug>/                  ← skill folder (SKILL.md must be directly inside)
│       ├── SKILL.md
│       ├── SCHEMA.md            (optional, recommended for EV-style skills)
│       ├── PLATFORM-CLAUDE.md   (optional)
│       ├── PLATFORM-CURSOR.md   (optional)
│       ├── CHANGELOG.md         (optional)
│       ├── prompts/             (optional)
│       └── tools/               (optional)
└── README.md                    ← human-readable description (recommended)
```

### `plugin.json` schema — KEEP IT MINIMAL

```json
{
  "name": "<slug>",
  "version": "<major.minor.patch>",
  "description": "<one-paragraph description of what the skill does>",
  "author": { "name": "<your name>" }
}
```

- `name` must match the `skills/<slug>/` folder name (lowercase, hyphens, max 64 chars)
- `version` uses three-part semver (`1.0.0`, not `1.0`)
- `description` should be under 1024 characters
- `author.name` is required — `author` must be an object, not a string
- **Do NOT add `keywords`.** The marketplace upload validator silently tolerates it; the
  direct `present_files` install validator rejects bundles that contain it.

### SKILL.md frontmatter — ALSO MINIMAL

```yaml
---
name: <slug>
description: >
  <multi-line folded description with all trigger phrases inline. Treat this as the
  agent-facing summary that drives skill auto-invocation. Put trigger keywords inside
  the prose, not in a separate keyword list.>
---
```

- `name` must match the plugin.json `name` and the `skills/<slug>/` folder name
- `description` carries every trigger phrase you want the skill to fire on — it's the
  only field the skill router reads to decide auto-invocation
- **Do NOT add a `metadata:` block** — `metadata.keywords` and `metadata.version` are
  non-standard and cause `present_files` validation to fail. The version lives in
  `plugin.json`, nowhere else.

### Build script

```bash
SLUG=everything-vault
VERSION=1.0.0
STAGE=/tmp/${SLUG}-stage
SRC=skill   # or wherever your skill source lives

rm -rf "$STAGE" && mkdir -p "$STAGE/.claude-plugin" "$STAGE/skills/${SLUG}"

# README at bundle root; SKILL.md and the rest under skills/<slug>/
cp README.md "$STAGE/README.md"
cp -r "$SRC"/{SKILL.md,SCHEMA.md,PLATFORM-CLAUDE.md,PLATFORM-CURSOR.md,CHANGELOG.md,prompts,tools} \
    "$STAGE/skills/${SLUG}/" 2>/dev/null

cat > "$STAGE/.claude-plugin/plugin.json" <<EOF
{
  "name": "${SLUG}",
  "version": "${VERSION}",
  "description": "Personal knowledge vault — markdown + YAML frontmatter, queried and updated through natural conversation.",
  "author": { "name": "<your name>" }
}
EOF

cd "$STAGE" && zip -r9 "$SRC/install/${SLUG}-${VERSION}.plugin" \
    .claude-plugin skills README.md
```

### Validator gotchas

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `keywords` array in `plugin.json` | "plugin validation failed" | Remove it. Trigger phrases go in the SKILL.md `description` instead. |
| `metadata.keywords` in SKILL.md frontmatter | "plugin validation failed" | Remove the entire `metadata:` block. |
| `metadata.version` in SKILL.md frontmatter | "plugin validation failed" | Same — version lives in `plugin.json` only. |
| Missing SKILL.md YAML frontmatter | "plugin validation failed" | Every SKILL.md must start with `---\nname: …\ndescription: …\n---`. |
| Two-part `version` in `plugin.json` (`"1.0"`) | Validation failure | Use three-part semver (`"1.0.0"`). |
| `author` as a bare string | Validation failure | `author` must be an object: `{ "name": "<your name>" }`. |

**`.skill` fallback:** if `.plugin` validation fails despite a clean lean rebuild,
package the same `skills/<slug>/` folder flat as `<slug>.skill` (zip with `.skill`
extension, no `.claude-plugin/` wrapper, no nested `skills/` folder). Cowork renders a
"Save skill" card instead of "Install/Update".

---

## 7. Tier-restricted apps (computer-use)

When the agent has computer-use tools, certain apps are granted at restricted tiers:

- **Browsers** → tier "read": visible in screenshots, no clicking/typing. Use the
  Claude-in-Chrome MCP for navigation.
- **Terminals & IDEs** → tier "click": left-clickable but no typing. For shell commands,
  use the Bash tool, not the integrated terminal.
- **Everything else** → tier "full": no restrictions.

The EV skill itself doesn't drive computer-use, but the dashboard launch path uses
osascript (host shell), so this rarely matters in practice.
