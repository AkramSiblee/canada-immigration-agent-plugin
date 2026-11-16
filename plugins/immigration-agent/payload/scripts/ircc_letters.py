#!/usr/bin/env python3
"""IRCC letter inbox: recognise an IRCC letter, find its case, file it, add its time limit and record it for the client update.

Usage:
  python3 scripts/ircc_letters.py read FILE                 what the letter is, its date, time limit and matching case (changes nothing)
  python3 scripts/ircc_letters.py scan [FOLDER]             read every letter in a folder (default Input/) and list them (changes nothing)
  python3 scripts/ircc_letters.py file FILE --case CASE [--type TYPE] [--date YYYY-MM-DD] [--due YYYY-MM-DD | --no-deadline] [--received YYYY-MM-DD]
  python3 scripts/ircc_letters.py types

Guarantees:
  - A letter is copied into the case's 06-correspondence folder. The original is never moved or changed (Input/ stays read-only).
  - A time limit is taken from the letter's own words ("within 30 days", "by December 1, 2026"). When the letter states none,
    a rule from deadline_rules.csv is used only where one exists for that letter type, and it is labelled as such.
    Otherwise no deadline is guessed: you are asked to give --due or --no-deadline.
  - Every letter filed is recorded in updates.csv as "received", so the daily alerts flag it until the client is told (Code s.22(3)).
  - Scanned letters (no text) are reported as such; give --type, --date and --due from the letter yourself.
  - Everything read from a letter is a draft. Check the date and the time limit against the letter before relying on them.
"""
import argparse
import csv
import datetime
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

