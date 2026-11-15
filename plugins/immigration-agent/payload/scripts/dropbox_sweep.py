#!/usr/bin/env python3
"""Client document drop folder: clients upload to a shared folder; this files each document into its case.

Usage:
  python3 scripts/dropbox_sweep.py setup --folder "C:/Users/me/OneDrive/Client uploads"
  python3 scripts/dropbox_sweep.py folders                       make one upload subfolder per open case (named by case id)
  python3 scripts/dropbox_sweep.py sweep [--dry-run]             file everything waiting
  python3 scripts/dropbox_sweep.py status                        what is waiting, and what each case is still missing

How it works:
  - Choose a folder your cloud service syncs to this computer (OneDrive, Google Drive or Dropbox), and share an upload-only
    link to each client's subfolder ("file request" in OneDrive and Dropbox, a shared folder in Google Drive).
  - Each client subfolder starts with the case id, e.g. "2026-001 Khan". A file left at the top is matched by a case id or the
    client's name in its file name; anything that can't be matched stays in "_unsorted" for you.
  - Sweep copies each file into the case's 03-documents/from-client/, named "<date received>-<document type>-<original name>",
    then moves the original into "_filed/<case>/" so nothing is filed twice. Nothing is deleted.

Guarantees:
  - A file is filed into a case only when the match is certain (case id, or the full client name). Never a guess.
  - The document type comes from the same reader as /extract (keyword-based); "unknown" when unsure.
  - Each case logs what came in, and the sweep lists what the case's IRCC checklist still lacks. Run /extract to read the new files.
  - Executable and archive files are not filed (they stay in _unsorted, flagged). Check every file's content before relying on it.
  - The sharing link and folder permissions are yours to manage: use your cloud service's upload-only or expiring links.
"""
import argparse
import datetime
import json
import pathlib
import re
import shutil
import sys
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

SETTINGS = cs.ROOT / ".dropbox-settings.json"
ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".docx", ".doc", ".xlsx", ".txt", ".webp", ".bmp"}
SKIP_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}


def die(msg):
    sys.exit("ERROR: " + msg)


def drop_folder():
    try:
        p = pathlib.Path(json.loads(SETTINGS.read_text(encoding="utf-8"))["folder"])
    except (OSError, ValueError, KeyError):
        return None
    return p


def cmd_setup(a):
    folder = pathlib.Path(a.folder).expanduser()
    if not folder.is_dir():
        die(f"no such folder: {folder}. Create it inside your OneDrive, Google Drive or Dropbox folder first")
    agent = de.REPO.resolve()
    if folder.resolve() == agent or agent in folder.resolve().parents:
        die("choose a folder outside the agent folder (inside your cloud drive)")
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps({"folder": str(folder.resolve())}), encoding="utf-8")
    for sub in ("_unsorted", "_filed"):
        (folder / sub).mkdir(exist_ok=True)
    print(f"Drop folder: {folder}\nNext: dropbox_sweep.py folders, then share each client's subfolder with an upload-only link.")


def need_folder():
    folder = drop_folder()
    if not folder:
        die("no drop folder set. Run: dropbox_sweep.py setup --folder PATH")
    if not folder.is_dir():
        die(f"the drop folder is missing or not synced: {folder}")
    return folder


def cmd_folders(_):
    folder = need_folder()
    made = 0
    for case in cs.folders(cs.ACTIVE):
        info = cs.read_case(case)
        cid = info.get("case_id", case.name[:8])
        if any(p.is_dir() and p.name.startswith(cid) for p in folder.iterdir()):
            continue
        surname = case.name.split("-")[2] if case.name.count("-") >= 2 else ""
        (folder / f"{cid} {surname.capitalize()}".strip()).mkdir()
        made += 1
    print(f"{made} new client folder(s) in {folder}. Share each with its client as an upload-only link.")


def case_for_folder(name, cases):
    m = re.match(r"(\d{4}-\d{3})\b", name)
    if m:
        hit = [c for c in cases if c.name.startswith(m.group(1))]
        return hit[0] if len(hit) == 1 else None
    return None


def case_for_file(name, cases):
    by_id = case_for_folder(re.sub(r"^[^\d]*", "", name), cases)
    if by_id:
        return by_id
    flat = re.sub(r"[^a-z]+", " ", name.lower())
    hits = []
    for c in cases:
        client = re.sub(r"[^a-z]+", " ", cs.read_case(c).get("client", "").lower()).strip()
        if client and len(client.split()) >= 2 and f" {client} " in f" {flat} ":
            hits.append(c)
    return hits[0] if len(hits) == 1 else None


def waiting(folder):
    """[(file, case folder or None)] for everything not yet filed."""
    cases = cs.folders(cs.ACTIVE)
    out = []
    for p in sorted(folder.iterdir()):
        if p.name in ("_unsorted", "_filed") or p.name.lower() in SKIP_NAMES:
            continue
        if p.is_dir():
            case = case_for_folder(p.name, cases)
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.name.lower() not in SKIP_NAMES and not f.name.startswith("~$"):
                    out.append((f, case))
        elif p.is_file():
            out.append((p, case_for_file(p.stem, cases)))
    return out


