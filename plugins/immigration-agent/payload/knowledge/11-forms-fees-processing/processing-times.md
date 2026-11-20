---
domain: 11-forms-fees-processing
topic: processing-times
status: verified
last_verified: 2026-11-19
confidence: H
review_every_days: 30
sources:
  - https://www.canada.ca/content/dam/ircc/documents/json/data-ptime-non-country-en.json
  - https://www.canada.ca/content/dam/ircc/documents/json/flpt-en.json
  - https://trenityconsultants.com/ircc-processing-times-2026/
  - https://www.getnorthpath.com/tools/processing-times
  - https://www.y-axis.com/news/canada-updates-processing-times-express-entry-provincial-nominee-programs/
  - https://www.canada.ca/content/dam/ircc/documents/json/data-ptime-en.json
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/corporate-initiatives/levels/inventories-backlogs.html
---
# Processing times

## Must cover
- By category with date checked (use IRCC tool)

## Current rules
**Always check the IRCC tool on the day you advise. Times change weekly.** IRCC JSON "lastupdated": **2026-11-18** (visas, permits, other lines); PR and citizenship estimates **2026-11-17**. Read 2026-11-19. The dashboard's "IRCC data" page shows every line from `templates/ircc/processing-times*.csv` (built by `scripts/ircc_times.py build`).

### Temporary residence from outside Canada (by country of residence; examples)
| Country | Visitor visa | Study permit | Work permit | Super visa |
|---|---|---|---|---|
| India | 31 days | 7 weeks | 10 weeks | 88 days |
| China | 49 days | 12 weeks | 4 weeks | 90 days |
| Philippines | 23 days | 5 weeks | 10 weeks | 97 days |
| Nigeria | 98 days | 11 weeks | 10 weeks | 27 days |
| USA | 18 days | 4 weeks | 3 weeks | 75 days |
| UK | 19 days | 3 weeks | 5 weeks | 97 days |
| France | 28 days | 2 weeks | 2 weeks | 99 days |

- **All countries, all four:** `templates/ircc/processing-times-country.csv` (dashboard "IRCC data" page; IRCC data lastupdated 2026-11-18). Visitor and super visa also in 05-temporary-residence/visitor-country-reference.md.

### PR and citizenship (IRCC inventory page, decisions Sep 2025-Aug 2026)
- FSW/CEC (EE): about **76%** within the 6-month standard; about 50% in 5 months or less.
- Spouses/partners/children: about **15 months**.
- PNP, citizenship grant and PR card: see the official estimates below. PGWP and PGP: check the IRCC tool.

### Applications already in the queue (IRCC flpt-en.json, updated 2026-11-17, read 2026-11-19) (H)
- Filed February 2026, estimated time left and people ahead: CEC about 1 month, about 7,100; FSW about 1 month, about 9,600; PNP-EE 3 months, about 6,500. Check by program and month at each use.
- IRCC: no news means still processing; web form is for files over the normal time, and another web form won't speed things up (web form page 2026-06-01). Calling doesn't help.
- Non-routine PR causes include outdated contact details, late documents, a dependant turning 18, added dependants, an expired medical needing resubmission (exams for all must be valid together), interviews, background checks, admissibility issues (processing times page 2026-10-30).
- Delay escalation: mandamus is Federal Court, so lawyer only. 2025-26 Federal Court mandamus reports reviewed involve multi-year delays (secondary, Conf. M; judgments not read).

### Notes
- Ebola (2026-05-27 to 23:59:59 ET 2026-11-27): applications not finalized for foreign nationals whose last country of residence is DRC, South Sudan or Uganda; travel restricted; exemptions on request (H; see 06-protection-humanitarian/special-measures-and-public-policies.md).

### Pass 2: PR, citizenship, PR card (secondary aggregators, about Sep-Nov 2026; M)
| Line | Reported time |
|---|---|
| Express Entry (FSW/CEC) | about 6-7 months |
| PNP enhanced (EE) / base | about 7 months / about 13-14 months |
| Citizenship grant | about 12-13 months (one outlier 25 months for certificates) |
| PR card renewal | about 38-42 days |
- Sources: https://www.y-axis.com/news/canada-updates-processing-times-express-entry-provincial-nominee-programs/ ; https://www.getnorthpath.com/tools/processing-times ; https://trenityconsultants.com/ircc-processing-times-2026/ - confirm on IRCC tool before quoting.

