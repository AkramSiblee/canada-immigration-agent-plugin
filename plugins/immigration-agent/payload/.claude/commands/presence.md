---
description: Count days in Canada for citizenship (1,095) or the PR residency obligation (730) from the client's trips
argument-hint: [case id, citizenship or pr, dates]
---
Request: $ARGUMENTS

1. Record each trip in the case's travel-history.csv: `python3 scripts/presence.py add CASE --left YYYY-MM-DD --returned YYYY-MM-DD --to COUNTRY --reason TEXT [--counts-as TYPE]`.
   Leave --returned out while the client is still abroad. --counts-as: crown (Crown service abroad, citizenship), citizen-spouse,
   canadian-employer or accompanying-employee (PR residency exceptions; proof needed).
2. Citizenship: `python3 scripts/presence.py citizenship CASE --pr-date D [--tr-from D] [--sign D] [--excluded FROM:TO]`.
   --tr-from is the first day in Canada as a temporary resident or protected person (half-day credit, max 365); --excluded for probation,
   parole, prison or conditional sentence (s.21). Gives the total, the margin and, if short, the earliest signing date.
3. PR: `python3 scripts/presence.py pr CASE --pr-date D [--as-of D]`. Gives the 730-day result (or, under 5 years as PR, whether it can still be met
   by the 5th anniversary) and the latest date the client can return if they leave now.
The PR date can also come from a pr_date fact in client-facts.csv. A report is saved in the case's 04-advice.
Departure and return days count as days in Canada (IRCC). The result is only as good as the trip list: check it against passport stamps and the
CBSA travel history, and use IRCC's own calculator for the application itself. A margin under 30 days is reported as too close.
