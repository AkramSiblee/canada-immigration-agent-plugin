#!/usr/bin/env python3
"""Fee quotes: your professional fees plus IRCC's fees for the program and family, as a Word letter on your letterhead.

Usage:
  python3 scripts/quote.py fee PROGRAM --base 3000 [--extra 500] [--schedule "50% when the agreement is signed; 50% before filing"] [--services "a; b; c"]
  python3 scripts/quote.py tax --rate 13 --name HST                      tax on professional fees (not on IRCC fees)
  python3 scripts/quote.py table                                         your fee table and IRCC's fees by program
  python3 scripts/quote.py make --program PROGRAM [--spouse] [--children 2] [--people 3] [--minors 1] [--open-work-permit 1]
                               (--prospect ID | --case CASE | --name "Client Name") [--valid 30] [--notes "..."]
  python3 scripts/quote.py calc ... (same options as make, prints the numbers only)

PROGRAM is one of: express-entry, pnp, spousal, pgp, visitor, super-visa, study, work, citizenship, pr-card (or text that matches one).
--people counts everyone applying for visas and permits (each pays); --spouse and --children are for permanent residence;
--people and --minors for citizenship (adults = people - minors).

Guarantees:
  - IRCC fees come from templates/quote-fees.csv, taken from knowledge/11-forms-fees-processing/fee-schedule.md (each row dated).
    The weekly IRCC fee check (watch.py) flags any change; check the fee list before filing.
  - Your own fees come from cases/.fee-table.csv, set once. Tax is added to your fees only.
  - A quote is not a service agreement (Code s.24). With --prospect, the prospect moves to "quoted" with your fee total.
"""
import argparse
import csv
import datetime
import json
import pathlib
import re
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

GOV = de.REPO / "templates" / "quote-fees.csv"
TABLE = cs.ROOT / ".fee-table.csv"
TAX = cs.ROOT / ".fee-tax.json"
TABLE_FIELDS = ["program", "base", "extra", "schedule", "services"]
CENT = Decimal("0.01")


def die(msg):
    sys.exit("NOT PRODUCED: " + msg)


def dollars(x):
    return f"${x:,.2f}"


def amount(text, label):
    try:
        v = Decimal(str(text).replace(",", "").replace("$", ""))
    except InvalidOperation:
        die(f"{label} must be an amount such as 3000")
    if v < 0:
        die(f"{label} can't be negative")
    return v.quantize(CENT)


def gov_rows():
    with GOV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    programs, current = {}, None
    for r in rows:
        if r["match"]:
            current = {"key": r["program"], "match": r["match"], "label": r["label"], "lines": []}
            programs[r["program"]] = current
        programs[r["program"]]["lines"].append(r)
    return programs


def program_of(text):
    programs = gov_rows()
    if text in programs:
        return programs[text]
    hits = [p for p in programs.values() if re.search(p["match"], text, re.I)]
    hits.sort(key=lambda p: p["key"] != "super-visa")  # "super visa" also matches visitor
    if not hits:
        die(f"no IRCC fee table for '{text}'. Programs: {', '.join(programs)}")
    return hits[0]


def table():
    if not TABLE.exists():
        return {}
    with TABLE.open(encoding="utf-8", newline="") as f:
        return {r["program"]: r for r in csv.DictReader(f)}


def tax():
    try:
        d = json.loads(TAX.read_text(encoding="utf-8"))
        return Decimal(d["rate"]), d.get("name", "Tax")
    except (OSError, ValueError, KeyError, InvalidOperation):
        return None, ""


def gov_lines(prog, a):
    """[(description, count, amount)] for IRCC's fees."""
    people = a.people if a.people else 1 + (1 if a.spouse else 0) + (a.children or 0)
    out = []
    for r in prog["lines"]:
        who, each, cap = r["who"], Decimal(r["amount"]), Decimal(r["cap"]) if r["cap"] else None
        n = {"principal": 1, "spouse": 1 if a.spouse else 0, "child": a.children or 0, "each": people, "biometrics": people,
             "owp": a.open_work_permit or 0, "adult": max(0, people - (a.minors or 0)), "minor": a.minors or 0}.get(who, 0)
        if not n:
            continue
        total = each * n
        if cap is not None and total > cap:
            total = cap
        out.append((r["description"], n, total.quantize(CENT), r["last_verified"]))
    return out, people


def numbers(a):
    prog = program_of(a.program)
    fees = table().get(prog["key"])
    if not fees:
        die(f"no professional fee set for {prog['key']}. Set it once: quote.py fee {prog['key']} --base 3000 [--extra 500]")
    gov, people = gov_lines(prog, a)
    base, extra = Decimal(fees["base"]), Decimal(fees["extra"] or "0")
    extras = max(0, people - 1)
    prof = [(f"Professional fees for the application{' (principal applicant)' if extras and extra else ''}", base)]
    if extras and extra:
        prof.append((f"Each additional family member ({extras})", (extra * extras).quantize(CENT)))
    prof_total = sum((x for _, x in prof), Decimal("0"))
    rate, tax_name = tax()
    tax_amount = (prof_total * rate / 100).quantize(CENT) if rate else Decimal("0")
    gov_total = sum((x for *_, x, _ in gov), Decimal("0"))
    return {"prog": prog, "fees": fees, "gov": gov, "prof": prof, "prof_total": prof_total, "tax": tax_amount, "tax_name": tax_name, "rate": rate,
            "gov_total": gov_total, "total": prof_total + tax_amount + gov_total, "checked": max((d for *_, d in gov), default="")}


