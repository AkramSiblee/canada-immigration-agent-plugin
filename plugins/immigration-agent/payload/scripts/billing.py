#!/usr/bin/env python3
"""Billing and client (trust) account records for each case.

Usage:
  python3 scripts/billing.py setup --name "Full Name" --rcic R000000 --model 1 [--business X] [--address X] [--tax-number X]
  python3 scripts/billing.py estimate CASE --fees 3000 --disbursements 1085
  python3 scripts/billing.py receive CASE AMOUNT --method e-transfer --purpose fees [--invoice NO] [--date D] [--deposited D]
  python3 scripts/billing.py deposit CASE ENTRY --date D
  python3 scripts/billing.py invoice CASE --desc "Services" --services-to D --fees 1000 [--disbursements 85] [--tax 130] [--written-agreement REF]
  python3 scripts/billing.py withdraw CASE AMOUNT --reason fees --method eft --invoice NO
  python3 scripts/billing.py reverse CASE ENTRY --reason "Why"
  python3 scripts/billing.py show CASE
  python3 scripts/billing.py statement CASE
  python3 scripts/billing.py reconcile --month 2026-10 --bank 5000 [--outstanding 0] [--in-transit 0] [--firm-funds 0]

Guarantees:
  - The ledger is only ever added to. A mistake is corrected with a reversal, so history stays visible.
  - It records what happened. It never moves money and never contacts a bank.
  - Rules are from the Code of Professional Conduct (SOR/2022-128) ss.31-33, 36
    and the CICC Client Account Regulation 2021-001 (cited as CAR).
"""
import argparse
import csv
import datetime
import json
import os
import pathlib
import re
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

FIELDS = ["id", "date", "kind", "amount", "account", "invoice", "method", "purpose", "description", "reference", "deposited", "fees", "disbursements", "tax", "services_to", "reverses", "recorded"]
SETTINGS = cs.ROOT / ".billing-settings.json"
RECON_DIR = cs.ROOT / "reconciliations"
RECON_INDEX = RECON_DIR / "index.csv"
RECON_FIELDS = ["month", "bank", "outstanding", "in_transit", "firm_funds", "adjusted_bank", "client_total", "difference", "balanced", "done_on", "file"]
ZERO = Decimal("0.00")
ELECTRONIC = {"e-transfer", "wire", "eft"}  # CAR 4.1(b): deemed deposited when the institution gives notice
RECEIVE_METHODS = ["e-transfer", "wire", "eft", "cheque", "cash", "card", "bank-draft"]
PURPOSES = ["fees", "government-fees", "disbursements"]
NEEDS_INVOICE = {"fees", "disbursement-invoiced"}
NEEDS_WRITING = {"disbursement-permission", "transfer"}
REASONS = ["fees", "disbursement-invoiced", "disbursement-permission", "transfer", "wrong-deposit", "refund"]
DEPOSIT_DAYS, WITHDRAW_DAYS, RECON_DAYS = 14, 30, 90


def today():
    return datetime.date.today()


def die(msg):
    sys.exit(f"NOT RECORDED: {msg}")


def money(text, label="amount", allow_zero=False):
    try:
        v = Decimal(str(text).replace(",", "").replace("$", "").strip()).quantize(Decimal("0.01"))
    except InvalidOperation:
        die(f"{label} is not a valid amount: {text}")
    if not v.is_finite() or v < 0 or (v == 0 and not allow_zero):
        die(f"{label} must be more than zero")
    return v


def stored(text):
    """Read an amount from the ledger. A damaged value raises, and the alert run reports that file."""
    try:
        return Decimal(text or "0").quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError("damaged amount in ledger") from None


def day_of(text):
    return datetime.date.fromisoformat(text) if text else None


def when(text, label="date", default=None):
    if not text:
        return default or today()
    d = cs.parse_date(text, label)
    if d > today():
        die(f"{label} can't be in the future")
    return d


def ledger_path(folder):
    return folder / "07-billing" / "ledger.csv"


def load(folder):
    path = ledger_path(folder)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        stored(r["amount"])
        day_of(r["date"])
    return rows


def append(folder, **row):
    rows = load(folder)
    row = {**{k: "" for k in FIELDS}, **row, "id": str(max((int(r["id"]) for r in rows), default=0) + 1), "recorded": datetime.datetime.now().isoformat(timespec="seconds")}
    path = ledger_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if fresh:
            w.writeheader()
        w.writerow(row)
    return row


