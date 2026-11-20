#!/usr/bin/env python3
"""IRCC processing times for the dashboard's "IRCC data" page: permanent residence and citizenship estimates for a new
application (with people waiting), visas and permits applied from outside Canada by country of residence, and in-Canada and
other services.

Usage:
  python3 scripts/ircc_times.py                    print the times as text
  python3 scripts/ircc_times.py --country IN       the visa and permit times for one country of residence (2-letter code)
  python3 scripts/ircc_times.py build [--from DIR] refresh the data files from IRCC's public feeds (maintainers, monthly watch
                                                   pass); --from reads flpt-en.json, data-ptime-en.json and
                                                   data-ptime-non-country-en.json already saved in DIR

Data: templates/ircc/processing-times.csv and templates/ircc/processing-times-country.csv, built from IRCC's own feeds behind
its "Check processing times" page and checked against knowledge/11-forms-fees-processing/processing-times.md. The dashboard
reads only these files; nothing is read from the internet.

Guarantees:
  - IRCC's words are kept as IRCC publishes them ("About 7 months", "More than 10 years", "Not enough data"), with IRCC's
    update date. Nothing is estimated.
  - Permanent residence and citizenship figures are IRCC's estimate for an application submitted now. Visa and permit times
    are how long IRCC took for most recent applications. Neither is a promise for a client's file.
  - The page is marked out of date once IRCC's update is more than STALE_DAYS old.
"""
import argparse
import csv
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINES = ROOT / "templates" / "ircc" / "processing-times.csv"
COUNTRY = ROOT / "templates" / "ircc" / "processing-times-country.csv"
NAMES = ROOT / "knowledge" / "05-temporary-residence" / "visitor-country-reference.md"
FEED = "https://www.canada.ca/content/dam/ircc/documents/json/"
SOURCE = "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html"
SOURCE_NAME = "IRCC, Check processing times"
STALE_DAYS = 45

# (IRCC key, group, label), in the order shown. Keys are IRCC's; a key IRCC drops is skipped, a new one is reported by build.
PR = [
    ("cec", "Economic", "Express Entry: Canadian Experience Class"),
    ("fsw", "Economic", "Express Entry: Federal Skilled Worker"),
    ("pnp-ee", "Economic", "Provincial nominee, through Express Entry"),
    ("pnp-base", "Economic", "Provincial nominee, base (paper)"),
    ("aip", "Economic", "Atlantic Immigration Program"),
    ("caregiver", "Economic", "Caregivers"),
    ("startup-visa", "Economic", "Start-up Visa"),
    ("self-employed", "Economic", "Self-employed"),
    ("qsw", "Economic", "Quebec skilled worker"),
    ("quebec-business", "Economic", "Quebec business"),
    ("spousal-abroad-roc", "Family", "Spouse or partner, outside Canada (outside Quebec)"),
    ("spousal-abroad-quebec", "Family", "Spouse or partner, outside Canada (Quebec)"),
    ("spousal-canada-roc", "Family", "Spouse or partner, in Canada (outside Quebec)"),
    ("spousal-canada-quebec", "Family", "Spouse or partner, in Canada (Quebec)"),
    ("pgp-roc", "Family", "Parents and grandparents (outside Quebec)"),
    ("pgp-quebec", "Family", "Parents and grandparents (Quebec)"),
    ("protected-persons-in-canada-roc", "Protection and humanitarian", "Protected persons in Canada (outside Quebec)"),
    ("protected-persons-in-canada-quebec", "Protection and humanitarian", "Protected persons in Canada (Quebec)"),
    ("dependants-abroad-roc", "Protection and humanitarian", "Dependants abroad of protected persons (outside Quebec)"),
    ("dependants-abroad-quebec", "Protection and humanitarian", "Dependants abroad of protected persons (Quebec)"),
    ("government-refugees-roc", "Protection and humanitarian", "Government-assisted refugees (outside Quebec)"),
    ("government-refugees-quebec", "Protection and humanitarian", "Government-assisted refugees (Quebec)"),
    ("private-refugees-roc", "Protection and humanitarian", "Privately sponsored refugees (outside Quebec)"),
    ("private-refugees-quebec", "Protection and humanitarian", "Privately sponsored refugees (Quebec)"),
    ("humanitarian-roc", "Protection and humanitarian", "Humanitarian and compassionate (outside Quebec)"),
    ("humanitarian-quebec", "Protection and humanitarian", "Humanitarian and compassionate (Quebec)"),
    ("citizen-grants", "Citizenship", "Citizenship grant"),
    ("citizen-proofs", "Citizenship", "Proof of citizenship (certificate)"),
]
OTHER = [
    ("visitor_inside_canada/visitor_inside_canada", "In Canada", "Visitor visa, applied from inside Canada"),
    ("visitor_extension/visitor_extension", "In Canada", "Visitor extension (visitor record)"),
    ("study_extension/study_extension", "In Canada", "Study permit extension"),
    ("work_extension/work_extension", "In Canada", "Work permit extension or new permit from inside Canada"),
    ("pr_card/new_pr", "PR card", "PR card for a new permanent resident"),
    ("pr_card/existing_pr", "PR card", "PR card renewal or replacement"),
    ("eta/eta", "Other", "eTA"),
    ("iec/iec", "Other", "International Experience Canada (work permit)"),
    ("sawp/sawp_current", "Other", "Seasonal Agricultural Worker Program"),
    ("citizenship/cit_renunciation", "Citizenship services", "Renounce citizenship"),
    ("citizenship/cit_search", "Citizenship services", "Search of citizenship records"),
    ("citizenship/cit_adoption_part1", "Citizenship services", "Citizenship for an adopted child"),
    ("citizenship/cit_resumption", "Citizenship services", "Resume citizenship"),
    ("rep_documents/vos", "Status documents", "Verification of status"),
    ("rep_documents/replacement", "Status documents", "Replace a status document"),
    ("rep_documents/amend_imm", "Status documents", "Amend a PR document (e.g. CoPR)"),
    ("rep_documents/amend_tr", "Status documents", "Amend a temporary residence document"),
]
EXTRA_NAMES = {"CA": "Canada", "GL": "Greenland", "IO": "British Indian Ocean Territory", "PS": "Palestinian Authority (Gaza)",
               "WB": "West Bank"}  # codes in IRCC's feed with no row in the visitor reference
