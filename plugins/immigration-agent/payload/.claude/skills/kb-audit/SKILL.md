---
name: kb-audit
description: Audit the knowledge base for stale, unsourced, conflicting, or inconsistent content. Use for /audit-kb.
---
# Kb Audit

## Read first
- knowledge/00-meta/reverify-list.md

## Workflow
1. Run python3 scripts/kb_status.py and list STALE and NEEDS-SEED
2. Spot-check cross-file consistency (fees, caps, program status)
3. Coverage check: `OK` in kb_status.py means fresh, not complete. For each province, compare streams, regional initiatives and city or community routes on the official site against the knowledge files; list anything named but not documented. Check rural-franco-communities.md and regional-community-streams.md for expired intakes
4. Update reverify-list; propose next 5 /update-kb targets in priority order (fast-changing first)

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
