"""Guided client questionnaire (intake form version 2) for five programs: visitor, study, work, Express Entry, family / PR.

Each program's questionnaire is a fillable PDF with a cover page, plain-language numbered sections, examples,
"why we ask" notes, one card per family member, one row per period in history tables, the background questions
in IRCC's exact wording, a program section and a document checklist. collect() turns a returned form into
client facts: worksheet keys for simple answers, family.<person>.<box> for the family cards, box parts for
addresses, and one-line summaries for the worksheets that still take a single answer.
"""
import datetime
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402

VERSION = "2"
PICK = "Select"
CHECKED_ON = "2026-11-11"
# Extra forms a visa office may ask for that this questionnaire already covers, so it can be used for them too.
COVERS_EXTRA = {"imm5707": "IMM 5707 (Family information): the family cards, marriage questions and present occupation cover it"}
BOX_GROUPS = {"mailing_address", "contacts_in_canada", "current_residence"}  # answers written box by box on IRCC forms

PROGRAMS = {
    "visitor": {"title": "Visitor visa", "forms": ["imm5257", "imm5645"], "background": "imm5257"},
    "study": {"title": "Study permit", "forms": ["imm1294", "imm5645"], "background": "imm1294"},
    "work": {"title": "Work permit", "forms": ["imm1295", "imm5645"], "background": "imm1295"},
    "express-entry": {"title": "Express Entry (permanent residence)", "forms": ["imm0008", "imm5669", "imm5406", "imm5562"], "background": "imm5669"},
    "family-pr": {"title": "Family sponsorship / permanent residence", "forms": ["imm0008", "imm5669", "imm5406", "imm5562", "imm1344"], "background": "imm5669"},
}


def program_for(program):
    """The questionnaire for a case's program."""
    import alerts as al
    p = program or ""
    topics = al.topics_for(p)
    if re.search(r"super", p, re.I):
        return "visitor"
    if "ee" in topics:
        return "express-entry"
    if topics & {"family", "pgp", "pnp", "quebec", "business", "caregiver", "protection"}:
        return "family-pr"
    for t in ("study", "work", "visitor"):
        if t in topics:
            return t
    return "family-pr"


# ---- the questions ----
def q(key, label, kind="text", help="", example="", options=None):
    return {"type": "q", "key": key, "label": label, "kind": kind, "help": help, "example": example, "options": options or []}


def table(name, label, columns, rows, help="", summary=None):
    return {"type": "table", "name": name, "label": label, "columns": columns, "rows": rows, "help": help, "summary": summary}


def note(text, bold=False):
    return {"type": "note", "text": text, "bold": bold}


def people(roles, help=""):
    return {"type": "people", "roles": roles, "help": help}


YES_NO = ["Yes", "No"]
DATE_HELP = "Use YYYY-MM-DD."


def about_you():
    return ("About you", "So we can match your answers to your passport and identity documents.", [
        q("family_name", "Family name (surname), exactly as in your passport", example="ADEYEMI"),
        q("given_name", "Given name(s), exactly as in your passport", example="FOLAKE GRACE"),
        q("other_name", "Any other names you have used (maiden name, nickname, other spellings)", "long", "Write None if you have not used any other name.", "Folake Bello (name before marriage)"),
        q("name_native_script", "Your name in your own language's script (for example Arabic, Chinese, Cyrillic, Bengali or Hindi), if you write it differently", help="Leave blank if not applicable."),
        q("sex", "Sex", "choice", options=["Female", "Male", "Another gender"]),
        q("date_of_birth", "Date of birth", "date", DATE_HELP, "1972-03-20"),
        q("birth_city", "City or town of birth", example="Lagos"),
        q("birth_country", "Country of birth", example="Nigeria"),
        q("citizenship", "Country of citizenship (all of them, if more than one)", example="Nigeria"),
        q("current_residence", "Where do you live now, your status there, and since when?", "long",
          "Status means citizen, permanent resident, worker, student or visitor.", "United Arab Emirates, worker, since 2018-03"),
        q("previous_countries", "In the last 5 years, have you lived in another country for more than 6 months?", "long",
          "Give the country, your status and the dates, or write No.", "No"),
        q("native_language", "Native language (mother tongue)", example="Yoruba"),
        q("communicate_language", "Can you communicate in English or French?", "choice", options=["English", "French", "Both", "Neither"]),
        q("language_test_taken", "Have you taken an English or French test (IELTS, CELPIP, PTE Core, TEF, TCF)?", "yesno"),
        q("national_id", "Do you have a national identity card?", "yesno", "Do not write the number here. Send a copy of the card with your documents."),
        q("us_lpr", "Do you hold a United States green card (permanent residence)?", "yesno"),
    ])


