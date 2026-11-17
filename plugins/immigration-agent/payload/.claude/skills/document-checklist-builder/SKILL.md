---
name: document-checklist-builder
description: Build a document checklist for a specific program and client. Use for any checklist request.
---
# Document Checklist Builder

## Read first
- knowledge/11-forms-fees-processing/forms-directory.md
- knowledge/11-forms-fees-processing/portals-and-submission.md
- Business streams: the province file in knowledge/02-pnp/, knowledge/11-forms-fees-processing/source-of-funds-net-worth.md, knowledge/03-quebec/business-immigration.md

## Business checklists (provincial entrepreneur streams)
Build each from the province file's own list (forms, deadlines and fees differ by province); the stages below are the skeleton. Mark which stage the client is at.
1. **EOI / registration:** passport, language test (validity window set by the stream), education credential (and ECA if required), business ownership or management proof (registration, share certificates, financial statements, tax returns), self-declared net worth, exploratory visit evidence (itinerary, meetings, receipts) where required.
2. **Business Establishment Plan / business plan:** business concept, NAICS code and check against the excluded list, location, market research, investment budget (eligible vs excluded spending), jobs plan (permanent full-time, not related persons, wage), ownership %, purchase file if buying (prior-owner years, valuation at fair market value, site visit, purchase agreement).
3. **Net worth verification:** designated verifier's report; for every asset: title or statement, valuation, how acquired; 5-year (or the stream's) trail of income and transfers; gifts (gift deed, donor's means, date received), loans (agreement, counted net of liability), sale of property (deed, sale proceeds, deposit trail); tax returns; currency conversion date; spouse's share. See source-of-funds-net-worth.md.
4. **Performance agreement:** signed agreement returned by the deadline; deposit if the province requires one; note the date: spending counts only after it.
5. **Work permit (C60):** province's work permit support letter, Employer Portal offer and compliance fee, IRCC application within the province's deadline; family permits; then arrival.
6. **Arrival meeting / landing:** arrival report or meeting within the province's window, proof the family lives in the province (lease, school enrolment), company registration, business bank account, licences.
7. **Nomination request / final report:** operating period met; accountant's review engagement or special-purpose report; proof of investment (invoices, bank statements), payroll records for each new employee (T4, ROE, citizenship/PR proof, not related), active management proof; proof of residence in the province.
8. **PNP-based PR (IRCC):** nomination certificate; IMM 0008 and schedules (see forms-directory); police certificates; medicals; proof of funds not required for nominees unless stated; fees (fee-schedule.md); work permit extension (T13) if nominated and permit is expiring.

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
