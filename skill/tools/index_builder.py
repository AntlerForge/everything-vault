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
Everything Vault — Index Builder (v2)

Rebuilds _index.md files for domains, episodes, and the master index.

Usage:
    python3 index_builder.py --vault <path>
    python3 index_builder.py --vault <path> --domain <slug>
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


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


DOMAINS = [
    ("core", "Core Memory"),
    ("family", "Family"),
    # ("family/<person>", "Person"), # add per-person folders here
    ("finance", "Finance"),
    ("health", "Health"),
    ("household", "Household"),
    ("vehicles", "Vehicles"),
    ("work", "Work"),
    ("professional", "Professional Development"),
    ("pets", "Pets"),
    ("hobbies", "Hobbies & Interests"),
    ("legal", "Legal"),
    ("it-setup", "IT & Tech Setup"),
    ("concepts", "Concepts & Ideas"),
    ("purchases", "Purchases & Subscriptions"),
    ("holidays", "Holidays"),
    ("holidays/australia-2026", "Australia 2026"),
    ("holidays/seville-2026", "Seville 2026"),
    ("work-log", "Work Log"),
    ("holding-pen", "Holding Pen"),
]


# Skip files inside any underscore-prefixed folder ("_for-deletion/", "_archive/" etc.)
# so soft-deleted content stays out of indexing, queries, and dashboard.
def _is_under_dot_or_underscore(path, vault_root):
    try:
        parts = path.relative_to(vault_root).parts
    except ValueError:
        return True  # outside vault
    return any(p.startswith("_") or p.startswith(".") for p in parts[:-1])

def build_domain_index(vault_path, domain_slug, domain_label):
    """Build _index.md for a single domain directory.

    If the existing _index.md contains the marker `_Hand-maintained_` (as used on
    multi-trip / multi-project landing pages), the file is left untouched. Useful
    for domains like `holidays` where top-level has no direct articles but sub-
    folders each carry a trip.
    """
    vault = Path(vault_path)
    domain_dir = vault / domain_slug

    if not domain_dir.exists():
        return False

    existing_index = domain_dir / "_index.md"
    if existing_index.exists():
        try:
            if "_Hand-maintained_" in existing_index.read_text(encoding="utf-8"):
                print(f"SKIP: {domain_slug}/_index.md (hand-maintained)")
                return True
        except Exception:
            pass

    articles = []
    for md_file in sorted(domain_dir.glob("*.md")):
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            rel_count = len(fm.get("relationships") or [])
            articles.append({
                "filename": md_file.name,
                "title": fm.get("title", md_file.stem),
                "type": fm.get("type", ""),
                "object_type": fm.get("object_type", "article"),
                "confidence": fm.get("confidence", ""),
                "last_verified": fm.get("last_verified", ""),
                "sensitivity": fm.get("sensitivity", "normal"),
                "renewal_date": fm.get("renewal_date"),
                "provider": fm.get("provider"),
                "cost": fm.get("cost"),
                "rel_count": rel_count,
            })
        except Exception:
            continue

    lines = [
        f"# {domain_label} — Index",
        f"",
        f"_Auto-generated {date.today().isoformat()}_",
        f"",
        f"{len(articles)} article(s) in this domain.",
        f"",
    ]

    if not articles:
        lines.append("_No articles yet._")
    else:
        lines.append("| Article | Type | Confidence | Last Verified |")
        lines.append("|---------|------|------------|---------------|")
        for a in articles:
            renewal_note = ""
            if a["renewal_date"] and a["renewal_date"] != "null":
                renewal_note = f" _(renews {a['renewal_date']})_"
            cost_note = f" £{a['cost']}/yr" if a.get("cost") and a["cost"] != "null" else ""
            provider_note = f" · {a['provider']}" if a.get("provider") and a["provider"] != "null" else ""
            ot_note = f" [{a['object_type']}]" if a["object_type"] != "article" else ""
            sens_note = " 🔒" if a["sensitivity"] not in ("normal", None, "") else ""
            rel_note = f" ({a['rel_count']} relationships)" if a.get("rel_count") else ""
            title_cell = f"[{a['title']}]({a['filename']}){ot_note}{sens_note}{rel_note}{provider_note}{cost_note}{renewal_note}"
            lines.append(f"| {title_cell} | {a['type']} | {a['confidence']} | {a['last_verified']} |")

    index_path = domain_dir / "_index.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: Updated {domain_slug}/_index.md ({len(articles)} articles)")
    return True


