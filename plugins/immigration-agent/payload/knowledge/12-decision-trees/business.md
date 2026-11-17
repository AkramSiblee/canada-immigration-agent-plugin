---
domain: 12-decision-trees
topic: business
status: verified
last_verified: 2026-11-17
confidence: H
review_every_days: 90
sources:
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/start-visa.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/self-employed.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/news/notices/immigration-measures-entrepreneurs.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/immigration-system/levels/supplementary-immigration-levels-2027-2029.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/foreign-workers/exemption-codes/entrepreneurs-self-employed-seeking-only-temp-residence-r205-c11.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/foreign-workers/exemption-codes/canadian-interests-significant-benefit-entrepreneurs-self-employed-candidates-seeking-operate-business-r205-c11.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/foreign-workers/exemption-codes/intra-company-transferees.html
  - https://www.quebec.ca/en/immigration/permanent/immigrate-business
  - https://budget.canada.ca/2026/report-rapport/chap3-en.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/news/2026/11/minister-metlege-diab-highlights-how-canada-is-working-with-provinces-and-territories-to-support-worker-retention.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/updates/2026-startup-selfemployed-pause.html
  - knowledge/01-federal-economic/business-and-self-employed.md
  - knowledge/02-pnp/comparison-table.md
  - knowledge/03-quebec/business-immigration.md
  - knowledge/05-temporary-residence/work-permits-lmia-exempt.md
  - knowledge/05-temporary-residence/work-permits-lmia.md
  - knowledge/05-temporary-residence/trade-agreement-work-permits.md
  - knowledge/14-policy-tracker/announced-for-2027.md
---
# Decision tree: business clients

## Must cover
- Routes a business owner, investor or self-employed client to: provincial entrepreneur (C60 -> nomination -> PR), Quebec business programs, temporary only (C11, C12/C61 ICT start-up, CUSMA T34/T35), owner-operator LMIA, legacy SUV/Self-Employed file (2027 workers cohort)
- Closed/paused/announced federal programs

## Federal status (re-check the policy tracker on the day)
| Program | Status | Source |
|---|---|---|
| Start-Up Visa (PR) | **CLOSED.** Final deadline 2026-06-30 for holders of a 2025 commitment certificate; closed to everyone else | business-and-self-employed.md; IRCC SUV page |
| SUV work permit | Closed to new applicants since 2025-12-19 (extensions only) | IRCC notice 2025-12-19 |
| Self-Employed Persons | **PAUSED** | IRCC self-employed page |
| Federal entrepreneur pilot ("high-impact start-up pilot", to replace SUV) | **ANNOUNCED, not launched**: no ministerial instruction, criteria or date (Budget 2026 ch. 3, 2026-11-05; notice 2025-12-19) | announced-for-2027.md |
| Quebec Investor / Entrepreneur / Self-Employed | Open, no cap (quebec.ca 2026-11-09/10) | 03-quebec/business-immigration.md |
| Quebec: political risk | New PQ minority government (sworn in 2026-10-21) proposes a moratorium on permanent economic immigration from abroad; **not adopted**; 2027 Quebec plan not tabled (M) | announced-for-2027.md |

