#!/usr/bin/env python3
"""Client opportunities: open and closed files where the client may need the firm again soon.

  python3 scripts/opportunities.py list [--days 120] [--all]      print them (changes nothing)
  python3 scripts/opportunities.py report [--days 120] [--out DIR] save Output/general/YYYY-MM-DD-client-opportunities.xlsx
  python3 scripts/opportunities.py consent CASE yes|no            record whether the client agreed to hear about future services

What it looks for (only from dates already in the files):
  - Citizenship: PR date known and 1,095 days reached, or reached within the window (travel-history.csv counted, as /presence does)
  - PR card: pr_card_expiry within 180 days or passed
  - Permit or status ending on a closed file (status_expiry): extension, PGWP, or a PR route
  - Study, PGWP or work files a year or more old: Canadian experience may now open CEC or a PNP stream
  - Express Entry: next birthday from age 30 lowers CRS age points; language test or profile running out
  - Family left behind: spouse, partner or child listed as not accompanying on a file where the client got PR

Guarantees:
  - Reads case files only. Nothing is sent and no file is changed (except 'consent', which sets contact_ok in case.md).
  - Each item is a prompt to review the file, not advice that the client qualifies.
  - Marketing to former clients uses their personal information for a new purpose: privacy law (PIPEDA or the provincial
    law) and anti-spam rules apply. Without contact_ok: yes, an item is marked "consent not recorded".
"""
import argparse
import csv
import datetime
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

WINDOW = 120
PR_CARD_DAYS = 180  # practice default: renewal takes weeks, and an expired card is needed to board flights to Canada
STATUS_DAYS = 180
CEC_MONTHS = 12
BIRTHDAY_DAYS = 90
PR_PROGRAMS = r"express|\bee\b|pnp|nominee|spous|partner|family|sponsor|pgp|parent|quebec|pstq|peq|caregiver|start-?up|self-?employ|h&c|humanitarian|refug|protect|rural|atlantic|aip|pr\b|permanent"
TR_TO_PR = r"stud|pgwp|work|lmia|owp|iec|\bict\b|cusma"
EE = r"express|\bee\b|crs|fsw|cec|\bfst\b"
FAMILY = r"spouse|wife|husband|partner|common-law|son|daughter|child"


def date_of(text):
    try:
        return datetime.date.fromisoformat(str(text).strip())
    except ValueError:
        return None


def facts(folder, client):
    """Principal's facts: key -> value."""
    path = folder / "client-facts.csv"
    out = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            who = (r.get("person") or "").strip().lower()
            if who in ("", "principal", "client", "applicant", client.lower()) and r.get("key") and r.get("value"):
                out.setdefault(r["key"].strip(), r["value"].strip())
    return out


def family_left(folder):
    text = (folder / "case.md").read_text(encoding="utf-8")
    m = re.search(r"## Family members.*?\n((?:\|.*\n?)+)", text)
    out = []
    for line in (m.group(1).splitlines() if m else [])[2:]:
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 4 and c[0] and re.search(FAMILY, c[1], re.I) and re.match(r"no\b|n\b", c[3], re.I):
            out.append((c[0], c[1]))
    return out


def age_on(dob, day):
    return day.year - dob.year - ((day.month, day.day) < (dob.month, dob.day))


def next_birthday(dob, today):
    for y in (today.year, today.year + 1):
        try:
            b = dob.replace(year=y)
        except ValueError:
            b = datetime.date(y, 3, 1)
        if b >= today:
            return b
    return None


def item(folder, info, when, kind, why, service, today):
    return {"case": folder.name, "id": info.get("case_id", folder.name[:8]), "client": info.get("client", ""), "state": "closed" if folder.parent == cs.CLOSED else "open",
            "program": info.get("program", ""), "kind": kind, "when": when.isoformat() if when else "", "left": (when - today).days if when else "",
            "why": why, "service": service, "consent": {"yes": "yes", "no": "no"}.get(info.get("contact_ok", "").lower(), "not recorded")}


def first_sign(pr, trips, today, horizon, pr_date, tr):
    """First signing date from today to the horizon with 1,095 days, or None. Checks the horizon first, so most files cost one count."""
    if not pr.citizenship(trips, horizon, pr_date, tr)["met"]:
        return None
    d = today
    while d < horizon and not pr.citizenship(trips, d, pr_date, tr)["met"]:
        d += datetime.timedelta(days=1)
    return d


