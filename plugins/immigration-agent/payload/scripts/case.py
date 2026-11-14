#!/usr/bin/env python3
"""Client case file manager.

Layout (CICC Client File Management Regulation: active and closed files kept apart):
  cases/active/<YYYY-NNN-surname-program>/
  cases/closed/<YYYY-NNN-surname-program>/
  cases/closed/closed-files.csv     closed-files list with projected destruction date

Usage:
  python3 scripts/case.py new SURNAME PROGRAM [--client "Full Name"] [--opened YYYY-MM-DD]
  python3 scripts/case.py status [--days 30] [--brief]
  python3 scripts/case.py show CASE
  python3 scripts/case.py rules
  python3 scripts/case.py deadline CASE TYPE --from YYYY-MM-DD [--desc TEXT]
  python3 scripts/case.py deadline CASE custom --due YYYY-MM-DD --desc TEXT [--basis TEXT]
  python3 scripts/case.py done CASE ROW
  python3 scripts/case.py log CASE TEXT
  python3 scripts/case.py set CASE KEY VALUE
  python3 scripts/case.py close CASE [--date YYYY-MM-DD]
  python3 scripts/case.py calendar [CASE] [--details] [--out DIR]   open deadlines and expiry dates as a calendar file (.ics)

CASE is a case id (2026-001) or any text that matches one folder name.
Nothing here deletes a file. Destruction is always a manual decision.
"""
import argparse
import csv
import datetime
import hashlib
import os
import pathlib
import re
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ROOT = pathlib.Path(os.environ.get("CASES_ROOT", REPO / "cases"))
TEMPLATE = REPO / "templates" / "case-file"
RULES = pathlib.Path(__file__).resolve().parent / "deadline_rules.csv"
ACTIVE = ROOT / "active"
CLOSED = ROOT / "closed"
TODAY = datetime.date.today()
RETENTION_YEARS = 6
SUBFOLDERS = ["01-intake", "02-agreements", "03-documents", "04-advice", "05-forms-submissions", "06-correspondence", "07-billing", "client-ids"]
DEADLINE_FIELDS = ["due", "type", "description", "basis", "status"]
CLOSING_KEYS = ["fees_settled", "property_returned", "client_notified_in_writing"]
INTAKE_KEYS = {"conflict_check": "conflict check", "agreement_signed": "service agreement", "imm5476_on_file": "IMM 5476"}


def die(msg):
    sys.exit("ERROR: " + msg)


def parse_date(text, label="date"):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        die(f"{label} must be YYYY-MM-DD, got: {text}")


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not s:
        die(f"cannot build a folder name from: {text}")
    return s


def add_years(day, years):
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 February
        return day.replace(month=3, day=1, year=day.year + years)


def read_case(folder):
    text = (folder / "case.md").read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    data = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()
    return data


def write_key(folder, key, value):
    path = folder / "case.md"
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        die(f"no front matter in {path}")
    block, n = re.subn(rf"(?m)^{re.escape(key)}:.*$", lambda _: f"{key}: {value}", m.group(1))
    if n != 1:
        die(f"unknown field '{key}' in case.md")
    path.write_text("---\n" + block + "\n---" + text[m.end():], encoding="utf-8")


def folders(base):
    if not base.exists():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and (p / "case.md").exists())


def find(ref, include_closed=False):
    pool = folders(ACTIVE) + (folders(CLOSED) if include_closed else [])
    hits = [p for p in pool if p.name.startswith(ref)] or [p for p in pool if ref.lower() in p.name.lower()]
    if not hits:
        die(f"no {'' if include_closed else 'active '}case matches: {ref}")
    if len(hits) > 1:
        die(f"'{ref}' matches several cases: " + ", ".join(p.name for p in hits))
    return hits[0]


