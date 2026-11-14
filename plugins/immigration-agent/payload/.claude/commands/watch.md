---
description: Check IRCC's form versions and fees against what the agent knows
argument-hint: [forms | fees]
---
Request: $ARGUMENTS

1. Run `python3 scripts/watch.py check` (add `--forms-only` or `--fees-only` if asked). It reads IRCC's public form pages and the fee list only.
2. Report: forms with a newer version on IRCC (autofill refuses these until the agent is updated, so the consultant fills the new version by
   hand from the worksheet answers and checks every question); forms republished under the same date (download the blank again); fees
   changed, added or no longer listed (use IRCC's amount, cite https://ircc.canada.ca/english/information/fees/fees.asp and today's date);
   anything that couldn't be checked (never present it as unchanged).
3. The daily alerts run this once a week and the dashboard shows the results. `python3 scripts/watch.py status` shows the last result.
Don't edit the knowledge base or the fee baseline in a firm's folder: updates come with new agent versions.
