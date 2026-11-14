#!/usr/bin/env python3
"""Watch IRCC's form pages and fee list for changes the agent doesn't know about yet.

Usage:
  python3 scripts/watch.py check [--forms-only | --fees-only]
  python3 scripts/watch.py status
  python3 scripts/watch.py accept-fees          (agent maintainers only: make today's IRCC fee list the baseline)

Forms: each form the agent has a worksheet for (templates/form-specs/index.csv) is compared with the "Last updated"
date on its IRCC page. A newer version means the worksheet and autofill may not match the form: autofill refuses it
until the agent is updated.
Fees: every amount on IRCC's fee list (ircc.canada.ca/english/information/fees/fees.asp) is compared with the amounts
the agent's fee table was checked against (templates/watch/fees-baseline.csv).

Guarantees:
  - It only reads public IRCC pages. Nothing about you or your clients is sent.
  - It changes no case file. Results go to cases/.watch-state.json, which the daily alerts and the dashboard read.
  - A page that can't be read is reported as not checked, never as unchanged.
"""
import argparse
import csv
import datetime
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402

REPO = cs.REPO
INDEX = REPO / "templates" / "form-specs" / "index.csv"
BASELINE = REPO / "templates" / "watch" / "fees-baseline.csv"
STATE = cs.ROOT / ".watch-state.json"
FEES_URL = "https://ircc.canada.ca/english/information/fees/fees.asp"
FORM_PAGE = "https://www.canada.ca/en/immigration-refugees-citizenship/services/application/application-forms-guides/{}.html"
EVERY_DAYS = 7
MIN_FEE_ROWS = 30  # fewer rows than this means the page layout changed, not that fees were removed


def fetch(url):
    """Page text, or None when it can't be read. Uses curl when available (canada.ca can stall other clients)."""
    curl = shutil.which("curl")
    try:
        if curl:
            r = subprocess.run([curl, "-sSL", "--fail", "--max-time", "90", "-A", "Mozilla/5.0", url], capture_output=True, timeout=110)
            if r.returncode == 0 and r.stdout:
                return r.stdout.decode("utf-8", "replace")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
    except Exception:
        return None


def clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("–", "-").replace("—", "-").replace("’", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


# ---- forms ----
def page_version(page, form):
    """(the 'Last updated' text next to the form's PDF link, the PDF link) from an IRCC form page, or (None, None)."""
    m = re.search(rf'href="([^"]*/{re.escape(form)}e?\.pdf)"', page, re.I)
    if not m:
        return None, None
    after = html.unescape(page[m.end():m.end() + 3000])  # IRCC writes "June&nbsp;2026" on some pages
    badge = re.search(r"Last updated:\s*([A-Za-z]+)\s+(\d{4})", after)
    return (f"{badge.group(1)} {badge.group(2)}" if badge else None), m.group(1)


def same_version(badge, recorded):
    """IRCC shows 'September 2023'; the index may add notes after it ('January 2023 (page); ...')."""
    return bool(badge) and recorded.lower().startswith(badge.lower())


def index_rows():
    with INDEX.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check_forms(previous):
    out = {}
    for r in index_rows():
        form = r["form"]
        result = {"title": r["title"], "agent_version": r["version"], "status": "not checked", "badge": None, "pdf": None}
        for url in dict.fromkeys((r["source_url"], FORM_PAGE.format(form))):
            page = fetch(url)
            badge, pdf = page_version(page, form) if page else (None, None)
            if pdf:
                result.update(badge=badge, pdf=pdf, page=url)
                break
        if not result["pdf"]:
            result["status"] = "not checked"
        elif not result["badge"]:
            result["status"] = "no version shown"
        elif same_version(result["badge"], r["version"]):
            old = (previous.get(form) or {}).get("pdf")
            result["status"] = "republished" if old and old != result["pdf"] else "current"
        else:
            result["status"] = "new version"
        out[form] = result
    return out


# ---- fees ----
def parse_fees(page):
    """[(section, service, amount)] from IRCC's fee list: every table row under each heading that ends in an amount."""
    rows = []
    page = re.sub(r"<h[1-6][^>]*modal-title[^>]*>.*?</h[1-6]>", " ", page, flags=re.S | re.I)  # pop-up help inside a table cell isn't a section
    for title, body in re.findall(r"<h[23][^>]*>(.*?)</h[23]>(.*?)(?=<h[23][\s>]|$)", page, re.S | re.I):
        section = clean(title)
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S | re.I):
            cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
            if len(cells) >= 2:
                amount = re.sub(r"[$,\s]", "", cells[-1])
                if re.fullmatch(r"\d+(\.\d{2})?", amount):
                    rows.append((section, cells[0], f"{float(amount):.2f}"))
    return rows


