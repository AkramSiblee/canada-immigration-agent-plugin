---
domain: 12-decision-trees
topic: study
status: verified
last_verified: 2026-11-17
confidence: H
review_every_days: 90
sources:
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/get-documents/provincial-attestation-letter.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/get-documents/financial-support.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/field-of-study.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/help-your-spouse-common-law-partner-work-canada.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/immigration-system/levels/supplementary-immigration-levels-2027-2029.html
  - https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/
  - knowledge/05-temporary-residence/study-permits.md
  - knowledge/05-temporary-residence/study-permit-status-and-compliance.md
  - knowledge/05-temporary-residence/pgwp.md
  - knowledge/03-quebec/caq-csq-and-students.md
  - knowledge/13-case-law/study-permit-pgwp-refusals.md
  - knowledge/14-policy-tracker/announced-for-2027.md
---
# Decision tree: students (school choice to PR)

## Must cover
- School/program choice -> PAL/cap -> funds -> compliance -> PGWP -> PR

## Tree
```
0. Screen (every branch)
   - Past refusals (any country), overstays, criminality, undeclared family (IRPR 117(9)(d)),
     ghost agents or fake LOAs/PALs (LOAs are verified with the school) -> flag; s.40 risk.
   - Medical exam if 6+ months in Canada and lived 6+ months in the last year in a designated
     country, or working/studying in health, childcare, primary/secondary education.

1. Choose the school and program FIRST (it decides PAL, PGWP and PR)
   - DLI on IRCC's list? PGWP-eligible (DLI list "PGWP: Yes / Details / No")?
     Curriculum-licensing (P3) college = no PGWP (narrow grandfathering).
   - Level: bachelor's/master's/PhD = no field-of-study test for PGWP.
     College/other: CIP must be on the PGWP list -> python3 scripts/cip_check.py CIP
     --applied YYYY-MM-DD (lock-in = study permit application date).
   - Length: under 8 months = no PGWP; 8 months-<2 yrs = PGWP up to program length;
     2+ yrs or a master's of 8+ months = up to 3 yrs. How IRCC measures length: pgwp.md.
   - Mostly online (>50% distance) = no PGWP; online time from abroad doesn't count.
   - Spouse OWP needed? Only for master's 16+ months, PhD, listed professional degrees or
     listed programs (since 2025-01-21). College diplomas: no spouse OWP.
   - Study plan must make sense: progression from past studies/work, cost vs home-country
     options, career outcome (s.216 refusals turn on this -> case law file).

2. PAL/TAL / cap
   - Needed? Exempt: public-DLI master's/PhD (from 2026-01-01), K-12, some exchange,
     GAC scholars, FMCSP schools, others (study-permits.md).
   - Quebec: CAQ (acts as the attestation) -> 03-quebec/caq-csq-and-students.md;
     Quebec CAQ caps per institution: 2025-12-17 to 2026-12-16, then to 2027-12-16.
   - Other provinces: how each issues the PAL -> study-permits.md (PAL by province).
   - 2026 PAL valid to 2026-12-31. 2027 cap and allocations NOT yet published
     (2027-2029 levels: 150,000 student arrivals/yr; that's not the cap) -> tracker.
   - Changing school later = new permit + new PAL; same school, different level group = PAL
     when the extension is filed; same level group (college -> bachelor's, master's -> PhD) = none.

3. Funds
   - First-year tuition + living costs table (outside Quebec: $23,448 single from
     2026-09-01, adjusted each Sept 1) + travel. Quebec uses its own amounts.
   - Source matters: 4-6 months of history, explain large deposits, sponsor's capacity
     and relationship; GIC optional evidence. Country instructions (PH, IN, VN, IR, GH,
     KE) -> study-permits.md.
   - Doubtful funds = s.216 / R220 refusal; false documents = s.40 (5-yr bar).

4. Apply
   - Outside Canada (SDS ended 2024-11-08; regular stream). US citizens/LPRs can apply
     at the port of entry (still need a PAL). In Canada: only if eligible (R215).
   - Refused? -> reapply with a fixed file (address each ground) vs judicial review
     (lawyer; 15/60 days) -> 13-case-law/study-permit-pgwp-refusals.md, /refusal.

5. While studying (compliance) -> study-permit-status-and-compliance.md
   - Enrolled and actively pursuing studies; authorized leave max 150 days.
   - Work: 24 h/week off campus in term, unlimited in scheduled breaks (max 180 days/yr),
     on campus unlimited; co-op permit no longer needed for post-secondary (2026-04-01).
     Unauthorized work/study -> R200(3)(e) / R221 bars.
   - Program or school change: update IRCC; new PAL/extension rules; the program you
     complete is what the PGWP is assessed on.
   - Permit expiring -> extend before expiry (maintained status). Expired -> restoration
     within 90 days (R182), no study/work meanwhile.
   - Spouse OWP (C42) is issued no later than the student's permit; R222 invalidates only
     the student's permit (no regulation invalidates the spouse's, but no IRCC guidance
     on working to expiry; extensions/new C42 fail): plan extensions together.
   - Student permit names the DLI (since 2024-11-08): leaving that DLI without completing
     ends the permit (R222(1)(a.1)); new DLI = new permit + new PAL (R217.1).

6. Graduation -> PGWP (pgwp.md)
   - Apply within 180 days of completion, study permit valid at some point in that time.
   - Language test valid at application: CLB 7 for university programs and any degree
     (non-university degrees from 2025-03-11) / CLB 5 other college programs (IELTS General,
     not Academic). Field of study (step 1). One PGWP per lifetime; passport caps length.

7. PGWP -> PR
   - 1 yr TEER 0-3 Canadian work -> CEC (Express Entry; categories; high-wage points from
     2026-11-03). PNP graduate streams (province files). Quebec: PSTQ (PEQ closed).
   - 2027 workers cohort: PNP extra allocations for in-Canada workers (no application).
   -> 12-decision-trees/temp-to-pr.md, skilled-worker.md
```

## Consultant pitfalls
- Choosing a program before checking the CIP and the PGWP flag on the DLI list.
- College diploma student expecting a spouse OWP.
- IELTS Academic used for the PGWP (not accepted).
- Taking the language test too late (must be valid at PGWP application).
- Switching school without a new PAL; working during an unauthorized leave.

## Re-verify before advising
- 2027 study cap and PAL allocations; 2027 PGWP field-of-study list (tracker)
- Proof-of-funds table each September 1

## Sources
- IRCC pages above (PAL, financial support 2026-08-28, PGWP eligibility 2026-06-24, field of study 2026-03-09, spouse of student 2026-02-03, levels 2026-11-05), read via the listed KB files (2026-11-09 to 2026-11-17).
