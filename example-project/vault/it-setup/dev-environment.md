---
title: "macOS development environment"
domains: [it-setup]
type: how-to
sensitivity: normal
created: 2026-01-15
last_updated: 2026-04-22
last_verified: 2026-05-07
confidence: high
source: manual
tags: [dev, macos, setup]
---

<!-- EXAMPLE: This article demonstrates a how-to in it-setup — repeatable steps for setting up a new machine. -->

# Development environment (macOS)

The setup I run on a fresh Mac. Goal: a working dev environment in under
two hours, no surprises.

## Package manager

- Homebrew for system-level tools.
- `brew bundle` from a checked-in Brewfile in `~/Developer/dotfiles/`.

## Language version manager

- `asdf` for Python, Node, Ruby, Go.
- One `.tool-versions` per project, pinning versions explicitly.

## Editors

- **Cursor** for AI-pairing-heavy work (recipe-manager, the client portal).
- **Neovim** for quick edits, config, and ssh sessions.
- VS Code installed but only used for the occasional notebook.

## Terminal

- iTerm2 with a minimal profile.
- `tmux` for long-running sessions, especially when ssh'd into the home
  server.
- `zsh` with starship prompt; aliases live in dotfiles.

## Other tools

- `gh` for GitHub CLI.
- `ripgrep`, `fd`, `bat`, `eza` — the usual modern Unix replacements.
- `git-delta` for diffs.
- `direnv` for per-project env vars.

## Project layout

```
~/Developer/
├── dotfiles/
├── personal/
│   ├── recipe-manager/
│   ├── …
├── clients/
│   ├── maria/
│   └── …
└── archive/
```

## Backups

- Time Machine to a NAS over the home network.
- Code lives on GitHub; remote is the source of truth, the laptop is a
  cache.
- Documents under `~/Documents/` synced to a personal cloud share.
