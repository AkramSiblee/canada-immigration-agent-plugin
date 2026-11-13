---
name: us-pathway-finder
description: Map US-based applicants (US citizens, green-card holders, H-1B, L-1, TN, F-1) to Canadian work permit and PR routes. Use when a client lives or works in the United States.
---
# US to Canada Pathway Finder

## Read first
- knowledge/12-decision-trees/us-to-canada.md
- knowledge/05-temporary-residence/work-permits-lmia-exempt.md
- knowledge/05-temporary-residence/work-permit-process-and-status.md
- knowledge/05-temporary-residence/visa-requirements-by-nationality.md
- knowledge/14-policy-tracker/ministerial-instructions-and-program-delivery.md
- knowledge/08-inadmissibility/criminality-rehabilitation-arc.md

## Workflow
1. Collect: citizenship(s), US status (citizen, LPR, H-1B, L-1, TN, F-1, other) and expiry, employer (multinational with a Canadian entity?), occupation and NOC/TEER, job offer in Canada, years of skilled work, education and ECA, language scores, spouse and children, every arrest, charge or DUI in any country.
2. Walk the decision tree: entry document by passport; work permit route (CUSMA professional or ICT for US citizens, C12 ICT for any citizenship, LMIA otherwise); where to apply (port of entry only if visa-exempt and ready); then PR (FSW now, or CEC after a year in Canada, categories, PNP).
3. **H-1B pathway:** check the policy tracker and IRCC on the day. As of 2026-11-13 it is announced (Budget 2025) but NOT open; never present it as open.
4. Run `/clb`, `/fsw`, `/crs` and `/pnp` as needed. Output a table of routes (eligible now / after a step / not eligible) with the gap, timeline and first step for each.
5. Flag DUI or any criminality (serious criminality; rehabilitation or TRP; lawyer if equivalency is unclear) and misrepresentation risk for undisclosed US arrests.

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
