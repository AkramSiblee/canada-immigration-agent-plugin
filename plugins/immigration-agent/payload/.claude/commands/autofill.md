---
description: Fill an IRCC form's official PDF with the worksheet answers that are ready
argument-hint: [form, person, and case id]
---
Request: $ARGUMENTS

1. Build or refresh the worksheet first (`/prefill`), and resolve what you can: only answers marked Ready (and firm-profile details) are written.
2. Run `python3 scripts/autofill.py fill --form imm5257 --person "Full Name" --case CASE`. It downloads the current blank from IRCC into `forms-cache/` (or use `--blank`), writes the answers, and reads the form back to confirm each one landed on the right question. `--include-confirm` also writes answers read from images.
3. Report the saved file (in the case's `05-forms-submissions`), how many answers were filled and confirmed, and every answer left for the consultant with its reason.
4. Remind: open it in Adobe Acrobat or Reader, check every page, fill the blanks (joined fields like addresses, split dates, country codes from passports), click Validate to make the barcodes, and sign. Conflicts, open questions, masked numbers and signatures are never filled.
5. If the consultant says a form looks corrupt, blank or shows "Please wait...": it was opened in a web browser (Edge, Chrome), Preview or another viewer. IRCC forms work only in Adobe Acrobat or the free Adobe Acrobat Reader: right-click the file > Open with > Adobe Acrobat. The autofill keeps IRCC's certification valid (Adobe shows "Certified by Immigration, Refugees and Citizenship Canada"). If autofill stops with "could not be filled safely", nothing was saved: fill that form by hand. IMM 5748 (income table) is never autofilled. Portal-only applications (Express Entry, PR Portal, online citizenship) can't be autofilled.
