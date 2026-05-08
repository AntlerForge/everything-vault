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
Everything Vault — Curate Tool (v2)

Maintains quality, validates structure, and audits sensitivity.

Usage:
    python3 curate.py --stale [--days 180]
    python3 curate.py --holding-pen
    python3 curate.py --gaps
    python3 curate.py --renewals [--within 90]
    python3 curate.py --validate
    python3 curate.py --sensitivity-audit
    python3 curate.py --episode-gaps
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
        for line in fm_text.splitlines():
            if not line.strip():
                continue
            if line.startswith("  - ") or line.startswith("- "):
                if current_list is not None:
                    current_list.append(line.strip().lstrip("- ").strip())
                continue
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if v == "" or v in ("|", ">"):
                    current_list = []
                    fm[k] = current_list
                elif v.startswith("[") and v.endswith("]"):
                    fm[k] = [i.strip().strip("'\"") for i in v[1:-1].split(",") if i.strip()]
                    current_list = None
                else:
                    fm[k] = v.strip("\"'")
                    current_list = None
    return fm, body


DOMAIN_EXPECTATIONS = {
    "family": "family members, contacts, arrangements",
    "family": "family members, contacts, shared arrangements",
    "finance": "bank accounts, mortgages, investments, financial trackers",
    "health": "GP details, prescriptions, medical history, fitness",
    "household": "utilities, property, maintenance, appliances",
    "vehicles": "car/van details, MOT dates, insurance, breakdown cover",
    "work": "employer, current role, key work projects",
    "professional": "qualifications, memberships, certifications",
    "pets": "pet names, vet contact, prescriptions, insurance",
    "hobbies": "interests and activities",
    "legal": "wills, LPA, contracts",
    "it-setup": "home network, computers, home automation",
    "purchases": "subscriptions, warranties, recurring costs",
}

# Keywords that suggest an article should be tagged sensitive
SENSITIVE_KEYWORDS = [
    "medication", "prescription", "diagnosis", "medical", "gp ", "doctor",
    "hospital", "surgery", "blood pressure", "mental health",
    "solicitor", "legal", "court", "will ", "lpa ", "power of attorney",
    "passport", "driving licence", "birth certificate", "national insurance",
    "ni number", "bank account", "sort code", "account number",
    "salary", "income", "tax return", "hmrc",
]

CREDENTIAL_PATTERNS = [
    r"password\s*[:=]",
    r"api[_\s]?key\s*[:=]",
    r"secret\s*[:=]",
    r"token\s*[:=]",
    r"recovery\s+code",
]


def load_all(vault_path):
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
            articles.append(fm)
        except Exception:
            continue
    return articles


def find_stale(vault_path, days=180):
    cutoff = date.today() - timedelta(days=days)
    articles = load_all(vault_path)
    stale = []

    for a in articles:
        domains = a.get("domains", [])
        if isinstance(domains, str):
            domains = [domains]
        if "holding-pen" in domains or "core" in domains or "episodes" in domains:
            continue

        reason = None
        lv = a.get("last_verified")
        if not lv or str(lv) == "null":
            reason = "never verified"
        else:
            try:
                lv_date = datetime.strptime(str(lv), "%Y-%m-%d").date()
                if lv_date < cutoff:
                    reason = f"last verified {lv} ({(date.today() - lv_date).days} days ago)"
            except ValueError:
                pass

        rd = a.get("renewal_date")
        if rd and str(rd) != "null":
            try:
                rd_date = datetime.strptime(str(rd), "%Y-%m-%d").date()
                if rd_date < date.today():
                    reason = (reason or "") + f" | renewal date {rd} has PASSED"
            except ValueError:
                pass

        if reason:
            stale.append({**a, "_stale_reason": reason})

    return stale


def holding_pen_items(vault_path):
    articles = load_all(vault_path)
    pen = []
    for a in articles:
        domains = a.get("domains", [])
        if isinstance(domains, str):
            domains = [domains]
        if "holding-pen" in domains:
            pen.append(a)
    return pen


def find_gaps(vault_path):
    vault = Path(vault_path)
    gaps = []
    for slug, description in DOMAIN_EXPECTATIONS.items():
        domain_dir = vault / slug
        if not domain_dir.exists():
            count = 0
        else:
            count = sum(1 for f in domain_dir.glob("*.md") if not f.name.startswith("_"))
        if count < 2:
            gaps.append({
                "domain": slug,
                "count": count,
                "suggestions": description,
            })
    return gaps