def read_deadlines(folder):
    path = folder / "deadlines.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_deadlines(folder, rows):
    with (folder / "deadlines.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, DEADLINE_FIELDS)
        w.writeheader()
        w.writerows(rows)


def add_log(folder, text, day=None):
    with (folder / "log.md").open("a", encoding="utf-8") as f:
        f.write(f"| {(day or TODAY).isoformat()} | {text.replace('|', '/')} |\n")


def load_rules():
    with RULES.open(encoding="utf-8", newline="") as f:
        return {r["type"]: r for r in csv.DictReader(f)}


def weekend_note(day):
    return f" [falls on {day.strftime('%A')}: file earlier]" if day.weekday() >= 5 else ""


def cmd_new(a):
    if not TEMPLATE.exists():
        die(f"template missing: {TEMPLATE}")
    opened = parse_date(a.opened, "--opened") if a.opened else TODAY
    used = [int(m.group(1)) for p in folders(ACTIVE) + folders(CLOSED)
            if (m := re.match(rf"{opened.year}-(\d{{3}})-", p.name))]
    case_id = f"{opened.year}-{max(used, default=0) + 1:03d}"
    dest = ACTIVE / f"{case_id}-{slug(a.surname)}-{slug(a.program)}"
    if dest.exists():
        die(f"already exists: {dest}")
    ACTIVE.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE, dest)
    for sub in SUBFOLDERS:
        (dest / sub).mkdir()
    path = dest / "case.md"
    text = path.read_text(encoding="utf-8")
    for key, val in {"{case_id}": case_id, "{client}": a.client or a.surname, "{program}": a.program, "{opened}": opened.isoformat()}.items():
        text = text.replace(key, val)
    path.write_text(text, encoding="utf-8")
    add_log(dest, "File opened", opened)
    print("Created", dest.relative_to(ROOT.parent) if ROOT.parent in dest.parents else dest)
    import conflicts
    hits, _ = conflicts.search([a.client or a.surname], dest.name)
    if hits:
        print(f"Conflict check: the client's name matches {len(hits)} name(s) in other files. Review before any work:")
        for h in hits[:5]:
            print(f"  {conflicts.STRENGTH[h['strength']]}: {h['found']} | {h['where']} | {h['file']} ({h['state']})")
    print(f"Run the full conflict check (client, spouse, sponsor, employer): conflicts.py check \"{a.client or a.surname}\" ... --case {case_id}")


def collect():
    items, gaps = [], []
    for folder in folders(ACTIVE):
        info = read_case(folder)
        rows = read_deadlines(folder)
        open_rows = [r for r in rows if r["status"].lower() != "done"]
        for r in open_rows:
            due = parse_date(r["due"], f"due date in {folder.name}")
            items.append(((due - TODAY).days, due, folder.name, r))
        miss = [label for key, label in INTAKE_KEYS.items() if info.get(key, "no").lower() != "yes"]
        if miss:
            gaps.append((folder.name, "missing: " + ", ".join(miss)))
        if not open_rows:
            gaps.append((folder.name, "no open deadline tracked"))
        if not info.get("next_action"):
            gaps.append((folder.name, "no next action set"))
    return sorted(items, key=lambda x: x[0]), gaps


def retention_due():
    path = CLOSED / "closed-files.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if parse_date(r["destroy_after"]) <= TODAY]


def cmd_status(a):
    items, gaps = collect()
    overdue = [i for i in items if i[0] < 0]
    soon = [i for i in items if 0 <= i[0] <= a.days]
    n = len(folders(ACTIVE))
    print(f"Cases: {n} active | overdue {len(overdue)} | due within {a.days} days {len(soon)} | file gaps {len(gaps)}")
    if a.brief:
        return
    for title, group in (("OVERDUE", overdue), (f"DUE WITHIN {a.days} DAYS", soon)):
        if group:
            print(f"\n{title}")
            for left, due, name, r in group:
                print(f"  {due} ({left:+d}d) {name}: {r['type']} - {r['description']}{weekend_note(due)}")
    later = [i for i in items if i[0] > a.days]
    if later:
        print(f"\nLATER: {len(later)} deadline(s). Use 'show' for detail.")
    if gaps:
        print("\nFILE GAPS")
        for name, text in gaps:
            print(f"  {name}: {text}")
    due = retention_due()
    if due:
        print("\nRETENTION PERIOD ENDED (review manually; nothing is deleted automatically)")
        for r in due:
            print(f"  {r['case_id']} {r['client']}: destroy after {r['destroy_after']}")


def cmd_show(a):
    folder = find(a.case, include_closed=True)
    print(folder.name)
    for k, v in read_case(folder).items():
        print(f"  {k}: {v}")
    print("\nDeadlines")
    for i, r in enumerate(read_deadlines(folder), 1):
        due = parse_date(r["due"])
        state = r["status"] if r["status"].lower() == "done" else f"{(due - TODAY).days:+d}d"
        print(f"  {i}. {due} [{state}] {r['type']} - {r['description']} ({r['basis']}){weekend_note(due)}")
    lines = [x for x in (folder / "log.md").read_text(encoding="utf-8").splitlines() if re.match(r"\| \d{4}-", x)]
    print("\nLast log entries")
    for x in lines[-10:]:
        print(" ", x)


