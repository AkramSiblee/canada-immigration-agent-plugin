---
description: File an IRCC letter (AOR, biometrics, medical, procedural fairness, PPR, refusal...) in its case, add its deadline and record it for the client update
argument-hint: [file or folder, case id; or "gmail" to look for IRCC emails]
---
Request: $ARGUMENTS

1. Find the letter(s):
   - A file or folder named: use it. Nothing named: `python3 scripts/ircc_letters.py scan` reads every letter in Input/.
   - "gmail" or "email": if the Gmail tools are connected, search the consultant's mail for IRCC messages from the last 14 days
     (for example `from:(cic.gc.ca OR canada.ca) newer_than:14d`, or what the consultant asks). Show sender, date and subject only, and
     ask which to use. Save chosen attachments to `.extraction/mail/` (never into Input/), then continue with step 2.
     IRCC mostly emails "a new message in your account": the letter itself is in the IRCC account, which the agent never logs in to.
     Ask the consultant to download it and drop it in Input/.
   - Fraud check: a letter or email not from an IRCC or canada.ca address, asking for payment, or with an odd link: flag it, don't file it.
2. `python3 scripts/ircc_letters.py read FILE`: type, letter date, time limits with the letter's own words, application number, matching case.
   A scanned letter has no text: read the PDF yourself (vision) and give the facts with --type, --date and --due.
3. Show the result and ask the consultant to confirm the case, the type, the letter date and the deadline before filing.
4. `python3 scripts/ircc_letters.py file FILE --case CASE [--type T] [--date D] [--due D | --no-deadline]`. It copies the letter into
   06-correspondence, adds the deadline, records the event in updates.csv and logs it. Input/ is never changed.
   It refuses to guess a deadline: if the letter's limit can't be counted, read the letter and pass --due.
5. Then, as the script says:
   - Client update (Code s.22(3)): `python3 scripts/updates.py notify CASE`, shown inline. If case.md has `client_language`, offer /translate.
   - Procedural fairness: /pf-response. Refusal: /refusal, and the JR deadline (refer Federal Court to a lawyer, CLAUDE.md rule 4).
   - Medical done, ITA received: record the date with `validity.py add` so it is tracked (`/validity`).
Check each date against the letter itself. Dates read by the script are drafts.
