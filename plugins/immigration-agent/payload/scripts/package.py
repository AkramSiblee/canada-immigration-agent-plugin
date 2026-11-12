#!/usr/bin/env python3
"""Sorting run: arrange a case's documents into IRCC's checklist order, one upload-ready PDF per item.

  build CASE [--program P] [--max-mb 4]

Reads 03-documents (never client-ids folders) and the latest extraction, matches each file to the program's
official checklist (templates/checklists/), and writes a new dated folder in 05-forms-submissions:

  01-<item>.pdf ...   each item's files combined in one PDF (a letter of explanation first), under the size limit
                      (compressed, then split into -part1, -part2 if needed)
  IRCC forms          copied unchanged: they must be uploaded as they are
  99-unsorted/        files that matched no item, copied unchanged
  package-index.xlsx  what went where, what is missing, what to tick by hand

The originals are never changed. A file goes to the first item it matches. Every result is a draft:
check each PDF before uploading.
"""
import argparse
import datetime
import io
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402
import pdf_studio as ps  # noqa: E402
import readiness as rd  # noqa: E402

EXPLANATION = r"explanation|\bloe\b|letter"
UPLOAD_EXT = {".pdf"} | ps.IMAGE_EXT | ps.OFFICE_EXT


def slug(text, words=6):
    t = re.sub(r"\(.*?\)", "", text)
    t = re.sub(r"[^A-Za-z0-9 ]+", " ", t).lower().split()
    return "-".join(t[:words]) or "item"


def readable_pdf(path, tmp):
    """(reader, is IRCC form) for any supported file, or (None, reason)."""
    try:
        r = ps.as_pdf_reader(path, tmp)
    except SystemExit as e:  # pdf_studio reports problems by exiting
        return None, str(e).replace("ERROR: ", "")
    return r, ps.is_form(r)


def write_item(files, slot, pkg, limit, tmp):
    """Combine one item's files. Returns [(package file, MB, note)]."""
    written, parts = [], []
    for f in sorted(files, key=lambda p: (not re.search(EXPLANATION, p.name, re.I), p.name.lower())):
        r, info = readable_pdf(f, tmp)
        if r is None:
            dest = ps.free_name(pkg / f"{slot}-{f.name}")
            shutil.copy2(f, dest)
            written.append((dest, ps.mb(dest.stat().st_size), f"copied unchanged: {info}"))
        elif info is True:  # an IRCC form keeps its form data only as the original file
            dest = ps.free_name(pkg / f"{slot}-{f.name}")
            shutil.copy2(f, dest)
            written.append((dest, ps.mb(dest.stat().st_size), "IRCC form: copied unchanged, upload as is"))
        else:
            parts.append((f, r))
    if not parts:
        return written
    w = ps.writer()
    for f, r in parts:
        start = len(w.pages)
        for page in r.pages:
            w.add_page(page)
        if len(parts) > 1:
            w.add_outline_item(f.stem, start)
    buf = io.BytesIO()
    w.write(buf)
    data, note = buf.getvalue(), f"{len(parts)} file(s) combined" if len(parts) > 1 else "one file"
    if ps.mb(len(data)) > limit:
        import pypdf
        r = pypdf.PdfReader(io.BytesIO(data))
        for quality, side in ((75, 2000), (60, 1600), (45, 1300), (35, 1000)):
            smaller, done = ps.shrink(r, quality, side)
            if len(smaller) < len(data):
                data, note = smaller, f"{note}; compressed (images at quality {quality})"
            if ps.mb(len(data)) <= limit or not done:
                break
    if ps.mb(len(data)) <= limit:
        dest = ps.free_name(pkg / f"{slot}.pdf")
        dest.write_bytes(data)
        return written + [(dest, ps.mb(len(data)), note)]
    import pypdf
    r = pypdf.PdfReader(io.BytesIO(data))
    for n, pages in enumerate(ps.size_groups(r, limit), 1):
        pw = ps.writer()
        for i in pages:
            pw.add_page(r.pages[i])
        dest = ps.save(pw, ps.free_name(pkg / f"{slot}-part{n}.pdf"))
        size = ps.mb(dest.stat().st_size)
        over = "; one page alone is over the limit: rescan it smaller" if size > limit else ""
        written.append((dest, size, f"{note}; split, pages {pages[0] + 1}-{pages[-1] + 1}{over}"))
    return written


