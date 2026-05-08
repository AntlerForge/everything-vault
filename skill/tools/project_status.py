#!/usr/bin/env python3
"""
project_status.py — assess and update project statuses from activity signals.

Reads every article with `tier: project`, gathers activity signals from:

  1. The article's own `last_updated` frontmatter date.
  2. Episodes (vault/episodes/**/*.md) whose `article_refs` contains the
     project's filename stem.
  3. Work-logs (vault/work-log/**/*.md) whose `projects_touched[].slug`
     matches the project's filename stem.

For each project computes a proposed status transition (or None) with a
confidence level. In --apply mode, high-confidence proposals are written
back into the article's frontmatter and a Change History row is prepended
(or a new Change History section created).

Rules (status transitions):

  R1. No signal-bearing activity in 60+ days AND current not in a delivered-*
      status → propose `delivered-and-parked` (high).

  R2. current == delivered-and-parked (or legacy `parked`) AND any forward-
      motion activity in last 14 days → propose `under-development` (high).

  R3. [retired 2026-04-24.]

  R4. current == ideas AND any `ship` activity in last 30 days →
      propose `prototype` (medium).

  R5. current == prototype AND >=3 `operate` kinds in last 30 days AND no
      new `build` in last 14 days → propose `under-development` (high).

  R6. current == under-development AND any `wrap` kind AND no `build`/`ship`
      in last 30 days → propose `delivered-and-operational` (medium).

Confidence policy:
  - `high` — unambiguous time-based rule (R1, R2, R5).
  - `medium` — content/kind-based inference (R4, R6).
  - `low` — reserved; currently none of the rules emit it.

Only `high`-confidence proposals are applied automatically with --apply.
Medium proposals land in the cache for morning review.

Usage:
    python3 project_status.py --vault <vault>                  # report only
    python3 project_status.py --vault <vault> --apply          # apply high-conf
    python3 project_status.py --vault <vault> --cache          # write cache json
    python3 project_status.py --vault <vault> --apply --cache  # both

Cache location:
    Proposals (when --cache is set) are written to
    <project>/_cache/project-status-proposals.json (a sibling of vault/, not
    inside it). The legacy in-vault location vault/_project-status-proposals.json
    is still readable as a fallback during this release.

Exit codes:
    0 success (report/apply completed)
    1 vault not found or unreadable
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

# Canonical EV status set — final five-slot pipeline as of 2026-04-24:
#
#   ideas → prototype → under-development → delivered-and-operational
#                                         → delivered-and-parked
#
# Vocabulary history (all 2026-04-24):
#   - `seed` was collapsed into `developing` (morning pass).
#   - `developing` was then renamed to `ideas`; existing developing articles
#     were promoted to `active` (they were already work-in-progress, not
#     fresh captures).
#   - `active` was renamed to `under-development`.
#   - `parked` was merged into `delivered-and-parked` (itself renamed from
#     `delivered-and-retired`) — one "shelved, might come back" bucket.
#   - `delivered` is retained as a legacy alias for `delivered-and-operational`.
#
# Residual legacy values are coerced to the current canonical slot by the
# dashboard and rule engine.
VALID_STATUSES = (
    "ideas", "prototype", "under-development",
    "delivered-and-operational", "delivered-and-parked",
    # legacy aliases
    "developing", "active", "delivered", "delivered-and-retired", "parked",
)

# Statuses that mean "the project has landed and shouldn't be auto-shelved
# by R1's long-idle rule" — shipped / in-use / parked-after-delivery items
# aren't forgotten, they're just not being actively worked on.
_DELIVERED_LIKE = (
    "delivered-and-operational", "delivered-and-parked",
    "delivered-and-retired", "delivered",  # legacy
)

# Keyword heuristics for inferring activity kind from episode text when the
# episode doesn't carry an explicit `kind` field. Work-log entries always
# carry explicit `kind` so they don't need inference.
KIND_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ship":    ("shipped", "deployed", "released", "launched", "installed", "went live"),
    "build":   ("built", "implemented", "wrote", "coded", "added", "created"),
    "iterate": ("refactored", "polished", "fixed", "tweaked", "improved"),
    "design":  ("spec'd", "designed", "planned", "researched", "sketched"),
    "operate": ("ran", "monitored", "triaged", "used", "processed"),
    "maintain":("patched", "updated", "reconfigured"),
    "wrap":    ("documented", "wrapped", "post-mortem", "archived", "handover"),
    "pause":   ("paused", "shelved", "parked", "on hold"),
}


# ── Cache path resolution ────────────────────────────────────────────

def cache_path(vault_path):
    """Return the path to write the project-status proposals cache. Always
    returns the sibling location <project>/_cache/project-status-proposals.json
    so new writes never land back inside vault/. The legacy in-vault location
    is read-only (current callers don't read it; future readers should fall
    back to vault/_project-status-proposals.json if the sibling is missing)."""
    vault = Path(vault_path).expanduser().resolve()
    sibling_cache = vault.parent / "_cache" / "project-status-proposals.json"
    sibling_cache.parent.mkdir(parents=True, exist_ok=True)
    return sibling_cache


# ── Frontmatter parsing (minimal, no pyyaml dep) ─────────────────────

# Skip files inside any underscore-prefixed folder ("_for-deletion/", "_archive/" etc.)
# so soft-deleted content stays out of indexing, queries, and dashboard.
def _is_under_dot_or_underscore(path, vault_root):
    try:
        parts = path.relative_to(vault_root).parts
    except ValueError:
        return True  # outside vault
    return any(p.startswith("_") or p.startswith(".") for p in parts[:-1])

def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse a minimal subset of YAML frontmatter. Returns (fm_dict, body)."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    fm: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[Any] | None = None
    pending_map: dict[str, Any] | None = None

    for raw_line in fm_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        # List item under current_key
        if line.startswith("  - ") or line.startswith("- "):
            item = line.strip()[2:].strip()
            if current_list is None:
                continue
            # Dict item: "- slug: foo"
            if ":" in item and not item.startswith("["):
                k, _, v = item.partition(":")
                pending_map = {k.strip(): _coerce(v.strip())}
                current_list.append(pending_map)
            else:
                current_list.append(_coerce(item))
                pending_map = None
            continue
        # Continuation of a dict item (indented keys)
        if line.startswith("    ") and pending_map is not None:
            k, _, v = line.strip().partition(":")
            if k:
                pending_map[k.strip()] = _coerce(v.strip())
            continue
        # Top-level key
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            current_key = k
            pending_map = None
            if v == "" or v in ("|", ">"):
                current_list = []
                fm[k] = current_list
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1]
                fm[k] = [_coerce(i.strip()) for i in inner.split(",") if i.strip()]
                current_list = None
            else:
                fm[k] = _coerce(v)
                current_list = None
    return fm, body


def _coerce(v: Any) -> Any:
    if isinstance(v, str):
        s = v.strip().strip("\"'")
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1]
            return [_coerce(i.strip()) for i in inner.split(",") if i.strip()]
        return s
    return v


# ── Gather signals ───────────────────────────────────────────────────

def _parse_date(s: Any) -> date | None:
    if not s:
        return None
    if isinstance(s, date):
        return s
    s = str(s).strip().strip("\"'")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def infer_kinds_from_text(text: str) -> list[str]:
    """Best-effort kind tagging for an episode based on its text."""
    text_lower = text.lower()
    hits: list[str] = []
    for kind, keywords in KIND_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            hits.append(kind)
    return hits


def collect_projects(vault: Path) -> list[dict[str, Any]]:
    """Return every tier=project article with parsed frontmatter and path."""
    projects: list[dict[str, Any]] = []
    for md in vault.rglob("*.md"):
        if _is_under_dot_or_underscore(md, vault):
            continue
        # Skip installed-skill folders mirrored into the vault; scan the live
        # vault only. The skills-catalog source tree is fine to scan but won't
        # contain project articles itself.
        if md.name.startswith("_"):
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm, body = parse_frontmatter(text)
        if str(fm.get("tier", "")).strip() != "project":
            continue
        projects.append({
            "path": md,
            "rel_path": str(md.relative_to(vault)),
            "slug": md.stem,
            "fm": fm,
            "body": body,
            "text": text,
        })
    return projects


def collect_episode_signals(vault: Path, project_slug: str) -> list[tuple[date, list[str]]]:
    """Return [(date, kinds)] for episodes referencing this project."""
    out: list[tuple[date, list[str]]] = []
    ep_dir = vault / "episodes"
    if not ep_dir.exists():
        return out
    for md in ep_dir.rglob("*.md"):
        if _is_under_dot_or_underscore(md, vault):
            continue
        if md.name.startswith("_"):
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm, body = parse_frontmatter(text)
        refs = fm.get("article_refs") or []
        # Normalise refs (strings or slug-only lookups).
        ref_slugs = {str(r).split("/")[-1].replace(".md", "").strip() for r in refs}
        if project_slug not in ref_slugs:
            continue
        dt = _parse_date(fm.get("date")) or _parse_date(fm.get("created"))
        if dt is None:
            continue
        # Prefer explicit kind field on the episode if present.
        raw_kinds = fm.get("kind") or fm.get("kinds") or []
        if isinstance(raw_kinds, str):
            raw_kinds = [raw_kinds]
        kinds = [k for k in raw_kinds if k in KIND_KEYWORDS] or infer_kinds_from_text(text)
        out.append((dt, kinds))
    return out


def collect_work_log_signals(vault: Path, project_slug: str) -> list[tuple[date, list[str], str]]:
    """Return [(date, kinds, level)] for work-log entries listing this project."""
    out: list[tuple[date, list[str], str]] = []
    wl_dir = vault / "work-log"
    if not wl_dir.exists():
        return out
    for md in wl_dir.rglob("*.md"):
        if _is_under_dot_or_underscore(md, vault):
            continue
        if md.name.startswith("_"):
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm, _ = parse_frontmatter(text)
        dt = _parse_date(fm.get("date"))
        if dt is None:
            continue
        touched = fm.get("projects_touched") or []
        for entry in touched:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("slug", "")).strip() != project_slug:
                continue
            raw_kinds = entry.get("kind") or []
            if isinstance(raw_kinds, str):
                raw_kinds = [raw_kinds]
            kinds = [k for k in raw_kinds if k in KIND_KEYWORDS]
            level = str(entry.get("level", "")).strip() or "unknown"
            out.append((dt, kinds, level))
    return out


# ── Rule engine ──────────────────────────────────────────────────────

def compute_signals(project: dict[str, Any], vault: Path, today: date) -> dict[str, Any]:
    fm = project["fm"]
    slug = project["slug"]
    last_updated = _parse_date(fm.get("last_updated")) or _parse_date(fm.get("created"))

    episodes = collect_episode_signals(vault, slug)
    work_logs = collect_work_log_signals(vault, slug)

    all_dates: list[date] = []
    if last_updated:
        all_dates.append(last_updated)
    all_dates.extend(d for d, _ in episodes)
    all_dates.extend(d for d, _, _ in work_logs)

    last_activity = max(all_dates) if all_dates else None
    days_since = (today - last_activity).days if last_activity else None

    def kinds_in_window(days: int) -> Counter:
        cutoff = today - timedelta(days=days)
        c: Counter = Counter()
        for d, kinds in episodes:
            if d >= cutoff:
                for k in kinds:
                    c[k] += 1
        for d, kinds, _ in work_logs:
            if d >= cutoff:
                for k in kinds:
                    c[k] += 1
        return c

    return {
        "current_status": fm.get("status"),
        "last_updated": last_updated,
        "last_activity": last_activity,
        "days_since_activity": days_since,
        "kinds_14d": kinds_in_window(14),
        "kinds_30d": kinds_in_window(30),
        "kinds_60d": kinds_in_window(60),
        "episodes_count": len(episodes),
        "work_log_count": len(work_logs),
    }


def propose_status(project: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any] | None:
    """Return a proposal dict or None. Keys: new_status, confidence, reason."""
    current = str(signals["current_status"] or "").strip()
    if current and current not in VALID_STATUSES:
        # Data-quality fix — map common aliases.
        if current == "completed":
            return _prop("delivered-and-operational", "high",
                         f"Invalid status '{current}' corrected to canonical 'delivered-and-operational'.")

    days = signals["days_since_activity"]
    k14 = signals["kinds_14d"]
    k30 = signals["kinds_30d"]

    # R1 — long-idle → delivered-and-parked (skip delivered-like statuses:
    # they've already landed, not forgotten)
    if (days is not None and days >= 60
            and current not in _DELIVERED_LIKE):
        return _prop("delivered-and-parked", "high",
                     f"No activity in {days} days (>60-day threshold).")

    # R2 — reactivation from a parked/shelved state (forward-motion kinds
    # only; pause/wrap don't count). A parked project that starts moving
    # again isn't fresh — it has existing substance — so it goes to
    # `under-development`, not `ideas`.
    forward_kinds_14d = sum(k14.get(k, 0) for k in
                            ("build", "ship", "design", "iterate", "operate", "maintain"))
    if (current in ("delivered-and-parked", "parked")
            and days is not None and days <= 14
            and forward_kinds_14d > 0):
        return _prop("under-development", "high",
                     f"Fresh forward-motion activity ({forward_kinds_14d} event(s)) after parked period.")

    # R3 — retired 2026-04-24.

    # R4 — ideas → prototype (ship). Accepts legacy `developing` too.
    if current in ("ideas", "developing") and k30.get("ship", 0) > 0:
        return _prop("prototype", "medium", "Ship activity detected in last 30 days.")

    # R5 — prototype → under-development (sustained operate, no new build)
    if (current == "prototype"
            and k30.get("operate", 0) >= 3
            and k14.get("build", 0) == 0):
        return _prop("under-development", "high",
                     f"Sustained operate activity ({k30['operate']} events / 30d) with no recent build.")

    # R6 — under-development → delivered-and-operational (wrap without new
    # build). Default assumes the thing stayed in use; if it was shelved,
    # the user can promote manually to delivered-and-parked. Accepts legacy
    # `active` too.
    if (current in ("under-development", "active")
            and k30.get("wrap", 0) > 0
            and (k30.get("build", 0) + k30.get("ship", 0)) == 0):
        return _prop("delivered-and-operational", "medium",
                     "Wrap-up activity with no new build/ship work in last 30 days.")

    return None


def _prop(new_status: str, confidence: str, reason: str) -> dict[str, Any]:
    return {"new_status": new_status, "confidence": confidence, "reason": reason}


# ── Apply ────────────────────────────────────────────────────────────

_CHANGE_HISTORY_HEADER = "## Change History"
_CHANGE_HISTORY_TABLE = "| Date | Change | Source | Confidence |\n|------|--------|--------|------------|"


def apply_proposal(project: dict[str, Any], proposal: dict[str, Any], today: date) -> None:
    """Rewrite the project's markdown file with the new status + Change History row."""
    text = project["text"]
    fm = project["fm"]
    new_status = proposal["new_status"]
    old_status = fm.get("status") or "(none)"
    reason = proposal["reason"]
    confidence = proposal["confidence"].capitalize()

    # Replace `status: <old>` in frontmatter block with new_status.
    # Only touches the first occurrence before the second `---` marker.
    fm_end = text.find("\n---", 4)
    if fm_end < 0:
        raise RuntimeError(f"No frontmatter terminator in {project['rel_path']}")
    fm_block = text[:fm_end]
    rest = text[fm_end:]
    new_fm_block = re.sub(r"(?m)^status:\s*.*$", f"status: {new_status}", fm_block, count=1)
    # Bump last_verified.
    today_str = today.isoformat()
    if re.search(r"(?m)^last_verified:\s*.*$", new_fm_block):
        new_fm_block = re.sub(r"(?m)^last_verified:\s*.*$",
                              f"last_verified: {today_str}", new_fm_block, count=1)
    new_text = new_fm_block + rest

    # Prepend a Change History row (or add the section if none).
    row = (f"| {today_str} | Status {old_status} → {new_status}. {reason} "
           f"| Nightly project-status inference | {confidence} |")
    if _CHANGE_HISTORY_HEADER in new_text:
        # Insert after the header + table separator line.
        lines = new_text.splitlines()
        out: list[str] = []
        inserted = False
        i = 0
        while i < len(lines):
            out.append(lines[i])
            if (not inserted
                    and lines[i].strip() == _CHANGE_HISTORY_HEADER):
                # Skip blank lines and header rows; find the separator then
                # insert after it so new rows appear at the top of the body.
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    out.append(lines[j]); j += 1
                # Expect header + separator lines.
                if j < len(lines) and lines[j].lstrip().startswith("| Date"):
                    out.append(lines[j]); j += 1
                if j < len(lines) and lines[j].lstrip().startswith("|---"):
                    out.append(lines[j]); j += 1
                out.append(row)
                inserted = True
                i = j
                continue
            i += 1
        if not inserted:
            out.append("")
            out.append(row)
        new_text = "\n".join(out)
        if not new_text.endswith("\n"):
            new_text += "\n"
    else:
        if not new_text.endswith("\n"):
            new_text += "\n"
        new_text += f"\n{_CHANGE_HISTORY_HEADER}\n\n{_CHANGE_HISTORY_TABLE}\n{row}\n"

    project["path"].write_text(new_text, encoding="utf-8")


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else "")
    ap.add_argument("--vault", required=True, help="Path to the vault directory")
    ap.add_argument("--apply", action="store_true",
                    help="Apply high-confidence proposals (updates articles)")
    ap.add_argument("--cache", action="store_true",
                    help="Write proposals to <project>/_cache/project-status-proposals.json")
    ap.add_argument("--threshold", default="high", choices=("high", "medium", "low"),
                    help="Minimum confidence to auto-apply (default: high)")
    ap.add_argument("--today", default=None,
                    help="Override today's date (YYYY-MM-DD), for testing")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"ERROR: vault not found: {vault}", file=sys.stderr)
        return 1

    today = _parse_date(args.today) if args.today else date.today()

    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    threshold = confidence_rank[args.threshold]

    projects = collect_projects(vault)
    proposals: list[dict[str, Any]] = []

    for p in projects:
        signals = compute_signals(p, vault, today)
        proposal = propose_status(p, signals)
        entry = {
            "path": p["rel_path"],
            "slug": p["slug"],
            "title": p["fm"].get("title", p["slug"]),
            "current_status": signals["current_status"],
            "last_activity": signals["last_activity"].isoformat() if signals["last_activity"] else None,
            "days_since_activity": signals["days_since_activity"],
            "episodes_count": signals["episodes_count"],
            "work_log_count": signals["work_log_count"],
            "kinds_30d": dict(signals["kinds_30d"]),
            "proposal": proposal,
            "applied": False,
        }
        if proposal and args.apply and confidence_rank[proposal["confidence"]] >= threshold:
            try:
                apply_proposal(p, proposal, today)
                entry["applied"] = True
            except Exception as e:
                entry["apply_error"] = str(e)
        proposals.append(entry)

    # Report
    any_proposed = sum(1 for e in proposals if e["proposal"])
    any_applied = sum(1 for e in proposals if e["applied"])
    print(f"Projects scanned: {len(proposals)}")
    print(f"Proposals:        {any_proposed}")
    if args.apply:
        print(f"Applied:          {any_applied} (threshold ≥ {args.threshold})")
    print()
    for e in proposals:
        prop = e["proposal"]
        if prop:
            tag = "✓ APPLIED" if e["applied"] else "  propose"
            print(f"{tag} {e['slug']}: {e['current_status']} → {prop['new_status']} "
                  f"[{prop['confidence']}] — {prop['reason']}")
        else:
            print(f"  no change {e['slug']}: {e['current_status']} "
                  f"({e['days_since_activity']}d since activity)")

    if args.cache:
        out_path = cache_path(vault)
        out_path.write_text(json.dumps({
            "generated": datetime.now().isoformat(timespec="seconds"),
            "today": today.isoformat(),
            "threshold": args.threshold,
            "apply": bool(args.apply),
            "proposals": proposals,
        }, indent=2, default=str), encoding="utf-8")
        print(f"\nCache written: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
