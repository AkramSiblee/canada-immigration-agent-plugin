---
description: LMIA stream, refusal-to-process, cap and recruitment checks for an employer file
argument-hint: [province, wage, location, industry, workforce, or an ads file]
---
Read `knowledge/05-temporary-residence/work-permits-lmia.md` first. Request: $ARGUMENTS

- Position check: `python3 scripts/lmia.py check --province ON --wage 28.50 --cma Toronto --naics 722 --noc 62200 --tfw 2 --workforce 25 [--date YYYY-MM-DD] [--days N] [--agricultural|--caregiver|--pr-only|--seasonal]`
- Recruitment: `python3 scripts/lmia.py recruit ads.csv --apply YYYY-MM-DD --stream high|low [--job-match YYYY-MM-DD]` (columns method,start,end,national,group)

Report STOP items first. The thresholds (`templates/lmia/wage-thresholds.csv`, each July) and the unemployment table (`templates/lmia/cma-unemployment.csv`, each quarter; next 2027-01-08) must be current: update them from ESDC when they change. LMIA applications are filed in LMIA Online; the employment agreement is EMP5711 (high-wage), EMP5712 (low-wage) or EMP5713 (Global Talent); a representative is named on EMP5575. The client is usually the employer: check the agreement and conflicts accordingly.
