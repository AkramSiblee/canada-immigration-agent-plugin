#!/usr/bin/env python3
"""Precedent library: the firm's own past letters and submissions, anonymised, sorted by issue, to start new drafts from.

Usage:
  python3 scripts/precedents.py add FILE --issue "study gap" --program study --outcome approved [--case CASE] [--note TEXT]
  python3 scripts/precedents.py approve ID          after you have read the anonymised text and found nothing identifying
  python3 scripts/precedents.py search WORDS... [--program P] [--outcome O] [--all]
  python3 scripts/precedents.py show ID
  python3 scripts/precedents.py list

Guarantees:
  - The library lives in cases/precedents/, so it is in every backup and never touched by agent updates.
  - Only an anonymised text copy is kept. Removed: the client's and family members' names from the case, application
    numbers, UCIs, passport-style numbers, email addresses, phone numbers and full dates (years are kept).
  - A new precedent is "not reviewed" until you approve it. Search shows approved ones only, unless --all.
  - Automatic anonymising misses things (addresses, employers, schools, rare facts). Read every precedent before approving.
  - A precedent is a starting point. Each new letter must be written for its own client's facts, and the IRB rule still
    applies: never reuse or rewrite a person's narrative, affidavit or evidence (CLAUDE.md rule 7).
"""
import argparse
import datetime
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import conflicts as cf  # noqa: E402
import doc_extract as de  # noqa: E402

LIB = cs.ROOT / "precedents"
OUTCOMES = ["approved", "refused", "pending", "withdrawn", "unknown"]
PATTERNS = [
    ("[EMAIL]", r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    ("[APPLICATION NO.]", r"\b[BEFGHNSVWX]\d{9}\b"),
    ("[UCI]", r"\b\d{4}-?\d{4}(?:-?\d{2})?\b"),
    ("[PHONE]", r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\d)|\+\d{1,3}[ .-]?\d{2,5}[ .-]?\d{3,5}[ .-]?\d{3,5}"),
    ("[DOCUMENT NO.]", r"\b[A-Z]{1,2}\d{6,9}\b"),
]


def die(msg):
    sys.exit("NOT SAVED: " + msg)


def read(path):
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            pages = de.read_pdf(path, 60)[0]
        elif ext == ".docx":
            pages = de.read_docx(path)
        elif ext in (".txt", ".md", ".text"):
            pages = de.read_text(path)
        else:
            die("use a Word, PDF or text file")
    except de.Skip as e:
        die(f"the file can't be read ({de.PLAIN_STATUS.get(e.status, e.status)})")
    text = "\n".join(t for _, t in pages).strip()
    if len(text) < 200:
        die("too little text was found (a scan?). Save the letter as Word or text first")
    return text


def names_in(folder):
    info = cs.read_case(folder)
    found = [info.get("client", "")] + [n for n, _ in cf.family_rows((folder / "case.md").read_text(encoding="utf-8"))] + [n for n, _ in cf.fact_names(folder)]
    parts = set()
    for n in found:
        n = n.strip()
        if len(n) >= 3:
            parts.add(n)
            parts.update(w for w in re.split(r"[\s,]+", n) if len(w) >= 3)
    return sorted(parts, key=len, reverse=True)


def anonymise(text, names):
    counts = {}
    for label, rx in PATTERNS:  # first, so an email address goes whole, not with only the name taken out
        text, n = re.subn(rx, label, text)
        if n:
            counts[label] = n
    for name in names:
        rx = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.I)
        text, n = rx.subn("[NAME]", text)
        if n:
            counts["names"] = counts.get("names", 0) + n
    text, n = re.subn(de.DATE_RX, lambda m: "[DATE " + (re.search(r"\d{4}", m.group(0)) or ["?"])[0] + "]", text, flags=re.I)
    if n:
        counts["[DATE]"] = n
    return text, counts


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "letter"


def entries():
    out = []
    for p in sorted(LIB.glob("*.md")) if LIB.exists() else []:
        text = p.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
        if not m:
            continue
        meta = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
        out.append({**meta, "path": p, "body": m.group(2)})
    return out


def get(ref):
    hits = [e for e in entries() if e.get("id") == ref]
    if not hits:
        die(f"no precedent {ref}. See: precedents.py list")
    return hits[0]