def live(rows):
    """Entries still in effect, with each receipt's deposit date filled in from its deposit entry."""
    voided = {r["reverses"] for r in rows if r["kind"] == "reversal"}
    active = [dict(r) for r in rows if r["id"] not in voided and r["kind"] != "reversal"]
    deposits = {r["reference"]: r["date"] for r in active if r["kind"] == "deposit"}
    for r in active:
        if r["kind"] == "receipt" and not r["deposited"]:
            r["deposited"] = deposits.get(r["id"], "")
    return active


def summary(rows, asof=None):
    asof = asof or datetime.date.max
    held, received, undeposited, invoices, est = ZERO, ZERO, [], {}, None
    active = live(rows)
    for r in active:
        if r["kind"] == "estimate":
            est = r
        elif r["kind"] == "invoice" and day_of(r["date"]) <= asof:
            invoices[r["invoice"]] = {"date": day_of(r["date"]), "total": stored(r["amount"]), "fees": stored(r["fees"]), "disbursements": stored(r["disbursements"]), "applied": ZERO}
    for r in active:
        amount = stored(r["amount"])
        if r["kind"] == "receipt" and day_of(r["date"]) <= asof:
            received += amount
            if r["account"] == "trust":
                if r["deposited"] and day_of(r["deposited"]) <= asof:
                    held += amount
                else:
                    undeposited.append(r)
            elif r["invoice"] in invoices:
                invoices[r["invoice"]]["applied"] += amount
        elif r["kind"] == "withdrawal" and day_of(r["date"]) <= asof:
            held -= amount
            if r["invoice"] in invoices:
                invoices[r["invoice"]]["applied"] += amount
    return {"held": held, "received": received, "undeposited": undeposited, "invoices": invoices, "estimate": est,
            "invoiced": sum((i["total"] for i in invoices.values()), ZERO), "owing": sum((i["total"] - i["applied"] for i in invoices.values()), ZERO)}


FIRM_FIELDS = ("name", "rcic", "business", "address", "phone", "email")


def firm_profile():
    import firm
    return firm.load_profile()


def settings():
    """Billing settings, with your name, licence and address taken from the firm profile when it exists."""
    try:
        s = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        die("run 'billing.py setup --model 1|2|none' first")
    profile = firm_profile()
    s.update({k: profile[k] for k in FIRM_FIELDS if profile.get(k)})
    if not s.get("name") or not s.get("rcic"):
        die("your name and RCIC number are missing. Run 'firm.py setup' (they're entered once there)")
    return s


def next_pdf(folder, stem):
    n = 1
    while True:
        p = folder / f"{stem}{'' if n == 1 else f'-v{n}'}.pdf"
        if not p.exists():
            return p
        n += 1


def write_pdf(path, title, profile, heads, table, notes):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    st = getSampleStyleSheet()
    para = lambda t, s="BodyText": Paragraph(escape(str(t)), st[s])
    who = profile.get("business") or profile["name"]
    flow = [para(who, "Heading2"), para(f"{profile['name']}, Regulated Canadian Immigration Consultant, {profile['rcic']}")]
    for extra in (profile.get("address"), f"GST/HST no. {profile['tax_number']}" if profile.get("tax_number") else None):
        if extra:
            flow.append(para(extra))
    flow += [Spacer(1, 10), para(title, "Title")]
    flow += [para(f"{k}: {v}") for k, v in heads]
    flow.append(Spacer(1, 10))
    grid = Table([[para(c) for c in row] for row in table], repeatRows=1, colWidths=[468 / len(table[0])] * len(table[0]))
    grid.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE3EE")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow += [grid, Spacer(1, 10)] + [para(n) for n in notes]
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp.pdf")
    os.close(fd)
    SimpleDocTemplate(tmp, pagesize=letter, title=title, leftMargin=72, rightMargin=72, topMargin=54, bottomMargin=54).build(flow)
    de.replace_with_retry(tmp, path)
    return path


def d(v):
    return f"${v:,.2f}"


def case_bits(ref, closed=False):
    folder = cs.find(ref, include_closed=closed)
    info = cs.read_case(folder)
    (folder / "07-billing").mkdir(exist_ok=True)
    return folder, info, folder / "07-billing"


