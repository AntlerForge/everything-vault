#!/usr/bin/env python3


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


"""
Everything Vault — Query Tool (v2)

Searches the vault and returns matching articles and episodes.

Usage:
    python3 query.py --question "When does my car insurance renew?"
    python3 query.py --keyword vnc
    python3 query.py --domain projects
    python3 query.py --episodes --question "kitchen renovation"
    python3 query.py --episodes --date-from 2026-01-01 --date-to 2026-06-30
    python3 query.py --structured --field renewal_date --within-days 90
    python3 query.py --stale --days 180
    python3 query.py --core
"""

import argparse
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


# ─── Shared frontmatter parser ─────────────────────────────────────────────

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
        fm = _simple_yaml_parse(fm_text)
    return fm, body


def _simple_yaml_parse(text):
    result = {}
    current_list = None
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("- "):
            item = line.strip().lstrip("- ").strip()
            if current_list is not None:
                current_list.append(item)
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "" or val == "|" or val == ">":
                current_list = []
                result[key] = current_list
            elif val.startswith("[") and val.endswith("]"):
                items = [i.strip().strip("'\"") for i in val[1:-1].split(",") if i.strip()]
                result[key] = items
                current_list = None
            else:
                result[key] = val.strip("\"'")
                current_list = None
    return result


# ─── Core memory ────────────────────────────────────────────────────────────

def load_core(vault_path):
    """Load all files from vault/core/ and return their contents."""
    vault = Path(vault_path)
    core_dir = vault / "core"
    if not core_dir.exists():
        print("No core/ directory found in vault.")
        return []
    results = []
    for md_file in sorted(core_dir.glob("*.md")):
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            results.append({
                "path": str(md_file.relative_to(vault)),
                "title": fm.get("title", md_file.stem),
                "body": body,
            })
        except Exception:
            continue
    return results


# ─── Search functions ────────────────────────────────────────────────────────

def load_all_articles(vault_path, include_episodes=True):
    """Load all articles from the vault."""
    vault = Path(vault_path)
    articles = []
    if not vault.exists():
        return articles
    for md_file in vault.rglob("*.md"):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            fm["_path"] = str(md_file.relative_to(vault))
            fm["_body"] = body
            fm["_full_path"] = str(md_file)

            ot = fm.get("object_type", "article")
            if not include_episodes and ot == "episode":
                continue
            articles.append(fm)
        except Exception:
            continue
    return articles


def load_episodes(vault_path):
    """Load only episode records."""
    vault = Path(vault_path)
    episodes_dir = vault / "episodes"
    episodes = []
    if not episodes_dir.exists():
        return episodes
    for md_file in episodes_dir.rglob("*.md"):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            fm["_path"] = str(md_file.relative_to(vault))
            fm["_body"] = body
            episodes.append(fm)
        except Exception:
            continue
    # Sort by date descending
    episodes.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    return episodes


def score_article(article, query_words):
    """Score an article against query words. Higher = more relevant."""
    score = 0
    title = str(article.get("title", "")).lower()
    domains = article.get("domains", [])
    if isinstance(domains, str):
        domains = [domains]
    tags = article.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    provider = str(article.get("provider", "")).lower()
    body = article.get("_body", "").lower()
    # v2: also search entity_refs and article_refs
    entity_refs = article.get("entity_refs", [])
    if isinstance(entity_refs, str):
        entity_refs = [entity_refs]
    article_refs = article.get("article_refs", [])
    if isinstance(article_refs, str):
        article_refs = [article_refs]

    # v2.1: also search relationships[].ref
    relationships = article.get("relationships", [])
    if isinstance(relationships, list):
        rel_refs = [r.get("ref", "") for r in relationships if isinstance(r, dict)]
        rel_types = [r.get("type", "") for r in relationships if isinstance(r, dict)]
    else:
        rel_refs = []
        rel_types = []

    for word in query_words:
        w = word.lower()
        if len(w) < 3:
            continue
        if w in title:
            score += 4
        if any(w in d for d in domains):
            score += 3
        if any(w in t for t in tags):
            score += 3
        if w in provider:
            score += 2
        if any(w in r for r in entity_refs):
            score += 2
        if any(w in r for r in article_refs):
            score += 2
        if any(w in r for r in rel_refs):
            score += 2
            # Bonus for strong relationship types
            for ref, rtype in zip(rel_refs, rel_types):
                if w in ref and rtype in ("supports", "implements"):
                    score += 1
        if w in body:
            score += 1

    return score


def keyword_search(vault_path, question, include_episodes=True):
    """Full-text + frontmatter keyword search."""
    query_words = re.sub(r"[^\w\s]", "", question.lower()).split()
    stop = {"what", "when", "where", "who", "how", "does", "is", "are", "my",
            "the", "a", "an", "i", "do", "did", "was", "be", "have", "has",
            "for", "with", "in", "on", "at", "to", "of", "and", "or", "it"}
    query_words = [w for w in query_words if w not in stop and len(w) >= 3]

    articles = load_all_articles(vault_path, include_episodes=include_episodes)
    scored = []
    for a in articles:
        s = score_article(a, query_words)
        if s > 0:
            scored.append((s, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:8]]