REPO = de.REPO
READABLE = {".pdf", ".txt", ".eml", ".md", ".text", ".docx"}
WORDS = {"seven": 7, "ten": 10, "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30, "forty-five": 45, "forty five": 45, "sixty": 60, "ninety": 90}

# type: (patterns with weights, plain name, what the client is told they received, what the client must do, deadline rule if the letter states none)
TYPES = {
    "account-message": ([(r"new message (?:has been )?(?:posted|sent) to your (?:online |secure )?account|check your (?:online |secure |IRCC secure )?account|a message is available", 6)],
                        "IRCC account message notice", "a notice that IRCC posted a message to the online account",
                        "", None),
    "aor": ([(r"acknowledge?ment of receipt", 6), (r"we (?:have )?received your application", 4), (r"application (?:is|was) (?:complete|received)", 2)],
            "Acknowledgement of receipt", "the acknowledgement of receipt of your application", "", None),
    "biometrics": ([(r"biometric instruction letter|biometrics? collection letter", 7), (r"(?:give|provide|enrol) (?:your )?biometrics", 4), (r"\bbiometrics?\b", 2), (r"visa application cent|service canada", 1)],
                   "Biometric instruction letter", "the biometric instruction letter", "Give your biometrics (fingerprints and photo) at a collection point, and bring this letter", "pr-biometrics-30"),
    "medical": ([(r"medical (?:examination|exam) (?:request|instructions)|instructions? (?:for|to) (?:undergo|complete) (?:a |an |your )?(?:immigration )?medical", 6),
                 (r"\bIMM ?1017\b|panel physician", 4), (r"immigration medical exam", 3), (r"medical exam", 1)],
                "Medical exam request", "a request for an immigration medical exam", "Book and attend the medical exam with an IRCC panel physician", None),
    "procedural-fairness": ([(r"procedural fairness", 8), (r"opportunity to respond", 3), (r"concerns?\b", 1)],
                            "Procedural fairness letter", "a procedural fairness letter about concerns with your application",
                            "We will prepare a response with you. Please send us any information or documents about the concerns as soon as possible", None),
    "additional-documents": ([(r"additional (?:documents?|information)", 4), (r"(?:please )?(?:submit|provide|upload) the following", 3), (r"request for (?:documents|information)", 4), (r"we need more information", 4)],
                             "Request for documents", "a request for more documents or information",
                             "Send us the documents listed so we can upload them in time", None),
    "interview": ([(r"\binterview\b", 3), (r"(?:scheduled|convocation|you are (?:required|invited) to attend)", 3)],
                  "Interview notice", "an interview notice", "Attend the interview on the date given. We will help you prepare", None),
    "passport-request": ([(r"passport request|request for (?:your )?passport|submit your passport", 7), (r"\bPPR\b", 3), (r"visa (?:counterfoil|stamp)", 2)],
                         "Passport request", "a request for your passport", "Send your passport (and any other items listed) as instructed", None),
    "pr-confirmation": ([(r"confirmation of permanent residence|\bCOPR\b", 7), (r"permanent residence portal|confirm (?:your )?(?:permanent residence|presence in canada)", 4), (r"ready for visa", 3)],
                        "PR confirmation", "your confirmation of permanent residence or a request to confirm your PR", "Follow the steps in the letter to confirm your permanent residence", None),
    "approval": ([(r"(?:has|have) been approved|we are pleased to inform|approval (?:letter|in principle)|port of entry letter of introduction|letter of introduction", 5)],
                 "Approval", "a positive decision on your application", "", None),
    "refusal": ([(r"notice of appeal|use this form", -6), (r"\b(?:refus(?:ed|al|ing)|cannot be approved|has been refused)\b", 5), (r"not satisfied", 2), (r"does not meet the requirements", 2)],
                "Refusal", "a decision refusing your application", "We will review the reasons with you and explain your options", None),
    "ita": ([(r"invitation to apply", 7), (r"express entry", 2)],
            "Invitation to apply (Express Entry)", "an invitation to apply for permanent residence", "Send us the documents for the application as soon as possible", "ee-ita-60"),
}
NO_LIMIT = {"account-message", "aor", "approval", "refusal"}  # these letters set no time limit of their own
IRCC_RX = r"immigration,? refugees and citizenship|\bIRCC\b|citoyennet[ée] canada|\bIRCC-?CIC\b|\bCIC\b|government of canada|gouvernement du canada"
APP_RX = r"\b([BEFGHNSVWX]\d{9})\b"
UCI_RX = r"\b(\d{4}-?\d{4}(?:-?\d{2})?)\b"
WITHIN_RX = r"within\s+(\d{1,3}|" + "|".join(WORDS) + r")\s*(?:\(\d{1,3}\)\s*)?(calendar\s+|business\s+)?days?"
# "You have 30 days from the date of this letter", "30 calendar days after receipt of this letter"
FROM_RX = (r"(\d{1,3}|" + "|".join(WORDS) + r")\s*(?:\(\d{1,3}\)\s*)?(calendar\s+|business\s+)?days?\s+(?:from|of|after|following)\s+"
           r"(?:the\s+)?(date\s+(?:of|on)\s+(?:this|the)\s+(?:letter|request|notice|e-?mail|message)|this\s+(?:letter|request|notice)|"
           r"(?:the\s+)?(?:receipt|date\s+you\s+receive(?:d)?)(?:\s+of)?(?:\s+this\s+(?:letter|request|notice))?)")
BY_RX = rf"(?:by|no later than|on or before|before|deadline(?: is|:)?|due(?: date)?(?: is|:)?)\s+({de.DATE_RX})"


def die(msg):
    sys.exit("NOT FILED: " + msg)


def read_pages(path):
    """(pages, status). status is 'ok', 'scanned' or the reason it couldn't be read."""
    ext = path.suffix.lower()
    if ext not in READABLE:
        return [], "this file type can't be read (use PDF, Word, text or .eml)"
    try:
        if ext == ".pdf":
            pages, need, _, _, _ = de.read_pdf(path, 30)
            if len(need) == len(pages):
                return pages, "scanned"
            return pages, "ok"
        if ext == ".docx":
            return de.read_docx(path), "ok"
        return de.read_text(path), "ok"
    except de.Skip as e:
        return [], de.PLAIN_STATUS.get(e.status, e.status)


def classify(text):
    scores = {}
    for kind, (rules, *_rest) in TYPES.items():
        s = sum(w for rx, w in rules if re.search(rx, text, re.I))
        if s > 0:
            scores[kind] = s
    if not scores:
        return None, "L", scores
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top, best = ranked[0]
    margin = best - (ranked[1][1] if len(ranked) > 1 else 0)
    if best < 4:
        return None, "L", scores
    return top, "H" if best >= 6 and margin >= 3 else "M", scores


def iso(text):
    day, _ = de.parse_date(text)
    return datetime.date.fromisoformat(day) if day else None


def letter_date(text):
    m = re.search(rf"(?:^|\n)\s*(?:date(?: of (?:this )?letter)?|dated|date d'envoi)\s*:?\s*({de.DATE_RX})", text, re.I)
    if m and iso(m.group(1)):
        return iso(m.group(1)), "labelled date"
    for m in re.finditer(de.DATE_RX, text[:900], re.I):
        if iso(m.group(0)):
            return iso(m.group(0)), "first date in the letter"
    return None, ""


def around(flat, start, end):
    """The words around a match, cut at word boundaries."""
    a = flat.rfind(" ", 0, max(0, start - 60)) + 1 if start > 60 else 0
    b = flat.find(" ", end + 20)
    return flat[a:b if b != -1 else len(flat)].strip()


def time_limits(text, sent):
    """Every time limit the letter states: (due, quote, how). A 'within N days' limit is counted from the letter date."""
    flat = re.sub(r"\s+", " ", text)
    out = []
    for m in re.finditer(WITHIN_RX, flat, re.I):
        g = m.group(1).lower()
        n = int(g) if g.isdigit() else WORDS[g]
        if not 1 <= n <= 365:
            continue
        business = bool(m.group(2) and "business" in m.group(2).lower())
        quote = around(flat, m.start(), m.end())
        if sent and not business:
            out.append((sent + datetime.timedelta(days=n), quote, f"{n} days from the letter date {sent}"))
        else:
            out.append((None, quote, f"{n} {'business ' if business else ''}days: count them from the date the letter gives"))
    taken = [m.span() for m in re.finditer(WITHIN_RX, flat, re.I)]
    for m in re.finditer(FROM_RX, flat, re.I):
        if any(a <= m.start() < b or m.start() <= a < m.end() for a, b in taken):
            continue  # "within 30 days of the date of this letter": already counted above
        g = m.group(1).lower()
        n = int(g) if g.isdigit() else WORDS[g]
        if not 1 <= n <= 365:
            continue
        business = bool(m.group(2) and "business" in m.group(2).lower())
        from_receipt = "receiv" in m.group(3).lower() or "receipt" in m.group(3).lower()
        quote = around(flat, m.start(), m.end())
        if sent and not business and not from_receipt:
            out.append((sent + datetime.timedelta(days=n), quote, f"{n} days from the letter date {sent}"))
        else:
            out.append((None, quote, f"{n} {'business ' if business else ''}days from {'receipt' if from_receipt else 'the date the letter gives'}: "
                                     "confirm the date the client received it, then count"))
    for m in re.finditer(BY_RX, flat, re.I):
        day = iso(m.group(1))
        if day and (not sent or day > sent):
            out.append((day, around(flat, m.start(), m.end()), "date stated in the letter"))
    return out


def references(text):
    apps = sorted(set(re.findall(APP_RX, text)))
    ucis = sorted({u for u in re.findall(UCI_RX, text) if re.search(r"(?:UCI|client ID|identificateur)[^\n]{0,30}" + re.escape(u), text, re.I)})
    return apps, ucis


def addressee(text):
    m = re.search(r"(?:^|\n)\s*(?:Dear|Bonjour|Madame,? Monsieur)\s+(?:Mr\.?|Mrs\.?|Ms\.?|Miss|Dr\.?|M\.|Mme)?\s*([A-Z][A-Za-z'\-]+(?: [A-Z][A-Za-z'\-]+){0,3})", text)
    return m.group(1).strip() if m else ""


def case_text(folder):
    parts = []
    for name in ("case.md", "updates.csv", "client-facts.csv"):
        p = folder / name
        if p.exists():
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def match_cases(apps, name):
    """Active cases that hold the application number, or whose client name matches the addressee: [(folder, why)]."""
    import conflicts
    hits = []
    for folder in cs.folders(cs.ACTIVE):
        text = case_text(folder)
        found = [a for a in apps if a in text]
        if found:
            hits.append((folder, f"application number {found[0]} is in the file"))
            continue
        client = cs.read_case(folder).get("client", "")
        if name and client and conflicts.score(name, client) >= 2:
            hits.append((folder, f"addressed to {name}, client is {client}"))
        elif name and client and " " not in name and conflicts.norm(name) == conflicts.norm(client.split()[-1]):
            hits.append((folder, f"addressed to {name} (surname only), client is {client}: confirm"))
    return hits


def analyse(path):
    pages, status = read_pages(path)
    text = "\n".join(t for _, t in pages)
    r = {"file": str(path), "name": path.name, "status": status, "type": None, "confidence": "L", "date": None, "date_how": "", "limits": [],
         "apps": [], "ucis": [], "addressee": "", "ircc": False, "cases": [], "text": text}
    if status != "ok":
        return r
    r["type"], r["confidence"], _ = classify(text)
    r["date"], r["date_how"] = letter_date(text)
    r["limits"] = time_limits(text, r["date"])
    r["apps"], r["ucis"] = references(text)
    r["addressee"] = addressee(text)
    r["ircc"] = bool(re.search(IRCC_RX, text, re.I))
    r["cases"] = match_cases(r["apps"], r["addressee"])
    return r


def chosen_limit(r, kind, program=""):
    """(due, basis) or (None, reason)."""
    dated = sorted((d, q, how) for d, q, how in r["limits"] if d)
    if dated:
        d, q, how = dated[0]
        return d, f"Letter: \"{q[:140]}\" ({how})"
    if r["limits"]:
        return None, "the letter gives a time limit that can't be counted automatically: " + r["limits"][0][2]
    rule = TYPES[kind][4] if kind in TYPES else None
    if rule and r["date"]:
        rules = cs.load_rules()
        if rule in rules:
            return r["date"] + datetime.timedelta(days=int(rules[rule]["days"])), f"No time limit found in the letter's text. Rule {rule}: {rules[rule]['days']} days from {rules[rule]['counted_from']} ({rules[rule]['basis']})"
    return None, "no time limit found in the letter"


def show(r):
    print(f"{r['name']}")
    if r["status"] == "scanned":
        print("  Scanned letter (no text). Read it yourself, then file it with --type, --date and --due (or --no-deadline).")
        return
    if r["status"] != "ok":
        print(f"  Not read: {r['status']}")
        return
    kind = r["type"]
    print(f"  Type: {TYPES[kind][1] if kind else 'not recognised'}" + (f" (how sure: {de.PLAIN_SURE[r['confidence']]})" if kind else " - give --type when filing (see: ircc_letters.py types)"))
    if not r["ircc"]:
        print("  Note: no IRCC name or heading found. Check it really is from IRCC (fraud letters copy IRCC wording).")
    print(f"  Letter date: {r['date'] or 'not found'}" + (f" ({r['date_how']})" if r["date"] else ""))
    for d, q, how in r["limits"]:
        print(f"  Time limit: {d or '?'} - {how}\n    \"{q[:160]}\"")
    if not r["limits"]:
        print("  Time limit: none found in the text")
    if r["apps"]:
        print("  Application number(s): " + ", ".join(r["apps"]))
    if r["ucis"]:
        print("  UCI: " + ", ".join(de.mask(u) for u in r["ucis"]))
    if r["cases"]:
        for f, why in r["cases"]:
            print(f"  Case: {f.name} ({why})")
    else:
        print("  Case: no active case matched. Give --case when filing")


def cmd_read(a):
    path = pathlib.Path(a.file)
    if not path.is_file():
        die(f"no such file: {path}")
    show(analyse(path))


def cmd_scan(a):
    folder = pathlib.Path(a.folder) if a.folder else REPO / "Input"
    if not folder.is_dir():
        die(f"no such folder: {folder}")
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in READABLE and not any(s in p.parts for s in de.SKIP_DIRS))
    if not files:
        print("No letters found (PDF, Word, text or .eml).")
        return
    found = 0
    for p in files:
        r = analyse(p)
        if r["type"] or r["status"] == "scanned":
            found += 1
            show(r)
            print()
    print(f"{len(files)} file(s) read, {found} look like IRCC letters (or are scanned and need reading).")


