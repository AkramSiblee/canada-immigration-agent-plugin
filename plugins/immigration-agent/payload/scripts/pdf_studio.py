#!/usr/bin/env python3
"""Private PDF studio: combine, organize, split, compress and convert documents on this computer.

Nothing is uploaded anywhere. Word, Excel and PowerPoint files are converted with the local LibreOffice.

  info FILE...                               pages, size, scanned or text, IRCC form, encryption
  combine IN... [--out F]                    PDFs, images and office files into one PDF, a bookmark per file
  organize FILE [--pages 3,1-2,5-end] [--delete 4] [--rotate 2:90] [--out F]
  split FILE (--every N | --ranges "1-3;4-end" | --max-mb 4) [--out-dir D]
  compress FILE [--target-mb 4] [--rasterize] [--out F]
  to-pdf IN... [--out-dir D]                 each image or office file to its own PDF
  to-images FILE [--dpi 150] [--format png|jpg] [--pages 1-3] [--out-dir D]
  to-text FILE [--pages 1-3]                 printed to the screen

Outputs go to Output/general/ unless you name a place. Existing files are never overwritten (-v2, -v3 ...).
Input/ is read-only and client-ids folders are never opened.
"""
import argparse
import datetime
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = REPO / "Output" / "general"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
OFFICE_EXT = {".doc", ".docx", ".odt", ".rtf", ".txt", ".xls", ".xlsx", ".ods", ".csv", ".ppt", ".pptx", ".odp"}
IRCC_LIMIT_MB = 4.0  # most IRCC portals (knowledge/11-forms-fees-processing/portals-and-submission.md, checked 2026-11-09); IRCC Portal: 5 MB
SOFFICE = [pathlib.Path(os.environ.get("SOFFICE", "")), pathlib.Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
           pathlib.Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"), pathlib.Path("/usr/bin/soffice"),
           pathlib.Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")]
FORM_WARNING = ("is an IRCC form with its own form data (and barcodes once validated). Upload it as it is: combining, reorganizing or compressing "
                "loses the form data, and IRCC's dynamic forms can come out as a blank 'please wait' page. Use --allow-forms only for a flattened, printed or scanned copy")


def fail(msg):
    sys.exit(f"ERROR: {msg}")


# ---- safety ----
def check_input(path):
    p = pathlib.Path(path)
    if any(part.lower() == "client-ids" for part in p.resolve().parts):
        fail(f"{p.name}: client-ids folders are not opened")
    if not p.is_file():
        fail(f"{p}: file not found")
    return p


def check_output(path):
    p = pathlib.Path(path).resolve()
    input_dir = (REPO / "Input").resolve()
    if p == input_dir or input_dir in p.parents:
        fail("refusing to write inside Input/, which is read-only")
    if any(part.lower() == "client-ids" for part in p.parts):
        fail("refusing to write inside a client-ids folder")
    return p


def free_name(path):
    """The path itself, or -v2, -v3 ... if it exists. Never overwrite."""
    path = pathlib.Path(path)
    n = 1
    while True:
        p = path if n == 1 else path.with_name(f"{path.stem}-v{n}{path.suffix}")
        if not p.exists():
            return p
        n += 1


def out_path(given, kind, suffix=".pdf"):
    if given:
        p = pathlib.Path(given)
        if p.suffix.lower() != suffix:
            p = p.with_suffix(suffix)
    else:
        p = OUTPUT / f"{datetime.date.today().isoformat()}-{kind}{suffix}"
    check_output(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    return free_name(p)


def out_dir(given, kind):
    d = pathlib.Path(given) if given else OUTPUT / f"{datetime.date.today().isoformat()}-{kind}"
    check_output(d)
    d = free_name(d) if not given else d
    d.mkdir(parents=True, exist_ok=True)
    return d


def mb(n):
    return n / 1024 / 1024


# ---- reading ----
def reader(path, password=None):
    import pypdf
    try:
        r = pypdf.PdfReader(str(path), strict=False)
    except Exception as e:  # damaged files
        fail(f"{pathlib.Path(path).name}: can't be read ({type(e).__name__})")
    if r.is_encrypted:
        # many PDFs (IRCC's forms among them) only restrict editing and open with an empty password
        if not r.decrypt(password or ""):
            fail(f"{pathlib.Path(path).name} is password protected. Give the password with --password")
    return r


def is_form(r):
    try:
        acro = r.trailer["/Root"].get("/AcroForm")
        return bool(acro and acro.get_object().get("/XFA") is not None)
    except Exception:
        return False


def is_signed(r):
    try:
        for f in (r.get_fields() or {}).values():
            if f.get("/FT") == "/Sig" and f.get("/V"):
                return True
    except Exception:
        pass
    return False


def guard_forms(r, name, allow):
    if is_form(r) and not allow:
        fail(f"{name} {FORM_WARNING}")
    if is_signed(r):
        print(f"Note: {name} has a digital signature. Any change makes that signature invalid.")


def page_spec(spec, count):
    """'1-3,5,7-end' -> [0,1,2,4,6,...]; '3-1' counts down. Page numbers start at 1."""
    pages = []
    for part in (spec or "").replace(" ", "").split(","):
        if not part:
            continue
        m = re.fullmatch(r"(\d+|end)(?:-(\d+|end))?", part, re.I)
        if not m:
            fail(f"page range '{part}' not understood (use e.g. 1-3,5,7-end)")
        a = count if m.group(1).lower() == "end" else int(m.group(1))
        b = a if m.group(2) is None else (count if m.group(2).lower() == "end" else int(m.group(2)))
        for n in (a, b):
            if not 1 <= n <= count:
                fail(f"page {n} is out of range (the file has {count} pages)")
        pages += list(range(a, b + 1)) if a <= b else list(range(a, b - 1, -1))
    return [p - 1 for p in pages]


# ---- converting ----
def soffice():
    for p in SOFFICE:
        if str(p) not in ("", ".") and p.is_file():
            return str(p)
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if not found:
        fail("LibreOffice is needed for Word, Excel and PowerPoint files and wasn't found. Install it, or set SOFFICE to soffice's path")
    return found


def office_to_pdf(path, tmp):
    """Convert with the local LibreOffice, using its own profile so an open LibreOffice window doesn't block it."""
    profile = pathlib.Path(tmp) / "lo-profile"
    cmd = [soffice(), f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(path)]
    try:
        subprocess.run(cmd, capture_output=True, timeout=300, check=False)
    except subprocess.TimeoutExpired:
        fail(f"{path.name}: conversion took too long")
    pdf = pathlib.Path(tmp) / f"{path.stem}.pdf"
    if not pdf.exists():
        fail(f"{path.name}: LibreOffice couldn't convert it")
    return pdf


def image_to_pdf_bytes(path, dpi=150):
    from PIL import Image, ImageOps
    with Image.open(path) as im:
        frames = []
        for i in range(getattr(im, "n_frames", 1)):  # multi-page TIFF
            im.seek(i)
            frames.append(ImageOps.exif_transpose(im.copy()).convert("RGB"))
    buf = io.BytesIO()
    frames[0].save(buf, "PDF", save_all=True, append_images=frames[1:], resolution=dpi)
    return buf.getvalue()


def as_pdf_reader(path, tmp, password=None):
    """Any supported input as a PDF reader."""
    import pypdf
    ext = path.suffix.lower()
    if ext == ".pdf":
        return reader(path, password)
    if ext in IMAGE_EXT:
        return pypdf.PdfReader(io.BytesIO(image_to_pdf_bytes(path)))
    if ext in OFFICE_EXT:
        return reader(office_to_pdf(path, tmp))
    fail(f"{path.name}: file type {ext or '(none)'} not supported")


def writer():
    import pypdf
    w = pypdf.PdfWriter()
    w.add_metadata({"/Producer": "pdf_studio (local)"})
    return w


def save(w, path):
    with open(path, "wb") as f:
        w.write(f)
    return path


def report(path, note=""):
    import pypdf
    n = len(pypdf.PdfReader(str(path)).pages)
    size = mb(path.stat().st_size)
    over = f"  Over IRCC's {IRCC_LIMIT_MB:g} MB upload limit: use compress or split --max-mb" if size > IRCC_LIMIT_MB else ""
    print(f"Saved: {path}  ({n} pages, {size:.2f} MB){over}")
    if note:
        print(note)


# ---- commands ----
def cmd_info(a):
    for f in a.files:
        p = check_input(f)
        size = mb(p.stat().st_size)
        if p.suffix.lower() != ".pdf":
            print(f"{p.name}: {p.suffix} file, {size:.2f} MB (convert with to-pdf)")
            continue
        r = reader(p, a.password)
        text = sum(1 for pg in r.pages[:20] if (pg.extract_text() or "").strip())
        checked = min(len(r.pages), 20)
        kind = "text" if text == checked else "scanned (no text)" if text == 0 else f"mixed ({text} of the first {checked} pages have text)"
        flags = [x for x, on in (("IRCC form (upload as is)", is_form(r)), ("digitally signed", is_signed(r))) if on]
        limit = f"over the {IRCC_LIMIT_MB:g} MB limit" if size > IRCC_LIMIT_MB else "within the upload limit"
        print(f"{p.name}: {len(r.pages)} pages, {size:.2f} MB ({limit}), {kind}" + (f", {', '.join(flags)}" if flags else ""))


def cmd_combine(a):
    files = [check_input(f) for f in a.files]
    if len(files) < 2:
        fail("give at least two files to combine")
    w = writer()
    with tempfile.TemporaryDirectory() as tmp:
        for p in files:
            r = as_pdf_reader(p, tmp, a.password)
            guard_forms(r, p.name, a.allow_forms)
            start = len(w.pages)
            for page in r.pages:
                w.add_page(page)
            if not a.no_bookmarks:
                w.add_outline_item(p.stem, start)
        if a.compact:
            w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        path = save(w, out_path(a.out, "combined"))
    report(path, f"Combined {len(files)} files in this order: " + ", ".join(p.name for p in files))


def cmd_organize(a):
    p = check_input(a.file)
    r = reader(p, a.password)
    guard_forms(r, p.name, a.allow_forms)
    count = len(r.pages)
    order = page_spec(a.pages, count) if a.pages else list(range(count))
    if a.delete:
        gone = set(page_spec(a.delete, count))
        order = [i for i in order if i not in gone]
    if not order:
        fail("no pages left")
    turns = {}
    for spec in a.rotate or []:
        m = re.fullmatch(r"(.+):(-?\d+)", spec.replace(" ", ""))
        if not m or int(m.group(2)) % 90:
            fail(f"rotation '{spec}' not understood (use e.g. 2:90 or 1-3:180)")
        for i in page_spec(m.group(1), count):
            turns[i] = (turns.get(i, 0) + int(m.group(2))) % 360
    w = writer()
    for i in order:
        page = w.add_page(r.pages[i])
        if turns.get(i):
            page.rotate(turns[i])
    path = save(w, out_path(a.out, "organized"))
    report(path, f"Pages, in order: {', '.join(str(i + 1) for i in order)}" + (f"; rotated: {', '.join(f'{i + 1} by {d}' for i, d in sorted(turns.items()))}" if turns else ""))


def cmd_split(a):
    p = check_input(a.file)
    r = reader(p, a.password)
    guard_forms(r, p.name, a.allow_forms)
    count = len(r.pages)
    if a.every:
        groups = [list(range(i, min(i + a.every, count))) for i in range(0, count, a.every)]
    elif a.ranges:
        groups = [page_spec(part, count) for part in a.ranges.split(";") if part.strip()]
    else:
        groups = size_groups(r, a.max_mb)
    folder = out_dir(a.out_dir, f"{p.stem}-split")
    for n, pages in enumerate(groups, 1):
        w = writer()
        for i in pages:
            w.add_page(r.pages[i])
        path = save(w, free_name(folder / f"{p.stem}-part{n}.pdf"))
        size = mb(path.stat().st_size)
        warn = "  (one page alone is over the limit: compress it)" if a.max_mb and size > a.max_mb else ""
        print(f"Saved: {path.name}  pages {pages[0] + 1}-{pages[-1] + 1}, {size:.2f} MB{warn}")
    print(f"Folder: {folder}")


def size_groups(r, limit):
    """Consecutive pages in parts that each stay under the limit (measured by writing them)."""
    groups, current = [], []
    for i in range(len(r.pages)):
        trial = current + [i]
        w = writer()
        for j in trial:
            w.add_page(r.pages[j])
        buf = io.BytesIO()
        w.write(buf)
        if current and mb(buf.tell()) > limit:
            groups.append(current)
            current = [i]
        else:
            current = trial
    if current:
        groups.append(current)
    return groups


def shrink(r, quality, max_side):
    """A copy with every image re-saved as JPEG at this quality and size. Text stays text."""
    from PIL import Image
    w = writer()
    for page in r.pages:
        w.add_page(page)
    done = 0
    for page in w.pages:
        try:
            images = list(page.images)
        except Exception:
            continue
        for img in images:
            try:
                im = img.image
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGB")
                elif im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                if max(im.size) > max_side:
                    im.thumbnail((max_side, max_side), Image.LANCZOS)
                img.replace(im, quality=quality)
                done += 1
            except Exception:
                continue  # masks and unusual images are left as they are
    for page in w.pages:
        try:
            page.compress_content_streams()
        except Exception:
            pass
    w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue(), done


def rasterize(path, dpi, quality, password=None):
    """Every page as a JPEG picture: smallest, but text can no longer be selected or searched."""
    import pypdfium2
    doc = pypdfium2.PdfDocument(str(path), password=password)
    pages = [doc[i].render(scale=dpi / 72).to_pil().convert("RGB") for i in range(len(doc))]
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:], resolution=dpi, quality=quality)
    return buf.getvalue()