def read_baseline():
    if not BASELINE.exists():
        return None
    with BASELINE.open(encoding="utf-8", newline="") as f:
        return [(r["section"], r["service"], r["amount"]) for r in csv.DictReader(f)]


def compare_fees(base, now):
    """Changed, added and removed amounts, matched by section, service and (when a line repeats, as for the two
    caregiver programs) its place among the lines with the same name."""
    def key(rows):
        seen, out = {}, {}
        for s, v, a in rows:
            n = seen[(s, v)] = seen.get((s, v), 0) + 1
            out[(s, v, n)] = a
        return out
    b, n = key(base), key(now)
    changes = [{"section": k[0], "service": k[1], "was": b[k], "now": n[k], "kind": "changed"} for k in n if k in b and b[k] != n[k]]
    changes += [{"section": k[0], "service": k[1], "was": "", "now": n[k], "kind": "new"} for k in n if k not in b]
    changes += [{"section": k[0], "service": k[1], "was": b[k], "now": "", "kind": "no longer listed"} for k in b if k not in n]
    return changes


def check_fees():
    page = fetch(FEES_URL)
    rows = parse_fees(page) if page else []
    if len(rows) < MIN_FEE_ROWS:
        return {"status": "not checked", "reason": "IRCC's fee page couldn't be read" if not page else "IRCC's fee page layout changed", "changes": []}
    base = read_baseline()
    if base is None:
        return {"status": "no baseline", "changes": [], "rows": len(rows)}
    modified = re.search(r'dateModified">\s*(\d{4}-\d{2}-\d{2})', page)
    changes = compare_fees(base, rows)
    return {"status": "changed" if changes else "current", "changes": changes, "rows": len(rows), "page_modified": modified.group(1) if modified else ""}