def upcoming_renewals(vault_path, within_days=90):
    articles = load_all(vault_path)
    today = date.today()
    upcoming = []

    for a in articles:
        rd = a.get("renewal_date")
        if not rd or str(rd) == "null":
            continue
        try:
            rd_date = datetime.strptime(str(rd), "%Y-%m-%d").date()
            delta = (rd_date - today).days
            if -30 <= delta <= within_days:
                upcoming.append({**a, "_days_until": delta})
        except ValueError:
            continue

    upcoming.sort(key=lambda x: x["_days_until"])
    return upcoming


def validate(vault_path):
    """Validate frontmatter completeness and structural integrity."""
    articles = load_all(vault_path)
    vault = Path(vault_path)
    issues = []

    # Build a set of all known slugs for reference checking
    all_slugs = set()
    for a in articles:
        path = a.get("_path", "")
        slug = Path(path).stem
        all_slugs.add(slug)
        aid = a.get("id")
        if aid:
            all_slugs.add(str(aid))

    for a in articles:
        path = a.get("_path", "unknown")

        # Required fields
        if not a.get("title"):
            issues.append(("error", path, "Missing 'title' field"))
        if not a.get("domains"):
            issues.append(("error", path, "Missing 'domains' field"))
        if not a.get("type"):
            issues.append(("warn", path, "Missing 'type' field"))

        # Date validation
        for date_field in ["created", "last_updated", "last_verified", "renewal_date", "date"]:
            val = a.get(date_field)
            if val and str(val) != "null":
                try:
                    datetime.strptime(str(val), "%Y-%m-%d")
                except ValueError:
                    issues.append(("error", path, f"Invalid date in '{date_field}': {val}"))

        # Broken related references
        related = a.get("related") or []
        if isinstance(related, str):
            related = [related]
        for ref in related:
            if ref not in all_slugs:
                issues.append(("warn", path, f"Broken 'related' reference: {ref}"))

        # Broken entity_refs
        entity_refs = a.get("entity_refs") or []
        if isinstance(entity_refs, str):
            entity_refs = [entity_refs]
        for ref in entity_refs:
            if ref not in all_slugs:
                issues.append(("info", path, f"Unresolved 'entity_refs': {ref}"))

        # v2.1: validate relationships field
        valid_rel_types = {"supports", "extends", "supersedes", "contradicts",
                           "refines", "implements", "inspires"}
        relationships = a.get("relationships") or []
        if isinstance(relationships, list):
            for rel in relationships:
                if not isinstance(rel, dict):
                    issues.append(("warn", path, f"'relationships' entry is not a dict: {rel}"))
                    continue
                ref = rel.get("ref")
                rtype = rel.get("type")
                if ref and ref not in all_slugs:
                    issues.append(("warn", path, f"Broken 'relationships' ref: {ref}"))
                if rtype and rtype not in valid_rel_types:
                    issues.append(("warn", path,
                                   f"Invalid 'relationships' type: '{rtype}'. "
                                   f"Must be one of: {', '.join(sorted(valid_rel_types))}"))

    return issues


def sensitivity_audit(vault_path):
    """Flag articles that may need sensitivity upgrade."""
    articles = load_all(vault_path)
    flags = []

    for a in articles:
        path = a.get("_path", "unknown")
        sensitivity = a.get("sensitivity", "normal")
        if sensitivity != "normal":
            continue

        text = (a.get("title", "") + " " + a.get("_body", "")).lower()

        # Check for sensitive keywords
        for kw in SENSITIVE_KEYWORDS:
            if kw in text:
                flags.append(("sensitive", path, f"Contains '{kw}' but tagged normal"))
                break

        # Check for credential patterns
        for pattern in CREDENTIAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(("credential", path, f"Contains credential-like pattern"))
                break

    return flags


def episode_gaps(vault_path):
    """Find active topics with no recent episodes."""
    articles = load_all(vault_path)
    vault = Path(vault_path)

    # Find articles with recent activity
    cutoff = date.today() - timedelta(days=90)
    active_articles = []
    for a in articles:
        ot = a.get("object_type", "article")
        if ot == "episode":
            continue
        domains = a.get("domains", [])
        if isinstance(domains, str):
            domains = [domains]
        if "core" in domains:
            continue

        lu = a.get("last_updated")
        if lu and str(lu) != "null":
            try:
                lu_date = datetime.strptime(str(lu), "%Y-%m-%d").date()
                if lu_date > cutoff:
                    active_articles.append(a)
                    continue
            except ValueError:
                pass

        rd = a.get("renewal_date")
        if rd and str(rd) != "null":
            try:
                rd_date = datetime.strptime(str(rd), "%Y-%m-%d").date()
                delta = (rd_date - date.today()).days
                if -30 <= delta <= 90:
                    active_articles.append(a)
            except ValueError:
                pass

    # Check which have associated episodes
    episodes_dir = vault / "episodes"
    episode_refs = set()
    if episodes_dir.exists():
        for md_file in episodes_dir.rglob("*.md"):
            if _is_under_dot_or_underscore(md_file, vault):
                continue
            if md_file.name.startswith("_"):
                continue
            try:
                text = md_file.read_text(encoding="utf-8")
                fm, _ = parse_frontmatter(text)
                for ref in fm.get("article_refs", []):
                    episode_refs.add(str(ref).lower())
            except Exception:
                continue

    gaps = []
    for a in active_articles:
        slug = Path(a.get("_path", "")).stem.lower()
        aid = str(a.get("id", "")).lower()
        if slug not in episode_refs and aid not in episode_refs:
            gaps.append(a)

    return gaps


