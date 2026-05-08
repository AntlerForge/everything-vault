---
title: "Structured weekly client update"
domains: [concepts, work]
type: reference
tier: idea
status: ideas
applies_to: work
relationships:
  - ref: small-bets-portfolio
    type: extends
related: [client-management, freelance-workflow]
created: 2026-04-02
last_updated: 2026-04-25
last_verified: 2026-05-07
confidence: medium
source: manual
tags: [freelance, communication, template]
---

<!-- EXAMPLE: This article demonstrates a tier:idea concept that could become a small-bet tool — a templated communication artefact. -->

# Structured weekly client update

A small idea: every freelance client gets a weekly email update in the
same fixed structure, sent the same day each week, even when there's
"nothing to report."

## The structure

```
Subject: <Project> — Week of <date>

This week
- <2-4 bullets, what shipped or moved>

Next week
- <2-4 bullets, what's planned>

Blocked / waiting on you
- <0-2 items>

Hours used / hours remaining
- <if on a retainer>

Anything else
- <optional>
```

## Why it works

- Predictability is a feature. The client knows when an update arrives, and
  doesn't ping mid-week to ask.
- The "Blocked / waiting on you" section flushes things into the open before
  they slip a week.
- Writing it weekly forces a small reflection on what actually moved.

## Could this be a tool?

Possibly. A template-driven generator that pulls from `work-log/` entries
could draft 80% of the update automatically, leaving me to add context and
hit send. A two-evening prototype, max.

## Risks

- Over-templating sounds robotic. The "anything else" slot has to stay
  warmly human.
- Different clients want different cadences. Templating shouldn't enforce
  weekly on everyone.
