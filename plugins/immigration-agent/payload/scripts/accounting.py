#!/usr/bin/env python3
"""Accounting export: invoices and payments from every billing ledger, for your bookkeeper, QuickBooks or Xero.

Usage:
  python3 scripts/accounting.py setup [--fees-account 200] [--disbursements-account 260] [--tax-type "HST on Sales"] [--terms-days 0]
  python3 scripts/accounting.py export [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--out DIR]

What you get:
  - Output/general/YYYY-MM-DD-accounting-export.xlsx: invoices, payments applied to invoices, and client (trust) account movements
    on separate sheets, with totals.
  - cases/exports/YYYY-MM-DD-xero-invoices.csv and -quickbooks-invoices.csv: one line per fee, disbursement and tax amount,
    ready for the import screen. Check the column mapping on the import screen, and the account codes and tax type you set.

Guarantees:
  - Reads billing ledgers only (billing.py), in open and closed files. Nothing is changed and nothing is sent anywhere.
  - Reversed entries are left out. Money held in the client account is not income: it is listed apart and never in the
    invoice files. Only invoiced fees, disbursements and tax are.
  - The import files hold client names (needed for invoices). They stay in cases/exports/, which is in every backup.
    Delete them once imported.
"""
import argparse
import csv
import datetime
import json
import pathlib
import sys
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import billing as bl  # noqa: E402
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

SETTINGS = cs.ROOT / ".accounting-settings.json"
EXPORTS = cs.ROOT / "exports"
XERO = ["*ContactName", "EmailAddress", "*InvoiceNumber", "Reference", "*InvoiceDate", "*DueDate", "InventoryItemCode", "*Description",
        "*Quantity", "*UnitAmount", "Discount", "*AccountCode", "*TaxType", "TaxAmount", "Currency"]
QBO = ["InvoiceNo", "Customer", "InvoiceDate", "DueDate", "Memo", "Item(Product/Service)", "ItemDescription", "ItemQuantity", "ItemRate", "ItemAmount", "ItemTaxAmount"]


def settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def cmd_setup(a):
    s = settings()
    for k in ("fees_account", "disbursements_account", "tax_type"):
        v = getattr(a, k)
        if v is not None:
            s[k] = v
    if a.terms_days is not None:
        s["terms_days"] = a.terms_days
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, indent=1), encoding="utf-8")
    print("Accounting export settings: " + ", ".join(f"{k} {v}" for k, v in s.items()))


def email_of(folder):
    import replies
    e = replies.emails(folder)
    return e[0] if e else ""


def collect(start, end):
    invoices, payments, trust = [], [], []
    for folder in cs.folders(cs.ACTIVE) + cs.folders(cs.CLOSED):
        rows = bl.live(bl.load(folder))
        if not rows:
            continue
        info = cs.read_case(folder)
        client, cid = info.get("client", ""), info.get("case_id", folder.name[:8])
        inside = lambda d: (not start or d >= start) and (not end or d <= end)  # noqa: E731
        state = bl.summary(rows)
        for r in rows:
            day = bl.day_of(r["date"])
            if not inside(day):
                continue
            amt = bl.stored(r["amount"])
            if r["kind"] == "invoice":
                inv = state["invoices"].get(r["invoice"], {})
                invoices.append({"date": day, "number": r["invoice"], "client": client, "case": cid, "email": email_of(folder), "description": r["description"],
                                 "fees": bl.stored(r["fees"]), "disbursements": bl.stored(r["disbursements"]), "tax": bl.stored(r["tax"]), "total": amt,
                                 "owing": inv.get("total", amt) - inv.get("applied", Decimal("0"))})
            elif r["kind"] == "receipt" and r["account"] != "trust" and r["invoice"]:
                payments.append({"date": day, "invoice": r["invoice"], "client": client, "case": cid, "amount": amt, "how": f"paid directly ({r['method']})"})
            elif r["kind"] == "withdrawal" and r["invoice"]:
                payments.append({"date": day, "invoice": r["invoice"], "client": client, "case": cid, "amount": amt, "how": "transferred from the client account"})
            if r["account"] == "trust" and r["kind"] == "receipt":
                trust.append({"date": day, "client": client, "case": cid, "what": f"received toward invoice {r['invoice']}" if r["invoice"] else f"received in advance ({r['purpose'] or 'not stated'})", "in": amt, "out": Decimal("0")})
            elif r["kind"] == "withdrawal":
                trust.append({"date": day, "client": client, "case": cid, "what": f"withdrawn ({r['purpose'] or r.get('description') or r.get('reference') or 'see ledger'})", "in": Decimal("0"), "out": amt})
    key = lambda r: (r["date"], r.get("number") or r.get("invoice") or "")  # noqa: E731
    return sorted(invoices, key=key), sorted(payments, key=key), sorted(trust, key=lambda r: r["date"])


def lines(inv, s):
    """Import lines for one invoice: (description, amount, account, tax amount)."""
    out = []
    if inv["fees"]:
        out.append(("Professional fees: " + inv["description"], inv["fees"], s.get("fees_account", ""), inv["tax"]))
    if inv["disbursements"]:
        out.append(("Disbursements", inv["disbursements"], s.get("disbursements_account", ""), Decimal("0")))
    if inv["tax"] and not inv["fees"]:
        out.append(("Tax", inv["tax"], s.get("fees_account", ""), Decimal("0")))
    return out