def doc_type(path):
    opts = types.SimpleNamespace(max_pages=20, large_deposit=5000)
    try:
        rec = de.process_file(path, path.parent, opts)
    except Exception:
        return "unknown"
    return rec.get("doc_type", "unknown") if rec.get("doc_type") not in ("imm_form",) else "ircc-form"


def free(path):
    n = 1
    target = path
    while target.exists():
        n += 1
        target = path.with_name(f"{path.stem}-v{n}{path.suffix}")
    return target


def missing_for(case):
    import readiness as rd
    try:
        cl, rows = rd.case_checklist(case)
    except Exception:
        return None
    if not cl:
        return None
    return [r["item"] for r in rows if r["status"] == rd.MISSING]


def cmd_sweep(a):
    folder = need_folder()
    items = waiting(folder)
    if not items:
        print("Nothing waiting in the drop folder.")
        return
    today = datetime.date.today().isoformat()
    filed, unsorted = {}, []
    for f, case in items:
        ext = f.suffix.lower()
        if ext not in ALLOWED:
            unsorted.append((f, f"file type {ext or 'none'} isn't filed (only documents and images)"))
            if not a.dry_run:
                shutil.move(str(f), str(free(folder / "_unsorted" / f.name)))
            continue
        if not case:
            unsorted.append((f, "no case matched: put it in the client's subfolder, or name it with the case id"))
            if not a.dry_run and f.parent == folder:
                shutil.move(str(f), str(free(folder / "_unsorted" / f.name)))
            continue
        kind = doc_type(f)
        name = re.sub(r"[^\w.\- ]+", "_", f.name)
        if a.dry_run:
            filed.setdefault(case, []).append((f.name, kind))
            continue
        dest_dir = case / "03-documents" / "from-client"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = free(dest_dir / f"{today}-{kind.replace('_', '-')}-{name}")
        shutil.copy2(f, dest)
        done = folder / "_filed" / case.name
        done.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(free(done / f.name)))
        filed.setdefault(case, []).append((dest.name, kind))
    for case, files in filed.items():
        info = cs.read_case(case)
        print(f"{info.get('case_id', case.name[:8])} {info.get('client', '')}: {len(files)} file(s){' would be filed' if a.dry_run else ' filed'}")
        for n, kind in files:
            print(f"    {n}  ({de.PLAIN_TYPES.get(kind, kind)})")
        if not a.dry_run:
            cs.add_log(case, f"Documents received from client via upload folder: {len(files)} file(s)")
            miss = missing_for(case)
            if miss is not None:
                print(f"  Still missing on the checklist: {len(miss)}" + (": " + "; ".join(m[:50] for m in miss[:6]) if miss else ""))
    for f, why in unsorted:
        print(f"Not filed: {f.name}: {why}")
    if filed and not a.dry_run:
        print("Next: /extract CASE to read the new documents (the checklist updates from what it finds).")


def cmd_status(_):
    folder = need_folder()
    items = waiting(folder)
    print(f"Drop folder: {folder}\nWaiting: {len(items)} file(s)" + (f", {sum(1 for _, c in items if not c)} with no matching case" if items else ""))
    left = [p for p in (folder / "_unsorted").glob("*") if p.is_file()] if (folder / "_unsorted").exists() else []
    if left:
        print(f"In _unsorted: {len(left)} file(s) for you to sort")
    for case in cs.folders(cs.ACTIVE):
        miss = missing_for(case)
        if miss:
            print(f"  {cs.read_case(case).get('case_id', case.name[:8])}: {len(miss)} checklist item(s) still missing")


def issues(today):
    """Firm-wide alert: files waiting in the drop folder. (rank, kind, tier, text, step, day)."""
    folder = drop_folder()
    if not folder:
        return []
    if not folder.is_dir():
        return [(2, "Client uploads", "missing", "The client upload folder can't be found (not synced?)", "Check your cloud drive, or run dropbox_sweep.py setup", None)]
    n = len(waiting(folder))
    unsorted = len([p for p in (folder / "_unsorted").glob("*") if p.is_file()]) if (folder / "_unsorted").exists() else 0
    out = []
    if n:
        out.append((3, "Client uploads", "waiting", f"{n} document(s) uploaded by clients are waiting to be filed", "Run /dropbox (dropbox_sweep.py sweep)", None))
    if unsorted:
        out.append((3, "Client uploads", "unsorted", f"{unsorted} uploaded file(s) couldn't be matched to a case", "Open the _unsorted folder and move each into its client's subfolder", None))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Client document drop folder")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("setup"); x.add_argument("--folder", required=True); x.set_defaults(fn=cmd_setup)
    x = s.add_parser("folders"); x.set_defaults(fn=cmd_folders)
    x = s.add_parser("sweep"); x.add_argument("--dry-run", action="store_true"); x.set_defaults(fn=cmd_sweep)
    x = s.add_parser("status"); x.set_defaults(fn=cmd_status)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
