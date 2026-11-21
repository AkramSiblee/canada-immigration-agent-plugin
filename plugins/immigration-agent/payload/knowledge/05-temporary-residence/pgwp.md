---
domain: 05-temporary-residence
topic: pgwp
status: verified
last_verified: 2026-11-20
confidence: H
review_every_days: 90
sources:
  - https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/study-permits/post-graduation-work-permit-program.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/field-of-study/currently-eligible.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/about.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/field-of-study.html
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/language-results.html
---
# Post-Graduation Work Permit (PGWP)

## Must cover
- Language, field-of-study list status, duration, 180-day rule, ineligible programs

## Current rules
### Eligibility
- Program at a **PGWP-eligible DLI**, at least **8 months** (900 h in Quebec); full-time each semester (final semester may be part-time).
- Apply within **180 days** of confirmation of completion. The study permit must have been valid at some point in those 180 days.
- **One PGWP per lifetime.**
- Fee **$255** ($155 + $100 OWP holder fee).

### Language (applications from 2024-11-01)
| Program | Minimum (all 4 skills) |
|---|---|
| Bachelor's, master's, doctoral, other university | **CLB/NCLC 7** |
| College, polytechnic, other non-university | **CLB/NCLC 5** |
| Flight school | None |

### Field of study
- **Not required** for bachelor's, master's, doctoral graduates.
- Required for other programs if the study permit application was made **on or after 2024-11-01**.
- **2026: list frozen.** "For 2026, we won't add or remove any eligible fields of study." Some entries are date-conditioned (e.g. teacher education and social work "after June 25, 2025").

- **Transition (list page 2026-03-09, read 2026-11-09; the 2026-01-15 notice date is M):** study permit before 2024-11-01: no requirement. Applied before 2025-06-25: eligible if on the list when applied. Fields removed 2025-06-25 were reinstated around 2025-07-04/07 (M); applicants in that window still qualify. CIP must be on the list at study permit or PGWP application. Lock-in is the study permit application date, not enrolment.
- List checked 2026-11-09: 52.0201, 52.0101, 52.0213, 52.0301, 52.0801, 52.1401 **not listed**; 52.0203, 52.0208, 52.1201, 52.1404 listed. Some rows are date-conditioned.

### Field-of-study list (stored)
- **File:** `templates/pgwp/field-of-study.csv`. Columns: cip, title, category, condition, condition_type, condition_date, page_modified, read_date.
- **Source:** IRCC field-of-study page, page details date **2026-03-09**, read 2026-11-17. Every CIP row from the page's search tables.
- **Rows: 1,107; unique CIPs 1,096** (11 CIPs sit in two categories). Rows extracted from the IRCC page (2026-03-09) with a summarizing fetch and spot-checked; a secondary count also gives 1,107 (M for transcription)

| Category | Rows | Date-conditioned |
|---|---|---|
| Agriculture and agri-food | 43 | 0 |
| Education | 69 | 48 |
| Healthcare and social services | 594 | 49 |
| STEM | 314 | 17 |
| Trade | 66 | 14 |
| Transport | 21 | 0 |
| **Total** | **1,107** | **128** |

