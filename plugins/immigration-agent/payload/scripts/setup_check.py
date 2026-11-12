#!/usr/bin/env python3
"""Installation check: is this computer ready to run the agent?

  python3 scripts/setup_check.py            check and list what to fix
  python3 scripts/setup_check.py --install  also install the Python libraries and create the working folders

Required: Python 3.10+ reachable as "python3", the libraries in requirements.txt, Claude Code, and (on Windows) Git.
Recommended: Adobe Acrobat or Reader (to finish and sign IRCC forms), LibreOffice (Word/Excel to PDF), curl.
"""
import argparse
import importlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
LIBRARIES = {"pypdf": "pypdf", "pypdfium2": "pypdfium2", "reportlab": "reportlab", "openpyxl": "openpyxl", "docx": "python-docx", "PIL": "pillow"}
WINDOWS = platform.system() == "Windows"
results = []


def report(level, item, detail, fix=""):
    results.append((level, item, detail, fix))


def run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else ""
    except Exception:
        return ""


def check_python():
    v = sys.version_info
    if v < (3, 10):
        report("FIX", "Python", f"{v.major}.{v.minor} found; 3.10 or newer is needed", "Install Python 3.12 from python.org (or the Microsoft Store on Windows)")
    else:
        report("OK", "Python", f"{v.major}.{v.minor}.{v.micro}")
    py3 = shutil.which("python3")
    if not py3:
        report("FIX", "python3 command", "not found: the agent's commands and start-up check call 'python3'",
               "Windows: install Python from the Microsoft Store (it adds python3), or run: winget install Python.Python.3.12 and add a python3 alias")
    elif "WindowsApps" in py3 and not run([py3, "--version"]).startswith("Python"):
        report("FIX", "python3 command", "only the Microsoft Store shortcut is present, not Python itself", "Install Python from the Microsoft Store, then run this check again")
    else:
        report("OK", "python3 command", py3)


def check_libraries(install):
    missing = []
    for module, package in LIBRARIES.items():
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(package)
    if missing and install:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "-r", str(REPO / "requirements.txt")], check=False)
        importlib.invalidate_caches()
        missing = [p for m, p in LIBRARIES.items() if not _importable(m)]
    if missing:
        report("FIX", "Python libraries", "missing: " + ", ".join(missing), f'Run: "{sys.executable}" -m pip install --user -r requirements.txt')
    else:
        report("OK", "Python libraries", ", ".join(LIBRARIES.values()))


def _importable(module):
    try:
        importlib.import_module(module)
        return True
    except Exception:
        return False


def check_tools():
    claude = shutil.which("claude")
    if claude:
        report("OK", "Claude Code", run([claude, "--version"]) or claude)
    else:
        report("FIX", "Claude Code", "not found", "Install Claude Code (see claude.com/claude-code) and sign in with your own Claude account")
    git = shutil.which("git")
    if git:
        report("OK", "Git", run([git, "--version"]))
    elif WINDOWS:
        report("FIX", "Git for Windows", "not found: Claude Code on Windows needs it", "Install Git for Windows from git-scm.com")
    else:
        report("OPTIONAL", "Git", "not found", "Install git to receive updates more easily")
    if acrobat():
        report("OK", "Adobe Acrobat / Reader", acrobat())
    else:
        report("RECOMMENDED", "Adobe Acrobat / Reader", "not found", "Install Adobe Acrobat Reader (free) to finish, validate and sign IRCC forms")
    office = os.environ.get("SOFFICE") or shutil.which("soffice") or shutil.which("libreoffice") or libreoffice()
    if office:
        report("OK", "LibreOffice", office)
    else:
        report("OPTIONAL", "LibreOffice", "not found", "Install LibreOffice to convert Word, Excel and PowerPoint files to PDF")
    if shutil.which("curl"):
        report("OK", "curl", "for downloading blank IRCC forms")
    else:
        report("OPTIONAL", "curl", "not found; Python's downloader is used instead")


