#!/usr/bin/env python3
"""Processing time tracker: each submitted file against IRCC's own published times, and a case-specific enquiry draft when a
file is past them.

Usage:
  python3 scripts/ptimes.py lines [--find TEXT]                   the processing-time lines IRCC publishes
  python3 scripts/ptimes.py set CASE --line LINE [--submitted D]  e.g. --line cec | spousal-abroad-roc | study:IN | work_extension | pr_card/existing_pr
  python3 scripts/ptimes.py check [--offline]                     read IRCC's times (public; nothing about clients is sent) and report every file
  python3 scripts/ptimes.py show CASE
  python3 scripts/ptimes.py enquiry CASE [--force]                draft the IRCC web form text for a file past the posted time
  python3 scripts/ptimes.py enquired CASE [--date D]              record that the web form was sent

Sources (IRCC's own feeds behind its "Check processing times" page):
  flpt-en.json                       PR and citizenship: time left for files submitted in each month ("We need more time..." when past)
  data-ptime-en.json                 visas and permits applied from outside Canada, by country of residence
  data-ptime-non-country-en.json     extensions, PR cards, IEC, some citizenship services

Guarantees:
  - The submitted date is the one recorded in the file (case.md "submitted", or the first "submitted" event in updates.csv).
  - A file is flagged only against IRCC's own numbers, read at most once a week, with the date IRCC last updated them.
  - The enquiry is a draft. The agent never logs in to IRCC or sends anything. IRCC says the web form is for files past the
    normal time, and a second enquiry won't speed things up, so the alerts don't ask again within 30 days.
  - A long delay can lead to a mandamus application: that is Federal Court, so refer it to a lawyer (CLAUDE.md rule 4).
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

BASE = "https://www.canada.ca/content/dam/ircc/documents/json/"
FEEDS = {"flpt": "flpt-en.json", "country": "data-ptime-en.json", "other": "data-ptime-non-country-en.json"}
STATE = cs.ROOT / ".ptimes-state.json"
EVERY_DAYS = 7
ENQUIRY_GAP = 30
BEYOND = "We need more time to process your application"
UNITS = {"minute": 1 / 1440, "day": 1, "week": 7, "month": 30.44, "year": 365.25}
GUESS = [  # program text -> line, for 'set' when no --line is given
    (r"\bcec\b|canadian experience", "cec"), (r"\bfsw\b|federal skilled worker", "fsw"), (r"express|\bee\b", None),
    (r"pnp|nominee", None), (r"spous|partner", None), (r"pgp|parent|grandparent", "pgp-roc"), (r"citizen", "citizen-grants"),
    (r"pr-?card", "pr_card/existing_pr"), (r"caregiver", "caregiver"), (r"start-?up|\bsuv\b", "startup-visa"), (r"self-?employ", "self-employed"),
    (r"\baip\b|atlantic", "aip"), (r"h&c|humanitarian", "humanitarian-roc"),
]


def die(msg):
    sys.exit("ERROR: " + msg)


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(STATE.name + ".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp, STATE)


def refresh():
    import watch as wt
    state = {"checked": datetime.datetime.now().isoformat(timespec="seconds")}
    for key, name in FEEDS.items():
        text = wt.fetch(BASE + name)
        if not text:
            raise ConnectionError(f"IRCC's {name} couldn't be read (no internet, or the page moved)")
        state[key] = json.loads(text.lstrip("﻿"))
    if not state["flpt"].get("current-flpt") or not state["country"].get("study"):
        raise ValueError("IRCC's processing time feeds changed layout")
    save_state(state)
    return state


def stale(today=None):
    checked = load_state().get("checked")
    if not checked:
        return True
    return ((today or datetime.date.today()) - datetime.date.fromisoformat(checked[:10])).days >= EVERY_DAYS


def days_of(text):
    """'32 days', 'About 7 months', '8 weeks', 'More than 10 years' -> days (float), or None."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(minute|day|week|month|year)s?", str(text), re.I)
    if not m:
        m2 = re.search(r"about (?:a|one) (day|week|month|year)", str(text), re.I)
        return UNITS[m2.group(1).lower()] if m2 else None
    return float(m.group(1)) * UNITS[m.group(2).lower()]


