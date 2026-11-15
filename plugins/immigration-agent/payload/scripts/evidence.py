#!/usr/bin/env python3
"""Relationship evidence organiser for spousal and partner files: a dated timeline of every item, then upload-ready PDFs.

Usage:
  python3 scripts/evidence.py timeline CASE [--folder PATH]      dates and sorts every item; saves an Excel timeline to fill in
  python3 scripts/evidence.py build CASE [--photos 20] [--contact-pages 10]   PDFs from the timeline (photos with captions, contact, other)

Put the evidence in the case's 03-documents/relationship/ (any subfolders), or give --folder.

How items are dated, most reliable first: the photo's own camera date (EXIF), a date in the file name (2023-05-14, 20230514,
IMG_20230514), the first date printed in a PDF or text file, and last the file's modified date (marked "confirm").
Categories come from the file name and type: photos, communication (chats, calls, emails), travel and visits, living together and
finances, events and family, other. Change any category, date or caption in the Excel timeline; 'build' uses your changes.

Rules (knowledge/04-family/spousal-common-law-conjugal.md, IMM 5533 as retrieved there): photos at most 20; proof of contact at most
10 pages. The build keeps to these limits; check the current IMM 5533 checklist before filing, as limits can change.

Guarantees:
  - Originals are only read. PDFs go to 05-forms-submissions/relationship-evidence/.
  - Photos for the PDF are the ones you mark Include = yes; if none are marked, up to the limit are picked spread across the timeline.
  - Every caption is yours or the date only. The agent never writes a description of the relationship (the client's IMM 5532 is
    their own account).
"""
import argparse
import datetime
import io
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

IMAGES = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".tif", ".tiff"}
DOCS = {".pdf", ".docx", ".txt"}
CATEGORIES = [
    ("Communication", r"chat|whats ?app|message|messenger|wechat|viber|telegram|signal|imo|sms|\btexts?\b|\bcalls?\b|call ?log|email|e-mail|screenshot|screen ?shot"),
    ("Travel and visits", r"ticket|boarding|itinerary|flight|airline|hotel|booking|passport|stamp|visit|trip|travel|entry|exit"),
    ("Living together and finances", r"lease|rent|tenancy|mortgage|deed|bank|joint|account|bill|hydro|utility|insurance|beneficiary|address|licence|license|tax|cra|noa"),
    ("Events and family", r"wedding|marriage|nikah|ceremony|engagement|reception|invitation|birth|baby|family|anniversary|card|gift"),
]
PHOTOS = "Photos"
FIELDS = ["No.", "Date", "How dated", "Category", "File", "Include? (yes/no)", "Caption (yours)"]
LIMIT_PHOTOS, LIMIT_CONTACT = 20, 10
DATE_IN_NAME = [r"(20\d{2}|19\d{2})[-_. ]?(0[1-9]|1[0-2])[-_. ]?(0[1-9]|[12]\d|3[01])"]


def die(msg):
    sys.exit("NOT PRODUCED: " + msg)


