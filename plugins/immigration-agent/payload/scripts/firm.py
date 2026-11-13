#!/usr/bin/env python3
"""Firm documents on your letterhead: agreements and letters as editable Word files.

Usage:
  python3 scripts/firm.py setup --name "Full Name" --rcic R000000 --address "..." --phone "..." --email "..." --incapacity-plan "..." [--business X] [--website X] [--logo PATH]
  python3 scripts/firm.py show
  python3 scripts/firm.py types
  python3 scripts/firm.py make TYPE [--case 2026-001] [--terms TERMS.json] [--out DIR]

Guarantees:
  - An agreement missing any element the Code of Professional Conduct requires is never produced,
    even if the template wording has been changed. Required elements are listed in this script, not the template.
  - Nothing is produced while any blank remains to be filled. It never guesses a client's details or terms.
  - The firm profile is optional: a document can take your details for that one document (terms "firm": {...}).
    Agreements still need your name, licence number and contact details (Code s.23(2)(a), s.24(3)(a)).
  - Files are never overwritten. Word files, so you can edit before signing.
Templates live in templates/firm/ and can be rewritten in your own words. Keep each "@covers" line.
"""
import argparse
import csv
import datetime
import json
import os
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402

REPO = de.REPO
TEMPLATES = pathlib.Path(os.environ.get("FIRM_TEMPLATES", REPO / "templates" / "firm"))
PROFILE = cs.ROOT / ".firm-profile.json"
TODAY = datetime.date.today()
CODE_TEXT = {
    "23(2)(a)": "your name, licence number and contact details", "23(2)(b)": "the client's name and contact details", "23(2)(c)": "the consultation fee",
    "23(2)(d)": "the College's role as regulator", "23(2)(e)": "the purpose and scope of the consultation",
    "24(3)(a)": "your name, licence number and contact details", "24(3)(b)": "the client's name, address and contact details", "24(3)(c)": "preliminary advice given",
    "24(3)(d)": "quality and supervision statement", "24(3)(e)": "people likely to assist", "24(3)(f)": "the client's instructions", "24(3)(g)": "itemized services",
    "24(3)(h)": "estimated time frames", "24(3)(i)": "fee estimate", "24(3)(j)": "expected disbursements", "24(3)(k)": "taxes", "24(3)(l)": "payment terms and interest",
    "24(3)(m)": "advance payments and refund policy", "24(3)(n)": "additional costs", "24(3)(o)": "conflicts of interest", "24(3)(p)": "return of original documents",
    "24(3)(q)": "confidentiality and how it is kept", "24(3)(r)": "your complaint procedure", "24(3)(s)": "official language of service", "24(3)(t)": "status updates",
    "24(3)(u)": "getting help, including interpreters", "24(3)(v)": "the College's role and complaints process", "24(3)(w)": "College document production",
    "24(3)(x)": "copy of the Code given", "24(3)(y)": "what happens to the file if you can't continue", "24(5)": "amendment agreed in writing by both",
    "27(a)": "written opinion with reasons", "27(b)": "client's written acknowledgement of the risks",
    "IRB-AI": "the IRB's required declaration on the use of AI (IRB Practice Notice, in force 2026-09-07)",
    "22(3)(a)": "notice of what was submitted or received", "22(3)(b)": "copies available on request", "22(1)(f)": "how to check the application online",
    "36(1)(a)": "return of documents and property", "36(1)(b)": "accounting of all money received", "36(1)(c)": "final invoice", "36(1)(d)": "refund of excess trust money",
}
TYPES = {  # type: (template, required Code elements, case folder, what it is)
    "consultation-agreement": ("consultation-agreement.md", [f"23(2)({c})" for c in "abcde"], "02-agreements", "before the first consultation (Code s.23)"),
    "service-agreement": ("service-agreement.md", [f"24(3)({c})" for c in "abcdefghijklmnopqrstuvwxy"], "02-agreements", "before any services (Code s.24)"),
    "amendment": ("amendment.md", ["24(5)"], "02-agreements", "any change to a service agreement, including higher fees (s.24(5), s.31(3))"),
    "risk-acknowledgement": ("risk-acknowledgement.md", ["27(a)", "27(b)"], "02-agreements", "client proceeds against your advice (s.27)"),
    "closing-letter": ("closing-letter.md", [f"36(1)({c})" for c in "abcd"], "06-correspondence", "within 30 days of the agreement ending (s.36(1), file closing s.7.1)"),
    "non-engagement-letter": ("non-engagement-letter.md", [], "06-correspondence", "confirms you are not acting for someone"),
    "letter": ("letter.md", [], "06-correspondence", "any letter on your letterhead"),
    "submission-letter": ("submission-letter.md", [], "05-forms-submissions", "cover letter, letter of explanation or submissions to IRCC or the IRB"),
    "status-update": ("status-update.md", ["22(3)(a)", "22(3)(b)", "22(1)(f)"], "06-correspondence", "tells the client what was submitted or received (s.22(3)); use updates.py"),
}
IRB_RX = r"Immigration and Refugee Board|\bIRB\b|\bCISR\b|Refugee Protection Division|Refugee Appeal Division|Immigration Appeal Division|Immigration Division|\b(?:RPD|RAD|IAD)\b"
FEDERAL_COURT_RX = r"Federal Court|Cour f[ée]d[ée]rale"
DEFAULTS = {
    "confidentiality": "Your file is kept in secure, access-controlled storage. Only the Consultant and the people named in this agreement can see it. Your information is shared only with your written consent, or where the law or the College requires it.",
    "complaints_procedure": "If you are unhappy with the services, please tell the Consultant in writing. The Consultant will acknowledge your complaint within 5 business days and give you a written response within 30 days.",
}
MY_DETAILS = {"name": "your full name", "rcic": "your RCIC licence number (R123456)", "address": "business address", "phone": "phone",
              "email": "email", "incapacity_plan": "your incapacity plan (who takes over your files)"}