def cmd_setup(a):
    old = {}
    if SETTINGS.exists():
        old = json.loads(SETTINGS.read_text(encoding="utf-8"))
    if old.get("model") and old["model"] != a.model and not a.change_model:
        die("CAR 4.2(c) requires one model for the entire audit year. Add --change-model only at a new audit year")
    profile = firm_profile()
    for key in ("name", "rcic", "business", "address"):
        given = getattr(a, key)
        if given and profile.get(key) and given.strip() != profile[key]:
            die(f"your firm profile has {key} '{profile[key]}'. Change it there with firm.py setup, so every document matches")
    if not profile.get("name") and not (a.name and a.rcic):
        die("give --name and --rcic, or better, run 'firm.py setup' first so they're entered once")
    data = {"model": a.model, "tax_number": a.tax_number if a.tax_number is not None else old.get("tax_number", "")}
    if not profile.get("name"):  # no firm profile yet: keep the details here until there is one
        data.update({k: (getattr(a, k) or old.get(k, "")) for k in ("name", "rcic", "business", "address")})
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(data), encoding="utf-8")
    print(f"Saved. Client account model: {a.model}" + (". Your name, licence and address come from your firm profile" if profile.get("name") else ""))


def cmd_estimate(a):
    folder, _, _ = case_bits(a.case)
    fees, disb = money(a.fees, "fees"), money(a.disbursements or 0, "disbursements", True)
    append(folder, date=when(a.date).isoformat(), kind="estimate", amount=str(fees + disb), fees=str(fees), disbursements=str(disb), description="Estimate in the service agreement")
    print(f"Estimate recorded: fees {d(fees)}, disbursements {d(disb)}")


def cmd_receive(a):
    profile, (folder, info, out) = settings(), case_bits(a.case)
    amount, day, rows = money(a.amount), when(a.date), load(folder)
    state = summary(rows)
    if a.invoice and a.invoice not in state["invoices"]:
        die(f"no invoice {a.invoice} on this file")
    if not a.invoice and not a.purpose:
        die("say what this advance is for (--purpose). Money can only be used for that purpose (s.32(e))")
    if not a.invoice and profile["model"] == "none":
        die("you've declared you hold no client money, so an advance can't be accepted (CAR 3.2, 3.4)")
    trust = profile["model"] == "1" or (profile["model"] == "2" and not a.invoice)
    account = "trust" if trust else "operating"
    deposited = ""
    if not trust or a.method in ELECTRONIC:
        deposited = day.isoformat()
    elif a.deposited:
        dep = when(a.deposited, "deposit date")
        if dep < day:
            die("deposit date is before the money was received")
        deposited = dep.isoformat()
    row = append(folder, date=day.isoformat(), kind="receipt", amount=str(amount), account=account, invoice=a.invoice or "", method=a.method, purpose=a.purpose or "", description=a.desc or "", deposited=deposited)
    what = f"Payment toward invoice {a.invoice}" if a.invoice else f"Advance held in trust for: {a.purpose}"
    pdf = write_pdf(next_pdf(out, f"{day.isoformat()}-receipt-{row['id']}"), "Receipt", profile,
                    [("Receipt no.", f"{info['case_id']}-R{row['id']}"), ("Date received", day.isoformat()), ("Received from", info.get("client", "")), ("File", info["case_id"])],
                    [["Description", "Method", "Amount"], [what, a.method, d(amount)]], [])
    print(f"Receipt recorded as entry {row['id']}. Held in: {'client account' if trust else 'business account'}")
    if trust and not deposited:
        print(f"Deposit it by {day + datetime.timedelta(days=DEPOSIT_DAYS)} (CAR 4.1(a)), then run: billing.py deposit {a.case} {row['id']} --date D")
    if deposited and (day_of(deposited) - day).days > DEPOSIT_DAYS:
        print("WARNING: deposited more than 14 days after receipt (CAR 4.1(a))")
    print("Receipt:", pdf.name)


def cmd_deposit(a):
    folder, _, _ = case_bits(a.case)
    rows = load(folder)
    row = next((r for r in live(rows) if r["id"] == a.entry and r["kind"] == "receipt" and r["account"] == "trust"), None)
    if not row:
        die(f"entry {a.entry} isn't a client account receipt on this file")
    if row["deposited"]:
        die("this receipt already has a deposit date")
    dep = when(a.date, "deposit date")
    if dep < day_of(row["date"]):
        die("deposit date is before the money was received")
    append(folder, date=dep.isoformat(), kind="deposit", amount="0", account="trust", reference=a.entry, description=f"Receipt {a.entry} deposited")
    print(f"Deposit recorded for entry {a.entry}")
    if (dep - day_of(row["date"])).days > DEPOSIT_DAYS:
        print("WARNING: deposited more than 14 days after receipt (CAR 4.1(a))")


