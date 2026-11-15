#!/usr/bin/env python3
"""Prospect pipeline: enquiries, paid consultations, quotes and sign-ups, with where prospects drop off.

Usage:
  python3 scripts/prospects.py add "Full Name" [--source referral|website|social|walk-in|...] [--program TEXT] [--contact TEXT] [--note TEXT] [--date D]
  python3 scripts/prospects.py move ID STAGE [--date D] [--fee 150] [--amount 3500] [--reason TEXT] [--case CASE] [--note TEXT]
  python3 scripts/prospects.py list [--stage STAGE] [--all]
  python3 scripts/prospects.py show ID
  python3 scripts/prospects.py report [--from D] [--to D] [--out DIR]

Stages, in order: enquiry, booked (consultation booked, --fee), paid (consultation fee received, --amount), consulted, quoted (--amount),
signed (service agreement signed, --case), and the endings: declined (the prospect said no), not-taken (you said no), no-show, lost (no reply).

Guarantees:
  - Prospects are kept in cases/prospects/ (backed up with the cases, never touched by updates). Every change is also written to
    history.csv, which is add-only.
  - Adding a prospect runs the conflict check against every open and closed file and the other-parties list (Code ss.15-18).
  - The CICC Code needs a written consultation agreement before the consultation (s.23). Moving to "booked" reminds you.
  - A consultation fee paid before the consultation is an advance payment: it goes to the client account (Code s.32(a)).
  - A prospect you decline gets a non-engagement letter, and is added to the other-parties list for future conflict checks.
"""
import argparse
import csv
import datetime
import pathlib
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

DIR = cs.ROOT / "prospects"
FILE = DIR / "prospects.csv"
HISTORY = DIR / "history.csv"
NOTES = DIR / "notes"
FIELDS = ["id", "name", "contact", "source", "program", "stage", "enquiry", "booked", "paid", "consulted", "quoted", "signed", "closed",
          "fee", "paid_amount", "quote", "case", "reason", "note"]
OPEN = ["enquiry", "booked", "paid", "consulted", "quoted"]
ENDS = ["signed", "declined", "not-taken", "no-show", "lost"]
STAGES = OPEN + ENDS
FUNNEL = ["enquiry", "booked", "paid", "consulted", "quoted", "signed"]
STALE = {"enquiry": 3, "booked": 0, "paid": 0, "consulted": 3, "quoted": 7}  # days before a follow-up is due (practice defaults)


def die(msg):
    sys.exit("NOT RECORDED: " + msg)


def load():
    if not FILE.exists():
        return []
    with FILE.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save(rows):
    DIR.mkdir(parents=True, exist_ok=True)
    text_rows = [{k: r.get(k, "") for k in FIELDS} for r in rows]
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS)
    w.writeheader()
    w.writerows(text_rows)
    de.atomic_write(FILE, buf.getvalue())


def history(pid, stage, day, detail):
    DIR.mkdir(parents=True, exist_ok=True)
    new = not HISTORY.exists()
    with HISTORY.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["id", "stage", "date", "detail", "recorded"])
        w.writerow([pid, stage, day.isoformat(), detail, datetime.datetime.now().isoformat(timespec="seconds")])


def get(ref):
    hits = [r for r in load() if r["id"] == ref.upper() or ref.lower() in r["name"].lower()]
    if len(hits) != 1:
        die(f"'{ref}' matches {len(hits)} prospect(s)")
    return hits[0]


def money(text, label):
    try:
        v = Decimal(str(text).replace(",", "").replace("$", ""))
    except InvalidOperation:
        die(f"{label} must be an amount such as 150")
    if v < 0:
        die(f"{label} can't be negative")
    return v.quantize(Decimal("0.01"))


def when(text):
    day = cs.parse_date(text, "--date") if text else datetime.date.today()
    if day > datetime.date.today() + datetime.timedelta(days=365):
        die("that date is too far ahead")
    return day


def cmd_add(a):
    import conflicts
    name = a.name.strip()
    if len(name) < 3:
        die("give the prospect's full name")
    hits, _ = conflicts.search([name], None)  # before saving, so the new prospect doesn't match itself
    rows = load()
    pid = f"L{max((int(r['id'][1:]) for r in rows if r['id'][1:].isdigit()), default=0) + 1:03d}"
    day = when(a.date)
    rows.append({"id": pid, "name": name, "contact": a.contact or "", "source": (a.source or "").lower(), "program": a.program or "", "stage": "enquiry",
                 "enquiry": day.isoformat(), "note": a.note or ""})
    save(rows)
    history(pid, "enquiry", day, a.note or "")
    print(f"Added {pid}: {name}")
    if hits:
        print(f"Conflict check: {len(hits)} possible match(es). Review before booking (Code ss.15-18):")
        for h in hits[:5]:
            print(f"  {conflicts.STRENGTH[h['strength']]}: {h['found']} | {h['where']} | {h['file']} ({h['state']})")
    else:
        print("Conflict check: no recorded name matched. Check the spouse, sponsor or employer too before acting: conflicts.py check ...")


