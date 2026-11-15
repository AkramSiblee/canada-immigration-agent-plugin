---
description: Record hours on a file and see what each file and each kind of file earns per hour
argument-hint: [case id, hours, what was done; or "report"]
---
Request: $ARGUMENTS

- Record: `python3 scripts/timesheet.py add CASE HOURS "what was done" [--date D] [--who NAME]`. A correction is a new line with negative hours.
- One file: `python3 scripts/timesheet.py show CASE`: hours, fees and the effective hourly rate.
- Firm-wide: `python3 scripts/timesheet.py report [--from D] [--to D] [--closed] [--target 150]` saves an Excel in Output/general with each
  file and each program's rate, lowest first. Set a target once: `python3 scripts/timesheet.py target 150`.
Fees come from the billing ledger (professional fees invoiced, or the agreement's estimate if nothing is invoiced yet).
When a kind of file keeps coming in under target, suggest reviewing its fixed fee or the scope in the service agreement.
