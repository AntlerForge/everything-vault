# Dashboard Guide

The dashboard is a single-file HTML/JS app (`dashboard/dashboard.html`) served by `build_dashboard.py`. The build script walks your vault, parses YAML frontmatter from every markdown file, and writes a snapshot to `ev-data.json`. A small HTTP server then serves both the HTML and the JSON, plus a handful of mutation endpoints that let the dashboard write changes back.

Launch it with `./dashboard/ev-dash` (see [skill-guide.md](skill-guide.md) for the per-platform notes). Default URL is `http://localhost:8077`.

## Views

The header has six tabs. Switching is instant — everything is in `ev-data.json` already.

**Vault.** A collapsible tree of every article, grouped by domain. Click a leaf to open the article viewer/editor modal.

**Concepts.** A kanban over the `concepts/` domain with columns for `insight`, `developing-concept`, `idea`, `candidate-project`, `active-project`, and `parked`. Drag a card between columns to update its `tier` and `status` frontmatter.

**Projects.** A kanban over `tier: project` articles, one column per lifecycle status (`ideas`, `prototype`, `under-development`, `delivered-and-operational`, `delivered-and-parked`). Drag-and-drop updates `status` and `last_updated`.

**Day.** The five-slot focus board from `vault/tasks/day-board.md`. Each slot is a task, project, concept, the today's-todos list, or empty. Edit `next`, `holding`, `notes`, and `recently_done` inline; mark done; dismiss; or flush a project slot's progress back into the article.

**Tasks.** A filterable table over `vault/tasks/todo-list.md`. Edit priority, urgency, and due date inline. Link tasks to projects via the link-task modal.

**Timeline.** A reverse-chronological feed of created/updated events, episodes, follow-ups, renewals, and due dates. Filter by domain. A `TODAY` marker separates past from future.

A collapsible **Stats** strip in the header shows totals (articles, episodes, concepts, open tasks, overdue, stale).

## Mutation endpoints

The server exposes a handful of write endpoints used by the front-end:

- `POST /concept/move` and `POST /project/move` — kanban drag-and-drop. Rewrites `tier` / `status` / `last_updated` in the article frontmatter.
- `POST /task/update` — inline edits to priority, urgency, and due date.
- `POST /board/*` — every day-board operation (`assign`, `done`, `dismiss`, `set-field`, `add-recent`, `todos-add`, `todos-remove`, `todos-toggle`, `flush-to-article`). The server shells out to `skill/tools/board.py` for the actual write.
- `POST /article/save` — write back from the article-editor modal.
- `POST /task/link`, `/task/unlink` — link tasks to project articles.

After every successful mutation the server rebuilds `ev-data.json`, so reloading (or the **↻ Refresh** button) shows the new state.

## Mobile

Responsive but optimised for desktop. On phones the day-board collapses to a single column, kanban columns scroll horizontally, and the stats strip wraps. Fine for glancing at the board on the move; not where you'd do heavy editing.

## Tailscale Funnel (optional)

If you have [Tailscale](https://tailscale.com) installed and a tailnet, the **Funnel** button in the header exposes the dashboard at `https://<machine>.tail<id>.ts.net` so you can hit it from anywhere. The button calls `/funnel/toggle`, which shells out to `tailscale funnel`.

If Tailscale isn't installed, the button hides itself. Funnel exposes the dashboard publicly over the internet via your Tailscale identity — only enable it if you understand that. Auth is whatever Tailscale gives you; the dashboard itself has no login.

## Theme

Red/green colour-blind safe by default. CSS variables live at the top of `dashboard.html`:

```css
--bg, --surface, --surface2, --border, --text, --text-dim,
--accent, --green, --amber, --red, --purple, --teal
```

Edit those to retheme — they cascade through badges, kanban tier strips, and timeline markers. See [customisation.md](customisation.md) for the honest take on editing the single-file dashboard.

## Keyboard shortcuts

The only shortcuts in the source are zoom: `Alt+=` / `Alt++` to zoom in, `Alt+-` to zoom out, `Alt+0` to reset. Persisted in `localStorage`. There are no keyboard shortcuts for tab switching, kanban moves, or task edits — those are mouse/touch only.