def cmd_move(a):
    if a.stage not in STAGES:
        die("stage must be one of: " + ", ".join(STAGES))
    rows = load()
    r = next((x for x in rows if x["id"] == get(a.id)["id"]), None)
    if r["stage"] in ENDS and a.stage in OPEN:
        print(f"Reopening {r['id']} (was {r['stage']}).")
        r["closed"] = r["reason"] = ""
    day = when(a.date)
    detail = []
    if a.stage == "booked":
        if a.fee is not None:
            r["fee"] = str(money(a.fee, "--fee"))
            detail.append(f"fee {r['fee']}")
    if a.stage == "paid":
        if a.amount is None:
            die("give the amount received: --amount")
        r["paid_amount"] = str(money(a.amount, "--amount"))
        detail.append(f"paid {r['paid_amount']}")
    if a.stage == "quoted":
        if a.amount is None:
            die("give the quoted professional fees: --amount")
        r["quote"] = str(money(a.amount, "--amount"))
        detail.append(f"quote {r['quote']}")
    if a.stage == "signed":
        if not a.case:
            die("open the case first (case.py new ...), then give --case")
        folder = de.active_case(a.case)
        r["case"] = cs.read_case(folder).get("case_id", folder.name[:8])
        cs.add_log(folder, f"Became a client from prospect {r['id']} (source: {r['source'] or 'not recorded'})")
    if a.stage in ("declined", "not-taken", "no-show", "lost"):
        r["reason"] = a.reason or ""
    if a.stage in ENDS:
        r["closed"] = day.isoformat()
    if a.stage in r:
        r[a.stage] = r.get(a.stage) or day.isoformat()
    r["stage"] = a.stage
    if a.note:
        r["note"] = (r["note"] + " | " if r["note"] else "") + a.note
    save(rows)
    history(r["id"], a.stage, day, "; ".join(detail + ([a.reason] if a.reason else []) + ([a.note] if a.note else [])))
    print(f"{r['id']} {r['name']}: {a.stage}")
    if a.stage == "booked":
        print("Before the consultation: a written consultation agreement with the fee (Code s.23): firm.py make consultation-agreement")
    if a.stage == "paid":
        print("Paid before the consultation: an advance payment, so it goes to the client account (Code s.32(a)). Record it with billing.py once the file exists.")
    if a.stage == "not-taken":
        import conflicts
        conflicts.append(conflicts.PARTIES, conflicts.PARTY_FIELDS, {"name": r["name"], "role": "prospect we declined", "case": "", "note": a.reason or "",
                                                                     "added": datetime.date.today().isoformat()})
        print("Added to the other-parties list for future conflict checks. Send a non-engagement letter: firm.py make non-engagement-letter")
    if a.stage == "signed":
        print("Next: service agreement signed (case.py set CASE agreement_signed yes), IMM 5476, and the conflict check recorded.")


def due(r, today):
    """Days a follow-up is overdue, or None."""
    if r["stage"] not in STALE:
        return None
    if r["stage"] in ("booked", "paid"):
        return None
    last = r.get(r["stage"]) or ""  # how long the prospect has sat at its current stage
    try:
        age = (today - datetime.date.fromisoformat(last)).days
    except ValueError:
        return None
    return age - STALE[r["stage"]] if age > STALE[r["stage"]] else None


def cmd_list(a):
    today = datetime.date.today()
    rows = [r for r in load() if (a.all or r["stage"] in OPEN) and (not a.stage or r["stage"] == a.stage)]
    if not rows:
        print("No open prospects." if not a.all else "No prospects recorded.")
    for r in rows:
        late = due(r, today)
        print(f"{r['id']}  {r['stage']:10} {r['name'][:26]:26} {r['program'][:18]:18} {r['source'][:10]:10}"
              + (f"  quote ${r['quote']}" if r["quote"] else "") + (f"  FOLLOW UP ({late}d)" if late else ""))


def cmd_show(a):
    r = get(a.id)
    for k in FIELDS:
        if r.get(k):
            print(f"{k:12} {r[k]}")
    if HISTORY.exists():
        with HISTORY.open(encoding="utf-8", newline="") as f:
            for h in csv.DictReader(f):
                if h["id"] == r["id"]:
                    print(f"  {h['date']}  {h['stage']:10} {h['detail']}")


def pct(n, d):
    return f"{100 * n / d:.0f}%" if d else ""


