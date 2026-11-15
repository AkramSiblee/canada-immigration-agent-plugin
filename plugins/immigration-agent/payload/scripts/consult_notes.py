#!/usr/bin/env python3
"""Consultation notes from a recording's transcript (or typed notes): risk scan, then a Word record in the file.

Usage:
  python3 scripts/consult_notes.py scan TRANSCRIPT                         risk words, money and dates mentioned (changes nothing)
  python3 scripts/consult_notes.py save --notes NOTES.json (--case CASE | --prospect ID) [--transcript FILE]

NOTES.json (Claude drafts it from the transcript; the consultant corrects it):
  {"meeting_date": "YYYY-MM-DD", "method": "video call", "attendees": "...", "source": "transcript of the recorded consultation" or "typed notes",
   "recording_consent": "yes" (required when the source is a recording), "goals": [...], "facts": [...], "advice": [...],
   "options": [...], "risks": [...], "documents_requested": [...], "next_steps": [...], "fees_discussed": "...",
   "follow_ups": [{"due": "YYYY-MM-DD", "what": "..."}]}

Guarantees:
  - A recorded consultation is filed only with "recording_consent": "yes": the client must have agreed to the recording.
  - The notes are saved as a Word file in the case's 04-advice (or with the prospect). Each advice line is also added to the
    "Advice given" table in case.md, and each dated follow-up becomes a deadline.
  - The transcript, if given, is copied into the case's 01-intake/transcripts. The original isn't moved or changed.
  - The risk scan is keyword-based. It flags words to look at (previous refusal, family not declared, criminal record, agent
    or "consultant" back home, false documents); it never decides anything.
  - Notes are a draft until the consultant has read them against the recording. Never use this for an IRB narrative or
    statement (CLAUDE.md rule 7).
"""
import argparse
import datetime
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

RISKS = [
    ("Previous refusal", r"\brefus(?:ed|al)\b|\brejected\b|\bdenied\b"),
    ("Overstay or status problem", r"overst(?:ay|ayed)|out of status|expired (?:permit|visa|status)|without status|deport|remov(?:ed|al) order"),
    ("Family not declared (IRPR 117(9)(d))", r"(?:didn'?t|did not|never|forgot to) (?:declare|list|mention|include)|not (?:declared|listed|included)|undeclared|hidden child|secret (?:marriage|child)"),
    ("Possible misrepresentation (IRPA s.40)", r"fake|false (?:document|letter|statement|information)|bought (?:a |the )?(?:letter|job offer|lmia)|paid for (?:a |the )?(?:job offer|lmia)|lied|not true|made up"),
    ("Ghost consultant or unlicensed agent", r"\bagent\b|consultant (?:back home|in india|in pakistan|in nigeria|in the philippines)|travel agent|someone else (?:filed|prepared|submitted)|my friend (?:filed|did)|unlicensed"),
    ("Criminality", r"arrest|charged|convict|criminal|\bDUI\b|\bDWI\b|impaired|police record|court case|jail|prison|probation"),
    ("Medical", r"tuberculosis|\bTB\b|dialysis|cancer|HIV|disab|chronic|hospitali[sz]ed|treatment"),
    ("Federal Court or IRB (lawyer or RCIC-IRB)", r"federal court|judicial review|appeal|\bIRB\b|\bIAD\b|\bRAD\b|\bRPD\b|hearing|removal|deportation"),
]


def die(msg):
    sys.exit("NOT SAVED: " + msg)


def read(path):
    ext = path.suffix.lower()
    try:
        if ext == ".docx":
            pages = de.read_docx(path)
        elif ext == ".pdf":
            pages = de.read_pdf(path, 200)[0]
        elif ext in (".txt", ".md", ".vtt", ".srt", ".text"):
            pages = de.read_text(path)
        else:
            die("use a transcript as text (.txt, .vtt, .srt), Word or PDF. Audio can't be read: export the transcript from Zoom, Teams, Otter or Word")
    except de.Skip as e:
        die(f"the transcript can't be read ({de.PLAIN_STATUS.get(e.status, e.status)})")
    text = "\n".join(t for _, t in pages)
    return re.sub(r"(?m)^\d{2}:\d{2}:\d{2}[.,]\d{3} --> .*$|^WEBVTT.*$|^\d+\s*$", "", text)  # drop subtitle timing lines