def build(case, program=None, limit=ps.IRCC_LIMIT_MB):
    folder = de.active_case(case)
    info = cs.read_case(folder)
    program = program or info.get("program", "")
    report = fp.latest_report(folder / "03-documents" / "_extraction")
    docs = json.loads(report.read_text(encoding="utf-8")).get("documents", []) if report else []
    cl_info, items = rd.checklist_for(program)
    if not cl_info:
        sys.exit(f"ERROR: no official checklist stored for the program '{program}'. Use --program (e.g. super-visa, pgp, spousal, citizenship)")
    root = folder / "03-documents"
    files = rd.case_files(folder)
    pkg = ps.free_name(folder / "05-forms-submissions" / f"{datetime.date.today().isoformat()}-package")
    ps.check_output(pkg)
    pkg.mkdir(parents=True)
    used, index = set(), []
    with tempfile.TemporaryDirectory() as tmp:
        for n, it in enumerate(items, 1):
            hits = rd.matches(it["detect"], docs, files) if it["detect"] else []
            mine = [h for h in hits if h not in used and (root / h).is_file() and (root / h).suffix.lower() in UPLOAD_EXT]
            others = [h for h in hits if h in used]
            used.update(mine)
            slot = f"{n:02d}-{slug(it['item'])}"
            need = "Always" if it["required"] == "always" else f"If: {it['condition']}"
            if not mine:
                status = (f"In an earlier item: {', '.join(others)}" if others else rd.BY_HAND if not it["detect"]
                          else rd.MISSING if it["required"] == "always" else rd.IF_APPLIES)
                index.append([slot, it["item"], need, status, "", "", "", it["note"]])
                continue
            for dest, size, note in write_item([root / h for h in mine], slot, pkg, limit, tmp):
                index.append([slot, it["item"], need, rd.FOUND, ", ".join(mine), dest.name, round(size, 2), note + (f"; {it['note']}" if it["note"] else "")])
        rest = [f for f in files if f not in used]
        if rest:
            (pkg / "99-unsorted").mkdir()
            for f in rest:
                dest = ps.free_name(pkg / "99-unsorted" / pathlib.Path(f).name)
                shutil.copy2(root / f, dest)
                index.append(["99-unsorted", "Matched no checklist item", "", "Unsorted", f, f"99-unsorted/{dest.name}", round(ps.mb(dest.stat().st_size), 2),
                              "Check whether it belongs to an item, or leave it out"])
    write_index(pkg, cl_info, info, index, bool(report))
    return pkg, index


def write_index(pkg, cl_info, info, index, extracted):
    import openpyxl
    book = openpyxl.Workbook()
    book.remove(book.active)
    found = sum(1 for r in index if r[3] == rd.FOUND)
    missing = sum(1 for r in index if r[3] == rd.MISSING)
    de.add_sheet(book, "Read me first", ["Document package"], [
        [f"File: {info.get('case_id', '')} {info.get('client', '')}"], [f"Checklist: {cl_info['title']}, {cl_info['source']} ({cl_info['version']}), read {cl_info['read']}"],
        [f"Made: {datetime.date.today().isoformat()}"], [""],
        [f"Package files: {found} | Required items missing: {missing}"],
        ["" if extracted else "No extraction was found: files were matched by file name only. Run doc_extract.py extract --case first for better matching."],
        ["Each PDF is a draft. Open every one before uploading: right document, right person, readable, complete, translated, in date."],
        ["IRCC forms are copied unchanged and must be uploaded as they are. The originals in 03-documents were not changed."]], [110])
    de.add_sheet(book, "Package", ["Slot", "Checklist item", "Required", "Status", "From (03-documents)", "Package file", "MB", "Note"], index,
                 [16, 60, 26, 18, 40, 34, 7, 50])
    fd, tmp = tempfile.mkstemp(dir=str(pkg), suffix=".tmp.xlsx")
    os.close(fd)
    try:
        book.save(tmp)
        os.replace(tmp, pkg / "package-index.xlsx")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def cmd_build(a):
    pkg, index = build(a.case, a.program, a.max_mb)
    print(f"Package: {pkg}")
    for row in index:
        if row[3] == rd.FOUND:
            print(f"  {row[5]}  ({row[6]} MB)  <- {row[4]}")
    for label, status in (("Missing (required)", rd.MISSING), ("Unsorted", "Unsorted")):
        rows = [r for r in index if r[3] == status]
        if rows:
            print(f"{label}: " + "; ".join((r[1] if status == rd.MISSING else r[4])[:70] for r in rows))
    print("Open every PDF before uploading. Details: package-index.xlsx")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Sort a case's documents into IRCC checklist order")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("build"); x.add_argument("case"); x.add_argument("--program"); x.add_argument("--max-mb", type=float, default=ps.IRCC_LIMIT_MB)
    x.set_defaults(fn=cmd_build)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