def contact():
    return ("Contact details", "IRCC sends letters and requests to this address and email.", [
        note("Your mailing address, in parts:", True),
        q("mailing_address__AptUnit", "Flat or apartment number (if any)", example="Apartment 504"),
        q("mailing_address__StreetNum", "House or building number", example="Building 12"),
        q("mailing_address__StreetName", "Road or street, and area", example="Al Barsha 1"),
        q("mailing_address__CityTown", "City or town", example="Dubai"),
        q("mailing_address__District", "District, province or state", example="Dubai"),
        q("mailing_address__PostalCode", "Postal code", "text", "Leave blank if your country has no postal codes.", "None in the United Arab Emirates: leave blank"),
        q("mailing_address__Country", "Country", example="United Arab Emirates"),
        q("residential_same", "Do you live at this same address?", "yesno"),
        q("residential_address", "If not, your home address", "long", "Leave blank if it is the same."),
        q("telephone", "Telephone number, with country code", example="+971 50 123 4567 (country code first)"),
        q("email", "Email address", example="name@example.com"),
        q("language_service", "In which language should IRCC write to you?", "choice", options=["English", "French"]),
    ])


def marital():
    return ("Marital status", "IRCC asks about every marriage or common-law relationship, current and past.", [
        q("marital_status", "Current marital status", "choice", options=["Single", "Married", "Common-law", "Widowed", "Divorced", "Legally separated", "Annulled marriage"]),
        q("marriage_date", "If married or common-law: date of marriage, or date you started living together", "date", DATE_HELP, "1995-06-10"),
        q("present_at_marriage", "If you married: were you physically present at your marriage ceremony?", "yesno"),
        q("spouse_present_at_marriage", "If you married: was your spouse physically present at the ceremony?", "yesno"),
        table("prevrel", "Previous marriages or common-law relationships (including a spouse who has died)",
              [("name", "Full name", 3), ("dob", "Date of birth", 2), ("type", "Married or common-law", 2), ("from", "From", 1.5), ("to", "To", 1.5)], 3,
              "Leave the table empty if there were none.", summary="previous_relationship"),
    ])


def family():
    roles = ["spouse", "mother", "father"] + [f"child{i}" for i in range(1, 5)] + [f"sibling{i}" for i in range(1, 5)]
    return ("Your family", "IRCC requires every family member, even those not coming to Canada. Leaving someone out can lead to "
            "refusal, a 5-year ban, or that person being unable to immigrate later.", [
        note("For anyone who has died: write Deceased, the city, country and date of death in the address box.", True),
        q("has_children", "Do you have any children, of any age, living anywhere (including adopted and step-children)?", "yesno"),
        q("has_siblings", "Do you have any brothers or sisters (including half- and step-brothers and sisters)?", "yesno"),
        people(roles, "Fill one card per person. Use extra pages if you have more than 4 children or 4 brothers and sisters."),
    ])


def education():
    return ("Education", "Some forms ask for your schooling after secondary school.", [
        q("post_secondary", "Have you studied after secondary school (college, university, trade school)?", "yesno"),
        table("edu", "Studies after secondary school, most recent first",
              [("from", "From (YYYY-MM)", 1.4), ("to", "To", 1.2), ("school", "School and city, country", 3), ("field", "Field of study", 2), ("award", "Diploma or degree", 2)], 4,
              summary="education_history"),
    ])


def work_history():
    return ("Work and activities: last 10 years", "IRCC needs every month accounted for, with no gaps. Include unemployment, "
            "studies, homemaking and retirement.", [
        q("occupation", "Your present occupation (job title)", help="If you are not working, write student, homemaker, retired or unemployed.", example="Sales manager"),
        table("hist", "What you were doing, most recent first",
              [("from", "From (YYYY-MM)", 1.4), ("to", "To", 1.2), ("activity", "Activity", 2), ("employer", "Employer or school", 2.5), ("place", "City, country", 2)], 8,
              "Activity: employed, self-employed, student, homemaker, retired or unemployed. Example: 2018-03 / now / Employed / ABC Trading LLC / Dubai, United Arab Emirates",
              summary="employment_history"),
    ])


def history():
    return ("Travel and immigration history", "Earlier applications and travel help show you respect visa conditions.", [
        q("tr_previous_application", "Have you ever applied for a Canadian visa, permit or immigration program?", "yesno"),
        table("apps", "Earlier applications to Canada or any other country",
              [("year", "Year", 1), ("country", "Country", 1.5), ("type", "Type (visitor visa, study permit...)", 3), ("result", "Result (approved, refused, withdrawn)", 2.5)], 4,
              summary="previous_applications"),
        table("travel", "Travel outside your country in the last 10 years",
              [("from", "From", 1.3), ("to", "To", 1.3), ("country", "Country", 2), ("purpose", "Purpose", 3)], 6, summary="travel_history"),
    ])


def background(form):
    rows = [r for r in fp.load_spec(form)[1] if r["section"] == "Background" or r["key"].startswith(("bg_", "tr_"))]
    items = [note("Answer every question Yes or No exactly as it applies. Your consultant will discuss any Yes answer with you.", True)]
    if form == "imm5669":
        items.append(note("Have you, or, if you are the principal applicant, any of your family members listed in your application for permanent residence in Canada, ever:", True))
    for r in rows:
        if r["key"] in ("tr_previous_application",):
            continue
        yes_no = r["help"].startswith("Yes or No") or r["key"].startswith("bg_") and r["key"] != "bg_details"
        items.append(q(r["key"], r["question"], "yesno" if yes_no else "long", "" if yes_no else "Give dates, places and outcomes."))
    return ("Background questions", "These are IRCC's own questions, in its exact words.", items)


