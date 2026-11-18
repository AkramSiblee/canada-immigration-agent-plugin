#!/usr/bin/env python3
"""Which 2026 Express Entry categories a NOC belongs to, read from IRCC's category page stored in the KB.

  python3 scripts/category_check.py 31102
  python3 scripts/category_check.py 21231 --json

The list is templates/ee/category-nocs.csv (every NOC on IRCC's category-based selection page, with the page date).
French-language proficiency has no NOC list: it is shown on every answer as a language-based option.
Category experience (renewed categories since 2026-02-18): 12 months full-time or equal part-time in the past
3 years in one listed occupation; it need not be continuous (IRCC page). Some categories add conditions (see the note).
"""
import argparse
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIST = ROOT / "templates" / "ee" / "category-nocs.csv"
HIGH_WAGE = ROOT / "templates" / "ee" / "high-wage.csv"
WHERE = "templates/ee/category-nocs.csv (IRCC category-based selection page; see knowledge/01-federal-economic/category-draws-history.md)"


def load(path=LIST):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check(noc, path=LIST):
    n = str(noc).strip().zfill(5)
    if not (n.isdigit() and len(n) == 5):
        return {"noc": noc, "error": "NOC must be 5 digits (e.g. 21231)"}
    rows = load(path)
    date = max((r.get("page_modified", "") for r in rows), default="unknown")
    hits = [r for r in rows if r.get("noc", "").strip().zfill(5) == n and r.get("noc", "").strip()]
    french = next((r for r in rows if r["category"].lower().startswith("french")), None)
    out = {"noc": n, "list_date": date, "source": WHERE,
           "categories": [{"category": r["category"], "title": r.get("title", ""), "teer": r.get("teer", ""),
                           "note": r.get("note", "")} for r in hits],
           "french": (french or {}).get("note", "French-language proficiency (language-based)")}
    if HIGH_WAGE.exists():
        with open(HIGH_WAGE, encoding="utf-8-sig", newline="") as f:
            hw = {r["noc"].strip().zfill(5): r["level"] for r in csv.DictReader(f)}
        out["high_wage"] = hw.get(n)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("noc")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if not LIST.exists():
        print(f"Category list missing ({WHERE}); check IRCC's category page by hand.")
        return 2
    r = check(a.noc)
    if "error" in r:
        print(r["error"])
        return 1
    if a.json:
        print(json.dumps(r, indent=2))
        return 0
    if r["categories"]:
        print(f"{r['noc']} is in {len(r['categories'])} 2026 categor{'y' if len(r['categories']) == 1 else 'ies'}:")
        for c in r["categories"]:
            print(f"- {c['category']}: {c['title']} (TEER {c['teer']})" + (f". {c['note']}" if c["note"] else ""))
    else:
        print(f"{r['noc']} is not in any 2026 occupation category.")
    print(f"- Any NOC: French-language proficiency ({r['french']}).")
    if "high_wage" in r:
        print(f"High-wage list (CRS labour market integration): {r['high_wage'] or 'not listed'}.")
    print(f"List: {r['source']}; IRCC page date {r['list_date']}. Category rounds also need the round's own instructions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
