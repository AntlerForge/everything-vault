# EV Sweep — Maintenance Composition

A sweep is a single composed round of EV maintenance, triggered by the user saying
"EV sweep" (or close variants like "do a sweep", "sweep the vault", "run a EV sweep").
It deliberately composes existing capabilities rather than adding new behaviour — the
value is the routine, not any new primitive.

## Purpose

One named call that answers:

- **Did anything from the current session need filing?**
- **Has anything shifted that means `active-context.md` is out of date?**
- **Are there contradictions that haven't been adjudicated?**
- **What's stale, missing, or clearly converging?**

Without a sweep, these live as separate workflows that each require a separate
trigger. The sweep is the ritual that makes sure they get composed regularly.

## Scope

Default scope is **session-aware full**: include Session Promotion for the current
conversation, then run a comprehensive maintenance round over the whole vault.

the user can narrow explicitly:

| Phrase | Scope |
|--------|-------|
| "EV sweep" | Default — session-aware full sweep |
| "EV sweep session" / "sweep this session" | Session Promotion + active-context delta only, no full curate/consolidate |
| "EV sweep concepts" (or any domain) | Limit curate + consolidate passes to that domain |
| "EV sweep last week" / "since <date>" | Limit stale / orphan / holding-pen checks to items touched in that window |
| "Quick sweep" | Skip consolidate; run session capture + active-context + stale + holding-pen only |
| "Deep sweep" | Include autoresearch candidates flagging (but never run autoresearch itself) |

Default is **read-mostly**: the sweep surfaces findings and proposes actions. Nothing
is written without the user's approval except the closing episode record.

## Ordering

Order matters — earlier steps reduce false positives in later ones.

1. **Voice inbox sweep.** If the active platform exposes a voice/notes inbox
   (see the relevant `PLATFORM-<name>.md` for how it's wired — e.g. an Apple
   Notes integration, a notes-MCP, a webhook drop), read the inbox note named
   "EV Inbox". If it contains timestamped voice-captured entries (format:
   `[YYYY-MM-DD HH:MM]` followed by transcribed text), classify each one:
   - Idea / insight / concept → ingest as a new concept article or addition to existing
   - Event / appointment → ingest as an episode or calendar entry
   - Task completion ("I've done X") → mark the relevant task done
   - Reminder / todo → add to the task list
   - Ambiguous → flag for the user to clarify, don't guess

   **Auto-action:** Entries with obvious intent are ingested immediately without
   asking the user to approve each one. Only flag genuinely ambiguous entries. The
   whole point of voice capture is low-friction — a confirmation step per entry
   defeats the purpose.

   **Extract temporal signals from the transcription.** Natural-language time
   references must be resolved to concrete dates before writing:
   - "today" / "for today" → today's date in the Due field
   - "tomorrow" → tomorrow's date
   - "this week" / "before Friday" → the named day
   - "before Seville" / "before the trip" → look up the relevant departure date
     in `core/active-context.md`
   - "after Sam is back" / "when X happens" → note the condition in the Notes
     field; set Due to the resolved date if known, otherwise leave blank
   - No temporal signal → no due date (leave Due as `—`)

   After processing, update the note to remove ingested entries (keep the header).
   If the note is empty or no voice-inbox channel is wired up for the active
   platform, skip silently — don't try to fall back to anything else.

2. **Session capture.** Run Session Promotion for the current conversation
   *before* the curate pass. Otherwise the curate pass may flag "gaps" that the
   session was about to fill.

3. **Active-context delta.** Read `core/active-context.md`. Ask: did anything in
   this session shift priorities, close a "thing in flight", or change an open
   item? Propose specific edits — don't rewrite silently.

4. **Conflict sweep.** Scan for any contradictions surfaced during the session
   that haven't been resolved via Conflict Resolution. If any, adjudicate before
   moving on. This prevents the curate pass from fossilising a half-resolved
   claim.

5. **Curate pass.** Run `curate.py` with `--stale`, `--holding-pen`, `--gaps`,
   `--validate`, `--sensitivity-audit`. Group findings by type. Present in
   order of likely impact (stale first, then sensitivity, then holding-pen,
   then gaps, then validation).

6. **Consolidate pass.** Run `consolidate.py --check all`. Surface convergence,
   orphan episodes, resolved tasks, missing links, stale concepts.

