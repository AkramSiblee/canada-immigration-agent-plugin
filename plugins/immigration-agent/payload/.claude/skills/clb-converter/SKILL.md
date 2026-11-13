---
name: clb-converter
description: Convert IELTS, CELPIP, PTE Core, TEF Canada or TCF Canada scores to CLB/NCLC levels and check program language minimums. Use for any test-score-to-CLB question.
---
# CLB Converter

## Read first
- knowledge/01-federal-economic/language-test-equivalency.md

## Workflow
1. Get the test and the four scores (speaking, listening, reading, writing). Confirm the test version: IELTS General Training (not Academic), CELPIP-General, PTE Core (not Academic), TEF Canada (ancien score column, not /699), TCF Canada.
2. Run `python3 scripts/clb.py <test> --speaking S --listening L --reading R --writing W` and show the result inline.
3. Say which minimums are met (FSW, CEC by TEER, FST) and the FSW language points. Flag a test date over 2 years old (at profile creation and at the PR application).
4. Offer next steps: `/crs` with these levels, `/fsw`, and which single ability to retake for the biggest gain.

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