def cmd_compress(a):
    p = check_input(a.file)
    r = reader(p, a.password)
    guard_forms(r, p.name, a.allow_forms)
    target, before = a.target_mb, mb(p.stat().st_size)
    best, how = None, ""
    for quality, side in ((85, 2400), (75, 2000), (65, 1700), (55, 1400), (45, 1200), (35, 1000)):
        data, done = shrink(r, quality, side)
        if best is None or len(data) < len(best):
            best, how = data, (f"{done} image(s) re-saved at JPEG quality {quality}, longest side {side} px" if done else "page content compressed (no images to shrink)")
        if not done:
            break  # no images: other settings give the same result
        if mb(len(data)) <= target:
            break
    if mb(len(best)) > target and a.rasterize:
        for dpi, quality in ((150, 70), (120, 60), (100, 50), (85, 45)):
            data = rasterize(p, dpi, quality, a.password)
            if len(data) < len(best):
                best, how = data, f"pages turned into pictures at {dpi} dpi (text no longer selectable)"
            if mb(len(data)) <= target:
                break
    if p.stat().st_size - len(best) < max(0.05 * p.stat().st_size, 20 * 1024):  # under 5% or 20 KB saved isn't worth a second copy
        print(f"{p.name} is already as small as it gets this way ({before:.2f} MB). Nothing saved." + ("" if before <= target else " Try --rasterize, or split --max-mb"))
        return
    path = out_path(a.out, f"{p.stem}-compressed")
    path.write_bytes(best)
    note = f"From {before:.2f} MB: {how}."
    if mb(len(best)) > target:
        note += f" Still over {target:g} MB: " + ("split it with split --max-mb." if a.rasterize else "try --rasterize, or split it with split --max-mb.")
    report(path, note + " Check the result is still easy to read before uploading.")


