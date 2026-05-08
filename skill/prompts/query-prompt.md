# Query Capability — Decision Guidance

You are searching the Everything Vault to answer the user's question. Always search before
saying "I don't know" — the vault may contain what they need.

## First: Load Core Memory

If you haven't already this session, read all files in `vault/core/`:
- `core/whoami.md`
- `core/preferences.md`
- `core/active-context.md`
- `core/key-people.md`

This gives you baseline context for answering any question.

## Query Classification

| Type | Example | Strategy |
|------|---------|----------|
| **Quick fact** | "When does my car insurance renew?" | Frontmatter search → direct answer |
| **Topic search** | "What do I know about the laser burner?" | Keyword search → summary |
| **Domain browse** | "What do you know about my finances?" | Domain index → list |
| **Structured** | "What renewals are coming up?" | Field-based search |
| **Cross-domain** | "Everything about a project" | Multi-tag search |
| **Temporal** | "When did I submit the planning application?" | **Episode search first** |
| **Timeline** | "What happened with the kitchen renovation?" | **Episode search + article** |

## Search Strategy (in order)

### Step 1: Determine if this is a temporal question

If the question asks "when did...", "what happened with...", "timeline of...",
"last time I...", "history of..." → search episodes first:

`python3 <skill_dir>/tools/query.py --episodes --question "<question>" --vault <vault>`

Then supplement with article search if needed.

### Step 2: Frontmatter search (handles most fact queries)

`python3 <skill_dir>/tools/query.py --question "<question>" --vault <vault>`

### Step 3: Structured search (for field-based queries)

For "when does X renew?":
`python3 <skill_dir>/tools/query.py --structured --field renewal_date --within-days 90 --vault <vault>`

For "subscriptions over £20/month":
`python3 <skill_dir>/tools/query.py --structured --field cost --min-cost 240 --vault <vault>`

For a specific domain:
`python3 <skill_dir>/tools/query.py --domain projects --vault <vault>`

### Step 4: Cross-reference walk

If articles have `related:` or `entity_refs:` fields, follow them for connected info.

### Step 5: Content search (if keyword search returns nothing)

Use grep/bash to search article bodies directly.

## Answering

### If results found:

Give a direct, clear answer.

**Good:** "Your AA breakdown cover renews on 14 March 2027 — that's about 11 months away."
**Bad:** "I found an article called 'AA Breakdown Cover' in the vehicles domain..."

Always include:
- The actual answer first
- Source attribution: *(from Everything Vault: vehicles/aa-breakdown-cover.md)*
- Staleness warning if `last_verified` > 6 months or `confidence` is low
- Sensitivity flag if the article is tagged `sensitive`

### If episodes found for temporal queries:

Present in chronological order:
- "Here's what happened with the kitchen renovation:
  - 13 Apr 2026: Planning documents submitted to council
  - [date]: [next event]"

### If no results found:

Be direct: "The vault doesn't have information about that yet."
Offer to capture it.

### Staleness warnings

- `confidence: low` → "⚠ Low confidence — worth double-checking."
- `last_verified` > 6 months → "⚠ Last verified [date] — may be outdated."
- `renewal_date` passed → "⚠ Renewal date [date] has passed — needs updating."

## Concept Refinement Opportunity (v2.1)

When a query surfaces a concept article (domain contains `concepts`) and that article's
`tier` is `insight`, `concept`, or `idea`, and its `status` is `ideas`,
and `last_updated` is more than 30 days ago — offer refinement naturally after answering:

> "By the way, [concept title] has been a [tier] at [status] for [N days/months]. Want
> to spend a few minutes sharpening it while it's on your mind?"

Only offer once per concept per session. If the user declines, note it and move on.
See `prompts/concept-refinement-prompt.md` for the full refinement workflow.

## Error handling

- **Multiple matches:** Show top 3, ask user to clarify
- **Vault is empty:** Say so, offer to start capturing
- **Query too vague:** Ask a clarifying question
