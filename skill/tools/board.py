#!/usr/bin/env python3
"""
board.py — manage the EV Day Board file (vault/tasks/day-board.md).

The Day Board has five **focus slots**, each one a self-contained
workspace for a single thread the user is interleaving through the day.
Each slot is one of:

  - empty
  - a task        (T-number from tasks/todo-list.md)
  - a project     (tier=project article, by filename stem)
  - a concept     (tier=concept/idea article)
  - todays-todos  (special — a curated checklist of T-numbers)

Each non-todos slot carries four free-text fields:
  recently_done · next · holding · notes

The todos slot carries an items list of `{ref, done, note}` entries.

This module is the canonical writer for the file. The dashboard server
endpoints and the EV skill both call it so all edits go through one
parse/render path.

CLI:

    python3 board.py --vault <path> read [--json]
    python3 board.py --vault <path> assign <position> <ref> [--type project|task|concept]
    python3 board.py --vault <path> assign-todos <position>
    python3 board.py --vault <path> dismiss <position>
    python3 board.py --vault <path> done <position>
    python3 board.py --vault <path> set-field <position> <field> <value>
    python3 board.py --vault <path> add-recent <position> <line>
    python3 board.py --vault <path> todos add <position> <Tnnn> [--note ...]
    python3 board.py --vault <path> todos remove <position> <Tnnn>
    python3 board.py --vault <path> todos toggle <position> <Tnnn>
    python3 board.py --vault <path> init

Positions are 1..5. Field is one of: recently_done, next, holding, notes.
recently_done accepts one bullet line per call via add-recent or a
newline-separated body via set-field.

Exit codes: 0 ok · 1 vault unreachable · 2 invalid input
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────

NUM_SLOTS = 5
FIELDS = ("recently_done", "next", "holding", "notes")
FIELD_HEADINGS = {
    "recently_done": "Recently done",
    "next": "Next",
    "holding": "Holding",
    "notes": "Notes",
    "items": "Items",
}
SLOT_RE = re.compile(r"^Slot\s+(\d+)\s*[:\u2014-]\s*(.+)$", re.IGNORECASE)
REF_RE = re.compile(
    r"^(?:T(\d+)|([A-Za-z0-9][A-Za-z0-9-]*))(?:\s*\(([^)]+)\))?$"
)
TODOS_ITEM_RE = re.compile(
    r"^-\s*\[(?P<done>[ xX])\]\s*(?P<ref>T\d+)(?:\s*[\u2014-]\s*(?P<note>.+))?$"
)


# ── Slot constructors ────────────────────────────────────────────────

def empty_slot(position):
    return {
        "position": position,
        "type": "empty",
        "ref": None,
        "recently_done": [],
        "next": "",
        "holding": "",
        "notes": "",
    }


def todos_slot(position):
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


def thread_slot(position, ref_type, ref):
    if ref_type not in ("project", "concept", "task"):
        raise ValueError(f"unknown ref-type '{ref_type}'")
    return {
        "position": position,
        "type": ref_type,
        "ref": ref,
        "recently_done": [],
        "next": "",
        "holding": "",
        "notes": "",
    }


# ── File location ────────────────────────────────────────────────────

def board_path(vault):
    return Path(vault) / "tasks" / "day-board.md"


# ── Frontmatter helpers ──────────────────────────────────────────────

def split_frontmatter(content):
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if not m:
        return "", content
    return content[: m.end()], content[m.end():]


def bump_frontmatter_dates(fm):
    if not fm:
        return fm
    today = date.today().isoformat()
    fm = re.sub(
        r"^(last_updated:\s*)[^\n]*", rf"\g<1>{today}",
        fm, count=1, flags=re.MULTILINE,
    )
    fm = re.sub(
        r"^(last_verified:\s*)[^\n]*", rf"\g<1>{today}",
        fm, count=1, flags=re.MULTILINE,
    )
    return fm


# ── Parse ────────────────────────────────────────────────────────────

def normalise_ref_input(ref, hint=None):
    """Accept 'T18', 'T018', 'em-arcline', 'project:em-arcline',
    'em-arcline (project)', 'em-arcline (concept)'.
    Return (ref_type, canonical_ref)."""
    raw = ref.strip()
    m = re.match(r"^(project|concept|task)\s*:\s*(.+)$", raw)
    if m:
        rt = m.group(1).lower()
        rest = m.group(2).strip()
        return _resolve_bare(rest, hint=rt)
    m = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", raw)
    if m:
        return _resolve_bare(m.group(1).strip(), hint=m.group(2).strip().lower())
    return _resolve_bare(raw, hint=hint)


def _resolve_bare(raw, hint=None):
    # Task: 'T18' / 'T018' / 't018'
    m = re.match(r"^[Tt](\d+)$", raw)
    if m:
        return "task", f"T{m.group(1).zfill(3)}"
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9-]*$", raw):
        raise ValueError(
            f"unparseable ref '{raw}' — expected T<nnn> or a slug"
        )
    rt = (hint or "project").lower()
    if rt not in ("project", "concept"):
        raise ValueError(f"invalid ref-type hint '{hint}'")
    return rt, raw


def parse(path):
    """Read the board file and return a structured dict.

    Shape: {frontmatter, intro, warnings, slots:[5], parked:{ref: context}}.
    Slots are always present in positions 1..5 and ordered.
    Parked holds context for dismissed items so they can be restored."""
    result = {
        "frontmatter": "",
        "intro": "",
        "warnings": [],
        "slots": [empty_slot(i + 1) for i in range(NUM_SLOTS)],
        "parked": {},
        "path": str(path),
    }

    if not path.exists():
        result["warnings"].append("file not found")
        return result

    content = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(content)
    result["frontmatter"] = fm

    current_slot = None
    current_field = None
    field_lines = []
    intro_lines = []

    def commit():
        nonlocal field_lines
        _commit_field(current_slot, current_field, field_lines)
        field_lines = []

    for lineno, raw in enumerate(body.splitlines(), 1):
        line = raw.rstrip()

        if line.startswith("## "):
            commit()
            current_field = None
            heading = line[3:].strip()
            if heading.lower() == "parked":
                # Parked section is always last; parsed separately after the loop
                break
            sm = SLOT_RE.match(heading)
            if not sm:
                result["warnings"].append(
                    f"line {lineno}: unrecognised slot heading '{heading}'"
                )
                current_slot = None
                continue
            position = int(sm.group(1))
            payload = sm.group(2).strip()
            if not (1 <= position <= NUM_SLOTS):
                result["warnings"].append(
                    f"line {lineno}: position {position} out of range"
                )
                current_slot = None
                continue
            current_slot = _interpret_payload(
                position, payload, result["slots"], result["warnings"], lineno
            )
            continue

        if line.startswith("### "):
            commit()
            heading = line[4:].strip().lower()
            mapping = {v.lower(): k for k, v in FIELD_HEADINGS.items()}
            current_field = mapping.get(heading)
            if current_field is None and heading:
                result["warnings"].append(
                    f"line {lineno}: unknown field '{heading}'"
                )
            continue

        if current_slot is None:
            intro_lines.append(raw)
            continue

        if current_field is not None:
            field_lines.append(raw)

    commit()

    while intro_lines and not intro_lines[-1].strip():
        intro_lines.pop()
    result["intro"] = "\n".join(intro_lines)

    result["slots"].sort(key=lambda s: s["position"])

    # Parse parked section (stored after slots in the markdown)
    parked_match = re.search(
        r"^## Parked\s*\n(.+)",
        body, re.MULTILINE | re.DOTALL,
    )
    if parked_match:
        result["parked"] = _parse_parked_section(parked_match.group(1))

    return result


def _commit_field(slot, field_key, lines):
    if slot is None or field_key is None:
        return
    while lines and not lines[-1].strip():
        lines.pop()

    if slot["type"] == "todos" and field_key == "items":
        for ln in lines:
            stripped = ln.strip()
            if not stripped:
                continue
            m = TODOS_ITEM_RE.match(stripped)
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


def _interpret_payload(position, payload, slots, warnings, lineno):
    idx = position - 1
    plow = payload.lower().strip().rstrip(".")
    if plow in {"empty", "(empty)"}:
        slots[idx] = empty_slot(position)
        return slots[idx]
    if plow.startswith("today's todos") or plow == "todos":
        slots[idx] = todos_slot(position)
        return slots[idx]
    m = REF_RE.match(payload.strip())
    if not m:
        warnings.append(f"line {lineno}: unparseable payload '{payload}'")
        slots[idx] = empty_slot(position)
        return slots[idx]
    if m.group(1):
        slot = thread_slot(position, "task", f"T{m.group(1).zfill(3)}")
    else:
        ref = m.group(2)
        rt = (m.group(3) or "project").strip().lower()
        if rt not in {"project", "concept", "task"}:
            warnings.append(
                f"line {lineno}: unknown ref-type '{rt}', defaulting to project"
            )
            rt = "project"
        slot = thread_slot(position, rt, ref)
    slots[idx] = slot
    return slot


# ── Parked section parser ────────────────────────────────────────────

PARKED_ENTRY_RE = re.compile(r"^### (.+?)\s*\(([^)]+)\)\s*$")

def _parse_parked_section(text):
    """Parse the ## Parked section into {ref: {type, recently_done, next, holding, notes}}."""
    parked = {}
    current_ref = None
    current_type = None
    current_field = None
    field_lines = []

    def commit_parked_field():
        nonlocal field_lines
        if current_ref is None or current_field is None:
            field_lines = []
            return
        entry = parked.setdefault(current_ref, {
            "type": current_type or "project",
            "recently_done": [], "next": "", "holding": "", "notes": "",
        })
        if current_field == "recently_done":
            for ln in field_lines:
                stripped = ln.strip()
                if stripped.startswith("- "):
                    entry["recently_done"].append(stripped[2:].strip())
                elif stripped:
                    entry["recently_done"].append(stripped)
        elif current_field in {"next", "holding", "notes"}:
            entry[current_field] = "\n".join(field_lines).strip()
        field_lines = []

    for line in text.splitlines():
        stripped = line.rstrip()
        m = PARKED_ENTRY_RE.match(stripped)
        if m:
            commit_parked_field()
            current_ref = m.group(1).strip()
            current_type = m.group(2).strip().lower()
            current_field = None
            parked.setdefault(current_ref, {
                "type": current_type,
                "recently_done": [], "next": "", "holding": "", "notes": "",
            })
            continue
        if stripped.startswith("#### "):
            commit_parked_field()
            heading = stripped[5:].strip().lower()
            mapping = {v.lower(): k for k, v in FIELD_HEADINGS.items()}
            current_field = mapping.get(heading)
            continue
        if current_ref is not None and current_field is not None:
            field_lines.append(line.rstrip())

    commit_parked_field()
    return parked


