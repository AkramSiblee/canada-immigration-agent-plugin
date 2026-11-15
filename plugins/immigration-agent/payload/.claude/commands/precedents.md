---
description: Keep the firm's past letters and submissions as anonymised precedents by issue, and find one to start a new draft from
argument-hint: [add FILE | search words | show ID | list]
---
Request: $ARGUMENTS

- Add: `python3 scripts/precedents.py add FILE --issue "study gap" --program study --outcome approved|refused|pending|withdrawn|unknown --case CASE`.
  Always give --case so the client's and family's names are removed. Then read the saved text yourself and point out anything still
  identifying (addresses, employers, schools, rare facts). The consultant edits the file, then runs `precedents.py approve ID`.
- Find: `python3 scripts/precedents.py search WORDS [--program P] [--outcome O]`, then `show ID`.
- Using a precedent: take its structure and arguments only. Write the new letter from the new client's own facts and documents, check every
  legal point against the knowledge base, and never copy facts across files.
- Never add or reuse IRB narratives, affidavits, statements or evidence: they are the person's own words (CLAUDE.md rule 7).