def cmd_report(a):
    import openpyxl
    start = cs.parse_date(a.start, "--from") if a.start else None
    end = cs.parse_date(a.end, "--to") if a.end else None
    rows = [r for r in load() if (not start or r["enquiry"] >= start.isoformat()) and (not end or r["enquiry"] <= end.isoformat())]
    reached = {s: sum(1 for r in rows if r.get(s)) for s in FUNNEL}
    out = pathlib.Path(a.out) if a.out else de.REPO / "Output" / "general"
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    stem, n = f"{datetime.date.today().isoformat()}-prospect-pipeline", 1
    path = out / f"{stem}.xlsx"
    while path.exists():
        n += 1
        path = out / f"{stem}-v{n}.xlsx"
    book = openpyxl.Workbook()
    book.remove(book.active)
    funnel = []
    for i, s in enumerate(FUNNEL):
        funnel.append([s, reached[s], pct(reached[s], reached["enquiry"]), pct(reached[s], reached[FUNNEL[i - 1]]) if i else ""])
    paid = sum((Decimal(r["paid_amount"]) for r in rows if r["paid_amount"]), Decimal("0"))
    signed_quotes = sum((Decimal(r["quote"]) for r in rows if r["stage"] == "signed" and r["quote"]), Decimal("0"))
    de.add_sheet(book, "Funnel", ["Stage", "Prospects who reached it", "Of all enquiries", "From the stage before"],
                 funnel + [["", "", "", ""], ["Consultation fees received", float(paid), "", ""], ["Quoted fees of signed clients", float(signed_quotes), "", ""]], [30, 24, 18, 22])
    by_source = {}
    for r in rows:
        g = by_source.setdefault(r["source"] or "(not recorded)", [0, 0, 0])
        g[0] += 1
        g[1] += bool(r.get("consulted"))
        g[2] += r["stage"] == "signed"
    de.add_sheet(book, "By source", ["Source", "Enquiries", "Consulted", "Signed", "Signed of enquiries"],
                 [[k, v[0], v[1], v[2], pct(v[2], v[0])] for k, v in sorted(by_source.items(), key=lambda x: -x[1][0])] or [["", "", "", "", ""]], [22, 12, 12, 10, 18])
    lost = {}
    for r in rows:
        if r["stage"] in ("declined", "not-taken", "no-show", "lost"):
            key = (r["stage"], r["reason"] or "(no reason recorded)")
            lost[key] = lost.get(key, 0) + 1
    de.add_sheet(book, "Why not signed", ["Ending", "Reason", "Prospects"], [[k[0], k[1], v] for k, v in sorted(lost.items(), key=lambda x: -x[1])] or [["", "", ""]], [14, 60, 12])
    today = datetime.date.today()
    de.add_sheet(book, "Open prospects", ["ID", "Name", "Stage", "Program", "Source", "Enquiry", "Quote", "Follow-up overdue (days)"],
                 [[r["id"], r["name"], r["stage"], r["program"], r["source"], r["enquiry"], r["quote"], due(r, today) or ""] for r in rows if r["stage"] in OPEN] or [["", "", "", "", "", "", "", ""]],
                 [8, 26, 12, 20, 14, 12, 10, 20])
    book.save(path)
    print(f"{len(rows)} prospect(s): {reached['consulted']} consulted, {reached['signed']} signed ({pct(reached['signed'], reached['enquiry']) or '0%'}). Saved to {path}")


def issues(today):
    """Firm-wide alerts: (rank, kind, tier, text, step, day)."""
    out = []
    try:
        rows = load()
    except (OSError, ValueError) as e:
        return [(2, "Prospects", "unreadable", f"Could not read prospects.csv ({type(e).__name__})", "Check cases/prospects/prospects.csv", None)]
    late = [r for r in rows if due(r, today)]
    if late:
        out.append((3, "Prospects", "follow-up", f"{len(late)} prospect(s) waiting for a follow-up: " + ", ".join(f"{r['id']} ({r['stage']})" for r in late[:6]),
                    "Run prospects.py list, then follow up or close them", None))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Prospect pipeline")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("add"); x.add_argument("name"); x.add_argument("--source"); x.add_argument("--program"); x.add_argument("--contact"); x.add_argument("--note"); x.add_argument("--date"); x.set_defaults(fn=cmd_add)
    x = s.add_parser("move"); x.add_argument("id"); x.add_argument("stage"); x.add_argument("--date"); x.add_argument("--fee"); x.add_argument("--amount"); x.add_argument("--reason")
    x.add_argument("--case"); x.add_argument("--note"); x.set_defaults(fn=cmd_move)
    x = s.add_parser("list"); x.add_argument("--stage"); x.add_argument("--all", action="store_true"); x.set_defaults(fn=cmd_list)
    x = s.add_parser("show"); x.add_argument("id"); x.set_defaults(fn=cmd_show)
    x = s.add_parser("report"); x.add_argument("--from", dest="start"); x.add_argument("--to", dest="end"); x.add_argument("--out"); x.set_defaults(fn=cmd_report)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