def acrobat():
    if WINDOWS:
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
            for rel in (r"Adobe\Acrobat DC\Acrobat\Acrobat.exe", r"Adobe\Acrobat Reader DC\Reader\AcroRd32.exe", r"Adobe\Acrobat Reader\Reader\AcroRd32.exe",
                        r"Adobe\Acrobat Reader DC\Acrobat\Acrobat.exe"):
                p = pathlib.Path(base) / rel
                if p.exists():
                    return str(p)
    elif platform.system() == "Darwin":
        for p in pathlib.Path("/Applications").glob("Adobe Acrobat*"):
            return str(p)
    return ""


def libreoffice():
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe", "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if pathlib.Path(p).exists():
            return p
    return ""


def check_folders(install):
    missing = [d for d in ("cases", "cases/active", "Input", "Output") if not (REPO / d).is_dir()]
    if missing and install:
        for d in missing:
            (REPO / d).mkdir(parents=True, exist_ok=True)
        missing = []
    if missing:
        report("FIX", "Working folders", "missing: " + ", ".join(missing), "Run this check with --install to create them")
    else:
        report("OK", "Working folders", "cases, Input, Output")
    sync = [s for s in ("OneDrive", "Dropbox", "Google Drive", "iCloud") if s.lower() in str(REPO).lower()]
    if sync:
        report("CHECK", "Cloud-synced folder", f"this folder is inside {sync[0]}: client files will sync to that service",
               "Make sure your cloud storage meets your privacy obligations (see knowledge/10-consultant-practice/ai-and-privacy.md)")


def check_firm():
    profile = REPO / "cases" / ".firm-profile.json"
    try:
        data = json.loads(profile.read_text(encoding="utf-8")) if profile.exists() else {}
    except Exception:
        data = {}
    if data.get("name") and data.get("rcic"):
        report("OK", "Firm profile", "set (letterhead, agreements and letters)")
    else:
        report("TO DO", "Firm profile", "not set yet",
               'Run: python3 scripts/firm.py setup --name "Your Name" --rcic R123456 --business "Firm" --address "..." --phone "..." --email "..."')


def check_scripts():
    bad = []
    for f in sorted((REPO / "scripts").glob("*.py")):
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")
        except Exception:
            bad.append(f.name)
    if bad:
        report("FIX", "Agent tools", "can't load: " + ", ".join(bad), "Download the release again; a file may be damaged")
    else:
        report("OK", "Agent tools", f"{len(list((REPO / 'scripts').glob('*.py')))} scripts load")
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "kb_status.py"), "--brief"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    line = (r.stdout or "").strip().splitlines()[-1] if (r.stdout or "").strip() else "no result"
    report("OK" if r.returncode == 0 else "CHECK", "Knowledge base", line, "" if "STALE 0" in line or r.returncode else "Run /update-kb on the stale files")


ORDER = {"FIX": 0, "TO DO": 1, "CHECK": 2, "RECOMMENDED": 3, "OPTIONAL": 4, "OK": 5}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Check that this computer is ready to run the agent")
    p.add_argument("--install", action="store_true", help="install missing Python libraries and create the working folders")
    a = p.parse_args()
    check_python()
    check_libraries(a.install)
    check_tools()
    check_folders(a.install)
    check_firm()
    check_scripts()
    print(f"Canada Immigration Agent {(REPO / 'VERSION').read_text().strip() if (REPO / 'VERSION').exists() else ''}: installation check")
    for level, item, detail, fix in sorted(results, key=lambda r: ORDER[r[0]]):
        print(f"  [{level}] {item}: {detail}")
        if fix and level != "OK":
            print(f"        -> {fix}")
    blocking = sum(1 for r in results if r[0] == "FIX")
    print("Ready to use." if not blocking else f"{blocking} item(s) to fix before the agent will work fully.")
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
