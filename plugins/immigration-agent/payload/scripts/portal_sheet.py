#!/usr/bin/env python3
"""Portal copy sheet: the client's answers for the forms IRCC takes online (PR portal, IRCC account, representative portal),
laid out to type in one by one, with a box to tick for each.

Usage:
  python3 scripts/portal_sheet.py CASE [--forms imm0008,imm5669,imm5406] [--person "Name" ...] [--all]

  --forms   the forms the portal asks for (default: the program's usual forms, as the readiness report uses)
  --person  each person to include (default: the client); repeat for a spouse or children who need their own forms
  --all     also list questions with no answer yet (by default they are listed once, at the end, as questions to settle first)

Guarantees:
  - Answers come from the same place as the form worksheets (/prefill): the latest document extraction and client-facts.csv.
    Each keeps its status ("Ready: please confirm", "Ask client", "Consultant decides"...). Nothing is typed into IRCC by the agent.
  - The sheet follows each form's own question order. The portals often split or regroup a form across screens, so match each
    portal question to the sheet by its wording, not by position.
  - Numbers shown as ****123 are hidden on purpose: copy them from the original document.
  - Saved as a Word file in the case's 05-forms-submissions.
"""
import argparse
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402

OPEN = {fp.ASK, fp.MUST, fp.YOU, fp.CONFLICT, fp.NO_PROFILE, fp.EXPIRED}


def die(msg):
    sys.exit("NOT PRODUCED: " + msg)


def gather(folder, forms, people):
    report_path = fp.latest_report(folder / "03-documents" / "_extraction")
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path else {"documents": []}
    out = []
    for person in people:
        docs, _ = fp.facts_from_report(report, person)
        client = fp.facts_from_file(folder / "client-facts.csv", person)
        for form in forms:
            info, spec = fp.load_spec(form)
            out.append((person, info, fp.build_rows(spec, docs, client)))
    return out, report_path


def cmd(a):
    import docx
    from docx.shared import Pt
    import readiness as rd
    folder = de.active_case(a.case)
    info = cs.read_case(folder)
    forms = [f.strip().lower() for f in a.forms.split(",")] if a.forms else [f for f in rd.default_forms(info.get("program", "")) if f != "imm5476"]
    if not forms:
        die("no usual forms for this program: give --forms")
    known = {r["form"] for r in fp.load_csv(fp.SPECS / "index.csv")}
    bad = [f for f in forms if f not in known]
    if bad:
        die(f"no worksheet for: {', '.join(bad)}. Available: {', '.join(sorted(known))}")
    people = a.person or [info.get("client", "")]
    sets, report_path = gather(folder, forms, people)
    from docx.shared import Inches
    import docstyle as ds
    d = docx.Document()
    sec = ds.setup(d, body_size=10)
    ds.footer(sec, f"Portal copy sheet - {info.get('client', '')} ({info.get('case_id', '')}) - internal working copy")
    ds.title(d, f"Portal copy sheet: {info.get('client', '')} ({info.get('case_id', '')})",
             f"Made {datetime.date.today()}. Answers from {'the extraction ' + report_path.name if report_path else 'client facts only (no extraction yet)'} and client-facts.csv.")
    d.add_paragraph("Type each answer into the portal and tick the box. The portal may split or reorder a form's questions across screens: "
                    "match by the wording of the question. Numbers shown as ****123 must be copied from the original document. "
                    "Anything marked 'Ask client' or 'Consultant decides' must be settled before you start.")
    widths = (Inches(0.5), Inches(2.6), Inches(2.0), Inches(1.4))
    tables = []
    open_items, counts = [], {"answered": 0, "open": 0}
    for person, form_info, rows in sets:
        ds.heading(d, f"{form_info['title']} - {person}", 1)
        section = None
        table = None
        for r in rows:
            unanswered = not r["answer"] or r["status"] in OPEN
            if unanswered:
                counts["open"] += 1
                open_items.append((person, form_info["form"].upper(), r))
                if not a.all:
                    continue
            else:
                counts["answered"] += 1
            if r["section"] != section:
                section = r["section"]
                ds.heading(d, section or "Questions", 2)
                table = d.add_table(rows=1, cols=4)
                tables.append(table)
                for c, h in zip(table.rows[0].cells, ("Done", "Question", "Answer", "Check")):
                    c.text = h
            cells = table.add_row().cells
            cells[0].text = "☐"
            cells[1].text = f"{r['no']} {r['question']}".strip()
            cells[2].text = r["answer"] or "—"
            cells[3].text = r["status"] + (f". {r['note']}" if r["note"] else "")
    for t in tables:  # styled once filled, so banding and widths cover every row
        ds.style_table(t, widths, size=9)
        for row in t.rows[1:]:
            row.cells[0].paragraphs[0].alignment = 1
    if open_items:
        ds.heading(d, "Settle these before you start", 1)
        for person, form, r in open_items:
            d.add_paragraph(f"{form} ({person}): {r['question']} [{r['status']}]", style="List Bullet")
    out = folder / "05-forms-submissions"
    de.guard_output(out)
    out.mkdir(exist_ok=True)
    path = out / f"{datetime.date.today().isoformat()}-portal-copy-sheet.docx"
    n = 1
    while path.exists():
        n += 1
        path = out / f"{datetime.date.today().isoformat()}-portal-copy-sheet-v{n}.docx"
    d.save(path)
    cs.add_log(folder, f"Portal copy sheet made: {path.name}")
    print(f"Forms: {', '.join(f.upper() for f in forms)} | people: {', '.join(people)}")
    print(f"Answers ready to type: {counts['answered']} | to settle first: {counts['open']}")
    print(f"Saved: {path}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Portal copy sheet")
    p.add_argument("case"); p.add_argument("--forms"); p.add_argument("--person", action="append"); p.add_argument("--all", action="store_true")
    cmd(p.parse_args())


if __name__ == "__main__":
    main()
