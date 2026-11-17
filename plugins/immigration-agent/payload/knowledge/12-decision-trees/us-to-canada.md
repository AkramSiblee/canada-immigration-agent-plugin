---
domain: 12-decision-trees
topic: us-to-canada
status: verified
last_verified: 2026-11-17
confidence: M
review_every_days: 60
sources:
  - knowledge/05-temporary-residence/work-permits-lmia-exempt.md
  - knowledge/05-temporary-residence/trade-agreement-work-permits.md
  - knowledge/05-temporary-residence/work-permit-process-and-status.md
  - knowledge/05-temporary-residence/visa-requirements-by-nationality.md
  - knowledge/05-temporary-residence/flagpoling-biometrics-medicals.md
  - knowledge/05-temporary-residence/transit-and-visit-purposes.md
  - knowledge/05-temporary-residence/study-permits.md
  - knowledge/05-temporary-residence/iec.md
  - knowledge/01-federal-economic/express-entry.md
  - knowledge/01-federal-economic/business-and-self-employed.md
  - knowledge/04-family/spousal-common-law-conjugal.md
  - knowledge/06-protection-humanitarian/stca-prra.md
  - knowledge/07-citizenship-pr-status/citizenship-proof-bill-c3.md
  - knowledge/07-citizenship-pr-status/pr-card-prtd-residency.md
  - knowledge/08-inadmissibility/criminality-rehabilitation-arc.md
  - knowledge/08-inadmissibility/misrepresentation-s40.md
  - https://budget.canada.ca/2025/report-rapport/chap1-en.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations/category-based-selection.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/news/notices.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/campaigns/tech-talent.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/foreign-workers/international-free-trade-agreements/cusma.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/foreign-workers/international-free-trade-agreements/cusma/traders.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/foreign-workers/international-free-trade-agreements/cusma/investors.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/foreign-workers/international-free-trade-agreements/cusma/business-visitors.html
  - https://www.canada.ca/en/border-services-agency/news/2024/12/ending-flagpoling-for-work-and-study-permits-at-the-border.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/study-permits/making-application.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship/spouse-partner-children/eligibility.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/admissibility-enforcement/overcome-criminal-convictions.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/biometrics/how-to-give.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/recognized-organizations.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/application/medical-police/police-certificates/how/united-states.html
---
# Decision tree: US-based applicant to Canada (US citizens, green-card holders, H-1B, TN, L-1, F-1, Canadians living in the US)

Confidence M overall: built from the linked knowledge files (each verified on its own date) plus official pages read 2026-11-13 and 2026-11-17.
Individual facts marked (H) were read on an official page. Re-check each branch's source file before advising; the H-1B branch changes fast.

## Must cover
- Citizenship decides the work permit route (CUSMA is for **US citizens**, not US visa status).
- US status decides entry documents and where an application can be made (port of entry, flagpoling exceptions).
- US time counts as foreign experience for CRS/FSW; US degrees need an ECA.
- Family, Canadians living in the US, US-specific inadmissibility, logistics, asylum.