def lines(state):
    """Every line IRCC publishes: {line: description}."""
    out = {k: f"PR or citizenship: {k}" for k in (state.get("flpt", {}).get("current-flpt") or {})}
    for prog, by in (state.get("country") or {}).items():
        out[f"{prog}:CC"] = f"{prog} applied from outside Canada, by country of residence (CC = 2-letter code, e.g. IN)"
    for group, vals in (state.get("other") or {}).items():
        if isinstance(vals, dict) and group != "default-update":
            for k in vals:
                out[k if k == group else f"{group}/{k}"] = f"{group}: {k}"
    return out


def posted(state, line, submitted):
    """(posted time in days or None, IRCC's words, beyond flag from IRCC, last updated)."""
    if ":" in line:
        prog, cc = line.split(":", 1)
        words = (state.get("country", {}).get(prog) or {}).get(cc.upper())
        return days_of(words), words, None, (state.get("other", {}).get("default-update") or {}).get("lastupdated", "")
    if "/" in line or line in (state.get("other") or {}):
        group, _, key = line.partition("/")
        words = (state.get("other", {}).get(group) or {}).get(key or group)
        return days_of(words), words, None, (state.get("other", {}).get("default-update") or {}).get("lastupdated", "")
    flpt = state.get("flpt") or {}
    upd = (flpt.get("default-update") or {}).get("flpt_lastupdated", "")
    if line not in (flpt.get("current-flpt") or {}):
        return None, None, None, upd
    left = (flpt.get("wait-times") or {}).get(f"{line}-{submitted:%Y/%m}")
    if left == BEYOND:
        return None, left, True, upd
    if left and days_of(left) is not None:
        # time left for files submitted in that month, counted from IRCC's update date
        try:
            upd_day = datetime.datetime.strptime(upd, "%B %d, %Y").date()
        except ValueError:
            upd_day = datetime.date.today()
        return (upd_day - submitted).days + days_of(left), left, False, upd
    whole = flpt["current-flpt"][line]
    return days_of(whole), f"{whole} (for new applications)", None, upd


def submitted_of(folder, info):
    if info.get("submitted"):
        try:
            return datetime.date.fromisoformat(info["submitted"])
        except ValueError:
            return None
    import updates as up
    days = sorted(r["date"] for r in up.load(folder) if r["kind"] == "submitted")
    return datetime.date.fromisoformat(days[0]) if days else None


def status(folder, state=None, today=None):
    """None if the file isn't tracked, else a dict."""
    today = today or datetime.date.today()
    state = load_state() if state is None else state
    info = cs.read_case(folder)
    line = info.get("ircc_line", "")
    if not line:
        return None
    sub = submitted_of(folder, info)
    r = {"case": folder.name, "id": info.get("case_id", folder.name[:8]), "client": info.get("client", ""), "line": line, "submitted": sub,
         "elapsed": (today - sub).days if sub else None, "posted_days": None, "words": None, "updated": "", "past": False, "enquired": info.get("last_enquiry", "")}
    if not sub or not state:
        return r
    r["posted_days"], r["words"], beyond, r["updated"] = posted(state, line, sub)
    r["past"] = bool(beyond) or (r["posted_days"] is not None and r["elapsed"] > r["posted_days"])
    return r


def insert_keys(folder, keys):
    path = folder / "case.md"
    text = path.read_text(encoding="utf-8")
    for key in keys:
        if not re.search(rf"(?m)^{key}:", text.split("\n---", 1)[0]):
            text = re.sub(r"\A---\n", f"---\n{key}:\n", text, count=1)
    path.write_text(text, encoding="utf-8")


def cmd_lines(a):
    state = load_state()
    if not state:
        die("no processing times saved yet. Run: ptimes.py check")
    for k, v in sorted(lines(state).items()):
        if not a.find or a.find.lower() in (k + v).lower():
            print(f"{k:34} {v}")


