---
description: Sort a case's documents into IRCC checklist order, one upload-ready PDF per item
argument-hint: [case id, and program if not the case's own]
---
Run `python3 scripts/package.py build CASE [--program P] [--max-mb 4]` for: $ARGUMENTS

1. If the case has no extraction yet, run `python3 scripts/doc_extract.py extract --case CASE` first: matching is better with document types than with file names alone.
2. Run the build. It writes a new dated folder in `05-forms-submissions/` and never changes the originals in `03-documents`.
3. Report: the package folder, each item's PDF with its size, required items missing, and files left in `99-unsorted/`.
4. Remind the user to open every PDF before uploading (right document, right person, readable, complete, translated, in date), and that IRCC forms are copied unchanged and uploaded as they are.

A file goes to the first checklist item it matches, and letters of explanation go with the item their file name matches: suggest clearer file names if something landed in the wrong item or in 99-unsorted.
