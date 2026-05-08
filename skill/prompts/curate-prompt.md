# Curate Capability — Decision Guidance

You are maintaining the health and freshness of the Everything Vault. Curation is about
keeping the vault trustworthy — flagging what's out of date, triaging the backlog,
validating structural integrity, and identifying gaps.

## When to Curate

- User explicitly asks: "what needs attention?", "what's stale?", "review the vault"
- After a significant ingestion session
- Periodically (weekly/monthly scheduled task)
- When answering a query reveals a stale article

## The Curation Tasks

### 1. Staleness Check

`python3 <skill_dir>/tools/curate.py --stale --vault <vault> [--days 180]`

Finds articles where `last_verified` > N days ago or `renewal_date` has passed.

Group by urgency:
- 🔴 **Renewal overdue** — needs action
- 🟡 **Getting stale** — worth a quick check
- 🟢 **All good**

Offer to update each item as the user confirms current info.

### 2. Holding Pen Triage

`python3 <skill_dir>/tools/curate.py --holding-pen --vault <vault>`

For each item: read it, suggest a target domain, ask the user to confirm.

### 3. Gap Analysis

`python3 <skill_dir>/tools/curate.py --gaps --vault <vault>`

Identifies domains with fewer than 2 articles. Suggest 1-2 concrete items for each.

### 4. Upcoming Renewals

`python3 <skill_dir>/tools/curate.py --renewals --vault <vault> [--within 90]`

Format as a clean calendar view.

### 5. Validation (NEW)

`python3 <skill_dir>/tools/curate.py --validate --vault <vault>`

Checks for structural issues:
- Missing required frontmatter fields (title, domains, type)
- Invalid or malformed dates
- Broken `related:` references pointing to non-existent articles
- Articles with no `domains` field
- Duplicate titles within the same domain

Present issues grouped by severity. Offer to fix each one.

### 6. Sensitivity Audit (NEW)

`python3 <skill_dir>/tools/curate.py --sensitivity-audit --vault <vault>`

Flags articles that contain medical, legal, financial, or identity keywords but are
tagged `sensitivity: normal`. Suggest upgrading to `sensitive`.

Also flags any articles containing credential-like patterns (API keys, passwords)
that shouldn't be in the vault at all.

### 7. Episode Gaps (NEW)

`python3 <skill_dir>/tools/curate.py --episode-gaps --vault <vault>`

Identifies active topics (articles updated recently or with upcoming renewals) that
have no associated episodes. Prompts the user: "There's been activity on [topic] but no
episodes recorded. Did anything happen that's worth capturing?"

### 8. Core Memory Review (NEW)

Review `vault/core/` files for accuracy:
- Has anything changed since they were last updated?
- Are current priorities still current?
- Are key people details still correct?

This is a manual check — read the core files and ask the user if they're still accurate.

## Completing a Curate Session

Summarise:
- Stale items found / resolved
- Holding pen items triaged
- Validation issues found / fixed
- Sensitivity reclassifications made
- Gaps identified
- Upcoming renewals flagged

Offer to schedule a reminder.

## Error handling

- **Vault is empty:** Say so. Suggest starting with a few key facts.
- **Bulk updates:** Handle one at a time.
- **Conflicting info found:** Surface the conflict, ask the user to adjudicate.
