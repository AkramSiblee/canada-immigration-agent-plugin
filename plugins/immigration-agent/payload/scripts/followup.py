#!/usr/bin/env python3
"""Client follow-up request: the open questions and missing documents of a case, sent to the client as one fillable PDF.

  make CASE [--person NAME] [--forms imm5257,imm5645] [--ask "question" ...] [--doc "document" ...] [--due YYYY-MM-DD]
  import FILE --case CASE [--person NAME]
  list CASE

make collects: questions the client must still answer or must clarify (conflicts) on the case's form worksheets,
Yes answers without their details, required documents missing from the official checklist, and blanks the final
form check found (identity numbers become document requests: they are never typed). Items already asked in an
open request are not asked again. The PDF goes to 06-correspondence; every item is recorded in followups.csv.

import adds the written answers to client-facts.csv (never overwriting; a different answer is kept beside the
old one) and marks documents the client says are coming. The readiness report lists open items; past the
reply-by date they are urgent.
"""
import argparse
import csv
import datetime
import os
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402

VERSION = "1"
TODAY = datetime.date.today()
REPLY_DAYS = 14
LOG_FIELDS = ["request", "no", "kind", "key", "text", "status", "due", "updated"]
OPEN, ANSWERED, COMING, CLOSED = "open", "answered", "document coming", "closed"
PICK = "Select"
IDENTITY = re.compile(r"passport|national identity|national id|green card|uci|social insurance|\bsin\b", re.I)


# ---- what to ask ----
PLAIN_DOCUMENTS = [  # (pattern in the question or check, what to ask the client for)
    (r"passport", "A clear colour copy of your current passport's photo page"),
    (r"national identity|national id", "A clear colour copy of your national identity card, front and back"),
    (r"green card|lawful permanent resident", "A clear colour copy of your United States green card, front and back"),
    (r"\buci\b|client identifier", "A copy of any earlier Canadian visa, permit or IRCC letter (it shows your client number, UCI)"),
]
PLAIN_ANSWERS = [  # (pattern, clearer question, how to answer)
    (r"employment for the past 10 years", "What have you been doing over the last 10 years? List each period with no gaps",
     "For each period: from (YYYY-MM), to (or now), what you did (job title, homemaker, retired, studying, unemployed), employer if any, city and country."),
]


def plain_document(text):
    return next((ask for rx, ask in PLAIN_DOCUMENTS if re.search(rx, text, re.I)), f"A clear copy of the document showing: {text}")


def plain_answer(text):
    for rx, question, how in PLAIN_ANSWERS:
        if re.search(rx, text, re.I):
            return question, how
    return text, ""
def form_items(folder, person, forms):
    """Questions the worksheets still need from the client, for the given forms."""
    import final_check as fc
    import json
    report = fp.latest_report(folder / "03-documents" / "_extraction")
    pool = fp.facts_from_report(json.loads(report.read_text(encoding="utf-8")), person)[0] if report else {}
    client = fp.facts_from_file(folder / "client-facts.csv", person)
    answers = {k: v[0]["value"] for k, v in client.items() if v}
    items, seen = [], set()
    for form in forms:
        try:
            _, spec = fp.load_spec(form)
        except SystemExit:
            continue
        for q, r in zip(spec, fp.build_rows(spec, pool, client)):
            key = q["key"]
            if key in seen or q["rule"] in ("sign", "consultant", "firm") or key in fc.ALWAYS_OPTIONAL:
                continue
            if r["status"] not in (fp.MUST, fp.ASK, fp.CONFLICT):
                continue
            if key in fc.CONDITIONS:
                other, values = fc.CONDITIONS[key]
                if answers.get(other) not in values and (pool.get(other) or [{}])[0].get("value") not in values:
                    continue
            elif fc.OPTIONAL.search(q["question"] + " " + q["help"]) and r["status"] != fp.CONFLICT:
                continue
            seen.add(key)
            if key in de.SENSITIVE or IDENTITY.search(q["question"]) and r["status"] != fp.CONFLICT:
                items.append({"kind": "document", "key": key, "text": plain_document(q["question"]),
                              "why": f"Needed for your application form ({form.upper().replace('IMM', 'IMM ')}). We copy numbers from your documents, so please send a copy rather than typing the number."})
                continue
            why = f"Needed for your application form ({form.upper().replace('IMM', 'IMM ').replace('CIT', 'CIT ')})."
            if r["status"] == fp.CONFLICT:
                why = f"Your documents or earlier answers disagree. {r['note'][:200]} Please tell us which is correct."
            elif q["help"]:
                why += f" {q['help']}"
            question, how = plain_answer(q["question"])
            items.append({"kind": "answer", "key": key, "text": question, "why": f"{why} {how}".strip()})
    return items


