#!/usr/bin/env python3
"""Create a fillable client intake form, and import the answers into a case.

Usage:
  python3 scripts/intake_form.py make --case 2026-001 --person "Full Name"
  python3 scripts/intake_form.py make [--out DIR]               (blank form, no case)
  python3 scripts/intake_form.py import FILE --case 2026-001 --person "Full Name"

The questions follow the case's program: visitor and super visa files ask IMM 5257 and IMM 5645's questions,
study and work files IMM 1294 or IMM 1295 with IMM 5645, everything else the permanent residence forms
(IMM 0008, IMM 5669, IMM 5406). The form records which set it used, so the import reads it back correctly.

Guarantees:
  - Passport, UCI and other identity numbers are not requested. They come from the documents.
  - Yes/No answers have no default, so a blank is never read as No.
  - Nothing is imported without the client's consent and declaration.
  - Answers are added to client-facts.csv. Existing answers are never overwritten.
    A different answer is kept beside the old one, so the worksheet shows a conflict.
  - Answers are not printed. Only counts and question numbers are shown.
"""
import argparse
import csv
import datetime
import os
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402

REPO = de.REPO
TODAY = datetime.date.today()
VERSION = "1"
CONSENT_FILE = REPO / "templates" / "intake-form-consent.txt"
FORMS = ["imm0008", "imm5669", "imm5406"]  # permanent residence
# temporary residence: the application and the family information form, with their own background questions
TR_FORMS = {"visitor": ["imm5257", "imm5645"], "study": ["imm1294", "imm5645"], "work": ["imm1295", "imm5645"]}
SAME_AS = {"parent1_details": "mother_details", "parent2_details": "father_details"}  # IMM 5707's parents are IMM 5645's mother and father
PR_TOPICS = {"family", "pgp", "ee", "pnp", "quebec", "business", "caregiver", "protection"}
FROM_DOCUMENTS_TOO = {"family_name", "given_name", "date_of_birth", "birth_city", "birth_country", "citizenship", "marriage_date"}
YESNO = {"csq_received", "valid_passport", "language_test_taken", "interpreter", "consent_province", "consent_employers", "consent_evaluation", "present_at_marriage", "spouse_present_at_marriage"}
BACKGROUND = {f"bg_{x}" for x in ("conviction_canada", "conviction_abroad", "refugee_claim", "refused_visa", "refused_admission", "war_crime", "armed_struggle", "armed_group", "criminal_org", "detained", "health")}
LONG = {"other_name", "previous_countries", "previous_relationship", "national_id", "us_lpr", "bg_details", "education_history", "personal_history", "organizations", "government_positions", "military_service", "address_history", "dependants", "father_details", "mother_details", "spouse_details", "parent1_details", "parent2_details", "children_details", "siblings_details", "current_residence", "mailing_address", "residential_address", "present_address", "education_years_by_level", "last_entry"}
DATES = {"date_of_birth", "marriage_date", "stay_from", "stay_to"}
LONG_EXTRA = {"current_residence", "contacts_in_canada", "present_address", "purpose_other"}
WHOLE_FAMILY = "Have you, or, if you are the principal applicant, any of your family members listed in your application for permanent residence in Canada, ever:"
MAX_ANSWER = 4000
PICK = "Select"  # A dropdown still on this has not been answered.


def forms_for(program):
    """The worksheets whose questions the intake form asks: temporary residence files get their own forms."""
    import alerts as al
    topics = al.topics_for(program or "")
    if re.search(r"super", program or "", re.I):
        topics = {"visitor"}
    if not topics & PR_TOPICS:
        for t in ("visitor", "study", "work"):
            if t in topics:
                return TR_FORMS[t]
    return FORMS


def questions(forms=None):
    seen, out = set(), []
    for form in forms or FORMS:
        for r in fp.load_spec(form)[1]:
            key = r["key"]
            if key in seen or key in de.SENSITIVE or r["rule"] in ("sign", "consultant"):
                continue
            if SAME_AS.get(key) in seen:  # already asked under its other name
                continue
            if r["rule"] == "auto" and key not in FROM_DOCUMENTS_TOO:
                continue
            seen.add(key)
            hint = r["help"]
            if key in DATES:
                hint = (hint + " Use YYYY-MM-DD.").strip()
            yes_no = key in YESNO or key in BACKGROUND or r["help"].startswith("Yes or No")
            long = key in LONG or key in LONG_EXTRA or key.endswith(("_details", "_history"))
            kind = "yesno" if yes_no else "long" if long else "text"
            out.append({"key": key, "section": r["section"], "question": r["question"], "help": hint, "kind": kind, "form": form})
    return out


