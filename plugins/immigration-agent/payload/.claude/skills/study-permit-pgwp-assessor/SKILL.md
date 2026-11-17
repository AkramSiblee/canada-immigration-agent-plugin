---
name: study-permit-pgwp-assessor
description: Assess study permit and PGWP eligibility including PAL/TAL, cap, field-of-study list, language. Use for student matters.
---
# Study Permit Pgwp Assessor

## Read first
- knowledge/12-decision-trees/study.md (the route: school/program -> PAL/cap -> funds -> compliance -> PGWP -> PR)
- knowledge/05-temporary-residence/study-permits.md
- knowledge/05-temporary-residence/study-permit-status-and-compliance.md
- knowledge/05-temporary-residence/pgwp.md
- knowledge/01-federal-economic/levels-plan-and-caps.md
- knowledge/13-case-law/study-permit-pgwp-refusals.md
- knowledge/14-policy-tracker/announced-for-2027.md (student watch list)
- Quebec: knowledge/03-quebec/caq-csq-and-students.md

## Workflow
1. Check DLI level, public/private, cap exemption, PAL/TAL needs, CAQ
2. Check funds vs current table; study plan strength
3. PGWP: field of study with `python3 scripts/cip_check.py CIP [--applied YYYY-MM-DD] [--pgwp YYYY-MM-DD]` (study permit and PGWP application dates; the answer is eligible, date-conditioned, not eligible or not listed, with the IRCC list date). Never answer a CIP question from memory. Not needed for bachelor's/master's/PhD or permits applied for before 2024-11-01. Then language CLB, program length (how IRCC measures it), duration, 180-day window, program changes after the study permit.
   - Compliance: program or school changes, scheduled breaks, work hours, spouse OWP validity, restoration (R182) and unauthorized work/study bars (R200(3)(e), R221): study-permit-status-and-compliance.md.
4. Output: eligibility, gaps, refusal risks

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
