---
title: "Recipe Manager"
domains: [projects]
type: reference
tier: project
status: under-development
development_platform: cursor
github: "git@github.com:alexchen/recipe-manager.git"
code_path: "~/Developer/personal/recipe-manager"
relationships:
  - ref: meal-planning-ai
    type: inspires
related: [japanese-resources, async-client-comms]
created: 2026-01-22
last_updated: 2026-05-05
last_verified: 2026-05-07
confidence: high
source: manual
tags: [open-source, side-project, python, typescript]
---

<!-- EXAMPLE: This article demonstrates a tier:project article with code_path, github, and a Change History recording status transitions. -->

# Recipe Manager

Open-source self-hosted recipe manager. Imports recipes from any URL, strips
ad copy, and stores clean structured markdown alongside ingredient and step
data. Built mostly for personal use; pushing toward a v1.0 that someone other
than me could install.

## Stack

- Python (FastAPI) on the back end.
- TypeScript / SvelteKit on the front end.
- SQLite for storage; Postgres optional for self-hosters.

## Current status

v0.2 release candidate. Import-from-URL endpoint is wired up and works on the
ten test sites I care about. Outstanding work:

1. Polish error states for malformed URLs.
2. Add the duplicate-detection step on import.
3. Docs pass — README, install guide, contributor notes.

Targeting tag and announce by the end of May 2026.

## Collaborators

Jordan (front end, weekly pairing). Otherwise solo.

## Change History

| Date       | Change                                          | Source                | Confidence |
|------------|-------------------------------------------------|-----------------------|------------|
| 2026-04-15 | v0.2 scope locked; import-from-URL prioritised  | Project brief         | High       |
| 2026-03-15 | v0.1 shipped (status: prototype → under-development) | Episode 2026-03-15 | High       |
| 2026-01-22 | Repo initialised (status: ideas → prototype)    | Manual                | High       |