def cmd_add(a):
    path = pathlib.Path(a.file)
    if not path.is_file():
        die(f"no such file: {path}")
    if a.outcome not in OUTCOMES:
        die("outcome must be one of: " + ", ".join(OUTCOMES))
    if len(a.issue.strip()) < 3:
        die("say what issue the letter deals with (--issue)")
    text = read(path)
    folder = cs.find(a.case, include_closed=True) if a.case else None
    names = names_in(folder) if folder else []
    clean, counts = anonymise(text, names)
    LIB.mkdir(parents=True, exist_ok=True)
    pid = f"P{max((int(e['id'][1:]) for e in entries() if e.get('id', '')[1:].isdigit()), default=0) + 1:03d}"
    meta = {"id": pid, "issue": a.issue.strip(), "program": a.program.strip(), "outcome": a.outcome, "added": datetime.date.today().isoformat(),
            "reviewed": "no", "from_case": cs.read_case(folder).get("case_id", "") if folder else "", "note": (a.note or "").replace("\n", " ")}
    dest = LIB / f"{pid}-{slug(a.issue)}.md"
    dest.write_text("---\n" + "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n---\n" + clean + "\n", encoding="utf-8")
    print(f"Saved {pid} ({a.issue}, {a.program}, {a.outcome}) to {dest}")
    print("Removed: " + (", ".join(f"{v} {k}" for k, v in counts.items()) or "nothing found"))
    if not folder:
        print("No --case given, so names weren't known: none were removed.")
    print(f"Read it now for anything still identifying (addresses, employers, schools, rare facts), edit the file, then: precedents.py approve {pid}")


def cmd_approve(a):
    e = get(a.id)
    text = e["path"].read_text(encoding="utf-8")
    e["path"].write_text(re.sub(r"(?m)^reviewed: no$", f"reviewed: yes {datetime.date.today().isoformat()}", text, count=1), encoding="utf-8")
    print(f"{a.id} approved for reuse.")


def score(e, words):
    hay_meta = f"{e.get('issue', '')} {e.get('program', '')} {e.get('note', '')}".lower()
    body = e["body"].lower()
    return sum(5 * hay_meta.count(w) + min(body.count(w), 5) for w in words)


def cmd_search(a):
    words = [w.lower() for w in a.words if len(w) >= 2]
    pool = [e for e in entries() if (a.all or e.get("reviewed", "").startswith("yes"))
            and (not a.program or a.program.lower() in e.get("program", "").lower()) and (not a.outcome or e.get("outcome") == a.outcome)]
    ranked = sorted(((score(e, words), e) for e in pool), key=lambda x: -x[0])
    hits = [(s, e) for s, e in ranked if s > 0 or not words]
    if not hits:
        print("No precedent matches." + ("" if a.all else " Unreviewed ones are left out (--all shows them)."))
    for s, e in hits[:10]:
        print(f"{e['id']}  {e.get('issue', '')} | {e.get('program', '')} | {e.get('outcome', '')} | reviewed {e.get('reviewed', 'no')}" + (f" | {e['note']}" if e.get("note") else ""))
    if hits:
        print("Open one: precedents.py show ID. Write the new letter for the new client's own facts.")


def cmd_show(a):
    e = get(a.id)
    if not e.get("reviewed", "").startswith("yes"):
        print("NOT REVIEWED YET: check it for identifying details before any reuse.\n")
    print(e["path"].read_text(encoding="utf-8"))


def cmd_list(_):
    items = entries()
    if not items:
        print("The library is empty. Add a letter: precedents.py add FILE --issue ... --program ... --outcome ... --case CASE")
    for e in items:
        print(f"{e['id']}  {e.get('issue', '')} | {e.get('program', '')} | {e.get('outcome', '')} | reviewed {e.get('reviewed', 'no')}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Precedent library")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("add"); x.add_argument("file"); x.add_argument("--issue", required=True); x.add_argument("--program", required=True)
    x.add_argument("--outcome", required=True); x.add_argument("--case"); x.add_argument("--note"); x.set_defaults(fn=cmd_add)
    x = s.add_parser("approve"); x.add_argument("id"); x.set_defaults(fn=cmd_approve)
    x = s.add_parser("search"); x.add_argument("words", nargs="*"); x.add_argument("--program"); x.add_argument("--outcome"); x.add_argument("--all", action="store_true"); x.set_defaults(fn=cmd_search)
    x = s.add_parser("show"); x.add_argument("id"); x.set_defaults(fn=cmd_show)
    x = s.add_parser("list"); x.set_defaults(fn=cmd_list)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