def cmd_export(a):
    import openpyxl
    start = cs.parse_date(a.start, "--from") if a.start else None
    end = cs.parse_date(a.end, "--to") if a.end else None
    s = settings()
    invoices, payments, trust = collect(start, end)
    stamp = datetime.date.today().isoformat()
    out = pathlib.Path(a.out) if a.out else de.REPO / "Output" / "general"
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    path, n = out / f"{stamp}-accounting-export.xlsx", 1
    while path.exists():
        n += 1
        path = out / f"{stamp}-accounting-export-v{n}.xlsx"
    f = float
    book = openpyxl.Workbook()
    book.remove(book.active)
    period = f"{start or 'the start'} to {end or 'today'}"
    tot = {k: sum((i[k] for i in invoices), Decimal("0")) for k in ("fees", "disbursements", "tax", "total", "owing")}
    de.add_sheet(book, "Read me first", ["About this export"], [
        [f"Billing ledgers of all open and closed files, {period}."],
        [f"Invoices: {len(invoices)}. Fees {tot['fees']:,.2f}, disbursements {tot['disbursements']:,.2f}, tax {tot['tax']:,.2f}, total {tot['total']:,.2f}, still unpaid {tot['owing']:,.2f}."],
        ["Client account (trust) money is not income until it is applied to an invoice: it is listed on its own sheet."],
        ["Import files for Xero and QuickBooks are in cases/exports/. Check the column mapping on the import screen; delete the files once imported."]], [120])
    de.add_sheet(book, "Invoices", ["Date", "Invoice", "Client", "Case", "Description", "Fees", "Disbursements", "Tax", "Total", "Still unpaid"],
                 [[i["date"].isoformat(), i["number"], i["client"], i["case"], i["description"], f(i["fees"]), f(i["disbursements"]), f(i["tax"]), f(i["total"]), f(i["owing"])] for i in invoices]
                 or [["", "", "No invoices in this period", "", "", "", "", "", "", ""]], [12, 14, 24, 10, 40, 12, 14, 10, 12, 12])
    de.add_sheet(book, "Payments on invoices", ["Date", "Invoice", "Client", "Case", "Amount", "How"],
                 [[p["date"].isoformat(), p["invoice"], p["client"], p["case"], f(p["amount"]), p["how"]] for p in payments] or [["", "", "No payments in this period", "", "", ""]],
                 [12, 14, 24, 10, 12, 34])
    de.add_sheet(book, "Client account", ["Date", "Client", "Case", "What", "In", "Out"],
                 [[t["date"].isoformat(), t["client"], t["case"], t["what"], f(t["in"]), f(t["out"])] for t in trust] or [["", "", "", "No client account movements", "", ""]],
                 [12, 24, 10, 40, 12, 12])
    book.save(path)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    terms = int(s.get("terms_days", 0))
    xero, qbo = EXPORTS / f"{stamp}-xero-invoices.csv", EXPORTS / f"{stamp}-quickbooks-invoices.csv"
    with xero.open("w", encoding="utf-8-sig", newline="") as fx, qbo.open("w", encoding="utf-8-sig", newline="") as fq:
        wx, wq = csv.writer(fx), csv.writer(fq)
        wx.writerow(XERO)
        wq.writerow(QBO)
        for i in invoices:
            due = (i["date"] + datetime.timedelta(days=terms)).strftime("%d/%m/%Y")
            for desc, amt, acct, tax_amt in lines(i, s):
                wx.writerow([i["client"], i["email"], i["number"], i["case"], i["date"].strftime("%d/%m/%Y"), due, "", desc, 1, f"{amt:.2f}", "", acct,
                             s.get("tax_type", "") if tax_amt else "Tax Exempt", f"{tax_amt:.2f}" if tax_amt else "", "CAD"])
                wq.writerow([i["number"], i["client"], i["date"].strftime("%m/%d/%Y"), (i["date"] + datetime.timedelta(days=terms)).strftime("%m/%d/%Y"), i["case"],
                             "Professional fees" if desc.startswith("Professional") else desc, desc, 1, f"{amt:.2f}", f"{amt:.2f}", f"{tax_amt:.2f}"])
    print(f"{len(invoices)} invoice(s), {len(payments)} payment(s), {len(trust)} client account movement(s), {period}")
    print(f"Workbook: {path}\nImport files: {xero}\n              {qbo}")
    if not s.get("fees_account") or not s.get("tax_type"):
        print("Set your account codes and tax type once (accounting.py setup ...), or fill them in on the import screen.")
    print("Delete the import files once imported: they hold client names.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Accounting export")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("setup"); x.add_argument("--fees-account"); x.add_argument("--disbursements-account"); x.add_argument("--tax-type"); x.add_argument("--terms-days", type=int); x.set_defaults(fn=cmd_setup)
    x = s.add_parser("export"); x.add_argument("--from", dest="start"); x.add_argument("--to", dest="end"); x.add_argument("--out"); x.set_defaults(fn=cmd_export)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
