#!/usr/bin/env python3
"""PGWP field-of-study check for a CIP code, read from IRCC's list stored in the knowledge base.

  python3 scripts/cip_check.py 52.0201
  python3 scripts/cip_check.py 13.1210 --applied 2025-07-10      # study permit application date
  python3 scripts/cip_check.py 13.1210 --pgwp 2026-12-01          # PGWP application date
  python3 scripts/cip_check.py 52.0201 --json

The list is templates/pgwp/field-of-study.csv (every row of IRCC's field-of-study page, with the page date). Nothing
here is a rule of its own. Answers:
  eligible           the CIP is on the list with no date condition
  date-conditioned   the CIP is on the list only for applications submitted before 2024-11-01 or after a date
                     (IRCC: study permit OR PGWP application); with --applied/--pgwp the condition is checked
                     and the answer becomes eligible or not eligible (the condition date itself stays
                     date-conditioned)
  not listed         the CIP is not on the list
  not eligible       on the list, but the application dates given don't meet its date condition

Reminders printed with every answer: bachelor's, master's and doctoral graduates don't need an eligible field;
study permits applied for before 2024-11-01 are exempt; the CIP is the one the DLI gives for the program.
"""
import argparse
import csv
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIST = ROOT / "templates" / "pgwp" / "field-of-study.csv"
REMOVED = ROOT / "templates" / "pgwp" / "field-of-study-removed.csv"
BEFORE = datetime.date(2024, 11, 1)  # field-of-study rule starts for study permits applied on/after this date
WHERE = "templates/pgwp/field-of-study.csv (from IRCC's PGWP field-of-study page; see knowledge/05-temporary-residence/pgwp.md)"
NOTES = [
    "Not needed for bachelor's, master's or doctoral graduates, or if the study permit was applied for before 2024-11-01.",
    "Use the CIP code the school (DLI) gives for the program; the CIP must be on the list when the study permit or the PGWP application is submitted.",
]


def norm(cip):
    """'52.201' / '52-0201' / '520201' -> '52.0201'; None if not a CIP shape."""
    s = str(cip).strip().replace("-", ".").replace(" ", "")
    if re.fullmatch(r"\d{6}", s):
        s = s[:2] + "." + s[2:]
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,4})", s)
    if not m:
        return None
    return f"{int(m.group(1)):02d}.{m.group(2).ljust(4, '0')}"


def load(path=LIST):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["cip"] = norm(r.get("cip", "")) or r.get("cip", "")
    return rows


def page_date(rows):
    dates = sorted({r.get("page_modified", "") for r in rows if r.get("page_modified")})
    return dates[-1] if dates else "unknown"


def _parse(d):
    try:
        return datetime.date.fromisoformat(d)
    except (TypeError, ValueError):
        return None


def check(cip, applied=None, path=LIST, pgwp=None):
    code = norm(cip)
    if not code:
        return {"cip": cip, "answer": "error", "reason": "Not a CIP code (expected like 52.0201)."}
    rows = load(path)
    hits = [r for r in rows if r["cip"] == code]
    out = {"cip": code, "list_date": page_date(rows), "source": WHERE, "notes": NOTES}
    if not hits:
        out.update(answer="not listed", reason=f"{code} is not on IRCC's PGWP field-of-study list.")
        if REMOVED.exists():
            with open(REMOVED, encoding="utf-8-sig", newline="") as f:
                gone = [r for r in csv.DictReader(f) if norm(r.get("cip", "")) == code]
            if gone:
                g = gone[0]
                out["reason"] += f" Removed {g.get('removed_on', '')}: {g.get('note', '')}".rstrip(": ")
        return out
    out["matches"] = [{k: h.get(k, "") for k in ("title", "category", "condition")} for h in hits]
    plain = [h for h in hits if (h.get("condition_type") or "none") == "none" and not h.get("condition")]
    if plain:
        h = plain[0]
        out.update(answer="eligible", reason=f"{code} {h.get('title', '')} is on the list ({h.get('category', '')}).")
        return out
    h = hits[0]
    out.update(answer="date-conditioned", reason=f"{code} {h.get('title', '')} ({h.get('category', '')}): {h.get('condition', '')}".strip())
    ctype, cdate = h.get("condition_type", ""), _parse(h.get("condition_date", ""))
    dates = [(label, d) for label, d in (("study permit", applied), ("PGWP", pgwp)) if d]
    if not (dates and cdate):
        return out
    results = []
    for label, d in dates:
        a = _parse(d)
        if not a:
            out["reason"] += f" ({label} date not understood; use YYYY-MM-DD)"
            return out
        if ctype == "applied_on_or_after":
            ok = a >= cdate
        elif ctype == "applied_before":
            ok = a < cdate
        else:
            # IRCC's wording: eligible if the study permit or PGWP application was submitted
            # "before November 1, 2024" or "after" the condition date. The day itself is not stated.
            if a == cdate:
                ok = None
            else:
                ok = a < BEFORE or a > cdate
        results.append((label, a, ok))
    if any(ok for _, _, ok in results):
        out["answer"] = "eligible"
    elif any(ok is None for _, _, ok in results):
        out["answer"] = "date-conditioned"
        out["reason"] += " Application filed on the condition date itself: IRCC doesn't say whether that day counts. Confirm with IRCC."
        return out
    else:
        out["answer"] = "not eligible"
    out["reason"] += " " + "; ".join(f"{label} application {a}: {'meets' if ok else 'does not meet'} the condition"
                                       for label, a, ok in results) + "."
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cip")
    p.add_argument("--applied", help="study permit application date YYYY-MM-DD (checks date conditions)")
    p.add_argument("--pgwp", help="PGWP application date YYYY-MM-DD (IRCC conditions accept either date)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if not LIST.exists():
        print(f"The field-of-study list is missing ({WHERE}). Check IRCC's page by hand.")
        return 2
    r = check(a.cip, a.applied, pgwp=a.pgwp)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"{r['answer'].upper()}: {r['reason']}")
        if r["answer"] != "error":
            print(f"List: {r['source']}; IRCC page date {r['list_date']}.")
            for n in r["notes"]:
                print(f"- {n}")
    return 0 if r["answer"] != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
