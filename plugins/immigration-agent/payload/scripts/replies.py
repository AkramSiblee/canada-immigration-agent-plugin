#!/usr/bin/env python3
"""Facts for answering a client's "what's happening with my file?" message, from the case file only.

Usage:
  python3 scripts/replies.py find "email@example.com or a name"     which open case a sender belongs to
  python3 scripts/replies.py facts CASE                              the facts a reply can rely on (changes nothing)
  python3 scripts/replies.py log CASE --summary "Replied: still in process, sent passport request steps" [--date D]

Guarantees:
  - Facts come only from the case file: events (updates.csv), open deadlines, client actions not yet done, checklist items still
    missing, the processing time tracked with ptimes.py, and the next action. Nothing is guessed, and no outcome or date is promised.
  - Nothing is sent. Claude drafts the reply (as a Gmail draft when Gmail is connected) for you to read and send yourself.
  - 'log' records the reply in the case log, so the file shows every communication.
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


def die(msg):
    sys.exit("ERROR: " + msg)


def emails(folder):
    p = folder / "client-facts.csv"
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return sorted({r["value"].strip().lower() for r in csv.DictReader(f) if r.get("key", "").lower() in ("email", "email_address", "client_email") and r.get("value")})


def cmd_find(a):
    import conflicts
    q = a.who.strip().lower()
    hits = []
    for folder in cs.folders(cs.ACTIVE):
        info = cs.read_case(folder)
        if "@" in q and q in emails(folder):
            hits.append((folder, "email on file"))
        elif "@" not in q and info.get("client") and conflicts.score(a.who, info["client"]) >= 2:
            hits.append((folder, f"name matches {info['client']}"))
    if not hits:
        print("No open case matches. Check the sender against the client facts before replying." + (" (Email addresses are matched only against client-facts.csv.)" if "@" in q else ""))
    for f, why in hits:
        print(f"{f.name} ({why})")
    if len(hits) > 1:
        print("More than one match: confirm which file before replying.")


def facts(folder, today=None):
    import ptimes
    import readiness as rd
    import updates as up
    today = today or datetime.date.today()
    info = cs.read_case(folder)
    out = {"case": info.get("case_id", folder.name[:8]), "client": info.get("client", ""), "program": info.get("program", ""),
           "language": info.get("client_language", ""), "emails": emails(folder), "next_action": info.get("next_action", "")}
    events = up.load(folder)
    out["events"] = [f"{e['date']}: {e['kind']} {e['what']}" + (f" (ref {e['reference']})" if e["reference"] else "") + ("" if e["notified"] or e["kind"] == "copy-requested" else " [client not told yet]")
                     for e in events[-6:]]
    out["client_actions"] = [e["client_action"] for e in events if e["client_action"]][-4:]
    out["deadlines"] = [f"{r['due']}: {r['description']}" for r in cs.read_deadlines(folder) if r.get("status", "").lower() != "done" and r.get("due", "") >= (today - datetime.timedelta(days=30)).isoformat()]
    try:
        cl, rows = rd.case_checklist(folder)
        out["missing"] = [r["item"] for r in rows if r["status"] == rd.MISSING] if cl else []
    except Exception:
        out["missing"] = []
    try:
        r = ptimes.status(folder)
    except Exception:
        r = None
    out["processing"] = ptimes.describe(r) + (" (past IRCC's posted time)" if r["past"] else "") if r else ""
    log = folder / "log.md"
    lines = [x for x in log.read_text(encoding="utf-8").splitlines() if re.match(r"\| \d{4}-", x)] if log.exists() else []
    out["last_contact"] = lines[-1] if lines else ""
    return out


def cmd_facts(a):
    f = facts(cs.find(a.case))
    print(f"Case {f['case']}: {f['client']} ({f['program']})" + (f" | client's language: {f['language']}" if f["language"] else ""))
    print("Email on file: " + (", ".join(f["emails"]) or "none recorded"))
    for title, key in (("Recent events", "events"), ("Waiting on the client", "client_actions"), ("Open deadlines", "deadlines"), ("Documents still missing", "missing")):
        print(f"\n{title}:")
        print("\n".join(f"  - {x}" for x in f[key]) if f[key] else "  - none")
    print(f"\nProcessing time: {f['processing'] or 'not tracked (ptimes.py set CASE --line ...)'}")
    print(f"Next action: {f['next_action'] or 'not set'}")
    print(f"Last log entry: {f['last_contact'] or 'none'}")
    if any("[client not told yet]" in e for e in f["events"]):
        print("\nSome news hasn't been reported to the client yet: report it in this reply, then run updates.py notify or mark it.")


def cmd_log(a):
    folder = cs.find(a.case)
    if len(a.summary.split()) < 3:
        die("give a short summary of the reply")
    day = cs.parse_date(a.date, "--date") if a.date else datetime.date.today()
    cs.add_log(folder, f"Client message answered: {a.summary}", day)
    print(f"Logged in {folder.name}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Facts for client replies")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("find"); x.add_argument("who"); x.set_defaults(fn=cmd_find)
    x = s.add_parser("facts"); x.add_argument("case"); x.set_defaults(fn=cmd_facts)
    x = s.add_parser("log"); x.add_argument("case"); x.add_argument("--summary", required=True); x.add_argument("--date"); x.set_defaults(fn=cmd_log)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
