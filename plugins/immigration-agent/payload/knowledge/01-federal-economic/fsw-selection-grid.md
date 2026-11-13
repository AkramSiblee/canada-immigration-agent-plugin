---
domain: 01-federal-economic
topic: fsw-selection-grid
status: verified
last_verified: 2026-11-13
confidence: H
review_every_days: 90
sources:
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/federal-skilled-workers/six-selection-factors-federal-skilled-workers.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/documents/education-assessment.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/documents/proof-funds.html
---
# Federal Skilled Worker: 67-point selection grid

Sources: six selection factors page (page 2026-11-03), ECA page FSW points table, proof of funds page (2026-10-16); all read 2026-11-13 (H).
Calculator: `python3 scripts/fsw.py` (data: `templates/fsw/selection-grid.json`). FSW points decide **eligibility**; CRS decides invitations.

## Pass mark: 67 / 100

| Factor | Max | Points |
|---|---|---|
| Language | 28 | First official language per ability: CLB 7 = 4, CLB 8 = 5, CLB 9+ = 6 (max 24); below CLB 7 in any ability = not eligible. Second official language CLB 5+ in all four = 4 |
| Education | 25 | PhD 25; master's 23; professional degree for a licensed profession 23; two or more credentials (one 3+ yrs) 22; bachelor's / 3+ yr program 21; two-year 19; one-year 15; secondary 5. Foreign: ECA under 5 years old |
| Experience | 15 | 1 yr 9; 2-3 yrs 11; 4-5 yrs 13; 6+ yrs 15 (TEER 0-3, paid, in Canada or abroad) |
| Age | 12 | 18-35: 12; 36: 11; 37: 10; 38: 9; 39: 8; 40: 7; 41: 6; 42: 5; 43: 4; 44: 3; 45: 2; 46: 1; 47+ or under 18: 0 (age on the day the application is received) |
| Arranged employment | 10 | Job offer 1+ yr, one employer, continuous, paid, full-time (30+ h/week), not seasonal, TEER 0-3, received before applying. **No LMIA needed from 2026-11-03**; officer still assesses genuineness |
| Adaptability | 10 | Spouse language CLB 4+ all four 5; your 2+ yrs full-time study in Canada 5; spouse study in Canada 5; your 1+ yr skilled work in Canada 10; spouse 1+ yr work in Canada 5; arranged employment 5; relative in Canada (18+, citizen/PR: parent, grandparent, child, grandchild, sibling, aunt/uncle, niece/nephew) 5. Total capped at 10 |

## Minimum requirements (before the grid)
- 1 year continuous full-time (or 1,560 hours; max 30 h/week counted) in one NOC, TEER 0-3, within the last 10 years; lead statement and most main duties met.
- CLB/NCLC 7 in all four abilities (first official language), approved test under 2 years old.
- Canadian credential, or foreign credential plus ECA.
- Admissible; plan to live outside Quebec.

## Proof of funds (FSW, FST)
- Family of 1 $15,263; 2 $19,001; 3 $23,360; 4 $28,362; 5 $32,168; 6 $36,280; 7 $40,392; each more $4,112 (updated 2025-07-07).
- Family size counts the spouse and dependent children even if not coming. Funds available at application and at visa issue; not borrowed; no home equity.
- Not needed: CEC, or authorized to work in Canada with a valid job offer (upload a letter explaining which).
