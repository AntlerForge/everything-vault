#!/usr/bin/env bash
# purge-example-data.sh — clear example content while preserving structure
#
# Removes all example articles, episodes, tasks, sources, and resets core/
# files to placeholder templates. Folder structure is preserved so the
# dashboard and tools still work; the vault just shows zero articles.
#
# Operates on the vault path the user picks (defaults to the path written
# by setup.sh into .ev-config). Use --vault to override.

set -e

if [ -t 1 ]; then
  BOLD=$(tput bold 2>/dev/null || echo "")
  DIM=$(tput dim 2>/dev/null || echo "")
  RESET=$(tput sgr0 2>/dev/null || echo "")
  GREEN=$(tput setaf 2 2>/dev/null || echo "")
  YELLOW=$(tput setaf 3 2>/dev/null || echo "")
  RED=$(tput setaf 1 2>/dev/null || echo "")
else
  BOLD="" DIM="" RESET="" GREEN="" YELLOW="" RED=""
fi
ok()    { echo "${GREEN}✓${RESET} $1"; }
warn()  { echo "${YELLOW}⚠${RESET} $1"; }
err()   { echo "${RED}✗${RESET} $1" >&2; }
info()  { echo "${DIM}  $1${RESET}"; }

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$REPO_DIR/skill"

# Resolve vault path and project (vault parent) path
VAULT_PATH=""
PROJECT_PATH=""
# Parse args: --vault <path> | --project <path>
while [ $# -gt 0 ]; do
  case "$1" in
    --vault)   VAULT_PATH="${2/#\~/$HOME}";   shift 2 ;;
    --project) PROJECT_PATH="${2/#\~/$HOME}"; shift 2 ;;
    *) shift ;;
  esac
done

if [ -z "$PROJECT_PATH" ] && [ -n "$EV_PROJECT_PATH" ]; then
  PROJECT_PATH="$EV_PROJECT_PATH"
fi
if [ -z "$VAULT_PATH" ] && [ -n "$EV_VAULT_PATH" ]; then
  VAULT_PATH="$EV_VAULT_PATH"
fi
if [ -z "$VAULT_PATH" ] && [ -f "$REPO_DIR/.ev-config" ]; then
  VAULT_PATH=$(grep '^EV_VAULT_PATH=' "$REPO_DIR/.ev-config" | head -1 | cut -d= -f2-)
fi
if [ -z "$PROJECT_PATH" ] && [ -f "$REPO_DIR/.ev-config" ]; then
  PROJECT_PATH=$(grep '^EV_PROJECT_PATH=' "$REPO_DIR/.ev-config" | head -1 | cut -d= -f2-)
fi
if [ -z "$VAULT_PATH" ] && [ -d "$HOME/Documents/everything-vault/vault" ]; then
  VAULT_PATH="$HOME/Documents/everything-vault/vault"
fi

# Derive missing path: if we know one, the other is a parent/child relation
if [ -n "$VAULT_PATH" ] && [ -z "$PROJECT_PATH" ]; then
  PROJECT_PATH="$(dirname "$VAULT_PATH")"
fi
if [ -n "$PROJECT_PATH" ] && [ -z "$VAULT_PATH" ]; then
  VAULT_PATH="$PROJECT_PATH/vault"
fi

if [ -z "$VAULT_PATH" ] || [ ! -d "$VAULT_PATH" ]; then
  err "Vault not found. Pass --vault /path/to/vault (or --project /path/to/project), or set EV_VAULT_PATH."
  exit 1
fi

echo ""
echo "${BOLD}Everything Vault — Purge Example Data${RESET}"
echo ""
echo "Project: $PROJECT_PATH"
echo "Vault:   $VAULT_PATH"
echo ""
echo "${YELLOW}This will:${RESET}"
echo "  • Delete every article in your vault domain folders"
echo "  • Clear all episodes, work-log entries, sources, and tasks"
echo "  • Reset core/ files to empty templates"
echo "  • Empty <project>/_for-deletion/ (folder + README preserved)"
echo "  • Empty <project>/_cache/ (folder + .gitkeep preserved)"
echo "  • Rebuild indexes (will show 0 articles)"
echo ""
echo "${RED}${BOLD}This cannot be undone.${RESET} Make sure you actually mean to do this."
echo ""
echo "If you want to keep the example data and just add your own alongside it,"
echo "you don't need to purge — just start writing your own articles."
echo ""