- 11 CIPs appear in two categories: 01.9999, 14.3301, 15.1001, 44.0403, 47.0615, 48.0507, 26.0802, 26.0807, 26.0899, 26.0910, 30.1901.
- **Date-conditioned rows (128):** IRCC cell wording is "Your program is eligible if you submitted your study permit application" [and separately "your PGWP application"]: "Before November 1, 2024" / "After June 25, 2025". There are 119 rows with June 25, 2025. There are 9 rows with "After December 17, 2024": 13.1207, 13.1208, 13.1210, 13.1501, 19.0706, 19.0708, 19.0709, 19.0711 and 19.0710. The CSV stores all 128 conditioned rows as `condition_type=other` (meaning "before 2024-11-01 or after condition_date") with `condition_date` = the "after" date. Either application (study permit or PGWP) falling in a window satisfies the row. IRCC says "after", not "on or after"; how an application filed on the date itself is treated is not stated.
- **No removed-fields table** is published on IRCC pages. Secondary sources say 178 fields were removed on 2025-06-25 and reinstated around 2025-07-04/07 (the date varies by source; M). Because nothing is published, `field-of-study-removed.csv` was not created.
- **Freeze:** "For 2026, we won't add or remove any eligible fields of study." (H)
- **2027 list: not published** (checked 2026-11-20). Field-of-study page still shows page details **2026-03-09** and the 2026 freeze text, no 2027 wording. IRCC notices page has no field-of-study notice after 2025-06-25. No secondary source reports a 2027 list. CSV left unchanged. Recheck from January 2027.
- **Lock-in and transition (IRCC page + PDI):**
  - The CIP "must be on the list of currently eligible CIP codes when you submit either your study permit application or your PGWP application".
  - PDI: "applicants may complete that program and remain eligible for a PGWP even if that field-of-study becomes ineligible".
  - Exempt groups: study permit applied for before 2024-11-01; PGWP applied for before 2024-11-01; bachelor's, master's and doctoral graduates; flight school graduates.
  - The "Currently eligible CIP codes" sub-page shows "Last updated: July 4, 2025", while the main page shows 2026-03-09. The rows checked (STEM, Trade, Transport, Agri) agree. The sub-page's Agri list showed 42 codes, without 12.0506 Meat cutting, which the main page lists. The main page is used as the authority.
- **How to check:** `python3 scripts/cip_check.py <CIP> [--applied YYYY-MM-DD] [--pgwp YYYY-MM-DD]` (e.g. `52.0203`): eligible, date-conditioned, not eligible (date condition not met) or not listed. Rows conditioned "before 2024-11-01 or after <date>" accept either the study permit or the PGWP application date; the condition day itself is unclear (confirm). Then confirm on the live IRCC page before advising, and confirm the CIP on the DLI's official completion documents.

### How IRCC measures program length (PGWP PDI, page date 2025-12-11, read 2026-11-17; H)
- **Measure the program, not the student's time.** "The length of the work permit should coincide with the length of the program", "as confirmed by the eligible designated learning institution (DLI) in the written confirmation of program completion". The transcript or completion letter "can be used on its own". Officers "may consider the duration of the program of study in Canada and confirm it with supporting documents."
- **Calendar vs stated length:** the PDI does not define calendar months against the stated length. It relies on the program length confirmed by the DLI. Scheduled breaks are included: "Regularly scheduled breaks (for example, regularly scheduled winter and summer breaks) should not be subtracted". Breaks do not count toward the full-time requirement.
- **Minimums:** the program is "at least 8 months, but less than 2 years" (PGWP = program length) or 2+ years (generally 3 years). Quebec vocational (DVS/AVS): "at least 900 hours, but less than 1,800 hours". "Each additional 112 hours" adds one month, and "Officers should round up to the next full month". 1,800+ hours gives 3 years. A master's of 8+ months but under 2 years (applications from 2024-02-15) can get up to 3 years; graduate certificates and diplomas are excluded.
- **Leave:** for leave authorized by the DLI, the applicant "must include, with their application, documentation that proves the leave was authorized by the DLI". The PDI does **not** say whether leave reduces PGWP length. The 150-day authorized-leave limit is on the public eligibility page, not the PDI.
- **Accelerated programs:** "the PGWP should be assessed on the length of the program, not the length of studies." Example: a 1-year (3-semester) program finished in 2 semesters (8 months) can get up to 1 year. **Exception:** if studies were shorter and *not* accelerated (e.g. 12 months of classes in a 2-year program), "the PGWP may be issued according to the duration of studies". Officers "may request additional information to determine whether the program was completed in an accelerated form."
- **Online / outside Canada:** courses completed outside Canada "must be excluded from the time that counts toward the length of the PGWP". More than 50% by distance means the program "may reasonably be considered a distance-learning program" (ineligible).
- **Combining programs (stacking):**
  - "both PGWP-eligible programs must" each be 8+ months at an eligible DLI. "The second program must be completed within 2 years of the completion of the first program."
  - If the combined length is 2+ years, the PGWP can be up to 3 years.
  - For study permits from 2024-11-01: "officers should assess each program separately against the applicable field-of-study requirements". If one program fails, "they would not benefit from program stacking" and the PGWP is based only on the eligible program. If the eligible program was the first, the 180 days run from its completion.
- **Transfers:** time at eligible DLIs is combined toward the 8 months. Time at an ineligible institution doesn't count. Credits transferred between eligible DLIs are considered.

