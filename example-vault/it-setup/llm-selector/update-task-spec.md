---
title: "LLM scores — update task spec"
domains: [it-setup]
type: how-to
sensitivity: normal
related: []
created: 2026-04-30
last_updated: 2026-05-07
last_verified: 2026-05-07
confidence: high
source: manual
tags: [llm, selector, evaluation]
---

<!-- EXAMPLE: This article demonstrates a how-to that describes a recurring maintenance task on a sibling file in the same folder. -->

# LLM scores — update task spec

How to refresh `llm-scores.yaml` so its recommendations stay useful.

## When to run

- Quarterly, on the same day as the finance review.
- Within two weeks of any major model release I'm likely to use.
- Whenever I notice a recommendation in the file is wrong in practice.

## Inputs

- `llm-scores.yaml` — the file being updated.
- A short personal log of "model X did well / poorly at task Y" notes
  collected since the last update. Doesn't need to be elaborate; a single
  text file suffices.
- For any new model: a quick read of the model card or release notes.

## Procedure

1. Bump `meta.last_updated` to today.
2. For each use case in `use_cases`:
   - Score every model on the 0-10 scale.
   - Use the rubric: 0 unusable, 5 passable, 10 best in class.
   - If I haven't tested a model on a use case, leave the score absent
     rather than guessing.
3. Update `recommendations` to point at the highest-scoring model per
   use case. Where two models are within 1 point, prefer the cheaper /
   faster one for fast-iteration tasks; prefer the most capable for
   planning and code-review.
4. Add a one-line note in `models[<id>].notes` for any model whose score
   shifted by more than 2 points since last update — explain why.
5. Commit and move on. Don't let this become a research project; the
   point is a living, biased-toward-personal-experience reference.

## Anti-pattern

- Filling in scores from someone else's published benchmarks. The whole
  value here is **my** experience with these models on **my** tasks.
- Adding new use cases speculatively. Add a use case only after I've hit
  it three times in real work.
