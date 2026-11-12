# Templates
- `firm/` : agreements and letters used by `scripts/firm.py`. Rewrite them in your own words if you like. Keep every `@covers` line: it marks a clause the Code of Professional Conduct requires, and the script refuses to produce an agreement when one is missing. Placeholders: `{firm.*}` from your profile, `{client.*}` from the case, `{terms.*}` for this client, `{?key}` optional. `@if key` ... `@endif` shows a section only when it has a value.
- `case-file/` : the files copied into every new case.
- `form-specs/` : questions for the IRCC form worksheets, and each form's current version.
- `checklists/` : IRCC's official document checklists, one CSV per program (`index.csv` gives each source, version and the programs it fits). Columns: item, `always` or `if` with a condition, and how a case document is recognized (`type:` document type, `form:` IRCC form number, `file:` file-name pattern; blank means confirm by hand). Re-read IRCC's checklist and update the CSV when IRCC publishes a new version.
- `intake-form-consent.txt` : the AI and privacy authorization on the intake form, reused as the technology notice in agreements.
