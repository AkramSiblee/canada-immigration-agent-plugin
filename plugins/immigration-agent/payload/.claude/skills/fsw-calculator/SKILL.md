---
name: fsw-calculator
description: Score the Federal Skilled Worker 67-point grid, check minimum requirements and proof of funds, and show what would add points. Use for FSW eligibility questions.
---
# FSW 67-Point Calculator

## Read first
- knowledge/01-federal-economic/fsw-selection-grid.md
- knowledge/01-federal-economic/language-test-equivalency.md
- knowledge/01-federal-economic/express-entry.md

## Workflow
1. Collect: age on the planned application date, highest education (and ECA status), first official language levels or test scores, second language, years of skilled TEER 0-3 work in the last 10 years (one NOC, continuous), job offer, adaptability facts (spouse language, study or work in Canada for each spouse, relatives in Canada), family size and settlement funds, work authorization in Canada.
2. Run `python3 scripts/fsw.py` with those facts (see `--help`); with test scores use `--test ielts --scores S L R W`.
3. Show the grid, pass/fail against 67, minimum requirements, proof of funds, and the ranked "what would add points" list inline.
4. Flag anything unconfirmed (ECA not done, experience not continuous, duties not matching the NOC lead statement). Then suggest `/crs` for invitation chances: the grid only decides eligibility.

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
