#!/usr/bin/env python3
"""Residence day counter: citizenship physical presence (1,095 days) and the PR residency obligation (730 days).

  add CASE --left YYYY-MM-DD [--returned YYYY-MM-DD] [--to COUNTRY] [--reason TEXT] [--counts-as TYPE]
  citizenship CASE [--sign YYYY-MM-DD] [--pr-date D] [--tr-from D] [--excluded FROM:TO ...] [--no-status FROM:TO ...]
  pr CASE [--as-of YYYY-MM-DD] [--pr-date D]
  (use --trips FILE instead of CASE for a quick count without a case; nothing is saved then)

Trips live in the case's travel-history.csv: left, returned, destination, reason, counts_as.
Leave "returned" empty while the client is still abroad.

How days are counted (IRCC):
- The day the client leaves and the day they return both count as days in Canada; only full days abroad are absences.
  A same-day or next-day trip has 0 days absent, but must still be listed on a citizenship application.
- Citizenship (Citizenship Act s.5(1)(c), s.5(1.001), s.21): 1,095 days in the 5 years before the signing date
  (the signing day itself doesn't count). Each day in Canada as a temporary resident or protected person before PR
  counts as half a day, at most 365. Days on probation, parole or in prison (and conditional sentences) don't count.
  counts_as "crown" (Crown service abroad, or living with a Crown servant) counts in full (s.5(1.01)); paper only.
- PR residency obligation (IRPA s.28): 730 days in Canada in the 5 years ending on the examination date, or, for a PR
  of under 5 years, able to reach 730 by the 5th anniversary. Days abroad count when counts_as is "citizen-spouse"
  (accompanying a Canadian citizen spouse, partner or parent) or "canadian-employer" / "accompanying-employee"
  (full-time for a Canadian business or public service, or accompanying a PR who is).
The counter is arithmetic on the dates given. It cannot see unlisted trips: check them against passport stamps and the
CBSA travel history before relying on the result.
"""
import argparse
import csv
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_extract as de  # noqa: E402

FIELDS = ["left", "returned", "destination", "reason", "counts_as"]
PR_EXCEPTIONS = {"citizen-spouse", "canadian-employer", "accompanying-employee"}
TYPES = PR_EXCEPTIONS | {"crown", ""}
CITIZENSHIP_DAYS, PRE_PR_CAP, PR_DAYS = 1095, 365, 730
CLOSE = 30  # a margin under this many days is reported as too close


def day(text, what="date"):
    try:
        return datetime.date.fromisoformat(str(text).strip())
    except ValueError:
        sys.exit(f"ERROR: {what} must be YYYY-MM-DD, got '{text}'")


def years_before(d, n):
    try:
        return d.replace(year=d.year - n)
    except ValueError:  # 29 February
        return d.replace(year=d.year - n, day=28)


def span(text):
    a, _, b = text.partition(":")
    return day(a, "period start"), day(b or a, "period end")


def dates(a, b):
    """Every date from a to b inclusive."""
    return {a + datetime.timedelta(n) for n in range((b - a).days + 1)} if b >= a else set()


# ---- trips ----
def trips_path(folder):
    return folder / "travel-history.csv"


def read_trips(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k: (r.get(k) or "").strip() for k in FIELDS} for r in csv.DictReader(f)]


def check_trips(trips, today):
    """Problems in the trip list: (level, text)."""
    out, spans = [], []
    for n, t in enumerate(trips, 1):
        left = day(t["left"], f"trip {n} left")
        back = day(t["returned"], f"trip {n} returned") if t["returned"] else None
        if t["counts_as"] not in TYPES:
            out.append(("MUST", f"Trip {n}: counts_as '{t['counts_as']}' isn't one of: {', '.join(sorted(x for x in TYPES if x))}"))
        if back and back < left:
            out.append(("MUST", f"Trip {n}: return {back} is before departure {left}"))
            continue
        if not back and left <= today:
            out.append(("CHECK", f"Trip {n}: no return date, so the client is counted as still abroad since {left}"))
        spans.append((left, back or datetime.date.max, n))
    spans.sort()
    for (a1, b1, n1), (a2, b2, n2) in zip(spans, spans[1:]):
        if a2 < b1:
            out.append(("MUST", f"Trips {n1} and {n2} overlap ({a2} is before the return of trip {n1}). Check the dates"))
    return out