### Program change after the study permit (PDI 2025-12-11 + field-of-study page 2026-03-09; H unless marked)
- **Program assessed is the one completed.** The field-of-study test applies to a graduate of "a program that does not result in a bachelor's, master's or doctoral degree". The PDI says "a CIP from the PGWP-eligible field-of-study list should be provided on official documentation" from the DLI, e.g. the completion letter. If the DLI documents omit it, the applicant should add the CIP with an explanation. The public page says you must "graduate from a program that's on the list". The test is therefore on the **completed program's CIP**, not on the program named on the LOA or study permit.
- **Lock-in date:** "the CIP should be on the PGWP-eligible list at the time of the study permit application" (or at PGWP application). The PDI does not expressly say that a program switched *within* the same study permit locks in at the original study permit date. Treat as M: the CIP of the new program must itself have been on the list at the study permit date or at the PGWP date.
- **New CIP must be on the list.** A program switch to a CIP that is not listed (or not listed in the relevant window) fails, unless a degree-level exemption applies.
- **Changing DLI:** "A student who has changed DLIs will need to apply for a new study permit." Studying at a DLI not on the permit risks a 6-month work bar (R200(3)(e)(i)). The PDI warns that someone with a pre-2024-11-01 study permit who "submit[s] a new study permit application on or after November 1, 2024, would not meet this exemption from the field-of-study requirement". **A new study permit application resets the field-of-study date.** An *extension* of a pre-2024-11-01 permit keeps the exemption "regardless of the field-of-study they had on the initial study permit."
- **Changing level:**
  - Moving to a bachelor's, master's or doctoral degree removes the field-of-study requirement. The PDI says students on a pathway "can follow the PGWP eligibility rules that are associated with acquiring a credential from a bachelor's degree program".
  - Moving down to a college diploma or certificate brings in the field-of-study test and the CLB 5 test.
  - The language level follows the credential completed: CLB 7 for university and degree programs, CLB 5 for other programs. Non-university degree graduates who applied 2024-11-01 to 2025-03-10 needed CLB 5; from 2025-03-11 they need CLB 7.
- **Unknown (re-checked 2026-11-20):** no IRCC text on a CIP change by the DLI (recoding) mid-program. Field-of-study page (2026-03-09, read in full) and PGWP PDI (2025-12-11) are silent. What they do say: CIP must be on the list "when you submit either your study permit application or your PGWP application"; IRCC uses "6-digit CIP codes based on the CIP Canada 2021"; a CIP "should be provided on official documentation by the DLI", and if missing, applicants "are encouraged to include the eligible CIP code" (H). Practice (M): get the DLI's letter stating the CIP of the program completed and the recoding date; test **both** codes against the list on the study permit date and the PGWP date; if only the old code qualifies, explain the recoding in a letter and expect officer discretion. A secondary search found no IRCC statement either.
- **Thesis-stage scheduled breaks (re-checked 2026-11-20):** no IRCC text on thesis or research-stage students in the PGWP PDI, Help Centre 499/503 or the work off campus page. For PGWP length the PDI counts "regularly scheduled breaks" in the program length; for full-time status breaks are excluded. Whether a thesis term without classes is a "scheduled break" depends on the DLI calendar (see study-permit-status-and-compliance.md) (M).

### Length
- 8 months to under 2 years: up to the program length. 2+ years: up to 3 years. **Master's of at least 8 months: up to 3 years** (since 2024-02-15).
- Capped at passport expiry.

### Ineligible
- Prior PGWP; ESL/FSL-only; general-interest or non-credit programs (except flight school); GAC scholarship with return obligation
- **More than 50% distance learning**: since 2024-09-01, at least 50% must be in class in Canada. Online study from abroad after 2024-08-31 doesn't count toward length.
- Non-Canadian institutions in Canada
- **Curriculum licensing (P3) colleges**, except: same-province programs started on or before 2024-05-15; between-province on or before 2023-01-31

### Language test scores (IRCC 2026-05-27)
Listed tests: CELPIP General, **IELTS General Training**, PTE Core, TEF Canada and others on the IRCC page. **IELTS Academic isn't in the table**, so a study permit IELTS Academic score won't serve for the PGWP.

