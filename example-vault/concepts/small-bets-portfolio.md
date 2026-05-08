---
title: "Side projects as a portfolio of small bets"
domains: [concepts]
type: reference
tier: concept
status: ideas
applies_to: both
related: [recipe-manager, async-client-comms, meal-planning-ai]
created: 2026-02-18
last_updated: 2026-04-05
last_verified: 2026-05-07
confidence: medium
source: manual
tags: [strategy, side-project, principle]
---

<!-- EXAMPLE: This article demonstrates a tier:concept article — a design principle that informs how multiple projects are run. -->

# Small bets portfolio

The design principle that side projects should be **cheap to start and fast
to validate**. Treat the collection of side projects like a portfolio of
small bets, not a sequence of grand plans.

## The shape of a small bet

- Defined enough to demo something real in 2-4 weekends.
- Cheap to abandon: no infrastructure that costs money to keep alive.
- Asymmetric upside: if it works, it can grow; if it fails, the lesson
  transfers to the next bet.

## Why this matters

The temptation with side projects is to over-design the foundation and
under-test whether the thing is actually wanted. A small-bet posture
reverses that: build the smallest thing that proves the bet, then expand
only with evidence.

## How it shows up here

- **recipe-manager** started as a Sunday afternoon scrape-then-store
  experiment. The "real" app emerged from there.
- **meal-planning-ai** is currently sitting in `concepts/` because the bet
  hasn't been sized yet — once I can describe the smallest demo, it earns
  prototype status.
- **async-client-comms** could be a 3-evening template build. Whether it
  becomes a tool depends on whether other freelancers actually want it.

## Anti-pattern to watch for

"Setup work" that creates infrastructure (deploy pipelines, multi-tenant
auth, plugin systems) before the core is proven. Move that to v0.5, never
v0.1.
