#!/usr/bin/env python3
"""Case readiness report: everything still open on a file, in one Excel workbook, before filing.

Usage:
  python3 scripts/readiness.py report CASE [--form imm5257 --form imm5645] [--person "Full Name"] [--out DIR]

It joins checks that already exist: document extraction flags, form worksheet answers, intake steps,
deadlines and expiring documents, client updates not yet sent, and client account issues.
Guarantees:
  - It never says a file is ready to file. The best result is "no blocking items found"; the RCIC decides.
  - It changes nothing in the case. It only reads and writes the report.
  - Missing inputs (no extraction yet, no forms chosen) are listed as items to do, never silently skipped.
"""
import argparse
import datetime
import json
import re
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import alerts as al  # noqa: E402
import billing as bl  # noqa: E402
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402
import updates as up  # noqa: E402

MUST, URGENT, TODO = "Must fix before filing", "Urgent", "To do"
ORDER = {MUST: 0, URGENT: 1, TODO: 2}
# Forms usually needed, by program topic (see alerts.PROGRAMS). Pass --form to choose exactly.
FORMS_BY_TOPIC = {
    "family": ["imm1344", "imm0008", "imm5406", "imm5669", "imm5532", "imm5476"],
    "pgp": ["imm1344", "imm5768", "imm0008", "imm5406", "imm5669", "imm5562", "imm5476"],
    "visitor": ["imm5257", "imm5645", "imm5476"],
    "study": ["imm1294", "imm5645", "imm5476"],
    "work": ["imm1295", "imm5645", "imm5476"],
    "citizenship": ["cit0002", "imm5476"],
    "prstatus": ["imm5444", "imm5476"],
}
OPEN = {fp.CONFLICT: MUST, fp.EXPIRED: MUST, fp.NO_PROFILE: MUST, fp.MUST: MUST, fp.ASK: MUST,
        fp.YOU: TODO, fp.SIGN: TODO, fp.READY: TODO, fp.CONFIRM: TODO, fp.COPY: TODO, fp.FROM_FIRM: TODO}


def item(priority, source, what, step):
    return {"priority": priority, "source": source, "what": what, "step": step}


def default_forms(program, marital=""):
    topics = al.topics_for(program)
    if re.search(r"super", program, re.I):
        topics.discard("pgp")  # a super visa is a visitor application, not a sponsorship
    forms = []
    for topic in sorted(topics):
        for f in FORMS_BY_TOPIC.get(topic, []):
            if f not in forms:
                forms.append(f)
    if "cit0002" in forms and re.search(r"proof|certificate|descent|c-?3", program, re.I):
        forms[forms.index("cit0002")] = "cit0001"  # proof of citizenship, not a grant
    if "cit0002" in forms and re.search(r"minor|5\(2\)", program, re.I):
        forms[forms.index("cit0002")] = "cit0003"  # a minor's s.5(2) application
    if forms and re.search(r"common.?law", f"{program} {marital}", re.I) and "imm5409" not in forms:
        forms.insert(len(forms) - 1 if forms[-1] == "imm5476" else len(forms), "imm5409")
    return forms


CHECKLISTS = de.REPO / "templates" / "checklists"
FOUND, MISSING, IF_APPLIES, BY_HAND = "Found", "Missing", "Only if it applies", "Confirm by hand"
CHECKLIST_STALE_DAYS = 180


def checklist_for(program):
    """The official checklist for a program: (index row, item rows), or (None, [])."""
    for row in fp.load_csv(CHECKLISTS / "index.csv"):
        if program and re.search(row["programs"], program, re.I):
            return row, fp.load_csv(CHECKLISTS / f"{row['checklist']}.csv")
    return None, []


def detectors(spec):
    """'type:passport|file:pass|travel' -> [('type', 'passport'), ('file', 'pass|travel')]: a file pattern keeps its own '|'."""
    out = []
    for part in (spec or "").split("|"):
        m = re.match(r"(type|form|file):(.*)$", part)
        if m:
            out.append([m.group(1), m.group(2)])
        elif out:
            out[-1][1] += "|" + part
    return out


def case_files(folder):
    """Document file names in 03-documents (names only; client-ids folders are skipped, never opened)."""
    root = folder / "03-documents"
    if not root.exists():
        return []
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*")
                  if p.is_file() and not {"client-ids", "_extraction"} & {x.lower() for x in p.relative_to(root).parts})


