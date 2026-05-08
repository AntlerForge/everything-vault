# Scheduled Tasks

Three pieces of vault maintenance benefit from running automatically. None are required — the system works fine if you trigger everything by hand — but they're how the original system has been used in practice. Treat the times and exact commands as starting points, not requirements.

## End-of-day work log (18:00)

The Work Log workflow reads the day's episodes, the day-board state, and any session transcripts, and writes two artefacts:

- A structured entry at `vault/work-log/YYYY/YYYY-QN/YYYY-MM-DD.md` with `projects_touched[].{slug, kind, level, summary}` — the activity signal the project-status rule engine reads the next morning.
- A narrative daily-summary episode at `vault/episodes/YYYY/YYYY-QN/YYYY-MM-DD-daily-summary.md`.

This is an LLM workflow, not a Python script — schedule it by triggering the agent at 18:00 with the prompt "run the end-of-day work log". The exact mechanism depends on which platform is hosting your agent:

- **Cowork:** scheduled task with a prompt
  ```yaml
  name: ev-end-of-day-worklog
  schedule: "0 18 * * *"
  prompt: "Run the Work Log workflow for today. See skill/prompts/work-log-prompt.md."
  ```
- **Claude Code / Cursor / others:** wire an equivalent invocation into launchd, cron, or systemd that opens an agent session pointed at the prompt file.
- **No agent at all:** trigger yourself daily — paste `prompts/work-log-prompt.md` into your LLM of choice once a day.

The workflow is read-mostly — it skips both artefacts on quiet days and doesn't fabricate. Full schema and guardrails: `skill/prompts/work-log-prompt.md`.

## Nightly project-status inference (02:02)

The rule engine in `skill/tools/project_status.py` looks at every `tier: project` article and decides whether its lifecycle status should change.

```bash
python3 skill/tools/project_status.py --vault $EV_VAULT_PATH --apply --cache
```

The rules in brief (full table in `skill/SKILL.md` § Project Status):

- **R1.** Long-idle (60+ days) → `delivered-and-parked` (high).
- **R2.** Forward-motion activity in last 14 days on a parked project → `under-development` (high).
- **R4.** `ship` activity in last 30 days on an `ideas` concept → `prototype` (medium).
- **R5.** 3+ `operate` kinds in 30 days, no new `build` in 14 → `under-development` (high).
- **R6.** `wrap` activity, no `build` / `ship` in 30 days → `delivered-and-operational` (medium).

Plus a data-quality fix correcting legacy `completed` to `delivered-and-operational`. Only high-confidence proposals are auto-applied; medium proposals land in `<project>/_cache/project-status-proposals.json` for morning review.

This is a plain Python invocation — wire it into whichever scheduler your machine has:

- **crontab** (macOS / Linux):
  ```cron
  2 2 * * * EV_VAULT_PATH=$HOME/Documents/everything-vault/vault \
    python3 $HOME/Documents/everything-vault/skill/tools/project_status.py \
    --vault $EV_VAULT_PATH --apply --cache
  ```
- **macOS launchd:** drop a `.plist` in `~/Library/LaunchAgents/` running the same command.
- **systemd timer** (Linux): a one-shot `.service` paired with a `.timer` for `OnCalendar=*-*-* 02:02:00`.
- **Cowork:** a scheduled task running the same shell command, no LLM in the loop.
  ```yaml
  name: ev-project-status-nightly
  schedule: "2 2 * * *"
  command: "python3 skill/tools/project_status.py --vault $EV_VAULT_PATH --apply --cache"
  ```

**Why 02:02.** Late enough that the day's work log is already in. Early enough that morning review sees the proposals. Adjust to taste.

The skill's guidance is firm: never run `--apply` on demand from a chat session. Use it only from a scheduled task. For ad-hoc review, run without `--apply` and hand the proposals to the user.

## Weekly LLM selector update

The LLM Selector reads `vault/it-setup/llm-selector/llm-scores.yaml` to pick a model. New releases land every few weeks; the scores get stale. The recommended cadence is a weekly nudge to update them — again, an LLM workflow you trigger from whatever scheduler your platform supports:

```yaml
# Cowork scheduled task example
name: ev-llm-scores-weekly
schedule: "0 9 * * mon"
prompt: "Open vault/it-setup/llm-selector/llm-scores.yaml and walk through any new model releases since meta.last_updated. Suggest score updates for each."
```

For Claude Code / Cursor / others: a calendar reminder pointing you at the same prompt file is the simplest version. The agent reviews the file, lists new models, proposes scores per use case. You confirm or correct, `meta.last_updated` bumps. See `skill/prompts/llm-selector-prompt.md` for the use-case taxonomy.

## Adapting these

These three are starting points. Other useful ones: a weekly **sweep** running `prompts/sweep-prompt.md`, a monthly **renewals-check** (`curate.py --renewals --within 90`), a quarterly **stale-articles** scan (`curate.py --stale --days 180`), or a daily `rsync` backup if you're not on Git.

The pattern is the same regardless of platform: pick a tool or workflow, pick a cadence, wire it into whatever scheduler is already running — macOS launchd, cron, systemd timers, Cowork's `mcp__scheduled-tasks__*`, GitHub Actions on a schedule (if your vault is in a repo), or your own preferred runner. The Python tools and the prompt files don't care which scheduler invoked them.

For the read-mostly philosophy to hold, automated write-mode tasks should be either high-confidence-only (like `project_status.py --apply`) or surface-findings-for-review. Don't auto-merge, auto-delete, or auto-rewrite core memory in a scheduled task.