COUNTRY_COLS = [("visitor", "visitor-outside-canada", "Visitor visa"), ("supervisa", "supervisa", "Super visa"),
                ("study", "study", "Study permit"), ("work", "work", "Work permit")]


def iso(text):
    try:
        return datetime.datetime.strptime(text.strip(), "%B %d, %Y").date().isoformat()
    except (AttributeError, ValueError):
        return ""


def waiting(text):
    """'About 11,100 people waiting' -> 'About 11,100'."""
    return re.sub(r"\s*people waiting\.?$", "", (text or "").strip(), flags=re.I)


def country_names():
    """2-letter code -> country name, from the visitor country reference table."""
    out = dict(EXTRA_NAMES)
    try:
        for line in NAMES.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*([^|]+?)\s*\|\s*([A-Z]{2})\s*\|", line)
            if m:
                out[m.group(2)] = m.group(1)
    except OSError:
        pass
    return out


def read_feeds(folder=None):
    names = {"flpt": "flpt-en.json", "country": "data-ptime-en.json", "other": "data-ptime-non-country-en.json"}
    out = {}
    for key, name in names.items():
        if folder:
            text = (pathlib.Path(folder) / name).read_text(encoding="utf-8-sig")
        else:
            import watch as wt
            text = wt.fetch(FEED + name)
            if not text:
                sys.exit(f"ERROR: IRCC's {name} couldn't be read (no internet, or the page moved)")
        out[key] = json.loads(text.lstrip("﻿"))
    return out


