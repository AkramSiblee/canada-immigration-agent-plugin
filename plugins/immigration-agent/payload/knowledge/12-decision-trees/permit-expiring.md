---
domain: 12-decision-trees
topic: permit-expiring
status: verified
last_verified: 2026-11-17
confidence: H
review_every_days: 90
sources:
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/pr-work-permits/bridging.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/restore.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/visitors/implied-status-extending-stay.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/foreign-workers/open-work-permits-province-territory.html
  - https://www.canada.ca/en/employment-social-development/services/foreign-workers/lmia-expiry.html
  - https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/
  - knowledge/05-temporary-residence/work-permit-process-and-status.md
  - knowledge/05-temporary-residence/open-work-permits.md
  - knowledge/05-temporary-residence/trp-restoration-maintained-status.md
  - knowledge/05-temporary-residence/pgwp.md
  - knowledge/05-temporary-residence/work-permits-lmia.md
  - knowledge/01-federal-economic/express-entry.md
  - knowledge/13-case-law/work-permit-status-refusals.md
---
# Decision tree: permit expiring (worker or graduate)

## Must cover
- Months left -> PGWP / LMIA / BOWP / spouse / visitor fallback / restoration

## Tree
```
0. Get the dates first: python3 scripts/status_clock.py --expiry YYYY-MM-DD
   [--stay-end YYYY-MM-DD if a later "must leave Canada by" date] [--second-applied ...]
   [--spouse-route c41|c49|exempt] [--mb-bridge]
   [--applied ...] [--refused ...] [--completion ...] [--study-expiry ...]
   [--principal-end ...] [--spouse-applies ...] [--unauthorized-ended ...]
   Also check: passport expiry (caps any permit), biometrics validity, any work outside
   the permit's conditions (R200(3)(e) 6-month bar), any pending application.

1. Already expired?
   - Applied for an extension/new permit ON OR BEFORE expiry -> maintained status: keep
     working under the same conditions while in Canada; don't travel without advice.
     Refused while on maintained status -> status lost on the refusal date -> step 6.
   - Nothing filed before expiry -> out of status since expiry -> step 6.

2. 6+ months left: plan the next permit now (processing times; LMIA takes months)
   a. PR application already filed?
      - Express Entry / PNP-EE: e-APR has passed the R10 completeness check (GCMS "R10 OK");
        upload the AOR as evidence (the A75 PDI says the AOR alone doesn't prove
        completeness; a profile or ITA is never enough) -> BOWP (A75), 24 months.
        Not passed yet = not eligible: extend another way. No "expires within 4 months" rule
        (Help Centre Q676 is outdated; client page and PDI govern).
      - Non-EE PNP: positive eligibility assessment -> BOWP (province-restricted).
      - Quebec skilled worker (CSQ valid at filing, "E" file letter) -> BOWP (Quebec only).
      - Caregiver approval in principle -> BOWP (Agri-Food: pending files only, pilot closed). AIP, RCIP, business: no BOWP.
   b. No PR file yet -> fastest PR route? (express-entry.md: CEC after 1 yr TEER 0-3;
      MI 2026-1 job-offer points need no LMIA from 2026-11-03; PNP in-Canada streams)
   c. Employer will support -> LMIA (high-wage up to 3 yrs; low-wage up to 2 yrs for LMIAs
      submitted from 2026-11-06; LMIA must be used within its validity, usually 6 months)
      or an LMIA-exempt code (work-permits-lmia-exempt.md). The permit can't exceed the
      LMIA employment duration or the passport.
   d. Student finishing a program -> PGWP (step 4).

3. Under 6 months left
   - Same as step 2 but file BEFORE expiry so maintained status covers the gap.
   - Waiting on an LMIA for an extension: IRCC makes no decision for 90 days after receipt
     (was 60; program update 2026-08-21; not yet on the instructions page) so the LMIA can
     arrive; file the extension before expiry anyway (work-permit-process-and-status.md).
   - Two applications pending: both filed before expiry -> maintained status continues
     if the first is refused. One filed after expiry gives no maintained status.

4. Graduate (PGWP)
   - Within 180 days of completion, study permit valid at some point in that window
     (status_clock.py --completion --study-expiry). Field of study: cip_check.py.
   - Study permit expired? Restore as a STUDENT + PGWP in one application within 90 days
     (and within the 180 days). One PGWP per lifetime.

5. Spouse / partner of the person
   - Spouse OWP (C41) needs the principal in TEER 0-1 or an eligible TEER 2-3 job with
     16+ months left when the spouse's application is received (owp_rules.py +
     status_clock.py --principal-end --spouse-applies). Principal on maintained status ->
     spouse's file held. Principal moving to a PGWP -> PGWP must be issued first.
   - Spouse of a BOWP holder -> C49 (principal authorized 6+ months after the family
     application). Worker-spouse permits issued before 2025-01-21: facilitation renewal
     only if the principal kept the same permit with 6+ months left.
   - Spouse can't qualify -> own permit (LMIA, PGWP, study) or visitor status.

6. Out of status (lost status on date X)
   - Within 90 days of X -> restoration (R182) + new permit in one application
     ($246.25 + permit fee; pay the $155 separately if the portal doesn't charge it).
     NO work or study while pending. Restoration covers only restorable breaches
     (period of stay, type of work/employer/location, studies).
   - Manitoba support-letter holders (letter on or before 2025-12-31 + current MB employer):
     Manitoba Workforce Transition Bridge waives the 90 days (received before 2027-12-31).
   - Over 90 days -> TRP (usually framed as compelling reasons; case law split, see
     trp-restoration-maintained-status.md) or leave Canada. s.41 report risk.
   - Worked without authorization -> R200(3)(e): no work permit until 6 months after
     it stopped (status_clock.py --unauthorized-ended); employer exposure under IRPA
     s.124 (employer-compliance-inspections.md).

7. Visitor fallback
   - No work option now -> apply to extend as a visitor BEFORE the permit expires (stop
     working on expiry unless maintained status covers a work-permit application).
   - Visitor status keeps the person in Canada while a new LMIA or job offer is arranged;
     it does not allow work.

8. Refused or about to be? -> 13-case-law/work-permit-status-refusals.md (reapply vs
   restore vs TRP vs judicial review; JR = lawyer, 15 days in Canada).
```

## Consultant pitfalls
- Filing one day late: no maintained status; the client must stop working.
- BOWP filed before the completeness check passed: likely refused (inference, M). If the e-APR itself proves incomplete, the PDI says the BOWP is refused, holder fee refunded, processing fee kept.
- Telling a client that Help Centre Q676's 4-month rule applies.
- Working while restoration is pending.
- Letting the spouse's permit lapse when the principal changes permit type.

## Re-verify before advising
- ESDC low-wage LMIA duration pages (still say 1 year; release says 2 years from 2026-11-06)
- Concurrent-processing 90-day hold on the instructions page
- Manitoba bridge expiry and any new provincial support-letter policy

## Sources
- IRCC and ESDC pages above (BOWP 2026-10-16, restore 2026-08-28, implied status instructions 2025-05-28, PGWP eligibility 2026-06-24, Manitoba bridge 2026-08-19, LMIA expiry 2026-04-14), via the listed KB files (read 2026-11-17).
