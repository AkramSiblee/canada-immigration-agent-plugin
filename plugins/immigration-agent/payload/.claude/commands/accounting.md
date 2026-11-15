---
description: Export invoices, payments and client account movements for your bookkeeper, QuickBooks or Xero
argument-hint: [from date, to date]
---
Request: $ARGUMENTS

1. Once: `python3 scripts/accounting.py setup --fees-account CODE --disbursements-account CODE --tax-type "TAX TYPE" [--terms-days N]`,
   with the codes from the consultant's own chart of accounts (ask; never guess them).
2. `python3 scripts/accounting.py export [--from YYYY-MM-DD] [--to YYYY-MM-DD]`. Report the totals it prints.
   - Excel for the bookkeeper in Output/general: invoices, payments applied to invoices, client account movements.
   - Import files in cases/exports/ for Xero and QuickBooks Online. Tell the consultant to check the column mapping on the import
     screen, and to delete the files once imported (they hold client names).
3. Client account (trust) money is never income until applied to an invoice; it stays on its own sheet (Code s.32). For reconciliation,
   use /billing reconcile, not this export.
