#!/usr/bin/env python3
"""IRCC application inventory: permanent residence by category (not finalized, change since the month before, share actively
processed and "waiting for space" under the yearly admission targets, finalized this year) next to the firm's own open files in
that category, and temporary residence by line (not finalized, change, finalized this year). Used by the dashboard (home card and
case page).

Usage:
  python3 scripts/inventory.py              print the card as text
  python3 scripts/inventory.py --case NAME  the line for one open case (folder name or case id)

Data: templates/ircc/inventory.csv, shipped with each release (checked against
knowledge/14-policy-tracker/backlogs-and-inventory.md). scripts/ircc_data.py reads IRCC's "Inside IRCC's application processing
system" page once a day and saves a local copy (cases/.ircc-data/inventory.csv) when IRCC publishes a newer month; the dashboard
shows whichever copy has the newer data. The dashboard itself reads no web page.

Guarantees:
  - Figures are IRCC's own, with the date the data runs to; nothing is estimated.
  - "Waiting for space" is a complete file held until a yearly target space opens. It is not a processing time and not a
    prediction for a client's file.
  - The card is marked out of date once IRCC's page date is more than STALE_DAYS old.
  - Temporary residence and citizenship files have no "waiting for space" figure, so the firm's files are counted only for
    permanent residence.
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
SOURCE_NAME = "IRCC, Inside IRCC's application processing system"
SOURCE = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/reports-statistics/statistics-open-data/immigration-stats/application-processing-system.html"
FIELDS = ["group", "line", "label", "not_finalized", "waiting_pct", "finalized_ytd", "prev_not_finalized", "prev_waiting_pct",
          "data_as_of", "prev_data_as_of", "page_date", "read_date"]
PAGE_LINES = [  # (group, line, label, heading or label on IRCC's page)
    ("pr", "economic", "Economic", "Economic"), ("pr", "family", "Family", "Family"), ("pr", "protection", "Protection", "Protection"),
    ("tr", "visitor", "Visitor visas", "Visitor visas"), ("tr", "work", "Work permits", "Work permits"), ("tr", "study", "Study permits", "Study permits"),
]
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


def local_path():
    return cs.ROOT / ".ircc-data" / "inventory.csv"


def current_path():
    """The local refresh when it holds IRCC data at least as new as the release's file."""
    local = local_path()
    if local.exists():
        a, b = load(local), load(DATA)
        if a and (not b or a[0]["data_as_of"] >= b[0]["data_as_of"]):
            return local
    return DATA