# ── Render ───────────────────────────────────────────────────────────

def render(parsed):
    out = []
    fm = parsed.get("frontmatter", "")
    if fm:
        out.append(fm.rstrip("\n"))
        out.append("")
    intro = parsed.get("intro", "").rstrip("\n")
    if intro:
        out.append(intro)
        out.append("")

    for slot in parsed["slots"]:
        out.append(_render_slot_heading(slot))
        out.append("")
        if slot["type"] == "empty":
            continue
        if slot["type"] == "todos":
            out.append("### Items")
            out.append("")
            for item in slot.get("items", []):
                check = "x" if item.get("done") else " "
                line = f"- [{check}] {item['ref']}"
                if item.get("note"):
                    line += f" — {item['note']}"
                out.append(line)
            out.append("")
            continue

        for key in FIELDS:
            out.append(f"### {FIELD_HEADINGS[key]}")
            out.append("")
            if key == "recently_done":
                for line in slot["recently_done"]:
                    out.append(f"- {line}")
            else:
                if slot[key]:
                    out.append(slot[key])
            out.append("")

    # Render parked section if any items are parked
    parked = parsed.get("parked", {})
    if parked:
        out.append("## Parked")
        out.append("")
        for ref, ctx in parked.items():
            out.append(f"### {ref} ({ctx.get('type', 'project')})")
            out.append("")
            for key in FIELDS:
                out.append(f"#### {FIELD_HEADINGS[key]}")
                out.append("")
                if key == "recently_done":
                    for line in ctx.get("recently_done", []):
                        out.append(f"- {line}")
                else:
                    if ctx.get(key):
                        out.append(ctx[key])
                out.append("")

    text = "\n".join(out).rstrip() + "\n"
    return text


