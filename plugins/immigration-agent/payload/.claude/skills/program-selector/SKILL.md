---
name: program-selector
description: Recommend immigration pathways for a client profile across federal, PNP, Quebec, family, temporary. Use when asked which program or route fits.
---
# Program Selector

## Read first
- knowledge/12-decision-trees/ (business.md for business clients)
- knowledge/01-federal-economic/
- knowledge/02-pnp/comparison-table.md
- knowledge/14-policy-tracker/legislation-and-regulations.md

## Workflow
1. Confirm program is open (policy tracker) before recommending
   - Client wants to start, buy or run a business, invest, or be self-employed: walk knowledge/12-decision-trees/business.md, then use the entrepreneur-assessor skill (`/entrepreneur`) for the provincial and Quebec entrepreneur streams. Start-Up Visa is closed, Self-Employed is paused, the federal entrepreneur pilot is not launched. PR-intent entrepreneurs use C60, never C11.
2. Walk the relevant decision tree; list eligible and near-eligible routes
3. Rank by realistic odds and timeline; note CRS/points gap
4. Output table: route, eligibility status, gap, timeline, fees, risks

## Guardrails
- Spouse open work permit: never suggest one without `python3 scripts/owp_rules.py check NOC [--permit-end YYYY-MM-DD]` (TEER and IRCC's eligible TEER 2-3 list, read from open-work-permits.md). If it says NO, say why and suggest another route; if CONFIRM, say eligibility is unconfirmed. Dependent children don't get one under the worker-spouse measure, and don't assume the PR-pathway family route for an LMIA-based permit.
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
