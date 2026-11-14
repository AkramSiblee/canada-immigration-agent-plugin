#!/usr/bin/env python3
"""Back up and restore the firm's data: case files, client account records, Input/ and Output/.

Usage:
  python3 scripts/backup.py setup --to DIR [--every 7]     where backups go, and how often the daily alerts make one
  python3 scripts/backup.py create [--to DIR]               make a backup now
  python3 scripts/backup.py list [--to DIR]
  python3 scripts/backup.py verify ZIP                      check every file in a backup against its fingerprint
  python3 scripts/backup.py restore ZIP --into NEW_DIR      unpack a backup into an empty folder
  python3 scripts/backup.py status

What is in a backup: cases/ (open and closed files, client-ids, ledgers, reconciliations, conflict checks, firm
profile and settings), Input/, Output/, your logo, CLAUDE.local.md and .claude/settings.local.json. The agent itself
is not backed up: reinstall it from the plugin.

Guarantees:
  - Nothing is ever deleted, and no existing file is overwritten: each backup is a new file, and restore only writes
    into an empty or new folder. Moving restored files back is your decision.
  - Each backup holds a manifest with a SHA-256 fingerprint of every file. A backup is checked after it is written
    and kept only if every file reads back exactly.
  - Backups aren't encrypted, and they contain identity documents. Keep them on an encrypted drive or in storage that
    meets your privacy obligations (CICC Code, PIPEDA or provincial law).
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402

REPO = cs.REPO
SETTINGS = cs.ROOT / ".backup-settings.json"
STATE = cs.ROOT / ".backup-state.json"
DEFAULT_DIR = REPO / "backups"
SOURCES = ["cases", "Input", "Output"]
SINGLE = ["CLAUDE.local.md", ".claude/settings.local.json"]
SKIP_NAMES = {"__pycache__", ".dashboard.json", ".dashboard-error.log"}
MANIFEST = "backup-manifest.json"
DEFAULT_EVERY = 7


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def destination(given=None):
    return pathlib.Path(given or load(SETTINGS).get("to") or DEFAULT_DIR).expanduser()


def files_to_back_up():
    """(path on disk, name in the backup). Skips files that are being written (.tmp, .part) and the dashboard's own state."""
    out = []
    for top in SOURCES:
        base = cs.ROOT if top == "cases" else REPO / top
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and not (set(p.relative_to(base).parts) & SKIP_NAMES) and p.suffix not in (".tmp", ".part"):
                out.append((p, f"{top}/{p.relative_to(base).as_posix()}"))
    for rel in SINGLE:
        if (REPO / rel).is_file():
            out.append((REPO / rel, rel))
    logo = load(cs.ROOT / ".firm-profile.json").get("logo")
    if logo and pathlib.Path(logo).is_file():
        out.append((pathlib.Path(logo), f"firm-logo/{pathlib.Path(logo).name}"))
    return out


def inside(child, parent):
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def create(to=None, now=None):
    now = now or datetime.datetime.now()
    out = destination(to)
    for top in SOURCES:
        if inside(out, cs.ROOT if top == "cases" else REPO / top):
            raise ValueError(f"backups can't go inside {top}/ (they would back up themselves)")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"immigration-agent-backup-{now:%Y-%m-%d-%H%M%S}.zip"
    if path.exists():
        raise ValueError(f"already exists: {path}")
    part = path.with_name(path.name + ".part")
    manifest = {"made": now.isoformat(timespec="seconds"), "agent_version": (REPO / "VERSION").read_text(encoding="utf-8").strip() if (REPO / "VERSION").exists() else "", "files": {}}
    skipped = []
    with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for src, name in files_to_back_up():
            try:
                data = src.read_bytes()  # one read, so the fingerprint is of exactly what was stored
            except OSError as e:
                skipped.append(f"{name} ({type(e).__name__})")
                continue
            manifest["files"][name] = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
            z.writestr(zipfile.ZipInfo(name, date_time=datetime.datetime.fromtimestamp(src.stat().st_mtime).timetuple()[:6]), data, zipfile.ZIP_DEFLATED)
        manifest["skipped"] = skipped
        z.writestr(MANIFEST, json.dumps(manifest, indent=1))
    problems = verify(part)
    if problems:
        part.unlink()
        raise ValueError("the backup didn't read back exactly, so it wasn't kept: " + "; ".join(problems[:5]))
    os.replace(part, path)
    state = load(STATE)
    state.update(last=now.isoformat(timespec="seconds"), last_file=str(path), files=len(manifest["files"]), size=path.stat().st_size)
    save(STATE, state)
    return path, manifest


def verify(path):
    problems = []
    try:
        with zipfile.ZipFile(path) as z:
            manifest = json.loads(z.read(MANIFEST))
            names = set(z.namelist()) - {MANIFEST}
            for name, meta in manifest["files"].items():
                if name not in names:
                    problems.append(f"missing: {name}")
                elif hashlib.sha256(z.read(name)).hexdigest() != meta["sha256"]:
                    problems.append(f"changed: {name}")
            problems += [f"not in the manifest: {n}" for n in sorted(names - set(manifest["files"]))]
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as e:
        problems.append(f"unreadable backup ({type(e).__name__})")
    return problems