def build_episode_index(vault_path):
    """Build _index.md for the episodes directory."""
    vault = Path(vault_path)
    episodes_dir = vault / "episodes"
    if not episodes_dir.exists():
        return False

    episodes = []
    for md_file in episodes_dir.rglob("*.md"):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            episodes.append({
                "path": str(md_file.relative_to(episodes_dir)),
                "title": fm.get("title", md_file.stem),
                "date": fm.get("date", "unknown"),
                "actors": fm.get("actors", []),
                "outcomes": fm.get("outcomes", []),
                "sensitivity": fm.get("sensitivity", "normal"),
            })
        except Exception:
            continue

    episodes.sort(key=lambda x: str(x.get("date", "")), reverse=True)

    lines = [
        "# Episodes — Index",
        "",
        f"_Auto-generated {date.today().isoformat()}_",
        "",
        f"{len(episodes)} episode(s) recorded.",
        "",
    ]

    if not episodes:
        lines.append("_No episodes yet._")
    else:
        lines.append("| Date | Episode | Actors |")
        lines.append("|------|---------|--------|")
        for ep in episodes:
            actors = ep["actors"]
            if isinstance(actors, str):
                actors = [actors]
            sens_note = " 🔒" if ep["sensitivity"] not in ("normal", None, "") else ""
            lines.append(f"| {ep['date']} | [{ep['title']}]({ep['path']}){sens_note} | {', '.join(actors)} |")

    index_path = episodes_dir / "_index.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: Updated episodes/_index.md ({len(episodes)} episodes)")
    return True


def build_master_index(vault_path):
    """Build the top-level _index.md across all domains."""
    vault = Path(vault_path)
    today = date.today().isoformat()

    lines = [
        "# Everything Vault — Master Index",
        "",
        f"_Auto-generated {today} | Schema v2_",
        "",
        "## Domains",
        "",
    ]

    total = 0
    for slug, label in DOMAINS:
        domain_dir = vault / slug
        if not domain_dir.exists():
            count = 0
        else:
            count = sum(1 for f in domain_dir.glob("*.md") if not f.name.startswith("_"))
        total += count

        # For hand-maintained parent landing pages (e.g. holidays, which has no
        # direct articles but hosts trip sub-folders), roll up counts from child
        # domains registered in DOMAINS as `<slug>/<child>`.
        is_hand_maintained = False
        existing_index = domain_dir / "_index.md"
        if existing_index.exists():
            try:
                if "_Hand-maintained_" in existing_index.read_text(encoding="utf-8"):
                    is_hand_maintained = True
            except Exception:
                pass

        if is_hand_maintained:
            children = [s for s, _ in DOMAINS if s.startswith(slug + "/")]
            child_count = 0
            for child in children:
                child_dir = vault / child
                if child_dir.exists():
                    child_count += sum(1 for f in child_dir.glob("*.md") if not f.name.startswith("_"))
            status = f"{child_count} article(s) across {len(children)} sub-folder(s)" if child_count > 0 else "_empty_"
        else:
            status = f"{count} article(s)" if count > 0 else "_empty_"
        lines.append(f"- **[{label}]({slug}/_index.md)** — {status}")

    # Episodes
    episodes_dir = vault / "episodes"
    ep_count = 0
    if episodes_dir.exists():
        ep_count = sum(1 for f in episodes_dir.rglob("*.md") if not f.name.startswith("_"))
    lines.append(f"- **[Episodes](episodes/_index.md)** — {ep_count} episode(s)")

    lines += [
        "",
        f"**Total articles:** {total} | **Episodes:** {ep_count}",
        "",
        "## Recent Activity",
        "",
        "_See individual domain indexes for details._",
    ]

    index_path = vault / "_index.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: Updated master _index.md (total {total} articles, {ep_count} episodes)")


def main():
    parser = argparse.ArgumentParser(description="Everything Vault — Index Builder (v2)")
    parser.add_argument("--vault", default=_find_vault_default())
    parser.add_argument("--domain", help="Rebuild only this domain slug")
    args = parser.parse_args()

    if args.domain:
        if args.domain == "episodes":
            build_episode_index(args.vault)
        else:
            label = next((l for s, l in DOMAINS if s == args.domain), args.domain.title())
            build_domain_index(args.vault, args.domain, label)
        build_master_index(args.vault)
    else:
        for slug, label in DOMAINS:
            build_domain_index(args.vault, slug, label)
        build_episode_index(args.vault)
        build_master_index(args.vault)


if __name__ == "__main__":
    main()
