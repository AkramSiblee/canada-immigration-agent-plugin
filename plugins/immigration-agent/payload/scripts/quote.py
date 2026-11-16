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
--spouse and --children are for permanent residence, and for visas and permits (each family member is priced by their own
application). --member role:application[:age] states one family member exactly, e.g. --member spouse:owp:34 --member child:study:12
(applications: visitor, super-visa, study, work, owp). Without --member, a worker's spouse is assumed to need an open work
permit and children a visitor visa; the quote says so. --people (visas and permits) counts everyone when roles aren't known;
for citizenship, --people and --minors (adults = people - minors).

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


TEMPORARY = {"visitor", "super-visa", "study", "work"}
APP_LABEL = {"visitor": "visitor visa", "super-visa": "super visa", "study": "study permit", "work": "work permit", "owp": "open work permit"}
BIOMETRICS_KB = de.REPO / "knowledge" / "05-temporary-residence" / "flagpoling-biometrics-medicals.md"


def biometrics_ages():
    """(youngest who gives biometrics, oldest), from the exemptions in the knowledge base ('children under 14', 'over 79')."""
    text = BIOMETRICS_KB.read_text(encoding="utf-8") if BIOMETRICS_KB.exists() else ""
    low, high = re.search(r"children under (\d+)", text), re.search(r"over (\d+)\*?\*?\s*\(", text) or re.search(r"over (\d+)", text)
    return (int(low.group(1)) if low else None), (int(high.group(1)) if high else None)


OWP_KB = de.REPO / "knowledge" / "05-temporary-residence" / "open-work-permits.md"


def children_get_owp():
    """False when the knowledge base says dependent children are no longer eligible for a family open work permit."""
    import owp_rules
    r = owp_rules.rules(OWP_KB)
    return bool(r and r["children"])  # unknown: never assume a child gets one


def principal_job(a):
    """(NOC, permit end) for the principal: --noc and --permit-end, else the case's client facts (noc_code, permit_expiry_date)."""
    noc, end = getattr(a, "noc", None), getattr(a, "permit_end", None)
    if (not noc or not end) and getattr(a, "case", None):
        import csv
        folder = de.active_case(a.case)
        client = cs.read_case(folder).get("client", "")
        path = folder / "client-facts.csv"
        rows = list(csv.DictReader(path.open(encoding="utf-8", newline=""))) if path.exists() else []
        mine = [r for r in rows if r.get("value") and (not client or de.same_person(client, r.get("person", "")))]
        noc = noc or next((r["value"] for r in mine if r["key"] == "noc_code"), None)
        end = end or next((r["value"] for r in mine if r["key"] == "permit_expiry_date"), None)
    return noc, end


def principal_is_open(a):
    """The principal's own permit is open only when the program says so (owp, open work permit, PGWP, BOWP)."""
    return bool(re.search(r"\bowp\b|open[ -]?work|pgwp|post-?graduation|bowp|bridging", str(a.program), re.I))


def members(prog, a):
    """[(who, application, age or None, assumed)] for a visa or permit application, principal first."""
    own = "owp" if prog["key"] == "work" and principal_is_open(a) else prog["key"]
    out = [("principal applicant", own, getattr(a, "age", None), False)]
    members.unassigned = 0
    given = getattr(a, "member", None) or []
    for i, m in enumerate(given, 1):
        bits = [b.strip() for b in m.split(":")]
        app = bits[1].lower() if len(bits) > 1 and bits[1] else ""
        if app not in APP_LABEL:
            die(f"--member {m}: give role:application[:age], application one of {', '.join(APP_LABEL)}")
        age = int(bits[2]) if len(bits) > 2 and bits[2].isdigit() else None
        out.append((bits[0] or f"family member {i}", app, age, False))
    if given:
        return out
    members.spouse_note = ""
    spouse_ok = None
    if prog["key"] == "work" and not principal_is_open(a):  # the worker-spouse rule, read from the knowledge base
        import owp_rules
        spouse_ok, members.spouse_note = owp_rules.spouse_check(*principal_job(a))
    spouse_app = ("visitor" if spouse_ok == "no" else "owp") if prog["key"] == "work" else prog["key"] if prog["key"] in ("visitor", "super-visa") else "visitor"
    child_app = prog["key"] if prog["key"] in ("visitor", "super-visa") else "visitor"
    if a.spouse:
        out.append(("spouse or partner", spouse_app, None, spouse_ok != "yes" and (spouse_app != prog["key"] or prog["key"] == "work")))
    for i in range(a.children or 0):
        out.append((f"child {i + 1}", child_app, None, child_app != prog["key"]))
    extra = (a.people or 0) - len(out)
    for i in range(max(0, extra)):  # people with no role given
        out.append((f"family member {i + 1}", child_app, None, child_app != prog["key"]))
    owps = (a.open_work_permit or 0) - sum(1 for p in out if p[1] == "owp")
    if prog["key"] == "work" and owps > 0:  # --open-work-permit N: spouse first, then dependants only if the rules allow
        order = [i for i, p in enumerate(out) if p[0].startswith("spouse") and spouse_ok != "no"] +                 ([i for i, p in enumerate(out) if p[0].startswith(("child", "family member"))] if children_get_owp() else [])
        for i in order:
            if owps and out[i][1] != "owp":
                who, _, age, _ = out[i]
                out[i] = (who, "owp", age, True)
                owps -= 1
        members.unassigned = owps
    return out


