#!/usr/bin/env python3
"""
build_dashboard.py — Build the Everything Vault Dashboard

Walks the vault, parses frontmatter from every .md file, extracts tasks and
timeline events, and emits ev-data.json. Optionally starts a local server
and opens the browser.

Usage:
    python3 build_dashboard.py --vault /path/to/vault
    python3 build_dashboard.py --vault /path/to/vault --no-serve
    python3 build_dashboard.py --stop
"""

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import webbrowser
from datetime import datetime, date
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread

PORT = 8077
PID_FILE = "/tmp/ev-dashboard-server.pid"
DEFAULT_DATA_FILENAME = "ev-data.json"

# ── Lightweight YAML frontmatter parser (no PyYAML dependency) ────────

def _parse_yaml_value(raw):
    """Parse a single YAML value from a string. Handles strings, numbers,
    booleans, nulls, lists, and simple inline lists."""
    raw = raw.strip()
    if not raw or raw.lower() in ('null', '~', ''):
        return None
    if raw.lower() == 'true':
        return True
    if raw.lower() == 'false':
        return False
    # Quoted string
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    # Inline list: [a, b, c]
    if raw.startswith('[') and raw.endswith(']'):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in inner.split(','):
            items.append(_parse_yaml_value(item.strip()))
        return items
    # Number
    try:
        if '.' in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        pass
    return raw


# Skip files inside any underscore-prefixed folder ("_for-deletion/", "_archive/" etc.)
# so soft-deleted content stays out of indexing, queries, and dashboard.
def _is_under_dot_or_underscore(path, vault_root):
    try:
        parts = path.relative_to(vault_root).parts
    except ValueError:
        return True  # outside vault
    return any(p.startswith("_") or p.startswith(".") for p in parts[:-1])

