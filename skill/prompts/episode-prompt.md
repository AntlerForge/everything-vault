# Episode Capture — Decision Guidance

You are recording an event in the Everything Vault's episodic memory. Episodes capture
**what happened, when, and with what outcome** — distinct from knowledge articles which
capture what is currently true.

## When to Create an Episode

Create an episode when:
- A document was submitted or filed
- A booking was made, changed, or cancelled
- A provider was contacted (phone, email, in person)
- An appointment occurred
- A subscription was cancelled or renewed
- A significant decision was made
- A task materially progressed
- A purchase was completed
- A referral was made or received

**Key principle:** Episodes are cheap to create. When in doubt, capture the event.
It's easier to ignore a redundant episode than to reconstruct a missing one.

## Step-by-step

### 1. Identify the event

From the user's message, extract:
- **What happened** (the action or event)
- **When** (date — if not stated, ask or use today)
- **Who was involved** (actors — use entity slugs where possible)
- **What was the outcome** (result, reference number, confirmation, next step)

### 2. Check for related articles

Search the vault for articles related to this event. Note them in `article_refs`.
If the event changes a fact in an existing article (e.g., "cancelled the subscription"),
you'll need to update that article too.

### 3. Write the episode

File location: `vault/episodes/YYYY/YYYY-QN/YYYY-MM-DD-short-description.md`

Quarter mapping: Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec.

Use the episode frontmatter schema from SKILL.md. The body should have:

```markdown
## What Happened

[Concise description of the event and its context]

## Outcome

[What resulted — confirmation received, reference number, next steps]

## Next Steps

[Follow-up actions if any, with dates]
```

### 4. Update related articles if needed

If the event changes a fact:
- Update the article's frontmatter to reflect the new state
- Add a row to the article's Change History table
- Update `last_updated` and `last_verified`

If the event creates a follow-up:
- Note it in the episode's `follow_up` field
- Consider creating or updating a task article

### 5. Rebuild the episode index

`python3 <skill_dir>/tools/index_builder.py --vault <vault> --domain episodes`

### 6. Confirm to user

One line: `✓ Episode: [title] → episodes/YYYY/YYYY-QN/`

If an article was also updated: `✓ Episode: [title] → episodes/YYYY/YYYY-QN/ (also updated [article])`

## Examples

### "I submitted the planning permission documents today"

Episode:
- title: Planning permission documents submitted to council
- date: 2026-04-13
- actors: [user]
- article_refs: [kitchen-renovation]
- outcomes: ["Supporting documents sent via email"]
- follow_up: "Chase if no acknowledgement by 2026-04-20"
- sensitivity: normal

Also: update the project article if it exists.

### "I cancelled Netflix"

Episode:
- title: Netflix subscription cancelled
- date: 2026-04-13
- actors: [user]
- article_refs: [netflix]
- outcomes: ["Subscription cancelled, active until end of billing period"]

Also: update the Netflix article — set a Change History entry, update status/cost.

### "Had a GP appointment, they changed my medication"

Episode:
- title: GP appointment — medication changed
- date: 2026-04-13
- actors: [user]
- entity_refs: [user]
- article_refs: [blood-pressure-medication, gp-details]
- outcomes: ["Switched medication after GP review"]
- sensitivity: sensitive

Also: update the medication article with new current state and Change History row.

## Error handling

- **Date unclear:** Ask: "When did this happen?"
- **Related article unclear:** Create the episode anyway, add article links later during curation
- **Minor event:** If it's trivial (e.g., "I checked the post"), probably not worth an episode.
  Use judgement — only capture events that the user might want to look up later.