def cmd_set(a):
    folder = cs.find(a.case)
    info = cs.read_case(folder)
    line = a.line
    if not line:
        for rx, guess in GUESS:
            if re.search(rx, info.get("program", ""), re.I):
                line = guess
                break
        if not line:
            die("give --line (see: ptimes.py lines). Express Entry: cec or fsw or pnp-ee. Spousal: spousal-abroad-roc / spousal-canada-roc (or -quebec). PNP: pnp-ee or pnp-base")
    state = load_state()
    if state and line.split(":")[0].split("/")[0] not in {k.split(":")[0].split("/")[0] for k in lines(state)}:
        die(f"IRCC publishes no line '{line}'. See: ptimes.py lines")
    if ":" in line and not re.fullmatch(r"[^:]+:[A-Za-z]{2}", line):
        die("a country line looks like study:IN (2-letter country code)")
    insert_keys(folder, ["ircc_line", "submitted", "last_enquiry"])
    cs.write_key(folder, "ircc_line", line)
    if a.submitted:
        cs.write_key(folder, "submitted", cs.parse_date(a.submitted, "--submitted").isoformat())
    cs.add_log(folder, f"Processing time tracked: {line}" + (f", submitted {a.submitted}" if a.submitted else ""))
    r = status(folder)
    print(f"{folder.name}: line {line}, submitted {r['submitted'] or 'not recorded (give --submitted, or record it with updates.py)'}")
    if r["words"]:
        print(f"IRCC: {r['words']} (updated {r['updated']})")


def describe(r):
    if not r["submitted"]:
        return "no submitted date recorded"
    if not r["words"]:
        return f"{r['elapsed']} days since filing; IRCC publishes no time for this line now"
    if r["words"] == BEYOND:
        return f"{r['elapsed']} days since filing. IRCC says: \"{BEYOND}\" for files submitted that month"
    return f"{r['elapsed']} days since filing; IRCC: {r['words']}" + (f" (about {round(r['posted_days'])} days in all)" if r["posted_days"] else "")


def cmd_check(a):
    if not a.offline:
        print("Reading IRCC's processing times (public pages; nothing about you or your clients is sent)...")
        try:
            refresh()
        except (ConnectionError, ValueError) as e:
            print(f"Not read: {e}. Using the times saved earlier.")
    state = load_state()
    if not state:
        die("no processing times saved yet")
    print(f"Times read {state['checked'][:10]}. PR and citizenship updated by IRCC on {state['flpt'].get('default-update', {}).get('flpt_lastupdated', '?')}.")
    n = 0
    for folder in cs.folders(cs.ACTIVE):
        r = status(folder, state)
        if r:
            n += 1
            print(f"  {'PAST ' if r['past'] else '     '}{r['id']} {r['client'][:22]:22} {r['line']:22} {describe(r)}")
    if not n:
        print("No file is tracked yet. Add one: ptimes.py set CASE --line LINE --submitted D")


def cmd_show(a):
    r = status(cs.find(a.case))
    if not r:
        die("this file isn't tracked. Run: ptimes.py set CASE --line LINE")
    print(f"{r['case']}: {r['line']}\n  {describe(r)}\n  Past the posted time: {'yes' if r['past'] else 'no'}" + (f"\n  Last enquiry: {r['enquired']}" if r["enquired"] else ""))


