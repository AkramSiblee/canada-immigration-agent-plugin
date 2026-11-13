# Cases
One folder per client matter. Client folders are ignored by git; only this README is tracked.

## Layout
- `active/<YYYY-NNN-surname-program>/` : open files
- `closed/<YYYY-NNN-surname-program>/` : closed files, kept apart as CICC requires
- `closed/closed-files.csv` : closed-files list with the earliest destruction date

Each client folder has:
- `case.md` : facts, family, risk flags, advice given, closing checklist
- `deadlines.csv` : tracked deadlines
- `log.md` : every contact, filing, decision and advice, in date order
- `property.csv` : client property received and returned
- `client-facts.csv` : answers the client gave, used by form worksheets (person, key, value, source)
- `01-intake`, `02-agreements`, `03-documents`, `04-advice`, `05-forms-submissions`, `06-correspondence`, `07-billing`
- `client-ids/` : identity scans. The agent is blocked from reading this folder

## Commands
Use `/case` in chat, or run these directly:
```
python3 scripts/case.py new Khan spousal --client "Sara Khan"
python3 scripts/case.py status
python3 scripts/case.py show 2026-001
python3 scripts/case.py rules
python3 scripts/case.py deadline 2026-001 iad-sponsorship --from 2026-11-09
python3 scripts/case.py deadline 2026-001 custom --due 2027-01-15 --desc "Work permit expires"
python3 scripts/case.py done 2026-001 1
python3 scripts/case.py log 2026-001 "Spoke with client about refusal"
python3 scripts/case.py set 2026-001 agreement_signed yes
python3 scripts/case.py close 2026-001
```

## Document progress
Each case is compared with IRCC's official checklist for its program (`templates/checklists/`: visitor, study permit, work permit, Express Entry, spousal, PGP, super visa, citizenship, PR card). The dashboard shows it on the case page: percentage received, still missing, to confirm, and the full list. Mark items there, or:
```
python3 scripts/readiness.py checklist 2026-001
python3 scripts/readiness.py mark 2026-001 6 not-needed        (received | missing | not-needed | clear)
python3 scripts/readiness.py add 2026-001 "Employer leave letter" --note "IMM 5890"
```
Marks go to `checklist-marks.csv` and added items to `checklist-extra.csv` in the case folder. Both are add-only, so every change is kept. The percentage counts required documents only; conditional items wait until you mark them.

## Readiness report
Before filing, `python3 scripts/readiness.py report 2026-001` saves `05-forms-submissions/YYYY-MM-DD-readiness-report.xlsx`: items to fix before filing, urgent items, and things to do, from every check on the file. Add `--form imm1234` for each form if the program's usual forms don't fit. It never says a file is ready; the final review is yours.

## Client status updates
The Code requires timely written updates when anything is submitted or received for a client (s.22(3)). Each case keeps `updates.csv`.
```
python3 scripts/updates.py record 2026-001 --kind submitted --what "your study permit application" --ref S123456789
python3 scripts/updates.py record 2026-001 --kind received --what "the biometrics instruction letter" --client-action "Give your biometrics within 30 days"
python3 scripts/updates.py notify 2026-001
python3 scripts/updates.py list 2026-001
```
The daily alerts flag an event the client hasn't been told about after 2 days (urgent after 7), and a requested copy not sent after 5 days. These are practice defaults; the Code says "timely" without a number.

## Daily alerts
`scripts/alerts.py` checks every open file each morning, on this computer only, and saves `Output/general/YYYY-MM-DD-alerts.xlsx` when something has changed. Pop-ups show counts only.
```
python3 scripts/alerts.py run
python3 scripts/alerts.py status
python3 scripts/alerts.py install --time 08:00
python3 scripts/alerts.py uninstall
python3 scripts/case.py set 2026-001 status_expiry 2027-01-15
python3 scripts/case.py set 2026-001 passport_expiry 2028-06-30
```
It covers deadlines, expiring documents, file gaps, quiet files, ended retention periods and rule changes matched to each file's program and province. It only knows dates recorded in the file. No alert doesn't mean no deadline.

## Billing and client account
`scripts/billing.py` keeps an add-only ledger in each file's `07-billing/ledger.csv`, and saves receipts, invoices and statements there as PDFs. Monthly reconciliations go to `reconciliations/`, kept 6 years.
```
python3 scripts/billing.py setup --model 1        (name, licence and address come from firm.py setup)
python3 scripts/billing.py estimate 2026-001 --fees 3000 --disbursements 1085
python3 scripts/billing.py receive 2026-001 1500 --method e-transfer --purpose fees
python3 scripts/billing.py invoice 2026-001 --desc "Prepared and filed the application" --services-to 2026-11-09 --fees 1500 --tax 195
python3 scripts/billing.py withdraw 2026-001 1695 --reason fees --method eft --invoice 2026-001-01
python3 scripts/billing.py show 2026-001
python3 scripts/billing.py statement 2026-001
python3 scripts/billing.py reconcile --month 2026-10 --bank 5000
```
A file can't close while client money is held, a receipt is undeposited or an invoice is unpaid. The daily alerts flag deposits due, invoiced trust money not withdrawn within 30 days, and months not reconciled.

## Rules built in (CICC Client File Management Regulation)
- A file closes only when fees are settled, property is returned, and the client is told in writing (s.7.1).
- Closed files are kept at least 6 years, with a closed-files list and a projected destruction date (s.7.2 to s.7.4).
- Nothing is ever deleted automatically. Record any destruction in a log: client name and address, service, closing date, destruction date (s.10).

Computed dates are planning aids. Confirm limitation dates against the decision itself.
