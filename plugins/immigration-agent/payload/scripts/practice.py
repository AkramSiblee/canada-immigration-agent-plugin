#!/usr/bin/env python3
"""Your own licence: CICC annual fee, professional liability insurance and CPD hours, with reminders before each deadline.

Usage:
  python3 scripts/practice.py setup [--class RCIC|RCIC-IRB|RISIA] [--licensed-on YYYY-MM-DD] [--fees single|instalments]
  python3 scripts/practice.py cpd-add --date D --hours 1.5 --title "..." [--provider TEXT] [--area TEXT] [--professionalism] [--proof FILE]
  python3 scripts/practice.py leave --term 2026 --months 2          months of leave in a CPD term (1 hour less per month)
  python3 scripts/practice.py paid annual-fee|instalment-1|instalment-2|instalment-3|instalment-4|insurance [--date D] [--term 2026]
  python3 scripts/practice.py status [--term 2026]

Rules (knowledge/10-consultant-practice/licensing-cpd-insurance.md, CICC regulations read 2026-11-07):
  - CPD (CPD Regulation for RCICs 2021-003 s.4): 16 hours per term from July 1 to June 30, at least 1 on professionalism and/or
    the Code, done by 11:59 p.m. on June 30. New licensees owe 1 hour per month left in the term (licensed April to June: none
    that term). Each month of leave lowers it by 1 hour. Suspended and conditional licensees still owe it.
  - Annual fee (Fees Regulation 2021-001): due July 1, or in 4 instalments on July 1, October 1, January 1 and April 1. Late fee
    after 30 days. Check the College's invoice for the amount.
  - Professional liability insurance (PLI Regulation 2021-001): the College group plan, term July 1 to July 1.
  Rules can change: the knowledge file says when they were last checked. Your College account is the record that counts.

Guarantees:
  - Kept in cases/practice/ (in every backup, never touched by agent updates). cpd.csv and payments.csv are add-only.
  - CPD proof files are copied into cases/practice/cpd-proof/ (CPD audits ask for them; keep them at least 6 years).
"""
import argparse
import csv
import datetime
import json
import pathlib
import shutil
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402

DIR = cs.ROOT / "practice"
SETTINGS = DIR / "settings.json"
CPD = DIR / "cpd.csv"
PAY = DIR / "payments.csv"
PROOF = DIR / "cpd-proof"
CPD_FIELDS = ["date", "hours", "title", "provider", "area", "professionalism", "proof", "recorded"]
PAY_FIELDS = ["term", "what", "date", "recorded"]
HOURS, PRO_HOURS = Decimal("16"), Decimal("1")
INSTALMENTS = [(7, 1), (10, 1), (1, 1), (4, 1)]
KB = "knowledge/10-consultant-practice/licensing-cpd-insurance.md"


def die(msg):
    sys.exit("NOT RECORDED: " + msg)


def settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append(path, fields, row):
    DIR.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fields)
        if new:
            w.writeheader()
        w.writerow(row)


def term_of(day):
    """The CPD and fee term a date falls in, named by the year it starts (July 1)."""
    return day.year if day.month >= 7 else day.year - 1


def term_dates(term):
    return datetime.date(term, 7, 1), datetime.date(term + 1, 6, 30)


def required(term, s=None):
    """(hours owed, professionalism hours owed, how it was worked out)."""
    s = settings() if s is None else s
    start, end = term_dates(term)
    owed, why = HOURS, "16 hours"
    lic = s.get("licensed_on")
    if lic:
        lic = datetime.date.fromisoformat(lic)
        if start < lic <= end:
            if lic.month in (4, 5, 6):
                return Decimal("0"), Decimal("0"), f"licensed {lic}: none owed this term"
            months = (end.year - lic.year) * 12 + end.month - lic.month  # full months left after the licensing month
            owed, why = Decimal(min(16, months)), f"licensed {lic}: 1 hour per remaining month = {min(16, months)}"
    leave = Decimal(str(s.get("leave", {}).get(str(term), 0)))
    if leave:
        owed, why = max(Decimal("0"), owed - leave), why + f", less {leave} for months of leave"
    return owed, (PRO_HOURS if owed else Decimal("0")), why