def for_case(folder, today, days):
    import presence as pr
    import validity as vd
    info = cs.read_case(folder)
    program = info.get("program", "")
    closed = folder.parent == cs.CLOSED
    f = facts(folder, info.get("client", ""))
    out = []
    horizon = today + datetime.timedelta(days=days)

    pr_date = date_of(f.get("pr_date", "")) or date_of(info.get("pr_date", ""))
    if pr_date and not re.search(r"citizen", program, re.I):
        trips = pr.read_trips(pr.trips_path(folder))
        tr = date_of(f.get("tr_from", ""))
        try:
            bad = [t for lvl, t in pr.check_trips(trips, today) if lvl == "MUST"]
            first = None if bad else first_sign(pr, trips, today, horizon, pr_date, tr)
        except SystemExit:  # presence.py stops on an unreadable date
            bad, first = ["a trip date can't be read"], None
        if bad:
            out.append(item(folder, info, None, "Citizenship", f"PR since {pr_date}, but the trip list needs fixing first ({bad[0]})", "Citizenship grant: check /presence", today))
        else:
            if first:
                note = "" if trips else " No trips recorded: confirm travel history."
                when = "may already have 1,095 days of presence" if first <= today else f"may reach 1,095 days of presence on {first}"
                out.append(item(folder, info, first, "Citizenship", f"PR since {pr_date}: {when} (trips listed so far).{note}",
                                "Citizenship grant application", today))

    card = date_of(f.get("pr_card_expiry", "")) or date_of(info.get("pr_card_expiry", ""))
    if card and (card - today).days <= PR_CARD_DAYS:
        out.append(item(folder, info, card, "PR card", f"PR card {'expired' if card < today else 'expires'} {card}", "PR card renewal (check the 730-day residency obligation first)", today))

    status = date_of(info.get("status_expiry", ""))
    if closed and status and today - datetime.timedelta(days=30) <= status <= today + datetime.timedelta(days=STATUS_DAYS):
        out.append(item(folder, info, status, "Status ending", f"Status in Canada {'ended' if status < today else 'ends'} {status} (closed file)",
                        "Extension, restoration (90 days), PGWP or a PR route", today))

    opened = date_of(info.get("opened", ""))
    if re.search(TR_TO_PR, program, re.I) and not re.search(PR_PROGRAMS, program, re.I) and opened and (today - opened).days >= CEC_MONTHS * 30 and not pr_date:
        out.append(item(folder, info, None, "Next step to PR", f"{program} file opened {opened}: a year or more of Canadian work may open the Canadian Experience Class or a PNP stream",
                        "PR assessment (/pr-plan)", today))

    dob = date_of(f.get("date_of_birth", ""))
    if dob and re.search(EE, program, re.I) and not pr_date:
        b = next_birthday(dob, today)
        if b and (b - today).days <= BIRTHDAY_DAYS and age_on(dob, b) >= 30:
            out.append(item(folder, info, b, "CRS age points", f"Turns {age_on(dob, b)} on {b}: CRS age points go down each year from age 30",
                            "Re-check the CRS score; act on any pending step before the birthday", today))

    try:
        rows, _ = vd.status(folder, today)
    except (OSError, ValueError, KeyError):
        rows = []
    for r in rows:
        if r["doc"] in ("language_test", "ee_profile") and r["until"] <= horizon and (closed or r["doc"] == "ee_profile"):
            what = "Language test result" if r["doc"] == "language_test" else "Express Entry profile"
            out.append(item(folder, info, r["until"], "Expiring document", f"{what}{' of ' + r['person'] if r['person'] else ''} runs out {r['until']}",
                            "New test, or a new Express Entry profile", today))

    if pr_date or (closed and re.search(r"pr\b|permanent|express|pnp", program, re.I)):
        for name, rel in family_left(folder):
            out.append(item(folder, info, None, "Family sponsorship", f"{rel.capitalize()} {name} listed as not accompanying",
                            "Family class sponsorship. Check IRPR 117(9)(d): were they examined or declared?", today))
    return out


