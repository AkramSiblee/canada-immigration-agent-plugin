---
name: us-pathway-finder
description: Map US-based clients (US citizens, green-card holders, H-1B, L-1, TN, F-1, Canadians and Canadian PRs living in the US) to Canadian visit, work, study, business, PR, family and citizenship routes. Use when a client lives or works in the United States.
---
# US to Canada Pathway Finder

## Read first
- knowledge/12-decision-trees/us-to-canada.md (the tree; it names the file for each branch)
- knowledge/05-temporary-residence/work-permits-lmia-exempt.md
- knowledge/05-temporary-residence/trade-agreement-work-permits.md
- knowledge/05-temporary-residence/work-permit-process-and-status.md
- knowledge/05-temporary-residence/visa-requirements-by-nationality.md
- knowledge/05-temporary-residence/flagpoling-biometrics-medicals.md
- knowledge/14-policy-tracker/ministerial-instructions-and-program-delivery.md
- knowledge/08-inadmissibility/criminality-rehabilitation-arc.md
- knowledge/08-inadmissibility/misrepresentation-s40.md
- By branch, as the tree says: transit-and-visit-purposes.md (business visitors), study-permits.md, iec.md, business-and-self-employed.md, 04-family/spousal-common-law-conjugal.md, 07-citizenship-pr-status/citizenship-proof-bill-c3.md, 07-citizenship-pr-status/pr-card-prtd-residency.md, 06-protection-humanitarian/stca-prra.md

## Workflow
1. Collect: who the client is (foreign national in the US, Canadian citizen in the US, Canadian PR in the US); citizenship(s); US status (citizen, LPR, H-1B, L-1, TN, F-1, other) and expiry; whether already in Canada; goal (visit/remote work, work, study, business, PR, sponsor family, children's citizenship); employer (multinational with a Canadian entity? US-owned business trading with Canada?); occupation and NOC/TEER; job offer in Canada; years of skilled work; education and ECA; language scores; spouse and children (and where each child was born, and when); every arrest, charge, diversion, expungement or DUI in any state or country; any US removal, visa refusal or overstay.
2. Walk the decision tree:
   - Entry document by passport.
   - Visit: business visitor, CUSMA business visitor (after-sales service), remote work for a US employer (visitor status, 6 months).
   - Work: CUSMA professional T36, ICT T37/T38, trader T34, investor T35 (US citizens); C12 ICT (any citizenship); other FTA codes; LMIA. SWAP Working Holidays for US citizens under 36. Spouse: domestic OWP rules only.
   - Where to apply: port of entry if visa-exempt and ready. US citizens and US LPRs are an exception to the end of flagpoling; H-1B/L-1/F-1 holders without a green card are not.
   - Study: US citizens and LPRs can apply at the port of entry.
   - PR: FSW now, CEC after a year in Canada, categories, PNP, Quebec; landing logistics.
   - Canadians in the US: sponsor must show a plan to live in Canada; children born in the US (Bill C-3 dates); PR residency obligation.
   - Asylum: STCA and the 14-day rule -> `/protection-claim-triage`.
3. **H-1B pathway:** check the policy tracker and IRCC on the day. As of 2026-11-17 it is announced (Budget 2025) but NOT open; never present it as open.
4. Run `/clb`, `/fsw`, `/crs`, `/pnp`, `/presence` and `/family-sponsorship-assessor` as needed. Output a table of routes (eligible now / after a step / not eligible) with the gap, timeline and first step for each.
5. Flag DUI or any criminality (serious criminality; rehabilitation or TRP; lawyer if equivalency is unclear). A US expungement or pardon isn't automatically recognized; cannabis is offence-by-offence. Flag misrepresentation risk for undisclosed US arrests, removals or visa refusals.

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