def build(feeds, today=None):
    """Write the two data files from IRCC's feeds. Returns a list of notes (new or missing IRCC keys)."""
    today = (today or datetime.date.today()).isoformat()
    flpt, country, other = feeds["flpt"], feeds["country"], feeds["other"]
    pr_upd = iso((flpt.get("default-update") or {}).get("flpt_lastupdated", ""))
    upd = iso((other.get("default-update") or {}).get("lastupdated", ""))
    cupd = iso((country.get("visitor-outside-canada") or {}).get("lastupdated", "")) or upd
    times, people = flpt.get("current-flpt") or {}, flpt.get("total-people") or {}
    if not times or not country.get("study") or not pr_upd or not upd:
        sys.exit("ERROR: IRCC's processing time feeds changed layout; nothing written")
    notes = [f"new IRCC line not shown: {k}" for k in times if k not in {p[0] for p in PR}]
    rows = []
    for key, group, label in PR:
        if key not in times:
            notes.append(f"IRCC no longer publishes: {key}")
            continue
        rows.append({"kind": "pr", "key": key, "group": group, "label": label, "time": times[key].strip(),
                     "waiting": waiting(people.get(key)), "updated": pr_upd, "read_date": today})
    for key, group, label in OTHER:
        g, _, k = key.partition("/")
        val = (other.get(g) or {}).get(k)
        if val is None:
            notes.append(f"IRCC no longer publishes: {key}")
            continue
        rows.append({"kind": "other", "key": key, "group": group, "label": label, "time": str(val).strip(), "waiting": "",
                     "updated": upd, "read_date": today})
    with open(LINES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kind", "key", "group", "label", "time", "waiting", "updated", "read_date"])
        w.writeheader()
        w.writerows(rows)
    names = country_names()
    codes = sorted(k for k in set().union(*(set(country.get(feed) or {}) for _, feed, _ in COUNTRY_COLS)) if re.fullmatch(r"[A-Z]{2}", k))
    crow = []
    for cc in codes:
        vals = {col: str((country.get(feed) or {}).get(cc, "")).strip() for col, feed, _ in COUNTRY_COLS}
        if not any(shown(v) for v in vals.values()):
            continue  # IRCC publishes no time for any of the four
        if cc not in names:
            notes.append(f"country code with no name in the visitor reference: {cc}")
        crow.append({"code": cc, "country": names.get(cc, cc), **vals, "updated": cupd, "read_date": today})
    crow.sort(key=lambda r: r["country"].lower())
    with open(COUNTRY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["code", "country"] + [c for c, _, _ in COUNTRY_COLS] + ["updated", "read_date"])
        w.writeheader()
        w.writerows(crow)
    return notes


def load(path):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def shown(text):
    """IRCC's 'No processing time available' and 'Not enough data' shown as a dash."""
    t = (text or "").strip()
    return "" if not t or re.match(r"no processing time|not enough data", t, re.I) else t


def card(today=None):
    today = today or datetime.date.today()
    lines, countries = load(LINES), load(COUNTRY)
    if not lines:
        return None
    dates = [datetime.date.fromisoformat(r["updated"]) for r in lines + countries if r.get("updated")]
    oldest = min(dates) if dates else None

    def groups(kind):
        out = []
        for r in (r for r in lines if r["kind"] == kind):
            if not out or out[-1]["group"] != r["group"]:
                out.append({"group": r["group"], "rows": []})
            out[-1]["rows"].append({"key": r["key"], "label": r["label"], "time": shown(r["time"]), "waiting": r["waiting"]})
        return out

    def first(kind, field):
        return next((r[field] for r in lines if r["kind"] == kind), "")

    return {
        "pr": groups("pr"), "pr_updated": first("pr", "updated"), "other": groups("other"), "other_updated": first("other", "updated"),
        "countries": [{"code": r["code"], "country": r["country"], **{c: shown(r[c]) for c, _, _ in COUNTRY_COLS}} for r in countries],
        "country_cols": [{"key": c, "label": l} for c, _, l in COUNTRY_COLS],
        "country_updated": countries[0]["updated"] if countries else "", "read_date": first("pr", "read_date"),
        "stale": oldest is None or (today - oldest).days > STALE_DAYS, "stale_after": STALE_DAYS,
        "source": SOURCE, "source_name": SOURCE_NAME,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["build"])
    ap.add_argument("--from", dest="src", help="folder holding IRCC's three feed files (build only)")
    ap.add_argument("--country", help="2-letter country code of residence")
    a = ap.parse_args()
    if a.cmd == "build":
        sys.path.insert(0, str(ROOT / "scripts"))
        for n in build(read_feeds(a.src)):
            print("NOTE: " + n)
        print(f"Written: {LINES.relative_to(ROOT)}, {COUNTRY.relative_to(ROOT)}")
        return
    c = card()
    if not c:
        sys.exit("ERROR: no data in " + str(LINES))
    if a.country:
        r = next((r for r in c["countries"] if r["code"] == a.country.upper()), None)
        if not r:
            sys.exit("ERROR: no IRCC times for country code " + a.country)
        print(f"{r['country']} ({r['code']}), applied from outside Canada (IRCC data updated {c['country_updated']}):")
        for col in c["country_cols"]:
            print(f"  {col['label']:<14} {r[col['key']] or 'no time published'}")
        return
    print(f"Permanent residence and citizenship: IRCC estimate for a new application (updated {c['pr_updated']})")
    for g in c["pr"]:
        print(f"  {g['group']}")
        for r in g["rows"]:
            print(f"    {r['label']:<58} {r['time'] or '-':<20} {r['waiting'] and r['waiting'] + ' waiting'}")
    print(f"\nIn Canada and other services (updated {c['other_updated']})")
    for g in c["other"]:
        for r in g["rows"]:
            print(f"    {r['label']:<58} {r['time'] or '-'}")
    print(f"\nVisas and permits from outside Canada: {len(c['countries'])} countries. Use --country CODE.")
    print(f"{'OUT OF DATE. ' if c['stale'] else ''}Source: {SOURCE}")


if __name__ == "__main__":
    main()