def cmd_rules(_):
    print("type | days | counted from | basis | last verified")
    for r in load_rules().values():
        print(f"{r['type']} | {r['days']} | {r['counted_from']} | {r['basis']} | {r['last_verified']}")


def cmd_deadline(a):
    folder = find(a.case)
    rows = read_deadlines(folder)
    if a.type == "custom":
        if not a.due or not a.desc:
            die("custom deadlines need --due and --desc")
        due = parse_date(a.due, "--due")
        row = {"due": due.isoformat(), "type": "custom", "description": a.desc, "basis": a.basis or "manual", "status": "open"}
    else:
        rules = load_rules()
        if a.type not in rules:
            die(f"unknown type '{a.type}'. Run: case.py rules")
        if not a.start:
            die(f"--from is needed: {rules[a.type]['counted_from']}")
        rule = rules[a.type]
        due = parse_date(a.start, "--from") + datetime.timedelta(days=int(rule["days"]))
        row = {"due": due.isoformat(), "type": a.type, "description": a.desc or f"{rule['days']} days from {a.start} ({rule['counted_from']})", "basis": rule["basis"], "status": "open"}
    rows.append(row)
    write_deadlines(folder, rows)
    add_log(folder, f"Deadline added: {row['type']} due {row['due']}")
    print(f"{folder.name}: {row['type']} due {row['due']} ({(due - TODAY).days:+d}d){weekend_note(due)}")


def cmd_done(a):
    folder = find(a.case)
    rows = read_deadlines(folder)
    if not 1 <= a.row <= len(rows):
        die(f"row must be 1 to {len(rows)}")
    rows[a.row - 1]["status"] = "done"
    write_deadlines(folder, rows)
    add_log(folder, f"Deadline done: {rows[a.row - 1]['type']} {rows[a.row - 1]['due']}")
    print("Marked done:", rows[a.row - 1]["type"], rows[a.row - 1]["due"])


def cmd_log(a):
    folder = find(a.case)
    add_log(folder, a.text)
    print("Logged in", folder.name)


def cmd_set(a):
    folder = find(a.case)
    if a.key in ("case_id", "status", "closed", "destroy_after"):
        die(f"'{a.key}' is managed by this script")
    write_key(folder, a.key, a.value)
    add_log(folder, f"Set {a.key}: {a.value}")
    print(f"{folder.name}: {a.key} = {a.value}")


def cmd_close(a):
    folder = find(a.case)
    info = read_case(folder)
    missing = [k for k in CLOSING_KEYS if info.get(k, "no").lower() != "yes"]
    if missing:
        die("cannot close. CICC file rules need these set to yes first: " + ", ".join(missing))
    import billing
    try:
        problem = billing.settled_problem(folder)
    except ValueError:
        problem = "the ledger is damaged and must be repaired"
    if problem:
        die(f"cannot close. Billing: {problem} (Code s.36(1))")
    open_rows = [r for r in read_deadlines(folder) if r["status"].lower() != "done"]
    if open_rows:
        die(f"cannot close. {len(open_rows)} deadline(s) still open.")
    closed = parse_date(a.date, "--date") if a.date else TODAY
    destroy = add_years(closed, RETENTION_YEARS)
    dest = CLOSED / folder.name
    if dest.exists():
        die(f"already exists: {dest}")
    write_key(folder, "status", "closed")
    write_key(folder, "closed", closed.isoformat())
    write_key(folder, "destroy_after", destroy.isoformat())
    add_log(folder, f"File closed. Earliest destruction {destroy}", closed)
    CLOSED.mkdir(parents=True, exist_ok=True)
    index = CLOSED / "closed-files.csv"
    new = not index.exists()
    with index.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["case_id", "client", "program", "closed", "destroy_after", "folder"])
        w.writerow([info["case_id"], info["client"], info["program"], closed.isoformat(), destroy.isoformat(), folder.name])
    shutil.move(str(folder), str(dest))
    print(f"Closed {folder.name}. Keep until at least {destroy}.")