def absent_days(trips, until, kinds=None):
    """Full days abroad up to `until`. kinds: only trips whose counts_as is in this set (None: all)."""
    out = set()
    for t in trips:
        if kinds is not None and t["counts_as"] not in kinds:
            continue
        left = day(t["left"])
        back = day(t["returned"]) if t["returned"] else until + datetime.timedelta(1)
        out |= dates(left + datetime.timedelta(1), min(back - datetime.timedelta(1), until))
    return out


def trip_rows(trips, start, end):
    rows = []
    for n, t in enumerate(trips, 1):
        left = day(t["left"])
        back = day(t["returned"]) if t["returned"] else None
        full = dates(left + datetime.timedelta(1), (back or end + datetime.timedelta(1)) - datetime.timedelta(1))
        inside = len({d for d in full if start <= d <= end})
        rows.append([n, t["left"], t["returned"] or "still abroad", t["destination"], t["reason"], t["counts_as"], len(full), inside])
    return rows


# ---- citizenship ----
def citizenship(trips, sign, pr_date, tr_from=None, excluded=(), no_status=()):
    start, end = years_before(sign, 5), sign - datetime.timedelta(1)
    window = dates(start, end)
    abroad = absent_days(trips, end, kinds={"", *PR_EXCEPTIONS})  # Crown service abroad counts as presence
    crown = absent_days(trips, end, kinds={"crown"}) & window
    s21 = set().union(*(dates(a, b) for a, b in excluded)) if excluded else set()
    gaps = set().union(*(dates(a, b) for a, b in no_status)) if no_status else set()
    present = window - abroad - s21
    as_pr = {d for d in present if d >= pr_date}
    first = tr_from or pr_date
    before = {d for d in present if first <= d < pr_date} - gaps
    credit = min(PRE_PR_CAP, len(before) / 2)
    total = len(as_pr) + credit
    return {"start": start, "end": end, "as_pr": len(as_pr), "before_pr": len(before), "credit": credit, "total": total,
            "needed": CITIZENSHIP_DAYS, "margin": total - CITIZENSHIP_DAYS, "abroad": len(abroad & window), "excluded": len(s21 & window),
            "crown": len(crown), "met": total >= CITIZENSHIP_DAYS}


def earliest_sign(trips, today, pr_date, tr_from=None, excluded=(), no_status=()):
    """First signing date from today with 1,095 days, assuming no trips beyond those listed."""
    d = today
    for _ in range(366 * 6):
        if citizenship(trips, d, pr_date, tr_from, excluded, no_status)["met"]:
            return d
        d += datetime.timedelta(1)
    return None


# ---- PR residency obligation ----
def residency(trips, as_of, pr_date):
    anniversary = years_before(pr_date, -5)
    under_five = as_of < anniversary
    start = pr_date if under_five else years_before(as_of, 5) + datetime.timedelta(1)
    window = dates(start, as_of)
    abroad = absent_days(trips, as_of)
    counted_abroad = absent_days(trips, as_of, kinds=PR_EXCEPTIONS) & window
    present = window - abroad
    days = len(present) + len(counted_abroad)
    still = (anniversary - as_of).days - 1 if under_five else 0  # days left before the 5th anniversary
    best = days + max(still, 0)
    return {"start": start, "end": as_of, "under_five": under_five, "anniversary": anniversary, "present": len(present),
            "counted_abroad": len(counted_abroad), "days": days, "still_possible": max(still, 0), "needed": PR_DAYS,
            "met": (best if under_five else days) >= PR_DAYS, "margin": (best if under_five else days) - PR_DAYS,
            "abroad": len(abroad & window)}


