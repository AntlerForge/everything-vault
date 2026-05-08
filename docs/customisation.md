# Customisation

The vault is plain markdown — most customisation is just editing files. A few things have an opinionated structure worth understanding before you change them.

## Adding a new domain

To add a new domain (say `gardening`):

1. Create the folder: `vault/gardening/`.
2. Add a row to the Domain Map table in `skill/SCHEMA.md` § Domain Map. One line: slug, brief description.
3. Update `vault/ev-manifest.yaml` so the manifest reflects what's there.
4. Rebuild the index:

   ```bash
   python3 skill/tools/index_builder.py --domain gardening
   ```

The Python tools don't hard-code a domain list — they take the slug from frontmatter, so a new domain works the moment the folder exists. Editing `SCHEMA.md` and `ev-manifest.yaml` keeps the LLM and the index in sync.

## Removing a domain

Delete the folder. Nothing else cares. The next index rebuild won't include it.

## Changing the default domain map

Edit `skill/SCHEMA.md` § Domain Map and `vault/ev-manifest.yaml` to match. If you're shipping the skill as a plugin, `SCHEMA.md` is part of the bundle — your customised map travels with it.

## Adding custom frontmatter fields

The lightweight YAML parser in `dashboard/build_dashboard.py` picks up any field you add — there's no whitelist. So `wattage:` or `colour:` shows up in `ev-data.json` and `query.py` can search it via `--structured --field`.

Honest limit: the dashboard front-end won't render unknown fields automatically. To make a new field appear in the UI, edit `dashboard.html` — the card renderers (`renderTreeLeaf`, `renderKanban`, `renderProjects`, `renderTasks`, `renderTimeline`) are where to look.

## Theming

CSS variables live at the top of `<style>` in `dashboard.html`:

```css
:root {
  --bg: #0f172a; --surface: #1e293b; --surface2: #334155;
  --border: #475569; --text: #e2e8f0; --text-dim: #94a3b8;
  --accent: #38bdf8; --green: #4ade80; --amber: #fbbf24;
  --red: #f87171; --purple: #a78bfa; --teal: #2dd4bf;
}
```

Edit those and most of the dashboard re-themes. The default palette is red/green colour-blind safe — `--green` is yellow-green and `--red` is salmon, not pure complementary colours.

Honest note: the dashboard is a single ~2,000-line HTML file. CSS, HTML, and JS all live in the same file. It's grep-friendly but not pretty, and the file weight is real. Splitting it would mean serving multiple files from `build_dashboard.py`'s static handler, which is doable but isn't the shipping default. If you fork to retheme, expect to scroll.

## Custom prompts

Drop new files into `skill/prompts/`. Reference them by name from `skill/SKILL.md` — there's no auto-discovery; the agent reads SKILL.md and follows pointers.

The convention is one file per workflow, named `<thing>-prompt.md`. A new prompt typically defines its trigger phrases, the steps to run, and the report format.

## Modifying the build script

`dashboard/build_dashboard.py` is plain Python with no external dependencies. The functions you'll most likely edit:

- `process_article` and `process_episode` — decide which fields make it into `ev-data.json`. Extend these to expose a new frontmatter field on every article/episode object.
- `build_timeline` — the timeline event generator. Add new event kinds here (e.g. an `expires` event from an `expiry_date` field).
- `compute_stats` — the header strip.

Mutation endpoints live in the `DashboardHandler` at the bottom of the file. Adding one is a new `do_POST` branch (or an entry in `BOARD_ROUTES` if it's board-related).

## What you can't easily change

The five primitives (Read, Write, Maintain, File, Execute) are baked into `SKILL.md` and the prompt files. Renaming them is a noticeable refactor.

The frontmatter fields the dashboard uses for special rendering — `tier`, `status`, `domains`, `last_verified`, `renewal_date`, `change_history` — are referenced by name in `build_dashboard.py` and the kanban column maps. Adding fields is free; renaming these means editing both the build script and the front-end.

For everything else, the vault is just markdown.
