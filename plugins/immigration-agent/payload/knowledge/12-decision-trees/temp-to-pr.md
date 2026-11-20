---
domain: 12-decision-trees
topic: temp-to-pr
status: verified
last_verified: 2026-11-20
confidence: H
review_every_days: 90
sources:
  - https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/page-25.html
  - https://laws-lois.justice.gc.ca/eng/acts/I-2.5/page-4.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/field-of-study.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/language-results.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/open-work-permit.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/special-instructions/spouses-dependent-children/eligibility.html
  - https://www.canada.ca/en/employment-social-development/services/foreign-workers/median-wage/low/requirements.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/who-can-apply/canadian-experience-class.html
  - https://www.ontario.ca/page/ontario-workforce-priority-stream
  - https://liveinnovascotia.com/resources/update-nova-scotia-nominee-program-and-atlantic-immigration-program-2026-selection
  - https://www.quebec.ca/en/immigration/permanent/skilled-workers/skilled-worker-selection-program/requirements
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/immigration-system/measures.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/immigration-system/levels/supplementary-immigration-levels-2027-2029.html
  - knowledge/05-temporary-residence/*.md
  - knowledge/12-decision-trees/study.md
  - knowledge/01-federal-economic/*.md
  - knowledge/14-policy-tracker/announced-for-2027.md
---
# Decision tree: temporary resident to PR

## Must cover
- Students, expiring permits, 2027 measure

## Current rules
```
1. Status check: valid / maintained (applied before expiry) / expired?
   - Expired under 90 days -> restoration (stop working) + new permit
   - Over 90 days -> TRP or leave; check s.41
2. Student near graduation?
   - PGWP: 180 days; CLB 7 (university or any degree) / 5 (other college); field of study
     (2026 list frozen; scripts/cip_check.py); 1 per lifetime. Full student route: study.md
   - Unauthorized work (excess hours) -> no work while the PGWP is pending; R200(3)(e)
     6-month bar. Restoration (R182) not available to a student who stopped studying
     (R182(2)); restoration needs a new PAL. Spouse C42 OWP: student not in last term
   - Passport validity limits the PGWP length -> renew first
3. Worker with expiring permit?
   - PR application filed? -> BOWP (EE/PNP-EE after the completeness check; non-EE PNP after a
     positive eligibility pass; Quebec CSQ; not AIP, RCIP or business classes) -> permit-expiring.md
   - Spouse OWP only if principal TEER 0-1 / select TEER 2-3 and 16+ months left
   - LMIA renewal (low-wage now up to 2 yrs) or IMP code
4. PR options in Canada:
   - CEC (1 yr TEER 0-3 in 3 yrs) + high-wage CWE points
   - PNP in-Canada streams (ON Workforce Priority: 6 months in offered job; BC; AB; SK work experience; NS one-time
     expanded selection for 2026-expiring permits CLOSED: EOIs had to be filed by 2026-06-30)
   - Quebec: PSTQ Stream 2 (PEQ closed)
   - Spousal in-Canada, H&C (Guide 5291; open WP after approval in principle, R207(d))
   - Caregivers (TEER 4): no EE; pilots paused -> 01-federal-economic/caregivers.md
   - Abused on an employer-specific permit -> OWP-V (fee-free, 1 yr); abused by spouse -> family violence TRP
5. 2027 time-limited measure (no application):
   - Workers cohort (up to 100,000 workers and families): people already waiting under AIP or closed programs
     (SUV, Self-Employed, Agri-Food, home care) or PNP-eligible, in Canada, outside Quebec, via optional extra
     PNP allocations used by 2027-03-31; no client application
   - Humanitarian ("up to"): Hong Kong 32,000; Ukraine Family Reunification 18,800; H&C already found eligible
     12,600; spouses, partners and children of citizens/PRs living in Canada 45,000 (sum 108,400 vs the
     stated 100,000: IRCC doesn't explain) -> see 14-policy-tracker/announced-for-2027.md (IRCC releases 2026-11-10/12)
```

## Recent changes (2025-2027)
- 2026-11-05: 2027 measure announced; 2026-11-06 TFWP 2-yr LMIA (H)

## Consultant pitfalls
- Never let a client leave Canada during maintained status without advice.

## Common refusal reasons
- See 05 files

## Re-verify before advising
- 2027 measure implementation; provincial allocations

## Sources
Official pages for each time-sensitive rule (read when the linked knowledge files were last verified):
- Restoration within 90 days (IRPR s.182) and maintained status: https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/page-25.html
- TRP (IRPA s.24): https://laws-lois.justice.gc.ca/eng/acts/I-2.5/page-4.html
- PGWP eligibility (180 days, language, field of study): https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html
- PGWP field of study list: https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/field-of-study.html
- PGWP language results: https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/language-results.html
- BOWP and other open work permits: https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/open-work-permit.html
- Spouse OWP: TEER 0-1 or listed TEER 2-3, 16+ months: https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/special-instructions/spouses-dependent-children/eligibility.html
- LMIA (low-wage up to 2 years for LMIAs submitted from 2026-11-06; ESDC's low-wage page still says 1 year): https://www.canada.ca/en/employment-social-development/news/2026/11/government-of-canada-announces-targeted-reforms-to-the-temporary-foreign-worker-program-to-respond-to-labour-market-needs.html
- CEC and high-wage Canadian experience points: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/who-can-apply/canadian-experience-class.html
- Ontario Workforce Priority stream (6 months in the offered job): https://www.ontario.ca/page/ontario-workforce-priority-stream
- Nova Scotia one-time expanded selection (2026): https://liveinnovascotia.com/resources/update-nova-scotia-nominee-program-and-atlantic-immigration-program-2026-selection
- PSTQ Stream 2 (Quebec): https://www.quebec.ca/en/immigration/permanent/skilled-workers/skilled-worker-selection-program/requirements
- 2027 time-limited measures: https://www.canada.ca/en/immigration-refugees-citizenship/corporate/immigration-system/measures.html
- 2027-2029 levels plan: https://www.canada.ca/en/immigration-refugees-citizenship/corporate/immigration-system/levels/supplementary-immigration-levels-2027-2029.html
- Derived from knowledge/05-temporary-residence, 01-federal-economic, 14-policy-tracker (verified 2026-11-07 to 2026-11-17)