def latest_return(trips, as_of, pr_date):
    """If the client leaves after as_of and stays away: the last date they can come back and still meet 730 days."""
    away = trips + [{"left": as_of.isoformat(), "returned": "", "destination": "", "reason": "", "counts_as": ""}]
    d = as_of
    for _ in range(366 * 6):
        nxt = d + datetime.timedelta(1)
        trial = [dict(t) for t in away]
        trial[-1]["returned"] = nxt.isoformat()
        if not residency(trial, nxt, pr_date)["met"]:
            return d
        d = nxt
    return None


def by_year(trips, start, end, pr_date):
    abroad = absent_days(trips, end)
    rows = []
    for y in range(start.year, end.year + 1):
        a, b = max(start, datetime.date(y, 1, 1)), min(end, datetime.date(y, 12, 31))
        span_ = dates(a, b)
        inside = len(span_ - abroad)
        rows.append([y, f"{a} to {b}", len(span_), inside, len(span_ & abroad), len({d for d in span_ - abroad if d >= pr_date})])
    return rows


# ---- commands ----
def setup(a):
    if a.trips:
        return None, read_trips(pathlib.Path(a.trips)), {}
    if not a.case:
        sys.exit("ERROR: give a case, or --trips FILE")
    folder = de.active_case(a.case)
    import form_prefill as fp
    import case as cs
    info = cs.read_case(folder)
    facts = fp.facts_from_file(folder / "client-facts.csv", a.person or info.get("client", ""))
    found = {k: v[0]["value"] for k, v in facts.items() if v}
    return folder, read_trips(trips_path(folder)), found


def need_pr_date(a, facts):
    text = a.pr_date or facts.get("pr_date")
    if not text:
        sys.exit("ERROR: the PR date is needed: --pr-date YYYY-MM-DD, or a pr_date fact in client-facts.csv")
    return day(text, "PR date")


def save(folder, kind, sheets):
    if folder is None:
        return None
    import openpyxl
    out = folder / "04-advice"
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    n = 1
    while True:
        path = out / f"{today}-{kind}{'' if n == 1 else f'-v{n}'}.xlsx"
        if not path.exists():
            break
        n += 1
    book = openpyxl.Workbook()
    book.remove(book.active)
    for title, header, rows, widths in sheets:
        de.add_sheet(book, title, header, rows, widths)
    book.save(path)
    return path


def show_flags(flags):
    for level, text in flags:
        print(f"  [{'Fix' if level == 'MUST' else 'Check'}] {text}")


def verdict(met, margin, what):
    if not met:
        return f"NOT MET: {abs(margin):g} day(s) short of {what}"
    if margin < CLOSE:
        return f"MET, but only {margin:g} day(s) over {what}: too close to rely on without checking every trip against CBSA and passport records"
    return f"MET with {margin:g} day(s) to spare"


def cmd_add(a):
    folder = de.active_case(a.case)
    left = day(a.left, "left")
    if a.returned and day(a.returned, "returned") < left:
        sys.exit("ERROR: the return date is before the departure date")
    if (a.counts_as or "") not in TYPES:
        sys.exit(f"ERROR: --counts-as must be one of: {', '.join(sorted(x for x in TYPES if x))}")
    path = trips_path(folder)
    rows = read_trips(path)
    rows.append({"left": a.left, "returned": a.returned or "", "destination": a.to or "", "reason": a.reason or "", "counts_as": a.counts_as or ""})
    rows.sort(key=lambda r: r["left"])
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Trips recorded: {len(rows)}")
    show_flags(check_trips(rows, datetime.date.today()))