def _render_slot_heading(slot):
    pos = slot["position"]
    if slot["type"] == "empty":
        return f"## Slot {pos}: empty"
    if slot["type"] == "todos":
        return f"## Slot {pos}: Today's todos"
    return f"## Slot {pos}: {slot['ref']} ({slot['type']})"


def save(path, parsed):
    path.parent.mkdir(parents=True, exist_ok=True)
    parsed["frontmatter"] = bump_frontmatter_dates(parsed.get("frontmatter", ""))
    path.write_text(render(parsed), encoding="utf-8")


# ── Operations ───────────────────────────────────────────────────────

def _slot_at(parsed, position):
    if not (1 <= position <= NUM_SLOTS):
        raise ValueError(f"position {position} out of range 1..{NUM_SLOTS}")
    for s in parsed["slots"]:
        if s["position"] == position:
            return s
    raise ValueError(f"slot {position} missing")


def _validate_position(position):
    if not (1 <= position <= NUM_SLOTS):
        raise ValueError(f"position {position} out of range 1..{NUM_SLOTS}")


def _set_slot(parsed, position, slot):
    _validate_position(position)
    parsed["slots"] = [
        slot if s["position"] == position else s
        for s in parsed["slots"]
    ]


def _park_slot(parsed, slot):
    """Save a slot's context to parked storage (keyed by ref).
    Only parks if the slot has meaningful content to preserve."""
    if slot["type"] in {"empty", "todos"}:
        return
    ref = slot.get("ref")
    if not ref:
        return
    has_content = (
        slot.get("recently_done")
        or slot.get("next")
        or slot.get("holding")
        or slot.get("notes")
    )
    if not has_content:
        return
    parsed.setdefault("parked", {})[ref] = {
        "type": slot["type"],
        "recently_done": list(slot.get("recently_done", [])),
        "next": slot.get("next", ""),
        "holding": slot.get("holding", ""),
        "notes": slot.get("notes", ""),
    }