VISIT = ("About your visit", "This explains the purpose of your trip and why you will return home.", [
    q("purpose_of_visit", "Main purpose of your visit", "choice", options=["Family Visit", "Tourism", "Business", "Other"]),
    q("purpose_other", "If Other, explain", "long"),
    q("stay_from", "Planned arrival date", "date", DATE_HELP, "2027-04-15"),
    q("stay_to", "Planned departure date", "date", DATE_HELP, "2027-06-15"),
    note("The person you will visit in Canada:", True),
    q("contacts_in_canada__Name", "Their full name", example="Tunde Adeyemi"),
    q("contacts_in_canada__Relationship", "Their relationship to you", example="Son"),
    q("contacts_in_canada__Address", "Their address in Canada", example="123 Main Street NW, Edmonton, AB T5J 0A1"),
    q("host_status", "Their status in Canada", "choice", options=["Canadian citizen", "Permanent resident", "Temporary resident", "Other"]),
    q("visit_paid_by", "Who will pay for the trip?", "choice", options=["Myself", "My host in Canada", "Both", "Someone else"]),
    q("funds", "Money available for the trip, in Canadian dollars", example="8000"),
    q("ties_home", "What will bring you back home? (job, business, property, family staying behind, other commitments)", "long",
      "This is one of the main points an officer checks.", "My job in Dubai; my husband and daughter live with me there"),
    q("invitation_letter", "Will your host send a letter of invitation?", "yesno"),
    q("super_visa_interest", "Do you want to stay longer than 6 months at a time? (A super visa may suit you better)", "yesno"),
])
STUDY = ("About your studies", "These answers become your study permit application and study plan.", [
    q("school_name", "School (designated learning institution)", example="University of Alberta"),
    q("dli_number", "DLI number (on your letter of acceptance)", example="O19257171832"),
    q("study_level", "Level of study", "choice", options=["Secondary", "College diploma or certificate", "Bachelor's degree", "Master's degree", "Doctorate", "Language course", "Other"]),
    q("study_field", "Program or field of study", example="BSc Computing Science"),
    q("study_address", "City and province of the school", example="Edmonton, Alberta"),
    q("study_from", "Program start date", "date", DATE_HELP),
    q("study_to", "Program end date", "date", DATE_HELP),
    q("loa_received", "Have you received your letter of acceptance?", "yesno"),
    q("pal_number", "Provincial or territorial attestation letter (PAL/TAL): number if received, or Not received", example="Not received"),
    q("caq_number", "Quebec only: CAQ number, if received"),
    q("tuition", "First-year tuition, in Canadian dollars", example="28000"),
    q("room_board", "Room and board for one year, in Canadian dollars", example="12000"),
    q("funds", "Total money available for your studies, in Canadian dollars", example="60000"),
    q("expenses_paid_by", "Who pays your expenses?", "choice", options=["Myself", "Parents", "Other family", "Scholarship", "Other"]),
    q("study_plan_why", "Why this program, this school and Canada?", "long", "A few sentences in your own words. Your consultant will help shape your study plan."),
    q("study_plan_career", "How will this program help your career when you return home?", "long"),
    q("study_gaps", "Any gaps in your studies or work? Explain what you did.", "long"),
])
WORK = ("About your job in Canada", "These answers become your work permit application.", [
    q("work_permit_type", "Type of work permit", "choice", options=["Employer-specific with LMIA", "Employer-specific, LMIA-exempt", "Open work permit", "Not sure"]),
    q("employer_name", "Employer's name in Canada"),
    q("job_title", "Job title", example="Cook"),
    q("noc_code", "NOC code, if your employer gave it", example="63200"),
    q("work_location", "City and province where you will work", example="Calgary, Alberta"),
    q("work_period", "Start date and length of the job", example="2027-03-01, 2 years"),
    q("wage", "Wage (hourly or yearly) and hours per week", example="$22.50 per hour, 40 hours"),
    q("lmia_or_offer_number", "LMIA number or offer of employment number, if your employer gave it"),
    q("job_duties", "Main duties of the job", "long"),
    q("family_accompanying", "Will your spouse or children come with you? Who?", "long"),
])
EE = ("About your Express Entry profile", "These answers decide your CRS score and which programs you qualify for.", [
    table("lang", "Language tests (yours, and your spouse's if any). Results must be less than 2 years old",
          [("person", "Whose (me or spouse)", 1.6), ("test", "Test", 1.5), ("date", "Test date", 1.4), ("l", "Listening", 1), ("r", "Reading", 1), ("w", "Writing", 1), ("s", "Speaking", 1)], 3,
          summary="ee_language"),
    table("eca", "Educational credential assessments (ECA), less than 5 years old",
          [("person", "Whose", 1.3), ("credential", "Degree or diploma", 2.5), ("org", "Organization (WES, ICAS...)", 2), ("date", "Date", 1.2), ("result", "Canadian equivalency", 2.5)], 3,
          summary="ee_eca"),
    table("eework", "Skilled work experience in the last 10 years (each job), most recent first",
          [("from", "From", 1.2), ("to", "To", 1.2), ("title", "Job title", 2), ("employer", "Employer, country", 2.5), ("hours", "Hours/week", 1), ("noc", "NOC if known", 1.1)], 6,
          "Your consultant will need a reference letter for each job.", summary="ee_work"),
    q("ee_duties", "Main duties of your current or most recent job", "long"),
    q("settlement_funds", "Money you can show for settling in Canada, in Canadian dollars", example="25000"),
    q("job_offer", "Do you have a job offer in Canada? Give employer, job and duration, or write No", "long"),
    q("provincial_nomination", "Do you have a provincial nomination? Which province? Or write No"),
    q("sibling_in_canada", "Do you or your spouse have a brother or sister in Canada who is a citizen or permanent resident?", "yesno"),
    q("canadian_study", "Have you studied in Canada? Program, school and dates, or write No", "long"),
    q("spouse_canadian_work", "Has your spouse worked in Canada? Dates and job, or write No", "long"),
    q("intended_province", "Province where you plan to live", example="Ontario"),
])
FAMILY_PR = ("About your sponsor and relationship", "For family sponsorship, IRCC must see that your relationship is genuine. "
             "Skip this section if no one is sponsoring you.", [
    q("sponsor_name", "Your sponsor's full name"),
    q("sponsor_relationship", "Your sponsor is your", "choice", options=["Spouse", "Common-law partner", "Conjugal partner", "Parent", "Grandparent", "Child", "Other relative", "No sponsor"]),
    q("sponsor_status", "Your sponsor's status in Canada", "choice", options=["Canadian citizen", "Permanent resident", "Registered Indian"]),
    q("relationship_history", "How and when did you meet? When did the relationship start, and when did you marry or start living together?", "long",
      "Dates and places help. Your consultant will prepare the relationship form with you."),
    q("cohabitation", "Periods you have lived together, with dates and addresses", "long"),
    q("previous_sponsorship", "Have you or your sponsor been sponsored, or sponsored someone, before?", "yesno"),
    q("intended_province", "Province where you plan to live", example="Alberta"),
    q("intended_city", "City where you plan to live", example="Edmonton"),
])
PROGRAM_SECTION = {"visitor": VISIT, "study": STUDY, "work": WORK, "express-entry": EE, "family-pr": FAMILY_PR}

