#!/usr/bin/env python3
"""Office dashboard: deadlines, alerts, cases, documents and agent status in the web browser. No AI, no cost.

  python3 app/dashboard.py              start it and open the browser (or reopen the one already running)
  python3 app/dashboard.py --shortcut   put an "Immigration Agent Dashboard" shortcut on the desktop (Windows)

It opens in its own app window (Microsoft Edge or Google Chrome app mode; otherwise the normal browser). Started from the
shortcut it runs without a console window, and it stops by itself a few minutes after the dashboard window is closed.

Guarantees:
  - Only this computer can open it: it listens on 127.0.0.1, every request needs this run's secret key, and
    requests addressed to any other host name are refused.
  - It reads case files and never changes them. Its one action is opening a file or folder of this agent folder
    in its usual program.
  - Uses the same rules as the daily alerts (scripts/alerts.py), so both always agree.
  - Python standard library only.
"""
import argparse
import datetime
import http.server
import json
import mimetypes
import os
import pathlib
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

APP = pathlib.Path(__file__).resolve().parent
WORK = APP.parent
STATIC = APP / "static"
sys.path.insert(0, str(WORK / "scripts"))
import alerts as al  # noqa: E402
import billing as bl  # noqa: E402
import case as cs  # noqa: E402
import kb_status as kb  # noqa: E402
import updates as up  # noqa: E402

STATE = cs.ROOT / ".dashboard.json"
ERROR_LOG = cs.ROOT / ".dashboard-error.log"
IDLE_STOP = int(os.environ.get("DASHBOARD_IDLE_SECONDS", "300"))  # stop this long after the last dashboard window went away
FIRST_VISIT = int(os.environ.get("DASHBOARD_FIRST_VISIT_SECONDS", "600"))  # stop if no window ever connects
OUTPUT = WORK / "Output"
HIDDEN = re.compile(r"(^|/)(\.|_extraction(/|$)|__pycache__)")
CASE_COMMANDS = [
    ("Readiness report", "/readiness {id}", "Everything still open before filing"),
    ("Document checklist", "/checklist {id}", "What the client must still provide"),
    ("Read documents", "/extract {id}", "Pull names, dates and numbers from new documents"),
    ("Final form check", "/final-check {id}", "Check finished forms before submitting"),
    ("Client follow-up", "/follow-up {id}", "Ask the client for missing answers and documents"),
    ("Status update", "/status-update {id}", "Record what was submitted or received; draft the client update"),
    ("Billing", "/billing {id}", "Invoices, payments and client account"),
]
GENERAL_COMMANDS = [
    ("New client intake", "/intake", "Start a new client matter"),
    ("Open a new case", "/case new", "Create a case file"),
    ("Which program fits?", "/select-program", "Recommend pathways for a client profile"),
    ("CRS score", "/crs", "Express Entry score with what-if options"),
    ("Government fees", "/fees", "Fees for an application"),
    ("What changed?", "/changelog", "Scan official sources for new immigration changes"),
]


def today():
    return datetime.date.today()


def date_of(text):
    try:
        return datetime.date.fromisoformat(str(text).strip())
    except ValueError:
        return None


def roots():
    """Folders whose files the dashboard may open: the agent folder, and the case files when kept elsewhere (CASES_ROOT)."""
    return [WORK, cs.ROOT.resolve()]


def rel(path):
    return str(pathlib.Path(path).resolve())


def firm_name():
    p = cs.ROOT / ".firm-profile.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d.get("business") or d.get("name") or ""
    except (OSError, ValueError):
        return ""


