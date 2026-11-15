#!/usr/bin/env python3
"""Document validity tracker: language tests, ECAs, medicals, police certificates, Express Entry profiles and ITAs.

Each of these documents is only good for a set time from its own date (test date, issue date, exam date). This tracks
that date for each person in the case, and warns before a document runs out or would run out before the planned filing
or landing date.

Usage:
  python3 scripts/validity.py rules
  python3 scripts/validity.py add CASE DOC --date YYYY-MM-DD [--person NAME] [--note TEXT]
  python3 scripts/validity.py plan CASE [--file-by YYYY-MM-DD] [--land-by YYYY-MM-DD]
  python3 scripts/validity.py import CASE            add test, ECA, police and ITA dates found by /extract (as drafts to confirm)
  python3 scripts/validity.py show CASE

DOC is one of the types listed by 'rules' (language_test, eca, medical, police_current, ee_profile, ita).

Guarantees:
  - Rules come from templates/validity-rules.csv, each with its knowledge file and the date it was last checked.
  - validity.csv in the case is add-only: a newer date for the same person and document replaces the old one in the
    checks, and the old row stays on file.
  - The daily alerts and the dashboard use issues(), so all three agree.
  - Dates are planning aids. A program, province or visa office can set a different rule: check the instructions for
    the application at hand.
"""
import argparse
import csv
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

RULES = de.REPO / "templates" / "validity-rules.csv"
FIELDS = ["id", "person", "doc", "date", "note", "recorded"]
PLAN = {"plan_filing": "planned filing date", "plan_landing": "planned landing or entry date"}
SOON_DAYS, URGENT_DAYS = 90, 30
FROM_EXTRACTION = {"language_test": ("language_test", "test_date"), "credential_assessment": ("eca", "assessment_date"),
                   "police_certificate": ("police_current", "issue_date"), "invitation_to_apply": ("ita", "invitation_date")}


def die(msg):
    sys.exit("NOT RECORDED: " + msg)


def rules():
    with RULES.open(encoding="utf-8", newline="") as f:
        return {r["doc"]: r for r in csv.DictReader(f)}


def add_months(day, months):
    m = day.month - 1 + months
    y, m = day.year + m // 12, m % 12 + 1
    for d in (day.day, 30, 29, 28):
        try:
            return datetime.date(y, m, d)
        except ValueError:
            continue


def valid_until(rule, start):
    """Last day the document is good, from its own date."""
    if rule["months"]:
        return add_months(start, int(rule["months"])) - datetime.timedelta(days=1)
    return start + datetime.timedelta(days=int(rule["days"]))


def path_of(folder):
    return folder / "validity.csv"


def load(folder):
    p = path_of(folder)
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append(folder, person, doc, day, note):
    rows = load(folder)
    row = {"id": str(max((int(r["id"]) for r in rows), default=0) + 1), "person": person, "doc": doc, "date": day.isoformat(), "note": note,
           "recorded": datetime.datetime.now().isoformat(timespec="seconds")}
    p = path_of(folder)
    new = not p.exists()
    with p.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    return row


def current(folder):
    """Latest row per (person, doc), and the plan dates."""
    latest, plan = {}, {}
    for r in load(folder):
        try:
            day = datetime.date.fromisoformat(r["date"])
        except ValueError:
            continue
        if r["doc"] in PLAN:
            plan[r["doc"]] = day
        else:
            latest[(r["person"].strip().lower(), r["doc"])] = {**r, "day": day}
    return list(latest.values()), plan


def status(folder, today=None):
    """One dict per tracked document: label, person, from, until, left, problem (or '')."""
    today = today or datetime.date.today()
    table, out = rules(), []
    items, plan = current(folder)
    for r in sorted(items, key=lambda r: (r["doc"], r["person"])):
        rule = table.get(r["doc"])
        if not rule:
            continue
        until = valid_until(rule, r["day"])
        need = plan.get("plan_filing") if rule["checked_at"] == "filing" else plan.get("plan_landing") if rule["checked_at"] == "landing" else None
        problem = ""
        if until < today:
            problem = "expired"
        elif need and until < need:
            problem = f"runs out before the {PLAN['plan_filing' if rule['checked_at'] == 'filing' else 'plan_landing']} ({need})"
        out.append({"doc": r["doc"], "label": rule["label"], "person": r["person"], "from": r["day"], "until": until, "left": (until - today).days,
                    "rule": rule, "need": need, "problem": problem, "note": r["note"]})
    return out, plan


