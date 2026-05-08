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
Everything Vault — Ingest Tool (v2.1)

Handles creating and updating knowledge articles and episodes in the vault.

Usage:
    python3 ingest.py scan --vault <path> --query <text>
    python3 ingest.py write --vault <path> --path <article_path> --content-file <file>
    python3 ingest.py episode --vault <path> --date YYYY-MM-DD --title "What happened"
    python3 ingest.py list --vault <path> [--domain <slug>]
    python3 ingest.py ripple --vault <path> --source <relative_article_path>
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


# ─── Frontmatter helpers ────────────────────────────────────────────────────

# Skip files inside any underscore-prefixed folder ("_for-deletion/", "_archive/" etc.)
# so soft-deleted content stays out of indexing, queries, and dashboard.
def _is_under_dot_or_underscore(path, vault_root):
    try:
        parts = path.relative_to(vault_root).parts
    except ValueError:
        return True  # outside vault
    return any(p.startswith("_") or p.startswith(".") for p in parts[:-1])

def parse_frontmatter(text):
    """Extract YAML frontmatter from a markdown string."""
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
    """Minimal YAML parser for simple key: value and key: [list] structures."""
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


def render_frontmatter(fm):
    """Render a frontmatter dict back to YAML string."""
    lines = ["---"]
    for key, val in fm.items():
        if isinstance(val, list):
            if len(val) == 0:
                lines.append(f"{key}: []")
            elif all(isinstance(v, dict) for v in val):
                # List of dicts (e.g. relationships: [{ref: ..., type: ...}])
                lines.append(f"{key}:")
                for item in val:
                    first = True
                    for k, v in item.items():
                        prefix = "  - " if first else "    "
                        if isinstance(v, str) and any(c in v for c in ':#{}[]|>&*!,'):
                            lines.append(f'{prefix}{k}: "{v}"')
                        else:
                            lines.append(f"{prefix}{k}: {v}")
                        first = False
            elif all(isinstance(v, str) and len(v) < 40 and ',' not in v for v in val):
                # Inline short string lists
                items = ", ".join(str(v) for v in val)
                lines.append(f"{key}: [{items}]")
            else:
                lines.append(f"{key}:")
                for item in val:
                    lines.append(f"  - {item}")
        elif val is None:
            lines.append(f"{key}: null")
        else:
            if isinstance(val, str) and any(c in val for c in ':#{}[]|>&*!,'):
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines)


# ─── Article operations ─────────────────────────────────────────────────────

def scan_vault(vault_path, query_text):
    """Search for existing articles that might match the query."""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"ERROR: Vault not found at {vault_path}", file=sys.stderr)
        return []

    query_words = set(re.sub(r"[^\w\s]", "", query_text.lower()).split())
    results = []

    for md_file in vault.rglob("*.md"):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            title = fm.get("title", md_file.stem)
            domains = fm.get("domains", [])
            if isinstance(domains, str):
                domains = [domains]

            searchable = f"{title} {' '.join(fm.get('tags', []))} {body}".lower()
            searchable_words = set(re.sub(r"[^\w\s]", "", searchable).split())
            overlap = len(query_words & searchable_words)

            if overlap >= 2 or (query_words and any(w in searchable for w in query_words if len(w) > 4)):
                results.append({
                    "path": str(md_file.relative_to(vault)),
                    "title": title,
                    "domains": domains,
                    "object_type": fm.get("object_type", "article"),
                    "confidence": fm.get("confidence", "unknown"),
                    "last_verified": fm.get("last_verified", "unknown"),
                    "sensitivity": fm.get("sensitivity", "normal"),
                    "overlap_score": overlap,
                })
        except Exception:
            continue

    results.sort(key=lambda x: x["overlap_score"], reverse=True)
    return results[:10]


def write_article(vault_path, article_path, content):
    """Write (create or overwrite) a knowledge article."""
    vault = Path(vault_path)
    full_path = vault / article_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    print(f"OK: Written to {article_path}")
    return str(full_path)