def exif_date(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            ex = im.getexif()
            raw = ex.get(36867) or ex.get_ifd(0x8769).get(36867) or ex.get(306)
        if raw:
            return datetime.datetime.strptime(str(raw)[:19], "%Y:%m:%d %H:%M:%S").date()
    except Exception:
        return None
    return None


def name_date(name):
    for rx in DATE_IN_NAME:
        m = re.search(rx, name)
        if m:
            try:
                return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def text_date(path):
    try:
        if path.suffix.lower() == ".pdf":
            pages = de.read_pdf(path, 3)[0]
        elif path.suffix.lower() == ".docx":
            pages = de.read_docx(path)
        else:
            pages = de.read_text(path)
    except Exception:
        return None
    text = "\n".join(t for _, t in pages)[:4000]
    for m in re.finditer(de.DATE_RX, text, re.I):
        iso, _ = de.parse_date(m.group(0))
        if iso:
            return datetime.date.fromisoformat(iso)
    return None


def dated(path):
    ext = path.suffix.lower()
    if ext in IMAGES:
        d = exif_date(path)
        if d:
            return d, "camera date"
    d = name_date(path.name)
    if d:
        return d, "date in file name"
    if ext in DOCS:
        d = text_date(path)
        if d:
            return d, "date printed in the document: confirm it's the right one"
    return datetime.date.fromtimestamp(path.stat().st_mtime), "file date: confirm"


def category(path):
    for label, rx in CATEGORIES:
        if re.search(rx, path.stem, re.I):
            return label
    return PHOTOS if path.suffix.lower() in IMAGES else "Other"


def source(folder, given):
    root = pathlib.Path(given) if given else folder / "03-documents" / "relationship"
    if not root.is_dir():
        die(f"no evidence folder: {root}. Put the relationship evidence there, or give --folder")
    return root


def items(root):
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGES | DOCS and "client-ids" not in {x.lower() for x in p.parts}:
            d, how = dated(p)
            out.append({"date": d, "how": how, "category": category(p), "file": p.relative_to(root).as_posix(), "include": "", "caption": ""})
    return sorted(out, key=lambda r: (r["date"], r["file"]))


def timeline_path(folder):
    return folder / "05-forms-submissions" / "relationship-evidence" / "evidence-timeline.xlsx"


def cmd_timeline(a):
    import openpyxl
    folder = de.active_case(a.case)
    root = source(folder, a.folder)
    rows = items(root)
    if not rows:
        die(f"no photos or documents found in {root}")
    path = timeline_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not a.replace:
        die(f"a timeline already exists with your changes: {path}. Use --replace to start again")
    book = openpyxl.Workbook()
    book.remove(book.active)
    counts = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    span = f"{rows[0]['date']} to {rows[-1]['date']}"
    de.add_sheet(book, "Read me first", ["How to use this timeline"], [
        [f"{len(rows)} item(s) from {root}, dated {span}."],
        ["Check every date marked 'confirm'. Change a category, date or caption in the Timeline sheet; 'evidence.py build' uses your changes."],
        [f"Photos: mark up to {LIMIT_PHOTOS} with Include = yes (IMM 5533 limit as recorded in the knowledge base). If none are marked, they are picked spread across the years."],
        [f"Proof of contact: at most {LIMIT_CONTACT} pages. Choose representative samples across the relationship."],
        ["Captions are yours: dates, places and who is shown. The relationship's story belongs to the client's own IMM 5532 answers."]]
        + [[f"{k}: {v}"] for k, v in sorted(counts.items())], [120])
    de.add_sheet(book, "Timeline", FIELDS, [[i, r["date"].isoformat(), r["how"], r["category"], r["file"], r["include"], r["caption"]] for i, r in enumerate(rows, 1)],
                 [6, 12, 30, 28, 50, 16, 50])
    years = sorted({r["date"].year for r in rows})
    gaps = [f"{y1} to {y2}" for y1, y2 in zip(years, years[1:]) if y2 - y1 > 1]
    if gaps:
        de.add_sheet(book, "Gaps", ["Years with no evidence"], [[g] for g in gaps], [40])
    book.save(path)
    cs.add_log(folder, f"Relationship evidence timeline made: {len(rows)} items")
    print(f"{len(rows)} item(s), {span}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if gaps:
        print("No evidence in the years between: " + "; ".join(gaps) + ". Ask the client whether there is any.")
    unsure = sum(1 for r in rows if "confirm" in r["how"])
    if unsure:
        print(f"{unsure} date(s) to confirm.")
    print(f"Saved: {path}\nCheck it, mark the photos to include and add captions, then: evidence.py build {a.case}")


def read_timeline(folder):
    import openpyxl
    path = timeline_path(folder)
    if not path.exists():
        die("make the timeline first: evidence.py timeline CASE")
    sheet = openpyxl.load_workbook(path, data_only=True)["Timeline"]
    head = [c.value for c in sheet[1]]
    out = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        r = dict(zip(head, row))
        if not r.get("File"):
            continue
        d = r.get("Date")
        d = d.date() if isinstance(d, datetime.datetime) else d if isinstance(d, datetime.date) else datetime.date.fromisoformat(str(d)[:10])
        out.append({"date": d, "category": str(r.get("Category") or "Other"), "file": str(r["File"]), "include": str(r.get("Include? (yes/no)") or "").strip().lower(),
                    "caption": str(r.get("Caption (yours)") or "").strip()})
    return sorted(out, key=lambda r: (r["date"], r["file"]))


def spread(rows, n):
    if len(rows) <= n:
        return rows
    step = (len(rows) - 1) / (n - 1) if n > 1 else 0
    return [rows[round(i * step)] for i in range(n)]


def photo_pdf(rows, root, path):
    from PIL import Image, ImageOps
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    slot_h = (h - 72) / 2
    for i, r in enumerate(rows):
        top = h - 36 - (i % 2) * slot_h
        with Image.open(root / r["file"]) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((1600, 1600))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=80)
            iw, ih = im.size
        scale = min((w - 72) / iw, (slot_h - 40) / ih)
        dw, dh = iw * scale, ih * scale
        c.drawImage(ImageReader(io.BytesIO(buf.getvalue())), (w - dw) / 2, top - dh, dw, dh)
        c.setFont("Helvetica", 10)
        c.drawCentredString(w / 2, top - dh - 14, (f"{r['date']:%B %d, %Y}" + (f": {r['caption']}" if r["caption"] else ""))[:120])
        if i % 2 == 1 or i == len(rows) - 1:
            c.showPage()
    c.save()


def combine(rows, root, path, max_pages=None):
    import pypdf
    import pdf_studio as ps
    w = pypdf.PdfWriter()
    for r in rows:
        src = root / r["file"]
        ext = src.suffix.lower()
        try:
            if ext == ".pdf":
                reader = pypdf.PdfReader(str(src))
            elif ext in IMAGES:
                reader = pypdf.PdfReader(io.BytesIO(ps.image_to_pdf_bytes(src)))
            else:
                continue  # Word and text files: convert to PDF first (/pdf)
            for page in reader.pages:
                w.add_page(page)
        except Exception as e:
            print(f"  Skipped {r['file']} ({type(e).__name__})")
    pages = len(w.pages)
    if not pages:
        return 0
    with open(path, "wb") as f:
        w.write(f)
    return pages


def cmd_build(a):
    folder = de.active_case(a.case)
    root = source(folder, a.folder)
    rows = read_timeline(folder)
    out = timeline_path(folder).parent
    photos = [r for r in rows if r["category"] == PHOTOS and r["include"] != "no" and (root / r["file"]).suffix.lower() in IMAGES]
    chosen = [r for r in photos if r["include"] == "yes"]
    if len(chosen) > a.photos:
        die(f"{len(chosen)} photos are marked yes; the limit is {a.photos}. Unmark some")
    if not chosen:
        chosen = spread(photos, a.photos)
    made = []
    if chosen:
        p = out / "relationship-photos.pdf"
        photo_pdf(chosen, root, p)
        made.append((p.name, f"{len(chosen)} photos, {chosen[0]['date']} to {chosen[-1]['date']}"))
    by_cat = {}
    for r in rows:
        if r["category"] != PHOTOS and r["include"] != "no":
            by_cat.setdefault(r["category"], []).append(r)
    skipped_docs = [r["file"] for r in rows if r["include"] != "no" and pathlib.Path(r["file"]).suffix.lower() in (".docx", ".txt")]
    for cat, items_ in by_cat.items():
        p = out / f"relationship-{re.sub(r'[^a-z]+', '-', cat.lower()).strip('-')}.pdf"
        n = combine(items_, root, p)
        if not n:
            continue
        note = f"{len(items_)} item(s), {n} page(s)"
        if cat == "Communication" and n > a.contact_pages:
            note += f": OVER the {a.contact_pages}-page limit for proof of contact. Mark some items 'no' in the timeline and build again"
        made.append((p.name, note))
    index = out / "relationship-evidence-index.xlsx"
    import openpyxl
    book = openpyxl.Workbook()
    book.remove(book.active)
    de.add_sheet(book, "Index", ["Date", "Category", "Item", "Caption"], [[r["date"].isoformat(), r["category"], r["file"], r["caption"]] for r in rows if r["include"] != "no" and (r["category"] != PHOTOS or r in chosen)],
                 [12, 28, 50, 60])
    book.save(index)
    cs.add_log(folder, "Relationship evidence PDFs built: " + ", ".join(n for n, _ in made))
    print(f"Saved in {out}:")
    for n, note in made:
        print(f"  {n}: {note}")
    print(f"  {index.name}: index of everything included")
    if skipped_docs:
        print(f"Word or text files not added ({len(skipped_docs)}): convert them to PDF first (/pdf to-pdf), then build again.")
    print("Check each PDF's size against IRCC's upload limit (/pdf compress if needed) and the current IMM 5533 checklist.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Relationship evidence organiser")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("timeline"); x.add_argument("case"); x.add_argument("--folder"); x.add_argument("--replace", action="store_true"); x.set_defaults(fn=cmd_timeline)
    x = s.add_parser("build"); x.add_argument("case"); x.add_argument("--folder"); x.add_argument("--photos", type=int, default=LIMIT_PHOTOS)
    x.add_argument("--contact-pages", type=int, default=LIMIT_CONTACT); x.set_defaults(fn=cmd_build)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
