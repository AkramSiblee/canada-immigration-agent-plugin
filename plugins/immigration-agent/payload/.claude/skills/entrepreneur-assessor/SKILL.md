---
name: entrepreneur-assessor
description: Assess a business owner or investor against every open provincial and Quebec entrepreneur stream (net worth, investment, jobs, points, compliance risks, C60 work permit, next steps). Use for any entrepreneur, investor, business purchase or self-employed PR question.
---
# Entrepreneur Assessor

## Read first
- knowledge/12-decision-trees/business.md (routing: provincial entrepreneur, Quebec, temporary only, owner-operator LMIA, legacy SUV/Self-Employed)
- knowledge/02-pnp/comparison-table.md ("Entrepreneur streams" table: status and headline figures)
- The province files for every stream in that table that is open: 02-pnp/british-columbia.md, alberta.md, manitoba.md, new-brunswick.md, nova-scotia.md, prince-edward-island.md, newfoundland-labrador.md, northwest-territories.md, regional-community-streams.md
- knowledge/03-quebec/business-immigration.md
- knowledge/01-federal-economic/business-and-self-employed.md
- knowledge/05-temporary-residence/work-permits-lmia-exempt.md (C11, C60, T13 rows)
- knowledge/11-forms-fees-processing/source-of-funds-net-worth.md
- knowledge/13-case-law/business-immigration-refusals.md
- knowledge/14-policy-tracker/announced-for-2027.md (federal entrepreneur pilot; 2027 workers cohort)

## Workflow
1. **Collect the profile** (ask only for what's missing): age; citizenship and country of residence; marital status, spouse and children (and where the family will live); personal net worth (assets minus liabilities, own and spouse's share); liquid funds; how each asset was acquired (business income, salary, sale, gift, inheritance, loan) and over what years; business ownership history (company, %, years, role, turnover, employees) or senior management years; education (highest credential, any Canadian study); language test, date and scores (run `/clb`); target province or community; business idea (new business or purchase, sector/NAICS, location, planned investment, planned jobs); exploratory visit made?; past refusals, overstays, criminality; any prior PNP application.
2. **Route first** with the business decision tree. If the client wants temporary residence only, or is a US/Mexican trader or investor, or already has a Canadian job offer from their own company, say so and send to the right branch (C11, T34/T35, C12/ICT, owner-operator LMIA) before scoring PR streams.
3. **Status gate:** for each stream, take status from the province file and the policy tracker. Never score a closed or paused stream as an option; list it under "Not open" with the date and source. Start-Up Visa is closed (final deadline 2026-06-30), Self-Employed is paused, the federal entrepreneur pilot is announced but not launched; re-check the tracker on the day.
4. **Per open stream** (provincial and Quebec), output one block:
   - Eligible: Yes / No / Near. If No, the first failing criterion (e.g. "net worth $420k < $600k minimum").
   - Points estimate (where the stream has an EOI grid), with the factors that drive it and the latest published selection score if the file has one. Mark it an estimate.
   - Investment and jobs plan against the minimums, with the margin (e.g. "investment $350k vs $300k minimum: margin $50k; only spending after the performance agreement counts").
   - Ineligible-business check: compare the sector and model against the stream's excluded list (e.g. NAICS 72 exclusions, passive investment, home-based, real estate, franchises/purchases with conditions).
   - Compliance risks: spending before the performance agreement; related-person or family employees; family not living in the province; source of funds gaps (gifts, loans, unexplained deposits, short history); investment over half of net worth; active management not shown; purchase rules (prior owner years, fair market value, exploratory visit).
   - Work permit: C60 with the province's support letter before nomination; T13 (R204(c)) after nomination if the stream allows it. Never C11 for a PR-intent client (C11 is temporary only).
   - Fees, deadlines and the minimum operating period before the nomination request.
   - Next steps (EOI, verifier/net worth report, exploratory visit, business plan).
5. **Rank** the open streams: eligible now first (by margin and points), then near-eligible with the gap and the cheapest fix (language retest, exploratory visit, location change, larger investment).
6. **Flag** every time: source-of-funds and misrepresentation risk (IRPA s.40 and the province's own misrepresentation bar); undeclared family members (IRPR 117(9)(d)); ghost consultants or "guaranteed" business buyer-seller schemes; offers to fund job creation or salaries back to the investor. Provincial refusals are challenged in the provincial superior court (judicial review) and IRCC refusals in Federal Court: both are lawyer referrals.
7. **Output:** a summary table (stream | status | eligible | failing criterion or margin | points estimate | WP code | fee), then the per-stream blocks, then "Not open" and "To verify on the day". Cite file + source URL + last_verified for every figure. Offer `/checklist` for the business checklists and `/pr-plan` for the client-ready document.

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, minimums, intake status, draw scores, allocations), verify on the official source before advising, then update the file.
- Never present a closed, paused or announced program as open. Quote figures exactly as the file has them; if a figure is marked unconfirmed or L, say so.
- Net worth and investment figures are the client's claims until a designated verifier confirms them; say so in the output.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, provincial superior court judicial review, criminal equivalency, corporate or tax structuring beyond immigration advice.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