DOCUMENTS = {
    "visitor": ["Passport: all pages, including old passports with visas and travel stamps", "National identity card (front and back), if you have one",
                "Birth certificate", "Marriage certificate; divorce or death certificate for any earlier or late spouse",
                "Bank statements for the last 6 months", "Proof of income: employer letter, pay slips, pension, business registration or rental income",
                "Proof of ties at home: property documents, family, ongoing work or business", "Letter of invitation from your host in Canada",
                "Your host's status: Canadian passport, citizenship certificate or PR card (both sides)",
                "Proof of your relationship to your host (for example their birth certificate naming you)",
                "Travel plan: provisional flight and where you will stay", "If someone else pays: their letter, ID and bank statements",
                "Any extra forms or documents the visa office for your country requires (your consultant will confirm, for example IMM 5707 for residents of Bangladesh)",
                "Certified English or French translation of any document in another language"],
    "study": ["Passport", "Letter of acceptance from your school", "Provincial or territorial attestation letter (PAL/TAL), unless your program is exempt",
              "Quebec only: CAQ", "Proof of funds for tuition and one year of living costs (bank statements, GIC, scholarship, sponsor's documents)",
              "Receipt for any tuition already paid", "Transcripts, diplomas and certificates", "Language test results, if your school required them",
              "Birth certificate (if under 18) and family documents", "Resume or CV, if you have worked",
              "Any extra forms or documents the visa office for your country requires (your consultant will confirm, for example IMM 5707 for residents of Bangladesh)",
                "Certified English or French translation of any document in another language"],
    "work": ["Passport", "Job offer or employment contract", "Copy of the LMIA, or the offer of employment number from your employer",
             "Diplomas, licences or certificates needed for the job", "Reference letters from past employers (job title, duties, dates, hours, salary)",
             "Resume or CV", "Language test results, if the job requires them", "Marriage and birth certificates for family members coming with you",
             "Any extra forms or documents the visa office for your country requires (your consultant will confirm, for example IMM 5707 for residents of Bangladesh)",
                "Certified English or French translation of any document in another language"],
    "express-entry": ["Passport (each family member)", "Language test results, less than 2 years old (you and your spouse)",
                      "Educational credential assessment (ECA), less than 5 years old, and your diplomas and transcripts",
                      "Reference letter for each job: letterhead, signed, job title, duties, hours per week, salary and dates",
                      "Pay slips, tax returns or employment contracts supporting each job", "Proof of settlement funds: bank statements for the last 6 months",
                      "Job offer letter or provincial nomination certificate, if you have one", "Marriage certificate and children's birth certificates",
                      "After an invitation: police certificates (each country of 6 months or more since age 18, last 10 years), medical exam, photos",
                      "Certified English or French translation of any document in another language"],
    "family-pr": ["Passport (each family member)", "Birth certificate (each family member)", "Marriage certificate, or proof of living together for common-law",
                  "Divorce, annulment or death certificate for any earlier marriage", "Your sponsor's proof of status in Canada",
                  "Relationship evidence: photos together, messages, joint documents, visits", "Police certificates (each country of 6 months or more since age 18)",
                  "Photos following IRCC's specifications", "Certified English or French translation of any document in another language"],
}


