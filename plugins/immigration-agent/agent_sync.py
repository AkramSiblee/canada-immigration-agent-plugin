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

Update check (--hook and --status, at most once a day): reads the public version number of the latest release from
the plugin's GitHub repository. Nothing about the firm, its folder or its clients is sent. If a newer release exists,
the user is told how to install it. The result is kept in .immigration-agent/update-check.json so the dashboard
(which never goes online) can show it too. Set IMMIGRATION_AGENT_NO_UPDATE_CHECK=1 to turn it off.
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
CHECK_FILE = "update-check.json"
MARKETPLACE = "immigration-agent-marketplace"
LATEST_URL = os.environ.get("IMMIGRATION_AGENT_LATEST_URL") or "https://raw.githubusercontent.com/AkramSiblee/canada-immigration-agent-plugin/main/plugins/immigration-agent/.claude-plugin/plugin.json"
CHECK_EVERY = datetime.timedelta(hours=20)
HOW_TO_UPDATE = (f"In the Claude app type /plugin, open Marketplaces, choose {MARKETPLACE}, then Update marketplace "
                 "(and Enable auto-update if it is offered). Then quit and reopen Claude and start a new conversation in "
                 "the agent folder: the new version installs into the folder by itself. Client files are never changed.")


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v or ""))[:3]) or (0,)


def check_latest(ws, plugin_version, force=False):
    """Latest released version (from GitHub, at most once a day; cached), or None. Never raises."""
    p = ws / STATE_DIR / CHECK_FILE
    try:
        cache = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        cache = {}
    now = datetime.datetime.now(datetime.timezone.utc)
    latest = cache.get("latest")
    try:
        fresh = now - datetime.datetime.fromisoformat(cache.get("checked", "")) < CHECK_EVERY
    except ValueError:
        fresh = False
    if os.environ.get("IMMIGRATION_AGENT_NO_UPDATE_CHECK") != "1" and (force or not fresh):
        try:
            import urllib.request
            req = urllib.request.Request(LATEST_URL, headers={"User-Agent": "immigration-agent-update-check", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=4) as r:
                latest = json.loads(r.read(20000).decode("utf-8")).get("version") or latest
            cache["checked"] = now.isoformat(timespec="seconds")
        except Exception:
            pass  # offline or GitHub unreachable: keep the last known answer
    cache.update({"latest": latest, "plugin": plugin_version})
    try:
        (ws / STATE_DIR).mkdir(exist_ok=True)
        p.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    except OSError:
        pass
    return latest


def update_notice(plugin_version, latest):
    if latest and vtuple(latest) > vtuple(plugin_version):
        return f"A newer Immigration Agent is available: version {latest} (this computer has {plugin_version}). To install it: {HOW_TO_UPDATE}"
    return ""


def hook_output(text, notice, latest=None):
    """SessionStart hook output: the user sees a short message; Claude gets the details and passes them on."""
    if not text and not notice:
        return ""
    context = "\n".join(x for x in (text, notice) if x)
    if notice:
        context += "\nTell the user about this update at the start of your first reply, in plain words, with the steps."
    short = f"Immigration Agent {latest} is available. Ask Claude: how do I update?" if notice else text.splitlines()[0]
    return json.dumps({"systemMessage": short, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}})


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


def same(path, digest):
    """True if the file matches the digest, also when only its line endings differ.
    Git on Windows (core.autocrlf) can turn the plugin's LF files into CRLF when the Claude app downloads it."""
    if not digest:
        return False
    if sha(path) == digest:
        return True
    with open(L(path), "rb") as f:
        data = f.read()
    return b"\r\n" in data and hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == digest


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
        elif not same(t, digest):
            todo.append(("replace-changed" if not same(t, old.get(rel)) else "copy", rel))
    for rel, digest in sorted(old.items()):
        if rel in manifest or PROTECTED.search(rel):
            continue
        t = target(ws, rel)
        if t is not None and exists(t):
            todo.append(("remove" if same(t, digest) else "remove-changed", rel))
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
                if os.name != "nt" and rel.endswith((".command", ".sh")):
                    os.chmod(L(t), 0o755)  # Mac launchers must stay double-clickable
                if action != "create-data":
                    files[rel] = manifest[rel]
            done += 1
        except OSError as e:
            failed.append(f"{rel} ({e.strerror or e})")
    for rel, digest in manifest.items():  # files already identical count as installed
        t = target(ws, rel)
        if t is not None and not DATA.match(rel) and not PROTECTED.search(rel) and rel not in files and exists(t) and same(t, digest):
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
        latest = check_latest(ws, version, force=True)
        print(f"Agent folder: {ws}\nInstalled version: {state.get('version')}\nPlugin version: {version}\n"
              f"Latest release: {latest or 'unknown (could not check online)'}\nPending changes: {len(todo)}")
        notice = update_notice(version, latest)
        if notice:
            print(notice)
        return 0
    if a.hook and state is None:
        return 0  # not an agent folder: stay silent and touch nothing
    first = state is None
    if first:
        state = {"version": None, "files": {}, "created": datetime.date.today().isoformat()}
    msg, failed = "", []
    if first or state.get("version") != version or plan(ws, state, manifest):
        old_version = state.get("version")
        done, failed, backed_up, stamp = apply(ws, state, manifest, version)
        msg = report(old_version, version, done, failed, backed_up, stamp, first)
    elif a.init:
        msg = f"Immigration Agent {version} is already installed and up to date in {ws}."
    latest = check_latest(ws, version)
    notice = update_notice(version, latest)
    if a.hook:
        out = hook_output(msg, notice, latest)
        if out:
            print(out)
        return 0
    if msg or notice:
        print("\n".join(x for x in (msg, notice) if x))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