def matches(spec, docs, files):
    hits = []
    for kind, value in detectors(spec):
        for d in docs:
            number = next((f["value"] for f in d.get("fields", []) if f["field"] == "form_number"), "")
            if (kind == "type" and d.get("doc_type") == value) or (kind == "form" and squash(number) == squash(value)):
                hits.append(d["file"])
        if kind == "file":
            hits += [f for f in files if re.search(value, pathlib.Path(f).name, re.I)]
    return sorted(set(hits))


def squash(text):
    return re.sub(r"\s+", "", text or "").upper()


def checklist_rows(folder, program, docs):
    """Each checklist item with its status. Returns (index row, rows)."""
    info, items = checklist_for(program)
    files = case_files(folder)
    rows = []
    for it in items:
        hits = matches(it["detect"], docs, files) if it["detect"] else []
        status = FOUND if hits else BY_HAND if not it["detect"] else MISSING if it["required"] == "always" else IF_APPLIES
        rows.append({**it, "status": status, "files": ", ".join(hits[:4]) + (f" (+{len(hits) - 4})" if len(hits) > 4 else "")})
    return info, rows


def checklist_items(info, rows, today):
    if not info:
        return []
    label = f"{info['source']} ({info['version']})"
    out = [item(MUST, "Checklist", f"Missing: {r['item']} [{label} item {r['no']}]"[:300], "Add it to 03-documents and run the extraction again, or record why it isn't needed")
           for r in rows if r["status"] == MISSING]
    maybe = sum(1 for r in rows if r["status"] == IF_APPLIES)
    by_hand = sum(1 for r in rows if r["status"] == BY_HAND)
    if maybe or by_hand:
        out.append(item(TODO, "Checklist", f"{maybe} item(s) apply only in some situations and {by_hand} can't be detected: see the Checklist tab", "Tick each one that applies, or note why it doesn't"))
    try:
        age = (today - datetime.date.fromisoformat(info["read"])).days
    except ValueError:
        age = CHECKLIST_STALE_DAYS + 1
    if age > CHECKLIST_STALE_DAYS or info.get("confidence") != "H":
        why = f"read {info['read']}" + ("; this checklist is old or for paper files, confirm against the online application" if info.get("confidence") != "H" else "")
        out.append(item(URGENT, "Checklist", f"{label}: {why}", f"Check IRCC's current version: {info['source_url']}"))
    return out


LETTER_NAMES = r"letter|explanation|\bloe\b|submission"


def letter_items(folder, docs):
    """Run the letter fact check on drafted letters in 05-forms-submissions and 06-correspondence."""
    import letter_check as lc
    out = []
    for sub in ("05-forms-submissions", "06-correspondence"):
        for path in sorted((folder / sub).glob("*")):
            if path.suffix.lower() not in (".docx", ".pdf") or not re.search(LETTER_NAMES, path.name, re.I) or "readiness" in path.name:
                continue
            try:
                found = lc.check(lc.letter_text(path), docs)
            except SystemExit:
                out.append(item(TODO, "Letters", f"{path.name}: couldn't be read for the fact check", "Check its facts by hand"))
                continue
            for sev, msg in found:
                out.append(item({"HIGH": MUST, "MEDIUM": URGENT}.get(sev, TODO), "Letters", f"{path.name}: {msg}"[:300],
                                "Correct the letter, or confirm the documents are what's out of date"))
    return out


def fact(client, key):
    return next((x["value"] for x in client.get(key, []) if x.get("value")), "")


