#!/usr/bin/env python3
"""IRCC permanent residence inventory: the share of files "waiting for space" under the yearly admission targets, by category,
next to the firm's own open files in that category. Used by the dashboard (home card and case page).

Usage:
  python3 scripts/inventory.py              print the card as text
  python3 scripts/inventory.py --case NAME  the line for one open case (folder name or case id)

Data: templates/ircc/inventory.csv, copied by hand from IRCC's "Inside IRCC's application processing system" page during the
monthly watch pass (see knowledge/14-policy-tracker/backlogs-and-inventory.md). Nothing is read from the internet.

Guarantees:
  - Figures are IRCC's own, with the date the data runs to; nothing is estimated.
  - "Waiting for space" is a complete file held until a yearly target space opens. It is not a processing time and not a
    prediction for a client's file.
  - The card is marked out of date once IRCC's page date is more than STALE_DAYS old.
  - Temporary residence and citizenship files have no "waiting for space" figure, so they are not counted.
"""
import argparse
import csv
import datetime
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parent.parent / "templates" / "ircc" / "inventory.csv"
SOURCE = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/corporate-initiatives/levels/inventories-backlogs.html"
STALE_DAYS = 60

# Program text -> PR category. Temporary and citizenship programs first, so "spousal OWP" or "super visa" never count as PR.
NOT_PR = r"\bowp\b|open work|work[- ]?permit|\bpgwp\b|\blmia\b|study|student|visitor|\btrv\b|super ?visa|\beta\b|\biec\b|\btrp\b|restor|extension|citizen|pr[- ]?card|prtd|residency"
CATEGORIES = [
    ("protection", r"refugee|asylum|protected|\bprra\b|h&c|humanitarian|resettle|\bgar\b|\bpsr\b|\bbvor\b"),
    ("family", r"spous|partner|common[- ]?law|conjugal|\bpgp\b|parent|grandparent|dependent child|family|sponsor"),
    ("economic", r"express|\bee\b|\bcec\b|\bfsw\b|\bfst\b|\bpnp\b|nominee|\baip\b|atlantic|\brcip\b|rural|caregiver|start[- ]?up|\bsuv\b|self[- ]?employ|"
                 r"skilled worker|economic|business|entrepreneur|investor|agri|\bpstq\b|\bpeq\b|\bcsq\b|quebec"),
]


def category_of(program):
    p = (program or "").lower()
    if not p or re.search(NOT_PR, p):
        return None
    for name, rx in CATEGORIES:
        if re.search(rx, p):
            return name
    return None


def date_of(s):
    try:
        return datetime.date.fromisoformat((s or "").strip())
    except ValueError:
        return None


def num(s):
    s = (s or "").strip().replace(",", "")
    return int(s) if s.isdigit() else None


def load(path=DATA):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return []
    out = []
    for r in rows:
        out.append({"line": r["line"].strip(), "label": r["label"].strip(), "not_finalized": num(r["not_finalized"]),
                    "waiting_pct": num(r["waiting_pct"]), "prev_not_finalized": num(r.get("prev_not_finalized")),
                    "prev_waiting_pct": num(r.get("prev_waiting_pct")), "data_as_of": r["data_as_of"].strip(),
                    "page_date": r["page_date"].strip()})
    return out


def trend(now, prev):
    if now is None or prev is None:
        return ""
    return "up" if now > prev else "down" if now < prev else "same"


def card(today=None, path=DATA, active=None):
    """The home card: one row per PR category with the firm's open files in it."""
    today = today or datetime.date.today()
    rows = load(path)
    if not rows:
        return None
    folders = cs.folders(cs.ACTIVE) if active is None else active
    counts = {}
    for f in folders:
        try:
            c = category_of(cs.read_case(f).get("program", ""))
        except (OSError, ValueError):
            c = None
        if c:
            counts[c] = counts.get(c, 0) + 1
    page = min((d for d in (date_of(r["page_date"]) for r in rows) if d), default=None)
    return {
        "data_as_of": rows[0]["data_as_of"], "page_date": page.isoformat() if page else "",
        "age": (today - page).days if page else None, "stale": page is None or (today - page).days > STALE_DAYS,
        "stale_after": STALE_DAYS, "source": SOURCE,
        "rows": [{"line": r["line"], "label": r["label"], "waiting_pct": r["waiting_pct"], "not_finalized": r["not_finalized"],
                  "pct_trend": trend(r["waiting_pct"], r["prev_waiting_pct"]),
                  "files_trend": trend(r["not_finalized"], r["prev_not_finalized"]), "yours": counts.get(r["line"], 0)} for r in rows],
    }


def for_program(program, path=DATA):
    """The line for one case, or None when the program is not a PR category."""
    c = category_of(program)
    if not c:
        return None
    for r in load(path):
        if r["line"] == c:
            return {"line": c, "label": r["label"], "waiting_pct": r["waiting_pct"], "data_as_of": r["data_as_of"]}
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", help="folder name or case id of an open case")
    a = ap.parse_args()
    if a.case:
        folder = next((f for f in cs.folders(cs.ACTIVE) if f.name == a.case or cs.read_case(f).get("case_id") == a.case), None)
        if not folder:
            sys.exit("ERROR: no open case " + a.case)
        r = for_program(cs.read_case(folder).get("program", ""))
        print(f"IRCC: {r['waiting_pct']}% of {r['label'].lower()} files held for space (data to {r['data_as_of']})" if r
              else "Not a permanent residence category: no 'waiting for space' figure.")
        return
    c = card()
    if not c:
        sys.exit("ERROR: no data in " + str(DATA))
    print(f"IRCC: files held for space (data to {c['data_as_of']}; IRCC page {c['page_date']}{', OUT OF DATE' if c['stale'] else ''})")
    arrow = {"up": "up", "down": "down", "same": "same", "": ""}
    for r in c["rows"]:
        print(f"  {r['label']:<11} {r['waiting_pct']}% {arrow[r['pct_trend']]:<5} {r['not_finalized']:>9,} not finalized ({arrow[r['files_trend']] or 'n/a'})  your open files: {r['yours']}")
    print("Source: " + SOURCE)


if __name__ == "__main__":
    main()