read -r -p "Purge all example data? [y/N]: " confirm
case "$confirm" in
  y|Y|yes|YES) ;;
  *) info "Aborted. No changes made."; exit 0 ;;
esac

TODAY=$(date +%Y-%m-%d)

# ── Domain folders: clear .md files but keep folders ─────────────────
DOMAIN_FOLDERS=(
  concepts projects health finance hobbies household it-setup work
  vehicles pets holidays family legal purchases professional holding-pen
)
for d in "${DOMAIN_FOLDERS[@]}"; do
  if [ -d "$VAULT_PATH/$d" ]; then
    # Delete .md files (recursively in case of subfolders like holidays/<trip>/)
    find "$VAULT_PATH/$d" -type f -name "*.md" -delete 2>/dev/null || true
    # Also wipe any orphan subfolder index leftovers
    find "$VAULT_PATH/$d" -type f -name "*.yaml" -delete 2>/dev/null || true
  fi
done
ok "Cleared domain folders"

# ── _for-deletion: wipe contents but keep the folder + README ─────────
# (it's a soft-delete bin — the folder must persist so the agent can use it)
# Lives as a SIBLING of vault/, not inside it.
FOR_DELETION="$PROJECT_PATH/_for-deletion"
if [ -d "$FOR_DELETION" ]; then
  find "$FOR_DELETION" -mindepth 1 ! -name "README.md" -exec rm -rf {} + 2>/dev/null || true
fi
mkdir -p "$FOR_DELETION"
if [ ! -f "$FOR_DELETION/README.md" ]; then
  cat > "$FOR_DELETION/README.md" <<'EOF'
# `_for-deletion/` — soft-delete bin

The agent moves superseded or unwanted articles here instead of deleting them.
This folder lives as a SIBLING of `vault/`, not inside it. Every tool excludes
this folder from indexing, queries, and the dashboard. You empty it
periodically — that's not the agent's job.
EOF
fi
ok "Reset _for-deletion/ (sibling of vault/, README in place)"

# Stray legacy in-vault soft-delete bin (from older versions): clear if present
if [ -d "$VAULT_PATH/_for-deletion" ]; then
  warn "Found legacy vault/_for-deletion/ — clearing contents (folder will remain)"
  find "$VAULT_PATH/_for-deletion" -mindepth 1 -delete 2>/dev/null || true
fi

# ── _cache: wipe contents but keep the folder + .gitkeep ──────────────
CACHE_DIR="$PROJECT_PATH/_cache"
if [ -d "$CACHE_DIR" ]; then
  find "$CACHE_DIR" -mindepth 1 ! -name ".gitkeep" -exec rm -rf {} + 2>/dev/null || true
fi
mkdir -p "$CACHE_DIR"
touch "$CACHE_DIR/.gitkeep"
ok "Reset _cache/ (sibling of vault/, .gitkeep in place)"

# ── Episodes / work-log: clear all year folders ──────────────────────
for sub in episodes work-log; do
  if [ -d "$VAULT_PATH/$sub" ]; then
    find "$VAULT_PATH/$sub" -type f -delete 2>/dev/null || true
    find "$VAULT_PATH/$sub" -type d -mindepth 1 -empty -delete 2>/dev/null || true
  fi
done
ok "Cleared episodes/ and work-log/"

# ── Sources: clear everything except the directory ──────────────────
if [ -d "$VAULT_PATH/sources" ]; then
  find "$VAULT_PATH/sources" -type f -delete 2>/dev/null || true
  find "$VAULT_PATH/sources" -type d -mindepth 1 -empty -delete 2>/dev/null || true
fi
ok "Cleared sources/"

# ── Tasks: reset to empty templates ─────────────────────────────────
mkdir -p "$VAULT_PATH/tasks"
cat > "$VAULT_PATH/tasks/todo-list.md" <<EOF
---
title: "Todo list"
domains: [tasks]
type: log
sensitivity: normal
created: $TODAY
last_updated: $TODAY
last_verified: $TODAY
confidence: high
source: manual
---