def version():
    try:
        return (WORK / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def kb_summary():
    rows = []
    for p in sorted(kb.ROOT.rglob("*.md")):
        d = kb.front(p)
        if "status" not in d:
            continue
        lv = date_of(d.get("last_verified", ""))
        age = (today() - lv).days if lv else None
        limit = int(d.get("review_every_days", 90) or 90)
        state = "needs seed" if d["status"] == "needs-seed" else "stale" if age is None or age > limit else "ok"
        rows.append({"file": p.relative_to(kb.ROOT).as_posix(), "state": state, "last_verified": d.get("last_verified", ""), "age": age})
    counts = {s: sum(1 for r in rows if r["state"] == s) for s in ("ok", "stale", "needs seed")}
    return {"total": len(rows), "counts": counts, "attention": [r for r in rows if r["state"] != "ok"]}


def scan():
    alerts, _ = al.scan_cases(today())
    for a in alerts:
        a["level"] = al.RANK_NAME.get(a["rank"], "")
    alerts.sort(key=lambda a: (a["rank"], a["left"] if a["left"] != "" else 9999, a["case"]))
    return alerts


def case_row(folder, alerts):
    info = cs.read_case(folder)
    open_rows = [r for r in cs.read_deadlines(folder) if r.get("status", "").lower() != "done"]
    dues = sorted((d, r) for r in open_rows for d in [date_of(r.get("due", ""))] if d)
    mine = [a for a in alerts if a["case"] == folder.name]
    nxt = dues[0] if dues else None
    return {
        "folder": folder.name, "id": info.get("case_id", folder.name[:8]), "client": info.get("client", ""),
        "program": info.get("program", ""), "province": info.get("province", ""), "opened": info.get("opened", ""),
        "next_action": info.get("next_action", ""),
        "next_deadline": {"due": nxt[0].isoformat(), "left": (nxt[0] - today()).days, "what": f"{nxt[1].get('type', '')}: {nxt[1].get('description', '')}"} if nxt else None,
        "urgent": sum(1 for a in mine if a["rank"] == al.URGENT), "soon": sum(1 for a in mine if a["rank"] == al.SOON),
    }


def home():
    alerts = scan()
    folders = cs.folders(cs.ACTIVE)
    week = [a for a in alerts if a["kind"] == "Deadline" and a["left"] != "" and 0 <= a["left"] <= 7]
    policy = al.last_policy_check()
    return {
        "firm": firm_name(), "version": version(), "today": today().isoformat(),
        "counts": {"cases": len(folders), "urgent": sum(1 for a in alerts if a["rank"] == al.URGENT),
                   "soon": sum(1 for a in alerts if a["rank"] == al.SOON), "week": len(week),
                   "housekeeping": sum(1 for a in alerts if a["rank"] == al.HOUSEKEEPING)},
        "alerts": alerts, "kb": kb_summary(),
        "policy_check": {"date": policy.isoformat() if policy else "", "age": (today() - policy).days if policy else None, "stale_after": al.TRACKER_STALE_DAYS},
        "commands": [{"label": l, "command": c, "help": h} for l, c, h in GENERAL_COMMANDS],
    }


def cases():
    alerts = scan()
    rows = []
    for folder in cs.folders(cs.ACTIVE):
        try:
            rows.append(case_row(folder, alerts))
        except (OSError, ValueError) as e:
            rows.append({"folder": folder.name, "id": folder.name[:8], "client": "", "error": f"Could not read this file ({type(e).__name__})"})
    closed = [{"folder": f.name, **{k: cs.read_case(f).get(k, "") for k in ("case_id", "client", "program", "closed", "destroy_after")}} for f in cs.folders(cs.CLOSED)]
    return {"active": rows, "closed": closed}


def files_of(folder):
    out = []
    for p in sorted(folder.rglob("*")):
        r = p.relative_to(folder).as_posix()
        if p.is_file() and not HIDDEN.search(r):
            st = p.stat()
            out.append({"path": rel(p), "name": p.name, "group": r.split("/")[0] if "/" in r else "", "size": st.st_size,
                        "modified": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes")})
    return out


def log_entries(folder, n=20):
    p = folder / "log.md"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (\d{4}-\d{2}-\d{2}) \| (.*) \|\s*$", line)
        if m:
            rows.append({"date": m.group(1), "text": m.group(2)})
    return rows[-n:][::-1]


def find_case(name):
    for base in (cs.ACTIVE, cs.CLOSED):
        for f in cs.folders(base):
            if f.name == name:
                return f
    return None


def case_detail(name):
    folder = find_case(name)
    if not folder:
        return None
    alerts = [a for a in scan() if a["case"] == folder.name]
    info = cs.read_case(folder)
    deadlines = []
    for i, r in enumerate(cs.read_deadlines(folder), 1):
        d = date_of(r.get("due", ""))
        deadlines.append({**r, "row": i, "left": (d - today()).days if d else None, "done": r.get("status", "").lower() == "done"})
    try:
        s = bl.summary(bl.load(folder))
        money = {"held": str(s["held"]), "received": str(s["received"]), "invoiced": str(s["invoiced"]), "owing": str(s["owing"]), "has_ledger": bl.ledger_path(folder).exists()}
    except Exception as e:  # a damaged ledger must not hide the rest of the file
        money = {"error": f"Could not read the billing ledger ({type(e).__name__})"}
    cid = info.get("case_id", folder.name[:8])
    return {
        "folder": folder.name, "path": rel(folder), "closed": folder.parent == cs.CLOSED, "info": info,
        "alerts": alerts, "deadlines": deadlines, "log": log_entries(folder), "updates": up.load(folder)[-10:][::-1],
        "money": money, "files": files_of(folder),
        "commands": [{"label": l, "command": c.format(id=cid), "help": h} for l, c, h in CASE_COMMANDS],
    }


def documents():
    rows = []
    if OUTPUT.exists():
        for p in OUTPUT.rglob("*"):
            r = p.relative_to(OUTPUT).as_posix()
            if p.is_file() and not HIDDEN.search(r) and p.name != "README.md":
                st = p.stat()
                rows.append({"path": rel(p), "name": p.name, "group": r.split("/")[0] if "/" in r else "general", "size": st.st_size,
                             "modified": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes")})
    rows.sort(key=lambda r: r["modified"], reverse=True)
    return {"folder": rel(OUTPUT) if OUTPUT.exists() else "", "files": rows}


def agent():
    notes = ""
    p = WORK / "WHATS-NEW.md"
    if p.exists():
        notes = p.read_text(encoding="utf-8")
    state = {}
    s = WORK / ".immigration-agent" / "workspace.json"
    if s.exists():
        try:
            d = json.loads(s.read_text(encoding="utf-8"))
            state = {"installed": d.get("version"), "updated": d.get("updated", "")}
        except ValueError:
            pass
    return {"version": version(), "folder": str(WORK), "whats_new": notes, "kb": kb_summary(), "install": state}


def open_path(relpath):
    """Open a file or folder (absolute path, as the API gives it) in its usual program. Returns an error text or None."""
    if not isinstance(relpath, str) or not relpath or "\x00" in relpath:
        return "No file given"
    target = pathlib.Path(relpath).resolve()
    if not target.is_absolute() or not any(target == r or r in target.parents for r in roots()):
        return "Only files in the agent folder or the case files can be opened"
    if not target.exists():
        return "That file no longer exists"
    if os.environ.get("DASHBOARD_NO_OPEN"):
        return None
    try:
        if sys.platform == "win32":
            os.startfile(str(target))  # noqa: S606 - the file's usual program, chosen by Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except OSError as e:
        return f"Could not open it ({e.strerror or e})"
    return None


TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}
ROUTES = {"/api/home": home, "/api/cases": cases, "/api/documents": documents, "/api/agent": agent}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "AgentDashboard"
    sys_version = ""

    def log_message(self, *args):
        pass  # nothing about clients is written to the console

    def allowed_host(self):
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def authorised(self):
        cookie = self.headers.get("Cookie", "")
        m = re.search(r"(?:^|;\s*)agent_key=([A-Za-z0-9_-]+)", cookie)
        return bool(m) and secrets.compare_digest(m.group(1), self.server.key)

    def send(self, code, body, kind="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8") if kind.startswith("application/json") else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.allowed_host():
            return self.send(403, {"error": "forbidden"})
        url = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(url.query)
        if url.path == "/ping":
            return self.send(200, {"ok": True, "app": "immigration-agent-dashboard"})
        if url.path == "/" and q.get("key", [""])[0]:
            if not secrets.compare_digest(q["key"][0], self.server.key):
                return self.send(403, "This dashboard link has expired. Open the dashboard again from its shortcut.", "text/plain; charset=utf-8")
            return self.send(303, b"", "text/plain", {"Location": "/", "Set-Cookie": f"agent_key={self.server.key}; HttpOnly; SameSite=Strict; Path=/"})
        if not self.authorised():
            return self.send(403, "Open the dashboard from its shortcut (or run app/dashboard.py).", "text/plain; charset=utf-8")
        if url.path in ("/", "/index.html"):
            return self.static("index.html")
        if url.path.startswith("/static/"):
            return self.static(url.path[len("/static/"):])
        try:
            if url.path in ROUTES:
                return self.send(200, ROUTES[url.path]())
            if url.path == "/api/case":
                d = case_detail(q.get("folder", [""])[0])
                return self.send(200, d) if d else self.send(404, {"error": "No such case"})
        except Exception as e:  # show the problem on the page instead of a blank screen
            return self.send(500, {"error": f"Something went wrong reading the files ({type(e).__name__}: {e})"})
        return self.send(404, {"error": "Not found"})

    def do_POST(self):
        if not self.allowed_host() or not self.authorised() or self.headers.get("X-Agent-Key") != self.server.key:
            return self.send(403, {"error": "forbidden"})
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/alive":
            self.server.last_seen = time.monotonic()
            return self.send(200, {"ok": True})
        if path != "/api/open":
            return self.send(404, {"error": "Not found"})
        try:
            n = min(int(self.headers.get("Content-Length", "0")), 10000)
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.send(400, {"error": "Bad request"})
        err = open_path(body.get("path"))
        return self.send(400 if err else 200, {"error": err} if err else {"ok": True})

    def static(self, name):
        p = (STATIC / name).resolve()
        if STATIC not in p.parents or not p.is_file():
            return self.send(404, {"error": "Not found"})
        kind = TYPES.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        body = p.read_bytes()
        if name == "index.html":
            body = body.replace(b"__AGENT_KEY__", self.server.key.encode())
        return self.send(200, body, kind)


def running():
    """The dashboard already running for this folder, as its URL, or None."""
    try:
        d = json.loads(STATE.read_text(encoding="utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{d['port']}/ping", timeout=2) as r:
            if json.loads(r.read()).get("app") == "immigration-agent-dashboard":
                return f"http://127.0.0.1:{d['port']}/?key={d['key']}"
    except (OSError, ValueError, KeyError):
        pass
    return None


def make_server(port=0):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.key = secrets.token_urlsafe(24)
    srv.daemon_threads = True
    srv.started = time.monotonic()
    srv.last_seen = None
    return srv


def watch_idle(srv, idle=None, first=None, step=5):
    """Stop the server once no dashboard window has checked in for a while. Runs in its own thread."""
    idle = IDLE_STOP if idle is None else idle
    first = FIRST_VISIT if first is None else first
    while True:
        time.sleep(step)
        now = time.monotonic()
        quiet = now - srv.started > first if srv.last_seen is None else now - srv.last_seen > idle
        if quiet:
            srv.shutdown()
            return


def app_browser():
    """A browser that can show a page as its own app window: [executable] or None."""
    if sys.platform == "win32":
        bases = [os.environ.get(k, "") for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
        for sub in (("Microsoft", "Edge", "Application", "msedge.exe"), ("Google", "Chrome", "Application", "chrome.exe")):
            for base in bases:
                if base and pathlib.Path(base, *sub).exists():
                    return [str(pathlib.Path(base, *sub))]
    elif sys.platform == "darwin":
        for app in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"):
            if pathlib.Path(app).exists():
                return [app]
    return None


def show(url):
    """Open the dashboard in its own app window, or in the normal browser when that is not possible."""
    exe = app_browser()
    if exe:
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
            subprocess.Popen(exe + [f"--app={url}", "--window-size=1280,860"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
            return
        except OSError:
            pass
    webbrowser.open(url)


def save_state(port, key):
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"port": port, "key": key, "pid": os.getpid()}), encoding="utf-8")
    os.replace(tmp, STATE)
    try:
        os.chmod(STATE, 0o600)
    except OSError:
        pass


def free_port(preferred=8765):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            return 0


def quiet_python():
    """pythonw.exe (Python without a console window) next to the running Python, or on PATH; None if missing."""
    p = pathlib.Path(sys.executable).with_name("pythonw.exe")
    if p.exists():
        return str(p)
    import shutil
    return shutil.which("pythonw")


def shortcut():
    if sys.platform != "win32":
        print("Shortcuts are made on Windows only. On a Mac, drag 'Dashboard.command' to the Dock.")
        return 1
    pythonw = quiet_python()
    target, args = (pythonw, f'"{APP / "dashboard.py"}"') if pythonw else (str(WORK / "Dashboard.bat"), "")
    icon = APP / "static" / "icon.ico"
    script = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\Immigration Agent Dashboard.lnk');"
              "$s.TargetPath=$env:T;$s.Arguments=$env:A;$s.WorkingDirectory=$env:W;$s.IconLocation=$env:I;$s.WindowStyle=7;"
              "$s.Description='Deadlines, alerts and cases';$s.Save()")
    env = {**os.environ, "T": target, "A": args, "W": str(WORK), "I": str(icon) if icon.exists() else target}
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env=env, capture_output=True, text=True, timeout=60)
    print("Desktop shortcut created: Immigration Agent Dashboard" if r.returncode == 0 else "Could not create the shortcut: " + (r.stderr or r.stdout).strip())
    return r.returncode


def main():
    if sys.stdout is None:  # started without a console (pythonw)
        sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Office dashboard for the Immigration Agent")
    p.add_argument("--shortcut", action="store_true", help="create a desktop shortcut (Windows)")
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args()
    if a.shortcut:
        return shortcut()
    url = running()
    if url:
        print("The dashboard is already running. Opening its window.")
        if not a.no_browser:
            show(url)
        return 0
    srv = make_server(free_port())
    port = srv.server_address[1]
    save_state(port, srv.key)
    url = f"http://127.0.0.1:{port}/?key={srv.key}"
    print("Immigration Agent dashboard is running on this computer only.")
    print("It stops by itself a few minutes after you close the dashboard window.")
    threading.Thread(target=watch_idle, args=(srv,), daemon=True).start()
    if not a.no_browser:
        threading.Timer(0.5, show, [url]).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            STATE.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # without a console nobody would see it: keep a note (no client data) for support
        import traceback
        try:
            cs.ROOT.mkdir(parents=True, exist_ok=True)
            with open(ERROR_LOG, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.datetime.now().isoformat(timespec='seconds')}\n{traceback.format_exc()}\n")
        except OSError:
            pass
        raise