def parse_frontmatter(filepath, return_body=False):
    """Extract YAML frontmatter from a markdown file.

    Handles the subset of YAML used in EV articles: scalar key-value pairs,
    inline lists [a, b], block lists (- item), and simple nested objects
    (- ref: x / type: y). No PyYAML dependency needed.

    When return_body=True, returns (fm, body) so callers can parse sections
    like Change History without re-reading the file.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return (None, "") if return_body else None

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return (None, content) if return_body else None

    body = content[match.end():]

    fm = {}
    lines = match.group(1).split('\n')
    current_key = None
    current_list = None
    current_obj = None  # For nested objects in lists (e.g., relationships)

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        indent = len(line) - len(line.lstrip())

        # Block list item under a key
        if stripped.startswith('- ') and current_key is not None:
            item_text = stripped[2:].strip()

            # Check if it's a key: value pair (nested object start)
            kv_match = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', item_text)
            if kv_match:
                # Start of a new object in the list
                if current_obj is not None and current_list is not None:
                    current_list.append(current_obj)
                current_obj = {kv_match.group(1): _parse_yaml_value(kv_match.group(2))}
            else:
                # Simple list item
                if current_obj is not None and current_list is not None:
                    current_list.append(current_obj)
                    current_obj = None
                if current_list is None:
                    current_list = []
                current_list.append(_parse_yaml_value(item_text))
            continue

        # Continuation of nested object (indented key: value under a list item)
        if indent >= 4 and current_obj is not None:
            kv_match = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', stripped)
            if kv_match:
                current_obj[kv_match.group(1)] = _parse_yaml_value(kv_match.group(2))
                continue

        # Flush any pending list/object
        if current_key is not None and (current_list is not None or current_obj is not None):
            if current_obj is not None:
                if current_list is None:
                    current_list = []
                current_list.append(current_obj)
                current_obj = None
            fm[current_key] = current_list
            current_list = None
            current_key = None

        # Top-level key: value
        kv_match = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', stripped)
        if kv_match:
            key = kv_match.group(1)
            val_raw = kv_match.group(2).strip()

            if not val_raw:
                # Could be start of a block list or multi-line value
                current_key = key
                current_list = []
            else:
                fm[key] = _parse_yaml_value(val_raw)
                current_key = key  # In case block list follows
                current_list = None

    # Flush final pending list/object
    if current_key is not None and (current_list is not None or current_obj is not None):
        if current_obj is not None:
            if current_list is None:
                current_list = []
            current_list.append(current_obj)
        if current_list:
            fm[current_key] = current_list

    if return_body:
        return (fm if fm else None), body
    return fm if fm else None


# ── Change History parser ─────────────────────────────────────────────

_STATUS_TRANSITION_RE = re.compile(
    r"""
    ^\s*Status\s+
    ['\"]?(?P<from>[\w\-()]+)['\"]?\s*
    (?:→|->|&rarr;)\s*
    ['\"]?(?P<to>[\w\-]+)['\"]?
    \s*\.\s*
    (?P<reason>.*)$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def parse_change_history(body):
    """Parse the ## Change History table in an article body into rows."""
    if not body:
        return []

    m = re.search(r"(?im)^\#{1,6}\s*change\s+history\s*$", body)
    if not m:
        return []

    after = body[m.end():]
    next_heading = re.search(r"(?m)^\#", after)
    section = after[:next_heading.start()] if next_heading else after

    rows = []
    for line in section.splitlines():
        line = line.rstrip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        first = cells[0].lower()
        if first in ("date",) or all(re.fullmatch(r"[-:]+", c or "") for c in cells):
            continue

        date_cell = cells[0]
        change_cell = cells[1] if len(cells) > 1 else ""
        source_cell = cells[2] if len(cells) > 2 else ""
        confidence_cell = cells[3] if len(cells) > 3 else ""

        row = {
            "date": date_cell,
            "change": change_cell,
            "source": source_cell,
            "confidence": confidence_cell,
        }

        transition = _STATUS_TRANSITION_RE.match(change_cell)
        if transition:
            row["from_status"] = transition.group("from")
            row["to_status"] = transition.group("to")
            row["reason"] = transition.group("reason").strip()

        rows.append(row)

    return rows


# ── Task table parser ─────────────────────────────────────────────────

def parse_task_table(vault_path):
    """Parse the markdown table in tasks/todo-list.md into structured objects."""
    todo_file = vault_path / "tasks" / "todo-list.md"
    if not todo_file.exists():
        return []

    with open(todo_file, "r", encoding="utf-8") as f:
        content = f.read()

    tasks = []
    in_table = False

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            if in_table:
                break
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 6:
            continue

        if not in_table:
            if "ID" in cells[0] or "Task" in cells[1]:
                in_table = True
                continue
            continue

        if all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
            continue

        task_id = cells[0].strip() if len(cells) > 0 else ""
        task_text = cells[1].strip() if len(cells) > 1 else ""
        status_raw = cells[2].strip() if len(cells) > 2 else ""
        priority = cells[3].strip().lower() if len(cells) > 3 else ""
        urgency = cells[4].strip().lower() if len(cells) > 4 else ""
        due = cells[5].strip() if len(cells) > 5 else ""
        source = cells[6].strip() if len(cells) > 6 else ""
        notes = cells[7].strip() if len(cells) > 7 else ""

        if "done" in status_raw.lower() or "✅" in status_raw:
            status = "done"
        elif "cancelled" in status_raw.lower() or "❌" in status_raw:
            status = "cancelled"
        elif "removed" in status_raw.lower():
            status = "cancelled"
        else:
            status = "open"

        if task_text.startswith("~~") and task_text.endswith("~~"):
            task_text = task_text.strip("~")

        due_clean = ""
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", due)
        if date_match:
            due_clean = date_match.group(1)

        tasks.append({
            "id": task_id,
            "task": task_text,
            "status": status,
            "priority": priority,
            "urgency": urgency,
            "due": due_clean,
            "source": source,
            "notes": notes,
        })

    return tasks


# ── Day Board parser (slot model) ────────────────────────────────────

BOARD_NUM_SLOTS = 5
BOARD_FIELDS = ["recently_done", "next", "holding", "notes"]
_BOARD_FIELD_HEADINGS = {
    "recently done": "recently_done",
    "next": "next",
    "holding": "holding",
    "notes": "notes",
    "items": "items",
}
_BOARD_SLOT_RE = re.compile(
    r"^Slot\s+(\d+)\s*[:—-]\s*(.+)$",
    re.IGNORECASE,
)
_BOARD_REF_RE = re.compile(
    r"^(?:T(\d+)|([A-Za-z0-9][A-Za-z0-9-]*))(?:\s*\(([^)]+)\))?$"
)
_BOARD_TODOS_ITEM_RE = re.compile(
    r"^-\s*\[(?P<done>[ xX])\]\s*(?P<ref>T\d+)(?:\s*[—-]\s*(?P<note>.+))?$"
)


def _empty_slot(position):
    return {
        "position": position,
        "type": "empty",
        "ref": None,
        "recently_done": [],
        "next": "",
        "holding": "",
        "notes": "",
    }


def _todos_slot(position):
    return {
        "position": position,
        "type": "todos",
        "ref": "todays-todos",
        "items": [],
        "recently_done": [],
        "next": "",
        "holding": "",
        "notes": "",
    }


def parse_board(vault_path):
    """Parse vault/tasks/day-board.md into the slot-model `board` structure."""
    board_file = Path(vault_path) / "tasks" / "day-board.md"
    result = {
        "source_path": None,
        "last_parsed": datetime.now().isoformat(timespec="seconds"),
        "warnings": [],
        "slots": [_empty_slot(i + 1) for i in range(BOARD_NUM_SLOTS)],
    }

    if not board_file.exists():
        result["warnings"].append("file not found")
        return result

    result["source_path"] = "tasks/day-board.md"

    try:
        content = board_file.read_text(encoding="utf-8")
    except Exception as exc:
        result["warnings"].append(f"read failed: {exc}")
        return result

    fm_match = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    body = content[fm_match.end():] if fm_match else content

    current_slot = None
    current_field = None
    field_lines = []

    def commit_field(slot, field_key, lines):
        if slot is None or field_key is None:
            return
        while lines and not lines[-1].strip():
            lines.pop()
        if slot["type"] == "todos" and field_key == "items":
            for ln in lines:
                m = _BOARD_TODOS_ITEM_RE.match(ln.strip())
                if not m:
                    continue
                slot["items"].append({
                    "ref": m.group("ref"),
                    "done": m.group("done").lower() == "x",
                    "note": (m.group("note") or "").strip(),
                })
            return
        if field_key == "recently_done":
            for ln in lines:
                stripped = ln.strip()
                if stripped.startswith("- "):
                    slot["recently_done"].append(stripped[2:].strip())
                elif stripped:
                    slot["recently_done"].append(stripped)
            return
        if field_key in {"next", "holding", "notes"}:
            slot[field_key] = "\n".join(lines).strip()
            return

    for lineno, raw in enumerate(body.splitlines(), 1):
        line = raw.rstrip()

        if line.startswith("## "):
            commit_field(current_slot, current_field, field_lines)
            current_field = None
            field_lines = []

            heading = line[3:].strip()
            if heading.lower() == "parked":
                current_slot = None
                break
            slot_match = _BOARD_SLOT_RE.match(heading)
            if not slot_match:
                result["warnings"].append(
                    f"line {lineno}: unrecognised slot heading '{heading}'"
                )
                current_slot = None
                continue

            position = int(slot_match.group(1))
            payload = slot_match.group(2).strip()

            if position < 1 or position > BOARD_NUM_SLOTS:
                result["warnings"].append(
                    f"line {lineno}: slot position {position} out of range 1..{BOARD_NUM_SLOTS}"
                )
                current_slot = None
                continue

            current_slot = _interpret_slot_payload(
                position, payload, result["slots"], result["warnings"], lineno
            )
            continue

        if line.startswith("### "):
            commit_field(current_slot, current_field, field_lines)
            field_lines = []

            heading = line[4:].strip().lower()
            current_field = _BOARD_FIELD_HEADINGS.get(heading)
            if current_field is None and heading:
                result["warnings"].append(
                    f"line {lineno}: unknown field '{heading}' (skipped)"
                )
            continue

        if current_field is not None:
            field_lines.append(raw)

    commit_field(current_slot, current_field, field_lines)

    result["slots"].sort(key=lambda s: s["position"])
    return result


def _interpret_slot_payload(position, payload, slots, warnings, lineno):
    """Apply a slot's payload (the bit after 'Slot N:') and return the
    slot dict the parser should now write fields into."""
    slot_idx = position - 1
    plow = payload.lower().strip()

    if plow in {"empty", "(empty)"}:
        slots[slot_idx] = _empty_slot(position)
        return slots[slot_idx]

    if plow.startswith("today's todos") or plow == "todos":
        slots[slot_idx] = _todos_slot(position)
        return slots[slot_idx]

    m = _BOARD_REF_RE.match(payload.strip())
    if not m:
        warnings.append(
            f"line {lineno}: unparseable slot payload '{payload}'"
        )
        slots[slot_idx] = _empty_slot(position)
        return slots[slot_idx]

    if m.group(1):
        ref_type = "task"
        ref = f"T{m.group(1).zfill(3)}"
    else:
        ref = m.group(2)
        ref_type = (m.group(3) or "project").strip().lower()
        if ref_type not in {"project", "concept", "task"}:
            warnings.append(
                f"line {lineno}: unknown ref type '{ref_type}' (defaulting to project)"
            )
            ref_type = "project"

    slot = {
        "position": position,
        "type": ref_type,
        "ref": ref,
        "recently_done": [],
        "next": "",
        "holding": "",
        "notes": "",
    }
    slots[slot_idx] = slot
    return slot


# ── Article processing ────────────────────────────────────────────────

def process_article(filepath, vault_path):
    """Process a single .md file into an article dict."""
    fm, body = parse_frontmatter(filepath, return_body=True)
    if not fm:
        return None

    rel_path = str(filepath.relative_to(vault_path))
    sensitivity = fm.get("sensitivity", "normal")

    change_history = []
    if fm.get("tier") == "project" and sensitivity != "credential":
        change_history = parse_change_history(body)

    if sensitivity == "credential":
        return {
            "path": rel_path,
            "title": fm.get("title", filepath.stem),
            "domains": fm.get("domains", []),
            "type": fm.get("type", ""),
            "object_type": fm.get("object_type", "article"),
            "sensitivity": "credential",
            "confidence": None,
            "tier": None,
            "status": None,
            "development_platform": None,
            "tags": [],
            "related": [],
            "relationships": [],
            "entity_refs": [],
            "created": str(fm.get("created", "")),
            "last_updated": str(fm.get("last_updated", "")),
            "last_verified": str(fm.get("last_verified", "")),
            "renewal_date": None,
            "cost": None,
            "provider": None,
            "redacted": True,
        }

    return {
        "path": rel_path,
        "title": fm.get("title", filepath.stem),
        "domains": fm.get("domains", []) or [],
        "type": fm.get("type", ""),
        "object_type": fm.get("object_type", "article"),
        "sensitivity": sensitivity,
        "confidence": fm.get("confidence", ""),
        "tier": fm.get("tier"),
        "status": fm.get("status"),
        "development_platform": fm.get("development_platform"),
        "applies_to": fm.get("applies_to"),
        "tags": fm.get("tags", []) or [],
        "related": fm.get("related", []) or [],
        "relationships": fm.get("relationships", []) or [],
        "entity_refs": fm.get("entity_refs", []) or [],
        "created": str(fm.get("created", "")),
        "last_updated": str(fm.get("last_updated", "")),
        "last_verified": str(fm.get("last_verified", "")),
        "renewal_date": str(fm.get("renewal_date", "")) if fm.get("renewal_date") else None,
        "cost": fm.get("cost"),
        "provider": fm.get("provider"),
        "source_ref": fm.get("source_ref"),
        "code_path": fm.get("code_path"),
        "github": fm.get("github"),
        "change_history": change_history,
        "redacted": False,
    }


def process_source(filepath, vault_path):
    """Process a file in vault/sources/ as a Source-tier entry."""
    name = filepath.name
    if name.endswith(".meta.yaml"):
        return None
    if name == "_index.md":
        return None

    rel_path = str(filepath.relative_to(vault_path))
    sidecar = filepath.with_suffix(filepath.suffix + ".meta.yaml")
    if not sidecar.exists():
        sidecar = filepath.parent / (filepath.stem + ".meta.yaml")

    meta = {}
    if sidecar.exists():
        meta = parse_frontmatter(sidecar) or {}
        if not meta:
            meta = {}
            try:
                with open(sidecar, encoding="utf-8") as fh:
                    for line in fh:
                        if ":" in line and not line.lstrip().startswith("-"):
                            k, _, v = line.partition(":")
                            meta[k.strip()] = _parse_yaml_value(v.strip())
            except Exception:
                pass

    return {
        "path": rel_path,
        "filename": name,
        "title": meta.get("title", name),
        "date": str(meta.get("date", "")),
        "origin": meta.get("origin", ""),
        "linked_articles": meta.get("linked_articles", []) or [],
        "sensitivity": meta.get("sensitivity", "normal"),
        "size_bytes": filepath.stat().st_size,
        "has_sidecar": sidecar.exists(),
    }


def process_episode(filepath, vault_path):
    """Process an episode .md file."""
    fm = parse_frontmatter(filepath)
    if not fm:
        return None

    rel_path = str(filepath.relative_to(vault_path))

    return {
        "path": rel_path,
        "title": fm.get("title", filepath.stem),
        "date": str(fm.get("date", "")),
        "domains": fm.get("domains", []) or [],
        "actors": fm.get("actors", []) or [],
        "outcomes": fm.get("outcomes", []) or [],
        "follow_up": fm.get("follow_up"),
        "article_refs": fm.get("article_refs", []) or [],
        "tags": fm.get("tags", []) or [],
        "sensitivity": fm.get("sensitivity", "normal"),
    }


# ── Timeline builder ──────────────────────────────────────────────────

def build_timeline(articles, episodes, tasks):
    """Build timeline events from all date-bearing sources."""
    events = []

    for art in articles:
        if art.get("redacted"):
            continue
        domains = art.get("domains", [])
        domain = domains[0] if domains else "unknown"

        if art.get("created"):
            events.append({
                "date": art["created"],
                "title": art["title"],
                "event_type": "created",
                "domain": domain,
                "source_path": art["path"],
            })

        if art.get("last_updated") and art["last_updated"] != art.get("created"):
            events.append({
                "date": art["last_updated"],
                "title": f"Updated: {art['title']}",
                "event_type": "updated",
                "domain": domain,
                "source_path": art["path"],
            })

        if art.get("renewal_date"):
            events.append({
                "date": art["renewal_date"],
                "title": f"Renewal: {art['title']}",
                "event_type": "renewal",
                "domain": domain,
                "source_path": art["path"],
            })

    for ep in episodes:
        if ep.get("date"):
            domains = ep.get("domains", [])
            domain = [d for d in domains if d != "episodes"]
            domain = domain[0] if domain else "episodes"
            events.append({
                "date": ep["date"],
                "title": ep["title"],
                "event_type": "episode",
                "domain": domain,
                "source_path": ep["path"],
            })

        if ep.get("follow_up"):
            fu = ep["follow_up"]
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", fu)
            if date_match:
                events.append({
                    "date": date_match.group(1),
                    "title": f"Follow-up: {fu}",
                    "event_type": "follow_up",
                    "domain": domain,
                    "source_path": ep["path"],
                })

    for task in tasks:
        if task.get("due") and task["status"] == "open":
            events.append({
                "date": task["due"],
                "title": f"Due: {task['task']}",
                "event_type": "due",
                "domain": "tasks",
                "source_path": "tasks/todo-list.md",
                "source_id": task["id"],
            })

    events.sort(key=lambda e: e.get("date", ""), reverse=True)
    return events


# ── Stats computation ─────────────────────────────────────────────────

def compute_stats(articles, episodes, concepts, tasks):
    """Compute summary statistics."""
    today = date.today()
    six_months_ago = today.replace(month=today.month - 6) if today.month > 6 else today.replace(year=today.year - 1, month=today.month + 6)

    stale_count = 0
    for art in articles:
        lv = art.get("last_verified", "")
        if lv:
            try:
                verified_date = datetime.strptime(lv, "%Y-%m-%d").date()
                if verified_date < six_months_ago:
                    stale_count += 1
            except ValueError:
                pass

    open_tasks = [t for t in tasks if t["status"] == "open"]
    done_tasks = [t for t in tasks if t["status"] == "done"]
    cancelled_tasks = [t for t in tasks if t["status"] == "cancelled"]

    overdue = 0
    for t in open_tasks:
        if t.get("due"):
            try:
                due_date = datetime.strptime(t["due"], "%Y-%m-%d").date()
                if due_date < today:
                    overdue += 1
            except ValueError:
                pass

    concept_statuses = {}
    for c in concepts:
        s = c.get("status", "unknown")
        concept_statuses[s] = concept_statuses.get(s, 0) + 1

    return {
        "total_articles": len(articles),
        "total_episodes": len(episodes),
        "total_concepts": len(concepts),
        "total_tasks_open": len(open_tasks),
        "total_tasks_done": len(done_tasks),
        "total_tasks_cancelled": len(cancelled_tasks),
        "tasks_overdue": overdue,
        "stale_count": stale_count,
        "concept_statuses": concept_statuses,
    }


# ── Main build ────────────────────────────────────────────────────────

def build(vault_path, output_dir=None):
    """Walk the vault and build ev-data.json."""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"ERROR: Vault not found at {vault}")
        sys.exit(1)

    articles = []
    episodes = []
    concepts = []
    sources = []

    for md_file in sorted(vault.rglob("*.md")):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name == "_index.md":
            continue
        rel = md_file.relative_to(vault)
        if rel.parts and rel.parts[0] == "dashboard":
            continue
        if rel.parts and rel.parts[0] == "sources":
            continue

        rel = str(md_file.relative_to(vault))

        if rel.startswith("episodes/"):
            ep = process_episode(md_file, vault)
            if ep:
                episodes.append(ep)
            continue

        if md_file.name in ("todo-conventions.md",):
            continue

        art = process_article(md_file, vault)
        if art:
            articles.append(art)
            if "concepts" in (art.get("domains") or []):
                concepts.append(art)

    sources_dir = vault / "sources"
    if sources_dir.exists():
        for src_file in sorted(sources_dir.rglob("*")):
            if _is_under_dot_or_underscore(src_file, vault):
                continue
            if not src_file.is_file():
                continue
            src = process_source(src_file, vault)
            if src:
                sources.append(src)

    tasks = parse_task_table(vault)

    timeline = build_timeline(articles, episodes, tasks)

    status_transitions = []
    for art in articles:
        if art.get("tier") != "project":
            continue
        for row in (art.get("change_history") or []):
            if "to_status" not in row:
                continue
            status_transitions.append({
                "date": row.get("date", ""),
                "slug": Path(art["path"]).stem,
                "title": art.get("title", ""),
                "from_status": row.get("from_status"),
                "to_status": row.get("to_status"),
                "reason": row.get("reason", ""),
                "source": row.get("source", ""),
                "confidence": row.get("confidence", ""),
                "path": art["path"],
            })
    status_transitions.sort(key=lambda r: r.get("date", ""), reverse=True)

    board = parse_board(vault)

    board_updated = None
    board_file = Path(vault) / "tasks" / "day-board.md"
    if board_file.exists():
        bfm, _ = parse_frontmatter(board_file, return_body=True)
        if bfm:
            board_updated = str(bfm.get("last_updated", ""))
    article_by_slug = {Path(a["path"]).stem: a for a in articles}

    project_tasks = {}
    for t in tasks:
        if t.get("status") != "open":
            continue
        src = t.get("source", "") or ""
        for part in src.split(","):
            part = part.strip()
            slug_match = re.match(r"(?:projects|concepts)/([^/]+)\.md$", part)
            if slug_match:
                slug = slug_match.group(1)
                project_tasks.setdefault(slug, []).append(t)

    for slot in board.get("slots", []):
        slot["external_updates"] = []
        slot["linked_tasks"] = []
        if slot.get("type") in ("project", "concept") and slot.get("ref"):
            ref = slot["ref"]
            art = article_by_slug.get(ref)
            if art and board_updated:
                for ch in (art.get("change_history") or []):
                    if ch.get("date", "") > board_updated:
                        slot["external_updates"].append(ch)
            slot["linked_tasks"] = project_tasks.get(ref, [])

    stats = compute_stats(articles, episodes, concepts, tasks)
    stats["total_sources"] = len(sources)
    stats["sources_with_sidecars"] = sum(1 for s in sources if s.get("has_sidecar"))

    output = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "vault_path": str(vault),
        "stats": stats,
        "articles": articles,
        "episodes": episodes,
        "concepts": concepts,
        "sources": sources,
        "tasks": tasks,
        "timeline_events": timeline,
        "status_transitions": status_transitions,
        "board": board,
    }

    # Decide where to write the JSON. By default, alongside the dashboard.html
    # in the dashboard's own directory (so the static server can serve it).
    if output_dir is None:
        # Co-locate output with this script (dashboard/ folder)
        out_dir = Path(__file__).resolve().parent
    else:
        out_dir = Path(output_dir)
        out_dir.mkdir(exist_ok=True, parents=True)

    json_path = out_dir / DEFAULT_DATA_FILENAME

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    filled = sum(1 for s in board["slots"] if s["type"] != "empty")
    warn_suffix = ""
    if board["warnings"]:
        warn_suffix = (
            f" (board warnings: {len(board['warnings'])} — "
            f"see {DEFAULT_DATA_FILENAME} .board.warnings)"
        )
    print(f"Built dashboard: {stats['total_articles']} articles, "
          f"{stats['total_episodes']} episodes, {stats['total_concepts']} concepts, "
          f"{stats['total_tasks_open']} open tasks, "
          f"{filled}/{len(board['slots'])} day-board slots filled. "
          f"→ {json_path}{warn_suffix}")

    return str(out_dir)