def issues(folder, today):
    """Alerts for one case: (rank, kind, tier, text, step, day)."""
    out = []
    try:
        rows, _ = status(folder, today)
    except (OSError, ValueError, KeyError) as e:
        return [(1, "Validity", "unreadable", f"Could not check document validity ({type(e).__name__})", "Check validity.csv in the case folder", None)]
    tracked = {r.get("type", "") for r in cs.read_deadlines(folder) if r.get("status", "").lower() != "done"}
    for r in rows:
        if r["doc"] == "ita" and tracked & {"ee-ita-60", "ircc-ita"}:
            continue  # already tracked as a deadline
        who = f" of {r['person']}" if r["person"] else ""
        what = f"{r['label']}{who}"
        if r["problem"] == "expired":
            out.append((1, "Validity", "expired", f"{what} is no longer valid (since {r['until']}): {r['rule']['must_be_valid']}",
                        "Get a new one before filing, or confirm it is no longer needed", r["until"]))
        elif r["problem"]:
            out.append((1, "Validity", "before plan", f"{what} {r['problem']}: {r['rule']['must_be_valid']}",
                        "File earlier, or get a new one in time", r["until"]))
        elif r["left"] <= URGENT_DAYS:
            out.append((1, "Validity", "30 days", f"{what} runs out on {r['until']}", "Plan the filing or a new one now", r["until"]))
        elif r["left"] <= SOON_DAYS:
            out.append((2, "Validity", "90 days", f"{what} runs out on {r['until']}", "Check the filing will happen before then, or book a new one", r["until"]))
    return out


def cmd_rules(_):
    for doc, r in rules().items():
        span = f"{r['months']} months" if r["months"] else f"{r['days']} days"
        print(f"{doc:15} {r['label']}: {span} from the {r['counted_from']}. {r['must_be_valid'].capitalize()}.")
        print(f"{'':15} Source: {r['basis']} ({r['knowledge_file']}, checked {r['last_verified']}, confidence {r['confidence']})")


def cmd_add(a):
    folder = de.active_case(a.case)
    if a.doc not in rules():
        die(f"unknown document '{a.doc}'. Run: validity.py rules")
    day = cs.parse_date(a.date, "--date")
    if day > datetime.date.today():
        die("the date can't be in the future (use the test, issue or exam date)")
    row = append(folder, (a.person or "").strip(), a.doc, day, a.note or "")
    rule = rules()[a.doc]
    until = valid_until(rule, day)
    cs.add_log(folder, f"Validity: {rule['label']}{' of ' + row['person'] if row['person'] else ''} dated {day}, good until {until}")
    print(f"Recorded: {rule['label']}{' of ' + row['person'] if row['person'] else ''}, dated {day}. Good until {until} ({(until - datetime.date.today()).days:+d} days).")


def cmd_plan(a):
    folder = de.active_case(a.case)
    if not a.file_by and not a.land_by:
        die("give --file-by and/or --land-by")
    for key, text in (("plan_filing", a.file_by), ("plan_landing", a.land_by)):
        if text:
            append(folder, "", key, cs.parse_date(text, key), "")
            cs.add_log(folder, f"Validity: {PLAN[key]} set to {text}")
    show(folder)


def cmd_import(a):
    import form_prefill as fp
    folder = de.active_case(a.case)
    path = fp.latest_report(folder / "03-documents" / "_extraction")
    if not path:
        die("no document extraction found for this case. Run /extract first")
    have = {(r["person"].strip().lower(), r["doc"], r["date"]) for r in load(folder)}
    added = 0
    for d in json.loads(path.read_text(encoding="utf-8")).get("documents", []):
        if d.get("doc_type") not in FROM_EXTRACTION:
            continue
        doc, key = FROM_EXTRACTION[d["doc_type"]]
        f = next((f for f in d.get("fields", []) if f.get("field") == key), None)
        try:
            day = datetime.date.fromisoformat(str(f["value"])) if f else None
        except ValueError:
            day = None
        if not day:
            continue
        who = de.doc_name(d) or ""
        if (who.strip().lower(), doc, day.isoformat()) in have:
            continue
        append(folder, who, doc, day, f"read from {d.get('file', '')}: confirm against the original")
        added += 1
    print(f"Added {added} date(s) from {path.name}. They are drafts: check each against the document.")
    show(folder)


def show(folder):
    rows, plan = status(folder)
    for key, label in PLAN.items():
        if key in plan:
            print(f"{label.capitalize()}: {plan[key]}")
    if not rows:
        print("No documents tracked yet. Add one: validity.py add CASE DOC --date YYYY-MM-DD --person NAME")
        return
    print(f"{'Document':48} {'Person':22} {'Dated':10}  {'Good until':10}  Days  Problem")
    for r in rows:
        print(f"{r['label'][:48]:48} {r['person'][:22]:22} {r['from']}  {r['until']}  {r['left']:+5d}  {r['problem']}")
    if not plan:
        print("No planned filing or landing date: add one with 'validity.py plan CASE --file-by D' to check documents against it.")


def cmd_show(a):
    show(de.active_case(a.case))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Document validity tracker")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("rules"); x.set_defaults(fn=cmd_rules)
    x = s.add_parser("add"); x.add_argument("case"); x.add_argument("doc"); x.add_argument("--date", required=True); x.add_argument("--person"); x.add_argument("--note"); x.set_defaults(fn=cmd_add)
    x = s.add_parser("plan"); x.add_argument("case"); x.add_argument("--file-by"); x.add_argument("--land-by"); x.set_defaults(fn=cmd_plan)
    x = s.add_parser("import"); x.add_argument("case"); x.set_defaults(fn=cmd_import)
    x = s.add_parser("show"); x.add_argument("case"); x.set_defaults(fn=cmd_show)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
