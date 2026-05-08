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
Everything Vault — File Handler

Summarises documents for filing into the vault. Reads PDFs, DOCX, emails,
and plain text files and extracts key metadata for knowledge article creation.

Usage:
    python3 file_handler.py --summarise <path>    # Extract key info from a document
    python3 file_handler.py --list-refs --vault <path>  # List all articles with source_refs
"""

import argparse
import os
import re
import sys
from pathlib import Path


def extract_text_plain(file_path):
    """Read plain text / markdown files."""
    return Path(file_path).read_text(encoding="utf-8", errors="replace")


def extract_text_pdf(file_path):
    """Extract text from PDF using pdfminer or pypdf2 if available."""
    try:
        import pdfminer.high_level
        return pdfminer.high_level.extract_text(file_path)
    except ImportError:
        pass
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        pass
    return f"[PDF text extraction not available — install pdfminer.six or PyPDF2]\nFile: {file_path}"


# Skip files inside any underscore-prefixed folder ("_for-deletion/", "_archive/" etc.)
# so soft-deleted content stays out of indexing, queries, and dashboard.
def _is_under_dot_or_underscore(path, vault_root):
    try:
        parts = path.relative_to(vault_root).parts
    except ValueError:
        return True  # outside vault
    return any(p.startswith("_") or p.startswith(".") for p in parts[:-1])

def extract_text_docx(file_path):
    """Extract text from DOCX using python-docx if available."""
    try:
        import docx
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return f"[DOCX extraction not available — install python-docx]\nFile: {file_path}"


def extract_text_email(file_path):
    """Extract text from .eml files."""
    import email
    try:
        with open(file_path, "rb") as f:
            msg = email.message_from_bytes(f.read())
        parts = []
        parts.append(f"From: {msg.get('From', '')}")
        parts.append(f"Subject: {msg.get('Subject', '')}")
        parts.append(f"Date: {msg.get('Date', '')}")
        parts.append("")
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        parts.append(payload.decode("utf-8", errors="replace"))
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                parts.append(payload.decode("utf-8", errors="replace"))
        return "\n".join(parts)
    except Exception as e:
        return f"[Could not parse email: {e}]\nFile: {file_path}"


def read_document(file_path):
    """Read any supported document type. Returns extracted text."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md", ".csv"):
        return extract_text_plain(file_path)
    elif suffix == ".pdf":
        return extract_text_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        return extract_text_docx(file_path)
    elif suffix == ".eml":
        return extract_text_email(file_path)
    else:
        # Try plain text as fallback
        try:
            return extract_text_plain(file_path)
        except Exception:
            return f"[Unsupported file type: {suffix}]\nFile: {file_path}"


def extract_key_facts(text, filename=""):
    """
    Heuristic extraction of key facts from document text.
    Returns a dict of found patterns — not exhaustive, aids the agent in structuring.
    """
    facts = {}
    text_lower = text.lower()

    # Dates (UK format DD/MM/YYYY or YYYY-MM-DD)
    date_patterns = re.findall(
        r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})\b', text
    )
    if date_patterns:
        facts["dates_found"] = date_patterns[:5]

    # Money amounts
    money = re.findall(r'£[\d,]+(?:\.\d{2})?|\b[\d,]+(?:\.\d{2})?\s*(?:per\s+year|p\.a\.|annually)', text)
    if money:
        facts["amounts_found"] = money[:5]

    # Policy/account/reference numbers
    refs = re.findall(r'\b[A-Z]{2,}[-\s]?\d{4,}\b|\b\d{6,}\b', text)
    if refs:
        facts["reference_numbers"] = refs[:5]

    # Provider names (look for "with", "from", "by" followed by capitalised words)
    providers = re.findall(r'(?:with|from|by|insured by|provided by)\s+([A-Z][A-Za-z&\s]{1,30})',
                           text)
    if providers:
        facts["potential_providers"] = [p.strip() for p in providers[:3]]

    # Renewal/expiry keywords
    if any(w in text_lower for w in ["renew", "expir", "valid until", "due date"]):
        facts["renewal_related"] = True

    # Filename hints
    facts["filename"] = filename

    return facts


def summarise_document(file_path):
    """
    Read a document and produce a structured summary for the agent to use
    when creating a knowledge article.
    """
    path = Path(file_path)
    print(f"Reading: {path.name}")
    print(f"Type: {path.suffix.upper()}")
    print()

    text = read_document(file_path)

    # Truncate for display
    preview = text[:2000]
    if len(text) > 2000:
        preview += f"\n\n[... {len(text) - 2000} more characters ...]"

    print("=== DOCUMENT CONTENT (first 2000 chars) ===")
    print(preview)
    print()

    facts = extract_key_facts(text, path.name)
    if facts:
        print("=== EXTRACTED KEY FACTS ===")
        for k, v in facts.items():
            print(f"  {k}: {v}")
        print()

    print("=== FILING SUGGESTION ===")
    print("Based on the above, the agent should:")
    print("1. Identify the primary domain and suggest a title")
    print("2. Extract: title, provider, renewal date, cost, policy/ref number")
    print("3. Create a knowledge article with source_ref pointing to this file")
    print(f"   source_ref: {file_path}")

    return text, facts


def list_source_refs(vault_path):
    """List all articles that have source_ref links to physical files."""
    vault = Path(vault_path)
    results = []
    for md_file in vault.rglob("*.md"):
        if _is_under_dot_or_underscore(md_file, vault):
            continue
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            # Quick check for source_ref
            if "source_ref:" in text:
                # Parse just enough to get the ref
                for line in text.splitlines():
                    if line.strip().startswith("source_ref:"):
                        ref = line.split(":", 1)[1].strip().strip("\"'")
                        results.append({
                            "article": str(md_file.relative_to(vault)),
                            "source_ref": ref,
                            "exists": Path(ref).exists() if ref else False,
                        })
        except Exception:
            continue
    return results


def main():
    parser = argparse.ArgumentParser(description="Everything Vault — File Handler")
    parser.add_argument("--vault", default=_find_vault_default())
    parser.add_argument("--summarise", metavar="FILE", help="Summarise a document for filing")
    parser.add_argument("--list-refs", action="store_true",
                        help="List all articles with source_ref links")
    args = parser.parse_args()

    if args.summarise:
        if not Path(args.summarise).exists():
            print(f"ERROR: File not found: {args.summarise}", file=sys.stderr)
            sys.exit(1)
        summarise_document(args.summarise)

    elif args.list_refs:
        results = list_source_refs(args.vault)
        if not results:
            print("No articles with source_ref links found.")
        else:
            print(f"Articles with source files ({len(results)}):\n")
            for r in results:
                status = "✓" if r["exists"] else "✗ (file not found)"
                print(f"  {r['article']}")
                print(f"    → {r['source_ref']} {status}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
