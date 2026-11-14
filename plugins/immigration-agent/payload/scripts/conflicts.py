#!/usr/bin/env python3
"""Conflict check across every case file, open and closed (CICC Code ss.15-18).

Usage:
  python3 scripts/conflicts.py check "Full Name" ["Other Name" ...] [--case CASE]
  python3 scripts/conflicts.py record CASE --result clear|consented|conflict --note TEXT
  python3 scripts/conflicts.py add-party "Name" --role ROLE [--case CASE] [--note TEXT]
  python3 scripts/conflicts.py parties
  python3 scripts/conflicts.py history [CASE]

Searched: every client, every family member listed in case.md, every name in client-facts.csv (applicants, spouses,
sponsors, employers, co-signers), the closed-files list, and other-parties.csv (people you declined, opposing or
third parties, employers and recruiters you have a link with).

Guarantees:
  - check never changes a case file. It adds one line to cases/conflict-checks.csv (add-only) so each check is on record.
  - Only record sets conflict_check in case.md, and only to the result the consultant gives.
  - A match is a prompt to review, not a finding that a conflict exists. No match doesn't prove there is none:
    the check only knows names recorded in the files.
"""
import argparse
import csv
import datetime
import difflib
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402

CHECKS = cs.ROOT / "conflict-checks.csv"
PARTIES = cs.ROOT / "other-parties.csv"
CHECK_FIELDS = ["date", "case", "searched", "matches", "result", "note", "recorded"]
PARTY_FIELDS = ["name", "role", "case", "note", "added"]
NAME_KEYS = re.compile(r"(^|_)(name|employer|sponsor|cosigner|co_signer)$|^(employer|sponsor)_name$")
SKIP_KEYS = re.compile(r"school|test|rep_|native|ircc|signed|name_change|variation")
RESULTS = {"clear": "yes", "consented": "yes", "conflict": "no"}
STRENGTH = {3: "Same name", 2: "Close match", 1: "Possible match"}


def norm(text):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return [t for t in re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split() if t not in {"mr", "mrs", "ms", "dr", "inc", "ltd", "corp"}]


def score(a, b):
    """3 same name (any order), 2 close (all of the shorter name's words found, or spelling within a letter or two), 1 possible."""
    ta, tb = norm(a), norm(b)
    if not ta or not tb:
        return 0
    if sorted(ta) == sorted(tb):
        return 3
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    found = [any(near(w, v) for v in long_) for w in short]
    if all(found) and (len(short) >= 2 or len(long_) == 1):
        return 2
    # a shared surname alone is common: flag it only when another word is spelled similarly too
    if len(short) >= 2 and any(f and len(w) >= 3 for w, f in zip(short, found)):
        rest = [w for w, f in zip(short, found) if not f]
        if any(ratio(w, v) >= 0.6 for w in rest for v in long_):
            return 1
    return 0


def ratio(x, y):
    return difflib.SequenceMatcher(None, x, y).ratio()


def near(x, y):
    """Same word, or a spelling variant (Sara/Sarah, Mohamed/Mohammed) for words of 4 letters or more."""
    return x == y or (min(len(x), len(y)) >= 4 and ratio(x, y) >= 0.8)


def family_rows(text):
    m = re.search(r"## Family members.*?\n((?:\|.*\n?)+)", text)
    out = []
    for line in (m.group(1).splitlines() if m else [])[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0]:
            out.append((cells[0], cells[1] if len(cells) > 1 and cells[1] else "family member"))
    return out


def fact_names(folder):
    path = folder / "client-facts.csv"
    if not path.exists():
        return []
    people, out = {}, []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key, value, person = (r.get("key") or "").strip().lower(), (r.get("value") or "").strip(), (r.get("person") or "").strip()
            if not value or SKIP_KEYS.search(key):
                continue
            if key in ("given_name", "family_name"):
                people.setdefault(person, {})[key] = value
            elif NAME_KEYS.search(key):
                out.append((value, f"{key.replace('_', ' ')} ({person or 'client facts'})"))
    for person, parts in people.items():
        full = " ".join(p for p in (parts.get("given_name"), parts.get("family_name")) if p)
        out.append((full, f"{person or 'person'} (client facts)"))
    return out


def index():
    """Every recorded name: (name, where, case folder name, open or closed)."""
    out = []
    for state, base in (("open", cs.ACTIVE), ("closed", cs.CLOSED)):
        for folder in cs.folders(base):
            try:
                info, text = cs.read_case(folder), (folder / "case.md").read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                out.append(("", "case.md unreadable: check this file by hand", folder.name, state))
                continue
            if info.get("client"):
                out.append((info["client"], "client", folder.name, state))
            out += [(n, f"{rel} (case.md)", folder.name, state) for n, rel in family_rows(text)]
            out += [(n, where, folder.name, state) for n, where in fact_names(folder)]
    closed_list = cs.CLOSED / "closed-files.csv"
    if closed_list.exists():
        known = {e[2] for e in out}
        with closed_list.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("folder") not in known and r.get("client"):
                    out.append((r["client"], "client (closed-files list)", r.get("folder") or r.get("case_id", ""), "closed"))
    for r in read(PARTIES):
        out.append((r["name"], f"other party: {r['role']}" + (f" ({r['note']})" if r.get("note") else ""), r.get("case") or "no file", "party"))
    return out


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append(path, fields, row):
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fields)
        if new:
            w.writeheader()
        w.writerow(row)