def clean(text):
    import html as h
    return re.sub(r"\s+", " ", h.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def parse_page(page):
    """IRCC's figures from the page: {data_as_of, page_date, lines: {line: (not_finalized, waiting_pct, finalized_ytd)}}."""
    main = page[page.find("<main"):] if "<main" in page else page
    text = clean(main)
    m = re.search(r"Data as of ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    modified = re.search(r'name="dcterms.modified"[^>]*content="(\d{4}-\d{2}-\d{2})"', page)
    if not m:
        raise ValueError("no 'Data as of' date on IRCC's inventory page")
    as_of = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
    lines = {}
    parts = re.split(r"(<h4[^>]*>.*?</h4>)", main, flags=re.S)
    for i, part in enumerate(parts):  # permanent residence: one h4 per category
        head = clean(part) if part.startswith("<h4") else ""
        for group, line, _, name in PAGE_LINES:
            if group == "pr" and head == name:
                body = clean(parts[i + 1]) if i + 1 < len(parts) else ""
                f = re.search(r"Finalized ([\d,]+)", body)
                n = re.search(r"not yet finalized ([\d,]+)", body)
                w = re.search(r"(\d+)% are waiting for space", body)
                if f and n and w:
                    lines[line] = (num(n.group(1)), int(w.group(1)), num(f.group(1)))
    for group, line, _, name in PAGE_LINES:  # temporary residence: label, then its two figures
        if group == "tr":
            m2 = re.search(rf"{name} Finalized ([\d,]+)[^%]*?not yet finalized ([\d,]+)", text)
            if m2:
                lines[line] = (num(m2.group(2)), None, num(m2.group(1)))
    tr_total = re.search(r"Temporary residence Data as of [^.]*?\d{4}.*?Finalized ([\d,]+) applications since.*?not yet finalized ([\d,]+)", text)
    missing = [l for _, l, _, _ in PAGE_LINES if l not in lines]
    if missing or not tr_total:
        raise ValueError("IRCC's inventory page changed layout (missing: " + ", ".join(missing or ["temporary residence total"]) + ")")
    lines["tr-total"] = (num(tr_total.group(2)), None, num(tr_total.group(1)))
    return {"data_as_of": as_of, "page_date": modified.group(1) if modified else "", "lines": lines}


def rows_from(parsed, before, today):
    """CSV rows for the parsed page; figures in 'before' (the copy in use) become the month-before figures when the month changed."""
    prev = {r["line"]: r for r in before if r["group"] == "pr"}
    prev.update({"tr-" + r["line"] if r["line"] == "total" else r["line"]: r for r in before if r["group"] == "tr"})
    same = bool(before) and before[0]["data_as_of"] == parsed["data_as_of"]
    out = []

    def add(group, line, label, key, nf, wp, fin):
        p = prev.get(key) or {}
        out.append({"group": group, "line": line, "label": label, "not_finalized": nf, "waiting_pct": "" if wp is None else wp,
                    "finalized_ytd": "" if fin is None else fin,
                    "prev_not_finalized": (p.get("prev_not_finalized") if same else p.get("not_finalized")) or "",
                    "prev_waiting_pct": (p.get("prev_waiting_pct") if same else p.get("waiting_pct")) or "",
                    "data_as_of": parsed["data_as_of"], "prev_data_as_of": (p.get("prev_data_as_of") if same else p.get("data_as_of")) or "",
                    "page_date": parsed["page_date"] or today.isoformat(), "read_date": today.isoformat()})
    L = parsed["lines"]
    for group, line, label, _ in PAGE_LINES:
        if group == "pr":
            add("pr", line, label, line, *L[line])
    add("pr", "total", "Permanent residence", "total", sum(L[l][0] for l in ("economic", "family", "protection")), None, None)
    for group, line, label, _ in PAGE_LINES:
        if group == "tr":
            add("tr", line, label, line, *L[line])
    add("tr", "total", "Temporary residence", "tr-total", *L["tr-total"])
    return out


def refresh_local(today=None, fetch=None):
    """Read IRCC's page and save the local copy. Returns 'new month', 'no change' or raises when the page can't be read."""
    import watch as wt
    today = today or datetime.date.today()
    page = (fetch or wt.fetch)(SOURCE)
    if not page:
        raise ConnectionError("IRCC's inventory page couldn't be read (no internet, or the page moved)")
    if "<title>Not Found" in page[:5000]:
        raise ConnectionError("IRCC's inventory page moved (Not Found)")
    parsed = parse_page(page)
    before = load(current_path())
    if before and parsed["data_as_of"] < before[0]["data_as_of"]:
        return "no change"
    rows = rows_from(parsed, [{k: ("" if v is None else v) for k, v in r.items()} for r in before], today)
    path = local_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)
    return "no change" if before and before[0]["data_as_of"] == parsed["data_as_of"] else "new month"


def load(path=DATA):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return []
    out = []
    for r in rows:
        out.append({"group": (r.get("group") or "pr").strip(), "line": r["line"].strip(), "label": r["label"].strip(),
                    "not_finalized": num(r["not_finalized"]), "waiting_pct": num(r["waiting_pct"]),
                    "finalized_ytd": num(r.get("finalized_ytd")), "prev_not_finalized": num(r.get("prev_not_finalized")),
                    "prev_waiting_pct": num(r.get("prev_waiting_pct")), "data_as_of": r["data_as_of"].strip(),
                    "prev_data_as_of": (r.get("prev_data_as_of") or "").strip(),
                    "page_date": r["page_date"].strip(), "read_date": (r.get("read_date") or "").strip()})
    return out


def trend(now, prev):
    if now is None or prev is None:
        return ""
    return "up" if now > prev else "down" if now < prev else "same"


def change(now, prev):
    return now - prev if now is not None and prev is not None else None


def row_out(r, counts=None):
    out = {"line": r["line"], "label": r["label"], "not_finalized": r["not_finalized"],
           "change": change(r["not_finalized"], r["prev_not_finalized"]), "finalized_ytd": r["finalized_ytd"],
           "files_trend": trend(r["not_finalized"], r["prev_not_finalized"])}
    if r["group"] == "pr" and r["line"] != "total":
        out.update({"waiting_pct": r["waiting_pct"],
                    "active_pct": 100 - r["waiting_pct"] if r["waiting_pct"] is not None else None,
                    "pct_trend": trend(r["waiting_pct"], r["prev_waiting_pct"]), "yours": (counts or {}).get(r["line"], 0)})
    return out


def table(rows, group, counts=None):
    lines = [r for r in rows if r["group"] == group and r["line"] != "total"]
    if not lines:
        return None
    tot = next((r for r in rows if r["group"] == group and r["line"] == "total"), None)
    if tot is None:  # no published total: add up the lines
        tot = {"group": group, "line": "total", "label": "Total", "waiting_pct": None, "prev_waiting_pct": None}
        for k in ("not_finalized", "finalized_ytd", "prev_not_finalized"):
            vals = [r[k] for r in lines]
            tot[k] = sum(vals) if all(v is not None for v in vals) else None
    return {"label": tot["label"], "total": row_out(tot), "rows": [row_out(r, counts) for r in lines]}


def card(today=None, path=None, active=None):
    """The home card: PR categories with the firm's open files in each, and temporary residence lines."""
    today = today or datetime.date.today()
    rows = load(path or current_path())
    if not [r for r in rows if r["group"] == "pr"]:
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
    pr = table(rows, "pr", counts)
    return {
        "data_as_of": rows[0]["data_as_of"], "prev_data_as_of": rows[0]["prev_data_as_of"],
        "period_start": rows[0]["data_as_of"][:4] + "-01-01" if rows[0]["data_as_of"] else "",
        "page_date": page.isoformat() if page else "", "read_date": rows[0].get("read_date", ""), "source_name": SOURCE_NAME,
        "age": (today - page).days if page else None, "stale": page is None or (today - page).days > STALE_DAYS,
        "stale_after": STALE_DAYS, "source": SOURCE,
        "pr": pr, "tr": table(rows, "tr"), "rows": pr["rows"],
    }


def for_program(program, path=None):
    """The line for one case, or None when the program is not a PR category."""
    c = category_of(program)
    if not c:
        return None
    for r in load(path or current_path()):
        if r["group"] == "pr" and r["line"] == c:
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
    print(f"IRCC application inventory (data to {c['data_as_of']}; IRCC page {c['page_date']}{', OUT OF DATE' if c['stale'] else ''})")
    n = lambda v: "n/a" if v is None else f"{v:,}"  # noqa: E731
    d = lambda v: "n/a" if v is None else f"{v:+,}"  # noqa: E731
    p = lambda v: "n/a" if v is None else f"{v}%"  # noqa: E731
    for t in (c["pr"], c["tr"]):
        if not t:
            continue
        print()
        print(f"{t['label']}: {n(t['total']['not_finalized'])} ({d(t['total']['change'])})")
        pr = "waiting_pct" in t["rows"][0]
        head = f"  {'Category':<14}{'Inventory':>10}{'Change':>9}"
        print(head + (f"{'Active':>8}{'Waiting':>9}" if pr else "") + f"{'Finalized':>12}" + ("  Your files" if pr else ""))
        for r in t["rows"]:
            line = f"  {r['label']:<14}{n(r['not_finalized']):>10}{d(r['change']):>9}"
            if pr:
                line += f"{p(r['active_pct']):>8}{p(r['waiting_pct']):>9}"
            line += f"{n(r['finalized_ytd']):>12}"
            print(line + (f"  {r['yours']}" if pr else ""))
    print()
    print("'Waiting for space': complete files held until a yearly admission target space opens; not a processing delay.")
    print("Source: " + SOURCE)


if __name__ == "__main__":
    main()