def find(today=None, days=WINDOW, include_closed=True):
    today = today or datetime.date.today()
    pool = cs.folders(cs.ACTIVE) + (cs.folders(cs.CLOSED) if include_closed else [])
    out, errors = [], []
    for folder in pool:
        try:
            out += for_case(folder, today, days)
        except (OSError, ValueError, KeyError, TypeError) as e:
            errors.append((folder.name, type(e).__name__))
    out.sort(key=lambda r: (r["left"] if r["left"] != "" else 99999, r["case"]))
    return out, errors


def cmd_list(a):
    rows, errors = find(days=a.days)
    if not a.all:
        rows = [r for r in rows if r["consent"] != "no"]
    if not rows:
        print("No opportunities found in the files (only dates recorded in the files are used).")
    for r in rows:
        print(f"{r['when'] or '-':10}  {r['id']}  {r['client'][:24]:24}  {r['kind']:18}  {r['why']}")
        print(f"{'':12}Service: {r['service']} | {r['state']} file | contact consent: {r['consent']}")
    for name, err in errors:
        print(f"Could not read {name} ({err})")
    print(f"\n{len(rows)} item(s). Each is a prompt to review the file, not a finding that the client qualifies.")
    if any(r["consent"] != "yes" for r in rows):
        print("Contact only clients who agreed to hear about future services (privacy and anti-spam rules). Record it: opportunities.py consent CASE yes")


def cmd_report(a):
    import openpyxl
    rows, errors = find(days=a.days)
    out = pathlib.Path(a.out) if a.out else de.REPO / "Output" / "general"
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    stem, n = f"{datetime.date.today().isoformat()}-client-opportunities", 1
    path = out / f"{stem}.xlsx"
    while path.exists():
        n += 1
        path = out / f"{stem}-v{n}.xlsx"
    book = openpyxl.Workbook()
    book.remove(book.active)
    de.add_sheet(book, "Read me first", ["About this list"], [
        [f"Clients who may need the firm again, from dates in the open and closed files, looking {a.days} days ahead."],
        ["Each row is a prompt to review the file, not advice that the client qualifies. Check the facts before contacting anyone."],
        ["Contact only clients who agreed to hear about future services. Privacy law and anti-spam rules apply to marketing messages."],
        ["Rows with consent 'no' are left out."]], [120])
    de.add_sheet(book, "Opportunities", ["Date", "Case", "Client", "Open or closed", "Program", "Opportunity", "Why", "Service to offer", "Contact consent"],
                 [[r["when"], r["id"], r["client"], r["state"], r["program"], r["kind"], r["why"], r["service"], r["consent"]] for r in rows if r["consent"] != "no"]
                 or [["", "", "", "", "", "None found", "", "", ""]], [12, 10, 24, 10, 18, 18, 60, 40, 14])
    if errors:
        de.add_sheet(book, "Not read", ["Case folder", "Problem"], [[n_, e] for n_, e in errors], [50, 30])
    book.save(path)
    print(f"{sum(r['consent'] != 'no' for r in rows)} item(s) saved to {path}")


def cmd_consent(a):
    folder = cs.find(a.case, include_closed=True)
    text = (folder / "case.md").read_text(encoding="utf-8")
    if not re.search(r"(?m)^contact_ok:", text.split("\n---", 1)[0]):
        text = re.sub(r"\A---\n", "---\ncontact_ok:\n", text, count=1)
        (folder / "case.md").write_text(text, encoding="utf-8")
    cs.write_key(folder, "contact_ok", a.answer)
    cs.add_log(folder, f"Client consent to hear about future services: {a.answer}")
    print(f"{folder.name}: contact_ok = {a.answer}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Client opportunities in open and closed files")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("list"); x.add_argument("--days", type=int, default=WINDOW); x.add_argument("--all", action="store_true", help="include clients who said no to contact"); x.set_defaults(fn=cmd_list)
    x = s.add_parser("report"); x.add_argument("--days", type=int, default=WINDOW); x.add_argument("--out"); x.set_defaults(fn=cmd_report)
    x = s.add_parser("consent"); x.add_argument("case"); x.add_argument("answer", choices=["yes", "no"]); x.set_defaults(fn=cmd_consent)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
