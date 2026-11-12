#!/usr/bin/env python3
"""Knowledge-base freshness report.

Usage:
  python3 scripts/kb_status.py                 # full report
  python3 scripts/kb_status.py --brief         # one-line summary (used by SessionStart hook)
  python3 scripts/kb_status.py --stale         # only STALE / SEED files
  python3 scripts/kb_status.py --domain 02-pnp # one domain
"""
import re
import sys
import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent / "knowledge"
TODAY = datetime.date.today()


def front(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    data = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()
    return data


def main():
    brief = "--brief" in sys.argv
    only_stale = "--stale" in sys.argv
    dom = sys.argv[sys.argv.index("--domain") + 1] if "--domain" in sys.argv else None
    rows = []
    for p in sorted(ROOT.rglob("*.md")):
        d = front(p)
        if "status" not in d:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if dom and not rel.startswith(dom):
            continue
        lv = d.get("last_verified", "null")
        age = None
        if lv not in ("null", "", "None"):
            try:
                age = (TODAY - datetime.date.fromisoformat(lv)).days
            except ValueError:
                pass
        limit = int(d.get("review_every_days", 90))
        if d["status"] == "needs-seed":
            state = "SEED"
        elif age is None or age > limit:
            state = "STALE"
        else:
            state = "OK"
        rows.append((state, rel, age, limit))
    c = {s: sum(1 for r in rows if r[0] == s) for s in ("OK", "STALE", "SEED")}
    print(f"KB: {len(rows)} files | OK {c['OK']} | STALE {c['STALE']} | NEEDS-SEED {c['SEED']}")
    if brief:
        return
    for state, rel, age, limit in rows:
        if only_stale and state == "OK":
            continue
        print(f"{state:5} {rel:72} age={age} limit={limit}")


if __name__ == "__main__":
    main()