# ── Server ────────────────────────────────────────────────────────────

class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler with /rebuild and /board/* endpoints."""

    vault_path = None
    board_tool = None  # Path to skill/tools/board.py

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON body: {exc}") from exc

    def _run_board(self, args):
        """Shell out to board.py with the given argv after --vault."""
        if not self.board_tool or not self.vault_path:
            return False, "no board tool / vault configured"
        cmd = [
            sys.executable, str(self.board_tool),
            "--vault", str(self.vault_path),
            "--json",
            *args,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            return False, proc.stderr.strip() or proc.stdout.strip()
        try:
            return True, json.loads(proc.stdout)
        except json.JSONDecodeError:
            return True, {"raw": proc.stdout.strip()}

    # ── Tailscale Funnel (optional) ───────────────────────────────
    TAILSCALE_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"

    def _funnel_status(self):
        """Check if Tailscale Funnel is currently active. Returns active=False
        if Tailscale isn't installed (which is the common case)."""
        try:
            result = subprocess.run(
                [self.TAILSCALE_CLI, "funnel", "status"],
                capture_output=True, text=True, timeout=5,
            )
            output = result.stdout.strip()
            if "No serve config" in output or not output:
                return {"active": False, "url": None}
            url = None
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("https://"):
                    url = line.split()[0].rstrip("/")
                    break
            return {"active": True, "url": url, "detail": output}
        except FileNotFoundError:
            return {"active": False, "url": None, "available": False}
        except Exception as e:
            return {"active": False, "url": None, "error": str(e)}

    def _funnel_toggle(self, enable):
        """Enable or disable Tailscale Funnel on the dashboard port."""
        try:
            if enable:
                cmd = [self.TAILSCALE_CLI, "funnel", "--bg", "--yes", str(PORT)]
                subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                return True, self._funnel_status()
            else:
                subprocess.run(
                    [self.TAILSCALE_CLI, "funnel", "reset"],
                    capture_output=True, text=True, timeout=5,
                )
                return True, {"active": False, "url": None}
        except Exception as e:
            return False, {"error": str(e)}

    def do_GET(self):
        if self.path == "/rebuild":
            if self.vault_path:
                build(self.vault_path, output_dir=str(Path(__file__).resolve().parent))
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(500, {"error": "no vault path"})
            return
        if self.path == "/funnel/status":
            self._send_json(200, self._funnel_status())
            return
        if self.path == "/board":
            ok, payload = self._run_board(["read"])
            if not ok:
                self._send_json(500, {"error": payload})
            else:
                self._send_json(200, payload)
            return
        from urllib.parse import urlparse
        if urlparse(self.path).path == "/article":
            self._serve_article()
            return
        if self.path in ("/", ""):
            self.path = "/dashboard.html"
        return super().do_GET()

    def _serve_article(self):
        """GET /article?path=projects/foo.md — return raw markdown content."""
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        rel_path = params.get("path", [None])[0]
        if not rel_path or not self.vault_path:
            self._send_json(400, {"error": "missing path param or vault not set"})
            return
        if ".." in rel_path:
            self._send_json(400, {"error": "invalid path"})
            return
        full = Path(self.vault_path) / rel_path
        if not full.exists():
            self._send_json(404, {"error": f"not found: {rel_path}"})
            return
        content = full.read_text(encoding="utf-8")
        self._send_json(200, {"path": rel_path, "content": content})

    def _save_article(self, body):
        """POST /article/save — write content back to vault file."""
        rel_path = body.get("path")
        content = body.get("content")
        if not rel_path or content is None or not self.vault_path:
            return False, "missing path or content"
        if ".." in rel_path:
            return False, "invalid path"
        full = Path(self.vault_path) / rel_path
        if not full.exists():
            return False, f"not found: {rel_path}"
        full.write_text(content, encoding="utf-8")
        return True, "saved"

    # ── Concept promotion endpoint ──────────────────────────────────

    _COLUMN_TO_FRONTMATTER = {
        "insight":            ("insight",  "ideas"),
        "developing-concept": ("concept",  "ideas"),
        "idea":               ("idea",     "ideas"),
        "candidate-project":  ("idea",     "under-development"),
        "active-project":     ("project",  "under-development"),
        "parked":             (None,       "delivered-and-parked"),
    }

    def _move_concept(self, body):
        """POST /concept/move — change a concept's kanban column."""
        rel_path = body.get("path")
        target_col = body.get("column")
        if not rel_path or not target_col or not self.vault_path:
            return False, "missing path, column, or vault"
        if ".." in rel_path:
            return False, "invalid path"
        mapping = self._COLUMN_TO_FRONTMATTER.get(target_col)
        if not mapping:
            return False, f"unknown column: {target_col}"
        new_tier, new_status = mapping

        full = Path(self.vault_path) / rel_path
        if not full.exists():
            return False, f"not found: {rel_path}"

        content = full.read_text(encoding="utf-8")

        fm_match = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", content, re.DOTALL)
        if not fm_match:
            return False, "no frontmatter found"

        fm_text = fm_match.group(2)
        before = fm_match.group(1)
        sep = fm_match.group(3)
        body_text = content[fm_match.end():]

        if new_tier is not None:
            if re.search(r"^tier\s*:", fm_text, re.MULTILINE):
                fm_text = re.sub(r"^(tier\s*:\s*).*$", rf"\g<1>{new_tier}", fm_text, flags=re.MULTILINE)
            else:
                fm_text += f"\ntier: {new_tier}"

        if re.search(r"^status\s*:", fm_text, re.MULTILINE):
            fm_text = re.sub(r"^(status\s*:\s*).*$", rf"\g<1>{new_status}", fm_text, flags=re.MULTILINE)
        else:
            fm_text += f"\nstatus: {new_status}"

        today = date.today().isoformat()
        if re.search(r"^last_updated\s*:", fm_text, re.MULTILINE):
            fm_text = re.sub(r"^(last_updated\s*:\s*).*$", rf"\g<1>{today}", fm_text, flags=re.MULTILINE)

        full.write_text(before + fm_text + sep + body_text, encoding="utf-8")
        return True, f"moved to {target_col}"

    # ── Project move endpoint ──────────────────────────────────────

    _PROJECT_COLUMN_TO_STATUS = {
        "ideas":                       "ideas",
        "prototype":                   "prototype",
        "under-development":           "under-development",
        "delivered-and-operational":    "delivered-and-operational",
        "delivered-and-parked":         "delivered-and-parked",
    }

    def _move_project(self, body):
        """POST /project/move — change a project's status column."""
        rel_path = body.get("path")
        target_col = body.get("column")
        if not rel_path or not target_col or not self.vault_path:
            return False, "missing path, column, or vault"
        if ".." in rel_path:
            return False, "invalid path"
        new_status = self._PROJECT_COLUMN_TO_STATUS.get(target_col)
        if not new_status:
            return False, f"unknown column: {target_col}"

        full = Path(self.vault_path) / rel_path
        if not full.exists():
            return False, f"not found: {rel_path}"

        content = full.read_text(encoding="utf-8")

        fm_match = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", content, re.DOTALL)
        if not fm_match:
            return False, "no frontmatter found"

        fm_text = fm_match.group(2)
        before = fm_match.group(1)
        sep = fm_match.group(3)
        body_text = content[fm_match.end():]

        if re.search(r"^status\s*:", fm_text, re.MULTILINE):
            fm_text = re.sub(r"^(status\s*:\s*).*$", rf"\g<1>{new_status}", fm_text, flags=re.MULTILINE)
        else:
            fm_text += f"\nstatus: {new_status}"

        today = date.today().isoformat()
        if re.search(r"^last_updated\s*:", fm_text, re.MULTILINE):
            fm_text = re.sub(r"^(last_updated\s*:\s*).*$", rf"\g<1>{today}", fm_text, flags=re.MULTILINE)

        full.write_text(before + fm_text + sep + body_text, encoding="utf-8")
        return True, f"moved to {target_col}"

    # ── Domain-toggle endpoint ──────────────────────────────────────

    def _toggle_domain(self, body):
        """POST /article/toggle-domain — add or remove a domain from an
        article's `domains:` list. Membership tagging only — no file move."""
        rel_path = body.get("path")
        domain = body.get("domain")
        action = body.get("action")
        if not rel_path or not domain or not action or not self.vault_path:
            return False, "missing path, domain, action, or vault"
        if ".." in rel_path:
            return False, "invalid path"
        if domain not in ("concepts", "projects"):
            return False, f"unknown domain: {domain}"
        if action not in ("add", "remove"):
            return False, f"unknown action: {action}"

        full = Path(self.vault_path) / rel_path
        if not full.exists():
            return False, f"not found: {rel_path}"

        content = full.read_text(encoding="utf-8")

        fm_match = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", content, re.DOTALL)
        if not fm_match:
            return False, "no frontmatter found"

        fm_text = fm_match.group(2)
        before = fm_match.group(1)
        sep = fm_match.group(3)
        body_text = content[fm_match.end():]

        # Parse the existing domains list (handle both inline and block YAML).
        current = []
        inline_match = re.search(r"^domains\s*:\s*\[(.*?)\]\s*$", fm_text, re.MULTILINE)
        block_start = None
        block_end = None
        if inline_match:
            raw = inline_match.group(1).strip()
            if raw:
                current = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
        else:
            # Block form: `domains:` followed by `  - foo` lines.
            lines = fm_text.split("\n")
            for i, line in enumerate(lines):
                if re.match(r"^domains\s*:\s*$", line):
                    block_start = i
                    j = i + 1
                    while j < len(lines) and re.match(r"^\s*-\s*", lines[j]):
                        item = re.sub(r"^\s*-\s*", "", lines[j]).strip().strip("'\"")
                        if item:
                            current.append(item)
                        j += 1
                    block_end = j
                    break

        # Mutate.
        new_list = list(current)
        if action == "add":
            if domain not in new_list:
                new_list.append(domain)
        else:  # remove
            if domain in new_list:
                if len(new_list) <= 1:
                    return False, "at least one domain required"
                new_list = [d for d in new_list if d != domain]

        # Rewrite using inline form for simplicity.
        new_line = f"domains: [{', '.join(new_list)}]"
        if inline_match:
            fm_text = (
                fm_text[: inline_match.start()]
                + new_line
                + fm_text[inline_match.end():]
            )
        elif block_start is not None:
            lines = fm_text.split("\n")
            new_lines = lines[:block_start] + [new_line] + lines[block_end:]
            fm_text = "\n".join(new_lines)
        else:
            # No domains field at all — append one.
            fm_text = fm_text.rstrip() + "\n" + new_line

        today = date.today().isoformat()
        if re.search(r"^last_updated\s*:", fm_text, re.MULTILINE):
            fm_text = re.sub(r"^(last_updated\s*:\s*).*$", rf"\g<1>{today}", fm_text, flags=re.MULTILINE)
        else:
            fm_text = fm_text.rstrip() + f"\nlast_updated: {today}"

        full.write_text(before + fm_text + sep + body_text, encoding="utf-8")
        return True, f"domains now [{', '.join(new_list)}]"

    # ── Task field-edit endpoint ────────────────────────────────────

    def _update_task(self, body):
        """POST /task/update — edit priority or due date on a task row."""
        task_id = (body.get("id") or "").strip()
        field = (body.get("field") or "").strip()
        value = (body.get("value") or "").strip()
        if not task_id or not field:
            return False, "missing id or field"
        if field not in ("priority", "urgency", "due"):
            return False, f"unsupported field: {field}"

        col_index = {"priority": 3, "urgency": 4, "due": 5}[field]

        todo_path = Path(self.vault_path) / "tasks" / "todo-list.md"
        if not todo_path.exists():
            return False, "todo-list.md not found"

        lines = todo_path.read_text(encoding="utf-8").split("\n")
        found = False
        for i, line in enumerate(lines):
            if not line.startswith("|"):
                continue
            cells = line.split("|")
            if len(cells) < 8:
                continue
            if cells[1].strip() == task_id:
                cells[col_index + 1] = f" {value} "
                lines[i] = "|".join(cells)
                found = True
                break

        if not found:
            return False, f"task {task_id} not found in table"

        todo_path.write_text("\n".join(lines), encoding="utf-8")
        return True, f"{task_id} {field} → {value}"

    # ── Board mutation endpoints ─────────────────────────────────────

    def _flush_slot_to_article(self, body):
        """Flush a day-board slot's recently_done and next into the project article."""
        from datetime import date as _date
        position = int(body["position"])

        board_tool = self.board_tool
        vault_path = self.vault_path
        if not board_tool or not vault_path:
            return False, "no board tool or vault"

        import importlib.util
        spec = importlib.util.spec_from_file_location("board", str(board_tool))
        bmod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bmod)
        bp = bmod.board_path(Path(vault_path))
        parsed = bmod.parse(bp)
        slot = bmod._slot_at(parsed, position)

        if slot["type"] not in ("project", "concept"):
            return False, f"slot {position} is {slot['type']}, not a project/concept"

        ref = slot.get("ref")
        if not ref:
            return False, "slot has no ref"

        article_path = None
        for subdir in ("projects", "concepts"):
            candidate = Path(vault_path) / subdir / f"{ref}.md"
            if candidate.exists():
                article_path = candidate
                break
        if not article_path:
            return False, f"article not found for {ref}"

        content = article_path.read_text(encoding="utf-8")
        today = _date.today().isoformat()
        changed = False

        recently_done = slot.get("recently_done", [])
        if recently_done:
            log_entry = f"\n### {today}\n\n"
            for item in recently_done:
                log_entry += f"- {item}\n"

            if "## Progress Log" in content:
                idx = content.index("## Progress Log")
                end_of_heading = content.index("\n", idx) + 1
                content = content[:end_of_heading] + log_entry + content[end_of_heading:]
            else:
                if "## Change History" in content:
                    idx = content.index("## Change History")
                    content = content[:idx] + "## Progress Log\n" + log_entry + "\n" + content[idx:]
                else:
                    content = content.rstrip() + "\n\n## Progress Log\n" + log_entry
            changed = True

        next_text = (slot.get("next") or "").strip()
        if next_text:
            new_section = f"## Next Actions\n\n{next_text}\n"
            if "## Next Actions" in content:
                start = content.index("## Next Actions")
                rest = content[start + len("## Next Actions"):]
                next_heading = re.search(r"\n## ", rest)
                if next_heading:
                    end = start + len("## Next Actions") + next_heading.start()
                    content = content[:start] + new_section + "\n" + content[end + 1:]
                else:
                    content = content[:start] + new_section
            else:
                inserted = False
                for marker in ("## Progress Log", "## Change History"):
                    if marker in content:
                        idx = content.index(marker)
                        content = content[:idx] + new_section + "\n" + content[idx:]
                        inserted = True
                        break
                if not inserted:
                    content = content.rstrip() + "\n\n" + new_section
            changed = True

        if changed:
            content = re.sub(
                r"^(last_updated:\s*)[^\n]*", rf"\g<1>{today}",
                content, count=1, flags=re.MULTILINE,
            )
            article_path.write_text(content, encoding="utf-8")

        if recently_done:
            bmod.op_set_field(parsed, position, "recently_done", "")
            bmod.save(bp, parsed)

        return True, f"flushed to {ref}: {len(recently_done)} progress items, next={'yes' if next_text else 'no'}"

    def _link_task_to_project(self, body):
        """Add a project article path to a task's source column in todo-list.md."""
        task_id = body.get("task_id", "").strip()
        slug = body.get("project_slug", "").strip()
        if not task_id or not slug:
            return False, "missing task_id or project_slug"
        vault = self.vault_path
        if not vault:
            return False, "no vault"

        article_path = None
        for subdir in ("projects", "concepts"):
            if (Path(vault) / subdir / f"{slug}.md").exists():
                article_path = f"{subdir}/{slug}.md"
                break
        if not article_path:
            return False, f"article not found for {slug}"

        todo_file = Path(vault) / "tasks" / "todo-list.md"
        if not todo_file.exists():
            return False, "todo-list.md not found"

        text = todo_file.read_text(encoding="utf-8")
        pattern = re.compile(
            r"^(\|\s*" + re.escape(task_id) + r"\s*\|"
            r"[^|]*\|"
            r"[^|]*\|"
            r"[^|]*\|"
            r"[^|]*\|"
            r"[^|]*\|"
            r"\s*)([^|]*?)(\s*\|)",
            re.MULTILINE,
        )
        m = pattern.search(text)
        if not m:
            return False, f"{task_id} not found"

        current_source = m.group(2).strip()
        if article_path in current_source:
            return True, f"{task_id} already linked to {slug}"

        if current_source and current_source != "—" and current_source != "-":
            new_source = f"{current_source}, {article_path}"
        else:
            new_source = article_path

        text = text[:m.start(2)] + f" {new_source} " + text[m.end(2):]
        todo_file.write_text(text, encoding="utf-8")
        return True, f"linked {task_id} → {slug}"

    def _unlink_task_from_project(self, body):
        """Remove a project article path from a task's source column."""
        task_id = body.get("task_id", "").strip()
        slug = body.get("project_slug", "").strip()
        if not task_id or not slug:
            return False, "missing task_id or project_slug"
        vault = self.vault_path
        if not vault:
            return False, "no vault"

        todo_file = Path(vault) / "tasks" / "todo-list.md"
        if not todo_file.exists():
            return False, "todo-list.md not found"

        text = todo_file.read_text(encoding="utf-8")
        pattern = re.compile(
            r"^(\|\s*" + re.escape(task_id) + r"\s*\|"
            r"[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*)([^|]*?)(\s*\|)",
            re.MULTILINE,
        )
        m = pattern.search(text)
        if not m:
            return False, f"{task_id} not found"

        current_source = m.group(2).strip()
        parts = [p.strip() for p in current_source.split(",")]
        parts = [p for p in parts if slug not in p]
        new_source = ", ".join(parts) if parts else "—"

        text = text[:m.start(2)] + f" {new_source} " + text[m.end(2):]
        todo_file.write_text(text, encoding="utf-8")
        return True, f"unlinked {task_id} from {slug}"

    BOARD_ROUTES = {
        "/board/assign":       lambda b: ["assign", str(b["position"]), b["ref"]] + (["--type", b["type"]] if b.get("type") else []),
        "/board/assign-todos": lambda b: ["assign-todos", str(b["position"])],
        "/board/dismiss":      lambda b: ["dismiss", str(b["position"])],
        "/board/done":         lambda b: ["done", str(b["position"])],
        "/board/set-field":    lambda b: ["set-field", str(b["position"]), b["field"], b["value"]],
        "/board/add-recent":   lambda b: ["add-recent", str(b["position"]), b["line"]],
        "/board/todos-add":    lambda b: ["todos", "add", str(b["position"]), b["ref"]] + (["--note", b["note"]] if b.get("note") else []),
        "/board/todos-remove": lambda b: ["todos", "remove", str(b["position"]), b["ref"]],
        "/board/todos-toggle": lambda b: ["todos", "toggle", str(b["position"]), b["ref"]],
        "/tasks/done":         lambda b: ["tasks-done", b["ref"]],
    }

    def do_POST(self):
        if self.path == "/funnel/toggle":
            try:
                body = self._read_json_body()
                enable = body.get("enable", False)
                ok, result = self._funnel_toggle(enable)
                if ok:
                    self._send_json(200, result)
                else:
                    self._send_json(500, result)
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path == "/article/save":
            try:
                body = self._read_json_body()
                ok, msg = self._save_article(body)
                if ok:
                    self._send_json(200, {"status": "ok", "message": msg})
                else:
                    self._send_json(400, {"error": msg})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path == "/task/update":
            try:
                body = self._read_json_body()
                ok, msg = self._update_task(body)
                if ok:
                    if self.vault_path:
                        build(self.vault_path, output_dir=str(Path(__file__).resolve().parent))
                    self._send_json(200, {"status": "ok", "message": msg})
                else:
                    self._send_json(400, {"error": msg})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path == "/concept/move":
            try:
                body = self._read_json_body()
                ok, msg = self._move_concept(body)
                if ok:
                    if self.vault_path:
                        build(self.vault_path, output_dir=str(Path(__file__).resolve().parent))
                    self._send_json(200, {"status": "ok", "message": msg})
                else:
                    self._send_json(400, {"error": msg})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path == "/project/move":
            try:
                body = self._read_json_body()
                ok, msg = self._move_project(body)
                if ok:
                    if self.vault_path:
                        build(self.vault_path, output_dir=str(Path(__file__).resolve().parent))
                    self._send_json(200, {"status": "ok", "message": msg})
                else:
                    self._send_json(400, {"error": msg})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path == "/article/toggle-domain":
            try:
                body = self._read_json_body()
                ok, msg = self._toggle_domain(body)
                if ok:
                    if self.vault_path:
                        build(self.vault_path, output_dir=str(Path(__file__).resolve().parent))
                    self._send_json(200, {"status": "ok", "message": msg})
                else:
                    self._send_json(400, {"error": msg})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path == "/board/flush-to-article":
            try:
                body = self._read_json_body()
                ok, msg = self._flush_slot_to_article(body)
                if ok:
                    if self.vault_path:
                        build(self.vault_path, output_dir=str(Path(__file__).resolve().parent))
                    self._send_json(200, {"status": "ok", "message": msg})
                else:
                    self._send_json(400, {"error": msg})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path in ("/task/link", "/task/unlink"):
            try:
                body = self._read_json_body()
                if self.path == "/task/link":
                    ok, msg = self._link_task_to_project(body)
                else:
                    ok, msg = self._unlink_task_from_project(body)
                if ok:
                    if self.vault_path:
                        build(self.vault_path, output_dir=str(Path(__file__).resolve().parent))
                    self._send_json(200, {"status": "ok", "message": msg})
                else:
                    self._send_json(400, {"error": msg})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        builder = self.BOARD_ROUTES.get(self.path)
        if builder is None:
            self._send_json(404, {"error": f"unknown path {self.path}"})
            return
        try:
            body = self._read_json_body()
            argv = builder(body)
        except (KeyError, ValueError) as exc:
            self._send_json(400, {"error": str(exc)})
            return

        ok, payload = self._run_board(argv)
        if not ok:
            self._send_json(400, {"error": payload})
            return

        if self.vault_path:
            try:
                build(self.vault_path, output_dir=str(Path(__file__).resolve().parent))
            except Exception as exc:
                self._send_json(500, {"error": f"rebuild failed: {exc}",
                                      "result": payload})
                return
        self._send_json(200, {"status": "ok", "result": payload})

    def log_message(self, format, *args):
        pass


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def find_board_tool():
    """Locate the skill's board.py. The dashboard server shells out to this
    to mutate the day-board file. The default layout is:

        everything-vault/
        ├── dashboard/
        │   └── build_dashboard.py    ← this file
        └── skill/
            └── tools/
                └── board.py

    Falls back to None if not found."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "skill" / "tools" / "board.py",
        here / "tools" / "board.py",
        # Legacy layout under a vault-bundled skills-catalog
        here.parent / "skills-catalog" / "everything-vault" / "tools" / "board.py",
    ]
    # Also probe EV_SKILL_PATH if set
    env_skill = os.environ.get("EV_SKILL_PATH")
    if env_skill:
        candidates.insert(0, Path(env_skill).expanduser() / "tools" / "board.py")

    for c in candidates:
        if c.exists():
            return c
    return None


def start_server(dashboard_dir, vault_path):
    """Start HTTP server in background."""
    if is_port_in_use(PORT):
        print(f"Server already running on port {PORT}")
        return

    DashboardHandler.vault_path = vault_path
    DashboardHandler.board_tool = find_board_tool()
    if DashboardHandler.board_tool is None:
        print("WARN: board.py not found — /board/* endpoints will fail")

    os.chdir(dashboard_dir)
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    print(f"Serving dashboard at http://localhost:{PORT}")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def stop_server():
    """Stop any running dashboard server."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            os.remove(PID_FILE)
            print(f"Stopped server (PID {pid})")
        except (ProcessLookupError, ValueError):
            os.remove(PID_FILE)
            print("Cleaned up stale PID file")
    else:
        print("No running server found")


def auto_detect_vault():
    """Try common locations for the vault directory."""
    home = Path.home()
    candidates = [
        home / "Documents" / "everything-vault" / "vault",
        home / "everything-vault" / "vault",
        Path(__file__).resolve().parent.parent / "example-vault",
        Path(__file__).resolve().parent.parent / "vault",
    ]
    env = os.environ.get("EV_VAULT_PATH")
    if env:
        candidates.insert(0, Path(env).expanduser())
    for c in candidates:
        if c.exists() and c.is_dir():
            return str(c)
    return None


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build and serve the Everything Vault Dashboard")
    parser.add_argument("--vault", type=str, help="Path to vault directory")
    parser.add_argument("--no-serve", action="store_true", help="Build only, don't start server")
    parser.add_argument("--stop", action="store_true", help="Stop running dashboard server")
    parser.add_argument("--port", type=int, default=PORT, help=f"Server port (default: {PORT})")
    args = parser.parse_args()

    port = args.port

    if args.stop:
        stop_server()
        return

    if not args.vault:
        args.vault = auto_detect_vault()
        if not args.vault:
            print("ERROR: --vault required (could not auto-detect)")
            print("Set EV_VAULT_PATH or pass --vault /path/to/vault")
            sys.exit(1)

    dashboard_dir = build(args.vault, output_dir=str(Path(__file__).resolve().parent))

    if not args.no_serve:
        start_server(dashboard_dir, args.vault)
        url = f"http://localhost:{port}"
        webbrowser.open(url)
        print(f"Dashboard open at {url}")
        print("Press Ctrl+C to stop")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping server...")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)


if __name__ == "__main__":
    main()
