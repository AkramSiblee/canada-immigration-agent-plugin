#!/usr/bin/env python3
"""Client status updates (Code of Professional Conduct s.22(3)): record what was submitted or received, then tell the client in writing.

Usage:
  python3 scripts/updates.py record CASE --kind submitted --what "Study permit application" [--party IRCC] [--date D] [--ref NUMBER] [--next "..."] [--client-action "..."]
  python3 scripts/updates.py record CASE --kind received --what "Biometrics instruction letter" [--party IRCC] ...
  python3 scripts/updates.py record CASE --kind copy-requested --what "Copy of the submitted forms"
  python3 scripts/updates.py list CASE
  python3 scripts/updates.py notify CASE [--online "how to check status"]
  python3 scripts/updates.py sent CASE ROW          (a requested copy was sent)

Guarantees:
  - Every event stays on file. Notifying never deletes anything.
  - A letter is drafted only from events not yet reported, and each event is reported once.
  - The daily alerts flag events the client hasn't been told about, and copies not yet sent.
"""
import argparse
import csv
import datetime
import os
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402
import firm  # noqa: E402

FIELDS = ["id", "date", "kind", "what", "party", "reference", "next_steps", "client_action", "notified", "letter", "recorded"]
KINDS = {"submitted": "submitted", "received": "received", "status": "status", "copy-requested": "copy requested"}
NOTIFY_SOON, NOTIFY_LATE, COPY_SOON = 2, 7, 5  # practice defaults: the Code says "timely" without a number
ONLINE = ("You can check the status of your application online: in your IRCC secure account if it was filed online, "
          "or with IRCC's online status tools using the application number above. Tell us if you see anything you don't expect.")
NEEDS_DEADLINE = r"biometric|procedural fairness|medical|request|additional document|refus|interview|passport request|decision"


def today():
    return datetime.date.today()


def die(msg):
    sys.exit(f"NOT RECORDED: {msg}")


def path_of(folder):
    return folder / "updates.csv"


def load(folder):
    p = path_of(folder)
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save(folder, rows):
    fd, tmp = tempfile.mkstemp(dir=str(folder), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    de.replace_with_retry(tmp, path_of(folder))


def sentence(r):
    when = r["date"]
    ref = f" Reference: {r['reference']}." if r["reference"] else ""
    if r["kind"] == "submitted":
        return f"On {when}, we submitted {r['what']} to {r['party'] or 'IRCC'}.{ref}"
    if r["kind"] == "received":
        return f"On {when}, we received {r['what']} from {r['party'] or 'IRCC'} for you.{ref}"
    return f"{when}: {r['what']}{ref}"


def cmd_record(a):
    folder = de.active_case(a.case)
    what = (a.what or "").strip()
    if len(what) < 3:
        die("say what was submitted or received (--what)")
    day = cs.parse_date(a.date, "--date") if a.date else today()
    if day > today():
        die("the date can't be in the future")
    rows = load(folder)
    row = {k: "" for k in FIELDS}
    row.update(id=str(max((int(r["id"]) for r in rows), default=0) + 1), date=day.isoformat(), kind=a.kind, what=what, party=a.party or "",
               reference=a.ref or "", next_steps=a.next or "", client_action=a.client_action or "", recorded=datetime.datetime.now().isoformat(timespec="seconds"))
    rows.append(row)
    save(folder, rows)
    cs.add_log(folder, f"{KINDS[a.kind].capitalize()}: {what}" + (f" ({a.party})" if a.party else ""), day)
    print(f"Recorded as event {row['id']}.")
    if a.kind == "copy-requested":
        print(f"Send the copy, then run: updates.py sent {a.case} {row['id']} (s.22(3)(b))")
    else:
        print(f"Tell the client with: updates.py notify {a.case}")
    if a.kind == "received" and re.search(NEEDS_DEADLINE, what, re.I):
        print("This may start a time limit. Add it: case.py rules, then case.py deadline CASE TYPE --from DATE (use the date it was received)")


def cmd_list(a):
    folder = de.active_case(a.case)
    rows = load(folder)
    if not rows:
        print("No events recorded.")
    for r in rows:
        status = f"told client {r['notified']}" if r["notified"] else ("copy sent" if r["kind"] == "copy-requested" and r["letter"] else "NOT YET TOLD")
        print(f"{r['id']:>3}  {r['date']}  {KINDS.get(r['kind'], r['kind']):14}  {r['what'][:50]:50}  {status}")


def cmd_notify(a):
    folder = de.active_case(a.case)
    rows = load(folder)
    pending = [r for r in rows if not r["notified"] and r["kind"] != "copy-requested"]
    if not pending:
        sys.exit("NOT PRODUCED: nothing new to report. Record an event first")
    terms = {"events": [sentence(r) for r in pending],
             "next_steps": [r["next_steps"] for r in pending if r["next_steps"]],
             "client_actions": [r["client_action"] for r in pending if r["client_action"]],
             "online_access": a.online or ONLINE}
    path, _ = firm.draft("status-update", folder, terms, a.out)
    for r in pending:
        r["notified"], r["letter"] = today().isoformat(), path.name
    save(folder, rows)
    print(f"Drafted: {path.name} ({len(pending)} event(s))")
    print("Saved in:", path.parent)
    print("  - Send it promptly, by a secure method. If you don't send it, delete the file and clear the 'notified' date.")


def cmd_sent(a):
    folder = de.active_case(a.case)
    rows = load(folder)
    row = next((r for r in rows if r["id"] == a.row and r["kind"] == "copy-requested"), None)
    if not row:
        die(f"event {a.row} isn't a copy request on this file")
    if row["letter"]:
        die("this copy is already marked as sent")
    row["letter"], row["notified"] = f"copy sent {today().isoformat()}", today().isoformat()
    save(folder, rows)
    cs.add_log(folder, f"Copy sent to client: {row['what']}")
    print(f"Marked as sent: {row['what']}")


def issues(folder, now):
    """Alerts for one case: (rank, kind, tier, text, step, day)."""
    out = []
    for r in load(folder):
        try:
            day = datetime.date.fromisoformat(r["date"])
        except ValueError:
            out.append((1, "Client update", "unreadable", f"Event {r['id']} has an unreadable date", "Correct it in updates.csv", None))
            continue
        age = (now - day).days
        if r["kind"] == "copy-requested":
            if not r["letter"] and age >= COPY_SOON:
                out.append((2, "Client update", "copy", f"Copy requested {age} days ago and not sent: {r['what']}", f"Send it, then run updates.py sent CASE {r['id']}", day))
        elif not r["notified"] and age >= NOTIFY_SOON:
            rank = 1 if age >= NOTIFY_LATE else 2
            out.append((rank, "Client update", "late" if rank == 1 else "due", f"Client not told yet ({age} days): {KINDS.get(r['kind'], r['kind'])} {r['what']}", "Run updates.py notify CASE (s.22(3))", day))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Client status updates")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("record"); x.add_argument("case"); x.add_argument("--kind", required=True, choices=list(KINDS)); x.add_argument("--what", required=True)
    x.add_argument("--party"); x.add_argument("--date"); x.add_argument("--ref"); x.add_argument("--next"); x.add_argument("--client-action"); x.set_defaults(fn=cmd_record)
    x = s.add_parser("list"); x.add_argument("case"); x.set_defaults(fn=cmd_list)
    x = s.add_parser("notify"); x.add_argument("case"); x.add_argument("--online"); x.add_argument("--out"); x.set_defaults(fn=cmd_notify)
    x = s.add_parser("sent"); x.add_argument("case"); x.add_argument("row"); x.set_defaults(fn=cmd_sent)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
