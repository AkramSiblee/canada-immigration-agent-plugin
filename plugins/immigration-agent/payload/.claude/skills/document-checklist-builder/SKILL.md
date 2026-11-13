---
name: document-checklist-builder
description: Build a document checklist for a specific program and client. Use for any checklist request.
---
# Document Checklist Builder

## Read first
- knowledge/11-forms-fees-processing/forms-directory.md
- knowledge/11-forms-fees-processing/portals-and-submission.md

## Workflow
0. If the program has a stored official checklist (`templates/checklists/index.csv`: visitor visa, study permit and work permit applied outside Canada, Express Entry, adult, minor and proof of citizenship, parents and grandparents, spousal, PR card, super visa), start from it, not from memory. For an open case, run `python3 scripts/readiness.py checklist CASE` to see what is found, missing, conditional or to confirm by hand, with the progress percentage. Check the checklist's `read` date and IRCC's page before relying on it.
   - The same checklist is the case's progress tracker in the dashboard. When the consultant confirms what applies, record it so both agree: `readiness.py mark CASE <no> received|missing|not-needed|clear`, and add visa-office or client-specific extras (e.g. IMM 5890 items) with `readiness.py add CASE "Document" --note "source"`. Only on the consultant's instruction; never mark an item received you have not seen in the file.
1. Pick program and client facts (family, history, province)
2. List forms, supporting docs, translations, police certificates, medicals, photos
3. Mark client-specific items and validity windows
4. Output: checklist table with owner and due date

## Guardrails
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
