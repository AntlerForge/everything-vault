---
title: "Freelance client portal soft-launched for Maria"
domains: [episodes, work, projects]
type: log
object_type: episode
date: 2026-02-12
actors: [user, maria]
entity_refs: [maria]
article_refs: [freelance-client-portal]
outcomes:
  - Soft launch live for Maria with three pilot clients enabled
  - One auth-flow bug found in pilot, patched same day
  - Final sign-off scheduled for 2026-02-20
follow_up: "Sign-off call 2026-02-20"
tags: [delivery, milestone]
sensitivity: normal
retrieval_default: searchable
source: conversation
created: 2026-02-12
confidence: high
---

<!-- EXAMPLE: This episode demonstrates a project-shipping milestone with concrete outcomes and a follow-up. -->

# Freelance portal soft-launched

Pushed the portal to its production VPS this morning, walked Maria through
the admin screens over a video call, and enabled the first three pilot
clients on her side.

A pilot user hit an edge case in the OAuth callback — the redirect URI was
URL-encoded twice. Patched, redeployed, verified within the hour.

Sign-off call booked for next week. Maintenance retainer terms agreed
verbally; I'll send the written version Monday.