PROFILE_LABELS = {"name": "--name", "rcic": "--rcic", "address": "--address", "phone": "--phone", "email": "--email", "incapacity_plan": "--incapacity-plan"}
TERM_HELP = {
    "preliminary_advice": "summary of advice given so far", "instructions": "the client's instructions", "services": "list of services",
    "time_frames": "estimated time frames", "fee_estimate": "fee estimate (fixed fee, or hourly rate and hours)", "disbursements": "list of expected disbursements",
    "taxes": "GST/HST or other taxes", "payment_terms": "when payments are due", "interest": "interest on unpaid amounts (or 'None')",
    "advance_payment": "advance payment required (or 'None')", "refund_policy": "refund policy, by stage", "additional_costs": "other costs the client may pay",
    "conflicts": "conflicts of interest (or 'None known')", "assistants": "people likely to assist (or 'None')", "service_language": "English or French",
    "consultation_purpose": "purpose and scope of the consultation", "consultation_fee": "consultation fee, or 'This consultation is free of charge (pro bono)'",
    "original_date": "date of the original agreement", "changes": "list of changes", "reason": "reason", "matter": "the matter", "reasons": "list of reasons",
    "risks": "list of risks", "outcome": "outcome in one or two sentences", "documents_returned": "list of documents returned", "final_invoice": "final invoice number and amount",
    "refund": "refund amount and how it was paid, or 'No money is owed to you'", "recipient": "recipient's name and address", "subject": "subject", "body": "list of paragraphs",
}


def die(msg):
    sys.exit(f"NOT PRODUCED: {msg}")


def load_profile():
    try:
        return json.loads(PROFILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_profile(p):
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(cs.ROOT), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=1)
    de.replace_with_retry(tmp, PROFILE)


