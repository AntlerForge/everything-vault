---
title: "Todo list"
domains: [tasks]
type: log
sensitivity: normal
created: 2026-01-15
last_updated: 2026-05-07
last_verified: 2026-05-07
confidence: high
source: manual
tags: [todos, tasks]
---

<!-- EXAMPLE: This article demonstrates the todo-list table that the dashboard parses. Mix of statuses, priorities, and due dates. -->

# Todo list

| ID   | Task                                          | Status      | Priority | Urgency | Due        | Source                              | Notes                |
|------|-----------------------------------------------|-------------|----------|---------|------------|-------------------------------------|----------------------|
| T001 | Sketch v0.2 recipe import error states        | open        | high     | medium  | 2026-05-15 | projects/recipe-manager.md          | —                    |
| T002 | Order kitchen worktop sample                  | done        | medium   | high    |            | projects/kitchen-renovation.md      | Done 2026-04-30      |
| T003 | Reply to Maria's email about June scope       | open        | high     | high    | 2026-05-09 | projects/freelance-client-portal.md | Holding her up       |
| T004 | Final glue-up for bench top                   | open        | medium   | low     |            | projects/woodworking-bench.md       | Halves drying first  |
| T005 | Genki II chapter 14 workbook                  | open        | low      | medium  |            | projects/japanese-study.md          | This week            |
| T006 | Q1 VAT return — submit                        | done        | high     | high    |            | finance/freelance-income-tracking.md | Done 2026-04-29     |
| T007 | Buy worktop sample swatch (alt colour)        | done        | low      | low     |            | projects/kitchen-renovation.md      | Done 2026-05-04      |
| T008 | Plan trip to Seville                          | cancelled   | low      | low     |            | core/active-context.md              | Postponed to 2027    |
| T009 | Tail vise hardware — order                    | blocked     | medium   | low     |            | projects/woodworking-bench.md       | Bench needs flat top first |
| T010 | Book electrician's first-fix walk             | open        | high     | high    | 2026-05-12 | projects/kitchen-renovation.md      | Slot pencilled       |

## Notes

- Status values: `open`, `done`, `blocked`, `cancelled`. The dashboard
  parser handles a tick-prefixed `done` too.
- Priority: high / medium / low. Urgency: high / medium / low. They are
  separate axes — a high-priority task can be low-urgency.
- Source column points to the article a task belongs to.
