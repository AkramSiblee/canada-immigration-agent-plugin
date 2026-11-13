---
domain: 12-decision-trees
topic: us-to-canada
status: verified
last_verified: 2026-11-13
confidence: M
review_every_days: 60
sources:
  - knowledge/05-temporary-residence/work-permits-lmia-exempt.md
  - knowledge/05-temporary-residence/work-permit-process-and-status.md
  - knowledge/05-temporary-residence/visa-requirements-by-nationality.md
  - knowledge/01-federal-economic/express-entry.md
  - knowledge/08-inadmissibility/criminality-rehabilitation-arc.md
  - https://budget.canada.ca/2025/report-rapport/chap1-en.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations/category-based-selection.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/application/medical-police/police-certificates/how/united-states.html
---
# Decision tree: US-based applicant to Canada (US citizens, green-card holders, H-1B, TN, L-1, F-1)

Confidence M: built from the linked knowledge files (each verified on its own date) plus official pages read 2026-11-13.
Re-check each branch's source file before advising; the H-1B branch changes fast.

## Must cover
- Citizenship decides the work permit route (CUSMA is for **US citizens**, not US visa status).
- Status in the US decides entry documents only.
- US time counts as foreign experience for CRS/FSW; US degrees need an ECA.

## Current rules
```
1. Citizenship?
   - US citizen -> visa-exempt and eTA-exempt (passport). Go to 2.
   - Other citizenship, US green card (LPR) -> eTA-exempt; carry passport + green card (visa-requirements-by-nationality.md). Go to 2.
   - Other citizenship on H-1B / L-1 / F-1 / O-1 / TN-Mexican -> entry document follows the PASSPORT:
     visa-required national -> visitor visa (TRV) with any permit; visa-exempt -> eTA by air. Go to 2.
2. Goal: work in Canada first, or straight to PR?
   - Straight to PR -> 4.
   - Work first -> 3.
3. Work permit routes
   a. US citizen with a job offer in one of the 63 CUSMA professions, qualified, pre-arranged, not self-employed
      -> CUSMA professional (T36/T23), LMIA-exempt, up to 3 yrs, unlimited extensions (work-permits-lmia-exempt.md).
   b. US (or Mexican) citizen moving within the same company, 1 yr continuous full-time in last 3 yrs
      -> CUSMA ICT (T37 executive/manager, T38 specialized knowledge).
   c. Any citizenship, same multinational, 1 yr continuous full-time in last 3 yrs (e.g. L-1 / H-1B with a global employer)
      -> Intra-company transferee C12 (C62 exec/manager max 7 yrs; C63 specialized knowledge max 5 yrs).
   d. Otherwise -> LMIA-based permit (work-permits-lmia.md) or another IMP code; spouse may qualify for an OWP (open-work-permits.md).
   - Where to apply: port of entry ONLY if visa-exempt (US citizen, LPR, eTA national) and the LMIA / offer number is ready
     (work-permit-process-and-status.md). Visa-required nationals apply online before travel.
     Flagpoling (leaving to the US and re-entering just for a permit) ended 2024-12-23 for most people already in Canada.
4. PR routes (run /crs, /fsw, /clb, /pnp)
   - Express Entry FSW: US experience counts as foreign skilled experience; needs 67/100 grid + CLB 7 + ECA for US degree.
     Proof of funds unless authorized to work in Canada with a valid job offer.
   - CEC only after 1 yr skilled work IN Canada (so: work permit first, then CEC).
   - Job offer: no LMIA needed for ITAs from 2026-11-03.
   - Categories (category-based-selection page 2026-10-16): French, healthcare/social services, STEM, trades, education,
     transport, physicians / senior managers / researchers with Canadian experience, skilled military recruits.
     **No H-1B category exists.** STEM is the usual fit for tech H-1B profiles.
   - PNP: check each province's tech / employer streams (/pnp).
5. H-1B pathway (perishable)
   - Budget 2025 (chapter 1): "in the coming months the government will also launch an accelerated pathway for H1-B visa holders."
   - Status 2026-11-13: ANNOUNCED, NOT OPEN. No IRCC launch page; no Express Entry category. Do not tell clients it is open.
   - The 2023 H-1B open work permit (one-time, capped) is closed. Check 14-policy-tracker before advising.
6. Admissibility checks for US applicants
   - Impaired driving (DUI/DWI) is serious criminality since 2018-12-18: deemed rehabilitation unavailable; individual
     rehabilitation or TRP (criminality-rehabilitation-arc.md). Ask about every arrest, charge and diversion.
   - Police certificate: FBI Identity History Summary (IRCC US page 2025-06-17); for PR, each country with 6+ months
     in a row in the last 10 years since 18.
```

## Watch
- Clients often think H-1B or green-card status gives a Canadian advantage: it does not, except entry documents.
- TN status is a US status; a Mexican or Canadian citizen's CUSMA eligibility comes from citizenship, not TN.
- Undisclosed US arrests (even dismissed) are a misrepresentation risk (s.40).
