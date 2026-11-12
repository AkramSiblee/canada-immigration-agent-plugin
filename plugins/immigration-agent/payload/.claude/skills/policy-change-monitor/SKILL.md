---
name: policy-change-monitor
description: Scan official sources for new immigration changes and update the policy tracker. Use for 'what changed' or scheduled refresh.
---
# Policy Change Monitor

## Read first
- knowledge/14-policy-tracker/
- knowledge/00-meta/changelog.md
- knowledge/00-meta/source-registry.md

## Workflow
1. Search IRCC news, Gazette Part II, LEGISinfo, PNP news pages, the IRCC Refugees menu (https://www.canada.ca/en/immigration-refugees-citizenship/services/refugees.html), the IRCC Work in Canada menu (https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada.html), the IRCC Immigrate menu (https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada.html), the IRCC Study in Canada menu (https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada.html), and the IRCC Visit Canada menu (https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada.html)
2. List changes since last tracker date with effective dates
3. Update affected knowledge files and changelog
4. Output: dated change summary with impact on open files

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
