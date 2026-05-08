# Autoresearch — Decision Guidance

You are enriching a concept-domain article with external research. The goal is to fill in
the landscape around the user's thinking — recent developments, related work, key papers,
alternative approaches — without overwriting or subordinating his original ideas.

## When to Trigger

Autoresearch requires an **explicit request**. Triggers include:
- "research [concept]"
- "what's new on [topic]"
- "enrich [article]"
- "what's out there on this?"
- "find some background on [topic]"

During concept refinement, if the user asks "what's already been written on this?" — that
is also an explicit trigger.

**Never auto-trigger.** This is always initiated by the user.

## Articles Eligible for Autoresearch

- Must be in the `concepts` domain (or cross-domain with `concepts`)
- Preferred: `tier` is `insight`, `concept`, `idea`, or `project` at `developing`/`active`/`prototype`
- Avoid: `delivered` projects (done) and `parked` concepts (intentionally shelved)

## Workflow

### 1. Read the current article

Load the concept article in full. Extract:
- The core idea, principle, or project description
- Current tags and entity_refs
- Any existing external references or `source_refs`
- Tier and status (shapes what kind of research is useful)

### 2. Formulate search queries

Based on the article, create **2–3 targeted search queries**:
- One for the core concept using domain-specific terminology
- One for recent developments (add "2025 2026" to the query)
- One for alternative approaches or counter-arguments

Keep queries specific enough to find relevant material, not so broad they drown in noise.

**For defence/S&T/EW concepts:** Use unclassified terminology only. Search for published
conference papers (NATO, TTCP, IEEE, EMRS), open-source technical reports, and publicly
available analysis. Do not reference or seek out classified material. If a result looks
like it shouldn't be public, skip it.

### 3. Search and fetch

Use WebSearch to find relevant sources. For the top **3–5 results**:
- Use WebFetch to read the full content where possible
- Extract: key claims, publication date, author/organisation, relevance to the user's concept
- Note: whether it agrees with, extends, challenges, or is orthogonal to the user's thinking

Prefer: recent publications (2024+), credible authors/organisations, primary sources.
Avoid: press releases, SEO content, unattributed summaries.

### 4. Synthesise and present as a research brief

Present findings before writing anything to the vault. Format:

---
**Research Brief: [Concept Title]**

**Searched:** [date] | **Queries used:** [list]

**Key Findings**

1. **[Source title]** — [author/org], [date]
   [2–3 sentence summary of what's relevant]
   *Relationship to your concept: [supports / extends / challenges / new angle]*

2. [repeat]

**Themes from the field**
- [What the external landscape looks like overall]
- [Where the user's thinking aligns with or diverges from mainstream thinking]
- [Any gaps or opportunities the research reveals]

**Suggested updates to the article**
- [ ] Add to article body: [specific content to add]
- [ ] New tags: [if warranted]
- [ ] New relationships: [if connections to other vault concepts are found]
- [ ] Consider: [any broader implications]

**Sources to cite:** [full URLs]
---

### 5. Apply updates on approval

the user reviews the brief and indicates what to incorporate. Apply only what he approves.

For approved content:
1. Add a `## External Research` section to the article body (or append to existing one):
   ```markdown
   ## External Research

   *Last updated: YYYY-MM-DD*

   [Synthesised findings — not a copy-paste of sources, but integrated insight]

   **Sources:**
   - [Source title](URL) — [author/org], [date]
   ```
2. Add new tags if warranted
3. Add entries to `relationships` if connections to other vault concepts were discovered
4. Update `last_updated` and `last_verified` to today
5. Run `ripple` to check if the new information affects other articles

### 6. Create an episode

For every autoresearch session, create an episode:
```
python3 <skill_dir>/tools/ingest.py episode --vault <vault> --date [today] \
  --title "Autoresearch: [concept title]"
```

Include in the episode: queries used, key sources found, what was added to the article.

## Guard Rails

**Never overwrite the user's original thinking.** External research goes in a clearly
labelled `## External Research` section. the user's ideas, observations, and framing in
the rest of the article stay intact.

**Cite everything.** Every external claim gets a source with date and author.
Unsourced synthesis is not acceptable here.

**Flag conflicts.** If sources disagree with each other, or with the user's current article,
say so explicitly in the brief: "Note: [Source A] argues X while [Source B] argues the
opposite. Your current article aligns with [X/Y/neither]."

**Keep it focused.** 3–5 sources per session. Not exhaustive — relevant and recent.
It's better to find 3 excellent sources than 10 mediocre ones.

**Respect classification context.** For defence/EW topics: unclassified only. If a
result's origin is unclear, skip it and note why.

**Don't over-research parked concepts.** If the user asks to research something marked
`parked`, check: "This concept is currently parked — still want to research it?"