## Tree
```
0. Screen first (every branch)
   - Source of funds: can every dollar of net worth be traced and shown legally earned?
     -> 11-forms-fees-processing/source-of-funds-net-worth.md. Gaps = s.40 risk.
   - Undeclared family (IRPR 117(9)(d)), past refusals, criminality, ghost consultant or
     "buy a business + guaranteed nomination" schemes -> flag.

1. Does the client already have a SUV or Self-Employed PR application in process?
   YES -> Legacy file.
     - Keep the file; keep any work permit valid (SUV WP: extensions only).
     - 2027 workers cohort: provinces "will also be able to identify" SUV / Self-Employed
       applicants already in process (backgrounder 2026-11-05). Optional extra PNP space,
       each province decides its use, intended to be used by 2027-03-31; aimed at workers
       already in Canada (applicants abroad likely not covered: inference). Applicants "do
       not need to do anything or contact IRCC" (IRCC release 2026-11-12). No province has
       announced outreach yet. -> 14-policy-tracker/announced-for-2027.md
     - Do NOT tell new clients SUV or Self-Employed is open.
   NO -> 2

2. Does the client want PR, or only to run a business in Canada for a while?
   TEMPORARY ONLY -> 3
   PR -> 4

3. Temporary business routes (no PR intent)
   a. US or Mexican citizen trading substantially with / investing in the home country's
      trade? -> CUSMA trader T34 / investor T35 (apply outside Canada; 1 yr initial).
      Other treaty investors (CETA T46, CUKTCA F65 ...) -> trade-agreement-work-permits.md
   b. Existing foreign company opening a Canadian branch/subsidiary and sending an
      executive or manager? -> ICT start-up C12 / C61 (new office: 1 yr permit; 1 yr
      continuous employment abroad in the last 3; physical premises; realistic staffing plan).
      CUSMA citizens: T37/T38 (new office 1 yr).
   c. Owner of 51%+ of a Canadian business, temporary or seasonal, with a plan to leave?
      -> C11 (R205(a)): significant benefit; Employer Portal offer + $230 fee (NOC 88888
      for entrepreneurs); max 18 months; support funds = LICO for 18 months, separate
      from business funds. Under 51% -> apply as an employee (LMIA or other IMP code). C11 is TEMPORARY INTENT ONLY: a client who wants PR under
      C11 = refusal risk. -> work-permits-lmia-exempt.md
   d. Business visitor only (meetings, buying, after-sales service)? -> visitor status,
      no work permit -> transit-and-visit-purposes.md
   e. Owner wants to work in their own Canadian company long-term and the company can
      meet ESDC tests? -> LMIA for the owner's position (step 6).

4. PR intent: will the client live in Quebec?
   YES -> Quebec business programs (03-quebec/business-immigration.md):
     - Investor (net worth + investment with a financial intermediary)
     - Entrepreneur (3 streams: innovative business; start/acquire; takeover)
     - Self-Employed
     - French oral NCLC 7 (check the program page); Quebec selection (CSQ), then federal PR.
     - Quebec self-employed / entrepreneurs who need to come before PR: C60 support
       (work-permits-lmia-exempt.md).
   NO -> 5

5. Provincial entrepreneur streams (outside Quebec)  -> /entrepreneur
   - Status first: 02-pnp/comparison-table.md "Entrepreneur streams". Saskatchewan
     entrepreneur/farm permanently closed (2025-03-27); Ontario has none; Yukon: see yukon.md.
   - Typical path: EOI -> ITA -> application + business plan + net worth verification
     -> interview -> performance agreement (investment counts only after it)
     -> work permit support letter -> C60 work permit -> arrive, arrival meeting
     -> establish and operate (minimum period per province) -> nomination request
     (accountant's report) -> nomination -> PR (paper/portal PNP base) -> T13 (R204(c))
     work permit extension if needed while PR is processed.
   - Graduate entrepreneur streams (AB, NL, and others per comparison table): Canadian
     graduates on a PGWP who already run a business in the province.
   - Farm streams (AB, MB): farm experience, net worth, investment in a primary farm.
     Neither is confirmed open (AB status not stated; MB: no BIS draws): confirm first.
   - Family must live in the province; active day-to-day management; jobs for
     Canadians/PRs who are not related.
   - At IRCC: since SOR/2026-63 (2026-03-30) the province alone decides economic
     establishment and intent to reside (R87(3)); IRCC checks the nomination, the
     passive-investment exclusion (R87(5)/(6)) and admissibility incl. s.40.
     -> pnp-federal-mechanics.md
   - Challenges: provincial refusal -> the province's internal review if any (e.g. BC:
     $500, 30/60 days, no new evidence) then provincial superior court judicial review
     (lawyer referral). IRCC refusal after nomination -> Federal Court (lawyer referral).
     -> 13-case-law/business-immigration-refusals.md

6. Owner-operator LMIA (any province)
   - No dedicated owner-operator stream on current ESDC pages; the recruitment-exempt
     owner/operator LMIA reportedly ended in 2021 (secondary only, M). What's left is a
     standard high/low-wage LMIA with full recruitment, wage rules, caps, $1,000 fee,
     and R200(5) genuineness. -> work-permits-lmia.md "Owner-operator LMIA".
   - PR: work by someone with substantial ownership or management control is generally
     treated as self-employment -> unlikely to count for CEC (IRCC instructions 2023-05-25).
     Express Entry job-offer points are back from 2026-11-03 (MI 2026-1, no LMIA needed);
     MI 2026-1 has no owner exclusion, but an offer from the client's own company is a
     high genuineness risk.

7. Nothing fits now?
   - Federal entrepreneur pilot: announced, not launched -> watch the tracker.
   - Skilled routes for the owner as an employee (Express Entry, employer-driven PNP).
   - Build eligibility: language retest, exploratory visit, more net worth or a
     different region (regional streams usually ask less).
```

## Consultant pitfalls
- C11 for a PR-intent client: wrong code (no dual intent). Pre-nomination provincial entrepreneurs use C60 with the province's support letter: max 2 years outside Quebec (3 in Quebec), extension only with a PR application in process or exceptional circumstances plus a letter of continued support; after nomination T13 (R204(c)). C60 still needs an Employer Portal offer, $230 compliance fee, NOC 88888 "Entrepreneur".
- Spouse open work permit: IRCC treats NOC 88888 as TEER 0/1 (C41-C46 instructions 2026-08-11), so the spouse of a C60/C11 entrepreneur can qualify with 16+ months left on the permit; the public family OWP page lists provincial business candidates under a different stream: check per file.
- Spending before the performance agreement: provinces usually don't count it.
- Hiring relatives or the investor's own staff from abroad as the "new jobs".
- Family settling in another province than the nominating one.
- Net worth with untraceable gifts or loans: counts against the client and can become misrepresentation.
- Offering SUV, Self-Employed or the federal pilot as open.

## Re-verify before advising
- Federal entrepreneur pilot launch; provincial outreach to SUV/SE waiting applicants (2027 cohort)
- Each province's entrepreneur intake status (comparison-table.md)

## Sources
- Federal: IRCC SUV page, self-employed page, entrepreneurs notice (2025-12-19), supplementary levels 2027-2029, C11 / C60 / ICT instruction pages (URLs above), via business-and-self-employed.md and work-permits-lmia-exempt.md (read 2026-11-07 to 2026-11-17).
- Quebec: quebec.ca business immigration pages (2026-11-09/10) via 03-quebec/business-immigration.md.
- Provincial figures: each 02-pnp file (read 2026-11-17).
