---
name: work-permit-pathfinder
description: Pick the right work permit stream (LMIA, IMP, CUSMA, ICT, IEC, Francophone Mobility, OWP). Use for work permit questions.
---
# Work Permit Pathfinder

## Read first
- knowledge/05-temporary-residence/work-permits-lmia.md
- knowledge/05-temporary-residence/work-permits-lmia-exempt.md
- knowledge/05-temporary-residence/open-work-permits.md
- knowledge/05-temporary-residence/work-permit-process-and-status.md
- knowledge/12-decision-trees/permit-expiring.md

## Workflow
1. Determine employer-specific vs open; LMIA required or exempt code
2. Check wage tier, refusal-to-process list, caps, employer compliance fee
3. Check spouse OWP eligibility: `python3 scripts/owp_rules.py check NOC [--permit-end YYYY-MM-DD]` (TEER and IRCC's eligible TEER 2-3 list from open-work-permits.md; children aren't eligible under this measure). For the dates (16-month test, maintained status, restoration deadline, 6-month bar, PGWP window) run `python3 scripts/status_clock.py`.
   - Current permit expiring: walk knowledge/12-decision-trees/permit-expiring.md (PGWP, LMIA, BOWP, spouse, visitor fallback, restoration).
4. Output: stream, code, documents, fees, timeline, risks

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