def next_path(folder, stem):
    n = 1
    while True:
        p = folder / f"{TODAY.isoformat()}-{stem}{'' if n == 1 else f'-v{n}'}.pdf"
        if not p.exists():
            return p
        n += 1


def make_pdf(path, person, forms=None):
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas
    width, height = letter
    left, right, top, bottom = 50, width - 50, height - 50, 50
    usable = right - left
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp.pdf")
    os.close(fd)
    c = canvas.Canvas(tmp, pagesize=letter)
    c.setTitle("Client intake form")
    state = {"y": top, "page": 1}
    navy, grey = HexColor("#1F3864"), HexColor("#555555")

    def footer():
        c.setFont("Helvetica", 8)
        c.setFillColor(grey)
        c.drawString(left, 30, "Protected when completed. Send it to your consultant by a secure method.")
        c.drawRightString(right, 30, f"Page {state['page']}")
        c.setFillColor(black)

    def room(need):
        if state["y"] - need < bottom:
            footer()
            c.showPage()
            state["page"] += 1
            state["y"] = top

    def write(text, font="Helvetica", size=10, color=black, gap=3):
        lines = simpleSplit(text, font, size, usable)
        room(len(lines) * (size + 3) + gap)
        c.setFont(font, size)
        c.setFillColor(color)
        for line in lines:
            c.drawString(left, state["y"] - size, line)
            state["y"] -= size + 3
        state["y"] -= gap
        c.setFillColor(black)

    def field(name, kind, tip):
        h = {"text": 20, "yesno": 20, "long": 78}[kind]
        room(h + 10)
        y = state["y"] - h
        if kind == "yesno":
            c.acroForm.choice(name=name, tooltip=tip[:200], value=PICK, options=[PICK, "Yes", "No"], x=left, y=y, width=90, height=h, fontName="Helvetica", fontSize=10, borderColor=navy, fillColor=white, textColor=black, forceBorder=True)
        else:
            flags = "multiline" if kind == "long" else ""
            c.acroForm.textfield(name=name, tooltip=tip[:200], value="", x=left, y=y, width=usable, height=h, maxlen=MAX_ANSWER, fontName="Helvetica", fontSize=10, borderColor=navy, fillColor=white, textColor=black, forceBorder=True, fieldFlags=flags)
        state["y"] = y - 12

    write("Client intake form", "Helvetica-Bold", 18, navy, 6)
    if person:
        write(f"For: {person}", "Helvetica-Bold", 11)
    c.acroForm.textfield(name="form_person", value=person or "", x=left, y=2, width=1, height=1, maxlen=200, fieldFlags="readOnly", annotationFlags="hidden", borderWidth=0, forceBorder=False)
    c.acroForm.textfield(name="form_version", value=VERSION, x=left + 2, y=2, width=1, height=1, maxlen=5, fieldFlags="readOnly", annotationFlags="hidden", borderWidth=0, forceBorder=False)
    c.acroForm.textfield(name="form_set", value=",".join(forms or FORMS), x=left + 4, y=2, width=1, height=1, maxlen=200, fieldFlags="readOnly", annotationFlags="hidden", borderWidth=0, forceBorder=False)
    write("Complete one form for each adult. Answer every question truthfully and completely. If a question doesn't apply, write N/A. Your consultant will review your answers, and will use your passport and other documents for details not asked here.", gap=6)
    write("You must tell us about every family member, even anyone not coming to Canada. Leaving out a person or a past refusal can lead to refusal, a 5-year ban, or a family member being barred from sponsorship later.", "Helvetica-Bold", 10, gap=8)
    section = None
    for q in questions(forms):
        if q["section"] != section:
            section = q["section"]
            room(60)
            state["y"] -= 6
            write(section, "Helvetica-Bold", 13, navy, 4)
            if section == "Background" and q["form"] == "imm5669":
                write(WHOLE_FAMILY, "Helvetica-Bold", 10, gap=4)
        need = len(simpleSplit(q["question"], "Helvetica", 10, usable)) * 13 + (78 if q["kind"] == "long" else 20) + 24
        room(need)
        write(q["question"], gap=2)
        if q["help"]:
            write(q["help"], "Helvetica-Oblique", 8.5, grey, 2)
        field(q["key"], q["kind"], q["question"])
    room(190)
    state["y"] -= 6
    write("Consent and declaration", "Helvetica-Bold", 13, navy, 4)
    write(CONSENT_FILE.read_text(encoding="utf-8").strip(), gap=3)
    write("Do you give this authorization?", "Helvetica-Bold", 10, gap=2)
    field("agree_ai_privacy", "yesno", "Authorization")
    write("I declare that the information I have given is truthful, complete and correct.", "Helvetica-Bold", 10, gap=2)
    field("agree_declaration", "yesno", "Declaration")
    write("Your full name and today's date", gap=2)
    field("signed_name", "text", "Full name and date")
    footer()
    c.save()
    de.replace_with_retry(tmp, path)