def document_items(folder, program, docs):
    """Required documents the official checklist doesn't find in 03-documents."""
    import readiness as rd
    info, rows = rd.checklist_rows(folder, program, docs)
    return [{"kind": "document", "key": f"doc:{r['no']}", "text": r["item"], "why": f"Required by IRCC's checklist {info['source']}." + (f" {r['note']}" if r["note"] else "")}
            for r in rows if r["status"] == rd.MISSING] if info else []


def final_items(folder, person):
    """Blanks in the finished forms that the client can supply."""
    import final_check as fc
    items, _ = fc.check(folder, person)
    out = []
    for i in items:
        if i["level"] != "MUST" or i["check"] not in ("Blank", "Family"):
            continue
        if IDENTITY.search(i["text"]):
            out.append({"kind": "document", "key": f"final:{i['text'][:40]}", "text": plain_document(i["text"]),
                        "why": f"Needed for your application form ({i['form']}). We copy numbers from your documents, so please send a copy rather than typing the number."})
        else:
            question, how = plain_answer(i["text"])
            out.append({"kind": "answer", "key": f"final:{i['text'][:40]}", "text": question, "why": f"Needed for your application form ({i['form']}). {how}".strip()})
    return out


def collect(folder, person, forms, extra_questions=(), extra_docs=()):
    import json
    import readiness as rd
    info = cs.read_case(folder)
    report = fp.latest_report(folder / "03-documents" / "_extraction")
    docs = json.loads(report.read_text(encoding="utf-8")).get("documents", []) if report else []
    forms = forms or [f for f in rd.default_forms(info.get("program", "")) if f != "imm5476"]
    items = form_items(folder, person, forms) + final_items(folder, person) + document_items(folder, info.get("program", ""), docs)
    items += [{"kind": "answer", "key": f"ask:{t[:40]}", "text": t, "why": "Your consultant needs this to complete your application."} for t in extra_questions]
    items += [{"kind": "document", "key": f"doc+:{t[:40]}", "text": t, "why": "Your consultant needs this to complete your application."} for t in extra_docs]
    have = {d.get("doc_type") for d in docs}
    if "passport" in have:  # a number missing on the form is typed from the copy already on file, not asked again
        items = [i for i in items if not (i["kind"] == "document" and i["text"] == plain_document("passport"))]
    asked = {r["key"] for r in read_log(folder) if r["status"] in (OPEN, COMING)}
    out, seen = [], set()
    for it in items:
        key = it["key"]
        if key in seen or key in asked:
            continue
        if it["kind"] == "document" and any(re.sub(r"\W", "", it["text"].lower())[:30] == re.sub(r"\W", "", o["text"].lower())[:30] for o in out):
            continue
        seen.add(key)
        out.append(it)
    return sorted(out, key=lambda x: x["kind"] != "answer")


# ---- the log ----
def log_path(folder):
    return folder / "followups.csv"


def read_log(folder):
    p = log_path(folder)
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_log(folder, rows):
    p = log_path(folder)
    fd, tmp = tempfile.mkstemp(dir=str(folder), suffix=".tmp.csv")
    os.close(fd)
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, LOG_FIELDS)
        w.writeheader()
        w.writerows(rows)
    de.replace_with_retry(tmp, p)