def list_articles(vault_path, domain=None, object_type=None):
    """List all articles in the vault, optionally filtered."""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"ERROR: Vault not found at {vault_path}", file=sys.stderr)
        return []

    results = []
    for md_file in vault.rglob("*.md"):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            domains = fm.get("domains", [])
            if isinstance(domains, str):
                domains = [domains]
            if domain and domain not in domains:
                continue
            ot = fm.get("object_type", "article")
            if object_type and ot != object_type:
                continue
            results.append({
                "path": str(md_file.relative_to(vault)),
                "title": fm.get("title", md_file.stem),
                "domains": domains,
                "type": fm.get("type", "unknown"),
                "object_type": ot,
                "confidence": fm.get("confidence", "unknown"),
                "last_verified": fm.get("last_verified", "unknown"),
                "sensitivity": fm.get("sensitivity", "normal"),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["path"])
    return results


def make_article(title, domains, article_type, body,
                 tags=None, source="conversation", source_ref=None,
                 confidence="medium", renewal_date=None, cost=None, provider=None,
                 related=None, relationships=None, object_type="article", article_id=None,
                 sensitivity="normal", retrieval_default="searchable",
                 entity_refs=None, entity_type=None, aliases=None,
                 login_method=None, password_manager=None, login_email=None):
    """Construct a complete knowledge article string with frontmatter.

    relationships: list of dicts [{ref: slug, type: supports|extends|...}]
    """
    today = date.today().isoformat()
    if isinstance(domains, str):
        domains = [domains]

    fm = {"title": title, "domains": domains, "type": article_type}

    # v2 fields
    if object_type != "article":
        fm["object_type"] = object_type
    if article_id:
        fm["id"] = article_id
    if sensitivity != "normal":
        fm["sensitivity"] = sensitivity
    if retrieval_default != "searchable":
        fm["retrieval_default"] = retrieval_default
    if entity_refs:
        fm["entity_refs"] = entity_refs if isinstance(entity_refs, list) else [entity_refs]
    if entity_type:
        fm["entity_type"] = entity_type
    if aliases:
        fm["aliases"] = aliases if isinstance(aliases, list) else [aliases]

    # v2.1 typed relationships
    if relationships:
        fm["relationships"] = relationships if isinstance(relationships, list) else [relationships]

    # Standard fields
    if tags:
        fm["tags"] = tags if isinstance(tags, list) else [tags]
    if related:
        fm["related"] = related if isinstance(related, list) else [related]
    fm["source"] = source
    if source_ref:
        fm["source_ref"] = source_ref
    fm["created"] = today
    fm["last_updated"] = today
    fm["last_verified"] = today
    fm["confidence"] = confidence
    if renewal_date:
        fm["renewal_date"] = renewal_date
    if cost is not None:
        fm["cost"] = cost
    if provider:
        fm["provider"] = provider
    if login_method:
        fm["login_method"] = login_method
    if password_manager:
        fm["password_manager"] = password_manager
    if login_email:
        fm["login_email"] = login_email

    return f"{render_frontmatter(fm)}\n\n{body.strip()}\n"


def make_episode(title, episode_date, domains, body,
                 actors=None, entity_refs=None, article_refs=None,
                 source_refs=None, outcomes=None, follow_up=None,
                 tags=None, sensitivity="normal", confidence="medium",
                 source="conversation"):
    """Construct an episode record with frontmatter."""
    today = date.today().isoformat()
    if isinstance(domains, str):
        domains = [domains]
    if "episodes" not in domains:
        domains.append("episodes")

    fm = {
        "title": title,
        "domains": domains,
        "type": "log",
        "object_type": "episode",
        "date": episode_date,
    }
    if actors:
        fm["actors"] = actors if isinstance(actors, list) else [actors]
    if entity_refs:
        fm["entity_refs"] = entity_refs if isinstance(entity_refs, list) else [entity_refs]
    if article_refs:
        fm["article_refs"] = article_refs if isinstance(article_refs, list) else [article_refs]
    if source_refs:
        fm["source_refs"] = source_refs if isinstance(source_refs, list) else [source_refs]
    if outcomes:
        fm["outcomes"] = outcomes if isinstance(outcomes, list) else [outcomes]
    if follow_up:
        fm["follow_up"] = follow_up
    if tags:
        fm["tags"] = tags if isinstance(tags, list) else [tags]
    if sensitivity != "normal":
        fm["sensitivity"] = sensitivity
    fm["retrieval_default"] = "searchable"
    fm["source"] = source
    fm["created"] = today
    fm["confidence"] = confidence

    return f"{render_frontmatter(fm)}\n\n{body.strip()}\n"


def write_episode(vault_path, episode_date, title, content):
    """Write an episode to the correct year/quarter directory."""
    vault = Path(vault_path)
    year = episode_date[:4]
    month = int(episode_date[5:7])
    quarter = f"Q{(month - 1) // 3 + 1}"
    quarter_dir = f"episodes/{year}/{year}-{quarter}"

    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s]+", "-", slug).strip("-")[:60]
    filename = f"{episode_date}-{slug}.md"

    full_path = vault / quarter_dir / filename
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    print(f"OK: Episode written to {quarter_dir}/{filename}")
    return str(full_path)


