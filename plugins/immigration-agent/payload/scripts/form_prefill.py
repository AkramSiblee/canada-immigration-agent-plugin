#!/usr/bin/env python3
"""Build a plain-English Excel data sheet of answers for an IRCC form.

Usage:
  python3 scripts/form_prefill.py list
  python3 scripts/form_prefill.py build --form imm0008 --person "Full Name" --case 2026-001
  python3 scripts/form_prefill.py build --form imm5669 --person "Full Name" --report REPORT.json [--facts client-facts.csv] [--out DIR]

Guarantees:
  - It never fills, changes or submits an IRCC form. A person enters every answer.
  - Answers come only from an extraction report or the client's own facts file.
  - Conflicting answers are shown, never chosen.
  - Questions marked "client" (background, refusals, family, consent) are never filled from documents.
  - Passport, UCI and account numbers stay masked. The full number is copied from the original.
"""
import argparse
import csv
import datetime
import json
import os
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_extract as de  # noqa: E402

REPO = de.REPO
SPECS = REPO / "templates" / "form-specs"
TODAY = datetime.date.today()
RULES = {"auto", "client", "consultant", "sign", "firm"}
FIRM_KEYS = {"rep_name": "name", "rep_membership_id": "rcic", "rep_organization": "business", "rep_address": "address", "rep_phone": "phone", "rep_email": "email"}
ANY_DOC = {"family_name", "given_name", "date_of_birth", "uci", "passport_number", "sex", "birth_city", "birth_country"}
BY_TYPE = {"passport": {"expiry_date": "passport_expiry_date", "issue_date": "passport_issue_date", "nationality": "citizenship"},
           "marriage_certificate": {"marriage_date": "marriage_date"}}
READY = "Ready: please confirm"
CONFIRM = "Confirm against the original"
COPY = "Copy the full number from the original"
CONFLICT = "Conflict: documents disagree"
ASK = "Ask client"
MUST = "Client must answer"
YOU = "Consultant decides"
SIGN = "Signature needed"
FROM_FIRM = "From your firm profile: confirm"
NO_PROFILE = "Set up your firm profile"
EXPIRED = "Problem: expired"


def load_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_spec(form):
    index = {r["form"]: r for r in load_csv(SPECS / "index.csv")}
    if form not in index:
        sys.exit(f"ERROR: unknown form '{form}'. Available: {', '.join(sorted(index))}")
    rows = load_csv(SPECS / f"{form}.csv")
    for r in rows:
        if r["rule"] not in RULES or not r["key"] or not r["question"]:
            sys.exit(f"ERROR: bad row in {form}.csv: {r['question'][:40]}")
    return index[form], rows


def norm(value):
    return re.sub(r"\s+", " ", str(value)).strip().upper()


def add(pool, key, value, source, sure, method, value_hash=None, note=""):
    pool.setdefault(key, []).append({"value": value, "hash": value_hash or norm(value), "source": source, "sure": sure, "method": method, "note": note})


def facts_from_report(report, person):
    pool, used = {}, []
    for d in report["documents"]:
        name = de.doc_name(d)
        if not name or not de.same_person(person, name):
            continue
        used.append(d["file"])
        kinds = BY_TYPE.get(d["doc_type"], {})
        earlier_form = d["doc_type"] == "imm_form"
        for f in d["fields"]:
            # an earlier IRCC form holds the client's past answers to the same questions
            key = f["field"] if f["field"] in ANY_DOC or earlier_form else kinds.get(f["field"])
            if not key:
                continue
            where = f"page {f['page']}" if f["page"] else "form answer"
            add(pool, key, f["value"], f"{d['file']}, {where}", f["confidence"], f["method"], f.get("value_hash"), f["note"])
    return pool, used


def facts_from_file(path, person):
    client = {}
    if not path or not path.exists():
        return client
    for r in load_csv(path):
        if r.get("key") and r.get("value") and de.same_person(person, r.get("person", "")):
            value, digest = r["value"], None
            if r["key"] in de.SENSITIVE:
                digest, value = de.number_hash(value), de.mask(value)
            add(client, r["key"], value, r.get("source") or "Client facts", "M", "client", digest)
    return client


