#!/usr/bin/env bash
# setup.sh — Interactive setup for Everything Vault
#
# Walks the user through:
#   - Choosing a vault location
#   - Optionally copying the example vault
#   - Running the initial index build
#   - Optionally launching the dashboard
#
# Idempotent — safe to re-run. Won't overwrite an existing populated vault
# without explicit confirmation.

set -e

# ── Colours (gracefully degrade if not a tty) ──────────────────────────
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

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXAMPLE_PROJECT="$PROJECT_DIR/example-project"
EXAMPLE_VAULT_LEGACY="$PROJECT_DIR/example-vault"  # fallback if example-project/ is missing
SKILL_DIR="$PROJECT_DIR/skill"
DEFAULT_PROJECT_LOCATION="$HOME/Documents/everything-vault"

# ── Banner ─────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}Everything Vault — Setup${RESET}"
echo "${DIM}A local-first personal knowledge management system.${RESET}"
echo ""
echo "This script will:"
echo "  1. Ask where to put your project folder (vault + sibling _for-deletion/, _cache/)"
echo "  2. Optionally copy the example data so you can explore"
echo "  3. Run the initial index build"
echo "  4. Offer to launch the dashboard"
echo ""

# ── Python check ───────────────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  err "python3 not found on PATH. Please install Python 3.8+ and try again."
  exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
  err "Python 3.8+ required (found $PY_VERSION)."
  exit 1
fi
ok "Python $PY_VERSION detected"

# ── Step 1: project folder location ────────────────────────────────────
echo ""
echo "${BOLD}Step 1 — Project folder location${RESET}"
echo "Where should your Everything Vault project folder live?"
echo "  Default: $DEFAULT_PROJECT_LOCATION"
echo ""
echo "${DIM}The project folder contains three siblings:${RESET}"
echo "${DIM}    vault/           — pure knowledge content${RESET}"
echo "${DIM}    _for-deletion/   — soft-delete bin (the agent moves files here)${RESET}"
echo "${DIM}    _cache/          — runtime caches (consolidation, status proposals)${RESET}"
read -r -p "  Project folder path [Enter for default]: " PROJECT_INPUT
PROJECT_PATH="${PROJECT_INPUT:-$DEFAULT_PROJECT_LOCATION}"
# Expand ~
PROJECT_PATH="${PROJECT_PATH/#\~/$HOME}"
VAULT_PATH="$PROJECT_PATH/vault"

if [ -d "$VAULT_PATH" ] && [ -n "$(ls -A "$VAULT_PATH" 2>/dev/null)" ]; then
  warn "Vault already exists and contains files: $VAULT_PATH"
  read -r -p "  Continue and merge into this vault? [y/N]: " confirm
  case "$confirm" in
    y|Y|yes|YES) info "Continuing — existing files will be preserved" ;;
    *) info "Aborted. Pick a different location and re-run setup."; exit 0 ;;
  esac
else
  mkdir -p "$VAULT_PATH"
  ok "Created $VAULT_PATH"
fi

# Always create the sibling folders alongside vault/
mkdir -p "$PROJECT_PATH/_for-deletion"
mkdir -p "$PROJECT_PATH/_cache"
touch "$PROJECT_PATH/_cache/.gitkeep"
ok "Created sibling folders: _for-deletion/, _cache/"

# ── Step 2: example data ───────────────────────────────────────────────
echo ""
echo "${BOLD}Step 2 — Example data${RESET}"
echo "Would you like to populate your vault with the example data?"
echo "(36 articles, 9 episodes, populated day-board, work-log, sources, etc."
echo " A fictional persona — Alex Chen, a freelance developer in Bristol)"
echo ""
echo "Choose:"
echo "  ${BOLD}y${RESET} — copy example data (recommended for first-time users)"
echo "  ${BOLD}n${RESET} — empty structure only"
read -r -p "  Copy example data? [Y/n]: " example_input
case "${example_input:-y}" in
  y|Y|yes|YES)
    if [ -d "$EXAMPLE_PROJECT" ]; then
      # Copy all three siblings (vault/, _for-deletion/, _cache/) at once.
      cp -R "$EXAMPLE_PROJECT"/. "$PROJECT_PATH/"
      ok "Copied example project into $PROJECT_PATH"
    elif [ -d "$EXAMPLE_VAULT_LEGACY" ]; then
      # Legacy fallback for older checkouts: copy example-vault/ into vault/,
      # but skip its in-vault _for-deletion/ — it lives as a sibling now.
      info "Using legacy example-vault/ layout"
      (cd "$EXAMPLE_VAULT_LEGACY" && \
       find . -mindepth 1 -maxdepth 1 ! -name '_for-deletion' \
            -exec cp -R {} "$VAULT_PATH/" \;)
      if [ -d "$EXAMPLE_VAULT_LEGACY/_for-deletion" ]; then
        cp -R "$EXAMPLE_VAULT_LEGACY/_for-deletion"/. "$PROJECT_PATH/_for-deletion/"
      fi
      ok "Copied example data into $PROJECT_PATH (legacy layout)"
    else
      warn "example-project/ and example-vault/ both missing — creating empty structure"
      example_input="n"
    fi
    ;;
  *)
    info "Creating empty structure only"
    ;;
esac

# Always ensure default folder structure exists inside vault/.
# Note: _for-deletion/ is a sibling of vault/, not inside it — it was created
# alongside the project folder above.
for subdir in core projects concepts episodes work-log tasks sources \
              health finance hobbies household it-setup work \
              vehicles pets holidays family legal purchases professional \
              holding-pen; do
  mkdir -p "$VAULT_PATH/$subdir"
done