7. **Index health.** Rebuild any indexes whose domain was touched. Check
   `<project>/_cache/consolidation.json` isn't stale.

8. **Report.** Short, structured summary (see format below). Offer next
   actions as a numbered list the user can pick from.

9. **Close with an episode.** Record the sweep itself as an episode in
   `episodes/YYYY/YYYY-QN/` so the vault has a history of maintenance
   activity.

## Presenting findings

Findings can be large. Keep it scannable. One pattern that works:

```
## Sweep report — 2026-04-21

### Voice inbox (3 entries)
- [10:23] Assurance culture thought → add to existing concept. [ingest / skip]
- [10:25] Professionalism as control mechanism → merge with above. [ingest / skip]
- [11:40] "Completed pottery class signup, booked appointment Thursday" → mark T050 done,
  add episode for the appointment. [apply / skip]

### Session capture (1 item)
- Operator intent capture in EW context → propose concept article. [file / skip]

### Active-context delta
- "Subscriptions audit — downgrade plan tier" reached decision this session.
  Propose: move to episode, remove from active-context. [yes / no / edit]

### Conflicts (0)
None outstanding.

### Curate (7 findings)
- 3 stale concepts (`ideas`, last_updated > 30 days)
- 2 holding-pen items awaiting classification
- 1 sensitivity-audit candidate (financial note tagged normal)
- 1 validation issue (missing `confidence` field on article X)

### Consolidate (3 findings)
- Convergence: 3 concepts around AI adoption framing — worth merging?
- Orphan episode: 2026-04-08 event has no article link
- Missing link: capability-composability references operator-intent-capture
  but not vice versa

### Suggested next actions (pick any)
1. File the session-capture concept
2. Edit active-context per delta
3. Review sensitivity-audit candidate
4. Decide on AI-adoption convergence
```

Group related findings. Never dump raw tool output. Never auto-apply.

## What the sweep explicitly does **not** do

- **Does not run autoresearch.** Autoresearch always requires an explicit
  request — sweep only *flags* candidates where it might help.
- **Does not merge or delete articles.** It proposes. the user decides.
- **Does not push to git.** That's the user's call (and outside the skill anyway).
- **Does not rewrite core memory.** `whoami.md`, `preferences.md`,
  `key-people.md` are never silently edited by a sweep.
- **Does not repeat work from this session.** If Session Promotion already
  filed items, the curate pass should not re-propose them.

## When not to offer a sweep

- Mid-task, unless the user explicitly asks
- When the session was trivial (no new facts, no priority shifts, no
  decisions) — just run Session Promotion and stop
- When energy is low — a full sweep is cognitive load; offer a "quick sweep"
  (step 1 + step 2 + stale check) as the alternative

## Tool calls — quick reference

```bash
# Session promotion decision is made by reading the conversation,
# no direct tool call needed.

python3 <skill_dir>/tools/curate.py --vault <vault> --stale
python3 <skill_dir>/tools/curate.py --vault <vault> --holding-pen
python3 <skill_dir>/tools/curate.py --vault <vault> --gaps
python3 <skill_dir>/tools/curate.py --vault <vault> --validate
python3 <skill_dir>/tools/curate.py --vault <vault> --sensitivity-audit

python3 <skill_dir>/tools/consolidate.py --vault <vault> --check all

python3 <skill_dir>/tools/index_builder.py <domain>   # per touched domain
```

For domain-scoped sweeps, pass `--domain <slug>` through to curate /
consolidate where supported, or filter the output before presentation.

## Closing episode

After the sweep, create an episode:

```yaml
---
title: "EV sweep — YYYY-MM-DD"
domains: [episodes]
type: log
object_type: episode
date: YYYY-MM-DD
actors: [user]
article_refs: []                 # articles touched (if any)
outcomes:
  - Ran session-aware full sweep
  - Captured N session items
  - Actioned M curate findings
  - Deferred K for later
follow_up: null
tags: [ev-sweep, maintenance]
sensitivity: normal
retrieval_default: searchable
source: conversation
created: YYYY-MM-DD
confidence: high
---

## Summary

Brief one-paragraph summary of what the sweep found and what the user actioned vs
deferred.
```

Rebuild the episode index after writing.

## Confirm

After the episode is written:

`✓ Sweep complete → [N captured, M actioned, K deferred] · episode: [slug]`