def supervisa_items(folder, person, docs, today):
    """Super visa host income, from the Notices of Assessment and the client facts (family_size, visitor_income, application_date)."""
    client = fp.facts_from_file(folder / "client-facts.csv", person)
    size = de.amount(fact(client, "family_size"))
    letter = next((f["value"] for d in docs if d.get("doc_type") == "letter_of_invitation" for f in d["fields"] if f["field"] == "family_size"), None)
    out = [item(URGENT, "Documents", f"Super visa: no {label} found in the latest extraction", "Add it to 03-documents and run the extraction again")
           for kind, label in (("letter_of_invitation", "letter of invitation"), ("insurance_policy", "insurance policy")) if not any(d.get("doc_type") == kind for d in docs)]
    if letter and size is not None and int(size) != int(letter):
        out.append(item(MUST, "Income", f"Super visa: the letter of invitation says family size {letter}, the client facts say {int(size)}",
                        "Recount (host, spouse, dependent children, the visitors, earlier super visa guests, sponsored persons still in effect) and correct the letter or the facts"))
    if size is None and letter:
        size = de.amount(letter)
    if size is None:
        return out + [item(MUST, "Income", "Super visa: no family size recorded, so the host income can't be checked",
                           "Add family_size to client-facts.csv, or make sure the letter of invitation states it (host, spouse, dependent children, the visitors, earlier super visa guests and sponsored persons still in effect)")]
    try:
        applying = datetime.date.fromisoformat(fact(client, "application_date")[:10])
    except ValueError:
        applying = today
    visitor = de.amount(fact(client, "visitor_income"))
    for sev, _, msg in de.supervisa_income(de.notice_income(docs), int(size), applying, visitor):
        priority = {"OK": TODO, "HIGH": MUST, "MEDIUM": URGENT}.get(sev, TODO)
        step = "Confirm the notices are the host's and co-signer's only" if sev == "OK" else "Get the missing proof, or reassess the family size or a co-signer"
        out.append(item(priority, "Income", ("Super visa: " + msg)[:300], step))
    return out


def worksheet_items(folder, person, forms, report_path):
    """Open worksheet answers per form: (items, per-form counts, open question rows)."""
    docs = {}
    if report_path:
        docs, _ = fp.facts_from_report(json.loads(report_path.read_text(encoding="utf-8")), person)
    client = fp.facts_from_file(folder / "client-facts.csv", person)
    items, counts, questions = [], [], []
    for form in forms:
        info, spec = fp.load_spec(form)
        rows = fp.build_rows(spec, docs, client)
        label = " ".join(info["title"].split(" ")[:2])  # e.g. "IMM 5257"
        tally = {}
        for r in rows:
            tally[r["status"]] = tally.get(r["status"], 0) + 1
            if OPEN.get(r["status"]) == MUST:
                questions.append([label, r["section"], r["no"], r["question"], r["status"], r["note"]])
        counts.append([label, len(rows)] + [tally.get(s, 0) for s in (fp.READY, fp.CONFIRM, fp.COPY, fp.FROM_FIRM, fp.MUST, fp.ASK, fp.CONFLICT, fp.EXPIRED, fp.YOU, fp.SIGN, fp.NO_PROFILE)])
        for r in rows:
            if r["status"] in (fp.CONFLICT, fp.EXPIRED):
                items.append(item(MUST, label, f"{r['question'][:90]}: {r['status']}", r["note"][:200] or "Resolve before filing"))
        unanswered = tally.get(fp.MUST, 0) + tally.get(fp.ASK, 0)
        if unanswered:
            items.append(item(MUST, label, f"{unanswered} question(s) still need the client's answer", "See the 'Open questions' tab, or send the intake form"))
        if tally.get(fp.NO_PROFILE):
            items.append(item(MUST, label, "Your representative details are missing", "Run firm.py setup"))
        to_confirm = sum(tally.get(s, 0) for s in (fp.READY, fp.CONFIRM, fp.COPY, fp.FROM_FIRM))
        if to_confirm:
            items.append(item(TODO, label, f"{to_confirm} answer(s) found: confirm each against the original", f"Build the worksheet: form_prefill.py build --form {form}"))
        if tally.get(fp.YOU):
            items.append(item(TODO, label, f"{tally[fp.YOU]} choice(s) for you to make", "Decide and record them"))
        if tally.get(fp.SIGN):
            items.append(item(TODO, label, f"{tally[fp.SIGN]} signature(s) needed", "Collect at filing, on the current form version"))
        items.append(item(TODO, label, f"Download the current version from IRCC on filing day (index: {info['version']}, checked {info['last_verified']})", "Old versions are returned"))
    return items, counts, questions


def extraction_items(report_path, case_id):
    if not report_path:
        return [item(MUST, "Documents", "No document extraction has been run for this file", f"Run doc_extract.py extract --case {case_id}")], []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    out = []
    for f in report.get("flags", []):
        priority = MUST if f["severity"] == "HIGH" else TODO
        out.append(item(priority, "Documents", f["message"][:300], "Check it in the extraction review sheet, then fix or record why it's fine"))
    stamp = datetime.date.fromtimestamp(report_path.stat().st_mtime)
    note = []
    if (datetime.date.today() - stamp).days > 30:
        note.append(item(TODO, "Documents", f"The latest extraction is from {stamp}. Documents added since aren't checked", "Run the extraction again"))
    return out + note, report.get("documents", [])


