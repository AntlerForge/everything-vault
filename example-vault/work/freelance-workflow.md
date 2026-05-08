---
title: "Freelance workflow — lead to invoice"
domains: [work]
type: how-to
sensitivity: normal
related: [client-management, freelance-income-tracking, async-client-comms]
created: 2026-01-25
last_updated: 2026-04-18
last_verified: 2026-05-07
confidence: high
source: manual
tags: [freelance, workflow, process]
---

<!-- EXAMPLE: This article demonstrates a how-to that captures a multi-stage process — readable as a checklist any time a new lead lands. -->

# Freelance workflow

The end-to-end flow I use for client work, from a first conversation to the
final invoice. Treats every project as a small contract with explicit
artefacts.

## 1. Lead and scoping

- Take a 30-minute intro call. No notes shared yet, just listening.
- Within 48 hours: send back a one-page scoping summary in plain prose.
  What I think the problem is, what I'd do first, what I'd do not at all.
- If the client signs off on the summary, we move to a proper proposal.

## 2. Proposal

- Fixed-fee for clearly bounded work, retainer for ongoing maintenance,
  rate card for time-and-materials when neither fits.
- Always include: deliverables, what's explicitly out of scope,
  payment milestones, and a "stop clause" — either side can pause work
  with seven days' notice.

## 3. Contract and kickoff

- A short, plain-English contract — proposal as the scope, payment terms,
  IP assignment, NDA if relevant.
- Kickoff doc in the client folder under `~/Developer/clients/<name>/`:
  a copy of the contract, the scope, and a one-page architecture sketch.

## 4. Build

- Weekly written update following the template in `async-client-comms`.
- Work-log entries daily on active days (see `work-log/`).
- All artefacts and code in the repo. Email or chat is for context, not
  artefacts.

## 5. Delivery

- Soft launch first — restricted access, real users, a week of bug-fixing.
- Then sign-off, and the project moves to `delivered-and-operational`.

## 6. Invoice and close

- Invoice within 24 hours of milestone completion.
- Closing note: what was built, what was deferred, what the next stable
  step would be. Saved to the client folder.
