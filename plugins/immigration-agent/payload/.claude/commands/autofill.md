---
description: Fill an IRCC form's official PDF with the worksheet answers that are ready
argument-hint: [form, person, and case id]
---
Request: $ARGUMENTS

1. Build or refresh the worksheet first (`/prefill`), and resolve what you can: only answers marked Ready (and firm-profile details) are written.
2. Run `python3 scripts/autofill.py fill --form imm5257 --person "Full Name" --case CASE`. It downloads the current blank from IRCC into `forms-cache/` (or use `--blank`), writes the answers, and reads the form back to confirm each one landed on the right question. `--include-confirm` also writes answers read from images.
   - Passport number: written in full automatically when it is in `client-facts.csv` or the passport PDF has text. If the output says "the passport is a scan", render the passport page (`doc_extract.py render`), read the number from the code lines at the bottom (check digit included), and rerun with `--passport-number NUMBER`. It is written only if it matches the number checked at extraction; never type the full number into chat output, the worksheet or any other file.
3. Report the saved file (in the case's `05-forms-submissions`), how many answers were filled and confirmed, and every answer left for the consultant with its reason.
   - Answers in parts (client-facts.csv keys): `employer.Name`, `employer.Address`, `work_location.Province|City|Address`,
     `job_title.Title|Duties`, `work_period.FromDate|ToDate`, `study_address.Province|City|Address`, `pal.Number|ExpiryDate`,
     `caq.Number|ExpiryDate`, `spouse_name.FamilyName|GivenName`, `other_name.FamilyName|GivenName`. Whole answers like
     "2027-03-01 to 2029-02-28" or "Cook: duties" are split automatically; the spouse's names come from the family facts.
   - Tables: `employment.1.From|To|Occupation|Employer|City|Country|Province` and `education.1.From|To|Field|School|City|Country`
     (YYYY-MM; To "present" stays blank). Rows that don't fit are listed: attach them on a separate sheet.
   - Yes/No answers with details ("Yes: KHATUN") set the box and put the details in the details field; "Check" lines show where Yes/No
     was read from details. IMM 5476 section B comes from the firm profile (name and Canadian address split into boxes).
   - Previous countries: `previous_countries.1.Country|Status|From|To` (full dates). The questionnaire writes these rows, and the education and employment rows, by itself; older one-line answers are read back into rows only when every line is clean (each unread line is reported).
   - "City, Province" answers for the place of work and the school are split when a Canadian province or territory is named; `job_duties` fills the duties box. Answers longer than a box are reported, never cut.
   - A Yes to post-secondary education or previous countries is written only with at least one row; otherwise both are left blank and reported.
   - "No expiry" leaves an expiry date blank; PAL/TAL or CAQ text such as "Not required" is never written in a number box.
   - Re-running with the same answers saves nothing ("Unchanged").
4. Remind: open it in Adobe Acrobat or Reader, check every page, fill the blanks (joined fields like addresses, split dates, country codes from passports), click Validate to make the barcodes, and sign. Conflicts, open questions, signatures, and hidden numbers that cannot be matched to the number on file (passport, national ID, green card) are never filled.
5. If the consultant says a form looks corrupt, blank or shows "Please wait...": it was opened in a web browser (Edge, Chrome), Preview or another viewer. IRCC forms work only in Adobe Acrobat or the free Adobe Acrobat Reader: right-click the file > Open with > Adobe Acrobat. The autofill keeps IRCC's certification valid (Adobe shows "Certified by Immigration, Refugees and Citizenship Canada"). If autofill stops with "could not be filled safely", nothing was saved: fill that form by hand. If it stops because IRCC has a newer version of the form, nothing was filled: the consultant fills the new version by hand from the worksheet answers, checking every question, until an agent update covers it (see /watch). IMM 5748 (income table) is never autofilled. Portal-only applications (Express Entry, PR Portal, online citizenship) can't be autofilled.