def expired(value):
    try:
        return datetime.date.fromisoformat(value) < TODAY
    except (TypeError, ValueError):
        return False


def resolve(row, docs, client):
    """Return (answer, status, source, how_sure, note)."""
    key, rule = row["key"], row["rule"]
    if rule == "sign":
        return "", SIGN, "", "", row["help"]
    if rule == "firm":  # your own details as the representative, from firm.py setup
        import firm
        value = firm.load_profile().get(FIRM_KEYS.get(key, ""), "")
        earlier = [c for c in docs.get(key, []) if c["method"] == "form"]
        changed = [c for c in earlier if value and norm(c["value"]) != norm(value)]
        note = ". ".join(x for x in (row["help"], ("An earlier IRCC form names " + "; ".join(f"'{c['value']}' ({c['source']})" for c in changed) + ". Check whether another representative is on file (Code s.24(2)(c))") if changed else "") if x)
        if not value:
            return "", NO_PROFILE if key != "rep_organization" else ASK, "", "", (note + ". Run firm.py setup").strip(". ") if key != "rep_organization" else note
        return value, FROM_FIRM, "Your firm profile", "", note
    if rule == "consultant":
        got = client.get(key, [])
        earlier = [c for c in docs.get(key, []) if c["method"] == "form"]
        note = ". ".join(x for x in (row["help"], "An earlier IRCC form said " + "; ".join(f"'{c['value']}' ({c['source']})" for c in earlier) if earlier else "") if x)
        return (got[0]["value"] if len(got) == 1 else ""), YOU, (got[0]["source"] if len(got) == 1 else ""), "", note
    found = list(client.get(key, []))
    if rule == "client":
        # an earlier IRCC form is shown for comparison only. It never answers a client question
        earlier = [c for c in docs.get(key, []) if c["method"] == "form"]
        said = "; ".join(f"'{c['value']}' ({c['source']})" for c in earlier)
        if len({c["hash"] for c in found}) == 1:
            changed = [c for c in earlier if c["hash"] != found[0]["hash"]]
            if changed:
                return "", CONFLICT, "; ".join([found[0]["source"]] + [c["source"] for c in changed]), "", f"Client now says '{found[0]['value']}', but an earlier IRCC form said {said}. A changed answer needs an explanation (IRPA s.40)"
            note = ". ".join(x for x in (row["help"], "Matches the earlier IRCC form" if earlier else "") if x)
            return found[0]["value"], READY, found[0]["source"], "Client's answer", note
        if found:
            return "", CONFLICT, "; ".join(c["source"] for c in found), "", "Client facts disagree: " + " / ".join(c["value"] for c in found)
        if earlier:
            return "", MUST, "", "", f"An earlier IRCC form said {said}. Confirm the current answer with the client. " + row["help"]
        return "", MUST, "", "", row["help"]
    found += docs.get(key, [])
    if not found:
        return "", ASK, "", "", row["help"]
    if len({c["hash"] for c in found}) > 1:
        return "", CONFLICT, "; ".join(c["source"] for c in found), "", "Sources disagree: " + " / ".join(f"{c['value']} ({c['source']})" for c in found)
    best = found[0]
    if len(found) > 1:
        best = next((c for c in found if c["sure"] == "H"), found[0])
    sources = "; ".join(c["source"] for c in found)
    sure = de.PLAIN_SURE.get(best["sure"], best["sure"])
    notes = [n for n in {c["note"] for c in found} if n]
    note = ". ".join(notes + ([row["help"]] if row["help"] else []))
    if key in de.SENSITIVE:
        return best["value"], COPY, sources, sure, note
    if key.endswith("expiry_date") and expired(best["value"]):
        return best["value"], EXPIRED, sources, sure, "This document has expired. Check whether a newer one exists"
    if best["sure"] == "L" or all(c["method"] == "vision" for c in found):
        return best["value"], CONFIRM, sources, sure, note
    return best["value"], READY, sources, sure, note


def build_rows(spec_rows, docs, client):
    return [{"section": r["section"], "no": r["no"], "question": r["question"], **dict(zip(("answer", "status", "source", "sure", "note"), resolve(r, docs, client)))} for r in spec_rows]