def done(term):
    start, end = term_dates(term)
    total, pro = Decimal("0"), Decimal("0")
    for r in read(CPD):
        try:
            day, h = datetime.date.fromisoformat(r["date"]), Decimal(r["hours"])
        except (ValueError, InvalidOperation):
            continue
        if start <= day <= end:
            total += h
            if r["professionalism"] == "yes":
                pro += h
    return total, pro


def paid(term, what):
    return any(r["term"] == str(term) and r["what"] == what for r in read(PAY))


def cmd_setup(a):
    s = settings()
    if a.licence_class:
        s["class"] = a.licence_class
    if a.licensed_on:
        s["licensed_on"] = cs.parse_date(a.licensed_on, "--licensed-on").isoformat()
    if a.fees:
        s["fees"] = a.fees
    DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, indent=1), encoding="utf-8")
    print("Licence details: " + ", ".join(f"{k} {v}" for k, v in s.items() if k != "leave"))


def cmd_cpd_add(a):
    day = cs.parse_date(a.date, "--date")
    if day > datetime.date.today():
        die("record CPD once it is done")
    try:
        h = Decimal(a.hours)
    except InvalidOperation:
        die("hours must be a number such as 1.5")
    if not Decimal("0") < h <= Decimal("40"):
        die("hours must be more than 0 and at most 40")
    if len(a.title.split()) < 2:
        die("give the activity's title")
    proof = ""
    if a.proof:
        src = pathlib.Path(a.proof)
        if not src.is_file():
            die(f"no such file: {src}")
        PROOF.mkdir(parents=True, exist_ok=True)
        dest = PROOF / f"{day.isoformat()}-{src.name}"
        n = 1
        while dest.exists():
            n += 1
            dest = PROOF / f"{day.isoformat()}-v{n}-{src.name}"
        shutil.copy2(src, dest)
        proof = dest.name
    append(CPD, CPD_FIELDS, {"date": day.isoformat(), "hours": str(h), "title": a.title.strip(), "provider": a.provider or "", "area": a.area or "",
                             "professionalism": "yes" if a.professionalism else "no", "proof": proof, "recorded": datetime.datetime.now().isoformat(timespec="seconds")})
    term = term_of(day)
    total, pro = done(term)
    owed, pro_owed, _ = required(term)
    print(f"Recorded {h} h ({a.title.strip()}). Term {term}-{term + 1 - 2000:02d}: {total} of {owed} hours, {pro} of {pro_owed} on professionalism or the Code.")
    if not proof:
        print("Keep the certificate or proof: CPD audits ask for it (--proof FILE copies it here).")


def cmd_leave(a):
    s = settings()
    if not 0 <= a.months <= 12:
        die("months must be 0 to 12")
    s.setdefault("leave", {})[str(a.term)] = a.months
    DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, indent=1), encoding="utf-8")
    print(f"Term {a.term}: {a.months} month(s) of leave recorded.")


def cmd_paid(a):
    day = cs.parse_date(a.date, "--date") if a.date else datetime.date.today()
    term = a.term if a.term is not None else term_of(day)
    append(PAY, PAY_FIELDS, {"term": str(term), "what": a.what, "date": day.isoformat(), "recorded": datetime.datetime.now().isoformat(timespec="seconds")})
    print(f"Recorded: {a.what} for term {term}, paid {day}.")


def due_items(today):
    """Fee and insurance dates coming up in the current and next term: [(day, what, key, term)]."""
    s = settings()
    out = []
    for term in (term_of(today), term_of(today) + 1):
        if s.get("fees") == "instalments":
            for i, (m, d) in enumerate(INSTALMENTS, 1):
                out.append((datetime.date(term + (m < 7), m, d), f"CICC annual fee, instalment {i}", f"instalment-{i}", term))
        else:
            out.append((datetime.date(term, 7, 1), "CICC annual fee", "annual-fee", term))
        out.append((datetime.date(term, 7, 1), "Professional liability insurance (College group plan) for the new term", "insurance", term))
    return out