| Level | IELTS General (R / W / L / S) | CELPIP General | PTE Core (R / W / L / S) |
|---|---|---|---|
| CLB 7 | 6.0 / 6.0 / 6.0 / 6.0 | 7 | 60-68 / 69-78 / 60-70 / 68-75 |
| CLB 5 | 4.0 / 5.0 / 5.0 / 5.0 | 5 | 42-50 / 51-59 / 39-49 / 51-58 |
- Exempt: flight school graduates; applications before 2024-11-01.

## Recent changes (2025-2027)
- 2024-11-01: language and field-of-study rules (H)
- 2025-06-25: field-of-study list update (entries dated) (H)
- 2026: field-of-study list frozen for the year (H) - confirms baseline (exact "2026-01-15" date not found on page; M for that date)

### Checking a school (IRCC DLI list data, read 2026-11-09)
- JSON: https://www.canada.ca/content/dam/ircc/documents/json/dli/dli-full-list.json . PGWP field values: Yes, Details (some programs only; see row details), No. Entries offering PGWP-eligible programs: public 603 of 608, private 248 of 817, Ontario private 69 of 336. Not all programs at a listed DLI are eligible. CIP must be on the list when the study permit or PGWP application is submitted.

### Leave, part-time and online (IRCC eligibility page 2026-06-24, read 2026-11-09)
- Authorized leave up to 150 days can still meet permit conditions, with DLI proof at PGWP application; unauthorized leave may make the applicant ineligible. Effect of a leave on PGWP length not stated on public pages. Over 50% distance learning is ineligible. Started on or after 2024-09-01: at least 50% in class in Canada; time online from outside Canada is deducted.
- Work while waiting (Help Centre 1181, 2026-11-03): applied with valid study permit, program completed, was eligible to work off campus, did not exceed 24 h/week in term.

### Unauthorized work or non-compliance (IRPR 200(3)(e); Justice Laws current to 2026-10-29, read 2026-11-17) (H)
- No work permit (including a PGWP) for someone who engaged in unauthorized work or study, or breached a permit condition, unless: (i) 6 months have passed since it stopped; (ii) the breach was only of conditions under R185(a), 185(b)(i)-(iii) or 185(c); (iii) s.206 applies; (iv) a TRP was later issued. Study permits: same bar in s.221 (exceptions (i), (ii), TRP).
- Working over 24 h/week off campus in term is generally treated as unauthorized work (hours are a 'times and periods' condition, R185(b)(iv), outside exception (ii)) (M: our reading; confirm on the facts).

## Consultant pitfalls
- Language test results must be valid (under 2 yrs) **at PGWP application**. Many grads test too late. Plan the test before program end.
- Field of study is tied to the **program's CIP code** on the DLI's list. Confirm the CIP before enrolment.
- Passport expiry cuts the PGWP length. Renew the passport before applying (a PGWP cannot be extended to fix this, except in narrow cases).
- If status lapses after completion, apply within 90 days for restoration + PGWP, still within 180 days.
- Combining programs: both must be eligible and completed within the time limits.

## Common refusal reasons
- Language below threshold or missing test; field of study not on list; P3 / non-eligible DLI; distance learning over 50%; applied after 180 days; prior PGWP

## Re-verify before advising
- 2027 field-of-study list update
- Any 2027 PGWP policy changes (Levels shift to PR from in-Canada pool)

## Sources
- PGWP landing (2026-03-09): https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation.html
- About/length (2026-03-09): https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/about.html
- Eligibility (2026-06-24): https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html
- Field of study: https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/field-of-study.html
All read 2026-11-07.
- Field of study page (page details 2026-03-09), read 2026-11-17 for full CIP extraction to `templates/pgwp/field-of-study.csv`
- Currently eligible CIP codes ("Last updated: July 4, 2025"), read 2026-11-17: https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/field-of-study/currently-eligible.html
- Field of study page re-read 2026-11-20 (still 2026-03-09, freeze text unchanged); IRCC notices page read 2026-11-20: https://www.canada.ca/en/immigration-refugees-citizenship/news/notices.html
- PGWP PDI and field-of-study page re-read 2026-11-20 for CIP recoding and thesis breaks (no text found)
- PGWP program delivery instructions (2025-12-11), read 2026-11-17: https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/study-permits/post-graduation-work-permit-program.html