def cmd_citizenship(a):
    folder, trips, facts = setup(a)
    today = datetime.date.today()
    sign = day(a.sign, "signing date") if a.sign else today
    pr_date = need_pr_date(a, facts)
    tr_text = a.tr_from or facts.get("tr_from")
    tr_from = day(tr_text, "temporary resident start") if tr_text else None
    excluded = [span(x) for x in a.excluded or []]
    no_status = [span(x) for x in a.no_status or []]
    flags = check_trips(trips, today)
    if any(l == "MUST" for l, _ in flags):
        show_flags(flags)
        sys.exit("Fix the trip list first")
    r = citizenship(trips, sign, pr_date, tr_from, excluded, no_status)
    first = None if r["met"] else earliest_sign(trips, max(sign, today), pr_date, tr_from, excluded, no_status)
    notes = []
    if not tr_from:
        notes.append("No date for time in Canada before PR (--tr-from): pre-PR half days are not counted")
    if r["crown"]:
        notes.append(f"{r['crown']} day(s) of Crown service abroad counted in full: the application must be on paper with CIT 0177")
    if r["excluded"]:
        notes.append(f"{r['excluded']} day(s) on probation, parole or in prison removed (s.21)")
    notes += ["List every trip on the application, including same-day and next-day trips (0 days absent)",
              "The signing date must equal the application date in IRCC's calculator; print or save its result for the application",
              "Also needed: income tax filed for 3 of the 5 years (s.5(1)(c)(iii)), language proof if 18-54, no prohibitions"]
    print(f"Citizenship physical presence, signing on {sign} (counting {r['start']} to {r['end']})")
    print(f"  Days as PR: {r['as_pr']} | days before PR: {r['before_pr']} = {r['credit']:g} credit (max 365) | total {r['total']:g} of 1,095")
    print(f"  Days abroad in the period: {r['abroad']}")
    print("  " + verdict(r["met"], r["margin"], "1,095"))
    if first:
        print(f"  Earliest signing date with 1,095 days, if no trips beyond those listed: {first}")
    show_flags(flags)
    for n in notes:
        print(f"  Note: {n}")
    summary = [[f"Signing date: {sign}"], [f"Counting period: {r['start']} to {r['end']} (the signing day doesn't count)"], [f"PR since: {pr_date}"],
               [f"Days in Canada as PR: {r['as_pr']}"], [f"Days in Canada before PR: {r['before_pr']}, credited as {r['credit']:g} (half days, max 365)"],
               [f"Total: {r['total']:g} of 1,095"], [verdict(r["met"], r["margin"], "1,095")]]
    if first:
        summary.append([f"Earliest signing date, if no trips beyond those listed: {first}"])
    summary += [[""]] + [[f"Check: {t}"] for _, t in flags] + [[f"Note: {n}"] for n in notes] + [[""],
                ["Days of departure and return count as days in Canada (IRCC). This is arithmetic on the dates in travel-history.csv; "
                 "it can't see unlisted trips. Compare with passport stamps and the CBSA travel history, then use IRCC's calculator for the application."]]
    path = save(folder, "citizenship-presence", [
        ("Summary", ["Citizenship physical presence"], summary, [120]),
        ("Trips", ["No.", "Left", "Returned", "Destination", "Reason", "Counts as", "Full days abroad", "Days abroad in the period"],
         trip_rows(trips, r["start"], r["end"]) or [["", "", "", "No trips listed", "", "", "", ""]], [6, 12, 14, 22, 30, 18, 16, 22]),
        ("Year by year", ["Year", "Dates", "Days", "In Canada", "Abroad", "In Canada as PR"], by_year(trips, r["start"], r["end"], pr_date), [8, 28, 8, 12, 10, 16])])
    if path:
        print("Saved:", path)


