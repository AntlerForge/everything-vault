# Consolidation — Decision Guidance

You are running a consolidation pass across the Everything Vault. This is a synthesis
operation — you're looking for patterns, connections, and gaps that individual ingests
and queries miss because they only see one article at a time.

## When to Run

- **Scheduled:** Nightly at 0200 via the platform's scheduled-task mechanism
  (Cowork's `mcp__scheduled-tasks__*`, macOS launchd, cron, systemd — whichever
  the user has set up; runs with `--save`)
- **On demand:** "run a consolidation", "what patterns do you see?", "anything converging?",
  "what's the vault missing?"
- **After a busy week:** Following significant ingestion sessions

## Step 0 (nightly only) — Project-Status Inference

Before the main consolidation checks, run the project-status inference tool. This
reads every `tier: project` article and looks at three signals:

- the article's own `last_updated`
- episodes whose `article_refs` include the project's slug
- work-logs whose `projects_touched[].slug` matches (see `vault/work-log/_index.md`
  for the schema and activity-kind taxonomy)

It applies five rules (long-idle → parked, developing + ship → prototype,
prototype + sustained operate → active, active + wrap without new build →
delivered-and-operational, parked + forward-motion → developing) and, with
`--apply`, rewrites frontmatter + prepends a Change History
row for any **high-confidence** proposals. Medium-confidence proposals are written
to the cache for morning review.

```
python3 <skill_dir>/tools/project_status.py --vault <vault> --apply --cache
```

Cache file: `<project>/_cache/project-status-proposals.json` (sibling of `vault/`, overwritten each run). Legacy in-vault location is read as a fallback during this release.

Report in the nightly output: projects scanned, proposals, applied (count), and
any medium-confidence proposals that need adjudication.

**Do not run the `--apply` variant on demand** — only the scheduled nightly task
auto-applies. For ad-hoc review during the day, use:

```
python3 <skill_dir>/tools/project_status.py --vault <vault>        # report only
```

Then hand the proposals to the user for approval, as with any other consolidation finding.

## IMPORTANT: Check for Cache Before Re-Running

When the user asks to review or action consolidation findings, **always check for a cached
result first** before running the checks again:

```
python3 <skill_dir>/tools/consolidate.py --vault <vault> --load-cache
```

If a cache exists and was generated today or yesterday, use it — do not re-run.
If the cache is older than 2 days or doesn't exist, run fresh with `--save`:

```
python3 <skill_dir>/tools/consolidate.py --vault <vault> --check all --save
```

The cache lives at `<project>/_cache/consolidation.json` (a sibling of `vault/`). The legacy in-vault location is read as a fallback during this release.

## Running the Checks

```
python3 <skill_dir>/tools/consolidate.py --vault <vault> --check all --save
```

Or individual checks (note: `--save` only saves what was checked):
```
python3 <skill_dir>/tools/consolidate.py --vault <vault> --check convergence --save
python3 <skill_dir>/tools/consolidate.py --vault <vault> --check orphan-episodes
python3 <skill_dir>/tools/consolidate.py --vault <vault> --check resolved-tasks
python3 <skill_dir>/tools/consolidate.py --vault <vault> --check missing-links
python3 <skill_dir>/tools/consolidate.py --vault <vault> --check concept-stale
```

## Review Mode — Interactive Actioning

When the user wants to work through findings, use **Review Mode**: present each finding
one at a time (or in small batches of 2–3) with lettered options. Wait for the user's
response before moving to the next finding.

**Never present all findings at once as a wall of text.**

### Convergence findings — present as:

> **[A] ↔ [B]** (overlap score: N)
> Shared: [tags/entities]
> Brief one-line description of each concept.
>
> **A** — Link  **B** — Merge  **C** — Skip  **D** — Parent concept needed

- **A — Link:** Ask which relationship type (supports / extends / implements / inspires /
  refines / contradicts / supersedes), then write to both articles.
- **B — Merge:** Confirm which article absorbs the other, fold content, update all refs.
- **C — Skip:** Note as confirmed-distinct. No action.
- **D — Parent concept needed:** Note the gap, offer to capture the parent concept now
  or add it to the task list. This is the right answer when both concepts share a common
  theme that isn't yet captured.

### Orphan episodes — present as:

> **Episode: [title]** ([date])
> No article links. Possible match: [suggested article(s)] via [shared entities].
>
> **A** — Link to [suggested]  **B** — Different article  **C** — No link needed

### Resolved tasks — present as:

> **[T-ID]** — [task description]
> Source article '[title]' updated [date]. Keywords found: [keywords].
>
> **A** — Mark resolved  **B** — Still open  **C** — Check it myself

### Missing links — present as:

> **[A] + [B]** appear together in [N] episodes but aren't cross-linked.
>
> **A** — Link them  **B** — Skip

### Stale concepts — present as:

> **[Concept title]** — [tier] / [status] — stale for [N days]
>
> **A** — Refine now  **B** — Skip for now

## Handling "Link" responses

When the user selects Link, immediately ask for the relationship type if it's not obvious:

> "Which direction best describes it?
> **A** supports  **B** extends  **C** implements  **D** inspires  **E** refines"

Then write the relationship to both articles without further confirmation — the user has
already approved the link, don't ask again.

## Handling "Parent concept needed" responses

When the user indicates two concepts link to a common parent that doesn't exist yet:
1. Ask the user to name or describe the parent concept briefly
2. Capture it as a new article immediately
3. Link both children to it as `supports` (or ask if a different type fits)
4. Continue the review queue

## Pacing

After each batch of 2–3 findings, check in:
> "That's [N] done, [M] remaining. Keep going?"

Don't power through all 32 findings without a break — the user controls the pace.

## Interpreting Results

### Convergence
Two concepts sharing significant tag/entity overlap may be aspects of the same idea, or
may be distinct concepts that should be explicitly connected. Score ≥ 4 is high confidence;
score 3 may just be "same field of work" with no meaningful link.

### Orphan Episodes
An episode with no article links is a missed connection. Read the episode content,
identify which articles it likely relates to before presenting options.

### Resolved Tasks
**Never auto-close tasks.** the user must confirm. When marking done: edit
`tasks/todo-list.md`, move row to Completed Tasks section, add completion date.

### Missing Links
Articles appearing together repeatedly in episodes probably belong in each other's
`related` lists. Propose the link.

### Stale Concepts
Offer refinement for the top 3, in order of staleness. Use concept-refinement-prompt.md.

## Output Format — Scheduled Run (no review)

When running as a scheduled task (no interactive review), present findings as a brief
summary to be picked up next session:

**If nothing found:**
> "Consolidation pass complete — vault looks healthy. 👍 Results saved."

**If findings exist:**
> "Consolidation pass found [N] thing(s) to review:
> - [N] converging concept pairs
> - [N] orphan episodes
> - [N] possibly resolved tasks
> - [N] missing cross-links
> - [N] stale concepts
>
> Results saved. Say 'let's action the consolidation findings' to work through them."

## After a Review Session

Summarise what was done:
- Relationships added: N
- Episodes linked: N
- Tasks closed: N
- Concepts refined: N

Offer to rebuild all indexes if significant changes were made:
`python3 <skill_dir>/tools/index_builder.py --vault <vault> --domain <domain>`