# ---- state ----
def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(STATE.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    os.replace(tmp, STATE)


def check(forms=True, fees=True):
    state = load_state()
    if forms:
        state["forms"] = check_forms(state.get("forms", {}))
    if fees:
        state["fees"] = check_fees()
    state["checked"] = datetime.datetime.now().isoformat(timespec="seconds")
    state["agent_version"] = (REPO / "VERSION").read_text(encoding="utf-8").strip() if (REPO / "VERSION").exists() else ""
    save_state(state)
    return state


def stale(today=None):
    today = today or datetime.date.today()
    state = load_state()
    if not state.get("checked"):
        return True
    if state.get("agent_version") != ((REPO / "VERSION").read_text(encoding="utf-8").strip() if (REPO / "VERSION").exists() else ""):
        return True  # the agent was updated: its worksheets and fee table may now match
    return (today - datetime.date.fromisoformat(state["checked"][:10])).days >= EVERY_DAYS


def findings(state=None):
    """Plain-language findings for alerts and the dashboard: (kind, text, step)."""
    state = load_state() if state is None else state
    out = []
    forms = state.get("forms") or {}
    unchecked = [" ".join(r["title"].split(" ", 2)[:2]) for r in forms.values() if r["status"] in ("not checked", "no version shown")]
    if len(unchecked) > 3:
        out.append(("Form version", f"{len(unchecked)} forms couldn't be checked on IRCC's pages (no internet, or IRCC changed its pages)", "Run /watch again later, and check each form's page on canada.ca before filing"))
    for form, r in sorted(forms.items()):
        label = " ".join(r["title"].split(" ", 2)[:2])
        if r["status"] in ("not checked", "no version shown") and len(unchecked) > 3:
            continue
        if r["status"] == "new version":
            out.append(("Form version", f"IRCC has a newer {label} (Last updated: {r['badge']}). The agent's worksheet is for {r['agent_version']}",
                        "Don't autofill it until the agent is updated. Fill the new version yourself from the worksheet answers, and check every question"))
        elif r["status"] == "republished":
            out.append(("Form version", f"IRCC republished the {label} file (same version date, {r['badge']})", "Download the blank again before filling: autofill.py fetch"))
        elif r["status"] in ("not checked", "no version shown"):
            out.append(("Form version", f"{label}: version couldn't be checked on IRCC's page", "Check the form's page on canada.ca before filing"))
    fees = state.get("fees") or {}
    for c in fees.get("changes", []):
        what = f"{c['section']}: {c['service']}"
        text = {"changed": f"IRCC fee changed: {what} was ${c['was']}, now ${c['now']}", "new": f"New IRCC fee listed: {what} ${c['now']}",
                "no longer listed": f"IRCC fee no longer listed: {what} (was ${c['was']})"}[c["kind"]]
        out.append(("Fee change", text, "Use IRCC's amount. The agent's fee table may be out of date until the next update"))
    if fees.get("status") == "not checked":
        out.append(("Fee change", f"Fees couldn't be checked: {fees.get('reason', '')}", "Check IRCC's fee list before quoting or paying fees"))
    return out


def cmd_check(a):
    print("Reading IRCC's form pages and fee list (public pages; nothing about you or your clients is sent)...")
    state = check(forms=not a.fees_only, fees=not a.forms_only)
    forms = state.get("forms") or {}
    counts = {}
    for r in forms.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    if not a.fees_only:
        print(f"Forms: {len(forms)} checked | " + " | ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    fees = state.get("fees") or {}
    if not a.forms_only:
        print(f"Fees: {fees.get('status')}" + (f" ({fees.get('rows')} amounts, IRCC page modified {fees.get('page_modified') or 'unknown'})" if fees.get("rows") else "")
              + (f": {fees.get('reason')}" if fees.get("reason") else ""))
    found = findings(state)
    for kind, text, step in found:
        print(f"  {kind}: {text}. {step}.")
    if not found:
        print("No changes found: every form version and fee matches what the agent knows.")


def cmd_status(_):
    state = load_state()
    print("Last check:", state.get("checked", "never"), f"(agent {state.get('agent_version', '?')})")
    for kind, text, step in findings(state):
        print(f"  {kind}: {text}. {step}.")


def cmd_accept_fees(_):
    page = fetch(FEES_URL)
    rows = parse_fees(page) if page else []
    if len(rows) < MIN_FEE_ROWS:
        cs.die("IRCC's fee page couldn't be read, so the baseline wasn't changed")
    old = read_baseline() or []
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    with BASELINE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["section", "service", "amount"])
        w.writerows(rows)
    print(f"Baseline set from today's IRCC fee list: {len(rows)} amounts" + (f", {len(compare_fees(old, rows))} change(s) from the previous baseline." if old else "."))
    print("Check knowledge/11-forms-fees-processing/fee-schedule.md matches, then release.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Watch IRCC form versions and fees")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("check"); g = x.add_mutually_exclusive_group(); g.add_argument("--forms-only", action="store_true"); g.add_argument("--fees-only", action="store_true"); x.set_defaults(fn=cmd_check)
    x = s.add_parser("status"); x.set_defaults(fn=cmd_status)
    x = s.add_parser("accept-fees"); x.set_defaults(fn=cmd_accept_fees)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
