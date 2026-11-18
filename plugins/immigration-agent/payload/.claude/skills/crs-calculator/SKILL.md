---
name: crs-calculator
description: Calculate Express Entry CRS including the Labour Market Integration Factor and show what-if improvements. Use for any CRS score question.
---
# Crs Calculator

## Read first
- knowledge/01-federal-economic/crs-scoring.md
- knowledge/01-federal-economic/category-draws-history.md

## Workflow
1. Collect age or date of birth (and the expected ITA date), education and ECA, language (CLB per ability; convert with `scripts/clb.py`), Canadian/foreign experience, high-wage Canadian experience by level and months, job offer NOC, spouse (accompanying? ECA? test? Canadian experience), PNP, sibling, French, Canadian study, certificate of qualification
2. Run `python3 scripts/crs.py ... --what-if` (see its --help). Never add the grid up by hand. It takes the higher of Canadian experience and the high-wage job offer (cap 150/140), gives spouse education points only with `--spouse-eca`, applies the transferability caps and the French bonus, and warns when a birthday before the expected ITA lowers age points. The high-wage level comes from the occupation (`python3 scripts/crs.py --noc NOC`), never from the client's pay.
3. Category eligibility: `python3 scripts/category_check.py NOC` (2026 category lists; 12 months in 3 years, need not be continuous).
4. Show the breakdown and total; compare with the latest round cut-off in category-draws-history.md (rounds JSON; no round after #453 as of 2026-11-17: re-check); list the ranked levers from --what-if.

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
