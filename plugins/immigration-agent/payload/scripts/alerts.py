#!/usr/bin/env python3
"""Daily alerts matched to open case files. Runs on this computer only.

Usage:
  python3 scripts/alerts.py run [--notify] [--force] [--out DIR]
  python3 scripts/alerts.py status
  python3 scripts/alerts.py install [--time 08:00]
  python3 scripts/alerts.py uninstall

Guarantees:
  - Nothing is sent anywhere, and no case file is changed. Once a week it reads IRCC's public form pages and fee list
    (scripts/watch.py; --offline skips it). When a backup folder is set (backup.py setup), it makes the backup that's due.
  - Pop-up notices and printed output show counts only, never client details.
  - One unreadable case file becomes an alert. It doesn't stop the others.
  - A failed run shows a notice, so alerts can't stop silently.
  - Rule-change matches are prompts to review, not findings that a file is affected.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import billing as bl  # noqa: E402
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402
import updates as up  # noqa: E402
import backup as bk  # noqa: E402
import watch as wt  # noqa: E402

REPO = de.REPO
TASK_NAME = "Canada Immigration Agent Alerts"
CHANGELOG = REPO / "knowledge" / "00-meta" / "changelog.md"
TRACKER = REPO / "knowledge" / "14-policy-tracker"
STATE = cs.ROOT / ".alerts-state.json"
ERROR_LOG = cs.ROOT / ".alerts-error.log"
BASELINE = "baseline"
URGENT, SOON, HOUSEKEEPING = 1, 2, 3
RANK_NAME = {URGENT: "Urgent", SOON: "Soon", HOUSEKEEPING: "Housekeeping"}
EXPIRY_WARN = {"passport": 180, "study_permit": 120, "work_permit": 120, "visitor_record": 120}
DEFAULT_WARN = 90
QUIET_DAYS = 60
NEW_CHANGE_DAYS = 14
RECENT_DAYS, COMING_DAYS = 14, 90
TRACKER_STALE_DAYS = 14
PR = r"PR fee|RPRF|levels plan"
TOPICS = {
    "family": rf"spous|sponsor|partner|common-law|dependent child|{PR}",
    "pgp": r"parent|grandparent|\bPGP\b|super visa",
    "ee": rf"express entry|\bCRS\b|\bEE\b|\bITA\b|\bFSW\b|\bCEC\b|{PR}",
    "pnp": rf"\bPNP\b|nominee|AAIP|SINP|NSNP|OINP|MPNP|{PR}",
    "quebec": r"quebec|\bPEQ\b|PSTQ|\bCSQ\b|\bCAQ\b",
    "study": r"study|student|PGWP|\bPAL\b|\bTAL\b|\bDLI\b|co-op",
    "work": r"work permit|LMIA|\bOWPs?\b|BOWP|\bTFW|temporary foreign|\bIEC\b",
    "visitor": r"visitor|\bTRV\b|\beTA\b|super visa|visa application cent",
    "protection": rf"asylum|refugee|PRRA|C-12|H&C|humanitarian|special measures|groups of five|{PR}",
    "citizenship": r"citizen|C-3",
    "prstatus": r"PR card|PRTD|residency obligation",
    "inadmissibility": r"inadmiss|criminal|rehab|\bTRP\b|misrep|medical|excessive demand",
    "business": rf"start-up|\bSUV\b|self-employed|entrepreneur|{PR}",
    "caregiver": rf"home care|caregiver|{PR}",
}
PROGRAMS = [
    (r"spous|partner|family|sponsor|dependent|child|conjugal", ["family"]),
    (r"pgp|parent|grandparent", ["pgp"]),
    (r"super", ["pgp", "visitor"]),
    (r"express|\bee\b|crs|fsw|cec|\bfst\b|skilled", ["ee"]),
    (r"pnp|nominee|aaip|oinp|sinp|nsnp|mpnp", ["pnp"]),
    (r"quebec|pstq|\bpeq\b|\bcsq\b|\bcaq\b", ["quebec"]),
    (r"stud|pgwp|\bsds\b", ["study"]),
    (r"work|lmia|\bowp\b|bowp|\bict\b|\biec\b|\bgts\b|cusma", ["work"]),
    (r"visit|\btrv\b|\beta\b", ["visitor"]),
    (r"refug|asylum|prra|protect|\bh-?c\b|h&c|humanitarian", ["protection"]),
    (r"citizen|c-3", ["citizenship"]),
    (r"pr-?card|prtd|residency", ["prstatus"]),
    (r"inadmiss|crimin|misrep|\btrp\b|rehab|medical", ["inadmissibility"]),
    (r"start-?up|\bsuv\b|self-?employ|entrepreneur|business", ["business"]),
    (r"caregiver|home-?care", ["caregiver"]),
]
PROVINCES = {
    "AB": r"alberta|\bAB\b|AAIP", "BC": r"british columbia|\bBC\b", "MB": r"manitoba|\bMB\b|MPNP", "NB": r"new brunswick|\bNB\b",
    "NL": r"newfoundland|\bNL\b", "NS": r"nova scotia|\bNS\b|NSNP", "NT": r"northwest territories|\bNWT\b", "NU": r"nunavut",
    "ON": r"ontario|\bON\b|OINP", "PE": r"prince edward|\bPEI\b", "QC": r"quebec|\bQC\b|PSTQ|\bPEQ\b", "SK": r"saskatchewan|\bSK\b|SINP", "YT": r"yukon",
}


def alert(rank, case, kind, tier, text, step, day=None, today=None):
    return {"rank": rank, "case": case, "kind": kind, "tier": tier, "text": text, "step": step, "day": day.isoformat() if day else "", "left": (day - today).days if day else ""}


def date_of(text):
    try:
        return datetime.date.fromisoformat(str(text).strip())
    except ValueError:
        return None


def deadline_alerts(name, rows, today):
    out = []
    for r in rows:
        if r.get("status", "").lower() == "done":
            continue
        due, what = date_of(r.get("due", "")), f"{r.get('type', '')}: {r.get('description', '')}"
        if not due:
            out.append(alert(URGENT, name, "Deadline", "unreadable", f"{what} has an unreadable due date", "Correct the date in the file"))
            continue
        left = (due - today).days
        if left > 30:
            continue
        rank, tier = (URGENT, "overdue") if left < 0 else (URGENT, "7 days") if left <= 7 else (SOON, "30 days")
        step = "If already done, mark it done. If missed, act today" if left < 0 else "Confirm the date and plan the filing"
        if r.get("type", "").startswith("jr-"):
            step += ". Federal Court matter: refer to a lawyer"
        if due.weekday() >= 5:
            step += f". Falls on a {due.strftime('%A')}: file earlier"
        out.append(alert(rank, name, "Deadline", tier, what + (f" ({r['basis']})" if r.get("basis") else ""), step, due, today))
    return out


def expiry_alert(name, label, day, warn, source, today):
    left = (day - today).days
    if left > warn:
        return None
    rank, tier = (URGENT, "expired") if left < 0 else (URGENT, "30 days") if left <= 30 else (SOON, f"{warn} days")
    verb = "expired" if left < 0 else "expires"
    return alert(rank, name, "Expiry", tier, f"{label} {verb} ({source})", "Check whether it was renewed, and what status or application depends on it", day, today)


def document_alerts(name, folder, today):
    path = fp.latest_report(folder / "03-documents" / "_extraction")
    if not path:
        return []
    latest = {}
    for d in json.loads(path.read_text(encoding="utf-8")).get("documents", []):
        for f in d.get("fields", []):
            day = date_of(f.get("value")) if f.get("field") == "expiry_date" else None
            if not day or d.get("doc_type") == "imm_form":
                continue
            who = de.doc_name(d) or d.get("file", "")
            key = (who.upper(), d["doc_type"])
            if key not in latest or day > latest[key][0]:
                latest[key] = (day, who, d["doc_type"], d.get("file", ""))
    out = []
    for day, who, kind, file in latest.values():
        label = f"{de.PLAIN_TYPES.get(kind, kind)} of {who}"
        out.append(expiry_alert(name, label, day, EXPIRY_WARN.get(kind, DEFAULT_WARN), f"read from {file}: confirm against the original", today))
    return [a for a in out if a]


def file_alerts(name, folder, info, rows, today):
    out = []
    for key, label, warn in (("status_expiry", "Status in Canada", 120), ("passport_expiry", "Passport", 180)):
        value = info.get(key, "")
        if value:
            day = date_of(value)
            if not day:
                out.append(alert(URGENT, name, "Expiry", "unreadable", f"{label} has an unreadable date", "Correct the date in the file"))
            else:
                out.append(expiry_alert(name, label, day, warn, "from the case file", today))
    gaps = [label for key, label in cs.INTAKE_KEYS.items() if info.get(key, "no").lower() != "yes"]
    if gaps:
        out.append(alert(HOUSEKEEPING, name, "File setup", "gaps", "Missing: " + ", ".join(gaps), "Complete these, or record why not"))
    if not info.get("next_action"):
        out.append(alert(HOUSEKEEPING, name, "File setup", "next action", "No next action set", "Set the next step"))
    if not [r for r in rows if r.get("status", "").lower() != "done"]:
        out.append(alert(HOUSEKEEPING, name, "File setup", "no deadline", "No open deadline tracked", "Add one, or confirm none applies"))
    log = folder / "log.md"
    dates = re.findall(r"(?m)^\| (\d{4}-\d{2}-\d{2}) \|", log.read_text(encoding="utf-8")) if log.exists() else []
    last = max(filter(None, map(date_of, dates)), default=None)
    if last and (today - last).days > QUIET_DAYS:
        out.append(alert(HOUSEKEEPING, name, "Quiet file", "quiet", f"No file activity for {(today - last).days} days", "Check the matter and update the client", last, today))
    return [a for a in out if a]


def retention_alerts(today):
    out = []
    path = cs.CLOSED / "closed-files.csv"
    if path.exists():
        for r in fp.load_csv(path):
            day = date_of(r.get("destroy_after", ""))
            if day and day <= today:
                out.append(alert(HOUSEKEEPING, r.get("case_id", ""), "Retention", "ended", "Retention period ended", "Review manually. Nothing is deleted automatically", day, today))
    return out


def scan_cases(today):
    alerts, cases = [], []
    for folder in cs.folders(cs.ACTIVE):
        try:
            info, rows = cs.read_case(folder), cs.read_deadlines(folder)
            cases.append({"name": folder.name, "program": info.get("program", ""), "province": info.get("province", "")})
            alerts += deadline_alerts(folder.name, rows, today) + file_alerts(folder.name, folder, info, rows, today) + document_alerts(folder.name, folder, today)
            alerts += [alert(rank, folder.name, kind, tier, text, step, day, today) for rank, kind, tier, text, step, day in bl.issues(folder, today) + up.issues(folder, today)]
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
            alerts.append(alert(URGENT, folder.name, "Unreadable file", "error", f"Could not check this file ({type(e).__name__})", "Open the file and repair it. Its deadlines were not checked"))
    alerts += retention_alerts(today)
    try:
        recon = bl.reconcile_issue(today)
    except (OSError, ValueError, KeyError):
        recon = (URGENT, "error", "Could not check client account reconciliations", "Check the billing ledgers and reconciliation index", None)
    if recon:
        alerts.append(alert(recon[0], "All files", "Client account", *recon[1:], today=today))
    return alerts, cases


def parse_changes(text):
    out = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) >= 3 and line.lstrip().startswith("|") and not set(parts[0]) <= set("-:") and parts[0] != "Effective":
            out.append({"effective": parts[0], "change": " | ".join(parts[1:-1]), "conf": parts[-1], "id": hashlib.sha256((parts[0] + parts[1]).encode("utf-8")).hexdigest()[:16]})
    return out


def topics_for(program):
    found = set()
    for pattern, names in PROGRAMS:
        if re.search(pattern, program, re.I):
            found.update(names)
    return found


def province_code(text):
    return next((code for code, pat in PROVINCES.items() if re.search(pat, text or "", re.I)), None)


def matches(change, case):
    named = {code for code, pat in PROVINCES.items() if re.search(pat, change)}
    home = province_code(case["province"])
    if named and home and home not in named:
        return False
    return any(re.search(TOPICS[t], change, re.I) for t in topics_for(case["program"]))


def recent_changes(changes, seen, cases, today):
    out = []
    for c in changes:
        first = seen.get(c["id"])
        is_new = bool(first and first != BASELINE and date_of(first) and (today - date_of(first)).days <= NEW_CHANGE_DAYS)
        eff = date_of(c["effective"])
        near = bool(eff and -RECENT_DAYS <= (eff - today).days <= COMING_DAYS)
        if is_new or near:
            out.append({**c, "is_new": is_new, "coming": bool(eff and eff > today), "files": [k["name"] for k in cases if matches(c["change"], k)]})
    return out


def last_policy_check():
    days = []
    for p in TRACKER.glob("*.md"):
        m = re.search(r"(?m)^last_verified:\s*(\d{4}-\d{2}-\d{2})", p.read_text(encoding="utf-8"))
        if m and date_of(m.group(1)):
            days.append(date_of(m.group(1)))
    return max(days, default=None)


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(cs.ROOT), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f)
    de.replace_with_retry(tmp, STATE)


def next_path(folder, today):
    n = 1
    while True:
        p = folder / f"{today.isoformat()}-alerts{'' if n == 1 else f'-v{n}'}.xlsx"
        if not p.exists():
            return p
        n += 1


def write_digest(path, alerts, changes, checked, today):
    import openpyxl
    book = openpyxl.Workbook()
    book.remove(book.active)
    counts = {r: sum(a["rank"] == r for a in alerts) for r in RANK_NAME}
    stale = not checked or (today - checked).days > TRACKER_STALE_DAYS
    intro = [[f"Alerts for {today.isoformat()}"],
             [f"Urgent: {counts[URGENT]} | Soon: {counts[SOON]} | Housekeeping: {counts[HOUSEKEEPING]} | Rule changes to review: {len(changes)}"],
             ["Rule changes last checked: " + (checked.isoformat() if checked else "unknown") + (". Overdue: run /changelog" if stale else "")],
             ["Alerts only cover dates recorded in the case files and documents. No alert doesn't mean no deadline."],
             ["Dates read from documents are drafts. Confirm them against the original."],
             ["Rule change matches use keywords. Each is a prompt to review, not a finding that the file is affected."]]
    de.add_sheet(book, "Read me first", ["About these alerts"], intro, [120])
    ordered = sorted(alerts, key=lambda a: (a["rank"], a["left"] if a["left"] != "" else 99999))
    de.add_sheet(book, "Action needed", ["Priority", "Case file", "Type", "What", "Date", "Days left", "Next step"],
                 [[RANK_NAME[a["rank"]], a["case"], a["kind"], a["text"], a["day"], a["left"], a["step"]] for a in ordered] or [["", "", "", "Nothing needs action", "", "", ""]],
                 [13, 34, 16, 60, 12, 10, 52])
    de.add_sheet(book, "Rule changes", ["Effective", "Change", "Confidence", "Status", "Open files to review"],
                 [[c["effective"], c["change"], c["conf"], "Newly added" if c["is_new"] else "Coming" if c["coming"] else "Recent", "; ".join(c["files"]) or "None matched"] for c in changes] or [["", "No recent rule changes", "", "", ""]],
                 [14, 80, 11, 13, 50])
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp.xlsx")
    os.close(fd)
    try:
        book.save(tmp)
        de.replace_with_retry(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def notify(message):
    """Show a Windows notice. The message must never hold client details."""
    if os.name != "nt":
        return
    script = ("Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
              "$n=New-Object System.Windows.Forms.NotifyIcon; $n.Icon=[System.Drawing.SystemIcons]::Information; $n.Visible=$true; "
              "$n.ShowBalloonTip(15000,'Immigration alerts',$env:ALERT_MESSAGE,[System.Windows.Forms.ToolTipIcon]::Info); Start-Sleep -Seconds 16; $n.Dispose()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env={**os.environ, "ALERT_MESSAGE": message}, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        pass


def watch_alerts(today, offline=False):
    """IRCC form versions and fees, re-read once a week (public pages only), then reported from the saved result."""
    out = []
    if not offline and wt.stale(today):
        try:
            wt.check()
        except Exception as e:  # a failed check must show, not pass as "no change"
            out.append(alert(SOON, "All files", "Form version", "not checked", f"IRCC form and fee check failed ({type(e).__name__})", "Run /watch"))
    for kind, text, step in wt.findings():
        rank = HOUSEKEEPING if "couldn't be checked" in text or "republished" in text else SOON
        out.append(alert(rank, "All files", kind, "IRCC", text, step))
    return out


def backup_alerts(today, make=True):
    """A due backup is made when a backup folder is set (make=False only reports, as the dashboard does)."""
    out, made = [], None
    try:
        made = bk.auto(today) if make else None
    except Exception as e:
        made = f"backup failed ({type(e).__name__}: {str(e)[:120]})"
    if made and not made.startswith("backup made"):
        out.append(alert(SOON, "All files", "Backup", "failed", made[0].upper() + made[1:], "Run backup.py status, then backup.py create"))
    is_due, days = bk.due(today)
    if is_due and not made:
        text = "No backup of your case files yet" if days is None else f"Last backup was {days} days ago"
        out.append(alert(SOON if days is None or days > 30 else HOUSEKEEPING, "All files", "Backup", "due", text,
                         "Run backup.py create, or backup.py setup --to <external drive folder> so the daily alerts make one each week"))
    return out


def cmd_run(a):
    today = datetime.date.today()
    state = load_state()
    alerts, cases = scan_cases(today)
    changes = parse_changes(CHANGELOG.read_text(encoding="utf-8")) if CHANGELOG.exists() else []
    first_run = "seen" not in state
    seen = state.get("seen", {})
    for c in changes:
        seen.setdefault(c["id"], BASELINE if first_run else today.isoformat())
    recent = recent_changes(changes, seen, cases, today) if cases else []
    checked = last_policy_check()
    for k in cases:
        if not topics_for(k["program"]):
            alerts.append(alert(HOUSEKEEPING, k["name"], "File setup", "program", f"Program \"{k['program']}\" not recognized, so rule changes can't be matched", "Use a clearer program name, and review rule changes manually"))
    if cases and (not checked or (today - checked).days > TRACKER_STALE_DAYS):
        alerts.append(alert(SOON, "All files", "Rule changes", "not checked", "Rule changes haven't been checked recently" + (f" (last {checked.isoformat()})" if checked else ""), "Run /changelog"))
    if cases:
        alerts += watch_alerts(today, offline=a.offline) + backup_alerts(today)
    relevant = [c for c in recent if c["files"]]
    fingerprint = sorted([f"{x['case']}|{x['kind']}|{x['text']}|{x['tier']}" for x in alerts] + [f"rule|{c['id']}|{','.join(sorted(c['files']))}" for c in relevant])
    urgent, soon = sum(x["rank"] == URGENT for x in alerts), sum(x["rank"] == SOON for x in alerts)
    path = None
    if cases and (a.force or fingerprint != state.get("fingerprint")):
        out = pathlib.Path(a.out) if a.out else REPO / "Output" / "general"
        de.guard_output(out)
        out.mkdir(parents=True, exist_ok=True)
        path = next_path(out, today)
        write_digest(path, alerts, recent, checked, today)
        state["last_digest"] = path.name
    state.update(seen=seen, fingerprint=fingerprint, last_run=datetime.datetime.now().isoformat(timespec="seconds"))
    save_state(state)
    print(f"Open files: {len(cases)} | urgent: {urgent} | soon: {soon} | housekeeping: {len(alerts) - urgent - soon} | rule changes to review: {len(relevant)}")
    print("Alerts file:", path if path else "no change since the last one")
    if a.notify and (urgent or path):
        notify(f"{urgent} urgent, {soon} soon, {len(relevant)} rule changes to review. See the latest alerts file in Output\\general.")


def powershell(script, **env):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env={**os.environ, **env}, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)


def cmd_install(a):
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", a.time):
        sys.exit("ERROR: use a 24-hour time such as 08:00")
    exe = pathlib.Path(sys.executable).with_name("pythonw.exe")
    if not exe.exists():
        sys.exit(f"ERROR: not found: {exe}")
    script = ("$a=New-ScheduledTaskAction -Execute $env:AL_EXE -Argument $env:AL_ARG -WorkingDirectory $env:AL_DIR; "
              "$t=New-ScheduledTaskTrigger -Daily -At $env:AL_TIME; "
              "$s=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10); "
              "Register-ScheduledTask -TaskName $env:AL_NAME -Action $a -Trigger $t -Settings $s -Force | Out-Null")
    r = powershell(script, AL_EXE=str(exe), AL_ARG=f'"{pathlib.Path(__file__).resolve()}" run --notify', AL_DIR=str(REPO), AL_TIME=a.time, AL_NAME=TASK_NAME)
    if r.returncode:
        sys.exit("ERROR: could not create the scheduled task: " + r.stderr.strip()[:300])
    print(f"Scheduled daily at {a.time}. If the computer is off then, it runs at the next start.")


def cmd_uninstall(_):
    r = powershell("Unregister-ScheduledTask -TaskName $env:AL_NAME -Confirm:$false", AL_NAME=TASK_NAME)
    if r.returncode:
        sys.exit("ERROR: no scheduled task was removed")
    print("Scheduled alerts removed.")


def cmd_status(_):
    state = load_state()
    print("Last run:", state.get("last_run", "never"))
    print("Last alerts file:", state.get("last_digest", "none"))
    r = powershell("$i=Get-ScheduledTaskInfo -TaskName $env:AL_NAME; \"$($i.LastRunTime) | result $($i.LastTaskResult) | next $($i.NextRunTime)\"", AL_NAME=TASK_NAME)
    print("Scheduled task:", r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "not installed")
    if ERROR_LOG.exists():
        print("Last failure:", time.strftime("%Y-%m-%d %H:%M", time.localtime(ERROR_LOG.stat().st_mtime)))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Daily alerts for open case files")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("run"); x.add_argument("--notify", action="store_true"); x.add_argument("--force", action="store_true"); x.add_argument("--out")
    x.add_argument("--offline", action="store_true", default=os.environ.get("IMMIGRATION_AGENT_OFFLINE") == "1", help="don't read IRCC's form and fee pages"); x.set_defaults(fn=cmd_run)
    x = s.add_parser("status"); x.set_defaults(fn=cmd_status)
    x = s.add_parser("install"); x.add_argument("--time", default="08:00"); x.set_defaults(fn=cmd_install)
    x = s.add_parser("uninstall"); x.set_defaults(fn=cmd_uninstall)
    a = p.parse_args()
    try:
        a.fn(a)
    except Exception:
        if a.cmd != "run":
            raise
        try:
            cs.ROOT.mkdir(parents=True, exist_ok=True)
            ERROR_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        finally:
            if a.notify:
                notify("Today's alert check failed. Deadlines were not checked. Run alerts.py status.")
        raise


if __name__ == "__main__":
    main()