def cmd_invoice(a):
    profile, (folder, info, out) = settings(), case_bits(a.case)
    desc = (a.desc or "").strip()
    if len(desc.split()) < 3:
        die("an invoice needs a full description of the services and disbursements (s.33(2))")
    day, through = when(a.date), when(a.services_to, "--services-to")
    if through > day:
        die("you can only invoice after the services or disbursements are provided (s.33(1))")
    fees, disb, tax = money(a.fees or 0, "fees", True), money(a.disbursements or 0, "disbursements", True), money(a.tax or 0, "tax", True)
    if fees + disb == 0:
        die("nothing to invoice")
    rows = load(folder)
    state = summary(rows)
    est = state["estimate"]
    if est and not a.written_agreement:
        billed_fees = sum((i["fees"] for i in state["invoices"].values()), ZERO) + fees
        billed_disb = sum((i["disbursements"] for i in state["invoices"].values()), ZERO) + disb
        if billed_fees > stored(est["fees"]) or billed_disb > stored(est["disbursements"]):
            die("this goes over the estimate in the service agreement. Get the client's written agreement first, then add --written-agreement REF (s.31(3))")
    number = f"{info['case_id']}-{sum(r['kind'] == 'invoice' for r in rows) + 1:02d}"
    total = fees + disb + tax
    append(folder, date=day.isoformat(), kind="invoice", amount=str(total), invoice=number, description=desc, fees=str(fees), disbursements=str(disb), tax=str(tax), services_to=through.isoformat(), reference=a.written_agreement or "")
    table = [["Item", "Amount"], ["Professional fees", d(fees)], ["Disbursements (actual cost)", d(disb)], ["Tax", d(tax)], ["Total", d(total)]]
    pdf = write_pdf(next_pdf(out, f"{day.isoformat()}-invoice-{number}"), "Invoice", profile,
                    [("Invoice no.", number), ("Date", day.isoformat()), ("Client", info.get("client", "")), ("File", info["case_id"]), ("Services provided through", through.isoformat()), ("Description", desc)], table, [])
    print(f"Invoice {number} recorded: {d(total)}")
    if not est:
        print("No estimate on this file yet. Record the service agreement's estimate with: billing.py estimate")
    if state["held"] > 0:
        print(f"Client account holds {d(state['held'])}. Withdraw any invoiced amount by {day + datetime.timedelta(days=WITHDRAW_DAYS)} (s.32(g))")
    print("Invoice:", pdf.name)


def cmd_withdraw(a):
    settings()
    folder, _, _ = case_bits(a.case)
    amount, day, rows = money(a.amount), when(a.date), load(folder)
    state = summary(rows)
    if amount > state["held"]:
        die(f"this client has {d(state['held'])} deposited in the client account. You can't withdraw more than is held for them (CAR 6.3)")
    if a.reason in NEEDS_INVOICE:
        inv = state["invoices"].get(a.invoice or "")
        if not inv:
            die("fees and invoiced disbursements can only be withdrawn against an invoice on this file (s.32(f), CAR 6.1)")
        if day < inv["date"]:
            die("the withdrawal is dated before the invoice (s.32(f))")
        if amount > inv["total"] - inv["applied"]:
            die(f"only {d(inv['total'] - inv['applied'])} is unpaid on invoice {a.invoice}")
        if (day - inv["date"]).days > WITHDRAW_DAYS:
            print("WARNING: withdrawn more than 30 days after the invoice date (s.32(g))")
    elif a.invoice:
        die("an invoice applies only to fees or invoiced disbursements")
    if a.reason in NEEDS_WRITING and not a.reference:
        die("this needs the client's written permission or direction. Add --reference naming it (CAR 6.1(a)(i), (iv))")
    row = append(folder, date=day.isoformat(), kind="withdrawal", amount=str(amount), account="trust", invoice=a.invoice or "", method=a.method, purpose=a.reason, description=a.desc or "", reference=a.reference or "")
    print(f"Withdrawal recorded as entry {row['id']}. Client account balance for this client: {d(state['held'] - amount)}")