# ─── Ripple scan ────────────────────────────────────────────────────────────

VALID_RELATIONSHIP_TYPES = {"supports", "extends", "supersedes", "contradicts",
                             "refines", "implements", "inspires"}


def ripple_scan(vault_path, source_article_path):
    """
    After writing an article or episode, scan for other articles potentially affected.

    Returns list of dicts: [{path, title, reason, strength}]
    strength: 'direct' | 'entity' | 'tag'
    """
    vault = Path(vault_path)
    source_full = vault / source_article_path
    if not source_full.exists():
        return []

    source_text = source_full.read_text(encoding="utf-8")
    src_fm, _ = parse_frontmatter(source_text)

    src_id = src_fm.get("id") or ""
    src_slug = Path(source_article_path).stem
    src_entity_refs = set(src_fm.get("entity_refs") or [])
    src_tags = set(src_fm.get("tags") or [])
    src_domains = set(src_fm.get("domains") or [])
    # Collect all slugs/ids by which source can be referenced
    src_identifiers = {src_slug}
    if src_id:
        src_identifiers.add(src_id)

    results = []
    for md_file in vault.rglob("*.md"):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name.startswith("_"):
            continue
        rel_path = str(md_file.relative_to(vault))
        if rel_path == source_article_path:
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
        except Exception:
            continue

        strength = None
        reasons = []

        # Check 1: direct reference (related, relationships[].ref, article_refs, entity_refs)
        other_related = set(fm.get("related") or [])
        other_article_refs = set(fm.get("article_refs") or [])
        other_entity_refs = set(fm.get("entity_refs") or [])
        other_rels = fm.get("relationships") or []
        other_rel_refs = set()
        if isinstance(other_rels, list):
            for r in other_rels:
                if isinstance(r, dict) and r.get("ref"):
                    other_rel_refs.add(r["ref"])

        all_direct_refs = other_related | other_article_refs | other_rel_refs
        if src_identifiers & all_direct_refs:
            strength = "direct"
            reasons.append(f"directly references {src_slug}")

        # Check 2: shared entity_refs (only if source has entities)
        if src_entity_refs and not strength:
            shared_entities = src_entity_refs & other_entity_refs
            if shared_entities:
                strength = "entity"
                reasons.append(f"shares entities: {', '.join(sorted(shared_entities))}")

        # Check 3: domain + tag overlap (weak signal, ≥2 shared tags required)
        if src_tags and not strength:
            other_tags = set(fm.get("tags") or [])
            other_domains = set(fm.get("domains") or [])
            shared_tags = src_tags & other_tags
            shared_domains = (src_domains & other_domains) - {"episodes", "holding-pen", "core"}
            if len(shared_tags) >= 2 and shared_domains:
                strength = "tag"
                reasons.append(f"shares tags: {', '.join(sorted(shared_tags))}")

        if strength:
            results.append({
                "path": rel_path,
                "title": fm.get("title", md_file.stem),
                "reason": "; ".join(reasons),
                "strength": strength,
            })

    # Sort: direct > entity > tag
    order = {"direct": 0, "entity": 1, "tag": 2}
    results.sort(key=lambda x: order.get(x["strength"], 9))
    return results