def cmd_to_pdf(a):
    files = [check_input(f) for f in a.files]
    folder = out_dir(a.out_dir, "converted") if len(files) > 1 or a.out_dir else None
    with tempfile.TemporaryDirectory() as tmp:
        for p in files:
            ext = p.suffix.lower()
            target = free_name(folder / f"{p.stem}.pdf") if folder else out_path(None, p.stem)
            if ext in IMAGE_EXT:
                target.write_bytes(image_to_pdf_bytes(p))
            elif ext in OFFICE_EXT:
                shutil.copyfile(office_to_pdf(p, tmp), target)
            elif ext == ".pdf":
                print(f"{p.name} is already a PDF")
                continue
            else:
                fail(f"{p.name}: file type {ext} not supported")
            report(target)


def cmd_to_images(a):
    import pypdfium2
    p = check_input(a.file)
    r = reader(p, a.password)
    count = len(r.pages)
    wanted = page_spec(a.pages, count) if a.pages else list(range(count))
    folder = out_dir(a.out_dir, f"{p.stem}-images")
    doc = pypdfium2.PdfDocument(str(p), password=a.password)
    ext = "jpg" if a.format == "jpg" else "png"
    for i in wanted:
        im = doc[i].render(scale=a.dpi / 72).to_pil()
        target = free_name(folder / f"{p.stem}-p{i + 1}.{ext}")
        if ext == "jpg":
            im.convert("RGB").save(target, "JPEG", quality=85)
        else:
            im.save(target)
    print(f"Saved {len(wanted)} page image(s) at {a.dpi} dpi in {folder}")