def cmd_setup(a):
    p = load_profile()
    for key in ("name", "rcic", "business", "address", "phone", "email", "website", "incapacity_plan", "complaints", "confidentiality", "technology_notice", "language"):
        value = getattr(a, key)
        if value is not None:
            p["complaints_procedure" if key == "complaints" else key] = value.strip()
    if a.no_technology_notice:
        p["technology_notice"] = ""
    elif "technology_notice" not in p:
        consent = REPO / "templates" / "intake-form-consent.txt"
        p["technology_notice"] = consent.read_text(encoding="utf-8").strip() if consent.exists() else ""
    if a.logo:
        logo = pathlib.Path(a.logo).resolve()
        try:
            from PIL import Image
            with Image.open(logo) as im:
                im.verify()
        except Exception:
            die(f"the logo isn't a readable image: {logo}")
        p["logo"] = str(logo)
    if p.get("rcic") and not re.fullmatch(r"R\d{6}", p["rcic"]):
        die("an RCIC licence number looks like R123456")
    save_profile(p)
    missing = [flag for key, flag in PROFILE_LABELS.items() if not p.get(key)]
    print("Firm profile saved." + (" Still needed: " + ", ".join(missing) if missing else ""))
    for key in DEFAULTS:
        if not p.get(key if key != "complaints_procedure" else "complaints_procedure"):
            print(f"Using standard wording for {key.replace('_', ' ')}. Replace it with your own using --{'complaints' if key == 'complaints_procedure' else key}")


def cmd_show(_):
    p = load_profile()
    if not p:
        die("no firm profile saved (it is optional). Save one with /firm-profile, or give your details with each document")
    for k, v in p.items():
        print(f"{k}: {v if len(str(v)) < 90 else str(v)[:87] + '...'}")


def cmd_types(_):
    for name, (_, req, folder, what) in TYPES.items():
        print(f"{name}: {what}. {len(req)} required elements")


def client_details(folder):
    """Client name from the case, contact details from answers the client gave in the intake form."""
    info = cs.read_case(folder)
    c = {"name": info.get("client", "")}
    facts = folder / "client-facts.csv"
    if facts.exists():
        with facts.open(encoding="utf-8", newline="") as f:
            rows = [r for r in csv.DictReader(f) if de.same_person(c["name"], r.get("person", ""))]
        for key, names in (("address", ("present_address", "residential_address", "mailing_address")), ("email", ("email",)), ("phone", ("telephone",))):
            for n in names:
                hit = [r["value"] for r in rows if r["key"] == n]
                if hit and not c.get(key):
                    c[key] = hit[-1]
    return info, c


def accounting_lines(folder):
    import billing
    rows = billing.load(folder)
    if not rows:
        return None
    s = billing.summary(rows)
    paid = sum((i["applied"] for i in s["invoices"].values()), billing.ZERO)
    return [f"Total received from you: {billing.d(s['received'])}", f"Total invoiced: {billing.d(s['invoiced'])}", f"Paid on invoices: {billing.d(paid)}",
            f"Unpaid on invoices: {billing.d(s['owing'])}", f"Still held in trust for you: {billing.d(s['held'])}"]


def context(profile, info, client, terms, accounting):
    ctx = {"date": f"{TODAY:%B} {TODAY.day}, {TODAY.year}", "case.id": info.get("case_id", ""), "case.program": info.get("program", "")}
    for k, v in profile.items():
        ctx[f"firm.{k}"] = v
    for k, v in DEFAULTS.items():
        ctx.setdefault(f"firm.{k}", v)
        if not ctx[f"firm.{k}"]:
            ctx[f"firm.{k}"] = v
    for k, v in {**client, **(terms.get("client") or {})}.items():
        ctx[f"client.{k}"] = v
    for k, v in terms.items():
        if k != "client":
            ctx[f"terms.{k}"] = v
    ctx.setdefault("terms.service_language", profile.get("language") or "")
    if accounting is not None:
        ctx["accounting"] = accounting
    elif "terms.accounting" in ctx:
        ctx["accounting"] = ctx["terms.accounting"]
    return ctx


def blank(v):
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not any(str(x).strip() for x in v))


