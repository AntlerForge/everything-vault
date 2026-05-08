# File Capability — Decision Guidance

You are bridging a physical document into the Everything Vault. Your job is to read the
document, extract what's useful, and create a knowledge article that references it —
without moving the original.

## Step-by-step

### 1. Read the document

`python3 <skill_dir>/tools/file_handler.py --summarise <file_path>`

This extracts text and identifies key patterns (dates, amounts, reference numbers,
provider names). Use this output as your starting point — don't rely on it exclusively,
as heuristics miss things that are obvious from reading.

For PDFs already uploaded to the conversation: use your built-in PDF reading capability.
For files referenced by path: use the tool above.

### 2. Extract the key facts

From the document, identify:
- **What is this?** (insurance policy, receipt, instruction manual, certificate, letter...)
- **Who is the provider / sender?**
- **Are there any dates?** (start date, expiry, renewal, MOT due...)
- **Is there a cost?** (annual premium, purchase price...)
- **Is there a policy/reference/account number?**
- **What domain does this belong to?**

### 3. Propose to the user (before writing)

Show a brief summary:
```
I've read the document. Here's what I'd create:

Title: AA Breakdown Cover
Domain: vehicles
Type: fact
Provider: AA
Renewal: 14 March 2027
Cost: £85/year
Membership: AA-12345678
Source: Vehicles/AA Breakdown cover Confirmation.pdf

Shall I create this article?
```

Wait for confirmation. The user may correct details or suggest a different domain.

### 4. Create the knowledge article

After approval:
- Write the article to `<vault>/<domain>/<slug>.md`
- Include YAML frontmatter with all extracted facts
- Set `source: filed-document`
- Set `source_ref:` to the **original file path** (do NOT move the file)
- Set `confidence: high` (document is an authoritative source)
- Write a concise body with the key facts in readable prose

### 5. Rebuild the index

`python3 <skill_dir>/tools/index_builder.py --vault <vault> --domain <domain>`

### 6. Confirm to the user

"Filed. Article created at vehicles/aa-breakdown-cover.md. The original PDF is
still at Vehicles/AA Breakdown cover Confirmation.pdf."

## File Naming

Convert the title to a lowercase hyphen-slug:
- "AA Breakdown Cover" → `aa-breakdown-cover.md`
- "Car Insurance 2026" → `car-insurance-2026.md`
- "Project notes" → `project-notes.md`

## What to do when the document is unclear

- **Can't determine what it is:** Put in holding-pen, note the file path
- **Looks like personal data with no clear admin purpose** (e.g. a random scan): Ask
  the user what they'd like to capture from it before creating an article
- **Very large document (report, manual):** Extract only the most useful facts —
  don't try to summarise everything. The article is a pointer and key-facts extractor,
  not a transcript.

## Important: Do NOT move original files

The `source_ref` field records where the original file is. The file stays there.
Only move or reorganise physical files if the user explicitly asks for it.

## Examples

### Filing a car insurance renewal PDF

Input: User uploads "Certificate_of_Insurance_2026.pdf"

Extract:
- Provider: Generic Insurance Co
- Policy: POL-123456
- Insured: the user (and any named drivers from the document)
- Renewal: 15 June 2027
- Annual premium: £450

Article: `vehicles/car-insurance.md`
```yaml
---
title: "Car Insurance"
domains: [vehicles, finance]
type: fact
tags: [insurance, renewal]
source: filed-document
source_ref: "sources/2026/2026-03-29-car-insurance-cert.pdf"
created: 2026-03-29
last_updated: 2026-03-29
last_verified: 2026-03-29
confidence: high
renewal_date: 2027-06-15
cost: 450
provider: "Generic Insurance Co"
---

Car insurance with Generic Insurance Co. Policy number POL-123456.
Annual premium £450. Renews 15 June 2027.
```

### Filing a mystery scan

Input: "Scanned Document.pdf" — unclear content

Action: Summarise to user, ask what they want to keep, or put in holding-pen with note.