def cmd_reverse(a):
    folder, _, _ = case_bits(a.case)
    rows = load(folder)
    row = next((r for r in live(rows) if r["id"] == a.entry), None)
    if not row:
        die(f"entry {a.entry} isn't an open entry on this file")
    test = rows + [{**{k: "" for k in FIELDS}, "kind": "reversal", "reverses": a.entry, "amount": "0", "date": today().isoformat()}]
    after = summary(test)
    if after["held"] < 0:
        die("reversing this would leave the client's balance below zero. Reverse the withdrawals first")
    if row["kind"] == "invoice" and summary(rows)["invoices"][row["invoice"]]["applied"] > 0:
        die("payments are applied to this invoice. Reverse those first")
    append(folder, date=today().isoformat(), kind="reversal", amount="0", reverses=a.entry, description=a.reason)
    print(f"Entry {a.entry} reversed. It stays visible in the ledger.")
    if row["kind"] in ("receipt", "withdrawal") and row["account"] == "trust":
        print("If this corrects an error in trust funds, it must be reported to the Registrar within 30 days of discovery (s.39(f)).")


def cmd_show(a):
    folder, _, _ = case_bits(a.case, True)
    s = summary(load(folder))
    est = s["estimate"]
    print(f"Estimate: {d(stored(est['amount'])) if est else 'not recorded'} | received: {d(s['received'])} | invoiced: {d(s['invoiced'])} | unpaid invoices: {d(s['owing'])}")
    print(f"In client account: {d(s['held'])} | received but not deposited: {len(s['undeposited'])}")


def cmd_statement(a):
    profile, (folder, info, out) = settings(), case_bits(a.case, True)
    rows = load(folder)
    s = summary(rows)
    table = [["Date", "Entry", "Details", "Amount"]]
    names = {"receipt": "Money received", "invoice": "Invoice", "withdrawal": "Paid from client account"}
    for r in live(rows):
        if r["kind"] in names:
            table.append([r["date"], names[r["kind"]], " ".join(x for x in (r["invoice"], r["purpose"], r["description"], r["method"]) if x), d(stored(r["amount"]))])
    notes = [f"Total received: {d(s['received'])}", f"Total invoiced: {d(s['invoiced'])}", f"Unpaid on invoices: {d(s['owing'])}", f"Held in the client account for you: {d(s['held'])}"]
    pdf = write_pdf(next_pdf(out, f"{today().isoformat()}-statement-of-account"), "Statement of account", profile, [("Client", info.get("client", "")), ("File", info["case_id"]), ("Date", today().isoformat())], table, notes)
    print("Statement:", pdf.name)
    if s["held"] > 0 and s["owing"] == 0:
        print(f"{d(s['held'])} is still held. On completion, excess funds are refunded within 30 days (s.36(1)(d))")


def all_folders():
    return cs.folders(cs.ACTIVE) + cs.folders(cs.CLOSED)


def month_end(month):
    y, m = map(int, month.split("-"))
    return datetime.date(y + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1)


def recon_index():
    if not RECON_INDEX.exists():
        return {}
    with RECON_INDEX.open(encoding="utf-8", newline="") as f:
        return {r["month"]: r for r in csv.DictReader(f)}  # the latest attempt for a month wins