### Official PR and citizenship estimates for NEW applications (IRCC forward-looking data, updated 2026-11-17, read 2026-11-19, monthly) (H)
| Program | Estimated time | People waiting |
|---|---|---|
| Express Entry: Canadian Experience Class | 6 months | About 48,200 |
| Express Entry: Federal Skilled Worker | About 9 months | About 60,100 |
| Provincial nominee, through Express Entry | About 7 months | About 13,800 |
| Provincial nominee, base (paper) | About 12 months | About 90,200 |
| Atlantic Immigration Program | About 25 months | About 11,100 |
| Caregivers | About 73 months | About 35,200 |
| Start-up Visa | More than 10 years | About 47,400 |
| Self-employed | More than 10 years | About 8,000 |
| Quebec skilled worker | 11 months | About 20,100 |
| Quebec business | About 73 months | About 3,600 |
| Spouse or partner, outside Canada (outside Quebec) | About 19 months | About 65,900 |
| Spouse or partner, outside Canada (Quebec) | About 34 months | About 19,700 |
| Spouse or partner, in Canada (outside Quebec) | About 27 months | About 55,100 |
| Spouse or partner, in Canada (Quebec) | About 33 months | About 14,700 |
| Parents and grandparents (outside Quebec) | About 26 months | About 33,800 |
| Parents and grandparents (Quebec) | About 60 months | About 10,100 |
| Protected persons in Canada (outside Quebec) | About 11 months | About 71,700 |
| Protected persons in Canada (Quebec) | More than 10 years | About 42,700 |
| Dependants abroad of protected persons (outside Quebec) | About 46 months | About 60,000 |
| Dependants abroad of protected persons (Quebec) | More than 10 years | About 23,200 |
| Government-assisted refugees (outside Quebec) | About 14 months | About 18,500 |
| Government-assisted refugees (Quebec) | About 8 months | About 300 |
| Privately sponsored refugees (outside Quebec) | About 39 months | About 70,700 |
| Privately sponsored refugees (Quebec) | About 52 months | About 2,200 |
| Humanitarian and compassionate (outside Quebec) | More than 10 years | About 57,500 |
| Humanitarian and compassionate (Quebec) | More than 10 years | About 20,900 |
| Citizenship grant | About 12 months | About 322,900 |
| Proof of citizenship (certificate) | About 35 months | About 139,200 |
- These are IRCC's **forward-looking** estimates for an application submitted now (queue-based), not historical 80% times.

### Official other lines (IRCC non-country data, updated 2026-11-18, read 2026-11-19) (H)
- PR card: new PR **32 days**; renewal **50 days**. eTA 5 minutes. IEC 4 weeks. SAWP 7 days.
- In Canada: visitor visa from inside Canada 12 days / visitor extension 296 days; study extension 52 days; **work permit extension 119 days**.
- Citizenship renunciation 4 months; search 18 months; adoption part 1: 5 months; resumption: not enough data.
- Verification of status 20 weeks; replace document 11 weeks; amend IMM 16 weeks; amend TR 11 weeks.
- Not in the data: PGWP (in-Canada work permit line used), FST EE (not enough data).

## Recent changes (2025-2027)
- 2026-11-17/18: IRCC times updated: FSW about 9 months (was 7), CEC 6; spouse outside Canada (outside QC) about 19 months, in Canada about 27; PGP about 26; protected persons in Canada about 11; proof of citizenship about 35; PR card renewal 50 days; work permit extension 119 days (H)
- 2026-11-04: IRCC times updated (H)
- 2026-10-09: proof of citizenship estimate about 34 months (post Bill C-3 demand) (H)

## Consultant pitfalls
- Times are **historical** (80% of files decided in X). Never promise a date.
- Country-of-residence times vary hugely. Use the client's actual residence.

## Common refusal reasons
- n/a

## Re-verify before advising
- Processing times change daily - always re-check IRCC tool
- Capture EE, PNP, spousal, PGWP, citizenship and PR card times when the tool loads

## Sources
- IRCC processing JSON (2026-11-18): https://www.canada.ca/content/dam/ircc/documents/json/data-ptime-en.json
- IRCC tool: https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html
- Inventory/service standards: https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/corporate-initiatives/levels/inventories-backlogs.html
- Secondary aggregators (Pass 2 table): https://www.y-axis.com/news/canada-updates-processing-times-express-entry-provincial-nominee-programs/ ; https://www.getnorthpath.com/tools/processing-times ; https://trenityconsultants.com/ircc-processing-times-2026/
- IRCC forward-looking processing data (official, 2026-11-17): https://www.canada.ca/content/dam/ircc/documents/json/flpt-en.json
- IRCC non-country processing data (official, 2026-11-18): https://www.canada.ca/content/dam/ircc/documents/json/data-ptime-non-country-en.json
IRCC feeds read 2026-11-19; secondary aggregators read 2026-11-07.