# ---- the PDF ----
def make_pdf(path, person, case_id, items, due, firm=""):
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas
    width, height = letter
    left, right, top, bottom = 48, width - 48, height - 54, 54
    usable = right - left
    navy, grey, light = HexColor("#1F3864"), HexColor("#555555"), HexColor("#EEF2F8")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp.pdf")
    os.close(fd)
    c = canvas.Canvas(tmp, pagesize=letter)
    c.setTitle("Follow-up request")
    st = {"y": top, "page": 1}

    def footer():
        c.setFont("Helvetica", 7.5)
        c.setFillColor(grey)
        c.drawString(left, 30, f"Follow-up request, file {case_id}. Protected when completed: return it by a secure method.")
        c.drawRightString(right, 30, f"Page {st['page']}")
        c.setFillColor(black)

    def room(need):
        if st["y"] - need < bottom:
            footer()
            c.showPage()
            st["page"] += 1
            st["y"] = top

    def text(t, font="Helvetica", size=9.5, color=black, gap=2, indent=0):
        lines = simpleSplit(t, font, size, usable - indent)
        room(len(lines) * (size + 2.5) + gap)
        c.setFont(font, size)
        c.setFillColor(color)
        for line in lines:
            c.drawString(left + indent, st["y"] - size, line)
            st["y"] -= size + 2.5
        st["y"] -= gap
        c.setFillColor(black)

    def bar(title):
        room(60)
        c.setFillColor(navy)
        c.rect(left, st["y"] - 20, usable, 20, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(left + 6, st["y"] - 14, title)
        c.setFillColor(black)
        st["y"] -= 28

    def field(name, kind, h, tip, w=None):
        common = dict(x=left, y=st["y"] - h, width=w or usable, height=h, borderColor=navy, fillColor=white, textColor=black, forceBorder=True, fontName="Helvetica", fontSize=9)
        if kind == "yesno":
            c.acroForm.choice(name=name, tooltip=tip[:200], value=PICK, options=[PICK, "Yes", "No"], **common)
        else:
            c.acroForm.textfield(name=name, tooltip=tip[:200], value="", maxlen=4000, fieldFlags="multiline" if h > 20 else "", **common)
        st["y"] -= h + 10

    c.setFillColor(navy)
    c.rect(0, height - 120, width, 120, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(left, height - 64, "Follow-up request")
    c.setFont("Helvetica", 10.5)
    c.drawString(left, height - 88, f"For: {person}     File: {case_id}     Date: {TODAY.isoformat()}" + (f"     From: {firm}" if firm else ""))
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(left, height - 106, f"Please reply by {due}")
    c.setFillColor(black)
    st["y"] = height - 145
    answers = [i for i in items if i["kind"] == "answer"]
    docs = [i for i in items if i["kind"] == "document"]
    text("To finish preparing your application, we need the following. Each item says why we need it. Answer in the boxes, "
         "or send the documents listed. If something doesn't apply, write N/A; if you can't get a document, tell us why.", size=10, gap=6)
    text("Open this file in Adobe Acrobat Reader (free), type your answers, save it, and send it back to us by the secure method we gave you, "
         "with the documents. Please do not type passport, national ID or other identity numbers: send a copy of the document instead.",
         "Helvetica-Oblique", 9, grey, gap=10)
    n = 0
    if answers:
        bar(f"Part A. Questions to answer in writing ({len(answers)})")
        for it in answers:
            n += 1
            room(110)
            text(f"{n}.  {it['text']}", "Helvetica-Bold", 9.5, gap=1)
            text(f"Why: {it['why']}", "Helvetica-Oblique", 8, grey, gap=3)
            field(f"a__{n}", "text", 46, it["text"])
    if docs:
        bar(f"Part B. Documents to send ({len(docs)})")
        for it in docs:
            n += 1
            lines = simpleSplit(f"{n}.  {it['text']}", "Helvetica-Bold", 9.5, usable - 22)
            room(len(lines) * 12 + 70)
            c.acroForm.checkbox(name=f"d__{n}", tooltip=it["text"][:200], x=left, y=st["y"] - 11, size=10, buttonStyle="check", borderColor=navy, fillColor=white, textColor=navy, forceBorder=True)
            c.setFont("Helvetica-Bold", 9.5)
            for k, line in enumerate(lines):
                c.drawString(left + 18, st["y"] - 9 - k * 12, line)
            st["y"] -= len(lines) * 12 + 3
            text(f"Tick the box if you are sending it. Why: {it['why']}", "Helvetica-Oblique", 8, grey, gap=3, indent=18)
            text("If you can't send it, tell us why:", "Helvetica", 8.5, gap=1, indent=18)
            field(f"n__{n}", "text", 18, f"{it['text']}: note")
    bar("Part C. Declaration")
    text("I declare that my answers are truthful, complete and correct.", "Helvetica-Bold", 9.5, gap=2)
    field("agree_declaration", "yesno", 18, "Declaration", 170)
    text("Your full name and today's date", "Helvetica-Bold", 9.5, gap=2)
    field("signed_name", "text", 18, "Name and date")
    for i, (name, value) in enumerate((("form_kind", "followup"), ("form_version", VERSION), ("form_case", case_id), ("form_person", person),
                                       ("form_request", TODAY.isoformat()))):
        c.acroForm.textfield(name=name, value=value, x=left + i * 2, y=2, width=1, height=1, maxlen=200, fieldFlags="readOnly", annotationFlags="hidden", borderWidth=0, forceBorder=False)
    footer()
    c.save()
    de.replace_with_retry(tmp, path)


def next_path(folder, stem):
    n = 1
    while True:
        p = folder / f"{TODAY.isoformat()}-{stem}{'' if n == 1 else f'-v{n}'}.pdf"
        if not p.exists():
            return p
        n += 1


def cmd_make(a):
    folder = de.active_case(a.case)
    info = cs.read_case(folder)
    person = a.person or info.get("client", "")
    forms = [f.strip().lower() for f in a.forms.split(",")] if a.forms else None
    items = collect(folder, person, forms, a.ask or [], a.doc or [])
    if not items:
        print("Nothing to ask: no open questions or missing documents found. Add your own with --ask or --doc.")
        return
    due = a.due or (TODAY + datetime.timedelta(days=REPLY_DAYS)).isoformat()
    out = folder / "06-correspondence"
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    path = next_path(out, "follow-up-request" + (f"-{re.sub(r'[^a-z0-9]+', '-', person.lower()).strip('-')}" if person else ""))
    try:
        import intake_form
        firm = intake_form.firm_name()
    except Exception:
        firm = ""
    make_pdf(path, person, info.get("case_id", a.case), items, due, firm)
    rows = read_log(folder)
    for n, it in enumerate(items, 1):
        rows.append({"request": TODAY.isoformat(), "no": str(n), "kind": it["kind"], "key": it["key"], "text": it["text"][:300], "status": OPEN, "due": due, "updated": TODAY.isoformat()})
    write_log(folder, rows)
    with (folder / "log.md").open("a", encoding="utf-8") as f:
        f.write(f"| {TODAY.isoformat()} | Follow-up request prepared (to send to the client): {sum(i['kind'] == 'answer' for i in items)} question(s), {sum(i['kind'] == 'document' for i in items)} document(s); reply by {due} |\n")
    print(f"Questions: {sum(i['kind'] == 'answer' for i in items)} | documents: {sum(i['kind'] == 'document' for i in items)} | reply by {due}")
    for n, it in enumerate(items, 1):
        print(f"  {n}. [{it['kind']}] {it['text'][:110]}")
    print("Request:", path)


# ---- reading the reply ----
def read_fields(path):
    import pypdf
    try:
        r = pypdf.PdfReader(str(path), strict=False)
        if r.is_encrypted and not r.decrypt(""):
            sys.exit("ERROR: this file is password protected")
        fields = r.get_fields() or {}
    except Exception as e:
        sys.exit(f"ERROR: can't read this PDF ({type(e).__name__})")
    out = {}
    for name, info in fields.items():
        v = info.get("/V")
        if v is None:
            continue
        t = str(v).lstrip("/").strip()
        t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", t)
        if t and t != PICK:
            out[name.split(".")[-1]] = t[:4000]
    return out


def cmd_import(a):
    src = pathlib.Path(a.file)
    if not src.exists():
        sys.exit(f"ERROR: not found: {src}")
    if any(p.lower() == "client-ids" for p in src.resolve().parts):
        sys.exit("ERROR: client-ids folders are not read")
    folder = de.active_case(a.case)
    info = cs.read_case(folder)
    person = a.person or info.get("client", "")
    got = read_fields(src)
    if got.get("form_kind") != "followup" or got.get("form_version") != VERSION:
        sys.exit("ERROR: this isn't a follow-up request")
    if got.get("form_case") != info.get("case_id"):
        sys.exit("ERROR: this request belongs to another file")
    if got.get("form_person") and not de.same_person(got["form_person"], person):
        sys.exit("ERROR: this request was sent to a different person")
    if got.get("agree_declaration") != "Yes":
        sys.exit("NOT IMPORTED: the client hasn't given the declaration")
    request = got.get("form_request", "")
    rows = read_log(folder)
    mine = {r["no"]: r for r in rows if r["request"] == request}
    if not mine:
        sys.exit("ERROR: no record of this request in followups.csv")
    facts_path = folder / "client-facts.csv"
    existing = [r for r in (list(csv.DictReader(facts_path.open(encoding="utf-8", newline=""))) if facts_path.exists() else []) if de.same_person(person, r.get("person", ""))]
    new, answered, coming, conflicts, notes = [], 0, 0, 0, []
    for no, r in mine.items():
        if r["kind"] == "answer" and got.get(f"a__{no}"):
            value = got[f"a__{no}"]
            key = r["key"] if not re.match(r"(ask|final):", r["key"]) else f"followup:{request}:{no}"
            old = [x for x in existing if x["key"] == key]
            if not any(fp.norm(x["value"]) == fp.norm(value) for x in old):
                conflicts += bool(old)
                new.append({"person": person, "key": key, "value": value, "source": f"Client follow-up {request} (reply imported {TODAY.isoformat()})"})
            r["status"], r["updated"] = ANSWERED, TODAY.isoformat()
            answered += 1
        elif r["kind"] == "document":
            if str(got.get(f"d__{no}", "")).lower() in ("yes", "on", "1", "true"):
                r["status"], r["updated"] = COMING, TODAY.isoformat()
                coming += 1
            if got.get(f"n__{no}"):
                notes.append(f"{no}. {r['text'][:60]}: {got[f'n__{no}'][:200]}")
    fresh = not facts_path.exists()
    with facts_path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["person", "key", "value", "source"])
        if fresh:
            w.writeheader()
        w.writerows(new)
    write_log(folder, rows)
    still = [r for r in mine.values() if r["status"] == OPEN]
    with (folder / "log.md").open("a", encoding="utf-8") as f:
        f.write(f"| {TODAY.isoformat()} | Follow-up reply ({request}) imported: {answered} answer(s), {coming} document(s) coming, {len(still)} still open |\n")
    print(f"Answered: {answered} | documents coming: {coming} | still open: {len(still)} | conflicts with earlier answers: {conflicts}")
    if conflicts:
        print("  A different answer was given before: both are kept. The worksheet shows the conflict to resolve")
    for n_ in notes:
        print(f"  Client note: {n_}")
    if coming:
        print("  Save the documents in 03-documents when they arrive, run the extraction, then mark them received: followup.py close CASE --item N")


def cmd_list(a):
    folder = de.active_case(a.case)
    rows = read_log(folder)
    if not rows:
        print("No follow-up requests yet")
        return
    for r in rows:
        late = r["status"] in (OPEN, COMING) and r["due"] and r["due"] < TODAY.isoformat()
        print(f"  {r['request']} #{r['no']} [{r['status']}{', OVERDUE' if late else ''}] {r['kind']}: {r['text'][:100]}")


def cmd_close(a):
    folder = de.active_case(a.case)
    rows = read_log(folder)
    targets = [r for r in rows if r["no"] == str(a.item) and (not a.request or r["request"] == a.request) and r["status"] != CLOSED]
    if not targets:
        sys.exit("ERROR: no open item with that number")
    for r in targets[-1:]:
        r["status"], r["updated"] = CLOSED, TODAY.isoformat()
        print(f"Closed: {r['request']} #{r['no']} {r['text'][:80]}")
    write_log(folder, rows)


def open_items(folder, today=None):
    """[(row, overdue)] for the readiness report."""
    today = (today or TODAY).isoformat()
    return [(r, bool(r["due"]) and r["due"] < today) for r in read_log(folder) if r["status"] in (OPEN, COMING)]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Client follow-up requests")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("make"); x.add_argument("case"); x.add_argument("--person"); x.add_argument("--forms", help="comma-separated, e.g. imm5257,imm5645,imm5707")
    x.add_argument("--ask", action="append", help="your own question"); x.add_argument("--doc", action="append", help="your own document request")
    x.add_argument("--due", help="reply-by date, YYYY-MM-DD (default 14 days)"); x.set_defaults(fn=cmd_make)
    x = s.add_parser("import"); x.add_argument("file"); x.add_argument("--case", required=True); x.add_argument("--person"); x.set_defaults(fn=cmd_import)
    x = s.add_parser("list"); x.add_argument("case"); x.set_defaults(fn=cmd_list)
    x = s.add_parser("close"); x.add_argument("case"); x.add_argument("--item", type=int, required=True); x.add_argument("--request"); x.set_defaults(fn=cmd_close)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