def alert_items(folder, info, today):
    rows = cs.read_deadlines(folder)
    found = al.deadline_alerts(folder.name, rows, today) + al.file_alerts(folder.name, folder, info, rows, today) + al.document_alerts(folder.name, folder, today)
    found += [al.alert(r, folder.name, k, t, x, s, d, today) for r, k, t, x, s, d in bl.issues(folder, today) + up.issues(folder, today)]
    out = []
    for a in found:
        if a["kind"] == "File setup" and a["text"].startswith("Missing:"):
            out.append(item(MUST, "Intake", a["text"] + " (Code s.23-24; IMM 5476 for IRCC)", a["step"]))
        elif a["tier"] in ("overdue", "expired", "unreadable", "negative", "late") and a["rank"] == 1:
            out.append(item(MUST if a["kind"] in ("Deadline", "Expiry", "Unreadable file") else URGENT, a["kind"], a["text"] + (f" ({a['day']})" if a["day"] else ""), a["step"]))
        else:
            out.append(item(URGENT if a["rank"] == 1 else TODO, a["kind"], a["text"] + (f" ({a['day']})" if a["day"] else ""), a["step"]))
    return out


def next_path(folder, today):
    n = 1
    while True:
        p = folder / f"{today.isoformat()}-readiness-report{'' if n == 1 else f'-v{n}'}.xlsx"
        if not p.exists():
            return p
        n += 1


