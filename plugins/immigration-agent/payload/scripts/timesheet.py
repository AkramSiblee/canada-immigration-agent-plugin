#!/usr/bin/env python3
"""Time per file: record hours on each case and see what each file, and each kind of file, really earns per hour.

Usage:
  python3 scripts/timesheet.py add CASE HOURS "what was done" [--date YYYY-MM-DD] [--who NAME]
  python3 scripts/timesheet.py show CASE
  python3 scripts/timesheet.py report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--target 150] [--closed] [--out DIR]
  python3 scripts/timesheet.py target 150          your target hourly rate, used to flag files that earn less

Guarantees:
  - Hours go to 07-billing/time.csv in the case (add-only: a correction is a new line with negative hours).
  - Fees come from the billing ledger (billing.py): professional fees invoiced, without disbursements or tax. A file
    with no invoice yet uses the fee estimate in the service agreement, marked as an estimate.
  - Time records are for your own management. An invoice for hourly work still needs the service details the Code
    requires (billing.py invoice).
"""
import argparse
import csv
import datetime
import json
import pathlib
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import billing as bl  # noqa: E402
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

FIELDS = ["id", "date", "hours", "who", "what", "recorded"]
SETTINGS = cs.ROOT / ".timesheet-settings.json"


def die(msg):
    sys.exit("NOT RECORDED: " + msg)


def path_of(folder):
    return folder / "07-billing" / "time.csv"


def load(folder):
    p = path_of(folder)
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def hours(rows, start=None, end=None):
    total = Decimal("0")
    for r in rows:
        try:
            day = datetime.date.fromisoformat(r["date"])
            h = Decimal(r["hours"])
        except (ValueError, InvalidOperation):
            continue
        if (not start or day >= start) and (not end or day <= end):
            total += h
    return total


def target():
    try:
        return Decimal(str(json.loads(SETTINGS.read_text(encoding="utf-8"))["target"]))
    except (OSError, ValueError, KeyError, InvalidOperation):
        return None


def fees_of(folder):
    """(fees, 'invoiced' | 'estimate' | '')."""
    try:
        s = bl.summary(bl.load(folder))
    except Exception:
        return None, "ledger unreadable"
    invoiced = sum((i["fees"] for i in s["invoices"].values()), bl.ZERO)
    if invoiced:
        return invoiced, "invoiced"
    if s["estimate"] and s["estimate"].get("fees"):
        return bl.stored(s["estimate"]["fees"]), "estimate"
    return None, ""


def file_row(folder, start=None, end=None):
    info = cs.read_case(folder)
    h = hours(load(folder), start, end)
    fees, basis = fees_of(folder)
    rate = (fees / h).quantize(Decimal("0.01")) if fees is not None and h > 0 else None
    return {"folder": folder.name, "id": info.get("case_id", folder.name[:8]), "client": info.get("client", ""), "program": info.get("program", ""),
            "state": "closed" if folder.parent == cs.CLOSED else "open", "hours": h, "fees": fees, "basis": basis, "rate": rate}


def cmd_add(a):
    folder = de.active_case(a.case)
    try:
        h = Decimal(a.hours)
    except InvalidOperation:
        die("hours must be a number such as 1.5 (use a negative number to correct an earlier line)")
    if h == 0 or abs(h) > 24:
        die("hours must be between -24 and 24, and not 0")
    if len((a.what or "").split()) < 2:
        die("say what was done (a few words)")
    day = cs.parse_date(a.date, "--date") if a.date else datetime.date.today()
    if day > datetime.date.today():
        die("the date can't be in the future")
    rows = load(folder)
    p = path_of(folder)
    p.parent.mkdir(exist_ok=True)
    new = not p.exists()
    with p.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        w.writerow({"id": str(len(rows) + 1), "date": day.isoformat(), "hours": str(h), "who": a.who or "", "what": a.what.strip(),
                    "recorded": datetime.datetime.now().isoformat(timespec="seconds")})
    print(f"Recorded {h} h on {folder.name}. Total on this file: {hours(load(folder))} h")


def cmd_show(a):
    folder = cs.find(a.case, include_closed=True)
    rows = load(folder)
    for r in rows:
        print(f"{r['date']}  {r['hours']:>6} h  {r['who'][:14]:14}  {r['what']}")
    r = file_row(folder)
    print(f"Total: {r['hours']} h")
    if r["fees"] is not None:
        print(f"Fees {r['basis']}: ${r['fees']:,}" + (f" = ${r['rate']:,} per hour" if r["rate"] else ""))
        t = target()
        if r["rate"] and t and r["rate"] < t:
            print(f"Below your target of ${t:,} per hour.")
    else:
        print("No fees recorded in the billing ledger yet (billing.py estimate or invoice).")