def cmd_types(_):
    for k, (_r, name, _w, action, rule) in TYPES.items():
        print(f"{k:22} {name}" + (f" | default rule if the letter states no limit: {rule}" if rule else ""))


def next_name(folder, day, kind, ext):
    stem = f"{day.isoformat()}-ircc-{kind}"
    path, n = folder / f"{stem}{ext}", 1
    while path.exists():
        n += 1
        path = folder / f"{stem}-v{n}{ext}"
    return path


def cmd_file(a):
    import updates as up
    path = pathlib.Path(a.file)
    if not path.is_file():
        die(f"no such file: {path}")
    folder = de.active_case(a.case)
    r = analyse(path)
    kind = a.type or r["type"]
    if kind not in TYPES:
        die("the letter type wasn't recognised. Give --type (see: ircc_letters.py types)")
    sent = cs.parse_date(a.date, "--date") if a.date else r["date"]
    if not sent:
        die("the letter date wasn't found. Give --date YYYY-MM-DD from the letter")
    if a.date:  # the consultant's date wins: count the letter's time limits from it
        r["date"], r["limits"] = sent, time_limits(r["text"], sent)
    received = cs.parse_date(a.received, "--received") if a.received else datetime.date.today()
    if received > datetime.date.today():
        die("the received date can't be in the future")
    info = cs.read_case(folder)
    if a.due:
        due, basis = cs.parse_date(a.due, "--due"), f"Letter dated {sent}: date given by the consultant"
    elif a.no_deadline:
        due, basis = None, ""
    else:
        due, basis = chosen_limit(r, kind, info.get("program", ""))
        if not due and kind not in NO_LIMIT:
            die(f"{basis}. Read the letter and give --due YYYY-MM-DD, or --no-deadline if it sets none")
    dest_dir = folder / "06-correspondence"
    dest_dir.mkdir(exist_ok=True)
    dest = next_name(dest_dir, sent, kind, path.suffix.lower())
    shutil.copy2(path, dest)
    _rules, name, what, action, _rule = TYPES[kind]
    if due:
        rows = cs.read_deadlines(folder)
        rows.append({"due": due.isoformat(), "type": f"ircc-{kind}", "description": f"{name} dated {sent}: {action or 'respond'}", "basis": basis, "status": "open"})
        cs.write_deadlines(folder, rows)
    events = up.load(folder)
    row = {k: "" for k in up.FIELDS}
    row.update(id=str(max((int(e["id"]) for e in events), default=0) + 1), date=received.isoformat(), kind="received", what=what + f" (letter dated {sent})",
               party="IRCC", reference=(r["apps"][0] if r["apps"] else ""), client_action=(action + (f". Deadline: {due}" if due and action else "")).strip(),
               recorded=datetime.datetime.now().isoformat(timespec="seconds"))
    events.append(row)
    up.save(folder, events)
    cs.add_log(folder, f"IRCC letter filed: {name} dated {sent} ({dest.name})" + (f"; deadline {due}" if due else ""), received)
    print(f"Filed in {folder.name}/06-correspondence as {dest.name}")
    if due:
        left = (due - datetime.date.today()).days
        print(f"Deadline added: {due} ({left:+d} days){cs.weekend_note(due)}\n  Basis: {basis}")
        print("  Check this date against the letter. If the letter counts from another date, fix it with case.py.")
    else:
        print("No deadline added" + (" (--no-deadline)" if a.no_deadline else "") + ".")
    print(f"Recorded as received (event {row['id']}). Draft the client update: updates.py notify {info.get('case_id', a.case)}")
    if kind == "procedural-fairness":
        print("Next: /pf-response. Procedural fairness responses are urgent; ask IRCC for more time early if needed.")
    elif kind == "refusal":
        print("Next: /refusal. If judicial review is considered, add its limit now: case.py deadline CASE jr-in-canada (or jr-outside-canada) --from <date the client was notified>.")
        print("  Federal Court matters go to a lawyer (CLAUDE.md rule 4).")
    elif kind == "ita":
        print("Next: check the score claims are still true on the ITA date, and request police certificates and medicals now.")
    elif kind == "medical":
        print("Medical results are valid 12 months: record the exam date with validity.py once done.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="IRCC letter inbox")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("read"); x.add_argument("file"); x.set_defaults(fn=cmd_read)
    x = s.add_parser("scan"); x.add_argument("folder", nargs="?"); x.set_defaults(fn=cmd_scan)
    x = s.add_parser("types"); x.set_defaults(fn=cmd_types)
    x = s.add_parser("file"); x.add_argument("file"); x.add_argument("--case", required=True); x.add_argument("--type", choices=list(TYPES)); x.add_argument("--date")
    x.add_argument("--due"); x.add_argument("--no-deadline", action="store_true"); x.add_argument("--received"); x.set_defaults(fn=cmd_file)
    a = p.parse_args()
    if getattr(a, "due", None) and getattr(a, "no_deadline", False):
        die("give --due or --no-deadline, not both")
    a.fn(a)


if __name__ == "__main__":
    main()
