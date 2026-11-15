#!/usr/bin/env python3
"""Staff tasks and the licensee's review sign-off (CICC Code s.38: you supervise those who assist you and stay responsible).

Usage:
  python3 scripts/tasks.py staff add "Name" --role rcic|assistant [--licence R123456]
  python3 scripts/tasks.py staff list
  python3 scripts/tasks.py add CASE "Prepare IMM 5257 worksheet" --to NAME [--due YYYY-MM-DD]
  python3 scripts/tasks.py done CASE ID --by NAME [--note TEXT]
  python3 scripts/tasks.py list [--who NAME] [--case CASE] [--all]
  python3 scripts/tasks.py review CASE FILE --by NAME [--note TEXT]        ask the licensee to review a prepared document
  python3 scripts/tasks.py approve CASE ID --by NAME [--note TEXT]         licensee signs off (the file must be unchanged)
  python3 scripts/tasks.py return CASE ID --by NAME --note "what to fix"   licensee sends it back
  python3 scripts/tasks.py reviews [--case CASE]

Guarantees:
  - Staff are kept in cases/staff.csv; each case keeps tasks.csv and reviews.csv (add-only history in the case log).
  - Only a person on the staff list with role "rcic" can approve. A review records the document's fingerprint: if the file
    changes after it was sent for review, approval is refused until it is sent again.
  - Pending reviews and overdue tasks show in the daily alerts, the dashboard and the readiness report. A readiness report
    lists any prepared document still waiting for the licensee's review as something to fix before filing.
"""
import argparse
import csv
import datetime
import hashlib
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

STAFF = cs.ROOT / "staff.csv"
STAFF_FIELDS = ["name", "role", "licence", "added"]
TASK_FIELDS = ["id", "created", "task", "assigned", "due", "status", "done_by", "done_on", "note"]
REVIEW_FIELDS = ["id", "requested", "file", "sha256", "prepared_by", "status", "reviewer", "decided", "note"]
REVIEW_LATE = 2  # days before a pending review shows as late (practice default)


def die(msg):
    sys.exit("NOT RECORDED: " + msg)


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(path, fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fields)
    w.writeheader()
    w.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    de.atomic_write(path, buf.getvalue())


def staff():
    return {r["name"].lower(): r for r in read(STAFF)}


def person(name, role=None):
    p = staff().get((name or "").strip().lower())
    if not p:
        die(f"'{name}' isn't on the staff list. Add them: tasks.py staff add \"{name}\" --role assistant|rcic")
    if role and p["role"] != role:
        die(f"{p['name']} is recorded as {p['role']}: only a licensee (role rcic) can do this")
    return p


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_staff(a):
    if a.action == "add":
        if not a.name or not a.role:
            die("give the name and --role")
        rows = [r for r in read(STAFF) if r["name"].lower() != a.name.strip().lower()]
        rows.append({"name": a.name.strip(), "role": a.role, "licence": a.licence or "", "added": datetime.date.today().isoformat()})
        cs.ROOT.mkdir(parents=True, exist_ok=True)
        write(STAFF, STAFF_FIELDS, rows)
        print(f"Staff: {a.name.strip()} ({a.role})")
    for r in read(STAFF):
        if a.action == "list":
            print(f"{r['name']:24} {r['role']:10} {r['licence']}")


def cmd_add(a):
    folder = de.active_case(a.case)
    who = person(a.to)
    rows = read(folder / "tasks.csv")
    due = cs.parse_date(a.due, "--due").isoformat() if a.due else ""
    row = {"id": str(len(rows) + 1), "created": datetime.date.today().isoformat(), "task": a.task.strip(), "assigned": who["name"], "due": due, "status": "open",
           "done_by": "", "done_on": "", "note": ""}
    rows.append(row)
    write(folder / "tasks.csv", TASK_FIELDS, rows)
    cs.add_log(folder, f"Task {row['id']} for {who['name']}: {row['task']}" + (f" (due {due})" if due else ""))
    print(f"Task {row['id']} on {folder.name} for {who['name']}" + (f", due {due}" if due else ""))


def cmd_done(a):
    folder = de.active_case(a.case)
    who = person(a.by)
    rows = read(folder / "tasks.csv")
    r = next((x for x in rows if x["id"] == a.id), None)
    if not r:
        die(f"no task {a.id} on this file")
    r.update(status="done", done_by=who["name"], done_on=datetime.date.today().isoformat(), note=a.note or r["note"])
    write(folder / "tasks.csv", TASK_FIELDS, rows)
    cs.add_log(folder, f"Task {a.id} done by {who['name']}: {r['task']}")
    print(f"Done: {r['task']}")


def all_tasks(case=None):
    pool = [de.active_case(case)] if case else cs.folders(cs.ACTIVE)
    for folder in pool:
        for r in read(folder / "tasks.csv"):
            yield folder, r


def cmd_list(a):
    today = datetime.date.today().isoformat()
    n = 0
    for folder, r in sorted(all_tasks(a.case), key=lambda x: (x[1]["due"] or "9999", x[0].name)):
        if (r["status"] == "done" and not a.all) or (a.who and r["assigned"].lower() != a.who.lower()):
            continue
        n += 1
        late = " OVERDUE" if r["status"] != "done" and r["due"] and r["due"] < today else ""
        print(f"{folder.name[:8]} #{r['id']:3} {r['assigned'][:16]:16} {r['due'] or '—':10} {r['status']:5} {r['task'][:60]}{late}")
    if not n:
        print("No open tasks.")