def main():
    parser = argparse.ArgumentParser(description="Everything Vault — Curate Tool (v2)")
    parser.add_argument("--vault", default=_find_vault_default())
    parser.add_argument("--stale", action="store_true")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--holding-pen", action="store_true")
    parser.add_argument("--gaps", action="store_true")
    parser.add_argument("--renewals", action="store_true")
    parser.add_argument("--within", type=int, default=90)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--sensitivity-audit", action="store_true")
    parser.add_argument("--episode-gaps", action="store_true")
    args = parser.parse_args()

    if args.stale:
        results = find_stale(args.vault, args.days)
        if not results:
            print(f"✓ No stale articles found (threshold: {args.days} days).")
        else:
            print(f"⚠ {len(results)} stale article(s) found:\n")
            for a in results:
                print(f"  [{a.get('confidence','?')}] {a.get('title', a['_path'])}")
                print(f"    → {a['_stale_reason']}")

    elif args.holding_pen:
        results = holding_pen_items(args.vault)
        if not results:
            print("✓ Holding pen is empty.")
        else:
            print(f"📥 {len(results)} item(s) in holding pen:\n")
            for a in results:
                print(f"  {a.get('title', a['_path'])}")
                print(f"    Source: {a.get('source', '?')} | Created: {a.get('created', '?')}")

    elif args.gaps:
        results = find_gaps(args.vault)
        if not results:
            print("✓ All domains have reasonable coverage.")
        else:
            print(f"📊 {len(results)} domain(s) with sparse coverage:\n")
            for g in results:
                label = "empty" if g["count"] == 0 else f"{g['count']} article(s)"
                print(f"  {g['domain']} ({label})")
                print(f"    Suggested content: {g['suggestions']}")

    elif args.renewals:
        results = upcoming_renewals(args.vault, args.within)
        if not results:
            print(f"✓ No renewals in the next {args.within} days.")
        else:
            print(f"📅 {len(results)} upcoming renewal(s):\n")
            for a in results:
                delta = a["_days_until"]
                rd = a.get("renewal_date")
                provider = a.get("provider", "")
                cost = a.get("cost")
                title = a.get("title", a["_path"])
                cost_str = f" — £{cost}" if cost and cost != "null" else ""
                if delta < 0:
                    timing = f"OVERDUE by {abs(delta)} days"
                elif delta == 0:
                    timing = "TODAY"
                else:
                    timing = f"in {delta} days ({rd})"
                print(f"  {timing}: {title} {provider}{cost_str}")

    elif args.validate:
        issues = validate(args.vault)
        if not issues:
            print("✓ No validation issues found.")
        else:
            errors = [i for i in issues if i[0] == "error"]
            warns = [i for i in issues if i[0] == "warn"]
            infos = [i for i in issues if i[0] == "info"]
            print(f"Validation: {len(errors)} error(s), {len(warns)} warning(s), {len(infos)} info(s)\n")
            if errors:
                print("ERRORS:")
                for _, path, msg in errors:
                    print(f"  ✗ {path}: {msg}")
            if warns:
                print("\nWARNINGS:")
                for _, path, msg in warns:
                    print(f"  ⚠ {path}: {msg}")
            if infos:
                print("\nINFO:")
                for _, path, msg in infos:
                    print(f"  ℹ {path}: {msg}")

    elif args.sensitivity_audit:
        flags = sensitivity_audit(args.vault)
        if not flags:
            print("✓ No sensitivity issues found.")
        else:
            print(f"🔒 {len(flags)} article(s) may need sensitivity review:\n")
            for level, path, reason in flags:
                icon = "🔑" if level == "credential" else "🔒"
                print(f"  {icon} {path}")
                print(f"    → {reason} (suggest: {level})")

    elif args.episode_gaps:
        gaps = episode_gaps(args.vault)
        if not gaps:
            print("✓ Active topics have associated episodes.")
        else:
            print(f"📋 {len(gaps)} active topic(s) with no recent episodes:\n")
            for a in gaps:
                print(f"  {a.get('title', a['_path'])}")
                print(f"    Last updated: {a.get('last_updated', '?')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
