---
name: application-package-qa
description: Pre-submission QA of an application package. Use before filing.
---
# Application Package Qa

## Read first
- knowledge/11-forms-fees-processing/common-returns-and-refusals.md
- knowledge/11-forms-fees-processing/forms-directory.md

## Workflow
1. Run the readiness report: `python3 scripts/readiness.py report CASE` (add `--form imm1234` for each form if the program's defaults don't fit). It joins extraction flags, form worksheet answers, intake steps, deadlines, client updates and client account issues. Report the "Must fix before filing" items first.
   - Default forms come from the program. IMM 5409 is added when the program or the client's marital status (client-facts.csv) says common-law; IMM 5562 is included for parents and grandparents files. A super visa file gets the visitor forms, not the sponsorship forms.
   - Super visa files: the report checks the host's income from the Notices of Assessment. Put `family_size` in client-facts.csv, and `application_date` and `visitor_income` (Canadian dollars) if known. The same check runs on its own with `python3 scripts/doc_extract.py supervisa REPORT --family-size N [--applying YYYY-MM-DD] [--visitor-income X]`.
   - The report compares the case's documents with IRCC's official checklist for the program (`templates/checklists/`): a required item with no matching file is a must-fix; conditional items and items that can't be detected are listed on the Checklist tab to tick by hand. "Found" only means a matching file exists: still check it is the right, current, complete and translated document. `readiness.py checklist CASE` shows the same in the terminal.
   - The report also fact-checks drafted letters (names with letter, explanation, LOE or submission) in 05-forms-submissions and 06-correspondence against the extracted documents.
   - Its Final forms tab checks the finished IRCC forms in 05-forms-submissions as edited in Adobe: blanks, Yes answers with empty details, family rows, passport validity and date logic, the same core answers across forms, the passport number against the passport, and edits since the worksheet. `/final-check CASE` runs it on its own.
   - When the file is ready, `python3 scripts/package.py build CASE` (or `/package`) arranges the documents in checklist order, one PDF per item under the 4 MB limit, with IRCC forms copied unchanged and an index of what went where.
2. Then check what the report can't see: form versions on IRCC's site on filing day, fees, photo specifications, translations with translator declarations, validity of police certificates and medicals, and the document checklist for the program.
3. Check declared family and history gaps across all forms; check IMM 5476 is signed by both.
4. Output: pass/fail list with fixes, citing the report file.

## Guardrails
- Never tell the RCIC a file is ready to file. Say what was checked, what is open, and that the final review is theirs.
- Read listed knowledge files first; check `last_verified` and `review_every_days`. If stale, needs-seed, or the fact is perishable (fees, caps, cut-offs, processing times, allocations, intake status), verify on the official source before advising, then update the file.
- Cite knowledge file + source URL + last_verified. Mark confidence H/M/L.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases.
- Decision support for a licensed RCIC; never guarantee outcomes. Be concise, bullets first.