def _unpark_slot(parsed, ref, slot):
    """If ref has parked context, restore it into slot and remove from parked.
    Returns True if context was restored."""
    parked = parsed.get("parked", {})
    ctx = parked.pop(ref, None)
    if ctx is None:
        return False
    slot["recently_done"] = ctx.get("recently_done", [])
    slot["next"] = ctx.get("next", "")
    slot["holding"] = ctx.get("holding", "")
    slot["notes"] = ctx.get("notes", "")
    return True


def op_assign(parsed, position, ref, ref_type=None):
    rt, canonical = normalise_ref_input(ref, hint=ref_type)
    new = thread_slot(position, rt, canonical)
    # Restore parked context if this ref was previously dismissed
    restored = _unpark_slot(parsed, canonical, new)
    _set_slot(parsed, position, new)
    return {"action": "assign", "position": position, "type": rt, "ref": canonical,
            "restored_from_park": restored}


def op_assign_todos(parsed, position):
    _set_slot(parsed, position, todos_slot(position))
    return {"action": "assign-todos", "position": position}


def op_dismiss(parsed, position):
    prior = _slot_at(parsed, position)
    # Park the context so it can be restored on re-assign
    _park_slot(parsed, prior)
    _set_slot(parsed, position, empty_slot(position))
    return {
        "action": "dismiss", "position": position,
        "prior_type": prior["type"], "prior_ref": prior.get("ref"),
        "summary": _slot_summary(prior),
    }


def op_done(parsed, position, todo_path=None):
    """Mark slot done. For task slots, also update todo-list.md.
    For project/concept/todos slots, just clear and report."""
    prior = _slot_at(parsed, position)
    extra = {}
    if prior["type"] == "task" and prior.get("ref"):
        if todo_path is None:
            todo_path = parsed_default_todo_path(parsed)
        if todo_path and todo_path.exists():
            ok, msg = mark_task_done_in_todo_list(todo_path, prior["ref"])
            extra = {"todo_list_updated": ok, "todo_list_message": msg}
    # Park the context so it can be restored if re-assigned later
    _park_slot(parsed, prior)
    _set_slot(parsed, position, empty_slot(position))
    return {
        "action": "done", "position": position,
        "prior_type": prior["type"], "prior_ref": prior.get("ref"),
        "summary": _slot_summary(prior),
        **extra,
    }