def sections(program):
    """[(title, why, items)] for a program, in order."""
    out = [about_you(), contact(), marital(), family(), education(), work_history(), history(), background(PROGRAMS[program]["background"]),
           PROGRAM_SECTION[program]]
    return out


def field_names(program):
    """Every fillable field name on a program's questionnaire (without the hidden and consent fields)."""
    names = []
    for _, _, items in sections(program):
        for it in items:
            if it["type"] == "q":
                names.append(it["key"])
            elif it["type"] == "table":
                names += [f"t__{it['name']}__{i}__{c[0]}" for i in range(1, it["rows"] + 1) for c in it["columns"]]
            elif it["type"] == "people":
                names += [f"p__{r}__{b}" for r in it["roles"] for b in person_boxes(r)]
    names += [f"d__{i}" for i in range(1, len(DOCUMENTS[program]) + 1)] + ["documents_note"]
    return names


def person_boxes(role):
    boxes = ["FamilyName", "GivenNames", "DOB", "COB", "MaritalStatus", "Occupation", "Address", "Accompanying"]
    if role.startswith(("child", "sibling")):
        boxes.insert(2, "Relationship")
    return boxes


PERSON_TITLE = {"spouse": "Spouse or common-law partner (current, or late spouse)", "mother": "Mother", "father": "Father"}
BOX_LABEL = {"FamilyName": "Family name", "GivenNames": "Given name(s)", "Relationship": "Relationship (son, daughter, brother, half-sister...)",
             "DOB": "Date of birth (YYYY-MM-DD)", "COB": "Country of birth", "MaritalStatus": "Marital status", "Occupation": "Occupation",
             "Address": "Current address (if deceased: Deceased, city, country, date)", "Accompanying": "Coming with you to Canada?"}


