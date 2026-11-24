---
domain: 14-policy-tracker
topic: backlogs-and-inventory
status: verified
last_verified: 2026-11-17
confidence: H
review_every_days: 30
sources:
  - https://immigrationtocanada.com/ircc-application-backlog-hits-lowest-point-since-july-2025/
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees/cimm-mar-23-2026/family-reunification.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/reports-statistics/statistics-open-data/immigration-stats/application-processing-system.html
---
# Backlogs and inventory

## Must cover
- IRCC inventory by category, service standards
- Monthly inventory snapshot with date

## Current rules

### Snapshot: data as of 2026-09-30 (page dated 2026-11-17; read 2026-11-17, H)
| Line | Not yet finalized | Finalized since 2026-01-01 | Note |
|---|---|---|---|
| TR: study permits (new) | 24,910 | 164,735 | |
| TR: work permits (new) | 24,970 | 204,250 | |
| TR: visitor visas | 298,060 | 1,923,425 | |
| **TR total (new, excl. extensions)** | **347,935** | 2,292,410 | |
| PR: Economic | 250,010 | 236,710 | 78% in processing, 22% waiting for space under targets |
| PR: Family | 168,855 | 79,705 | 58% in processing, 42% waiting for space |
| PR: Protection (PP, GAR, PSR, H&C; excl. special measures) | 288,540 | 103,075 | 56% in processing, 44% waiting for space |
| **PR total (derived)** | **707,405** | | |
| Citizenship grants | 322,650 | 245,900 | |
| Proof of citizenship | 130,685 | 44,060 | |
| **All lines (derived, not on page)** | **about 1,508,675** | | |

- Values are rounded to multiples of 5 and approximate (TR sub-lines sum to 347,940 vs page total 347,935: rounding). Page gives no system-wide total inventory or backlog %.
- FSW + CEC (Oct 2025-Sep 2026): about 74% decided within the 6-month standard; about 50% in 5 months or less.
- Spouses, partners, children (outside Quebec): about 15 months (Oct 2025-Sep 2026). The 2027 humanitarian cohort aims for about 12 months outside Quebec.
- History (not yet finalized): 2026-08-31: TR 365,425 (visitor visas 310,990 / work permits 25,995 / study permits 28,440, derived from the page's month-over-month changes); PR 715,340 (Econ 256,555 / Fam 167,170 / Prot 291,615, 43% waiting); citizenship grants 327,125; proof 135,965; FSW+CEC 76% within standard.
- PGP inventory (Jan 31, 2026, CIMM briefing): about 48,400 outside Quebec and 12,100 Quebec (H).
- **Note:** IRCC changed format. The page now shows "not yet finalized" and the share "waiting for space under yearly targets", not the old backlog-vs-service-standard split. The old 80% target is not stated on the current page.

### Secondary data (older format, M)
- 2026-04-30 (secondary, from the earlier IRCC dashboard): total inventory 2,153,900; within standards 1,231,200 (about 57%); backlog 922,700 (about 43%).

## Recent changes (2025-2027)
- 2026-11-17: page updated to data as of 2026-09-30; PR not yet finalized down to 707,405 (from 715,340); Protection waiting-for-space up to 44% (H)
- 2026-10-20: IRCC inventory page reformatted ("not yet finalized" plus "waiting for space under targets") (H)

## Consultant pitfalls
- "Waiting for space under yearly targets" means a complete file may sit idle until a Levels space opens, especially Family (42%) and Protection (44%, data 2026-09-30). Set client expectations; don't quote service standards as promises.
- Don't compare figures across the two formats. The old backlog % and the new "waiting for space" % measure different things.

## Common refusal reasons
- n/a

## Re-verify before advising
- Refresh monthly. IRCC updates this page about monthly with a lag of about 6-7 weeks. Update `templates/ircc/inventory.csv` (dashboard card) at the same time; `scripts/test_inventory.py` checks they match.
- Per-program processing times: use the IRCC tool (see 11-forms-fees-processing/processing-times.md)

## Sources
- Inside IRCC's application processing system (data 2026-09-30, page dated 2026-11-17, read 2026-11-17): https://www.canada.ca/en/immigration-refugees-citizenship/corporate/reports-statistics/statistics-open-data/immigration-stats/application-processing-system.html
- CIMM briefing, Mar 23, 2026 (PGP inventory): https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees/cimm-mar-23-2026/family-reunification.html
- Secondary (April 2026 figures): https://immigrationtocanada.com/ircc-application-backlog-hits-lowest-point-since-july-2025/