def op_set_field(parsed, position, field, value):
    slot = _slot_at(parsed, position)
    if field not in {"next", "holding", "notes", "recently_done"}:
        raise ValueError(f"unknown field '{field}'")
    if slot["type"] in {"empty", "todos"}:
        raise ValueError(
            f"cannot set field on {slot['type']} slot {position}"
        )
    if field == "recently_done":
        # value is a newline-separated string; one bullet per non-empty line
        lines = [ln.strip().lstrip("-").strip() for ln in value.splitlines()]
        slot["recently_done"] = [ln for ln in lines if ln]
    else:
        slot[field] = value.strip()
    return {"action": "set-field", "position": position, "field": field}


def op_add_recent(parsed, position, line):
    slot = _slot_at(parsed, position)
    if slot["type"] in {"empty", "todos"}:
        raise ValueError(
            f"cannot add recent on {slot['type']} slot {position}"
        )
    line = line.strip().lstrip("-").strip()
    if not line:
        return {"action": "add-recent", "position": position, "noop": True}
    slot["recently_done"].append(line)
    return {"action": "add-recent", "position": position, "line": line}


def op_todos_add(parsed, position, ref, note=""):
    slot = _slot_at(parsed, position)
    if slot["type"] != "todos":
        raise ValueError(f"slot {position} is not a todos slot")
    rt, canonical = normalise_ref_input(ref)
    if rt != "task":
        raise ValueError(f"todos slot only accepts task refs, got '{ref}'")
    if any(it["ref"] == canonical for it in slot["items"]):
        return {"action": "todos-add", "position": position,
                "ref": canonical, "noop": True}
    slot["items"].append({"ref": canonical, "done": False, "note": note.strip()})
    return {"action": "todos-add", "position": position, "ref": canonical}


def op_todos_remove(parsed, position, ref):
    slot = _slot_at(parsed, position)
    if slot["type"] != "todos":
        raise ValueError(f"slot {position} is not a todos slot")
    _, canonical = normalise_ref_input(ref)
    before = len(slot["items"])
    slot["items"] = [it for it in slot["items"] if it["ref"] != canonical]
    return {"action": "todos-remove", "position": position,
            "ref": canonical, "removed": before - len(slot["items"])}


def op_todos_toggle(parsed, position, ref, todo_path=None):
    slot = _slot_at(parsed, position)
    if slot["type"] != "todos":
        raise ValueError(f"slot {position} is not a todos slot")
    _, canonical = normalise_ref_input(ref)
    item = next((it for it in slot["items"] if it["ref"] == canonical), None)
    if not item:
        raise ValueError(f"task {canonical} not in todos slot {position}")
    item["done"] = not item.get("done", False)
    extra = {}
    if item["done"]:
        if todo_path is None:
            todo_path = parsed_default_todo_path(parsed)
        if todo_path and todo_path.exists():
            ok, msg = mark_task_done_in_todo_list(todo_path, canonical)
            extra = {"todo_list_updated": ok, "todo_list_message": msg}
    return {"action": "todos-toggle", "position": position,
            "ref": canonical, "done": item["done"], **extra}


def _slot_summary(slot):
    if slot["type"] in {"empty", "todos"}:
        return None
    parts = []
    if slot.get("recently_done"):
        parts.append("Recent: " + "; ".join(slot["recently_done"]))
    if slot.get("holding"):
        parts.append("Holding: " + slot["holding"])
    if slot.get("notes"):
        parts.append("Notes: " + slot["notes"])
    return " | ".join(parts) if parts else None


# ── Todo-list write-through ──────────────────────────────────────────

def parsed_default_todo_path(parsed):
    """Resolve tasks/todo-list.md path from the board file path."""
    board = Path(parsed.get("path", ""))
    if not board.parent.name == "tasks":
        return None
    return board.parent / "todo-list.md"


