---
name: citizenship-eligibility-checker
description: Check citizenship grant, proof, and Bill C-3 questions. Use for citizenship, lost Canadians, born-abroad children.
---
# Citizenship Eligibility Checker

## Read first
- knowledge/07-citizenship-pr-status/

## Workflow
1. Grant: compute physical presence with `python3 scripts/presence.py citizenship CASE` (trips in travel-history.csv; see /presence), then tax filing, language, test
2. Proof/C-3: identify generation, birth/adoption date vs Dec 15, 2025, 1,095-day parent presence
3. Flag complex multigenerational cases for counsel
4. Output: eligibility, documents, fees, processing

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