def cmd_report(a):
    today = datetime.date.today()
    folder = de.active_case(a.case)
    info = cs.read_case(folder)
    person = a.person or info.get("client", "")
    marital = fact(fp.facts_from_file(folder / "client-facts.csv", person), "marital_status")
    forms = a.form or default_forms(info.get("program", ""), marital)
    report_path = fp.latest_report(folder / "03-documents" / "_extraction")
    items = []
    if not forms:
        items.append(item(TODO, "Forms", f"No forms matched the program '{info.get('program', '')}'", "Run again with --form imm1234 for each form"))
    ws_items, counts, questions = worksheet_items(folder, person, forms, report_path)
    ex_items, docs = extraction_items(report_path, info.get("case_id", a.case))
    cl_info, cl_rows = checklist_rows(folder, info.get("program", ""), docs)
    import final_check as fc
    import followup as fu
    final_items, final_forms = fc.check(folder, person)
    for row, late in fu.open_items(folder, today):
        what = f"Follow-up {row['request']} #{row['no']} ({row['status']}): {row['text']}"
        items.append(item(URGENT if late else TODO, "Follow-up", (what + (f" - reply was due {row['due']}" if late else ""))[:300],
                          "Chase the client" if late else "Wait for the reply, then import it with followup.py import"))
    items += ex_items + ws_items + alert_items(folder, info, today) + checklist_items(cl_info, cl_rows, today) + letter_items(folder, docs) +         [item({"MUST": MUST, "URGENT": URGENT}.get(i["level"], TODO), "Final forms", f"{i['form']} | {i['check']}: {i['text']}"[:300],
              "Fix it on the form in Adobe, or confirm it is right") for i in final_items if i["level"] != "OK"]
    if re.search(r"super", info.get("program", ""), re.I):
        items += supervisa_items(folder, person, docs, today)
    items.sort(key=lambda x: ORDER[x["priority"]])
    tally = {p: sum(1 for x in items if x["priority"] == p) for p in ORDER}
    verdict = (f"NOT READY: {tally[MUST]} item(s) must be fixed before filing" if tally[MUST]
               else "No blocking items found. Your own final review is still needed before filing")
    out = pathlib.Path(a.out) if a.out else folder / "05-forms-submissions"
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    path = next_path(out, today)
    import openpyxl
    book = openpyxl.Workbook()
    book.remove(book.active)
    de.add_sheet(book, "Summary", ["Readiness report"], [
        [f"File: {folder.name}"], [f"Client: {person}"], [f"Program: {info.get('program', '')}"], [f"Date: {today.isoformat()}"], [""],
        [verdict], [f"{MUST}: {tally[MUST]} | {URGENT}: {tally[URGENT]} | {TODO}: {tally[TODO]}"], [""],
        ["Forms checked: " + (", ".join(c[0] for c in counts) or "none")],
        ["Documents in the latest extraction: " + (str(len(docs)) if report_path else "no extraction yet")],
        ["This report only joins existing checks. It can't see anything not recorded in the file, and it is not legal advice."]], [110])
    de.add_sheet(book, "Items", ["Priority", "Area", "What", "Next step"], [[x["priority"], x["source"], x["what"], x["step"]] for x in items] or [["", "", "Nothing found", ""]], [22, 16, 90, 50])
    de.add_sheet(book, "Forms", ["Form", "Questions", "Ready", "Confirm original", "Copy number", "From firm profile", "Client must answer", "Ask client",
                                 "Conflict", "Expired", "You decide", "Signatures", "Firm profile missing"], counts or [["No forms checked"] + [""] * 12], [14] + [11] * 12)
    if cl_info:
        head = [f"{cl_info['title']}: {cl_info['source']} ({cl_info['version']}), read {cl_info['read']}, confidence {cl_info['confidence']}", "", "", "", "", "", ""]
        sheet = [head] + [[r["no"], r["item"], "Always" if r["required"] == "always" else f"If: {r['condition']}", r["status"], r["files"], r["note"], ""] for r in cl_rows]
        sheet.append(["", "Found means a matching file is in 03-documents. Check each file is the right one, current, complete and translated.", "", "", "", "", ""])
    else:
        sheet = [["", f"No official checklist stored for the program '{info.get('program', '')}'", "", "", "", "", ""]]
    de.add_sheet(book, "Checklist", ["No.", "Item", "Required", "Status", "Files", "Note", "Your check"], sheet, [7, 70, 30, 18, 40, 40, 14])
    final_rows = [[fc.LABEL[i["level"]], i["form"], i["check"], i["text"]] for i in sorted(final_items, key=lambda x: fc.ORDER[x["level"]])]
    if not final_forms:
        final_rows = [["", "", "", "No finished IRCC forms in 05-forms-submissions yet"]]
    de.add_sheet(book, "Final forms", ["Result", "Form", "Check", "Detail"], final_rows, [12, 26, 12, 110])
    de.add_sheet(book, "Open questions", ["Form", "Section", "No.", "Question", "Status", "Note"], questions or [["", "", "", "No open questions", "", ""]], [12, 22, 7, 70, 22, 50])
    fd, tmp = tempfile.mkstemp(dir=str(out), suffix=".tmp.xlsx")
    os.close(fd)
    try:
        book.save(tmp)
        de.replace_with_retry(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    cs.add_log(folder, f"Readiness report: {tally[MUST]} must fix, {tally[URGENT]} urgent, {tally[TODO]} to do")
    print(verdict)
    print(f"{MUST}: {tally[MUST]} | {URGENT}: {tally[URGENT]} | To do: {tally[TODO]} | forms: {', '.join(forms) or 'none'}")
    print("Report:", path.name)
    print("Saved in:", path.parent)


def cmd_checklist(a):
    folder = de.active_case(a.case)
    info = cs.read_case(folder)
    program = a.program or info.get("program", "")
    report_path = fp.latest_report(folder / "03-documents" / "_extraction")
    docs = json.loads(report_path.read_text(encoding="utf-8")).get("documents", []) if report_path else []
    cl_info, rows = checklist_rows(folder, program, docs)
    if not cl_info:
        known = ", ".join(r["checklist"] for r in fp.load_csv(CHECKLISTS / "index.csv"))
        sys.exit(f"No official checklist stored for the program '{program}'. Stored: {known}. Use --program")
    print(f"{cl_info['title']}: {cl_info['source']} ({cl_info['version']}), read {cl_info['read']}, confidence {cl_info['confidence']}")
    if not report_path:
        print("No extraction yet: matching uses file names only. Run doc_extract.py extract --case " + folder.name.split("_")[0])
    for r in rows:
        print(f"  [{r['status']}] {r['no']}. {r['item']}" + (f"  <- {r['files']}" if r["files"] else "") + (f"  (if: {r['condition']})" if r["status"] == IF_APPLIES else ""))
    tally = {s: sum(1 for r in rows if r["status"] == s) for s in (FOUND, MISSING, IF_APPLIES, BY_HAND)}
    print(" | ".join(f"{k}: {v}" for k, v in tally.items()))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Case readiness report")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("report"); x.add_argument("case"); x.add_argument("--form", action="append"); x.add_argument("--person"); x.add_argument("--out"); x.set_defaults(fn=cmd_report)
    x = s.add_parser("checklist", help="compare a case's documents with IRCC's checklist"); x.add_argument("case"); x.add_argument("--program", help="override the case's program"); x.set_defaults(fn=cmd_checklist)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