# Todo list

| ID | Task | Status | Priority | Urgency | Due | Source | Notes |
|----|------|--------|----------|---------|-----|--------|-------|
EOF

cat > "$VAULT_PATH/tasks/day-board.md" <<EOF
---
title: "Day Board"
domains: [tasks]
type: log
last_updated: $TODAY
sensitivity: normal
created: $TODAY
last_verified: $TODAY
confidence: high
source: manual
---

# Day Board

## Slot 1: empty

## Slot 2: empty

## Slot 3: empty

## Slot 4: empty

## Slot 5: empty
EOF
ok "Reset tasks/ to empty templates"

# ── Core: reset to placeholder templates ────────────────────────────
mkdir -p "$VAULT_PATH/core"
USERNAME_DEFAULT="$(whoami)"

cat > "$VAULT_PATH/core/whoami.md" <<EOF
---
title: "Who I am"
domains: [core]
type: reference
sensitivity: normal
created: $TODAY
last_updated: $TODAY
last_verified: $TODAY
confidence: high
source: manual
---

# Who I am

<!-- Add your details here. Anything you want the LLM to always know about
     you when it loads core memory at the start of a session. -->

Name: $USERNAME_DEFAULT
EOF

cat > "$VAULT_PATH/core/preferences.md" <<EOF
---
title: "Vault preferences"
domains: [core]
type: reference
sensitivity: normal
created: $TODAY
last_updated: $TODAY
last_verified: $TODAY
confidence: high
source: manual
---

# Vault preferences

<!-- How you like the vault operated. Communication style, naming
     conventions, default behaviours, things to always or never do. -->
EOF

cat > "$VAULT_PATH/core/active-context.md" <<EOF
---
title: "Active context"
domains: [core]
type: log
sensitivity: normal
created: $TODAY
last_updated: $TODAY
last_verified: $TODAY
confidence: high
source: manual
---

# Active context

<!-- Current priorities and things in flight. Update this regularly so the
     LLM always knows what's top of mind. -->
EOF

cat > "$VAULT_PATH/core/key-people.md" <<EOF
---
title: "Key people"
domains: [core]
type: contact
sensitivity: normal
created: $TODAY
last_updated: $TODAY
last_verified: $TODAY
confidence: high
source: manual
---

# Key people

<!-- The people who matter most to your day-to-day. -->
EOF

ok "Reset core/ to placeholder templates"

# ── Recreate the year subfolders so episodes/work-log have somewhere to land ──
mkdir -p "$VAULT_PATH/episodes/$(date +%Y)/$(date +%Y)-Q$(($(date +%m -1) / 3 + 1))" 2>/dev/null || \
  mkdir -p "$VAULT_PATH/episodes/$(date +%Y)"
mkdir -p "$VAULT_PATH/work-log/$(date +%Y)"
mkdir -p "$VAULT_PATH/sources/$(date +%Y)"

# ── Rebuild indexes ─────────────────────────────────────────────────
if python3 "$SKILL_DIR/tools/index_builder.py" --vault "$VAULT_PATH" >/tmp/ev-purge-index.log 2>&1; then
  ok "Rebuilt indexes (vault now empty)"
else
  warn "Index rebuild had issues — see /tmp/ev-purge-index.log"
fi

# ── Regenerate dashboard JSON ───────────────────────────────────────
if python3 "$REPO_DIR/dashboard/build_dashboard.py" --vault "$VAULT_PATH" --no-serve >/tmp/ev-purge-dash.log 2>&1; then
  ok "Regenerated dashboard JSON"
else
  warn "Dashboard rebuild had issues — see /tmp/ev-purge-dash.log"
fi

echo ""
echo "${BOLD}${GREEN}Purge complete.${RESET}"
echo ""
echo "Your vault structure is preserved. The vault now shows 0 articles."
echo "Open ${BOLD}$VAULT_PATH/core/whoami.md${RESET} to start filling in your own details."
echo ""