def temporary_lines(prog, a):
    """IRCC fees for a family's visas and permits, each person priced by their own application."""
    programs = gov_rows()
    people = members(prog, a)
    out = []
    by_app = {}
    for who, app, age, assumed in people:
        by_app.setdefault(app, []).append((who, age, assumed))
    for app, group in by_app.items():
        key = "work" if app == "owp" else app
        lines = programs[key]["lines"]
        each = next(r for r in lines if r["who"] == "each")
        n = len(group)
        total = Decimal(each["amount"]) * n
        if each["cap"] and total > Decimal(each["cap"]):
            total = Decimal(each["cap"])
        names = ", ".join(w + (f" (age {g})" if g is not None else "") + (" - assumed" if s else "") for w, g, s in group)
        cap_note = f" (family maximum ${each['cap']})" if each["cap"] else ""
        out.append((f"{APP_LABEL[app].capitalize()}: ${each['amount']} each{cap_note}: {names}", n, total.quantize(CENT), each["last_verified"]))
        if app == "owp":
            holder = next(r for r in lines if r["who"] == "owp")
            out.append((f"{holder['description']}: {names}", n, (Decimal(holder["amount"]) * n).quantize(CENT), holder["last_verified"]))
    bio = next(r for r in programs[prog["key"]]["lines"] if r["who"] == "biometrics")
    low, high = biometrics_ages()
    giving = [p for p in people if p[2] is None or ((low is None or p[2] >= low) and (high is None or p[2] <= high))]
    exempt = len(people) - len(giving)
    if giving:
        total = min(Decimal(bio["amount"]) * len(giving), Decimal(bio["cap"])) if bio["cap"] else Decimal(bio["amount"]) * len(giving)
        note = f" ({exempt} exempt by age: under {low} or over {high})" if exempt else ""
        out.append((bio["description"] + note, len(giving), total.quantize(CENT), bio["last_verified"]))
    assumed = [f"{w}: {APP_LABEL[app]}" for w, app, _, s in people if s]
    if getattr(members, "spouse_note", "") and any(w.startswith("spouse") for w, *_ in people):
        assumed.append(("Spouse priced as a visitor: " if any(w.startswith("spouse") and app == "visitor" for w, app, *_ in people) else "")
                       + members.spouse_note)
    if getattr(members, "unassigned", 0):
        assumed.append(f"{members.unassigned} open work permit(s) not priced: no eligible spouse in the quote, the principal's own permit "
                       "isn't open, and dependent children aren't eligible (open-work-permits.md)")
    return out, len(people), assumed


def gov_lines(prog, a):
    """[(description, count, amount)] for IRCC's fees."""
    if prog["key"] in TEMPORARY:
        lines, people, assumed = temporary_lines(prog, a)
        gov_lines.assumed = assumed
        return lines, people
    gov_lines.assumed = []
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
    return {"assumed": getattr(gov_lines, "assumed", []), "people": members(prog, a) if prog["key"] in TEMPORARY else [],
            "prog": prog, "fees": fees, "gov": gov, "prof": prof, "prof_total": prof_total, "tax": tax_amount, "tax_name": tax_name, "rate": rate,
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
    if n["people"]:
        print("  Each person's application: " + "; ".join(f"{w}: {APP_LABEL[app]}" for w, app, _, _ in n["people"]))
    if n["assumed"]:
        print("  Assumed (confirm, or give --member role:application[:age]): " + "; ".join(n["assumed"]))


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


def who_applies(n):
    """The sentence in the quote that says which application each person's IRCC fee is for."""
    if not n["people"]:
        return ""
    each = "; ".join(f"{w}, {APP_LABEL[app]}" for w, app, _, _ in n["people"])
    return f"IRCC fees assume each person applies for: {each}. If anyone needs a different application, the IRCC fees change."


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
             "fees_checked": n["checked"], "valid_days": str(a.valid),
             "notes": " ".join(x for x in (who_applies(n), a.notes or "") if x)}
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
    x.add_argument("--member", action="append", help="one family member of a visa or permit application: role:application[:age], e.g. child:study:12")
    x.add_argument("--age", type=int, help="the principal applicant's age (biometrics exemptions)")
    x.add_argument("--noc", help="the principal's NOC code, to check the spouse's open work permit (default: the case's noc_code)")
    x.add_argument("--permit-end", help="the principal's permit end date (default: the case's permit_expiry_date)")


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
