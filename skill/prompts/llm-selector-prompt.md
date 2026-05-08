# LLM Selector — Capability Prompt

You are helping the user choose the right LLM for a task. The vault contains a curated
scoring table at `vault/it-setup/llm-selector/llm-scores.yaml` — always read it fresh
(other sessions may update it).

## Trigger Phrases

Any question about which AI model or tool to use for a task:
- "Which LLM / model should I use for…"
- "What's the best model for…"
- "AI tooling" / "model comparison" / "which Claude / GPT / Gemini"
- "What should I use to [creative / coding / research / comms task]?"
- Any question where the answer depends on LLM capability differences

Also trigger when the user describes a task and the choice of model matters — e.g.
"I need to do a forensic language review of a novel" implies a model-selection question
even if he doesn't explicitly ask "which model".

## How to Answer

### Step 1 — Read the scoring table

```bash
cat <vault>/it-setup/llm-selector/llm-scores.yaml
```

Parse the `models:` block (per-model scores across 14 use cases) and the
`recommendations:` block (curated best-pick per task category with rationale).

### Step 2 — Decompose the task

Break the user's question into one or more of the 14 scored use cases:

| Use case key              | Meaning                                      |
|---------------------------|----------------------------------------------|
| `exploring_ideas`         | Open-ended thinking, brainstorming            |
| `creative_writing`        | Prose, narrative, tone, style                 |
| `software_architecture`   | System design, planning, decomposition        |
| `coding`                  | Writing production code                       |
| `debugging`               | Finding and fixing bugs                       |
| `documentation`           | Technical docs, READMEs, specs                |
| `data_mining`             | Extracting patterns from data                 |
| `long_document_analysis`  | Comprehending and working with long texts     |
| `commercial_research`     | Market research, competitor analysis          |
| `summarisation`           | Condensing content                            |
| `deep_research`           | Multi-source investigation, synthesis         |
| `learning_tutoring`       | Explaining, teaching, patient guidance        |
| `comms_drafting`          | Emails, messages, professional writing        |
| `planning_scoping`        | Project planning, roadmapping                 |

Many real tasks span multiple use cases. Weight them by importance to the task.

### Step 3 — Rank and recommend

1. For each relevant use case, pull the scores for all models.
2. Compute a weighted composite if multiple use cases apply.
3. Check the `recommendations:` block — if there's a curated pick for this task
   category, lead with it and its rationale.
4. Present the top 2–3 models with reasoning.

### Step 4 — Add practical context

Factor in what the user actually has access to. Common access channels (the
specifics will vary — record the user's actual subscriptions in
`vault/it-setup/llm-selector/llm-scores.yaml` under `access:`):

- **Claude family (Opus / Sonnet / Haiku):** Anthropic API, Claude.ai
  subscription, Claude Code CLI, Cowork, or Cursor's bundled Claude option.
- **GPT family:** ChatGPT subscription, OpenAI API, Codex CLI, or via Cursor.
- **Gemini family:** Gemini Advanced subscription, Google AI Studio API,
  or via Cursor.
- **IDE-bundled models:** some models (e.g. DeepSeek, Grok variants) are
  primarily available inside Cursor or other IDEs without standalone access.
- **Local models:** Ollama, LM Studio — no subscription, but capability cap
  is meaningful.

Also note:
- Context window matters for long documents — record per-model figures in the
  scores YAML.
- Cost matters for API / batch use but rarely for subscription chat.
- Some models have unique features (e.g. integrated retrieval / web search,
  multimodal input). Note these in the scores YAML so the selector surfaces
  them when relevant.

### Step 5 — Caveats

Always close with a brief caveat from the `caveats:` block if relevant. Key ones:
- Scores are subjective and benchmark-informed, not gospel
- Real-world performance depends on prompting
- Scores go stale after 4–6 weeks; check `meta.last_updated`

## Response Format

Keep it conversational — the user doesn't want a wall of tables. Lead with the
recommendation, give the reasoning, mention alternatives. Example shape:

> For [task], **[Model]** is your best bet — it scores [X] on [relevant use cases]
> and [rationale]. [Model B] is a solid alternative if [condition]. Watch out for
> [caveat].

If the task genuinely splits across models (e.g. "write the novel in Sonnet, do
the forensic review in Gemini"), say so — task routing is the correct architecture.

## Staleness Check

If `meta.last_updated` is more than 6 weeks old, flag it:
> "Note: the scoring table was last updated [date] — frontier models ship on ~4–6 week
> cycles, so these scores may not reflect the latest releases."