# If no _for-deletion README copied (empty-structure path), seed one inline.
if [ ! -f "$PROJECT_PATH/_for-deletion/README.md" ]; then
  cat > "$PROJECT_PATH/_for-deletion/README.md" <<'EOF'
# `_for-deletion/` — soft-delete bin

This folder is the soft-delete bin for the vault. It lives as a SIBLING of
`vault/` (not inside it), so vault/ stays purely knowledge content.

When the agent supersedes, deduplicates, or retires an article, it moves the
file here instead of deleting. That's safer (the move is reversible), tidier
(every tool excludes this folder from indexing, queries, and the dashboard),
and platform-independent (a plain `mv` works on every host).

The agent **never empties this folder.** That's your decision. When you're
satisfied nothing in here is needed, empty it through Finder, your file
manager, or the shell:

```bash
rm -rf <project>/_for-deletion/*
```

This README is the only file you'll find here on a fresh project. After a
sweep or two, expect to see retired articles starting to accumulate.
EOF
fi

# Empty structure — write template core files
case "${example_input:-y}" in
  y|Y|yes|YES) ;;  # examples already copied
  *)
    USERNAME_DEFAULT="$(whoami)"
    read -r -p "  Your name (for whoami.md) [${USERNAME_DEFAULT}]: " name_input
    USER_NAME="${name_input:-$USERNAME_DEFAULT}"
    TODAY=$(date +%Y-%m-%d)

    if [ ! -f "$VAULT_PATH/core/whoami.md" ]; then
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

<!-- Add your details here. Anything you want the LLM to always know about you
     when it loads core memory at the start of a session. -->

Name: $USER_NAME

(Add more details — role, location, interests, anything you want surfaced
by default.)
EOF
    fi

    if [ ! -f "$VAULT_PATH/core/preferences.md" ]; then
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

(Add your preferences here.)
EOF
    fi

    if [ ! -f "$VAULT_PATH/core/active-context.md" ]; then
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

(Add your current priorities here.)
EOF
    fi

    if [ ! -f "$VAULT_PATH/core/key-people.md" ]; then
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

<!-- The people who matter most to your day-to-day. Family, close
     colleagues, key collaborators. The LLM uses this for context when
     names come up. -->

(Add the important people here.)
EOF
    fi

    if [ ! -f "$VAULT_PATH/tasks/todo-list.md" ]; then
      cat > "$VAULT_PATH/tasks/todo-list.md" <<'EOF'
---
title: "Todo list"
domains: [tasks]
type: log
sensitivity: normal
created: 2026-01-01
last_updated: 2026-01-01
last_verified: 2026-01-01
confidence: high
source: manual
---

# Todo list

| ID | Task | Status | Priority | Urgency | Due | Source | Notes |
|----|------|--------|----------|---------|-----|--------|-------|
EOF
    fi

    if [ ! -f "$VAULT_PATH/tasks/day-board.md" ]; then
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
    fi

    ok "Created template core/, tasks/ files"
    ;;
esac

# ── Step 3: write a tiny .ev-config so other tooling knows the vault path ──
CONFIG_FILE="$PROJECT_DIR/.ev-config"
{
  echo "# Generated by setup.sh on $(date +%Y-%m-%dT%H:%M:%S)"
  echo "EV_VAULT_PATH=$VAULT_PATH"
  echo "EV_PROJECT_PATH=$PROJECT_PATH"
} > "$CONFIG_FILE"
ok "Wrote $CONFIG_FILE (used by ev-dash if EV_VAULT_PATH is not exported)"

echo ""
echo "${DIM}Tip: add this to your shell profile to make EV_VAULT_PATH always available:${RESET}"
echo "${DIM}    export EV_VAULT_PATH=\"$VAULT_PATH\"${RESET}"

# ── Step 4: initial index ─────────────────────────────────────────────
echo ""
echo "${BOLD}Step 3 — Building initial indexes${RESET}"
if python3 "$SKILL_DIR/tools/index_builder.py" --vault "$VAULT_PATH" >/tmp/ev-index.log 2>&1; then
  ok "Indexes built"
  info "(see /tmp/ev-index.log if you want the full output)"
else
  warn "Index build had issues — see /tmp/ev-index.log"
fi

# ── Step 5: optional dashboard launch ─────────────────────────────────
echo ""
echo "${BOLD}Step 4 — Dashboard${RESET}"
read -r -p "  Launch the dashboard now? [Y/n]: " launch_input
case "${launch_input:-y}" in
  y|Y|yes|YES)
    export EV_VAULT_PATH="$VAULT_PATH"
    bash "$PROJECT_DIR/dashboard/ev-dash"
    ;;
  *)
    info "Skipped. You can launch it later with: $PROJECT_DIR/dashboard/ev-dash"
    ;;
esac

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "${BOLD}${GREEN}Setup complete.${RESET}"
echo ""
echo "Next steps:"
echo "  • Read ${BOLD}docs/getting-started.md${RESET} for a guided tour"
echo "  • Try a query: python3 $SKILL_DIR/tools/query.py --vault $VAULT_PATH --question \"<your question>\""
echo "  • Open the dashboard: $PROJECT_DIR/dashboard/ev-dash"
echo "  • Install the skill into your LLM (any LLM that can read markdown works):"
echo "      Cursor / Codex CLI / VS Code: see skill/PLATFORM-CURSOR.md"
echo "      Claude Code / Cowork:         see skill/PLATFORM-CLAUDE.md"
echo "      ChatGPT / Gemini / others:    see docs/skill-guide.md"
echo ""
echo "When you're ready to clear the example data and start fresh:"
echo "  ./purge-example-data.sh"
echo ""
