---
name: pr-plan-builder
description: Build a client-ready PR Masterplan (full eligibility assessment) comparing CRS, FSW grid, language levels, PNP matches and family or temporary routes, with a step-by-step timeline, as a Word document on the firm's letterhead. Use for a full eligibility assessment or PR plan.
---
# PR Plan Builder (eligibility assessment + PR Masterplan)

## Read first
- knowledge/12-decision-trees/ (skilled-worker, temp-to-pr, family, us-to-canada as relevant)
- knowledge/01-federal-economic/crs-scoring.md, express-entry.md, fsw-selection-grid.md, language-test-equivalency.md
- knowledge/02-pnp/comparison-table.md
- knowledge/14-policy-tracker/ (every route must be open; never present closed or paused programs as open)

## Workflow
1. Collect the full profile (as for /crs and /fsw) plus goals, preferred province, budget and deadlines (permit or passport expiry). Use the case file if one exists (`cases/`, client-facts.csv).
2. Calculate: `scripts/clb.py` for each test; `scripts/fsw.py`; CRS with the crs-calculator skill (show the breakdown); PNP matches with the pnp-matcher skill; the us-pathway-finder skill if US-based; family or Quebec routes if relevant.
3. Compare 3-6 pathways: fit (Strong / Possible / Not now), why, gap to close, realistic timeline, next step. Compare the CRS with recent draw cut-offs for the relevant category (verify the latest draws online; they are perishable).
4. Write a step-by-step plan by stage (e.g. "Months 1-2: retake IELTS, start ECA"), documents to gather, risks (misrepresentation, undeclared family IRPR 117(9)(d), expiring status, inadmissibility) and assumptions.
5. Save the plan as JSON in the scratchpad (format in `scripts/pr_plan.py`) and run `python3 scripts/pr_plan.py build plan.json --folder <Input subfolder or general> [--case CASE]`. It writes Output/<folder>/YYYY-MM-DD-pr-plan.docx on the letterhead (and a copy in the case's 04-advice). Show the summary and pathway table inline too.
6. Tell the consultant it is a draft for their review before it goes to the client.

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
