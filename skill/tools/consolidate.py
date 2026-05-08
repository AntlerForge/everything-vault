#!/usr/bin/env python3

"""
Everything Vault — Consolidation Tool (v2.1)

Runs synthesis checks across the vault to surface patterns, gaps, and connections
that individual ingests and queries miss.

Usage:
    python3 consolidate.py --vault <path> --check all
    python3 consolidate.py --vault <path> --check convergence
    python3 consolidate.py --vault <path> --check orphan-episodes
    python3 consolidate.py --vault <path> --check resolved-tasks
    python3 consolidate.py --vault <path> --check missing-links
    python3 consolidate.py --vault <path> --check concept-stale
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_vault_default():
    """Auto-detect vault path. Checks EV_VAULT_PATH, then common locations."""
    import glob as _glob
    env = os.environ.get("EV_VAULT_PATH")
    if env:
        return os.path.expanduser(env)
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Documents", "everything-vault", "vault"),
        os.path.join(home, "everything-vault", "vault"),
        os.path.abspath("vault"),
        os.path.abspath("../vault"),
    ]
    # Also probe sandboxed cloud-IDE mounts (Cowork, GitHub Codespaces, etc.)
    candidates.extend(sorted(_glob.glob("/sessions/*/mnt/everything-vault/vault")))
    candidates.extend(sorted(_glob.glob("/sessions/*/mnt/*/everything-vault/vault")))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


# Skip files inside any underscore-prefixed folder ("_for-deletion/", "_archive/" etc.)
# so soft-deleted content stays out of indexing, queries, and dashboard.
def _is_under_dot_or_underscore(path, vault_root):
    try:
        parts = path.relative_to(vault_root).parts
    except ValueError:
        return True  # outside vault
    return any(p.startswith("_") or p.startswith(".") for p in parts[:-1])

def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    if yaml:
        try:
            fm = yaml.safe_load(fm_text) or {}
        except Exception:
            fm = {}
    else:
        fm = {}
        current_list = None
        current_key = None
        current_dict = None
        for line in fm_text.splitlines():
            if not line.strip():
                continue
            # Handle indented dict items (relationships)
            if line.startswith("    - ") or line.startswith("    "):
                if current_dict is not None:
                    k2, _, v2 = line.strip().partition(":")
                    current_dict[k2.strip()] = v2.strip().strip("\"'")
                continue
            if line.startswith("  - "):
                val = line.strip().lstrip("- ").strip()
                if current_list is not None:
                    # Could be start of a dict item
                    if ":" in val and not val.startswith('"'):
                        k2, _, v2 = val.partition(":")
                        current_dict = {k2.strip(): v2.strip().strip("\"'")}
                        current_list.append(current_dict)
                    else:
                        current_dict = None
                        current_list.append(val.strip("\"'"))
                continue
            current_dict = None
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if v == "" or v in ("|", ">"):
                    current_list = []
                    fm[k] = current_list
                    current_key = k
                elif v.startswith("[") and v.endswith("]"):
                    fm[k] = [i.strip().strip("'\"") for i in v[1:-1].split(",") if i.strip()]
                    current_list = None
                else:
                    fm[k] = v.strip("\"'")
                    current_list = None
    return fm, body


def load_articles(vault_path, domain_slug):
    """Load all articles from a domain, returning list of (path, fm, body)."""
    domain_dir = Path(vault_path) / domain_slug
    if not domain_dir.exists():
        return []
    results = []
    for md_file in sorted(domain_dir.glob("*.md")):
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            results.append((md_file, fm, body))
        except Exception:
            continue
    return results


def load_all_articles(vault_path):
    """Load all articles across all domains."""
    vault = Path(vault_path)
    results = []
    for d in vault.iterdir():
        if not d.is_dir() or d.name.startswith("_") or d.name == "episodes":
            continue
        for md_file in sorted(d.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            try:
                text = md_file.read_text(encoding="utf-8")
                fm, body = parse_frontmatter(text)
                results.append((md_file, fm, body))
            except Exception:
                continue
    return results


def load_episodes(vault_path, days=30):
    """Load episodes from the last N days."""
    vault = Path(vault_path)
    episodes_dir = vault / "episodes"
    if not episodes_dir.exists():
        return []
    cutoff = date.today() - timedelta(days=days)
    results = []
    for md_file in episodes_dir.rglob("*.md"):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            ep_date_raw = fm.get("date", "")
            try:
                if isinstance(ep_date_raw, date):
                    ep_date = ep_date_raw
                else:
                    ep_date = datetime.strptime(str(ep_date_raw), "%Y-%m-%d").date()
                if ep_date >= cutoff:
                    results.append((md_file, fm, body))
            except ValueError:
                # Include if we can't parse the date (might be recent)
                results.append((md_file, fm, body))
        except Exception:
            continue
    return results


def get_related_refs(fm):
    """Extract all ref slugs from related and relationships fields."""
    refs = set()
    related = fm.get("related") or []
    if isinstance(related, list):
        for r in related:
            if r:
                refs.add(str(r).strip())
    relationships = fm.get("relationships") or []
    if isinstance(relationships, list):
        for r in relationships:
            if isinstance(r, dict) and r.get("ref"):
                refs.add(str(r["ref"]).strip())
    return refs


def get_slug(fm, path):
    """Get article slug from frontmatter id or filename stem."""
    return fm.get("id") or fm.get("slug") or Path(path).stem


def parse_date_field(val):
    """Parse a date field to a date object, or None."""
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Check 1: Convergence
# ---------------------------------------------------------------------------

def convergence_check(vault_path):
    """
    Find concept pairs with significant tag/entity overlap that aren't cross-linked.
    Score: shared tags (1 each) + shared entity_refs (2 each) + shared non-concepts domains (1 each)
    Flag pairs with score >= 3 that aren't already linked.
    """
    articles = load_articles(vault_path, "concepts")
    if not articles:
        return []

    findings = []

    for i, (path_a, fm_a, _) in enumerate(articles):
        for j, (path_b, fm_b, _) in enumerate(articles):
            if j <= i:
                continue

            slug_a = get_slug(fm_a, path_a)
            slug_b = get_slug(fm_b, path_b)

            # Check if already linked
            refs_a = get_related_refs(fm_a)
            refs_b = get_related_refs(fm_b)
            if slug_b in refs_a or slug_a in refs_b:
                continue

            # Compute overlap score
            tags_a = set(fm_a.get("tags") or [])
            tags_b = set(fm_b.get("tags") or [])
            shared_tags = tags_a & tags_b

            entities_a = set(fm_a.get("entity_refs") or [])
            entities_b = set(fm_b.get("entity_refs") or [])
            shared_entities = entities_a & entities_b

            domains_a = set(d for d in (fm_a.get("domains") or []) if d != "concepts")
            domains_b = set(d for d in (fm_b.get("domains") or []) if d != "concepts")
            shared_domains = domains_a & domains_b

            score = len(shared_tags) + (len(shared_entities) * 2) + len(shared_domains)

            if score >= 3:
                findings.append({
                    "a_slug": slug_a,
                    "a_title": fm_a.get("title", slug_a),
                    "b_slug": slug_b,
                    "b_title": fm_b.get("title", slug_b),
                    "score": score,
                    "shared_tags": sorted(shared_tags),
                    "shared_entities": sorted(shared_entities),
                    "shared_domains": sorted(shared_domains),
                })

    findings.sort(key=lambda x: x["score"], reverse=True)
    return findings


# ---------------------------------------------------------------------------
# Check 2: Orphan Episodes
# ---------------------------------------------------------------------------

def orphan_episodes_check(vault_path, days=30):
    """
    Find recent episodes with no article_refs.
    Also check if there are entity matches to suggest possible links.
    """
    episodes = load_episodes(vault_path, days=days)
    all_articles = load_all_articles(vault_path)

    # Build entity -> article map
    entity_to_articles = defaultdict(list)
    for path, fm, _ in all_articles:
        for entity in (fm.get("entity_refs") or []):
            entity_to_articles[entity].append({
                "slug": get_slug(fm, path),
                "title": fm.get("title", Path(path).stem),
            })

    findings = []
    for path, fm, body in episodes:
        article_refs = fm.get("article_refs") or []
        if isinstance(article_refs, str):
            article_refs = [article_refs]

        if not article_refs or article_refs == []:
            # Try to suggest related articles via entity overlap
            ep_entities = set(fm.get("entity_refs") or [])
            ep_actors = set(fm.get("actors") or [])
            all_mentioned = ep_entities | ep_actors

            suggestions = {}
            for entity in all_mentioned:
                for art in entity_to_articles.get(entity, []):
                    slug = art["slug"]
                    if slug not in suggestions:
                        suggestions[slug] = {"title": art["title"], "via": []}
                    suggestions[slug]["via"].append(entity)

            findings.append({
                "path": str(path.relative_to(Path(vault_path) / "episodes") if
                           str(path).startswith(str(Path(vault_path) / "episodes")) else path),
                "title": fm.get("title", path.stem),
                "date": str(fm.get("date", "unknown")),
                "suggestions": [
                    {"slug": s, "title": v["title"], "via": v["via"]}
                    for s, v in suggestions.items()
                ][:5],
            })

    return findings


# ---------------------------------------------------------------------------
# Check 3: Resolved Tasks
# ---------------------------------------------------------------------------

def resolved_tasks_check(vault_path):
    """
    Parse tasks/todo-list.md for active tasks.
    Check if the source article was recently updated and contains resolution keywords.
    """
    vault = Path(vault_path)
    todo_path = vault / "tasks" / "todo-list.md"
    if not todo_path.exists():
        return []

    todo_text = todo_path.read_text(encoding="utf-8")

    # Find Active Tasks table rows: | T-ID | Priority | Task | Source Article | Notes |
    # Look for table rows after "Active Tasks" heading
    active_section = re.search(r"#+\s+Active Tasks.*?(?=#+\s|\Z)", todo_text, re.DOTALL | re.IGNORECASE)
    if not active_section:
        return []

    table_rows = re.findall(
        r"\|\s*(T-\d+)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|",
        active_section.group(0)
    )

    resolution_keywords = ["✅", "completed", "cancelled", "done", "resolved", "closed", "fixed"]
    findings = []
    today = date.today()
    cutoff = today - timedelta(days=14)  # Updated in last 2 weeks = possibly resolved

    for row in table_rows:
        task_id, priority, task_desc, source_article, notes = [r.strip() for r in row]
        if not task_id.startswith("T-"):
            continue

        # Skip header rows
        if "Priority" in priority or "Task" in task_desc:
            continue

        # Look for source article
        source_slug = source_article.strip().strip("[]").strip()
        if not source_slug:
            continue

        # Find the article file
        article_path = None
        for domain_dir in vault.iterdir():
            if not domain_dir.is_dir() or domain_dir.name.startswith("_") or domain_dir.name == "episodes":
                continue
            candidate = domain_dir / f"{source_slug}.md"
            if candidate.exists():
                article_path = candidate
                break

        if not article_path:
            continue

        try:
            text = article_path.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            last_updated = parse_date_field(fm.get("last_updated"))

            if last_updated and last_updated >= cutoff:
                # Check for resolution keywords in body
                body_lower = body.lower()
                found_keywords = [kw for kw in resolution_keywords if kw.lower() in body_lower]
                if found_keywords:
                    findings.append({
                        "task_id": task_id,
                        "task_desc": task_desc,
                        "priority": priority,
                        "source_slug": source_slug,
                        "source_title": fm.get("title", source_slug),
                        "last_updated": str(last_updated),
                        "keywords_found": found_keywords,
                    })
        except Exception:
            continue

    return findings


# ---------------------------------------------------------------------------
# Check 4: Missing Links
# ---------------------------------------------------------------------------

def missing_links_check(vault_path, min_co_occurrences=2):
    """
    Build co-occurrence matrix from episodes' article_refs and entity_refs.
    Flag article pairs that co-occur >= min_co_occurrences times but aren't cross-linked.
    """
    episodes = load_episodes(vault_path, days=90)  # Look back 90 days
    all_articles = load_all_articles(vault_path)

    # Build slug -> (path, fm) map
    slug_to_fm = {}
    for path, fm, _ in all_articles:
        slug = get_slug(fm, path)
        slug_to_fm[slug] = (path, fm)

    # Build co-occurrence counts
    co_occur = defaultdict(int)
    for _, fm, _ in episodes:
        refs = list(fm.get("article_refs") or [])
        if isinstance(refs, str):
            refs = [refs]

        # Deduplicate within this episode
        refs = list(set(str(r).strip() for r in refs if r))

        for i, a in enumerate(refs):
            for b in refs[i + 1:]:
                key = tuple(sorted([a, b]))
                co_occur[key] += 1

    findings = []
    for (slug_a, slug_b), count in co_occur.items():
        if count < min_co_occurrences:
            continue

        if slug_a not in slug_to_fm or slug_b not in slug_to_fm:
            continue

        _, fm_a = slug_to_fm[slug_a]
        _, fm_b = slug_to_fm[slug_b]

        refs_a = get_related_refs(fm_a)
        refs_b = get_related_refs(fm_b)

        if slug_b in refs_a or slug_a in refs_b:
            continue  # Already linked

        findings.append({
            "a_slug": slug_a,
            "a_title": fm_a.get("title", slug_a),
            "b_slug": slug_b,
            "b_title": fm_b.get("title", slug_b),
            "co_occurrences": count,
        })

    findings.sort(key=lambda x: x["co_occurrences"], reverse=True)
    return findings


# ---------------------------------------------------------------------------
# Check 5: Concept Staleness
# ---------------------------------------------------------------------------

def concept_stale_check(vault_path, stale_days=30):
    """
    Find concepts in the `ideas` slot that haven't been touched in stale_days.
    Sort by staleness (most stale first).
    Returns top 5 to avoid overwhelming output.
    (Legacy statuses seed/developing are accepted for backwards compat.)
    """
    articles = load_articles(vault_path, "concepts")
    eligible_tiers = {"insight", "concept", "idea"}
    eligible_statuses = {"ideas", "seed", "developing"}  # last two are legacy

    today = date.today()
    findings = []

    for path, fm, _ in articles:
        tier = (fm.get("tier") or "").lower().strip()
        status = (fm.get("status") or "").lower().strip()

        if tier not in eligible_tiers:
            continue
        if status not in eligible_statuses:
            continue

        last_updated = parse_date_field(fm.get("last_updated"))
        if last_updated is None:
            days_stale = 9999  # Unknown — treat as very stale
        else:
            days_stale = (today - last_updated).days

        if days_stale >= stale_days:
            findings.append({
                "slug": get_slug(fm, path),
                "title": fm.get("title", path.stem),
                "tier": tier,
                "status": status,
                "last_updated": str(last_updated) if last_updated else "unknown",
                "days_stale": days_stale,
            })

    findings.sort(key=lambda x: x["days_stale"], reverse=True)
    return findings[:5]  # Only top 5 — don't overwhelm


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

def print_convergence(findings):
    if not findings:
        print("  ✓ No converging concept pairs found.")
        return
    print(f"  ⚡ {len(findings)} converging concept pair(s):\n")
    for f in findings:
        print(f"  [{f['a_title']}] ↔ [{f['b_title']}]  (score: {f['score']})")
        if f["shared_tags"]:
            print(f"    Tags: {', '.join(f['shared_tags'])}")
        if f["shared_entities"]:
            print(f"    Entities: {', '.join(f['shared_entities'])}")
        if f["shared_domains"]:
            print(f"    Domains: {', '.join(f['shared_domains'])}")
        print()


def print_orphan_episodes(findings):
    if not findings:
        print("  ✓ No orphan episodes found (all recent episodes are linked).")
        return
    print(f"  🔗 {len(findings)} unlinked episode(s):\n")
    for f in findings:
        print(f"  [{f['date']}] {f['title']}")
        if f["suggestions"]:
            print("    Possible links:")
            for s in f["suggestions"]:
                print(f"    → {s['title']} (via: {', '.join(s['via'])})")
        else:
            print("    No obvious article matches found.")
        print()


def print_resolved_tasks(findings):
    if not findings:
        print("  ✓ No potentially resolved tasks found.")
        return
    print(f"  ✅ {len(findings)} task(s) that may be resolved:\n")
    for f in findings:
        print(f"  {f['task_id']} [{f['priority']}] — {f['task_desc']}")
        print(f"    Source article: {f['source_title']} (updated {f['last_updated']})")
        print(f"    Keywords found: {', '.join(f['keywords_found'])}")
        print()


def print_missing_links(findings):
    if not findings:
        print("  ✓ No missing cross-links found.")
        return
    print(f"  🔍 {len(findings)} article pair(s) that appear together but aren't linked:\n")
    for f in findings:
        print(f"  [{f['a_title']}] + [{f['b_title']}]  ({f['co_occurrences']}x in episodes)")
    print()


def print_concept_stale(findings):
    if not findings:
        print("  ✓ No stale concepts found.")
        return
    print(f"  🌱 {len(findings)} stale concept(s) worth revisiting:\n")
    for f in findings:
        days = f["days_stale"]
        age = f"{days} days" if days < 9999 else "unknown age"
        print(f"  [{f['title']}] — {f['tier']} / {f['status']} — stale for {age}")
        print(f"    Last updated: {f['last_updated']}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECK_MAP = {
    "convergence": (convergence_check, print_convergence, "Convergence"),
    "orphan-episodes": (orphan_episodes_check, print_orphan_episodes, "Orphan Episodes"),
    "resolved-tasks": (resolved_tasks_check, print_resolved_tasks, "Resolved Tasks"),
    "missing-links": (missing_links_check, print_missing_links, "Missing Links"),
    "concept-stale": (concept_stale_check, print_concept_stale, "Stale Concepts"),
}


CACHE_FILENAME = "_consolidation-cache.json"  # legacy, kept for fallback reads


def cache_path(vault_path):
    """Return the path to write the consolidation cache. Always returns the
    sibling location <project>/_cache/consolidation.json so new writes never
    land back inside vault/. The legacy in-vault location is read-only — see
    load_cache() for the read-side fallback."""
    vault = Path(vault_path).expanduser().resolve()
    sibling_cache = vault.parent / "_cache" / "consolidation.json"
    sibling_cache.parent.mkdir(parents=True, exist_ok=True)
    return sibling_cache


def load_cache(vault_path):
    """Load cached consolidation results if they exist. Returns dict or None.
    Reads sibling location first, falls back to legacy in-vault location."""
    import json
    vault = Path(vault_path).expanduser().resolve()
    sibling_cache = vault.parent / "_cache" / "consolidation.json"
    legacy_cache = vault / CACHE_FILENAME
    for path in (sibling_cache, legacy_cache):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


def save_cache(vault_path, results):
    """Save consolidation results to cache file in <project>/_cache/.
    Always writes to the new sibling location; never writes to legacy."""
    import json
    path = cache_path(vault_path)
    # cache_path() guarantees the parent dir exists, but be defensive
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated": date.today().isoformat(),
        "results": results,
    }
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return str(path)


def main():
    parser = argparse.ArgumentParser(description="Everything Vault — Consolidation Tool (v2.1)")
    parser.add_argument("--vault", default=_find_vault_default(), help="Path to vault directory")
    parser.add_argument(
        "--check",
        default="all",
        choices=list(CHECK_MAP.keys()) + ["all"],
        help="Which check to run (default: all)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to <project>/_cache/consolidation.json for later review",
    )
    parser.add_argument(
        "--load-cache",
        action="store_true",
        help="Print cached results instead of re-running checks",
    )
    args = parser.parse_args()

    if not args.vault:
        print("ERROR: Could not find vault. Use --vault <path>", file=sys.stderr)
        sys.exit(1)

    vault_path = args.vault
    if not Path(vault_path).exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    # --load-cache: just print the cached results without re-running
    if args.load_cache:
        import json
        cache = load_cache(vault_path)
        if not cache:
            print("No cache found. Run with --save to generate one.")
            sys.exit(0)
        print(f"\nCached results from {cache['generated']}:\n")
        print(json.dumps(cache["results"], indent=2))
        sys.exit(0)

    checks_to_run = list(CHECK_MAP.keys()) if args.check == "all" else [args.check]
    total_findings = 0
    all_results = {}

    print(f"\n{'='*60}")
    print(f"Everything Vault — Consolidation Pass")
    print(f"Date: {date.today().isoformat()} | Vault: {vault_path}")
    print(f"{'='*60}\n")

    for check_name in checks_to_run:
        check_fn, print_fn, label = CHECK_MAP[check_name]
        print(f"── {label} ──")
        try:
            findings = check_fn(vault_path)
            print_fn(findings)
            total_findings += len(findings)
            all_results[check_name] = findings
        except Exception as e:
            print(f"  ERROR running {check_name}: {e}")
            all_results[check_name] = []
        print()

    print(f"{'='*60}")
    if total_findings == 0:
        print("Vault looks healthy — nothing to flag. 👍")
    else:
        print(f"{total_findings} finding(s) across {len(checks_to_run)} check(s).")

    if args.save:
        cache_path = save_cache(vault_path, all_results)
        print(f"Results saved to {cache_path}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