def episode_search(vault_path, question=None, date_from=None, date_to=None, entity=None):
    """Search episodes by keyword, date range, or entity."""
    episodes = load_episodes(vault_path)
    results = []

    for ep in episodes:
        ep_date = str(ep.get("date", ""))

        # Date range filter
        if date_from and ep_date < date_from:
            continue
        if date_to and ep_date > date_to:
            continue

        # Entity filter
        if entity:
            refs = ep.get("entity_refs", [])
            actors = ep.get("actors", [])
            if isinstance(refs, str):
                refs = [refs]
            if isinstance(actors, str):
                actors = [actors]
            all_entities = [r.lower() for r in refs + actors]
            if entity.lower() not in all_entities:
                continue

        # Keyword filter
        if question:
            query_words = re.sub(r"[^\w\s]", "", question.lower()).split()
            stop = {"what", "when", "where", "who", "how", "does", "is", "are", "my",
                    "the", "a", "an", "i", "do", "did", "was", "be", "have", "has",
                    "for", "with", "in", "on", "at", "to", "of", "and", "or", "it"}
            query_words = [w for w in query_words if w not in stop and len(w) >= 3]
            if query_words:
                s = score_article(ep, query_words)
                if s == 0:
                    continue

        results.append(ep)

    return results


def domain_search(vault_path, domain):
    """Return all articles in a given domain."""
    articles = load_all_articles(vault_path)
    results = []
    for a in articles:
        domains = a.get("domains", [])
        if isinstance(domains, str):
            domains = [domains]
        if domain in domains:
            results.append(a)
    return results


def structured_search(vault_path, field, within_days=None, max_cost=None, min_cost=None):
    """Search by structured frontmatter fields."""
    articles = load_all_articles(vault_path, include_episodes=False)
    results = []
    today = date.today()

    for a in articles:
        val = a.get(field)
        if val is None or val == "null":
            continue

        if field == "renewal_date" and within_days is not None:
            try:
                rd = datetime.strptime(str(val), "%Y-%m-%d").date()
                delta = (rd - today).days
                if 0 <= delta <= within_days or delta < 0:
                    a["_renewal_delta"] = delta
                    results.append(a)
            except ValueError:
                continue
        elif field == "cost":
            try:
                cost_val = float(val)
                if min_cost is not None and cost_val < min_cost:
                    continue
                if max_cost is not None and cost_val > max_cost:
                    continue
                results.append(a)
            except (ValueError, TypeError):
                continue
        else:
            results.append(a)

    return results


def stale_search(vault_path, days=180):
    """Find articles not verified within the given number of days."""
    articles = load_all_articles(vault_path, include_episodes=False)
    results = []
    cutoff = date.today() - timedelta(days=days)

    for a in articles:
        lv = a.get("last_verified")
        if not lv or lv == "null":
            a["_stale_reason"] = "never verified"
            results.append(a)
            continue
        try:
            lv_date = datetime.strptime(str(lv), "%Y-%m-%d").date()
            if lv_date < cutoff:
                a["_stale_reason"] = f"last verified {lv}"
                results.append(a)
        except ValueError:
            continue

    for a in articles:
        rd = a.get("renewal_date")
        if rd and rd != "null":
            try:
                rd_date = datetime.strptime(str(rd), "%Y-%m-%d").date()
                if rd_date < date.today():
                    a["_stale_reason"] = f"renewal date {rd} has passed"
                    if a not in results:
                        results.append(a)
            except ValueError:
                continue

    return results


# ─── Output formatting ──────────────────────────────────────────────────────

def format_article_summary(a, include_body=False):
    """Format an article for display."""
    lines = []
    title = a.get("title", a.get("_path", "Unknown"))
    domains = a.get("domains", [])
    if isinstance(domains, str):
        domains = [domains]
    confidence = a.get("confidence", "unknown")
    last_verified = a.get("last_verified", "unknown")
    renewal = a.get("renewal_date")
    cost = a.get("cost")
    provider = a.get("provider")
    ot = a.get("object_type", "article")
    sensitivity = a.get("sensitivity", "normal")

    type_badge = f" [{ot}]" if ot != "article" else ""
    sens_badge = f" 🔒" if sensitivity not in ("normal", None) else ""

    lines.append(f"## {title}{type_badge}{sens_badge}")
    lines.append(f"Domains: {', '.join(domains)} | Confidence: {confidence} | Last verified: {last_verified}")

    if ot == "episode":
        ep_date = a.get("date", "unknown")
        actors = a.get("actors", [])
        if isinstance(actors, str):
            actors = [actors]
        lines.append(f"Date: {ep_date} | Actors: {', '.join(actors) if actors else 'unknown'}")
        outcomes = a.get("outcomes", [])
        if outcomes:
            if isinstance(outcomes, str):
                outcomes = [outcomes]
            lines.append(f"Outcomes: {'; '.join(outcomes)}")
        follow_up = a.get("follow_up")
        if follow_up and follow_up != "null":
            lines.append(f"Follow-up: {follow_up}")

    if provider:
        lines.append(f"Provider: {provider}")
    if renewal and renewal != "null":
        today = date.today()
        try:
            rd = datetime.strptime(str(renewal), "%Y-%m-%d").date()
            delta = (rd - today).days
            if delta < 0:
                lines.append(f"⚠ Renewal date: {renewal} (OVERDUE by {abs(delta)} days)")
            elif delta <= 90:
                lines.append(f"⚡ Renewal date: {renewal} (in {delta} days)")
            else:
                lines.append(f"Renewal date: {renewal}")
        except ValueError:
            lines.append(f"Renewal date: {renewal}")
    if cost and cost != "null":
        lines.append(f"Cost: £{cost}/year")
    # v2.1: typed relationships
    relationships = a.get("relationships", [])
    if relationships and isinstance(relationships, list):
        rel_parts = []
        for r in relationships:
            if isinstance(r, dict) and r.get("ref") and r.get("type"):
                rel_parts.append(f"{r['type']}: {r['ref']}")
        if rel_parts:
            lines.append(f"🔗 {' | '.join(rel_parts)}")

    if a.get("_path"):
        lines.append(f"Article: {a['_path']}")
    if include_body and a.get("_body"):
        lines.append("")
        lines.append(a["_body"][:500] + ("..." if len(a["_body"]) > 500 else ""))
    return "\n".join(lines)