def render(template, ctx):
    """Template lines into blocks. Returns (blocks, covered codes, missing keys)."""
    blocks, covers, missing, skipping = [], set(), [], False

    def fill(text):
        def sub(m):
            optional, key = m.group(1) == "?", m.group(2)
            v = ctx.get(key)
            if blank(v):
                if not optional and key not in missing:
                    missing.append(key)
                return ""
            return "; ".join(map(str, v)) if isinstance(v, list) else str(v)
        return re.sub(r"\{(\??)([a-z_.]+)\}", sub, text)

    for raw in template.splitlines():
        line = raw.rstrip()
        if line.startswith("@if "):
            skipping = blank(ctx.get(line[4:].strip()))
            continue
        if line == "@endif":
            skipping = False
            continue
        if skipping:
            continue
        if line.startswith("@covers"):
            covers.update(line.split()[1:])
        elif line == "@signatures":
            blocks.append(("signatures", ""))
        elif line.startswith("# "):
            blocks.append(("title", fill(line[2:])))
        elif line.startswith("## "):
            text = fill(line[3:])
            if re.match(r"\d+\.\s", text):  # renumber, so an optional section that is left out leaves no gap
                numbered = sum(1 for k, t in blocks if k == "heading" and re.match(r"\d+\.\s", t)) + 1
                text = re.sub(r"^\d+\.", f"{numbered}.", text)
            blocks.append(("heading", text))
        elif line.startswith("- "):
            m = re.fullmatch(r"- \{([a-z_.]+)\}", line)
            value = ctx.get(m.group(1)) if m else None
            if m and isinstance(value, list):
                blocks += [("bullet", str(x)) for x in value if str(x).strip()]
                if blank(value) and m.group(1) not in missing:
                    missing.append(m.group(1))
            else:
                blocks.append(("bullet", fill(line[2:])))
        elif re.fullmatch(r"\{([a-z_.]+)\}", line) and isinstance(ctx.get(line[1:-1]), list):
            value = ctx[line[1:-1]]  # a list on a line of its own: one paragraph per item
            blocks += [("body", str(x)) for x in value if str(x).strip()]
            if blank(value) and line[1:-1] not in missing:
                missing.append(line[1:-1])
        elif line:
            blocks.append(("para", fill(line)))
        else:
            blocks.append(("space", ""))
    return blocks, covers, missing


def runs(par, text, size=None):
    from docx.shared import Pt
    for i, part in enumerate(re.split(r"\*\*", text)):
        r = par.add_run(part)
        r.bold = i % 2 == 1
        if size:
            r.font.size = Pt(size)