## Current rules
```
0. Who is the client?
   - Foreign national in the US -> 1.
   - Canadian citizen in the US (sponsoring, returning, children born in the US) -> 8.
   - Canadian PR living in the US -> 9.
   - Wants to claim asylum after the US -> 10.
1. Citizenship and entry document
   - US citizen -> visa-exempt and eTA-exempt (passport).
   - US green card (LPR), other citizenship -> eTA-exempt; carry passport + green card (visa-requirements-by-nationality.md).
   - Other citizenship on H-1B / L-1 / F-1 / O-1 / TN-Mexican -> entry document follows the PASSPORT:
     visa-required national -> visitor visa (TRV) with any permit; visa-exempt -> eTA by air.
2. Goal: visit or work remotely, work, study, start a business, or straight to PR?
   - Visit or business visit -> 3. Work -> 4. Study -> 5. Business -> 6. PR -> 7.
3. Visiting
   a. Business visitor (R186(a)): no permit; meetings, buying, after-sales service, training (transit-and-visit-purposes.md).
   b. CUSMA business visitor (US or Mexican citizens): Appendix 1 activities (research and design, manufacture,
      marketing, sales, distribution, after-sales service, etc.). Request entry at the port of entry; "an application
      cannot be made prior to arriving in Canada"; usually 6 months or less. After-sales service: original sales
      contract + warranty/service agreement, commercial or industrial equipment bought outside Canada, specialized
      knowledge, no hands-on construction; referred to Immigration Secondary (CUSMA business visitors page 2025-12-22) (H).
   c. Remote work for a US employer: visitor status only, up to 6 months at a time, no work permit
      (IRCC Tech Talent page 2024-04-24; no newer wording found 2026-11-17) (M). Work for a Canadian client or employer
      needs a permit. Ask what the client actually does in Canada.
4. Work permit routes
   a. US citizen with a job offer in one of the 63 CUSMA professions, qualified, pre-arranged, not self-employed
      -> CUSMA professional T36 (formerly T23), LMIA-exempt, up to 3 yrs, unlimited 3-yr extensions (work-permits-lmia-exempt.md).
   b. US (or Mexican) citizen moving within the same company, 1 yr continuous full-time in last 3 yrs
      -> CUSMA ICT T37 executive/manager (7 yrs total), T38 specialized knowledge (5 yrs total).
   c. US citizen trader or investor (enterprise of US nationality, supervisory/executive or essential skills, IMM 5321)
      -> CUSMA trader T34 (formerly T21): over 50% of the enterprise's international trade is Canada-US/Mexico, trade
         already exists. CUSMA investor T35 (formerly T22): substantial investment, controlling interest (50% or less
         usually fails), no fixed minimum, proportionality test, secured loans don't count.
         Initial permit max 1 yr, extensions 2 yrs. Initial application "should be submitted outside of Canada"
         (CUSMA traders and investors pages 2024-10-03) (H). Not a POE-same-day route.
   d. Any citizenship, same multinational, 1 yr continuous full-time in last 3 yrs (e.g. L-1 / H-1B with a global employer)
      -> Intra-company transferee C12 (C62 exec/manager max 7 yrs; C63 specialized knowledge max 5 yrs).
   e. Citizen of another FTA country living in the US (EU, UK, CPTPP, Korea, Chile...) -> that FTA's codes
      (trade-agreement-work-permits.md).
   f. Otherwise -> LMIA-based permit (work-permits-lmia.md) or another IMP code (Global Talent Stream: global-skills-strategy.md).
   - Spouses: CUSMA "does not extend special privileges to spouses" (CUSMA index 2024-10-03) (H). Spouse OWP only under
     the domestic rules: principal's NOC TEER 0-1 or on IRCC's TEER 2-3 list, 16+ months left (open-work-permits.md;
     scripts/owp_rules.py).
   - Under 36, US citizen: not an IEC country. Only the Recognized Organization SWAP Working Holidays accepts US
     citizens (IEC RO page) (H); check the IEC season status first (iec.md).
   - Where to apply: port of entry if visa-exempt (US citizen, LPR, eTA national) with the offer number / LMIA ready
     (work-permit-process-and-status.md). Visa-required nationals apply online before travel.
   - Flagpoling ended 2024-12-23 for work and study permits, BUT "citizens and lawful Permanent Residents of the United
     States" are an exception (CBSA notice 2024-12-23) (H). A US citizen or green-card holder already in Canada can still
     apply at the border. H-1B / L-1 / F-1 holders without a green card cannot, unless another exception applies
     (FTA professionals/technicians, truck drivers, pre-booked CBSA appointment).
5. Study
   - US citizens, US nationals, US LPRs (and residents of Greenland / Saint-Pierre and Miquelon) may apply for a study
     permit at the port of entry (R214; IRCC study permit instructions) (H). They still need a PAL/TAL unless exempt
     (study-permits.md). Canada.ca's public page is confusingly worded; confirm on the day.
   - F-1 students moving to Canada: PGWP rules apply to the Canadian program only; US study doesn't count (pgwp.md).
6. Business / self-employed
   - CUSMA trader/investor (4c), C11 entrepreneur, Start-up Visa, PNP entrepreneur streams, Quebec business programs
     (business-and-self-employed.md; 03-quebec/business-immigration.md). Check 14-policy-tracker for pauses first.
7. PR routes (run /crs, /fsw, /clb, /pnp)
   - Express Entry FSW: US experience counts as foreign skilled experience; needs 67/100 grid + CLB 7 + ECA for US degree.
     Proof of funds unless authorized to work in Canada with a valid job offer.
   - CEC only after 1 yr skilled work IN Canada (so: work permit first, then CEC).
   - Job offer: no LMIA needed for ITAs from 2026-11-03.
   - Categories (category-based-selection page 2026-10-16, rechecked 2026-11-17): French, healthcare/social services,
     STEM, trades, education, transport, physicians / senior managers / researchers with Canadian experience, skilled
     military recruits. **No H-1B category exists.** STEM is the usual fit for tech H-1B profiles.
   - PNP: tech / employer / entrepreneur streams (/pnp). Quebec: PSTQ (03-quebec/).
   - H-1B pathway (perishable): Budget 2025 promised "an accelerated pathway for H1-B visa holders".
     Status 2026-11-17: ANNOUNCED, NOT OPEN. No IRCC notice (notices page read 2026-11-17), no category.
     The 2023 H-1B open work permit (10,000 cap) is closed (Tech Talent page: "Status: Closed"). Check 14-policy-tracker.
   - Landing: a US-based COPR holder lands at a Canadian port of entry or online confirmation of PR (portal) if already
     in Canada. The 2024 flagpoling change covers work and study permits only, not PR landing (CBSA notice) (H).
     Medical results (12 months) and passport validity set the latest landing date (flagpoling-biometrics-medicals.md).
8. Canadian citizen living in the US
   - Sponsoring a spouse/partner from the US: a citizen abroad "must show that you plan to live in Canada when the people
     you're sponsoring become permanent residents" (IRCC eligibility page 2026-06-23) (H). Evidence: job offer or job
     search, lease or home, school enrolment, move plans. Outside-Canada class if the couple lives in the US; in-Canada
     class only if they live together in Canada and the spouse has TR status (spousal-common-law-conjugal.md).
     /family-sponsorship-assessor.
   - Children born in the US: born before 2025-12-15 -> likely a citizen at any generation (Bill C-3 removed the
     first-generation limit). Born on or after 2025-12-15 -> citizen only if the Canadian parent had 1,095 days in Canada
     before the birth (citizenship-proof-bill-c3.md). Apply for proof (CIT 0001). Multigenerational cases: lawyer.
   - Returning to Canada: a citizen needs no immigration process; a US spouse/children need PR (sponsorship) or a permit.
9. Canadian PR living in the US
   - Residency obligation: 730 days in 5 years. Days abroad count only if accompanying a Canadian-citizen spouse/partner
     or parent, or employed full-time by a Canadian business (genuine assignment) (pr-card-prtd-residency.md). /presence.
   - A PR living in the US cannot sponsor a spouse until they live in Canada (IRCC eligibility page 2026-06-23) (H).
   - Short of 730 days: PRTD with H&C reasons, or return and rebuild the days. Airlines need a valid PR card or PRTD;
     run /pr-status-advisor before the client travels.
10. Asylum after the US
   - STCA applies at land ports of entry and between ports if the claim is made under 14 days after entry
     (Additional Protocol, SOR/2023-58); exceptions (family in Canada, unaccompanied minors, etc.) apply
     (stca-prra.md). Run /protection-claim-triage. Bill C-12 bars and eligibility: same file.
11. Admissibility checks for US applicants (inadmissibility-assessor)
   - Impaired driving (DUI/DWI/OWI, including cannabis) is serious criminality since 2018-12-18: deemed rehabilitation
     unavailable; individual rehabilitation (5 yrs after sentence incl. probation) or TRP (criminality-rehabilitation-arc.md).
   - Ask about every arrest, charge, diversion, deferred adjudication and juvenile matter, in every state.
   - US expungement, sealing, set-aside or governor's pardon: NOT automatically recognized. IRCC: "check with the visa
     office that serves the country or region where you live"; it "will tell you if the pardon is valid in Canada"
     (overcome-criminal-convictions page 2026-07-23) (H). Officers ask whether the foreign law erases the conviction
     or only recognizes rehabilitation (ENF 3) (M). Get certified court records for every disposition anyway.
   - Cannabis: conduct that is no longer an offence in Canada (simple possession within Canadian limits) is generally not
     a ground (ENF 3 policy on offences no longer in the Criminal Code) (M). Possession for distribution, cultivation
     over limits, trafficking, and cannabis-impaired driving still count; equivalency is offence-by-offence -> lawyer if unclear.
   - Rehabilitation for eTA/visa-exempt travellers: apply by mail/courier to the visa office for the region before
     travel; IRCC's page names no port-of-entry route (page 2026-07-23) (H). Don't promise a border decision.
   - Prior US removal, deportation, voluntary departure, US visa refusal or overstay: every IRCC form asks about refusals
     and removals from ANY country. Non-disclosure is misrepresentation (s.40, 5-yr bar). A US removal order doesn't
     itself need an ARC for Canada.
   - Police certificate: FBI Identity History Summary (IRCC US page 2025-06-17), not a state check; for PR, each country
     with 6+ months in a row in the last 10 years since 18. Order at intake (slow).
12. Logistics in the US
   - Biometrics: at a USCIS Application Support Center, only with IRCC's biometric instruction letter, by appointment,
     only if already legally in the US; don't travel to the US just for biometrics (IRCC how-to-give page) (H).
     US citizens are exempt from TR biometrics (flagpoling-biometrics-medicals.md). Fee $85 / $170 family.
   - Medicals: IRCC panel physician in the US (panel physician finder); results valid 12 months.
   - IRCC VACs in the US: Los Angeles and New York (visitor-country-reference.md).
```