def cmd_pr(a):
    folder, trips, facts = setup(a)
    today = datetime.date.today()
    as_of = day(a.as_of, "as-of date") if a.as_of else today
    pr_date = need_pr_date(a, facts)
    flags = check_trips(trips, today)
    if any(l == "MUST" for l, _ in flags):
        show_flags(flags)
        sys.exit("Fix the trip list first")
    r = residency(trips, as_of, pr_date)
    back = latest_return(trips, as_of, pr_date) if r["met"] else None
    print(f"PR residency obligation on {as_of} (counting {r['start']} to {r['end']}{', PR under 5 years' if r['under_five'] else ''})")
    print(f"  Days in Canada: {r['present']} | days abroad that count: {r['counted_abroad']} | total {r['days']} of 730")
    if r["under_five"]:
        print(f"  5th anniversary of PR: {r['anniversary']}; {r['still_possible']} more day(s) possible before then")
    print("  " + verdict(r["met"], r["margin"], "730"))
    if back:
        print(f"  If the client leaves Canada now: back by {back} at the latest to still meet 730 days")
    show_flags(flags)
    notes = ["Days abroad count only with proof: accompanying a citizen spouse or parent (living together), or full-time work for a Canadian business "
             "or public service (not a business set up to keep status)", "Same-day trips needn't be listed on IMM 5444"]
    if not r["met"]:
        notes.append("Not met: consider humanitarian and compassionate factors (IRPA s.28(2)(c)); the IAD appeal deadline is 60 days from the decision")
    for n in notes:
        print(f"  Note: {n}")
    summary = [[f"Examination date: {as_of}"], [f"PR since: {pr_date}"], [f"Counting period: {r['start']} to {r['end']}"],
               [f"Days in Canada: {r['present']}"], [f"Days abroad that count (s.28(2)(a)): {r['counted_abroad']}"], [f"Total: {r['days']} of 730"]]
    if r["under_five"]:
        summary.append([f"PR for under 5 years: 5th anniversary {r['anniversary']}, {r['still_possible']} more day(s) possible before then"])
    summary.append([verdict(r["met"], r["margin"], "730")])
    if back:
        summary.append([f"If the client leaves now: back by {back} at the latest"])
    summary += [[""]] + [[f"Check: {t}"] for _, t in flags] + [[f"Note: {n}"] for n in notes] + [[""],
                ["Days of departure and return count as days in Canada (IRCC). This is arithmetic on the dates in travel-history.csv; "
                 "it can't see unlisted trips. Compare with passport stamps and the CBSA travel history."]]
    path = save(folder, "pr-residency", [
        ("Summary", ["PR residency obligation"], summary, [120]),
        ("Trips", ["No.", "Left", "Returned", "Destination", "Reason", "Counts as", "Full days abroad", "Days abroad in the period"],
         trip_rows(trips, r["start"], r["end"]) or [["", "", "", "No trips listed", "", "", "", ""]], [6, 12, 14, 22, 30, 18, 16, 22]),
        ("Year by year", ["Year", "Dates", "Days", "In Canada", "Abroad", "In Canada as PR"], by_year(trips, r["start"], r["end"], pr_date), [8, 28, 8, 12, 10, 16])])
    if path:
        print("Saved:", path)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Residence day counter: citizenship (1,095 days) and PR residency obligation (730 days)")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("add", help="record a trip")
    x.add_argument("case"); x.add_argument("--left", required=True); x.add_argument("--returned"); x.add_argument("--to"); x.add_argument("--reason")
    x.add_argument("--counts-as", help="crown, citizen-spouse, canadian-employer or accompanying-employee"); x.set_defaults(fn=cmd_add)
    for name, fn in (("citizenship", cmd_citizenship), ("pr", cmd_pr)):
        x = s.add_parser(name)
        x.add_argument("case", nargs="?"); x.add_argument("--trips", help="a trips CSV instead of a case (nothing is saved)")
        x.add_argument("--person"); x.add_argument("--pr-date")
        if name == "citizenship":
            x.add_argument("--sign", help="signing date (default today)"); x.add_argument("--tr-from", help="first day in Canada as a temporary resident or protected person")
            x.add_argument("--excluded", action="append", help="FROM:TO on probation, parole, in prison or under a conditional sentence")
            x.add_argument("--no-status", action="append", help="FROM:TO in Canada before PR without temporary status (not credited)")
        else:
            x.add_argument("--as-of", help="examination date (default today)")
        x.set_defaults(fn=fn)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