def mark_task_done_in_todo_list(todo_path, t_ref):
    """Set the named T-row's status to done in todo-list.md.

    Side-effects: bumps the file's last_updated frontmatter. Does not
    move the row to the Completed Tasks section — that's a curation step
    the user does explicitly. Returns (ok, message).
    """
    text = todo_path.read_text(encoding="utf-8")
    # Find the row beginning with `| T<id>` (allow padding/whitespace)
    pattern = re.compile(
        r"^(\|\s*" + re.escape(t_ref) + r"\s*\|\s*[^|]+\|\s*)([^|]+?)(\s*\|)",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return False, f"{t_ref} not found in todo-list.md"
    current_status = m.group(2).strip().lower()
    if "done" in current_status:
        return True, f"{t_ref} already marked done"
    new_text = pattern.sub(r"\g<1>✅ done\g<3>", text, count=1)
    new_text = re.sub(
        r"^(last_updated:\s*)[^\n]*", rf"\g<1>{date.today().isoformat()}",
        new_text, count=1, flags=re.MULTILINE,
    )
    todo_path.write_text(new_text, encoding="utf-8")
    return True, f"{t_ref} → ✅ done"


# ── Init helper ──────────────────────────────────────────────────────

def init(path):
    if path.exists():
        return False
    today = date.today().isoformat()
    body = (
        "---\n"
        'title: "Day Board"\n'
        "domains:\n  - tasks\n"
        "type: reference\n"
        "tags:\n  - board\n  - workflow\n  - day-dashboard\n"
        "source: manual\n"
        f"created: {today}\n"
        f"last_updated: {today}\n"
        f"last_verified: {today}\n"
        "confidence: high\n"
        "---\n\n"
        "# Day Board\n\n"
        "Five focus slots — managed via the dashboard's Day tab or the "
        "EV skill's DAY BOARD capability.\n\n"
    )
    parts = [body]
    for i in range(1, NUM_SLOTS + 1):
        parts.append(f"## Slot {i}: empty\n\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts).rstrip() + "\n", encoding="utf-8")
    return True


# ── CLI ──────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description="Manage the EV Day Board (slot model).")
    ap.add_argument("--vault", required=True)
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("read")
    sub.add_parser("init")

    p = sub.add_parser("assign")
    p.add_argument("position", type=int)
    p.add_argument("ref")
    p.add_argument("--type", default=None)

    p = sub.add_parser("assign-todos")
    p.add_argument("position", type=int)

    p = sub.add_parser("dismiss")
    p.add_argument("position", type=int)

    p = sub.add_parser("done")
    p.add_argument("position", type=int)

    p = sub.add_parser("set-field")
    p.add_argument("position", type=int)
    p.add_argument("field", choices=["recently_done", "next", "holding", "notes"])
    p.add_argument("value")

    p = sub.add_parser("add-recent")
    p.add_argument("position", type=int)
    p.add_argument("line")

    p = sub.add_parser("todos")
    p.add_argument("op", choices=["add", "remove", "toggle"])
    p.add_argument("position", type=int)
    p.add_argument("ref")
    p.add_argument("--note", default="")

    p = sub.add_parser("tasks-done")
    p.add_argument("ref")

    args = ap.parse_args(argv)
    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"ERROR: vault not found at {vault}", file=sys.stderr)
        return 1

    bp = board_path(vault)
    if args.cmd == "init":
        created = init(bp)
        result = {"action": "init", "created": created, "path": str(bp)}
        return _emit(result, args.json)

    if not bp.exists():
        if args.cmd == "read":
            result = {"action": "read", "warnings": ["file not found"], "slots": []}
            return _emit(result, args.json)
        # Auto-init for any write op
        init(bp)

    parsed = parse(bp)

    try:
        if args.cmd == "read":
            result = {
                "action": "read", "path": str(bp),
                "warnings": parsed["warnings"], "slots": parsed["slots"],
                "parked": parsed.get("parked", {}),
            }
        elif args.cmd == "assign":
            result = op_assign(parsed, args.position, args.ref, args.type)
            save(bp, parsed)
        elif args.cmd == "assign-todos":
            result = op_assign_todos(parsed, args.position)
            save(bp, parsed)
        elif args.cmd == "dismiss":
            result = op_dismiss(parsed, args.position)
            save(bp, parsed)
        elif args.cmd == "done":
            result = op_done(parsed, args.position)
            save(bp, parsed)
        elif args.cmd == "set-field":
            result = op_set_field(parsed, args.position, args.field, args.value)
            save(bp, parsed)
        elif args.cmd == "add-recent":
            result = op_add_recent(parsed, args.position, args.line)
            save(bp, parsed)
        elif args.cmd == "todos":
            if args.op == "add":
                result = op_todos_add(parsed, args.position, args.ref, args.note)
            elif args.op == "remove":
                result = op_todos_remove(parsed, args.position, args.ref)
            else:
                result = op_todos_toggle(parsed, args.position, args.ref)
            save(bp, parsed)
        elif args.cmd == "tasks-done":
            tp = parsed_default_todo_path(parsed)
            if tp is None:
                result = {"action": "tasks-done", "ref": args.ref, "ok": False,
                          "message": "could not resolve todo-list.md"}
            else:
                ok, msg = mark_task_done_in_todo_list(tp, args.ref)
                result = {"action": "tasks-done", "ref": args.ref, "ok": ok, "message": msg}
        else:
            ap.error(f"unknown command {args.cmd}")
            return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return _emit(result, args.json)


def _emit(result, as_json):
    if as_json:
        print(json.dumps(result, indent=2, default=str))
        return 0
    action = result.get("action")
    if action == "read":
        for s in result.get("slots", []):
            head = f"  Slot {s['position']}: "
            if s["type"] == "empty":
                print(head + "empty")
            elif s["type"] == "todos":
                items = " ".join(
                    ("✓" if it["done"] else "·") + it["ref"]
                    for it in s.get("items", [])
                )
                print(head + f"todos — {items or '(none)'}")
            else:
                print(head + f"{s['ref']} ({s['type']})")
                if s.get("next"):
                    print(f"      next:    {s['next'][:80]}")
                if s.get("holding"):
                    print(f"      holding: {s['holding'][:80]}")
        for w in result.get("warnings", []):
            print(f"  ⚠ {w}")
        return 0
    if action in {"assign", "assign-todos"}:
        if action == "assign-todos":
            print(f"✓ slot {result['position']} → Today's todos")
        else:
            print(f"✓ slot {result['position']} → {result['type']}:{result['ref']}")
        return 0
    if action == "dismiss":
        print(f"✓ slot {result['position']} dismissed (was {result['prior_type']}:{result.get('prior_ref') or '—'})")
        if result.get("summary"):
            print(f"  archived: {result['summary']}")
        return 0
    if action == "done":
        print(f"✓ slot {result['position']} done (was {result['prior_type']}:{result.get('prior_ref') or '—'})")
        if "todo_list_message" in result:
            print(f"  todo-list.md: {result['todo_list_message']}")
        if result.get("summary"):
            print(f"  archived: {result['summary']}")
        return 0
    if action == "set-field":
        print(f"✓ slot {result['position']} {result['field']} updated")
        return 0
    if action == "add-recent":
        if result.get("noop"):
            print(f"  slot {result['position']} unchanged (empty line)")
        else:
            print(f"✓ slot {result['position']} recent + '{result['line']}'")
        return 0
    if action == "todos-add":
        if result.get("noop"):
            print(f"  slot {result['position']} already has {result['ref']}")
        else:
            print(f"✓ slot {result['position']} todos + {result['ref']}")
        return 0
    if action == "todos-remove":
        print(f"✓ slot {result['position']} todos − {result['ref']} ({result['removed']} removed)")
        return 0
    if action == "todos-toggle":
        state = "done" if result["done"] else "open"
        print(f"✓ slot {result['position']} {result['ref']} → {state}")
        if "todo_list_message" in result:
            print(f"  todo-list.md: {result['todo_list_message']}")
        return 0
    if action == "init":
        if result["created"]:
            print(f"✓ initialised {result['path']}")
        else:
            print(f"  exists: {result['path']}")
        return 0
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