def safe_name(name):
    p = pathlib.PurePosixPath(name)
    return not (p.is_absolute() or ".." in p.parts or ":" in name or "\\" in name)


def restore(path, into):
    into = pathlib.Path(into).expanduser()
    if into.exists() and any(into.iterdir()):
        raise ValueError(f"{into} isn't empty. Restore into a new or empty folder; nothing is overwritten")
    problems = verify(path)
    if problems:
        raise ValueError("the backup failed its check, so nothing was restored: " + "; ".join(problems[:5]))
    into.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(path) as z:
        for name in json.loads(z.read(MANIFEST))["files"]:
            if not safe_name(name):
                raise ValueError(f"unsafe file name in backup: {name}")
            target = into / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
            n += 1
    return n


def due(today=None):
    """(is a backup due, days since the last one or None). Only when there are case files to protect."""
    today = today or datetime.date.today()
    last = load(STATE).get("last")
    if not last:
        return True, None
    days = (today - datetime.date.fromisoformat(last[:10])).days
    return days >= int(load(SETTINGS).get("every", DEFAULT_EVERY)), days


def auto(today=None):
    """Called by the daily alerts. Makes a backup when one is due and a destination is set and reachable. Returns a message or None."""
    settings = load(SETTINGS)
    if not settings.get("to") or not due(today)[0]:
        return None
    if not pathlib.Path(settings["to"]).expanduser().exists():
        return f"backup folder not reachable: {settings['to']} (plug in the drive or run backup.py setup)"
    path, _ = create()
    return f"backup made: {path.name}"


def human(n):
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024


def cmd_setup(a):
    to = pathlib.Path(a.to).expanduser().resolve()
    if inside(to, REPO):
        print("Note: this folder is inside the agent folder, on the same disk. A backup there doesn't survive a disk failure or a lost laptop. Prefer an external or network drive.")
    if a.every < 1:
        cs.die("--every must be 1 day or more")
    to.mkdir(parents=True, exist_ok=True)
    save(SETTINGS, {"to": str(to), "every": a.every})
    print(f"Backups go to {to}, every {a.every} day(s), made by the daily alerts (alerts.py install) or by backup.py create.")


def cmd_create(a):
    try:
        path, m = create(a.to)
    except ValueError as e:
        cs.die(str(e))
    print(f"Backup made and checked: {path}")
    print(f"{len(m['files'])} files, {human(path.stat().st_size)}")
    for s in m["skipped"]:
        print("  Not backed up (couldn't read):", s)
    if inside(path, REPO) and not load(SETTINGS).get("to"):
        print("It is on the same disk as your files. Copy it to an external drive, or run backup.py setup --to <drive folder>.")
    print("It contains identity documents and isn't encrypted: store it securely.")


def cmd_list(a):
    out = destination(a.to)
    zips = sorted(out.glob("immigration-agent-backup-*.zip")) if out.exists() else []
    print(f"{len(zips)} backup(s) in {out}")
    for z in zips:
        print(f"  {z.name}  {human(z.stat().st_size)}")


def cmd_verify(a):
    problems = verify(a.zip)
    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for p in problems[:50]:
            print("  " + p)
        sys.exit(1)
    with zipfile.ZipFile(a.zip) as z:
        m = json.loads(z.read(MANIFEST))
    print(f"OK: all {len(m['files'])} files match their fingerprints. Made {m['made']} (agent {m.get('agent_version') or 'unknown'}).")


def cmd_restore(a):
    try:
        n = restore(a.zip, a.into)
    except ValueError as e:
        cs.die(str(e))
    print(f"Restored {n} files into {a.into}")
    print("Nothing in your agent folder was changed. To use the restored files, close the dashboard and Claude, then move")
    print("the folders you need (cases, Input, Output) into the agent folder yourself, keeping the current ones until you're sure.")


def cmd_status(_):
    settings, state = load(SETTINGS), load(STATE)
    print("Backup folder:", settings.get("to") or f"not set (default {DEFAULT_DIR}, same disk)")
    print("Every:", f"{settings.get('every', DEFAULT_EVERY)} day(s)" + ("" if settings.get("to") else " (automatic backups need backup.py setup --to DIR)"))
    is_due, days = due()
    print("Last backup:", f"{state['last']} ({days} day(s) ago), {state.get('files', '?')} files" if state.get("last") else "never")
    if is_due:
        print("A backup is due: backup.py create")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Back up and restore the firm's data")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("setup"); x.add_argument("--to", required=True); x.add_argument("--every", type=int, default=DEFAULT_EVERY); x.set_defaults(fn=cmd_setup)
    x = s.add_parser("create"); x.add_argument("--to"); x.set_defaults(fn=cmd_create)
    x = s.add_parser("list"); x.add_argument("--to"); x.set_defaults(fn=cmd_list)
    x = s.add_parser("verify"); x.add_argument("zip"); x.set_defaults(fn=cmd_verify)
    x = s.add_parser("restore"); x.add_argument("zip"); x.add_argument("--into", required=True); x.set_defaults(fn=cmd_restore)
    x = s.add_parser("status"); x.set_defaults(fn=cmd_status)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