def show(n):
    print(n["prog"]["label"])
    for d, x in n["prof"]:
        print(f"  {d}: {dollars(x)}")
    if n["tax"]:
        print(f"  {n['tax_name']} {n['rate']}% on professional fees: {dollars(n['tax'])}")
    for d, c, x, _ in n["gov"]:
        print(f"  IRCC: {d}{f' x{c}' if c > 1 else ''}: {dollars(x)}")
    print(f"  Professional fees {dollars(n['prof_total'] + n['tax'])} + IRCC fees {dollars(n['gov_total'])} = {dollars(n['total'])}")
    print(f"  IRCC fees from the fee schedule checked {n['checked']}.")


def cmd_fee(a):
    prog = program_of(a.program)
    rows = table()
    rows[prog["key"]] = {"program": prog["key"], "base": str(amount(a.base, "--base")), "extra": str(amount(a.extra or 0, "--extra")),
                         "schedule": a.schedule or rows.get(prog["key"], {}).get("schedule", ""), "services": a.services or rows.get(prog["key"], {}).get("services", "")}
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    with TABLE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, TABLE_FIELDS)
        w.writeheader()
        w.writerows(rows.values())
    print(f"{prog['key']}: {dollars(Decimal(rows[prog['key']]['base']))}" + (f" + {dollars(Decimal(rows[prog['key']]['extra']))} per additional family member" if Decimal(rows[prog['key']]['extra']) else ""))


def cmd_tax(a):
    rate = amount(a.rate, "--rate")
    if rate > 20:
        die("a tax rate over 20% looks wrong")
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    TAX.write_text(json.dumps({"rate": str(rate), "name": a.name}), encoding="utf-8")
    print(f"{a.name} {rate}% added to professional fees in quotes.")


def cmd_table(_):
    mine = table()
    for key, p in gov_rows().items():
        f = mine.get(key)
        print(f"{key:13} {p['label']}: " + (f"your fee {dollars(Decimal(f['base']))}" + (f" + {dollars(Decimal(f['extra']))} per extra person" if Decimal(f["extra"] or 0) else "") if f else "your fee not set"))
        for r in p["lines"]:
            print(f"{'':15}IRCC {r['who']}: ${r['amount']}" + (f" (max ${r['cap']})" if r["cap"] else "") + f"  [{r['last_verified']}]")


def cmd_calc(a):
    show(numbers(a))


def cmd_make(a):
    import firm
    n = numbers(a)
    folder, out, name, prospect = None, None, a.name, None
    if a.case:
        folder = de.active_case(a.case)
        out = folder / "02-agreements"
    elif a.prospect:
        import prospects as ps
        prospect = ps.get(a.prospect)
        name = prospect["name"]
    if not folder and not name:
        die("give --prospect, --case or --name")
    if a.out:
        out = pathlib.Path(a.out)
    lines = [f"{d}: {dollars(x)}" for d, x in n["prof"]]
    if n["tax"]:
        lines.append(f"{n['tax_name']} ({n['rate']}%): {dollars(n['tax'])}")
    terms = {"program_label": n["prog"]["label"],
             "services": [s.strip() for s in (n["fees"].get("services") or "").split(";") if s.strip()] or [f"Preparing and filing the {n['prog']['label'].lower()} application, and representing you with IRCC until a decision"],
             "fee_lines": lines,
             "gov_lines": [f"{d}{f' (x{c})' if c > 1 else ''}: {dollars(x)}" for d, c, x, _ in n["gov"]],
             "totals": [f"Our fees{' with tax' if n['tax'] else ''}: {dollars(n['prof_total'] + n['tax'])}", f"IRCC fees: {dollars(n['gov_total'])}", f"Total: {dollars(n['total'])}"],
             "schedule": [s.strip() for s in (n["fees"].get("schedule") or "").split(";") if s.strip()] or ["As set out in the service agreement"],
             "fees_checked": n["checked"], "valid_days": str(a.valid), "notes": a.notes or ""}
    if not folder:
        terms["client"] = {"name": name}
    path, _ = firm.draft("quote", folder, terms, out)
    show(n)
    print(f"Saved: {path}")
    if prospect:
        import subprocess
        r = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("prospects.py")), "move", prospect["id"], "quoted", "--amount", str(n["prof_total"])],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout.strip() or r.stderr.strip())
    if folder:
        print(f"Once agreed: billing.py estimate {cs.read_case(folder).get('case_id', a.case)} --fees {n['prof_total']} --disbursements {n['gov_total']}")


def add_family(x):
    x.add_argument("--program", required=True); x.add_argument("--spouse", action="store_true"); x.add_argument("--children", type=int, default=0)
    x.add_argument("--people", type=int, default=0); x.add_argument("--minors", type=int, default=0); x.add_argument("--open-work-permit", type=int, default=0)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Fee quotes")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("fee"); x.add_argument("program"); x.add_argument("--base", required=True); x.add_argument("--extra"); x.add_argument("--schedule"); x.add_argument("--services"); x.set_defaults(fn=cmd_fee)
    x = s.add_parser("tax"); x.add_argument("--rate", required=True); x.add_argument("--name", default="GST/HST"); x.set_defaults(fn=cmd_tax)
    x = s.add_parser("table"); x.set_defaults(fn=cmd_table)
    x = s.add_parser("calc"); add_family(x); x.set_defaults(fn=cmd_calc)
    x = s.add_parser("make"); add_family(x); g = x.add_mutually_exclusive_group(); g.add_argument("--prospect"); g.add_argument("--case"); g.add_argument("--name")
    x.add_argument("--valid", type=int, default=30); x.add_argument("--notes"); x.add_argument("--out"); x.set_defaults(fn=cmd_make)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