def cmd_review(a):
    folder = de.active_case(a.case)
    who = person(a.by)
    path = pathlib.Path(a.file)
    if not path.is_absolute():
        path = folder / a.file
    if not path.is_file():
        die(f"no such file: {path}")
    try:
        rel = path.resolve().relative_to(folder.resolve()).as_posix()
    except ValueError:
        die("the document must be inside the case folder")
    rows = read(folder / "reviews.csv")
    row = {"id": str(len(rows) + 1), "requested": datetime.date.today().isoformat(), "file": rel, "sha256": fingerprint(path), "prepared_by": who["name"],
           "status": "pending", "reviewer": "", "decided": "", "note": a.note or ""}
    rows.append(row)
    write(folder / "reviews.csv", REVIEW_FIELDS, rows)
    cs.add_log(folder, f"Sent for review by {who['name']}: {rel}")
    print(f"Review {row['id']} requested: {rel}")


def decide(a, status):
    folder = de.active_case(a.case)
    who = person(a.by, role="rcic")
    rows = read(folder / "reviews.csv")
    r = next((x for x in rows if x["id"] == a.id), None)
    if not r:
        die(f"no review {a.id} on this file")
    if r["status"] != "pending":
        die(f"review {a.id} is already {r['status']}")
    path = folder / r["file"]
    if status == "approved":
        if not path.is_file():
            die(f"the document is gone: {r['file']}")
        if fingerprint(path) != r["sha256"]:
            die("the document changed after it was sent for review. Review the new version: tasks.py review CASE FILE --by NAME")
    if status == "returned" and not a.note:
        die("say what needs fixing (--note)")
    r.update(status=status, reviewer=who["name"], decided=datetime.date.today().isoformat(), note=a.note or r["note"])
    write(folder / "reviews.csv", REVIEW_FIELDS, rows)
    cs.add_log(folder, f"Review {a.id} {status} by {who['name']}: {r['file']}" + (f" ({a.note})" if a.note else ""))
    print(f"Review {a.id} {status}: {r['file']}")


def cmd_reviews(a):
    pool = [de.active_case(a.case)] if a.case else cs.folders(cs.ACTIVE)
    n = 0
    for folder in pool:
        for r in read(folder / "reviews.csv"):
            if r["status"] == "pending" or a.case:
                n += 1
                print(f"{folder.name[:8]} #{r['id']} {r['status']:8} {r['requested']} {r['prepared_by'][:14]:14} {r['file']}" + (f" ({r['reviewer']} {r['decided']})" if r["reviewer"] else ""))
    if not n:
        print("No reviews waiting.")


def approved(folder, rel):
    """True when this exact version of a document was approved."""
    path = folder / rel
    if not path.is_file():
        return False
    digest = fingerprint(path)
    return any(r["file"] == rel and r["status"] == "approved" and r["sha256"] == digest for r in read(folder / "reviews.csv"))


def issues(folder, today):
    """Alerts for one case: (rank, kind, tier, text, step, day)."""
    out = []
    for r in read(folder / "reviews.csv"):
        if r["status"] != "pending":
            continue
        try:
            age = (today - datetime.date.fromisoformat(r["requested"])).days
        except ValueError:
            age = 0
        changed = (folder / r["file"]).is_file() and fingerprint(folder / r["file"]) != r["sha256"]
        out.append((2 if age >= REVIEW_LATE else 3, "Review", "pending", f"Waiting for the licensee's review ({age} days): {r['file']}, prepared by {r['prepared_by']}"
                    + (" - changed since it was sent: send it again" if changed else ""), f"tasks.py approve CASE {r['id']} --by NAME, or return it with a note", None))
    for r in read(folder / "tasks.csv"):
        if r["status"] != "done" and r["due"]:
            try:
                due = datetime.date.fromisoformat(r["due"])
            except ValueError:
                continue
            if due < today:
                out.append((2, "Task", "overdue", f"Task for {r['assigned']} overdue since {due}: {r['task']}", f"Finish it (tasks.py done CASE {r['id']} --by NAME) or change the due date", due))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Staff tasks and review sign-off")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("staff"); x.add_argument("action", choices=["add", "list"]); x.add_argument("name", nargs="?"); x.add_argument("--role", choices=["rcic", "assistant"]); x.add_argument("--licence"); x.set_defaults(fn=cmd_staff)
    x = s.add_parser("add"); x.add_argument("case"); x.add_argument("task"); x.add_argument("--to", required=True); x.add_argument("--due"); x.set_defaults(fn=cmd_add)
    x = s.add_parser("done"); x.add_argument("case"); x.add_argument("id"); x.add_argument("--by", required=True); x.add_argument("--note"); x.set_defaults(fn=cmd_done)
    x = s.add_parser("list"); x.add_argument("--who"); x.add_argument("--case"); x.add_argument("--all", action="store_true"); x.set_defaults(fn=cmd_list)
    x = s.add_parser("review"); x.add_argument("case"); x.add_argument("file"); x.add_argument("--by", required=True); x.add_argument("--note"); x.set_defaults(fn=cmd_review)
    x = s.add_parser("approve"); x.add_argument("case"); x.add_argument("id"); x.add_argument("--by", required=True); x.add_argument("--note"); x.set_defaults(fn=lambda a: decide(a, "approved"))
    x = s.add_parser("return"); x.add_argument("case"); x.add_argument("id"); x.add_argument("--by", required=True); x.add_argument("--note"); x.set_defaults(fn=lambda a: decide(a, "returned"))
    x = s.add_parser("reviews"); x.add_argument("--case"); x.set_defaults(fn=cmd_reviews)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