def scan(text):
    flat = re.sub(r"\s+", " ", text)
    found = []
    for label, rx in RISKS:
        hits = [flat[max(0, m.start() - 70):m.end() + 70].strip() for m in re.finditer(rx, flat, re.I)]
        if hits:
            found.append((label, hits[:3], len(hits)))
    money = sorted(set(re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?", flat)))[:12]
    dates = sorted(set(m.group(0) for m in re.finditer(de.DATE_RX, flat, re.I)))[:12]
    return found, money, dates


def cmd_scan(a):
    path = pathlib.Path(a.transcript)
    if not path.is_file():
        die(f"no such file: {path}")
    text = read(path)
    found, money, dates = scan(text)
    print(f"{path.name}: {len(text.split())} words")
    if not found:
        print("No risk words found. That doesn't mean there are no risks: read the transcript.")
    for label, hits, n in found:
        print(f"\n{label} ({n} mention{'s' if n > 1 else ''}):")
        for h in hits:
            print(f"  ...{h}...")
    if money:
        print("\nAmounts mentioned: " + ", ".join(money))
    if dates:
        print("Dates mentioned: " + ", ".join(dates))


def advice_rows(folder, day, advice, out_name):
    """Add each advice line to the 'Advice given' table in case.md."""
    path = folder / "case.md"
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(## Advice given\n(?:.*\n)*?\|---.*\n)((?:\|.*\n?)*)", text)
    if not m:
        return 0
    rows = [r for r in m.group(2).splitlines() if r.strip() and not re.fullmatch(r"\|(?:\s*\|)+", r.strip())]
    rows += [f"| {day} | {a.replace('|', '/')} | {out_name} | consultation notes |" for a in advice]
    path.write_text(text[:m.start(2)] + "\n".join(rows) + "\n" + text[m.end(2):], encoding="utf-8")
    return len(advice)


def cmd_save(a):
    import firm
    try:
        notes = json.loads(pathlib.Path(a.notes).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die(f"can't read the notes file ({type(e).__name__})")
    source = str(notes.get("source", "")).strip()
    if not source:
        die('say where the notes come from ("source": "transcript of the recorded consultation" or "typed notes")')
    recorded = bool(a.transcript) or re.search(r"record|transcri", source, re.I)
    if recorded and str(notes.get("recording_consent", "")).lower() != "yes":
        die('a recorded consultation needs the client\'s consent to the recording: add "recording_consent": "yes" once you have it')
    day = cs.parse_date(notes.get("meeting_date", ""), "meeting_date")
    if not notes.get("advice"):
        die("the notes have no advice given. Add it, or write [\"No advice given\"]")
    follow = []
    for f in notes.get("follow_ups") or []:
        follow.append((cs.parse_date(f.get("due", ""), "follow_ups due"), str(f.get("what", "")).strip() or "Follow-up from the consultation"))
    if a.case:
        folder = de.active_case(a.case)
        out = None
    else:
        import prospects as pr
        p = pr.get(a.prospect)
        folder, out = None, pr.NOTES / p["id"]
        notes.setdefault("client_name_override", p["name"])
    terms = {k: v for k, v in notes.items() if k not in ("follow_ups", "recording_consent")}
    if not folder:
        terms["client"] = {"name": notes.get("client_name_override", "")}
    path, _ = firm.draft("consultation-notes", folder, terms, out)
    print(f"Saved: {path}")
    if folder:
        n = advice_rows(folder, day.isoformat(), notes["advice"], path.name)
        print(f"Advice given: {n} line(s) added to case.md")
        if follow:
            rows = cs.read_deadlines(folder)
            rows += [{"due": d.isoformat(), "type": "custom", "description": w, "basis": f"consultation {day}", "status": "open"} for d, w in follow]
            cs.write_deadlines(folder, rows)
            print(f"Follow-ups: {len(follow)} deadline(s) added")
        if a.transcript:
            src = pathlib.Path(a.transcript)
            dest = folder / "01-intake" / "transcripts"
            dest.mkdir(parents=True, exist_ok=True)
            target = dest / f"{day.isoformat()}-consultation-transcript{src.suffix.lower()}"
            n = 1
            while target.exists():
                n += 1
                target = dest / f"{day.isoformat()}-consultation-transcript-v{n}{src.suffix.lower()}"
            shutil.copy2(src, target)
            print(f"Transcript filed: {target.name}")
        cs.add_log(folder, f"Consultation on {day}: notes filed ({path.name})", day if day <= datetime.date.today() else None)
    print("Read the notes against the recording before relying on them. The client can ask for a copy.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Consultation notes")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("scan"); x.add_argument("transcript"); x.set_defaults(fn=cmd_scan)
    x = s.add_parser("save"); x.add_argument("--notes", required=True); g = x.add_mutually_exclusive_group(required=True); g.add_argument("--case"); g.add_argument("--prospect")
    x.add_argument("--transcript"); x.set_defaults(fn=cmd_save)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