def cmd_enquiry(a):
    folder = cs.find(a.case)
    r = status(folder)
    if not r or not r["submitted"]:
        die("track the file first: ptimes.py set CASE --line LINE --submitted D")
    if not r["past"] and not a.force:
        die(f"this file isn't past IRCC's posted time ({describe(r)}). IRCC asks people to use the web form only then. --force to draft anyway")
    import updates as up
    refs = [e["reference"] for e in up.load(folder) if e["kind"] == "submitted" and e["reference"]]
    info = cs.read_case(folder)
    text = "\n".join([
        "IRCC web form: case-specific enquiry (draft)",
        "Where: IRCC web form, case-specific enquiry, as the client's representative (check the current menu on IRCC's web form page).",
        "",
        f"Applicant: {info.get('client', '')}",
        f"Application number: {refs[0] if refs else '[application number]'}",
        "UCI: [UCI]   Date of birth: [date of birth]",
        f"Application type: {r['line']} ({info.get('program', '')})",
        f"Submitted: {r['submitted']}",
        "",
        f"This application was submitted on {r['submitted']}, {r['elapsed']} days ago. "
        + ((f"IRCC's processing times page now says for applications submitted that month: \"{r['words']}\". " if ":" not in r["line"] and "/" not in r["line"] and r["line"] not in (load_state().get("other") or {})
            else f"IRCC's posted processing time for this application type is {r['words']}. ") if r["words"] else "")
        + f"(checked {datetime.date.today()}, IRCC data updated {r['updated']}).",
        "We have received no request or decision since the last update in the client's account. Could you please confirm the application's status, "
        "tell us whether anything is outstanding from the applicant, and give an estimated time for a decision?",
        "",
        "I am the authorized representative on file (IMM 5476).",
        "",
        "Do not send another enquiry within 30 days: IRCC says it won't speed processing.",
    ])
    out = folder / "06-correspondence"
    out.mkdir(exist_ok=True)
    path = out / f"{datetime.date.today().isoformat()}-webform-enquiry-draft.txt"
    n = 1
    while path.exists():
        n += 1
        path = out / f"{datetime.date.today().isoformat()}-webform-enquiry-draft-v{n}.txt"
    path.write_text(text + "\n", encoding="utf-8")
    cs.add_log(folder, f"Web form enquiry drafted ({path.name})")
    print(text)
    print(f"\nSaved: {path}\nAfter sending it: ptimes.py enquired {r['id']}")


def cmd_enquired(a):
    folder = cs.find(a.case)
    day = cs.parse_date(a.date, "--date") if a.date else datetime.date.today()
    insert_keys(folder, ["last_enquiry"])
    cs.write_key(folder, "last_enquiry", day.isoformat())
    cs.add_log(folder, f"IRCC web form enquiry sent {day}")
    print(f"{folder.name}: enquiry sent {day}. The alerts won't ask again for {ENQUIRY_GAP} days.")


def issues(folder, today, state=None):
    """Alerts for one case: (rank, kind, tier, text, step, day)."""
    try:
        r = status(folder, state, today)
    except (OSError, ValueError, KeyError) as e:
        return [(3, "Processing time", "unreadable", f"Could not check processing time ({type(e).__name__})", "Check ircc_line and submitted in case.md", None)]
    if not r or not r["past"]:
        return []
    try:
        last = datetime.date.fromisoformat(r["enquired"]) if r["enquired"] else None
    except ValueError:
        last = None
    if last and (today - last).days < ENQUIRY_GAP:
        return []
    if last:
        return [(3, "Processing time", "after enquiry", f"Still past IRCC's posted time; enquiry sent {last}. {describe(r)}",
                 "Check the IRCC account and the client's file; for a long delay, mandamus is Federal Court: refer to a lawyer", None)]
    return [(2, "Processing time", "past", f"Past IRCC's posted time: {describe(r)}", "Check the IRCC account, then draft an enquiry: ptimes.py enquiry CASE", None)]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Processing time tracker")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("lines"); x.add_argument("--find"); x.set_defaults(fn=cmd_lines)
    x = s.add_parser("set"); x.add_argument("case"); x.add_argument("--line"); x.add_argument("--submitted"); x.set_defaults(fn=cmd_set)
    x = s.add_parser("check"); x.add_argument("--offline", action="store_true"); x.set_defaults(fn=cmd_check)
    x = s.add_parser("show"); x.add_argument("case"); x.set_defaults(fn=cmd_show)
    x = s.add_parser("enquiry"); x.add_argument("case"); x.add_argument("--force", action="store_true"); x.set_defaults(fn=cmd_enquiry)
    x = s.add_parser("enquired"); x.add_argument("case"); x.add_argument("--date"); x.set_defaults(fn=cmd_enquired)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
