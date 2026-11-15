---
description: Prospect pipeline: enquiries, paid consultations, quotes and sign-ups, with follow-ups and where prospects drop off
argument-hint: [add NAME | move ID STAGE | list | report]
---
Request: $ARGUMENTS

- New enquiry: `python3 scripts/prospects.py add "Full Name" --source referral|website|social|walk-in|... --program TEXT --contact TEXT`.
  It runs the conflict check; show any match and ask the consultant to review it before booking (Code ss.15-18).
- Move along: `python3 scripts/prospects.py move ID STAGE` with booked (--fee), paid (--amount), consulted, quoted (--amount), signed (--case),
  declined / not-taken / no-show / lost (--reason). Relay what the script says:
  - booked: a written consultation agreement before the consultation (Code s.23): offer /agreement consultation-agreement.
  - paid: a fee paid in advance goes to the client account (Code s.32(a)).
  - consulted: offer /consult-notes for the record of the consultation.
  - signed: open the case first (`case.py new`), then a service agreement (/agreement) and IMM 5476.
  - not-taken: offer a non-engagement letter (/agreement non-engagement-letter). The name is added to the conflict list.
- `list` shows open prospects and who is due a follow-up; `report` saves the funnel, conversion by source and reasons for not signing
  (Excel in Output/general). Suggest where the firm loses prospects, from the numbers only.
