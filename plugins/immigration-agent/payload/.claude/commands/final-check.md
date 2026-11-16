---
description: Check the finished IRCC forms in a case before submitting (blanks, logic, consistency, passport number)
argument-hint: [case id]
---
Run `python3 scripts/final_check.py check CASE` for: $ARGUMENTS

It checks each person's forms separately (spouse and children are not compared with the principal's own answers), using the newest
version (-v2, -v3 ...) of each form per person, and names the file it checked. `--person "Name"` checks one person. Across people it
checks that the spouse named on each form matches the spouse's own forms, and that children on the family forms match their applications.
For each form:
- required questions still blank (conditional ones only when they apply), and a Yes whose details boxes are empty (national ID, US green card)
- family table rows missing a name, date of birth, country of birth or address
- logic: passport valid past the departure date, dates in order, a visit over 6 months, family ages, marriage after age 14
- the same name, date of birth and marital status on every form, plus the extractor's cross-checks
- the passport number on the form against the passport in 03-documents (by fingerprint; never shown)
- answers changed or typed in Adobe since the worksheet, for a last confirmation

Report "Must fix" items first. Signatures are never checked: remind the consultant to validate each form in Adobe, then sign and date it. A clean result is not a guarantee the file is complete. The readiness report (`/readiness`) includes the same results in its Final forms tab.