def ics_text(text):
    return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def ics_fold(line):
    """Lines of at most 75 bytes, continued with a leading space (RFC 5545 3.1)."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur)
            cur = b""
        cur += b
    out.append(cur)
    return b"\r\n ".join(out).decode("utf-8")


def calendar_events(pool, details):
    """All-day events for open deadlines and recorded expiry dates. Without details, titles hold the case id only."""
    events = []
    for folder in pool:
        info = read_case(folder)
        cid = info.get("case_id") or folder.name[:8]
        items = [(r["due"], r["type"], r["description"], r.get("basis", ""), str(i)) for i, r in enumerate(read_deadlines(folder), 1) if r["status"].lower() != "done"]
        items += [(info[k], label, label, "from the case file", k) for k, label in (("status_expiry", "status in Canada expires"), ("passport_expiry", "passport expires")) if info.get(k)]
        for due, kind, desc, basis, key in items:
            try:
                day = datetime.date.fromisoformat(due)
            except ValueError:
                continue
            summary = f"{cid}: {kind}" + (f" - {desc}" if details and desc != kind else "")
            body = (f"{folder.name}\n{desc}\nBasis: {basis}\n" if details else "Open the case file for details.\n") + "A computed date is a planning aid: confirm it against the decision or document."
            uid = hashlib.sha256(f"{folder.name}|{kind}|{key}|{due}".encode()).hexdigest()[:24] + "@immigration-agent"
            events.append((day, uid, summary, body))
    return sorted(events)


def ics(events):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Canada Immigration Agent//Deadlines//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Immigration deadlines"]
    for day, uid, summary, body in events:
        lines += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + datetime.timedelta(days=1):%Y%m%d}",
                  f"SUMMARY:{ics_text(summary)}", f"DESCRIPTION:{ics_text(body)}", "TRANSP:TRANSPARENT"]
        for before in ("P7D", "P1D"):
            lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{ics_text(summary)}", f"TRIGGER:-{before}", "END:VALARM"]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(ics_fold(x) for x in lines) + "\r\n"


def cmd_calendar(a):
    pool = [find(a.case)] if a.case else folders(ACTIVE)
    events = calendar_events(pool, a.details)
    out = pathlib.Path(a.out) if a.out else REPO / "Output" / "general"
    if out.resolve() == (REPO / "Input").resolve() or (REPO / "Input").resolve() in out.resolve().parents:
        die("refusing to write inside Input/, which is read-only")
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{TODAY.isoformat()}-deadlines-calendar"
    path, n = out / f"{stem}.ics", 1
    while path.exists():
        n += 1
        path = out / f"{stem}-v{n}.ics"
    path.write_bytes(ics(events).encode("utf-8"))
    print(f"{len(events)} date(s) from {len(pool)} file(s) saved to {path}")
    print("Import it into Outlook, Google Calendar or Apple Calendar. Each date has reminders 7 days and 1 day before.")
    print("Titles show the case id only" + ("" if not a.details else " plus the deadline description and file name: these go to your calendar provider") + ".")
    print("Importing again later adds the new dates; it doesn't remove dates you marked done, so delete those in the calendar.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Client case file manager")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("new"); x.add_argument("surname"); x.add_argument("program"); x.add_argument("--client"); x.add_argument("--opened"); x.set_defaults(fn=cmd_new)
    x = s.add_parser("status"); x.add_argument("--days", type=int, default=30); x.add_argument("--brief", action="store_true"); x.set_defaults(fn=cmd_status)
    x = s.add_parser("show"); x.add_argument("case"); x.set_defaults(fn=cmd_show)
    x = s.add_parser("rules"); x.set_defaults(fn=cmd_rules)
    x = s.add_parser("deadline"); x.add_argument("case"); x.add_argument("type"); x.add_argument("--from", dest="start"); x.add_argument("--due"); x.add_argument("--desc"); x.add_argument("--basis"); x.set_defaults(fn=cmd_deadline)
    x = s.add_parser("done"); x.add_argument("case"); x.add_argument("row", type=int); x.set_defaults(fn=cmd_done)
    x = s.add_parser("log"); x.add_argument("case"); x.add_argument("text"); x.set_defaults(fn=cmd_log)
    x = s.add_parser("set"); x.add_argument("case"); x.add_argument("key"); x.add_argument("value"); x.set_defaults(fn=cmd_set)
    x = s.add_parser("close"); x.add_argument("case"); x.add_argument("--date"); x.set_defaults(fn=cmd_close)
    x = s.add_parser("calendar"); x.add_argument("case", nargs="?"); x.add_argument("--details", action="store_true"); x.add_argument("--out"); x.set_defaults(fn=cmd_calendar)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
