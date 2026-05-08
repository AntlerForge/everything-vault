---
title: "AI-driven meal planning"
domains: [concepts]
type: reference
tier: idea
status: ideas
relationships:
  - ref: recipe-manager
    type: extends
related: [small-bets-portfolio]
created: 2026-03-22
last_updated: 2026-04-15
last_verified: 2026-05-07
confidence: medium
source: conversation
tags: [ai, recipes, planning]
---

<!-- EXAMPLE: This article demonstrates a tier:idea concept linked to an active project that it could feed into. -->

# AI-driven meal planning

A meal-planning module that sits on top of recipe-manager. Given a
household's pantry, taste preferences, and dietary constraints, it proposes
a week's plan that minimises food waste and balances cooking effort across
the week.

## Why now

The recipe-manager already has structured ingredient and step data, plus
per-recipe time and difficulty estimates. That's most of what an LLM-driven
planner would need as input.

## Shape of the experiment

Smallest interesting version:

1. Tag a small library (40-50 recipes) with already-have ingredients.
2. Ask the model: "plan four dinners using mostly these ingredients,
   balanced by effort, and only one supermarket trip mid-week."
3. Compare to what Sam and I would have picked manually.

If the planner consistently saves Sunday-evening meal-planning effort
without producing weird meals, it earns a real prototype.

## Risks / open questions

- Hallucinated ingredients? Need strict grounding to the existing recipe set.
- How does the planner learn that I'm vegetarian Mon-Wed but not other days?
- Privacy: this can run entirely against a local model — and probably should.

## Next step

Sketch the prompt structure. Don't build anything yet — just see whether the
output is plausible before committing engineering time.