def cmd_to_text(a):
    p = check_input(a.file)
    r = reader(p, a.password)
    wanted = page_spec(a.pages, len(r.pages)) if a.pages else range(len(r.pages))
    empty = 0
    for i in wanted:
        t = (r.pages[i].extract_text() or "").strip()
        empty += not t
        print(f"--- page {i + 1} ---\n{t or '(no text: scanned page)'}")
    if empty:
        print(f"\n{empty} page(s) have no text layer. They are pictures; read them with the document-extractor skill.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Private PDF studio: everything stays on this computer")
    s = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        x = s.add_parser(name, help=help_)
        x.add_argument("--password", help="password of a protected PDF")
        x.set_defaults(fn=fn)
        return x
    x = add("info", cmd_info, "pages, size, text or scanned, IRCC form"); x.add_argument("files", nargs="+")
    x = add("combine", cmd_combine, "join PDFs, images and office files into one PDF"); x.add_argument("files", nargs="+"); x.add_argument("--out")
    x.add_argument("--no-bookmarks", action="store_true"); x.add_argument("--compact", action="store_true", help="drop repeated objects (smaller)"); x.add_argument("--allow-forms", action="store_true")
    x = add("organize", cmd_organize, "keep, reorder, delete or rotate pages"); x.add_argument("file"); x.add_argument("--pages"); x.add_argument("--delete")
    x.add_argument("--rotate", action="append", help="PAGES:DEGREES, e.g. 2:90 or 1-3:180"); x.add_argument("--out"); x.add_argument("--allow-forms", action="store_true")
    x = add("split", cmd_split, "split into parts"); x.add_argument("file"); g = x.add_mutually_exclusive_group(required=True)
    g.add_argument("--every", type=int); g.add_argument("--ranges", help='e.g. "1-3;4-end"'); g.add_argument("--max-mb", type=float, help="parts under this size, e.g. 4 for IRCC")
    x.add_argument("--out-dir"); x.add_argument("--allow-forms", action="store_true")
    x = add("compress", cmd_compress, "make smaller, keeping text as text"); x.add_argument("file"); x.add_argument("--target-mb", type=float, default=IRCC_LIMIT_MB)
    x.add_argument("--rasterize", action="store_true", help="if needed, turn pages into pictures (smaller, text not selectable)"); x.add_argument("--out"); x.add_argument("--allow-forms", action="store_true")
    x = add("to-pdf", cmd_to_pdf, "images, Word, Excel or PowerPoint to PDF"); x.add_argument("files", nargs="+"); x.add_argument("--out-dir")
    x = add("to-images", cmd_to_images, "PDF pages to PNG or JPG"); x.add_argument("file"); x.add_argument("--dpi", type=int, default=150)
    x.add_argument("--format", choices=["png", "jpg"], default="png"); x.add_argument("--pages"); x.add_argument("--out-dir")
    x = add("to-text", cmd_to_text, "PDF text to the screen"); x.add_argument("file"); x.add_argument("--pages")
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
