---
domain: 12-decision-trees
topic: family
status: verified
last_verified: 2026-11-20
confidence: H
review_every_days: 90
sources:
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/canadian-citizenship/proof-citizenship.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/canadian-citizenship/act-changes/rules-2025.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship/spouse-partner-children/eligibility.html
  - https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship/spouse-partner-children/who-you-can-sponsor.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship/spouse-partner-children/spouse-common-law-partner-canada-open-work-permit.html
  - https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/page-1.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/policies-operational-instructions-agreements/ministerial-instructions/other-goals/mi89.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/parent-grandparent-super-visa/eligibility.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/news/notices/changes-parents-grandparents-super-visa-income-requirement-calculated.html
  - https://ircc.canada.ca/english/information/fees/fees.asp
  - knowledge/04-family/*.md
  - knowledge/07-citizenship-pr-status/citizenship-proof-bill-c3.md
---
# Decision tree: family

## Must cover
- Spouse, PGP, Super Visa, C-3 check

## Current rules
```
0. C-3 check: born abroad to a Canadian parent? -> maybe already a citizen.
   Apply for a certificate ($75). Complex cases go to a lawyer.
1. Who is the sponsor?
   18+, citizen/PR/registered Indian, living in Canada (PR abroad can't sponsor)?
   Bars: s.130(3) 5-yr; prior spouse undertaking; s.133 (removal order, jail,
   convictions, default, bankruptcy, social assistance non-disability) -> STOP / remedy
2. Who is sponsored?
   a) Spouse / common-law (12 mo cohabitation) / conjugal (barrier proof)
      - s.117(9)(c),(c.1) proxy marriage?  (d) undeclared at sponsor's landing? -> barred
        (public policy ended 2026-09-10; H&C only)
      - In Canada + cohabiting + status -> SCLPC class: OWP with AOR; no IAD appeal
      - Otherwise -> Family class: IAD appeal (30 days)
   b) Dependent child (<22, or 22+ dependent with condition) -> custody/consent; examine all
   c) Parent/grandparent -> PGP PAUSED (MI89; no intake) -> Super Visa
      (income table, 2-yr look-back, 75% + parent income; OSFI insurer at least $100k, 1 yr)
   d) Other relatives -> only "lonely Canadian" / orphaned rules (R117(1)(f)-(h)); H&C
3. Sponsor lives in Quebec? -> also MII undertaking: cap 15,700 to 2028-06-30
   (13,300 spouses; 2,400 parents/others; children exempt), filing date set by the
   IRCC letter date (03-quebec/family-sponsorship-quebec.md)
4. Abuse in the relationship / status depends on abuser? -> family violence TRP
   (fee-exempt, OWP, IFHP) + H&C (06-protection-humanitarian/family-violence-trafficking-vulnerable-workers.md)
5. Fees: spouse $1,260; child $180; Super Visa $100 + $85 biometrics
```

## Recent changes (2025-2027)
- 2026-09-10: 117(9)(d) relief ended; 2026-03-31: Super Visa income change (H)

## Consultant pitfalls
- Choose class (in-Canada vs family class) by weighing the appeal right against the OWP.

## Common refusal reasons
- See 04-family files

## Re-verify before advising
- PGP intake announcements; Quebec cap usage per category

## Sources
Official pages for each time-sensitive rule (read when the linked knowledge files were last verified):
- Proof of citizenship and Bill C-3 ($75 certificate): https://www.canada.ca/en/immigration-refugees-citizenship/services/canadian-citizenship/proof-citizenship.html
- Bill C-3 rules (citizenship by descent): https://www.canada.ca/en/immigration-refugees-citizenship/services/canadian-citizenship/act-changes/rules-2025.html
- Sponsor eligibility and bars (IRPR s.130, s.133): https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship/spouse-partner-children/eligibility.html
- IRPR s.117(9), s.130, s.133 (text): https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/
- Who you can sponsor; 117(9)(d) public policy ended 2026-09-10: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship/spouse-partner-children/who-you-can-sponsor.html
- Spouse in Canada class: open work permit: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship/spouse-partner-children/spouse-common-law-partner-canada-open-work-permit.html
- IAD appeal: 30 days (IRPA s.63; IAD Rules 2022 r.16): https://laws-lois.justice.gc.ca/eng/regulations/SOR-2022-277/page-1.html
- PGP paused (MI89): https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/policies-operational-instructions-agreements/ministerial-instructions/other-goals/mi89.html
- Super Visa eligibility, income and insurance: https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada/parent-grandparent-super-visa/eligibility.html
- Super Visa income change (2026-03-31): https://www.canada.ca/en/immigration-refugees-citizenship/news/notices/changes-parents-grandparents-super-visa-income-requirement-calculated.html
- Fees: spouse $1,260; child $180; Super Visa $100; biometrics $85 (fee list modified 2026-11-10): https://ircc.canada.ca/english/information/fees/fees.asp
- Quebec sponsorship caps (MII, 2026-11-11): https://www.quebec.ca/en/immigration/permanent/sponsor-family-member/rules-reception-applications
- Family violence TRP (PDI 2025-04-04): https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/permits/family-violence.html
- Derived from knowledge/04-family, 03-quebec, 06-protection-humanitarian and 07-citizenship-pr-status (all H; tree re-checked 2026-11-20)
