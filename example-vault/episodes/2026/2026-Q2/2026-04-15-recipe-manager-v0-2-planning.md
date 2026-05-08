---
title: "Recipe manager v0.2 scope locked"
domains: [episodes, projects]
type: log
object_type: episode
date: 2026-04-15
actors: [user, jordan]
entity_refs: [jordan]
article_refs: [recipe-manager]
source_refs: ["sources/2026/2026-04-15-recipe-manager-brief.txt"]
outcomes:
  - v0.2 scope locked to import-from-URL polish, duplicate detection, docs pass
  - Target tag-and-announce date set for end of May 2026
  - meal-planning-ai parked as a v0.3+ exploration, not in v0.2
follow_up: "Cut release branch when import error states are done"
tags: [recipe-manager, planning, milestone]
sensitivity: normal
retrieval_default: searchable
source: conversation
created: 2026-04-15
confidence: high
---

<!-- EXAMPLE: This episode demonstrates linking an episode to a Source-tier file via source_refs. -->

# Recipe manager — v0.2 scope locked

Two-hour planning session with Jordan. The brief has been bouncing around
for a couple of weeks; today we cut it down to a v0.2 we can actually
ship.

In:

- Polish error states for malformed URLs.
- Duplicate detection on import.
- Docs pass — README, install guide, contributor notes.

Out (deferred to a later release):

- Meal-planning AI exploration. Lives in `concepts/` until the smallest
  interesting demo is sketched.
- Multi-tenant user model. Single-user is fine for v0.x.

Brief notes filed under `sources/2026/2026-04-15-recipe-manager-brief.txt`.
