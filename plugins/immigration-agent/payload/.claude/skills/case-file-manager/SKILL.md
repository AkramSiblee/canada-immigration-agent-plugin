---
name: case-file-manager
description: Open, update, review and close client case files, and track deadlines. Use when the user names a client file or asks about open cases, deadlines, or filing work to a case.
---
# Case File Manager

## Read first
- cases/README.md
- knowledge/10-consultant-practice/record-keeping.md

## Workflow
1. Open: `python3 scripts/case.py new SURNAME PROGRAM --client "Full Name"`. Run a conflict check before work starts.
2. Update: fill `case.md`, and record every contact, filing, decision and advice with `case.py log`.
3. Deadlines: list types with `case.py rules`, then add with `case.py deadline CASE TYPE --from DATE`. Always ask for the date the client actually received or learned of the decision. Never guess it.
4. Review: `case.py status`. Report overdue items first, then items due soon, then file gaps.
   Alerts: `python3 scripts/alerts.py run`, then `status` to confirm the daily task is running. Report counts and point to the alerts file. Record status and passport expiry with `case.py set CASE status_expiry DATE`.
   Billing: use `scripts/billing.py` (see cases/README.md). Read knowledge/10-consultant-practice/client-agreements-trust-fees.md first. Never record an amount the user hasn't given. Report any refusal message as it stands; never work around a rule check.
   Client updates (Code s.22(3)): every time something is submitted or received for the client, run `python3 scripts/updates.py record CASE --kind submitted|received --what "..." [--party IRCC] [--date D] [--ref NUMBER] [--next "..."] [--client-action "..."]`, then `updates.py notify CASE` to draft the letter on letterhead. Copy requests: `--kind copy-requested`, then `updates.py sent CASE ROW` once sent. Never invent dates, numbers or next steps; ask.
   Before filing: run `python3 scripts/readiness.py report CASE` (see the application-package-qa skill).
5. File work: when the user asks, copy a finished deliverable into the case folder and add it to "Advice given" in `case.md`.
6. Close: only after fees are settled, property returned and the client told in writing. `case.py close CASE` then records the file for 6 years.

## Guardrails
- Before relying on a rule in `scripts/deadline_rules.csv`, check its `last_verified` date. If it's more than 90 days old, verify it on the official source and update the row.
- A computed date is a planning aid. For Federal Court, IAD or other limitation dates, tell the user to confirm the date against the decision itself.
- Never delete client files or edit `Input/`. Destruction is a manual decision by the RCIC, recorded in a destruction log.
- Don't store passport, UCI or other identity scans outside `client-ids/`, which is blocked from reading.
- Flag IRPA s.40, IRPR 117(9)(d) and ghost-consultant risk whenever seen. Refer Federal Court matters to a lawyer.
