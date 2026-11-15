---
description: Track each submitted file against IRCC's published processing times, and draft the case-specific enquiry when one is past them
argument-hint: [check | set CASE --line LINE | enquiry CASE]
---
Request: $ARGUMENTS

1. Track a file: `python3 scripts/ptimes.py set CASE --line LINE [--submitted YYYY-MM-DD]`. Lines are IRCC's own: `ptimes.py lines --find TEXT`.
   PR and citizenship: cec, fsw, pnp-ee, pnp-base, spousal-abroad-roc, spousal-canada-roc (-quebec for Quebec), pgp-roc, citizen-grants...
   Visas and permits from outside Canada: study:IN, work:PH, visitor-outside-canada:NG, supervisa:IN (country of residence code).
   In Canada: work_extension, study_extension, visitor_extension, pr_card/existing_pr. The submitted date comes from --submitted or the
   first "submitted" event in updates.csv.
2. `python3 scripts/ptimes.py check` reads IRCC's times (public; nothing about clients is sent) and lists every tracked file, marking those
   past the posted time. The daily alerts do this once a week. Check `knowledge/11-forms-fees-processing/processing-times.md` for context.
3. For a file past the time: check the client's IRCC account first (a request may be waiting). Then `python3 scripts/ptimes.py enquiry CASE`
   drafts the web form text, shown inline; fill in the UCI and date of birth. The consultant sends it; record it with `ptimes.py enquired CASE`.
   IRCC says another enquiry won't speed things up: no repeat within 30 days. A long delay can mean mandamus: Federal Court, refer to a lawyer.
