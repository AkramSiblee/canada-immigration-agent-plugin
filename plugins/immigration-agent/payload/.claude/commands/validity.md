---
description: Track how long language tests, ECAs, medicals, police certificates, Express Entry profiles and ITAs stay valid, against the planned filing date
argument-hint: [case id, documents and dates]
---
Request: $ARGUMENTS

1. Rules: `python3 scripts/validity.py rules` (each with its knowledge file and check date). Read `knowledge/01-federal-economic/express-entry.md`
   first, and if it is stale, verify on canada.ca before relying on a rule (CLAUDE.md rules 1-2). Other programs, provinces and visa offices
   can set their own rules: check the instructions for the application at hand.
2. Record each document's own date (test date, ECA issue date, medical exam date, police certificate issue date, profile date, ITA date):
   `python3 scripts/validity.py add CASE DOC --date YYYY-MM-DD --person "Name" [--note TEXT]`.
   After /extract, `python3 scripts/validity.py import CASE` adds the test, ECA, police and ITA dates it read, as drafts to confirm.
3. Set the plan: `python3 scripts/validity.py plan CASE --file-by YYYY-MM-DD [--land-by YYYY-MM-DD]`.
4. `python3 scripts/validity.py show CASE` and present the table inline: anything expired, or running out before the planned filing or
   landing date, comes first, with what to do (file earlier, retest, new medical, new police certificate).
The daily alerts and the dashboard warn 90 and 30 days ahead, and at once when a document runs out before the planned date.