def cmd_reconcile(a):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", a.month):
        die("use a month such as 2026-10")
    end = month_end(a.month)
    if end >= today():
        die("a month can only be reconciled after it ends")
    bank, outstanding, transit, firm = (money(x, n, True) for x, n in ((a.bank, "bank balance"), (a.outstanding or 0, "outstanding"), (a.in_transit or 0, "in transit"), (a.firm_funds or 0, "firm funds")))
    held, moves = [], []
    for folder in all_folders():
        rows = load(folder)
        if not rows:
            continue
        info = cs.read_case(folder)
        balance = summary(rows, end)["held"]
        if balance or any(r["account"] == "trust" for r in rows):
            held.append([info["case_id"], info.get("client", ""), balance])
        for r in live(rows):
            if r["account"] == "trust" and r["date"][:7] == a.month and r["kind"] in ("receipt", "withdrawal"):
                moves.append([r["date"], info["case_id"], "In" if r["kind"] == "receipt" else "Out", stored(r["amount"]), r["method"], r["deposited"], r["invoice"], r["purpose"]])
    total = sum((h[2] for h in held), ZERO)
    adjusted = bank - outstanding + transit
    diff = adjusted - total - firm
    balanced = diff == 0 and all(h[2] >= 0 for h in held)
    import openpyxl
    book = openpyxl.Workbook()
    book.remove(book.active)
    de.add_sheet(book, "Summary", ["Item", "Amount"],
                 [["Month ended", end.isoformat()], ["Bank statement balance", d(bank)], ["Less: cheques not yet cleared", d(outstanding)], ["Add: deposits not yet on the statement", d(transit)], ["Adjusted bank balance", d(adjusted)],
                  ["Total held for clients", d(total)], ["Firm money for bank charges (CAR 5.1(a))", d(firm)], ["Difference", d(diff) if diff >= 0 else f"-{d(-diff)}"], ["Result", "Balanced" if balanced else "DOES NOT BALANCE: find the cause. A trust error must be reported within 30 days of discovery (s.39(f))"],
                  ["Keep with this file", "The bank statement for the month, for at least 6 years, at your principal business address (CAR 9.1(b))"]], [50, 60])
    de.add_sheet(book, "Money held per client", ["File", "Client", "Held at month end"], [[h[0], h[1], d(h[2]) if h[2] >= 0 else f"-{d(-h[2])}"] for h in held] or [["", "No client money held", ""]], [16, 40, 20])
    de.add_sheet(book, "Movements", ["Date", "File", "In or out", "Amount", "Method", "Deposited", "Invoice", "Purpose"], [[*m[:3], d(m[3]), *m[4:]] for m in sorted(moves, key=lambda x: x[0])] or [["", "No movements this month", "", "", "", "", "", ""]], [12, 14, 9, 14, 12, 12, 16, 22])
    RECON_DIR.mkdir(parents=True, exist_ok=True)
    n, path = 1, RECON_DIR / f"{a.month}-reconciliation.xlsx"
    while path.exists():
        n += 1
        path = RECON_DIR / f"{a.month}-reconciliation-v{n}.xlsx"
    book.save(path)
    fresh = not RECON_INDEX.exists()
    with RECON_INDEX.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, RECON_FIELDS)
        if fresh:
            w.writeheader()
        w.writerow({"month": a.month, "bank": bank, "outstanding": outstanding, "in_transit": transit, "firm_funds": firm, "adjusted_bank": adjusted, "client_total": total, "difference": diff, "balanced": "yes" if balanced else "no", "done_on": today().isoformat(), "file": path.name})
    print(f"Month {a.month}: adjusted bank {d(adjusted)} | client total {d(total)} | difference {d(abs(diff))} | {'BALANCED' if balanced else 'DOES NOT BALANCE'}")
    print("Reconciliation:", path.name)


def settled_problem(folder):
    """Why this file's money isn't settled, for case.py close. None means it is fine."""
    s = summary(load(folder))
    if s["undeposited"]:
        return "a receipt has no deposit date in the ledger"
    if s["held"] != 0:
        return f"{d(s['held'])} is still held in the client account"
    if s["owing"] != 0:
        return f"{d(s['owing'])} is unpaid on invoices. Reverse it, or record how it was resolved"
    return None


def issues(folder, now):
    """Billing alerts for one case: (rank, kind, tier, text, step, day)."""
    out, rows = [], load(folder)
    s = summary(rows)
    for r in s["undeposited"]:
        due = day_of(r["date"]) + datetime.timedelta(days=DEPOSIT_DAYS)
        left = (due - now).days
        out.append((1 if left <= 3 else 2, "Client money", "late" if left < 0 else "deposit", f"{d(stored(r['amount']))} received {r['date']} has no deposit date (CAR 4.1(a))", "Deposit it, then record the deposit", due))
    if s["held"] < 0:
        out.append((1, "Client money", "negative", "Client's trust balance is below zero (CAR 6.3)", "Investigate today. Trust errors must be reported within 30 days of discovery (s.39(f))", None))
    for number, inv in s["invoices"].items():
        unpaid = inv["total"] - inv["applied"]
        if unpaid <= 0:
            continue
        due = inv["date"] + datetime.timedelta(days=WITHDRAW_DAYS)
        left = (due - now).days
        if s["held"] > 0 and left <= 14:
            out.append((1 if left <= 7 else 2, "Client money", "late" if left < 0 else "withdraw", f"Invoice {number}: {d(unpaid)} unpaid while the client account holds {d(s['held'])} (s.32(g))", "Withdraw the invoiced amount within 30 days of the invoice", due))
        elif s["held"] <= 0 and (now - inv["date"]).days > 60:
            out.append((3, "Billing", "unpaid", f"Invoice {number}: {d(unpaid)} unpaid for over 60 days", "Follow up with the client", None))
    if s["invoices"] and not s["estimate"]:
        out.append((3, "Billing", "no estimate", "Invoiced, but no estimate recorded", "Record the service agreement's estimate", None))
    return out


