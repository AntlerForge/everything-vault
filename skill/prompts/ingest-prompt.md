# Ingest Capability — Decision Guidance

You are capturing information into the Everything Vault. Your job is to turn what the user
has shared into a well-structured knowledge article.

## Step-by-step

### 1. Identify what's being shared

Parse the user's message and extract:
- **Facts** (dates, amounts, numbers, identifiers)
- **How-to information** (steps, processes, instructions)
- **Contact details** (names, phone, email, role)
- **Background/context** (descriptions, explanations)
- **Events** (something that happened — may need an episode too)

Multiple types can exist in one message — create separate articles if topics are distinct,
or combine if tightly related.

### 2. Scan for existing articles first

Run: `python3 <skill_dir>/tools/ingest.py scan --vault <vault> --query "<key topic words>"`

If a relevant article exists:
- **Update it** rather than creating a duplicate
- **Check for conflicts** — if the new info contradicts what's there, surface both values
  and ask the user which is correct (see Conflict Resolution in SKILL.md)
- Preserve existing information, add new info, update `last_updated` and `last_verified`

If no relevant article exists:
- Create a new one

### 3. Choose the domain(s)

Use the domain map in SKILL.md. Ask yourself:
- Which part of the user's life does this relate to?
- Could it belong to multiple domains? (Common: `[family, it-setup]`, `[household, finance]`,
  `[vehicles, finance]`, `[household, legal]`)

If genuinely unsure: use `holding-pen` and tell the user.

### 4. Choose the article type and object type

**Article type:**

| Type | Use when... |
|------|------------|
| `fact` | It's a specific datum — a date, amount, policy number, renewal detail |
| `account` | It's a service or website the user logs into |
| `how-to` | It explains how to do something step by step |
| `reference` | It provides background context or describes a setup/system |
| `log` | It's a timestamped record of something that happened |
| `contact` | It's a person or organisation's contact details |

**Object type:**

| Object Type | Use when... |
|-------------|------------|
| `article` | Default. Most knowledge articles. |
| `entity` | The article primarily describes a persistent real-world thing: a person, account, vehicle, device, organisation, or project. Add `entity_type` and optionally `aliases`. |
| `episode` | Use the episode workflow instead (see prompts/episode-prompt.md). |

**Don't force entity type.** Most articles stay as plain articles. Only tag something as
an entity when it genuinely represents a persistent thing that other articles reference.

### 5. Set confidence

| Level | When |
|-------|------|
| `high` | Came from an official document, confirmed by the user explicitly |
| `medium` | Shared in conversation, believed correct |
| `low` | Uncertain, approximate, from memory, needs verification |

Default for conversational capture: `medium`.
Default for filed document: `high`.

### 5b. Check for login info (account type)

If the information relates to a service the user logs into, and no login method was mentioned:

> "How do you log in to this — email/password, Apple, Google, email OTP, or an authenticator
> app? And if there's a password, is it in mSecure or Apple Passwords?"

Login fields: `login_method`, `password_manager`, `login_email`.

### 5c. Set sensitivity

| Level | When |
|-------|------|
| `normal` | Default. General personal information. |
| `sensitive` | Medical details, legal correspondence, identity documents, financial specifics |
| `credential` | Passwords, recovery codes, API keys — **do not store these in the vault** |

If the content is sensitive, set `sensitivity: sensitive`. If it's a credential, gently
note that you won't capture it and suggest a password manager.

### 5d. Extract temporal signals

When the user's message (or a voice transcription) contains natural-language time
references, resolve them to concrete dates before writing. This applies to any field
that takes a date — `due`, `date`, `renewal_date`, `created`, etc.

| Signal | Resolution |
|--------|-----------|
| "today" / "for today" | Today's date |
| "tomorrow" | Tomorrow's date |
| "this week" / "by Friday" / "before Thursday" | The named day this week |
| "next week" / "next Monday" | The named day next week |
| "before the trip" / "before Seville" | Look up the departure date in `core/active-context.md` |
| "after Sam is back" / "when X happens" | Note the condition in a free-text field; resolve the date if the event date is known in the vault, otherwise leave blank |
| "in a couple of weeks" / "end of May" | Best-estimate date |
| No temporal signal | Leave date fields blank or `—` |

**Always convert relative dates to absolute dates.** "Thursday" in a message sent on
Monday 2026-04-28 becomes `2026-05-01`, not "Thursday". Relative dates become
meaningless once the conversation is over.

