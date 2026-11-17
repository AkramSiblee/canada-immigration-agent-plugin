---
name: temporary-residence-advisor
description: Advise on visitor, study, work permits, status maintenance and restoration. Use for any temporary resident question.
---
# Temporary Residence Advisor

## Read first
- knowledge/05-temporary-residence/
- knowledge/12-decision-trees/permit-expiring.md
- knowledge/13-case-law/work-permit-status-refusals.md

## Workflow
1. Establish current status and expiry, then run `python3 scripts/status_clock.py` with the dates you have (`--expiry`, `--stay-end` if a later must-leave date, `--applied`, `--second-applied`, `--refused`, `--completion`, `--study-expiry`, `--principal-end`, `--spouse-applies`, `--unauthorized-ended`, `--spouse-route c41|c49|exempt`, `--mb-bridge`): maintained status, the date status was lost, the 90-day restoration deadline, the 6-month bar end, the spouse 16-month test and the 180-day PGWP window. Never count these dates by hand.
   - Permit expiring or expired: walk knowledge/12-decision-trees/permit-expiring.md.
2. Select permit type; verify caps, PAL/TAL, LMIA lists, exemptions
3. Flag dual-intent and s.216 risks; never advise flagpoling
4. Output: options, requirements, fees, processing, risks

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