def search(names, own=None):
    hits, unreadable = [], []
    for name, where, folder, state in index():
        if own and folder == own:
            continue
        if not name:
            unreadable.append(folder)
            continue
        for wanted in names:
            s = score(wanted, name)
            if s:
                hits.append({"searched": wanted, "found": name, "strength": s, "where": where, "file": folder, "state": state})
    hits.sort(key=lambda h: (-h["strength"], h["file"]))
    return hits, unreadable


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def cmd_check(a):
    own = cs.find(a.case, include_closed=True).name if a.case else None
    hits, unreadable = search(a.names, own)
    print(f"Searched {len(a.names)} name(s) against every open and closed file and the other-parties list.")
    if not hits:
        print("No matching names found.")
    for h in hits:
        print(f"  {STRENGTH[h['strength']]}: '{h['searched']}' ~ '{h['found']}' | {h['where']} | {h['file']} ({h['state']})")
    for folder in unreadable:
        print(f"  Not checked: {folder} (case.md unreadable). Check it by hand.")
    append(CHECKS, CHECK_FIELDS, {"date": cs.TODAY.isoformat(), "case": own or "", "searched": "; ".join(a.names),
                                  "matches": "; ".join(f"{h['found']} ({h['file']})" for h in hits) or "none",
                                  "result": "", "note": "check run", "recorded": now()})
    if own:
        cs.add_log(cs.find(own, include_closed=True), f"Conflict check run on {len(a.names)} name(s): {len(hits)} match(es)")
    print("\nA match is a prompt to review, not a finding. No match only means no recorded name matched.")
    print("Also ask the client about links to other clients, employers or sponsors you act for (Code ss.15-18).")
    if own:
        print(f"Then record your decision: conflicts.py record {a.case} --result clear|consented|conflict --note \"...\"")


def cmd_record(a):
    folder = cs.find(a.case)
    ran = [r for r in read(CHECKS) if r["case"] == folder.name and r["note"] == "check run"]
    if not ran:
        cs.die(f"no conflict check on record for {folder.name}. Run: conflicts.py check \"Client name\" ... --case {a.case}")
    if a.result == "consented" and not re.search(r"writ|sign|consent", a.note, re.I):
        cs.die("'consented' needs written disclosure and the client's written, informed consent (Code s.15(1)). Say where it is filed in --note")
    cs.write_key(folder, "conflict_check", RESULTS[a.result])
    append(CHECKS, CHECK_FIELDS, {"date": cs.TODAY.isoformat(), "case": folder.name, "searched": ran[-1]["searched"], "matches": ran[-1]["matches"],
                                  "result": a.result, "note": a.note, "recorded": now()})
    cs.add_log(folder, f"Conflict check decision: {a.result}. {a.note}")
    print(f"{folder.name}: conflict_check = {RESULTS[a.result]} ({a.result})")
    if a.result == "conflict":
        print("Don't act until it is resolved. Some conflicts can't be consented to (Code s.16). Consider a non-engagement letter: /agreement")


def cmd_add_party(a):
    case = cs.find(a.case, include_closed=True).name if a.case else ""
    append(PARTIES, PARTY_FIELDS, {"name": a.name, "role": a.role, "case": case, "note": a.note or "", "added": cs.TODAY.isoformat()})
    print(f"Added to other-parties list: {a.name} ({a.role})")


def cmd_parties(_):
    rows = read(PARTIES)
    print(f"{len(rows)} other part{'y' if len(rows) == 1 else 'ies'} on record")
    for r in rows:
        print(f"  {r['name']} | {r['role']} | {r['case'] or 'no file'} | {r['note']} | added {r['added']}")


def cmd_history(a):
    folder = cs.find(a.case, include_closed=True).name if a.case else None
    rows = [r for r in read(CHECKS) if not folder or r["case"] == folder]
    for r in rows:
        print(f"  {r['date']} | {r['case'] or 'no file'} | searched: {r['searched']} | matches: {r['matches']} | {r['result'] or 'not decided'} | {r['note']}")
    if not rows:
        print("No conflict checks on record.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Conflict check across all case files")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("check"); x.add_argument("names", nargs="+"); x.add_argument("--case"); x.set_defaults(fn=cmd_check)
    x = s.add_parser("record"); x.add_argument("case"); x.add_argument("--result", required=True, choices=sorted(RESULTS)); x.add_argument("--note", required=True); x.set_defaults(fn=cmd_record)
    x = s.add_parser("add-party"); x.add_argument("name"); x.add_argument("--role", required=True); x.add_argument("--case"); x.add_argument("--note"); x.set_defaults(fn=cmd_add_party)
    x = s.add_parser("parties"); x.set_defaults(fn=cmd_parties)
    x = s.add_parser("history"); x.add_argument("case", nargs="?"); x.set_defaults(fn=cmd_history)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