### 5e. Set tier for concepts-domain articles

If the article belongs to the `concepts` domain, you **must** set the `tier` field. The
concepts hierarchy is a four-rung ladder — each rung has a specific meaning:

| Tier | Meaning | Set when... |
|------|---------|-------------|
| `insight` | An observation, pattern, or nugget worth noting | User says "insight", "observation", "I noticed", "pattern", or shares a standalone observation that isn't yet a crystallised principle. **This is the default entry point for thinking-aloud capture.** |
| `concept` | A crystallised principle or design approach | The idea has been refined into a clear, reusable principle with implications. Usually promoted from insight after refinement, not created directly. |
| `idea` | A specific possibility with enough shape to explore | Has a direction, audience, and rough scope — more than a principle, not yet a project. |
| `project` | Something with scope, intent, and (often) code | Has deliverables, a plan, and active work. Usually gets its own `projects/` article too. |

**Critical rule:** When the user says "add an insight" or "I had an insight", set
`tier: insight`, NOT `tier: concept`. Insights are the lightest capture — observations
worth keeping that may later be promoted. Don't over-classify. The user explicitly
choosing the word "insight" is a strong signal.

**When ambiguous:** Default to `insight` for thinking-aloud and observations. Only use
`concept` if the user presents a crystallised, reusable principle with clear implications.
Only use `idea` if there's a specific direction and rough scope. Only use `project` if
there are deliverables and active work.

Also set `status` (usually `ideas` for new captures at any tier).

### 6. Draft the article

For **simple facts**: just write it — no pre-writing proposal needed.

For **complex or multi-part articles**: briefly confirm interpretation before writing.

### 7. Write the article

Structure: YAML frontmatter + markdown body.

**Frontmatter must include:** title, domains, type, source, created, last_updated,
last_verified, confidence.

**v2 fields to include when relevant:** object_type, id, sensitivity, retrieval_default,
entity_refs, **tier** (concepts domain — see 5e).

**For entity type also include:** entity_type, aliases.

**For account type also include:** login_method, password_manager, login_email.

**If updating a time-varying fact:** Don't just overwrite the old value. Add a row to the
Change History table in the article body:

```markdown
## Change History

| Date | Change | Source | Confidence |
|------|--------|--------|------------|
| 2026-04-13 | Changed provider from X to Y | Conversation | Medium |
```

### 8. Consider creating an episode

If the user's message describes something that **happened** (not just a fact):
- "I called the insurance company" → episode
- "I cancelled Netflix" → episode
- "My car insurance is with SomeProvider" → no episode (just a fact)
- "I switched from SomeProvider to AnotherProvider" → episode (something changed)

See `prompts/episode-prompt.md` for the full episode workflow.

### 8b. Run ripple scan (v2.1)

After writing a new article or making a significant update, run the ripple scan to identify
other articles that may be affected by this new information:

`python3 <skill_dir>/tools/ingest.py --vault <vault> ripple --source <article_filename.md>`

Review the output:
- **🔗 DIRECT** hits — articles that directly reference the one you just wrote. Check if they
  need updating (e.g., a related article should mention the new detail).
- **👤 ENTITY** hits — articles sharing entity refs. Scan for potential conflicts or updates.
- **🏷 TAG** hits — articles with strong tag/domain overlap. Usually no action needed, but
  worth a quick scan if the new info is significant.

**When to act on ripple results:**
- New info **contradicts** something in a related article → surface the conflict to the user
- New info **extends or supersedes** a related article → offer to add a `relationships` link
- New info is **simply related** → no action needed, just awareness

Skip the ripple scan for: minor edits, typo corrections, or date-only updates.

### 9. Rebuild the index

`python3 <skill_dir>/tools/index_builder.py --vault <vault> --domain <primary_domain>`

### 10. Confirm to the user

**One line only.** Format: `✓ [Title] → [domain(s)]`

If an episode was also created: `✓ [Title] → [domain(s)] + episode captured`

The only exceptions where you may add a second line:
- Ambiguous judgement call
- Parked in holding-pen
- Need one specific piece of information

## Error handling

- **Can't determine domain:** → holding-pen. Tell user what you'd suggest.
- **Contradicts existing article:** → surface both values, ask which is correct.
  Never silently overwrite. Add both to Change History if resolved.
- **User shares very little info:** → capture what you have, confidence: low, note what's missing.
- **Sensitive info (passwords, full card numbers):** → don't capture. Suggest password manager.