def next_path(folder, form, person=""):
    who = re.sub(r"[^a-z0-9]+", "-", person.lower()).strip("-")[:40]
    stem = f"{TODAY.isoformat()}-{form}-{who + '-' if who else ''}data-sheet"
    n = 1
    while True:
        p = folder / f"{stem}{'' if n == 1 else f'-v{n}'}.xlsx"
        if not p.exists():
            return p
        n += 1


def write_sheet(path, info, person, rows, used):
    import openpyxl
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    book = openpyxl.Workbook()
    book.remove(book.active)
    intro = [[f"Form: {info['title']} (version on IRCC's page: {info['version']}, checked {info['last_verified']})"],
             [f"Person: {person}"],
             ["Download the form from IRCC on the day you file. Old versions are returned."],
             ["This is a worksheet only. A person must enter each answer on the form and check it against the original."],
             ["Numbers shown as ****123 are hidden on purpose. Copy the full number from the original document."],
             ["Where documents disagree, no answer is suggested. Find out which is right."],
             ["Background, refusal, family and consent questions must come from the client."],
             ["Documents used: " + ("; ".join(used) if used else "none")]]
    intro += [[f"{k}: {v}"] for k, v in sorted(counts.items())]
    de.add_sheet(book, "Read me first", ["About this worksheet"], intro, [120])
    de.add_sheet(book, "Answers", ["Section", "Question no.", "Question on the form", "Proposed answer", "Status", "Where it came from", "How sure", "Note", "Entered on form?", "Correction"],
                 [[r["section"], r["no"], r["question"], r["answer"], r["status"], r["source"], r["sure"], r["note"], "", ""] for r in rows],
                 [24, 10, 60, 30, 28, 40, 20, 40, 14, 22])
    ask = [[r["section"], r["no"], r["question"], r["note"], ""] for r in rows if r["status"] in (ASK, MUST)]
    de.add_sheet(book, "Questions for client", ["Section", "Question no.", "Question", "Help", "Client's answer"], ask or [["", "", "No questions outstanding", "", ""]], [24, 10, 70, 44, 40])
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp.xlsx")
    os.close(fd)
    try:
        book.save(tmp)
        de.replace_with_retry(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return counts


def latest_report(folder):
    found = sorted(folder.glob("*.json"), key=os.path.getmtime) if folder.exists() else []
    return found[-1] if found else None


def cmd_list(_):
    for r in load_csv(SPECS / "index.csv"):
        print(f"{r['form']}: {r['title']} (version {r['version']}, checked {r['last_verified']})")


def cmd_build(a):
    info, spec_rows = load_spec(a.form)
    if a.case:
        case = de.active_case(a.case)
        report_path, facts, out = latest_report(case / "03-documents" / "_extraction"), case / "client-facts.csv", case / "05-forms-submissions"
        if a.report:
            report_path = pathlib.Path(a.report)
    else:
        if not a.report:
            sys.exit("ERROR: give --case or --report")
        report_path, facts = pathlib.Path(a.report), pathlib.Path(a.facts) if a.facts else None
        sub = report_path.parent.name if de.WORK_DIR in report_path.resolve().parents else "general"
        out = REPO / "Output" / sub
    if a.facts:
        facts = pathlib.Path(a.facts)
    if a.out:
        out = pathlib.Path(a.out)
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    docs, used = {}, []
    if report_path:
        if not report_path.exists():
            sys.exit(f"ERROR: not found: {report_path}")
        docs, used = facts_from_report(json.loads(report_path.read_text(encoding="utf-8")), a.person)
    rows = build_rows(spec_rows, docs, facts_from_file(facts, a.person))
    path = next_path(out, a.form, a.person)
    counts = write_sheet(path, info, a.person, rows, used)
    print(f"Questions: {len(rows)} | documents used: {len(used)}")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    print("Data sheet:", path)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Build an IRCC form data sheet")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("list"); x.set_defaults(fn=cmd_list)
    x = s.add_parser("build"); x.add_argument("--form", required=True); x.add_argument("--person", required=True); x.add_argument("--case"); x.add_argument("--report"); x.add_argument("--facts"); x.add_argument("--out"); x.set_defaults(fn=cmd_build)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