def read_answers(path):
    import pypdf
    try:
        reader = pypdf.PdfReader(str(path), strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            sys.exit("ERROR: this file is password protected")
        fields = reader.get_fields() or {}
    except Exception as e:
        sys.exit(f"ERROR: can't read this PDF ({type(e).__name__})")
    out = {}
    for name, info in fields.items():
        value = info.get("/V")
        if value is None:
            continue
        text = str(value).lstrip("/") if str(value).startswith("/") else str(value)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text).strip()
        if text and text != PICK:
            out[name.split(".")[-1]] = text[:MAX_ANSWER]
    return out


def read_facts(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def firm_name():
    try:
        import firm
        return (firm.load_profile() or {}).get("business") or (firm.load_profile() or {}).get("name", "")
    except Exception:
        return ""


def cmd_make(a):
    import intake_questionnaire as iq
    extras = [f.lower() for f in a.add_form or []]
    uncovered = [f for f in extras if f not in iq.COVERS_EXTRA]
    guided = not a.classic and not uncovered  # the guided questionnaire (version 2) unless an extra form needs the classic one
    if a.case:
        out = de.active_case(a.case) / "01-intake"
    else:
        default = "client-questionnaires" if guided else "general"  # blank questionnaires have their own folder
        out = pathlib.Path(a.out) if a.out else REPO / "Output" / default
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    if guided:
        program = a.program or iq.program_for(case_program(a.case) if a.case else "")
        if program not in iq.PROGRAMS:
            sys.exit(f"ERROR: program must be one of: {', '.join(iq.PROGRAMS)}")
        slug = f"-{re.sub(r'[^a-z0-9]+', '-', a.person.lower()).strip('-')}" if a.person else ""
        path = next_path(out, f"client-questionnaire-{program}{slug}")
        iq.make_pdf(path, a.person or "", program, firm_name())
        print(f"Questionnaire: {iq.PROGRAMS[program]['title']} ({iq.describe(program)})")
        for f in extras:
            print(f"Also covers {iq.COVERS_EXTRA[f]}")
        print("Form:", path)
        return
    if uncovered and not a.classic:
        print(f"Note: the guided questionnaire does not cover {', '.join(f.upper() for f in uncovered)}; using the classic form.")
    forms = forms_for(case_program(a.case)) if a.case else FORMS
    known = {r["form"] for r in fp.load_csv(fp.SPECS / "index.csv")}
    for extra in a.add_form or []:
        if extra.lower() not in known:
            sys.exit(f"ERROR: no worksheet for {extra}")
        if extra.lower() not in forms:
            forms = forms + [extra.lower()]
    path = next_path(out, "client-intake-form" + (f"-{re.sub(r'[^a-z0-9]+', '-', a.person.lower()).strip('-')}" if a.person else ""))
    make_pdf(path, a.person or "", forms)
    print(f"Questions: {len(questions(forms))} (from {', '.join(f.upper().replace('IMM', 'IMM ').replace('CIT', 'CIT ') for f in forms)})")
    print("Form:", path)


def cmd_import(a):
    src = pathlib.Path(a.file)
    if not src.exists():
        sys.exit(f"ERROR: not found: {src}")
    if any(p.lower() == "client-ids" for p in src.resolve().parts):
        sys.exit("ERROR: client-ids folders are not read")
    case = de.active_case(a.case)
    answers = read_answers(src)
    import intake_questionnaire as iq
    if answers.get("form_version") not in (VERSION, iq.VERSION):
        sys.exit("ERROR: this isn't a current intake form")
    if answers.get("form_person") and not de.same_person(answers["form_person"], a.person):
        sys.exit("ERROR: this form was issued to a different person")
    if answers.get("agree_ai_privacy") != "Yes" or answers.get("agree_declaration") != "Yes":
        sys.exit("NOT IMPORTED: the client hasn't given both the authorization and the declaration")
    flags, keep = [], {}
    if answers.get("form_version") == iq.VERSION:
        program = answers.get("form_program") or ""
        if program not in iq.PROGRAMS:
            sys.exit("ERROR: this questionnaire names a program that isn't known")
        keep, flags, qs = iq.collect(answers, program)
        sent = iq.PROGRAMS[program]["forms"]
        return write_import(a, case, keep, flags, qs, sent)
    sent = [f for f in (answers.get("form_set") or "").split(",") if f]
    known = {r["form"] for r in fp.load_csv(fp.SPECS / "index.csv")}
    if any(f not in known for f in sent):
        sys.exit("ERROR: this form names a question set that isn't known")
    qs = questions(sent or FORMS)
    for q in qs:
        value = answers.get(q["key"])
        if not value:
            continue
        if q["key"] in DATES:
            parsed, _ = de.parse_date(value)
            if not parsed:
                flags.append(f"{fp_label(q)}: not a clear date. Not imported")
                continue
            value = parsed
        if q["kind"] == "yesno" and value not in ("Yes", "No"):
            flags.append(f"{fp_label(q)}: not Yes or No. Not imported")
            continue
        keep[q["key"]] = value
    wanted = {r["key"] for f in (sent or FORMS) for r in fp.load_spec(f)[1]}
    for parent, same in SAME_AS.items():  # a parent asked once fills both names (Parent 1 = mother, Parent 2 = father)
        if parent in wanted and keep.get(same) and parent not in keep:
            keep[parent] = keep[same]
    return write_import(a, case, keep, flags, qs, sent)


def write_import(a, case, keep, flags, qs, sent):
    """Add the answers to client-facts.csv: nothing overwritten, a different answer kept beside the old one."""
    facts_path = case / "client-facts.csv"
    rows = read_facts(facts_path)
    existing = [r for r in rows if de.same_person(a.person, r.get("person", ""))]
    source = f"Client intake form {TODAY.isoformat()}"
    added, same, conflicts, new_rows = 0, 0, 0, []
    for key, value in keep.items():
        old = [r for r in existing if r["key"] == key]
        if any(fp.norm(r["value"]) == fp.norm(value) for r in old):
            same += 1
            continue
        if old:
            conflicts += 1
            flags.append(f"{key}: differs from an earlier answer. Both are kept")
        new_rows.append({"person": a.person, "key": key, "value": value, "source": source})
        added += 1
    fresh = not facts_path.exists()
    with facts_path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["person", "key", "value", "source"])
        if fresh:
            w.writeheader()
        w.writerows(new_rows)
    blank = [q for q in qs if q["key"] not in keep]
    background = {q["key"] for q in qs if q["key"] in BACKGROUND or (q["key"].startswith("tr_") and q["kind"] == "yesno")}
    yes = [q for q in qs if q["key"] in background and keep.get(q["key"]) == "Yes"]
    if yes:
        flags.insert(0, f"URGENT: {len(yes)} background answer(s) are Yes: review before filing")
        if not (keep.get("bg_details") or any(keep.get(q["key"]) for q in qs if q["key"].startswith("tr_") and q["key"].endswith("_details"))):
            flags.insert(1, "URGENT: background answer is Yes but no details were given")
    if not keep.get("children_details"):
        flags.append("Children left blank: confirm the client has none (IRPR 117(9)(d))")
    if any(q["key"] in background for q in blank):
        flags.append(f"{sum(q['key'] in background for q in blank)} background question(s) left blank")
    log = case / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(f"| {TODAY.isoformat()} | Intake form imported for {a.person.replace('|', '/')}: {added} new answers, {conflicts} conflicts, {len(blank)} blank |\n")
    print(f"Added: {added} | unchanged: {same} | conflicts: {conflicts} | left blank: {len(blank)}")
    for x in flags:
        print(" ", x)


def case_program(ref):
    text = (de.active_case(ref) / "case.md").read_text(encoding="utf-8")
    m = re.search(r"(?m)^program:\s*(.*)$", text)
    return m.group(1).strip() if m else ""


def fp_label(q):
    return q["question"][:60]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Client intake form")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("make"); x.add_argument("--case"); x.add_argument("--person"); x.add_argument("--out")
    x.add_argument("--classic", action="store_true", help="the original one-list form instead of the guided questionnaire")
    x.add_argument("--program", help="questionnaire: visitor, study, work, express-entry or family-pr (default: from the case)")
    x.add_argument("--add-form", action="append", help="also ask this form's questions, e.g. imm5707 for residents of Bangladesh (IMM 5890)"); x.set_defaults(fn=cmd_make)
    x = s.add_parser("import"); x.add_argument("file"); x.add_argument("--case", required=True); x.add_argument("--person", required=True); x.set_defaults(fn=cmd_import)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