def cmd_target(a):
    try:
        t = Decimal(a.rate)
    except InvalidOperation:
        die("give a number, such as 150")
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps({"target": str(t)}), encoding="utf-8")
    print(f"Target hourly rate: ${t:,}")


def cmd_report(a):
    import openpyxl
    start = cs.parse_date(a.start, "--from") if a.start else None
    end = cs.parse_date(a.end, "--to") if a.end else None
    t = Decimal(str(a.target)) if a.target else target()
    pool = cs.folders(cs.ACTIVE) + (cs.folders(cs.CLOSED) if a.closed else [])
    rows = [r for r in (file_row(f, start, end) for f in pool) if r["hours"] or r["fees"] is not None]
    by_program = {}
    for r in rows:
        g = by_program.setdefault(r["program"] or "(no program)", {"files": 0, "hours": Decimal("0"), "fees": Decimal("0"), "rated_hours": Decimal("0")})
        g["files"] += 1
        g["hours"] += r["hours"]
        if r["fees"] is not None and r["hours"] > 0:
            g["fees"] += r["fees"]
            g["rated_hours"] += r["hours"]
    out = pathlib.Path(a.out) if a.out else de.REPO / "Output" / "general"
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    stem, n = f"{datetime.date.today().isoformat()}-time-and-fees", 1
    path = out / f"{stem}.xlsx"
    while path.exists():
        n += 1
        path = out / f"{stem}-v{n}.xlsx"
    flag = lambda rate: "below target" if rate is not None and t and rate < t else ""  # noqa: E731
    book = openpyxl.Workbook()
    book.remove(book.active)
    de.add_sheet(book, "Read me first", ["About this report"], [
        [f"Hours recorded{' from ' + str(start) if start else ''}{' to ' + str(end) if end else ''}, against professional fees (no disbursements or tax)."],
        ["Fees are what was invoiced. A file with no invoice uses the fee estimate in its service agreement."],
        ["Hours limited by --from/--to are compared with all fees on the file, so a partial period can look better or worse than it is."],
        [f"Target hourly rate: ${t:,}" if t else "No target rate set (timesheet.py target 150)."]], [120])
    de.add_sheet(book, "By file", ["Case", "Client", "Program", "Open or closed", "Hours", "Fees", "Fees from", "Per hour", "Flag"],
                 [[r["id"], r["client"], r["program"], r["state"], float(r["hours"]), float(r["fees"]) if r["fees"] is not None else "", r["basis"],
                   float(r["rate"]) if r["rate"] is not None else "", flag(r["rate"])] for r in sorted(rows, key=lambda r: (r["rate"] is None, r["rate"] or 0))]
                 or [["", "", "No time or fees recorded", "", "", "", "", "", ""]], [10, 24, 22, 12, 9, 12, 12, 10, 14])
    prog = []
    for name, g in sorted(by_program.items()):
        rate = (g["fees"] / g["rated_hours"]).quantize(Decimal("0.01")) if g["rated_hours"] else None
        prog.append([name, g["files"], float(g["hours"]), float(g["fees"]), float(rate) if rate is not None else "", flag(rate)])
    de.add_sheet(book, "By program", ["Program", "Files", "Hours", "Fees (files with hours)", "Per hour", "Flag"], prog or [["", "", "", "", "", ""]], [26, 8, 10, 22, 10, 14])
    book.save(path)
    print(f"{len(rows)} file(s) saved to {path}")
    low = [r for r in rows if flag(r["rate"])]
    if low:
        print(f"{len(low)} file(s) below the target rate.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Time per file")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("add"); x.add_argument("case"); x.add_argument("hours"); x.add_argument("what"); x.add_argument("--date"); x.add_argument("--who"); x.set_defaults(fn=cmd_add)
    x = s.add_parser("show"); x.add_argument("case"); x.set_defaults(fn=cmd_show)
    x = s.add_parser("report"); x.add_argument("--from", dest="start"); x.add_argument("--to", dest="end"); x.add_argument("--target", type=float); x.add_argument("--closed", action="store_true"); x.add_argument("--out"); x.set_defaults(fn=cmd_report)
    x = s.add_parser("target"); x.add_argument("rate"); x.set_defaults(fn=cmd_target)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
