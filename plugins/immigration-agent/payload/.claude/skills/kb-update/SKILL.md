---
name: kb-update
description: Research and rewrite one knowledge file (or ingest _inbox) from official sources. Use for /update-kb or when a file is stale or needs-seed.
---
# Kb Update

## Read first
- knowledge/00-meta/source-registry.md
- knowledge/00-meta/confidence-legend.md

## Workflow
1. Pick target via scripts/kb_status.py or user argument
2. Read the stub's Must-cover list; research official sources first, secondary second; run separate searches per sub-topic
3. Rewrite file: current rules, recent changes, pitfalls, refusal reasons, re-verify items, sources with URLs and dates
4. Set front matter: status verified, last_verified today, confidence, sources
5. Append to 00-meta/update-log.md; add notable changes to 00-meta/changelog.md; update comparison/decision-tree files that depend on it
6. Record conflicts instead of silently picking one

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