# ---- the PDF ----
def make_pdf(path, person, program, firm=""):
    import os
    import tempfile
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas
    width, height = letter
    left, right, top, bottom = 48, width - 48, height - 54, 54
    usable = right - left
    navy, grey, light, rule = HexColor("#1F3864"), HexColor("#555555"), HexColor("#EEF2F8"), HexColor("#C9D3E3")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp.pdf")
    os.close(fd)
    c = canvas.Canvas(tmp, pagesize=letter)
    title = PROGRAMS[program]["title"]
    c.setTitle(f"Client questionnaire: {title}")
    st = {"y": top, "page": 1}

    def footer():
        c.setStrokeColor(rule)
        c.line(left, 42, right, 42)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(grey)
        c.drawString(left, 30, f"Client questionnaire: {title}. Protected when completed: return it by a secure method.")
        c.drawRightString(right, 30, f"Page {st['page']}")
        c.setFillColor(black)

    def new_page():
        footer()
        c.showPage()
        st["page"] += 1
        st["y"] = top

    def room(need):
        if st["y"] - need < bottom:
            new_page()

    def text(t, font="Helvetica", size=9.5, color=black, gap=2, indent=0):
        lines = simpleSplit(t, font, size, usable - indent)
        room(len(lines) * (size + 2.5) + gap)
        c.setFont(font, size)
        c.setFillColor(color)
        for line in lines:
            c.drawString(left + indent, st["y"] - size, line)
            st["y"] -= size + 2.5
        st["y"] -= gap
        c.setFillColor(black)

    def box(name, kind, x, y, w, h, options=None, tip=""):
        common = dict(x=x, y=y, width=w, height=h, borderColor=navy, fillColor=white, textColor=black, forceBorder=True, fontName="Helvetica", fontSize=9)
        if kind in ("yesno", "choice"):
            opts = [PICK] + (YES_NO if kind == "yesno" else options)
            c.acroForm.choice(name=name, tooltip=tip[:200], value=PICK, options=opts, **common)
        else:
            c.acroForm.textfield(name=name, tooltip=tip[:200], value="", maxlen=4000, fieldFlags="multiline" if kind == "long" else "", **common)

    def question(it, n):
        h = 54 if it["kind"] == "long" else 18
        label = f"{n}  {it['label']}"
        lines = simpleSplit(label, "Helvetica-Bold", 9.5, usable)
        hint = " ".join(x for x in (it["help"], f"Example: {it['example']}" if it["example"] else "") if x)
        hint_lines = simpleSplit(hint, "Helvetica-Oblique", 8, usable) if hint else []
        room(len(lines) * 12 + len(hint_lines) * 10 + h + 12)
        text(label, "Helvetica-Bold", 9.5, gap=1)
        if hint:
            text(hint, "Helvetica-Oblique", 8, grey, gap=2)
        width_ = 170 if it["kind"] in ("yesno", "choice", "date") else usable
        box(it["key"], it["kind"], left, st["y"] - h, width_, h, it["options"], it["label"])
        st["y"] -= h + 9

    def grid(it, n):
        cols, total = it["columns"], sum(c_[2] for c_ in it["columns"])
        widths = [usable * c_[2] / total for c_ in cols]
        head = max(len(simpleSplit(c_[1], "Helvetica-Bold", 7.5, w - 4)) for c_, w in zip(cols, widths))
        room(30 + head * 9 + 18 * min(it["rows"], 3))
        text(f"{n}  {it['label']}", "Helvetica-Bold", 9.5, gap=1)
        if it["help"]:
            text(it["help"], "Helvetica-Oblique", 8, grey, gap=2)

        def header():
            hh = head * 9 + 4
            c.setFillColor(light)
            c.rect(left, st["y"] - hh, usable, hh, stroke=0, fill=1)
            c.setFillColor(navy)
            x = left
            for c_, w in zip(cols, widths):
                for k, line in enumerate(simpleSplit(c_[1], "Helvetica-Bold", 7.5, w - 4)):
                    c.setFont("Helvetica-Bold", 7.5)
                    c.drawString(x + 2, st["y"] - 9 - k * 9, line)
                x += w
            c.setFillColor(black)
            st["y"] -= hh + 2
        header()
        for i in range(1, it["rows"] + 1):
            if st["y"] - 18 < bottom:
                new_page()
                header()
            x = left
            for c_, w in zip(cols, widths):
                box(f"t__{it['name']}__{i}__{c_[0]}", "text", x, st["y"] - 16, w - 2, 16, tip=f"{it['label']}: {c_[1]}, row {i}")
                x += w
            st["y"] -= 18
        st["y"] -= 8

    def card(role):
        boxes = person_boxes(role)
        name = PERSON_TITLE.get(role) or (f"Child {role[5:]}" if role.startswith("child") else f"Brother or sister {role[7:]}")
        need = 16 + 4 * 30
        room(need)
        c.setFillColor(light)
        c.rect(left, st["y"] - 14, usable, 14, stroke=0, fill=1)
        c.setFillColor(navy)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left + 4, st["y"] - 10, name)
        c.setFillColor(black)
        st["y"] -= 18
        rows_ = [["FamilyName", "GivenNames"] + (["Relationship"] if "Relationship" in boxes else []), ["DOB", "COB", "MaritalStatus"], ["Occupation", "Accompanying"], ["Address"]]
        for row in rows_:
            w = usable / len(row)
            for k, b in enumerate(row):
                x = left + k * w
                c.setFont("Helvetica", 7)
                c.setFillColor(grey)
                c.drawString(x + 1, st["y"] - 7, BOX_LABEL[b])
                c.setFillColor(black)
                kind = "yesno" if b == "Accompanying" else "choice" if b == "MaritalStatus" else "text"
                opts = ["Single", "Married", "Common-law", "Widowed", "Divorced", "Legally separated", "Annulled marriage"] if b == "MaritalStatus" else None
                box(f"p__{role}__{b}", kind, x, st["y"] - 25, w - 4, 16, opts, f"{name}: {BOX_LABEL[b]}")
            st["y"] -= 29
        st["y"] -= 6

    # cover page
    c.setFillColor(navy)
    c.rect(0, height - 150, width, 150, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(left, height - 72, "Client questionnaire")
    c.setFont("Helvetica", 14)
    c.drawString(left, height - 96, title)
    c.setFont("Helvetica", 10)
    c.drawString(left, height - 122, (f"Prepared for: {person}" if person else "") + (f"     Your consultant: {firm}" if firm else ""))
    c.setFillColor(black)
    st["y"] = height - 180
    text("Thank you for choosing us. This questionnaire collects what we need to prepare your application accurately. "
         "Please read these instructions before you start.", size=10.5, gap=8)
    for head, body in (
            ("How to fill it", "Open it in Adobe Acrobat Reader (free), not in a web browser, so your answers are saved. Type in the boxes; "
             "choose from the lists where shown. Save the file often."),
            ("Answer every question", "Write None or N/A where something doesn't apply, so we know you didn't skip it. Use YYYY-MM-DD for dates."),
            ("Be complete and truthful", "List every family member and every earlier refusal, even if it seems unimportant. Leaving something out "
             "can lead to a refusal and a 5-year ban from applying (Immigration and Refugee Protection Act, s.40)."),
            ("No identity numbers", "Do not type passport, national ID or other identity numbers. We take them from copies of your documents."),
            ("Not sure?", "Answer what you can and add a note. We will go through it with you."),
            ("Time needed", "About 45 to 60 minutes. You can save and continue later."),
            ("When you finish", "Give your consent and declaration on the last page, save the file, and send it back to us by the secure method we gave you, "
             "with the documents listed in the checklist section.")):
        text(head, "Helvetica-Bold", 10, navy, gap=1)
        text(body, size=9.5, gap=6)
    text("What this questionnaire covers", "Helvetica-Bold", 10, navy, gap=2)
    secs = sections(program)
    for i, (t, _, _) in enumerate(secs + [("Documents to send", "", []), ("Consent and declaration", "", [])], 1):
        text(f"{i}.  {t}", size=9.5, gap=0, indent=12)
    c.acroForm.textfield(name="form_person", value=person or "", x=left, y=2, width=1, height=1, maxlen=200, fieldFlags="readOnly", annotationFlags="hidden", borderWidth=0, forceBorder=False)
    c.acroForm.textfield(name="form_version", value=VERSION, x=left + 2, y=2, width=1, height=1, maxlen=5, fieldFlags="readOnly", annotationFlags="hidden", borderWidth=0, forceBorder=False)
    c.acroForm.textfield(name="form_program", value=program, x=left + 4, y=2, width=1, height=1, maxlen=40, fieldFlags="readOnly", annotationFlags="hidden", borderWidth=0, forceBorder=False)
    new_page()

    for s_no, (t, why, items) in enumerate(secs, 1):
        room(70)
        c.setFillColor(navy)
        c.rect(left, st["y"] - 20, usable, 20, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(left + 6, st["y"] - 14, f"{s_no}. {t}")
        c.setFillColor(black)
        st["y"] -= 26
        text(f"Why we ask: {why}", "Helvetica-Oblique", 8.5, grey, gap=6)
        n = 0
        for it in items:
            if it["type"] == "note":
                text(it["text"], "Helvetica-Bold" if it["bold"] else "Helvetica", 9, gap=4)
            elif it["type"] == "q":
                n += 1
                question(it, f"{s_no}.{n}")
            elif it["type"] == "table":
                n += 1
                grid(it, f"{s_no}.{n}")
            elif it["type"] == "people":
                if it["help"]:
                    text(it["help"], "Helvetica-Oblique", 8, grey, gap=4)
                for role in it["roles"]:
                    card(role)
        st["y"] -= 6

    s_no = len(secs) + 1
    docs = DOCUMENTS[program]
    room(90)
    c.setFillColor(navy)
    c.rect(left, st["y"] - 20, usable, 20, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(left + 6, st["y"] - 14, f"{s_no}. Documents to send")
    c.setFillColor(black)
    st["y"] -= 26
    text(f"Tick each document you will send with this questionnaire. This list follows IRCC's published requirements (checked {CHECKED_ON}). "
         "Your consultant will confirm the final list for your situation and country, and may ask for more.", "Helvetica-Oblique", 8.5, grey, gap=6)
    for i, d in enumerate(docs, 1):
        lines = simpleSplit(d, "Helvetica", 9, usable - 22)
        room(len(lines) * 11.5 + 6)
        c.acroForm.checkbox(name=f"d__{i}", tooltip=d[:200], x=left, y=st["y"] - 11, size=10, buttonStyle="check", borderColor=navy, fillColor=white, textColor=navy, forceBorder=True)
        c.setFont("Helvetica", 9)
        for k, line in enumerate(lines):
            c.drawString(left + 18, st["y"] - 9 - k * 11.5, line)
        st["y"] -= len(lines) * 11.5 + 5
    st["y"] -= 4
    question(q("documents_note", "Any document you cannot get, and why", "long"), f"{s_no}.{len(docs) + 1}")

    s_no += 1
    room(240)
    c.setFillColor(navy)
    c.rect(left, st["y"] - 20, usable, 20, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(left + 6, st["y"] - 14, f"{s_no}. Consent and declaration")
    c.setFillColor(black)
    st["y"] -= 28
    text((de.REPO / "templates" / "intake-form-consent.txt").read_text(encoding="utf-8").strip(), size=9, gap=6)
    for name, label in (("agree_ai_privacy", "Do you give this authorization?"),
                        ("agree_declaration", "I declare that the information I have given is truthful, complete and correct.")):
        question(q(name, label, "yesno"), f"{s_no}.{1 if name == 'agree_ai_privacy' else 2}")
    question(q("signed_name", "Your full name and today's date", example="Folake Adeyemi, 2026-11-20"), f"{s_no}.3")
    footer()
    c.save()
    de.replace_with_retry(tmp, path)


# ---- reading a returned form ----
def summary_line(cells, columns):
    parts = [cells.get(col[0], "").strip() for col in columns]
    return ", ".join(p for p in parts if p)


def person_line(p):
    name = " ".join(x for x in (p.get("GivenNames"), p.get("FamilyName")) if x)
    bits = [name, p.get("Relationship", "").lower() or None, f"born {p['DOB']}" if p.get("DOB") else None, f"in {p['COB']}" if p.get("COB") else None,
            p.get("MaritalStatus", "").lower() or None, p.get("Occupation"), p.get("Address"),
            f"accompanying: {p['Accompanying']}" if p.get("Accompanying") else None]
    return ", ".join(b for b in bits if b)


def collect(answers, program):
    """(facts {key: value}, flags [text], question list [{key, kind}]) from a returned questionnaire."""
    facts, flags, qs = {}, [], []
    for title, _, items in sections(program):
        for it in items:
            if it["type"] == "q":
                qs.append({"key": it["key"], "kind": it["kind"], "question": it["label"]})
                v = (answers.get(it["key"]) or "").strip()
                if not v or v == PICK:
                    continue
                if it["kind"] == "date":
                    iso, _ = de.parse_date(v)
                    if not iso:
                        flags.append(f"{it['label'][:60]}: not a clear date. Not imported")
                        continue
                    v = iso
                if it["kind"] == "yesno" and v not in YES_NO:
                    flags.append(f"{it['label'][:60]}: not Yes or No. Not imported")
                    continue
                group, _, part = it["key"].partition("__")
                facts[f"{group}.{part}" if group in BOX_GROUPS and part else it["key"]] = v
            elif it["type"] == "table":
                lines = []
                for i in range(1, it["rows"] + 1):
                    cells = {col[0]: (answers.get(f"t__{it['name']}__{i}__{col[0]}") or "").strip() for col in it["columns"]}
                    if any(cells.values()):
                        lines.append(summary_line(cells, it["columns"]))
                qs.append({"key": it["summary"], "kind": "table", "question": it["label"]})
                if lines and it["summary"]:
                    facts[it["summary"]] = "; ".join(lines)
            elif it["type"] == "people":
                for role in it["roles"]:
                    person = {b: (answers.get(f"p__{role}__{b}") or "").strip() for b in person_boxes(role)}
                    person = {b: v for b, v in person.items() if v and v != PICK}
                    if not person:
                        continue
                    if "DOB" in person:
                        iso, _ = de.parse_date(person["DOB"])
                        if iso:
                            person["DOB"] = iso
                        else:
                            flags.append(f"{role}: date of birth not clear. Kept as written")
                    for b, v in person.items():
                        facts[f"family.{role}.{b}"] = v
    # one-line answers for worksheets that take a single answer
    fam = {}
    for k, v in facts.items():
        if k.startswith("family."):
            _, role, b = k.split(".")
            fam.setdefault(role, {})[b] = v
    for role, key in (("spouse", "spouse_details"), ("mother", "mother_details"), ("father", "father_details")):
        if role in fam:
            facts[key] = person_line(fam[role])
            if fam[role].get("Accompanying"):
                facts[f"{role}_accompanying"] = fam[role]["Accompanying"]
    if "mother" in fam:
        facts["parent1_details"] = facts["mother_details"]
    if "father" in fam:
        facts["parent2_details"] = facts["father_details"]
    for kind, key, flag in (("child", "children_details", "has_children"), ("sibling", "siblings_details", "has_siblings")):
        rows = [person_line(fam[r]) for r in sorted(fam) if r.startswith(kind)]
        if rows:
            facts[key] = "; ".join(f"{i}) {r}" for i, r in enumerate(rows, 1))
            if facts.get(flag) == "No":
                flags.insert(0, f"URGENT: {key.split('_')[0]} listed, but the answer to '{flag.replace('_', ' ')}' is No. Check with the client")
        elif facts.get(flag) == "No":
            facts[key] = "None"
        elif facts.get(flag) == "Yes":
            flags.insert(0, f"URGENT: the client has {'children' if kind == 'child' else 'brothers or sisters'} but listed none. All must be declared (IRPR 117(9)(d); IRPA s.40)")
    if "spouse_details" in facts and facts.get("marital_status") in ("Married", "Common-law"):
        facts.setdefault("spouse_name", " ".join(x for x in (fam["spouse"].get("GivenNames"), fam["spouse"].get("FamilyName")) if x))
    parts = [facts.get(f"mailing_address.{p}") for p in ("AptUnit", "StreetNum", "StreetName", "CityTown", "District", "PostalCode", "Country")]
    if any(parts):
        facts["mailing_address"] = ", ".join(p for p in parts if p)
        if facts.get("residential_same") == "Yes":
            facts.setdefault("residential_address", facts["mailing_address"])
        facts.setdefault("present_address", facts.get("residential_address") or facts["mailing_address"])
    contact_parts = [facts.get(f"contacts_in_canada.{p}") for p in ("Name", "Relationship", "Address")]
    if any(contact_parts):
        facts["contacts_in_canada"] = ", ".join(p for p in contact_parts if p)
    if "occupation" in facts:
        facts.setdefault("current_occupation", facts["occupation"])
    if "employment_history" in facts:
        facts.setdefault("personal_history", facts["employment_history"])
    if "previous_applications" in facts:
        facts.setdefault("tr_previous_application", "Yes")
    if facts.get("previous_relationship") is None and facts.get("marital_status") == "Single":
        facts["previous_relationship"] = "No"
    ticked = [d for i, d in enumerate(DOCUMENTS[program], 1) if str(answers.get(f"d__{i}", "")).strip().lower() in ("yes", "on", "1", "/yes", "true")]
    if ticked:
        facts["documents_will_send"] = "; ".join(ticked)
    if answers.get("documents_note"):
        facts["documents_note"] = answers["documents_note"].strip()
    return facts, flags, qs


def describe(program):
    """A short count of what a program's questionnaire contains."""
    secs = sections(program)
    n_q = sum(1 for _, _, items in secs for it in items if it["type"] == "q")
    n_t = sum(1 for _, _, items in secs for it in items if it["type"] == "table")
    return f"{len(secs) + 2} sections, {n_q} questions, {n_t} tables, 11 family cards, {len(DOCUMENTS[program])} documents in the checklist"
