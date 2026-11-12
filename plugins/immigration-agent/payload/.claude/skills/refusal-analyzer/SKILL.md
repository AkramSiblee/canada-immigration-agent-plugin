---
name: refusal-analyzer
description: Analyze a refusal letter and GCMS notes and recommend reapply, reconsideration, or JR referral. Use when a client is refused.
---
# Refusal Analyzer

## Read first
- knowledge/09-procedure-litigation/
- knowledge/11-forms-fees-processing/common-returns-and-refusals.md

## Workflow
1. Extract refusal grounds and cited sections; map to evidence gaps
2. Note deadlines (JR 15/60 days) and appeal rights (IAD, RAD)
3. Recommend: reapply with fixes, reconsideration, ATIP request, or refer to lawyer for JR
4. Output: ground-by-ground table with fix and evidence

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