## Watch
- Clients often think H-1B or green-card status gives a Canadian advantage: it doesn't, except entry documents and the
  US-LPR flagpoling / study-permit-at-POE exceptions.
- TN status is a US status; a Mexican or Canadian citizen's CUSMA eligibility comes from citizenship, not TN.
- Undisclosed US arrests (even dismissed or expunged) are a misrepresentation risk (s.40).
- "Remote work as a visitor" fails when the work is really for Canadian clients, or the stay becomes residence.
- A Canadian citizen sponsor in the US with no concrete plan to move is a common refusal point.

## Sources (read dates)
- CUSMA index, traders, investors (2024-10-03), business visitors (2025-12-22), exemption codes (2026-09-23): read 2026-11-17 (H)
- CBSA flagpoling notice (2024-12-23): read 2026-11-17 (H)
- Spousal sponsor eligibility (2026-06-23): read 2026-11-17 (H)
- Overcome criminal convictions (2026-07-23): read 2026-11-17 (H)
- Study permits: making an application (R214 list): search result 2026-11-17 (M; page not read in full)
- IEC Recognized Organizations (SWAP for US citizens): search result 2026-11-17 (M)
- Biometrics how-to-give (ASC by appointment): search result 2026-11-17 (M)
- Tech Talent campaign (digital nomads; H-1B OWP closed) (2024-04-24): read 2026-11-17 (M, old page)
- IRCC notices (2026-11-05) and category-based selection (2026-10-16): read 2026-11-17, no H-1B pathway (H)
- ENF 3 (2022-03-03) on foreign pardons and offences no longer in Canadian law: search result 2026-11-17 (M)