# ─── CLI entry point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Everything Vault — Query Tool (v2)")
    parser.add_argument("--vault", default=_find_vault_default())
    parser.add_argument("--question", help="Natural language question")
    parser.add_argument("--keyword", help="Keyword search")
    parser.add_argument("--domain", help="Search within a specific domain")
    parser.add_argument("--episodes", action="store_true", help="Search episodes only")
    parser.add_argument("--date-from", help="Episode date range start (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="Episode date range end (YYYY-MM-DD)")
    parser.add_argument("--entity", help="Filter episodes by entity slug")
    parser.add_argument("--core", action="store_true", help="Load and display core memory")
    parser.add_argument("--structured", action="store_true", help="Structured field search")
    parser.add_argument("--field", help="Frontmatter field to search")
    parser.add_argument("--within-days", type=int, help="For renewal_date: window in days")
    parser.add_argument("--min-cost", type=float, help="Minimum cost filter")
    parser.add_argument("--max-cost", type=float, help="Maximum cost filter")
    parser.add_argument("--stale", action="store_true", help="Find stale articles")
    parser.add_argument("--days", type=int, default=180, help="Staleness threshold")
    parser.add_argument("--full", action="store_true", help="Show full article body")

    args = parser.parse_args()

    if args.core:
        results = load_core(args.vault)
        if not results:
            print("No core memory files found.")
        else:
            print(f"Core memory ({len(results)} files):\n")
            for r in results:
                print(f"### {r['title']} ({r['path']})")
                print(r["body"][:500])
                print()

    elif args.episodes:
        results = episode_search(args.vault,
                                 question=args.question,
                                 date_from=args.date_from,
                                 date_to=args.date_to,
                                 entity=args.entity)
        if not results:
            q = args.question or "given criteria"
            print(f"No episodes found for: {q}")
        else:
            print(f"Found {len(results)} episode(s):\n")
            for ep in results:
                print(format_article_summary(ep, include_body=args.full))
                print()

    elif args.question or args.keyword:
        q = args.question or args.keyword
        results = keyword_search(args.vault, q)
        if not results:
            print(f"No results found for: {q}")
            print("The vault may not contain information on this topic yet.")
        else:
            print(f"Found {len(results)} result(s) for: {q}\n")
            for a in results:
                print(format_article_summary(a, include_body=args.full))
                print()

    elif args.domain:
        results = domain_search(args.vault, args.domain)
        if not results:
            print(f"No articles found in domain: {args.domain}")
        else:
            print(f"Articles in domain '{args.domain}' ({len(results)} found):\n")
            for a in results:
                print(format_article_summary(a))
                print()

    elif args.structured:
        if not args.field:
            print("ERROR: --field required with --structured", file=sys.stderr)
            sys.exit(1)
        results = structured_search(args.vault, args.field,
                                    within_days=args.within_days,
                                    min_cost=args.min_cost,
                                    max_cost=args.max_cost)
        if not results:
            print(f"No articles found with field '{args.field}' matching criteria.")
        else:
            print(f"Structured query on '{args.field}': {len(results)} result(s)\n")
            for a in results:
                print(format_article_summary(a, include_body=args.full))
                if a.get("_renewal_delta") is not None:
                    delta = a["_renewal_delta"]
                    if delta < 0:
                        print(f"  → OVERDUE by {abs(delta)} days")
                    else:
                        print(f"  → Due in {delta} days")
                print()

    elif args.stale:
        results = stale_search(args.vault, days=args.days)
        if not results:
            print(f"No stale articles found (threshold: {args.days} days).")
        else:
            print(f"Stale articles ({len(results)} found, threshold: {args.days} days):\n")
            for a in results:
                print(format_article_summary(a))
                if a.get("_stale_reason"):
                    print(f"  → {a['_stale_reason']}")
                print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