def issues(today):
    """Firm-wide alerts: (rank, kind, tier, text, step, day). Only once the licence details are set up."""
    s = settings()
    if not s:
        return []
    out = []
    term = term_of(today)
    start, end = term_dates(term)
    owed, pro_owed, _ = required(term, s)
    total, pro = done(term)
    short, pro_short = max(Decimal("0"), owed - total), max(Decimal("0"), pro_owed - pro)
    if short or pro_short:
        left = (end - today).days
        rank = 1 if left <= 30 else 2 if left <= 61 else 3 if left <= 120 else None
        if rank:
            what = f"{short} CPD hour(s) still to do" + (f", including {pro_short} on professionalism or the Code" if pro_short else "")
            out.append((rank, "CPD", f"{left} days", f"{what} by {end} ({total} of {owed} done)", "Book CPD and record it: practice.py cpd-add", end))
    prev = term - 1
    p_owed, p_pro_owed, _ = required(prev, s)
    p_total, p_pro = done(prev)
    if (today - term_dates(prev)[1]).days <= 90 and (p_total < p_owed or p_pro < p_pro_owed) and (read(CPD) or s.get("licensed_on")):
        out.append((1, "CPD", "term ended", f"CPD term {prev}-{prev + 1 - 2000:02d} ended short: {p_total} of {p_owed} hours recorded",
                    "Check your College account; record any missing hours. Non-completion can bring fines (CPD Regulation s.15)", term_dates(prev)[1]))
    for day, what, key, t in due_items(today):
        if paid(t, key):
            continue
        left = (day - today).days
        if -30 <= left <= 30:
            rank = 1 if left <= 7 else 2
            out.append((rank, "Licence", "fee" if key != "insurance" else "insurance", f"{what} {'was due' if left < 0 else 'due'} {day}",
                        f"Pay through your College account, then: practice.py paid {key} --term {t}" + (". A late fee applies after 30 days" if key != "insurance" else ""), day))
    return out


def cmd_status(a):
    s = settings()
    today = datetime.date.today()
    term = a.term if a.term is not None else term_of(today)
    start, end = term_dates(term)
    owed, pro_owed, why = required(term, s)
    total, pro = done(term)
    print(f"Licence: {s.get('class', 'class not set')}" + (f", licensed {s['licensed_on']}" if s.get("licensed_on") else "") + f", fees {s.get('fees', 'not set')}")
    print(f"CPD term {start} to {end}: {total} of {owed} hours ({why}); {pro} of {pro_owed} on professionalism or the Code")
    for r in read(CPD):
        if start.isoformat() <= r["date"] <= end.isoformat():
            print(f"  {r['date']}  {r['hours']:>5} h  {r['title'][:50]}" + (" [professionalism]" if r["professionalism"] == "yes" else "") + ("" if r["proof"] else "  (no proof filed)"))
    for day, what, key, t in due_items(today):
        if 0 <= (day - today).days <= 400 or paid(t, key):
            print(f"  {day}  {what}: {'paid' if paid(t, key) else 'not recorded as paid'}")
    print(f"Rules from {KB}. Your College account is the record that counts.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Licence, fees, insurance and CPD")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("setup"); x.add_argument("--class", dest="licence_class", choices=["RCIC", "RCIC-IRB", "RISIA"]); x.add_argument("--licensed-on"); x.add_argument("--fees", choices=["single", "instalments"]); x.set_defaults(fn=cmd_setup)
    x = s.add_parser("cpd-add"); x.add_argument("--date", required=True); x.add_argument("--hours", required=True); x.add_argument("--title", required=True); x.add_argument("--provider")
    x.add_argument("--area"); x.add_argument("--professionalism", action="store_true"); x.add_argument("--proof"); x.set_defaults(fn=cmd_cpd_add)
    x = s.add_parser("leave"); x.add_argument("--term", type=int, required=True); x.add_argument("--months", type=int, required=True); x.set_defaults(fn=cmd_leave)
    x = s.add_parser("paid"); x.add_argument("what", choices=["annual-fee", "instalment-1", "instalment-2", "instalment-3", "instalment-4", "insurance"]); x.add_argument("--date"); x.add_argument("--term", type=int); x.set_defaults(fn=cmd_paid)
    x = s.add_parser("status"); x.add_argument("--term", type=int); x.set_defaults(fn=cmd_status)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