def reconcile_issue(now):
    """The oldest unreconciled month: (rank, tier, text, step, day), or None."""
    first = None
    for folder in all_folders():
        for r in live(load(folder)):
            if r["account"] == "trust" and r["kind"] in ("receipt", "withdrawal"):
                first = min(first or r["date"][:7], r["date"][:7])
    if not first:
        return None
    done = recon_index()
    bad = sorted(m for m, r in done.items() if r["balanced"] != "yes")
    if bad:
        return (1, "unbalanced", f"Reconciliation for {bad[0]} does not balance", "Find the cause and reconcile again. Trust errors must be reported within 30 days of discovery (s.39(f))", None)
    y, m = map(int, first.split("-"))
    missing = []
    while True:
        key = f"{y:04d}-{m:02d}"
        if month_end(key) >= now:
            break
        if key not in done:
            missing.append(key)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    if not missing:
        return None
    due = month_end(missing[0]) + datetime.timedelta(days=RECON_DAYS)
    left = (due - now).days
    return (1 if left <= 14 else 2, "reconcile", f"Client account not reconciled: {len(missing)} month(s), oldest {missing[0]} (CAR 9.1)", "Run billing.py reconcile with the bank statement", due)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Billing and client account records")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("setup"); x.add_argument("--name"); x.add_argument("--rcic"); x.add_argument("--model", required=True, choices=["1", "2", "none"]); x.add_argument("--business"); x.add_argument("--address"); x.add_argument("--tax-number"); x.add_argument("--change-model", action="store_true"); x.set_defaults(fn=cmd_setup)
    x = s.add_parser("estimate"); x.add_argument("case"); x.add_argument("--fees", required=True); x.add_argument("--disbursements"); x.add_argument("--date"); x.set_defaults(fn=cmd_estimate)
    x = s.add_parser("receive"); x.add_argument("case"); x.add_argument("amount"); x.add_argument("--method", required=True, choices=RECEIVE_METHODS); x.add_argument("--purpose", choices=PURPOSES); x.add_argument("--invoice"); x.add_argument("--date"); x.add_argument("--deposited"); x.add_argument("--desc"); x.set_defaults(fn=cmd_receive)
    x = s.add_parser("deposit"); x.add_argument("case"); x.add_argument("entry"); x.add_argument("--date", required=True); x.set_defaults(fn=cmd_deposit)
    x = s.add_parser("invoice"); x.add_argument("case"); x.add_argument("--desc", required=True); x.add_argument("--services-to", required=True); x.add_argument("--fees"); x.add_argument("--disbursements"); x.add_argument("--tax"); x.add_argument("--date"); x.add_argument("--written-agreement"); x.set_defaults(fn=cmd_invoice)
    x = s.add_parser("withdraw"); x.add_argument("case"); x.add_argument("amount"); x.add_argument("--reason", required=True, choices=REASONS); x.add_argument("--method", required=True, choices=["cheque", "eft"]); x.add_argument("--invoice"); x.add_argument("--reference"); x.add_argument("--date"); x.add_argument("--desc"); x.set_defaults(fn=cmd_withdraw)
    x = s.add_parser("reverse"); x.add_argument("case"); x.add_argument("entry"); x.add_argument("--reason", required=True); x.set_defaults(fn=cmd_reverse)
    x = s.add_parser("show"); x.add_argument("case"); x.set_defaults(fn=cmd_show)
    x = s.add_parser("statement"); x.add_argument("case"); x.set_defaults(fn=cmd_statement)
    x = s.add_parser("reconcile"); x.add_argument("--month", required=True); x.add_argument("--bank", required=True); x.add_argument("--outstanding"); x.add_argument("--in-transit"); x.add_argument("--firm-funds"); x.set_defaults(fn=cmd_reconcile)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