# ─── CLI entry point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Everything Vault — Ingest Tool (v2)")
    parser.add_argument("--vault", default=_find_vault_default(),
                        help="Path to vault root directory")

    subparsers = parser.add_subparsers(dest="command")

    # scan
    scan_p = subparsers.add_parser("scan", help="Scan for existing related articles")
    scan_p.add_argument("--query", required=True, help="Search query text")

    # write
    write_p = subparsers.add_parser("write", help="Write an article to the vault")
    write_p.add_argument("--path", required=True,
                         help="Relative path within vault, e.g. finance/car-insurance.md")
    write_p.add_argument("--content", help="Full markdown content (or use --content-file)")
    write_p.add_argument("--content-file", help="Read content from this file")

    # episode
    ep_p = subparsers.add_parser("episode", help="Write an episode record")
    ep_p.add_argument("--date", required=True, help="Episode date YYYY-MM-DD")
    ep_p.add_argument("--title", required=True, help="Episode title")
    ep_p.add_argument("--content", help="Full markdown content (or use --content-file)")
    ep_p.add_argument("--content-file", help="Read content from this file")

    # list
    list_p = subparsers.add_parser("list", help="List articles in the vault")
    list_p.add_argument("--domain", help="Filter by domain slug")
    list_p.add_argument("--object-type", help="Filter by object type (article/entity/episode)")

    # ripple
    ripple_p = subparsers.add_parser("ripple", help="Scan for articles affected by a change")
    ripple_p.add_argument("--source", required=True,
                          help="Relative path of the article just written, e.g. projects/kitchen-renovation.md")

    # Legacy flags for backwards compat
    parser.add_argument("--scan", action="store_true", help="(legacy) scan mode")
    parser.add_argument("--write", action="store_true", help="(legacy) write mode")
    parser.add_argument("--list", action="store_true", help="(legacy) list mode")
    parser.add_argument("--query", help="(legacy) search query")
    parser.add_argument("--path", help="(legacy) article path")
    parser.add_argument("--content", help="(legacy) article content")
    parser.add_argument("--content-file", help="(legacy) content file")
    parser.add_argument("--domain", help="(legacy) domain filter")

    args = parser.parse_args()

    # Handle legacy flags
    if args.scan or args.command == "scan":
        query = getattr(args, "query", None)
        if not query:
            print("ERROR: --query is required for scan", file=sys.stderr)
            sys.exit(1)
        results = scan_vault(args.vault, query)
        if not results:
            print("No existing related articles found.")
        else:
            print(f"Found {len(results)} potentially related article(s):")
            for r in results:
                ot = f" [{r['object_type']}]" if r['object_type'] != 'article' else ""
                sens = f" 🔒" if r.get('sensitivity') not in ('normal', None) else ""
                print(f"  [{r['domains']}] {r['title']}{ot}{sens}")
                print(f"    Path: {r['path']}")
                print(f"    Confidence: {r['confidence']} | Last verified: {r['last_verified']}")

    elif args.write or args.command == "write":
        path = getattr(args, "path", None)
        content = getattr(args, "content", None)
        content_file = getattr(args, "content_file", None)
        if content_file:
            content = Path(content_file).read_text(encoding="utf-8")
        if not path or not content:
            print("ERROR: --path and (--content or --content-file) required", file=sys.stderr)
            sys.exit(1)
        write_article(args.vault, path, content)

    elif args.command == "episode":
        content = args.content
        if args.content_file:
            content = Path(args.content_file).read_text(encoding="utf-8")
        if not content:
            print("ERROR: --content or --content-file required for episode", file=sys.stderr)
            sys.exit(1)
        write_episode(args.vault, args.date, args.title, content)

    elif args.list or args.command == "list":
        domain = getattr(args, "domain", None)
        object_type = getattr(args, "object_type", None)
        articles = list_articles(args.vault, domain, object_type)
        if not articles:
            label = f"domain '{domain}'" if domain else "vault"
            print(f"No articles found in {label}.")
        else:
            for a in articles:
                ot = f" [{a['object_type']}]" if a['object_type'] != 'article' else ""
                print(f"  {a['path']}{ot}")
                print(f"    Title: {a['title']} | Type: {a['type']} | Confidence: {a['confidence']}")

    elif args.command == "ripple":
        results = ripple_scan(args.vault, args.source)
        if not results:
            print(f"Ripple: no affected articles found for {args.source}")
        else:
            strength_labels = {"direct": "🔗 DIRECT", "entity": "👤 ENTITY", "tag": "🏷  TAG"}
            direct = [r for r in results if r["strength"] == "direct"]
            entity = [r for r in results if r["strength"] == "entity"]
            tag = [r for r in results if r["strength"] == "tag"]
            print(f"Ripple scan for: {args.source}")
            print(f"Found {len(results)} potentially affected article(s):\n")
            for group, label in [(direct, "Direct references"), (entity, "Shared entities"), (tag, "Domain+tag overlap")]:
                if group:
                    print(f"  {label}:")
                    for r in group:
                        print(f"    {r['title']}")
                        print(f"      {r['path']} — {r['reason']}")
            if tag:
                print("\n  (Tag overlap is a weak signal — check manually before acting)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
