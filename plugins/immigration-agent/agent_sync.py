#!/usr/bin/env python3
"""Keep a firm's agent folder up to date from the installed plugin. Standard library only.

  python3 agent_sync.py --hook      (run by the plugin at every Claude start; silent unless something changed)
  python3 agent_sync.py --init      (make the current folder the firm's agent folder, then install)
  python3 agent_sync.py --status    (installed version, plugin version, pending changes)

The plugin carries payload/ (the agent: CLAUDE.md, .claude/, scripts/, knowledge/, templates/ ...) and
payload-manifest.json ({path: sha256}). This copies it into the agent folder.

Guarantees:
  - Only a folder marked by --init is ever written to. Any other folder Claude opens is left alone.
  - Client and firm data is never written, moved or deleted: cases/, Input/, Output/, forms-cache/, .extraction/,
    .env, CLAUDE.local.md, .claude/settings.local.json. (Their README.md is created only if missing.)
  - A file the firm changed is copied to .immigration-agent/backup/<time>/ before it is replaced or removed.
  - A file that fails to copy is retried at the next start.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
PAYLOAD = HERE / "payload"
STATE_DIR = ".immigration-agent"
STATE_FILE = "workspace.json"
LONG = "\\\\?\\"  # Windows extended-length path prefix
DATA = re.compile(r"^(cases|Input|Output)/")
PROTECTED = re.compile(r"^(cases/|Input/|Output/|forms-cache/|\.extraction/|\.immigration-agent/|\.git/)|^(\.env|CLAUDE\.local\.md|\.claude/settings\.local\.json)$")


def L(path):
    """Windows: a path that also works past the 260-character limit (deep OneDrive folders, long cache paths)."""
    p = str(pathlib.Path(path).absolute())
    if os.name != "nt" or p.startswith(LONG):
        return p
    return LONG + "UNC\\" + p[2:] if p.startswith("\\\\") else LONG + p


def exists(path):
    return os.path.exists(L(path))


def sha(path):
    h = hashlib.sha256()
    with open(L(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def plugin_info():
    manifest = json.loads((HERE / "payload-manifest.json").read_text(encoding="utf-8"))
    version = json.loads((HERE / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version", "?")
    return version, manifest


def workspace():
    return pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def is_source_repo(ws):
    return (ws / ".git").exists() and (ws / "plugin" / "agent_sync.py").exists() and (ws / "scripts" / "build_plugin.py").exists()


def load_state(ws):
    p = ws / STATE_DIR / STATE_FILE
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"version": None, "files": {}}


def save_state(ws, state):
    d = ws / STATE_DIR
    d.mkdir(exist_ok=True)
    tmp = d / (STATE_FILE + ".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, d / STATE_FILE)


def target(ws, rel):
    """The file in the agent folder, or None when the path is unsafe."""
    if rel.startswith("/") or ".." in pathlib.PurePosixPath(rel).parts:
        return None
    t = (ws / rel).resolve()
    return t if ws in t.parents else None


def backup(ws, stamp, rel, src):
    dest = ws / STATE_DIR / "backup" / stamp / rel
    os.makedirs(L(dest.parent), exist_ok=True)
    shutil.copy2(L(src), L(dest))


def plan(ws, state, manifest):
    """[(action, rel)] with action in copy / replace-changed / remove / remove-changed / create-data."""
    old = state.get("files", {})
    todo = []
    for rel, digest in sorted(manifest.items()):
        t = target(ws, rel)
        if t is None:
            continue
        if DATA.match(rel):
            if rel.endswith("README.md") and not exists(t):
                todo.append(("create-data", rel))
            continue
        if PROTECTED.search(rel):
            continue
        if not exists(t):
            todo.append(("copy", rel))
        elif sha(t) != digest:
            todo.append(("replace-changed" if sha(t) != old.get(rel) else "copy", rel))
    for rel, digest in sorted(old.items()):
        if rel in manifest or PROTECTED.search(rel):
            continue
        t = target(ws, rel)
        if t is not None and exists(t):
            todo.append(("remove" if sha(t) == digest else "remove-changed", rel))
    return todo


def apply(ws, state, manifest, version):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    files = dict(state.get("files", {}))
    done, failed, backed_up = 0, [], []
    for action, rel in plan(ws, state, manifest):
        t = target(ws, rel)
        try:
            if action.endswith("changed"):
                backup(ws, stamp, rel, t)
                backed_up.append(rel)
            if action.startswith("remove"):
                os.remove(L(t))
                files.pop(rel, None)
            else:
                os.makedirs(L(t.parent), exist_ok=True)
                tmp = t.with_name(t.name + ".agent-tmp")
                shutil.copy2(L(PAYLOAD / rel), L(tmp))
                os.replace(L(tmp), L(t))
                if action != "create-data":
                    files[rel] = manifest[rel]
            done += 1
        except OSError as e:
            failed.append(f"{rel} ({e.strerror or e})")
    for rel, digest in manifest.items():  # files already identical count as installed
        t = target(ws, rel)
        if t is not None and not DATA.match(rel) and not PROTECTED.search(rel) and rel not in files and exists(t) and sha(t) == digest:
            files[rel] = digest
    new_state = {"version": version if not failed else state.get("version"), "files": files,
                 "updated": datetime.datetime.now().isoformat(timespec="seconds"), "created": state.get("created") or datetime.date.today().isoformat()}
    save_state(ws, new_state)
    return done, failed, backed_up, stamp


def whats_new(old_version, new_version):
    p = PAYLOAD / "WHATS-NEW.md"
    if not p.exists():
        return ""
    out, keep = [], False
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+v?([0-9][^\s]*)", line)
        if m:
            keep = m.group(1) != old_version
            if not keep and out:
                break
        if keep:
            out.append(line)
    return "\n".join(out[:40]).strip()


def report(old_version, version, done, failed, backed_up, stamp, first):
    lines = []
    if first:
        lines.append(f"Immigration Agent {version} installed in this folder ({done} files).")
    elif done or failed:
        lines.append(f"Immigration Agent updated: {old_version or 'earlier version'} -> {version}.")
        note = whats_new(old_version, version)
        if note:
            lines += ["What's new:", note]
        lines.append("New or changed commands work from the next new conversation.")
    if backed_up:
        lines.append(f"{len(backed_up)} file(s) you had changed were saved first in {STATE_DIR}/backup/{stamp}/: " + ", ".join(backed_up[:10]) + (" ..." if len(backed_up) > 10 else ""))
        lines.append("To keep your own instructions across updates, put them in CLAUDE.local.md (never replaced).")
    if failed:
        lines.append(f"{len(failed)} file(s) could not be updated and will be retried next start (close any program using them): " + ", ".join(failed[:5]))
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Install or update the Immigration Agent in the firm's agent folder")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--hook", action="store_true")
    g.add_argument("--init", action="store_true")
    g.add_argument("--status", action="store_true")
    a = p.parse_args()
    ws = workspace()
    try:
        version, manifest = plugin_info()
    except Exception as e:
        if a.hook:
            return 0
        print(f"The plugin files are incomplete ({e}). Reinstall the plugin.")
        return 1
    if is_source_repo(ws):
        if not a.hook:
            print("This is the agent's source folder (where releases are built). It is never synced. Open the firm's agent folder instead.")
        return 0 if a.hook else 1
    state = load_state(ws)
    if a.status:
        if state is None:
            print(f"This folder is not an agent folder yet: {ws}\nPlugin version: {version}. Run the setup command here to install.")
            return 0
        todo = plan(ws, state, manifest)
        print(f"Agent folder: {ws}\nInstalled version: {state.get('version')}\nPlugin version: {version}\nPending changes: {len(todo)}")
        return 0
    if a.hook and state is None:
        return 0  # not an agent folder: stay silent and touch nothing
    first = state is None
    if first:
        state = {"version": None, "files": {}, "created": datetime.date.today().isoformat()}
    if not first and state.get("version") == version and not plan(ws, state, manifest):
        if a.init:
            print(f"Immigration Agent {version} is already installed and up to date in {ws}.")
        return 0
    old_version = state.get("version")
    done, failed, backed_up, stamp = apply(ws, state, manifest, version)
    msg = report(old_version, version, done, failed, backed_up, stamp, first)
    if msg:
        print(msg)
    return 0 if (a.hook or not failed) else 1


if __name__ == "__main__":
    sys.exit(main())
