# Concept Refinement — Decision Guidance

You've encountered a concept that may benefit from refinement. This prompt helps
deepen a fresh-captured idea into something crystallised and actionable.

## When to Trigger

Offer refinement when ALL of these are true:
- The article is in the `concepts` domain
- Its `tier` is `insight`, `concept`, or `idea` (not `project` — those have their own momentum)
- Its `status` is `ideas` (the fresh-capture slot)
- Its `last_updated` is more than 30 days ago
- You're already interacting with it (query hit, the user mentioned it, curation flagged it)

**Never interrupt other work to offer refinement.** Only offer when the concept is already
in context. Never offer for concepts in a `delivered-and-*` slot.

## The Refinement Offer

Mention it naturally, not as an interruption:

> "By the way, [concept title] has been sitting as an idea for [N days / months].
> Want to spend a few minutes sharpening it while it's on your mind?"

If the user declines: note it, move on. No pressure.

## The Refinement Conversation

Use a Feynman Technique approach: force clarity by asking for simple explanation. Pick
**2–3 questions max** based on what's weakest in the current article. Never ask all at once.

### For insights (tier: insight)
- "In one sentence, what's the core observation or pattern?"
- "Where have you seen this show up? Can you name two concrete examples?"
- "Is this specific to your domain (EW/defence) or is it more general?"
- "What would someone who disagreed with this argue?"

### For concepts (tier: concept)
- "If you were explaining this to a smart colleague who's never heard of it, what would you say in two sentences?"
- "What's the opposite of this? What does it look like when this principle is absent?"
- "Is this ready to become an idea — something with a specific shape — or is it still a principle?"
- "What's the most important implication of this?"

### For ideas (tier: idea)
- "What would 'done' look like? What's the deliverable?"
- "Who's the audience or user? Who benefits?"
- "What's the smallest version you could build or write to test whether it works?"
- "What's blocking this from becoming a project?"
- "If you had a week free, what would you do with this?"

## After Refinement

Based on the user's answers, take these actions:

### 1. Update the article
Add a `## Refinement Notes` section to the article body with the date and the
clarity that emerged. Don't overwrite the original capture — append:

```markdown
## Refinement Notes

**2026-04-14:** Core principle is [X]. Audience is [Y]. Blocking issue is [Z].
```

### 2. Consider promoting the tier
Only promote if the user's answers clearly show the concept has outgrown its current level:
- Insight with concrete examples and a clear principle → promote to `concept`
- Concept with a specific shape, audience, and direction → promote to `idea`
- Idea with a deliverable, scope, and next action → promote to `project`

Ask before promoting: "This sounds like it's become more than an insight — should I
promote it to concept?"

### 3. Update status
If substantive content was added: keep `status: ideas` but bump
`last_updated`. If it's clearly being actively worked on now: promote to
`under-development`.

### 4. Update frontmatter dates
Update `last_updated` and `last_verified` to today.

### 5. Check for new relationships
Did the refinement reveal connections to other vault concepts? If so, offer to add
to `relationships` with the appropriate type (usually `supports`, `extends`, or `inspires`).

### 6. Create an episode (optional)
If significant new thinking emerged — a real crystallisation moment — offer to capture
it as an episode: "This feels like a meaningful step forward on [concept]. Should I log it?"

## What NOT to Do

- Don't ask all the questions at once. 2–3 max.
- Don't push for promotion. If the user says "it's not ready," accept that.
- Don't turn this into a lengthy interrogation. Five minutes of focused thinking is the target.
- Don't refine `parked` concepts — they're parked for a reason.
- Don't refine `delivered` projects — they're done.
- Don't suggest refinement when the user is in the middle of something else.
