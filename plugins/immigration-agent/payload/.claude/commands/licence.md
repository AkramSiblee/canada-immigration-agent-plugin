---
description: Your CICC licence: annual fee, professional liability insurance and CPD hours, with reminders before each deadline
argument-hint: [status | cpd-add ... | setup | paid ...]
---
Request: $ARGUMENTS

1. Read `knowledge/10-consultant-practice/licensing-cpd-insurance.md` first. If it is stale (over 90 days), re-check the CICC CPD, fees and
   insurance regulations on college-ic.ca before relying on the numbers (CLAUDE.md rules 1-2).
2. Once: `python3 scripts/practice.py setup --class RCIC|RCIC-IRB|RISIA --fees single|instalments [--licensed-on YYYY-MM-DD]`
   (licensed-on only for a first licence in the current term).
3. CPD: `python3 scripts/practice.py cpd-add --date D --hours H --title "..." [--provider ...] [--area ...] [--professionalism] [--proof FILE]`.
   --professionalism for hours on professionalism or the Code (1 hour needed each term). Leave: `practice.py leave --term 2026 --months N`.
4. Payments: `python3 scripts/practice.py paid annual-fee|instalment-1..4|insurance [--term 2026]` once paid, so the reminder stops.
5. `python3 scripts/practice.py status` shows the term's hours, what is missing and what is due. The daily alerts and dashboard warn before
   June 30 (CPD) and each fee and insurance date. The College account is the record that counts.
