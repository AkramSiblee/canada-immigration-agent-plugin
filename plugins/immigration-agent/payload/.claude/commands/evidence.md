---
description: Organise spousal or partner relationship evidence into a dated timeline and upload-ready PDFs (photos, contact, travel, living together)
argument-hint: [case id]
---
Request: $ARGUMENTS

1. Read `knowledge/04-family/spousal-common-law-conjugal.md` (evidence, IMM 5533 limits). The evidence goes in the case's
   03-documents/relationship/ (any subfolders), or give --folder.
2. `python3 scripts/evidence.py timeline CASE`: dates every item (camera date, date in the name, date in the document, or file date to
   confirm), sorts it into categories and saves an Excel timeline. Report the span, the counts, gaps of a year or more, and dates to confirm.
3. The consultant (or client) checks the timeline: marks up to 20 photos Include = yes, sets "no" on anything to leave out, and adds
   captions (date, place, who). Never write captions that tell the relationship's story: that is the client's own account in IMM 5532.
4. `python3 scripts/evidence.py build CASE`: photos PDF (two per page, captioned), one PDF per other category, and an index, in
   05-forms-submissions/relationship-evidence/. Relay any category over a limit (proof of contact 10 pages), and offer /pdf to convert
   Word files or compress to IRCC's upload size. Ask for an explanation from the client where the evidence has gaps.
