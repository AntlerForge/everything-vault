---
title: "Freelance client portal (for Maria)"
domains: [projects, work]
type: reference
tier: project
status: delivered-and-operational
development_platform: cursor
github: "git@github.com:alexchen/maria-client-portal.git"
code_path: "~/Developer/clients/maria/client-portal"
entity_refs: [maria]
related: [freelance-workflow, client-management]
created: 2026-01-12
last_updated: 2026-04-25
last_verified: 2026-05-07
confidence: high
source: manual
tags: [client-work, delivered, maintenance]
---

<!-- EXAMPLE: This article demonstrates a delivered project that has moved into ongoing maintenance mode. -->

# Freelance client portal

Built for Maria's consulting business. A small portal where her clients can
log in, see their engagement state, view documents, and exchange messages
with her. Replaces the email-thread chaos that was eating her afternoons.

## Stack

- TypeScript / SvelteKit front end.
- Python (FastAPI) back end, sharing patterns with my recipe-manager work.
- Postgres on a small managed instance.
- Hosted on a single VPS with nightly backups.

## Delivered

Soft launch 2026-02-12. Final sign-off 2026-02-20. See episode
`2026-02-12-freelance-portal-shipped`.

## Now

Maintenance retainer of 8 hours/month. So far that has mostly absorbed:

- Two small UI tweaks Maria asked for.
- One library upgrade.
- Patching the auth provider after their library had a security advisory.

A new reporting feature is scoped for June 2026 — Maria wants per-client
time-spent rollups.

## Watch list

- Hosting renewal in August 2026.
- Dependency drift — set a quarterly reminder to pull non-breaking updates.