def write_docx(path, blocks, profile, client_name):
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor, Inches
    d = docx.Document()
    style = d.styles["Normal"]
    style.font.name, style.font.size = "Calibri", Pt(11)
    sec = d.sections[0]
    sec.left_margin = sec.right_margin = Inches(0.9)
    head = sec.header.paragraphs[0]
    if profile.get("logo") and pathlib.Path(profile["logo"]).exists():
        head.add_run().add_picture(profile["logo"], height=Inches(0.55))
        head = sec.header.add_paragraph()
    if profile.get("business") or profile.get("name"):  # no firm details: plain paper, no empty letterhead
        runs(head, f"**{profile.get('business') or profile.get('name', '')}**", 12)
        line = "  |  ".join(x for x in (profile.get("address"), profile.get("phone"), profile.get("email"), profile.get("website")) if x)
        if line:
            runs(sec.header.add_paragraph(), line, 9)
    if profile.get("name") and profile.get("rcic"):
        foot = sec.footer.paragraphs[0]
        foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = foot.add_run(f"{profile['name']}, Regulated Canadian Immigration Consultant, licence no. {profile['rcic']}. Regulated by the College of Immigration and Citizenship Consultants.")
        r.font.size, r.font.color.rgb = Pt(8), RGBColor(0x55, 0x55, 0x55)
    previous = None
    for kind, text in blocks:
        if kind == "space":
            if previous == "para":  # a blank line between paragraphs, as in letters
                d.add_paragraph().paragraph_format.space_after = Pt(0)
            previous = kind
            continue
        previous = kind
        if kind == "title":
            p = d.add_paragraph()
            runs(p, f"**{text}**", 16)
        elif kind == "heading":
            p = d.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            runs(p, f"**{text}**", 12)
        elif kind == "bullet":
            runs(d.add_paragraph(style="List Bullet"), text)
        elif kind in ("para", "body"):
            p = d.add_paragraph()
            p.paragraph_format.space_after = Pt(8 if kind == "body" else 2)  # letter paragraphs get room between them
            runs(p, text)
        elif kind == "table":  # text = [header row, row, ...]
            rows = [[str(c) for c in r] for r in text]
            t = d.add_table(rows=len(rows), cols=max(len(r) for r in rows))
            t.style = "Table Grid"
            for i, r in enumerate(rows):
                for j, c in enumerate(r):
                    cell = t.cell(i, j)
                    cell.text = ""
                    runs(cell.paragraphs[0], f"**{c}**" if i == 0 else c, 9.5)
            d.add_paragraph().paragraph_format.space_after = Pt(2)
        elif kind == "signatures":
            t = d.add_table(rows=4, cols=2)
            for col, who in enumerate((f"{profile.get('name', '')}, RCIC {profile.get('rcic', '')}", client_name)):
                t.cell(0, col).text = "\n\n_______________________________"
                t.cell(1, col).text = who
                t.cell(2, col).text = "\nDate: ____________________"
                t.cell(3, col).text = ""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp.docx")
    os.close(fd)
    try:
        d.save(tmp)
        de.replace_with_retry(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def next_path(folder, stem):
    n = 1
    while True:
        p = folder / f"{stem}{'' if n == 1 else f'-v{n}'}.docx"
        if not p.exists():
            return p
        n += 1


CHECKLISTS = {
    "consultation-agreement": ["Have it signed BEFORE the consultation starts (s.23(1)).", "Give the client a signed copy and keep one (s.23(3))."],
    "service-agreement": ["Before signing: confirm the client's identity and contact details, with corroboration if possible (s.24(2)(a)).",
                          "Give the client this draft to review before signing (s.24(2)(b)).",
                          "Check whether the client already has another representative, and confirm that agreement ended or get clear instructions (s.24(2)(c)).",
                          "Give the client a copy of the Code of Professional Conduct, as the agreement states (s.24(3)(x)).",
                          "Give the client a signed copy and keep one (s.24(4)). Then run: case.py set CASE agreement_signed yes",
                          "File IMM 5476 (Use of a Representative) with IRCC."],
    "amendment": ["Both of you sign before the change takes effect (s.24(5)). Higher fees need the client's written agreement first (s.31(3))."],
    "risk-acknowledgement": ["Have the client sign before you file anything (s.27(b))."],
    "closing-letter": ["Send within 30 days of the agreement ending (s.36(1)). Return all documents first.",
                       "Then record in the case: fees_settled, property_returned and client_notified_in_writing, and close the file."],
    "non-engagement-letter": ["Name any time limit you know of, so the person can act in time."],
    "status-update": ["Send it promptly, by a secure method. Attach copies the client asked for."],
    "submission-letter": ["Check every fact, date and number against the forms and documents before signing.",
                          "Check every legal citation on an official source such as Justice Laws or CanLII.",
                          "IRB: never use this for a narrative, affidavit, statement or other evidence. Those are the person's own words (IRB Practice Notice; CLAUDE.md rule 7)."],
    "letter": [],
}


def draft(kind, folder, terms, out=None):
    """Produce one document. Returns (path, profile). Exits with NOT PRODUCED and the reason if anything is missing."""
    if kind not in TYPES:
        die(f"unknown type '{kind}'. Types: {', '.join(TYPES)}")
    # The saved firm profile is optional: details given for this document (terms "firm") are used first.
    profile = {**load_profile(), **{k: str(v).strip() for k, v in (terms.get("firm") or {}).items() if str(v or "").strip()}}
    if profile.get("rcic") and not re.fullmatch(r"R\d{6}", profile["rcic"]):
        die("an RCIC licence number looks like R123456")
    template_name, required, sub, _ = TYPES[kind]
    info, client = client_details(folder) if folder else ({}, {})
    accounting = accounting_lines(folder) if folder and kind == "closing-letter" else None
    ctx = context(profile, info, client, terms, accounting)
    if kind == "submission-letter":
        who = f"{terms.get('recipient', '')} {terms.get('tribunal', '')}"
        if re.search(FEDERAL_COURT_RX, who, re.I):
            die("Federal Court matters go to a lawyer. RCICs can't represent there (CLAUDE.md rule 4)")
        if re.search(IRB_RX, who, re.I):  # the IRB requires the declaration on anything AI drafted or materially changed
            ctx["ai_declaration"] = "yes"
            required = list(required) + ["IRB-AI"]
        elif str(terms.get("ai_declaration", "")).lower() in ("yes", "true", "1"):
            ctx["ai_declaration"] = "yes"
    template = (TEMPLATES / template_name).read_text(encoding="utf-8")
    blocks, covers, missing = render(template, ctx)
    lost = [c for c in required if c not in covers]
    if lost:
        die(f"templates/firm/{template_name} no longer covers what the Code requires: " + "; ".join(f"{c} ({CODE_TEXT.get(c, '')})" for c in lost) + ". Restore the wording and its @covers line")
    mine = [k for k in missing if k.startswith("firm.")]
    if mine:
        die("this document needs your own details: " + ", ".join(MY_DETAILS.get(k[5:], k[5:].replace("_", " ")) for k in mine)
            + ". Give them in this request (terms \"firm\": {...}), or save them once with /firm-profile (optional)")
    if missing:
        die("fill these in first: " + "; ".join(f"{k} ({TERM_HELP.get(k.split('.')[-1], k.split('.')[-1].replace('_', ' '))})" for k in missing))
    out = pathlib.Path(out) if out else (folder / sub if folder else REPO / "Output" / "general")
    de.guard_output(out)
    out.mkdir(parents=True, exist_ok=True)
    who = "" if folder else "-" + re.sub(r"[^a-z0-9]+", "-", str(ctx.get("client.name", "")).lower()).strip("-")[:30]
    path = next_path(out, f"{TODAY.isoformat()}-{kind}{who if who != '-' else ''}")
    write_docx(path, blocks, profile, str(ctx.get("client.name", "")))
    if folder:
        cs.add_log(folder, f"Drafted {kind.replace('-', ' ')}: {path.name}")
    return path, profile


def cmd_make(a):
    terms = {}
    if a.terms:
        try:
            terms = json.loads(pathlib.Path(a.terms).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            die(f"can't read the terms file ({type(e).__name__})")
    folder = de.active_case(a.case) if a.case else None
    path, profile = draft(a.type, folder, terms, a.out)
    required = TYPES[a.type][1]
    print(f"Drafted: {path.name}" + (f" ({len(required)} required elements present)" if required else ""))
    print("Saved in:", path.parent)
    standard = [k for k in DEFAULTS if not profile.get(k)]
    if standard and a.type in ("service-agreement", "consultation-agreement"):
        print("Standard wording used for: " + ", ".join(k.replace("_", " ") for k in standard) + ". Review it, or set your own with firm.py setup")
    for item in CHECKLISTS[a.type]:
        print("  -", item)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Firm documents on your letterhead")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("setup")
    for flag in ("name", "rcic", "business", "address", "phone", "email", "website", "logo", "incapacity-plan", "complaints", "confidentiality", "technology-notice", "language"):
        x.add_argument(f"--{flag}")
    x.add_argument("--no-technology-notice", action="store_true")
    x.set_defaults(fn=cmd_setup)
    x = s.add_parser("show"); x.set_defaults(fn=cmd_show)
    x = s.add_parser("types"); x.set_defaults(fn=cmd_types)
    x = s.add_parser("make"); x.add_argument("type"); x.add_argument("--case"); x.add_argument("--terms"); x.add_argument("--out"); x.set_defaults(fn=cmd_make)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
