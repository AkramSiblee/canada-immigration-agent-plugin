#!/usr/bin/env python3
"""Final form check: the finished IRCC forms in a case's 05-forms-submissions, as they stand after editing in Adobe.

  check CASE [--person NAME]     each person's forms are checked separately; --person checks one person

For the newest PDF of each IRCC form it reports:
  Blank      required questions still empty (conditional ones only when their condition applies)
  Family     family table rows missing a name, date of birth, country of birth or address
  Logic      passport valid past the departure date, dates in order, a visit over 6 months, family ages,
             marriage after age 14, 10-year work history gaps
  Across     name, date of birth and marital status the same on every form, plus the extractor's cross-checks
             (children between family forms, history gaps, earlier answers changed)
  Documents  the passport number on the form matches the passport (compared by fingerprint, never shown)
  Edited     answers that differ from the worksheet, or were typed in Adobe, for a last confirmation
  Sign       signatures are never checked by this tool: a reminder

A finding is a question for the consultant. A clean result doesn't mean the application is complete.
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402
import autofill as af  # noqa: E402
import form_prefill as fp  # noqa: E402

TR = {"5257", "1294", "1295", "5710", "5708", "5709"}
TR_EXTRA = {"date_of_birth", "employment_history", "education_history", "contacts_in_canada"}
OPTIONAL = re.compile(r"\bif (yes|any|known|applicable|different|other|you have|more than one)\b|\(if |if yes|if no\b|give details if|purpose: other", re.I)
ALWAYS_OPTIONAL = {"uci", "other_name", "language_at_ease", "student_id", "caq_number", "pal_number", "visa_type", "application_type", "funds_other"}
CONDITIONS = {  # key: (other key, values that make it required)
    "spouse_name": ("marital_status", {"Married", "Common-law", "Common-Law"}),
    "marriage_date": ("marital_status", {"Married", "Common-law", "Common-Law", "Widowed"}),
    "purpose_other": ("purpose_of_visit", {"Other"}),
    "education_history": ("post_secondary", {"Yes"}),
    "tr_health_details": ("tr_tb", {"Yes"}), "tr_refusal_details": ("tr_refused", {"Yes"}), "tr_criminal_details": ("tr_criminal", {"Yes"}),
    "tr_military_details": ("tr_military", {"Yes"}),
}
VISIT_DAYS = 183
# a Yes that needs its details boxes filled (identity numbers are only checked for presence, never shown)
IF_YES_BOXES = {
    "national_id": ("national identity document", [(r"natIDdocs/DocNum/DocNum$", "number"), (r"natIDdocs/CountryofIssue/CountryofIssue$", "country of issue"),
                                                   (r"natIDdocs/IssueDate/IssueDate$", "issue date")]),
    "us_lpr": ("US green card", [(r"usCarddocs/DocNum/DocNum$", "number"), (r"usCarddocs/ExpiryDate$", "expiry date")]),
}


VERSION_RX = re.compile(r"-v(\d+)$")


def version_of(path):
    m = VERSION_RX.search(path.stem)
    return int(m.group(1)) if m else 1


def date_of_file(path):
    """The date at the start of an agent-made file name (2026-11-16-imm1295-...), else the day the file was saved."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
    return m.group(1) if m else datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def name_in_file(path):
    """The person in an agent-made file name: 2026-11-15-imm5257-abul-bashar-autofill-v2.pdf -> 'Abul Bashar'."""
    m = re.search(r"(?:imm|cit)\d{4}[a-z]?-(.+?)-(?:autofill|final|data-sheet|signed|filled)(?:-|$)", VERSION_RX.sub("", path.stem.lower()))
    return m.group(1).replace("-", " ").title() if m else ""


def form_person(got, path):
    """Whose form this is: the applicant's name on the form itself, else the name in the file name."""
    name = " ".join(x for x in (got.get("given_name", {}).get("value", ""), got.get("family_name", {}).get("value", "")) if x).strip()
    return name or name_in_file(path)


def all_finals(folder):
    """[(person, number, path, values, answers)]: the newest version (-v2, -v3 ..., then the latest saved) of each form per person."""
    import pypdf
    best = {}
    sub = folder / "05-forms-submissions"
    for path in sorted(sub.glob("*.pdf"), key=lambda p: p.stat().st_mtime) if sub.exists() else []:
        try:
            r = pypdf.PdfReader(str(path), strict=False)
            if r.is_encrypted:
                r.decrypt("")
            values = de.read_form(r)
        except Exception:
            continue
        if not values:
            continue
        label, _ = de.form_number(values, [], path.name)
        if not label:
            continue
        number = label.split()[1] if label.startswith("IMM") else label.replace(" ", "")
        got = answers_of(number, values)
        person = form_person(got, path)
        same = next((k for k in best if k[1] == number and ((not k[0] and not person) or (k[0] and person and de.same_person(k[0], person)))), None)
        key = same or (person, number)
        rank = (date_of_file(path), version_of(path), path.stat().st_mtime)  # newest date first, then -v2, -v3 on that date
        if key not in best or rank >= best[key][0]:
            best[key] = (rank, (person or key[0], number, path, values, got))
    return [v for _, v in best.values()]


def group_people(entries, client=""):
    """{person: {number: (path, values, answers)}}, people matched loosely by name; forms with no name go to the client."""
    groups = {}
    for person, number, path, values, got in entries:
        who = person or client or "Unnamed"
        key = next((k for k in groups if de.same_person(k, who)), who)
        groups.setdefault(key, {})[number] = (path, values, got)
    return groups


def finals(folder, person=None):
    """{form number: (path, raw values)} for one person's newest forms (every form when no person is given)."""
    out = {}
    for who, number, path, values, _ in all_finals(folder):
        if person and who and not de.same_person(person, who):
            continue
        out[number] = (path, values)
    return out


def answers_of(number, values):
    return {f["field"]: f for f in de.form_answers(values, number)}


def children_on(number, values):
    """[{name, dob}] for each child row on a family form."""
    return [f["person"] for f in de.form_answers(values, number) if f["field"] == "child" and f.get("person", {}).get("name")]


def producible(number):
    maps, joins = de.form_maps(number)
    keys = {m[0] for m in maps} | {j[0] for j in joins}
    if number in TR:
        keys |= TR_EXTRA
    return keys


def spec_name(number):
    return f"imm{number}" if number.isdigit() else number.lower()


def item(level, form, check, text):
    return {"level": level, "form": form, "check": check, "text": text}


def blanks(number, got):
    """Required questions the form can hold but that are still empty."""
    out = []
    try:
        _, spec = fp.load_spec(spec_name(number))
    except SystemExit:
        return out
    can = producible(number)
    answers = {k: f["value"] for k, f in got.items()}
    for r in spec:
        key = r["key"]
        if r["rule"] in ("sign", "consultant") or key not in can or key in got or key in ALWAYS_OPTIONAL:
            continue
        if key in CONDITIONS:
            other, values = CONDITIONS[key]
            if answers.get(other) not in values:
                continue
        elif OPTIONAL.search(r["question"] + " " + r["help"]):
            continue
        out.append({**item("MUST", f"IMM {number}", "Blank", r["question"][:110]), "key": key, "rule": r["rule"]})
    return out


FAMILY_ROWS = {
    "5645": (r"SectionA/(Spouse|Mother|Father)/|SectionB/Child(\[\d+\])?/|SectionC/Child(\[\d+\])?/", ("Name", "DOB", "COB", "Address")),
    "5707": (r"Section[AB]/(Spouse|Parent1|Parent2|Child(\[\d+\])?)/", ("FamilyName", "GivenNames", "DOB", "COB", "Address")),
}


def details_boxes(number, got, values):
    """A Yes whose details boxes are still empty (for example a national ID with no number)."""
    out = []
    for key, (label, boxes) in IF_YES_BOXES.items():
        if got.get(key, {}).get("value") != "Yes":
            continue
        missing = [name for rx, name in boxes if not any(re.search(rx, de.clean_path(p)) and str(v).strip() for p, v in values.items())]
        if missing:
            out.append(item("MUST", f"IMM {number}", "Blank", f"{label}: answered Yes, but the {', '.join(missing)} is empty"))
    return out


def same_content(a, b):
    """Two answers that say the same thing in a different order or format ('BGD (Bangladesh)' and 'Bangladesh')."""
    ta = set(re.findall(r"[a-z0-9]{2,}", str(a).lower()))
    tb = set(re.findall(r"[a-z0-9]{2,}", str(b).lower()))
    if not ta or not tb:
        return False
    small, large = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return len(small & large) / len(small) >= 0.75


def family_rows(number, values):
    """Family table rows that have something filled in but are missing a core detail."""
    if number not in FAMILY_ROWS:
        return []
    pattern, needed = FAMILY_ROWS[number]
    rows = {}
    for path, v in values.items():
        m = re.search(pattern, path)
        if m and v and str(v).strip():
            row = path[:m.end()]
            rows.setdefault(row, {})[re.sub(r"^(Spouse|Mother|Father|Child|App)", "", path.rsplit("/", 1)[-1])] = str(v).strip()
    out = []
    for row, cells in rows.items():
        if set(cells) <= {"No", "Yes", "MStatus", "Relationship"} or not any(k in cells for k in needed):
            continue
        missing = [k for k in needed if k not in cells and not any(c.endswith(k) for c in cells)]
        if missing:
            who = re.sub(r".*/(Section\w/)", r"\1", row).strip("/")
            out.append(item("MUST", f"IMM {number}", "Family", f"{who}: missing {', '.join(missing)}"))
    return out


def day(text):
    try:
        return datetime.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def logic(number, got, values):
    out = []
    a = {k: f["value"] for k, f in got.items()}
    f_ = f"IMM {number}"
    start, end, expiry = day(a.get("stay_from")), day(a.get("stay_to")), day(a.get("passport_expiry_date"))
    if start and end and end < start:
        out.append(item("MUST", f_, "Logic", f"Departure {end} is before arrival {start}"))
    if expiry and end and expiry < end:
        out.append(item("MUST", f_, "Logic", f"Passport expires {expiry}, before the planned departure {end}"))
    elif expiry and expiry < datetime.date.today() + datetime.timedelta(days=183):
        out.append(item("URGENT", f_, "Logic", f"Passport expires {expiry}: less than 6 months from today"))
    if start and end and (end - start).days > VISIT_DAYS and number == "5257":
        out.append(item("URGENT", f_, "Logic", f"Planned stay of {(end - start).days} days is over 6 months: the officer may limit it, or consider a super visa"))
    for a_key, b_key in (("study_from", "study_to"),):
        x, y = day(a.get(a_key)), day(a.get(b_key))
        if x and y and y < x:
            out.append(item("MUST", f_, "Logic", f"{b_key.replace('_', ' ')} {y} is before {a_key.replace('_', ' ')} {x}"))
    dob, married = day(a.get("date_of_birth")), day(a.get("marriage_date"))
    if dob and married and (married - dob).days < 14 * 365:
        out.append(item("MUST", f_, "Logic", f"Marriage date {married} is before age 14 (born {dob})"))
    if dob:
        for path, v in values.items():
            d = day(v) if re.search(r"(Child|Mother|Father|Parent[12]|Spouse)[^/]*/?.*DOB$", path) else None
            if not d:
                continue
            who = "child" if "Child" in path else "parent" if re.search(r"Mother|Father|Parent", path) else None
            if who == "child" and (d - dob).days < 12 * 365:
                out.append(item("MUST", f_, "Logic", f"A child's date of birth {d} is less than 12 years after the applicant's ({dob})"))
            if who == "parent" and (dob - d).days < 12 * 365:
                out.append(item("MUST", f_, "Logic", f"A parent's date of birth {d} is less than 12 years before the applicant's ({dob})"))
    return out


def across(found, docs=()):
    """The same core answers on every form, and the extractor's own cross-checks.
    A 'Yes' to a refusal is a 'Confirm' (not a 'Must fix') when this person's refusal letter is already in the documents."""
    letters = [d["file"] for d in docs if d.get("doc_type") == "refusal_letter"]
    out, seen = [], {}
    for number, (path, values, got) in found.items():
        for key in ("family_name", "given_name", "date_of_birth", "marital_status"):
            if key in got:
                seen.setdefault(key, {})[f"IMM {number}"] = got[key]["value"]
    for key, by_form in seen.items():
        if len({de.squash(v) for v in by_form.values()}) > 1:
            out.append(item("MUST", ", ".join(by_form), "Across", f"{key.replace('_', ' ')} differs: " + "; ".join(f"{f} '{v}'" for f, v in by_form.items())))
    form_docs = []
    for number, (path, values, got) in found.items():
        form_docs.append({"file": path.name, "doc_type": "imm_form", "status": "ok", "detail": "", "sha256": "", "needs_vision": [],
                     "fields": [de.field("form_number", f"IMM {number}" if number.isdigit() else number, 0, "form")] + list(got.values())})
    for f in de.cross_check(form_docs):
        if f["rule"] in ("form_version_unknown", "duplicate"):
            continue
        level = "MUST" if f["severity"] == "HIGH" else "URGENT" if f["severity"] == "MEDIUM" else "TODO"
        text = f["message"]
        if f["rule"] == "background_yes" and letters and re.search(r"refused a visa", text, re.I):
            level = "TODO"
            text = re.sub(r"\s*Get every refusal letter.*$", "", text) + f" Refusal letter on file: {', '.join(letters[:3])}. Confirm it covers every refusal"
        out.append(item(level, ", ".join(f["files"]) or "forms", "Across", text[:240]))
    return out


def documents(found, docs):
    """The passport number on each form against the passport read from the case's documents."""
    out = []
    passports = {f["value_hash"] for d in docs if d.get("doc_type") == "passport" for f in d.get("fields", []) if f["field"] == "passport_number" and f.get("value_hash")}
    if not passports:
        return out
    for number, (path, values, got) in found.items():
        f = got.get("passport_number")
        if f and f.get("value_hash") and f["value_hash"] not in passports:
            out.append(item("MUST", f"IMM {number}", "Documents", f"Passport number {f['value']} doesn't match the passport in 03-documents"))
        elif f and f.get("value_hash"):
            out.append(item("OK", f"IMM {number}", "Documents", f"Passport number {f['value']} matches the passport"))
    return out


# answers autofill writes from facts kept under other keys: parts (current_residence.Country), table rows (employment.1.From)
FACT_GROUPS = {"employment_history": ("employment", "employment_history"), "education_history": ("education", "education_history"),
               "previous_countries_details": ("previous_countries",), "employer_name": ("employer", "employer_name"),
               "study_address": ("study_address", "school_address"), "pal_number": ("pal", "pal_number"), "caq_number": ("caq", "caq_number"),
               "job_title": ("job", "job_title", "job_duties")}


def fact_words(text):
    """Words and numbers in an answer, with provinces and countries also under their full names (NS = Nova Scotia, BGD = Bangladesh)."""
    out = set()
    for w in re.findall(r"[A-Za-z0-9]+", str(text)):
        out.add(w.lower())
        full = af.PROVINCES.get(w.upper()) or (de.country_name(w) if len(w) == 3 and w.isupper() else None)
        if full and full != w:
            out |= {x.lower() for x in re.findall(r"[A-Za-z0-9]+", full)}
    return out


def from_facts(key, value, client):
    """True when every word of the form's answer is in the client's current facts for that question (whole, parts or rows)."""
    prefixes = FACT_GROUPS.get(key, (key,))
    texts = [c["value"] for k, entries in client.items() for c in entries
             if k == key or any(k == pre or k.startswith(pre + ".") for pre in prefixes)]
    if not texts:
        return False
    have = set().union(*(fact_words(t) for t in texts))
    stated = [w for w in re.findall(r"[A-Za-z0-9]+", str(value)) if not re.fullmatch(r"\d{1,2}", w)]  # skip "01" month boxes etc.

    def known(w):  # the word itself, or the full name of a code (NS = Nova Scotia, BGD = Bangladesh)
        full = fact_words(w) - {w.lower()}
        return w.lower() in have or bool(full) and full <= have
    return bool(stated) and all(known(w) for w in stated)


def edited(number, got, folder, person):
    """Answers that differ from the worksheet, or were added in Adobe."""
    out = []
    try:
        _, spec = fp.load_spec(spec_name(number))
    except SystemExit:
        return out
    report = fp.latest_report(folder / "03-documents" / "_extraction")
    pool = fp.facts_from_report(json.loads(report.read_text(encoding="utf-8")), person)[0] if report else {}
    client = fp.facts_from_file(folder / "client-facts.csv", person)
    rows = {q["key"]: r for q, r in zip(spec, fp.build_rows(spec, pool, client))}
    for key, f in got.items():
        if key not in rows or f.get("sensitive"):
            continue
        planned = rows[key]["answer"]
        if from_facts(key, f["value"], client):
            continue  # what autofill wrote from the current client facts (parts, rows, codes): not an edit
        if not planned:
            out.append(item("TODO", f"IMM {number}", "Edited", f"{rows[key]['question'][:70]}: typed on the form ('{str(f['value'])[:50]}'), not in the worksheet"))
        elif de.squash(planned) != de.squash(f["value"]) and not same_content(planned, f["value"]) and not af.matches(str(f["value"]), str(planned)):
            out.append(item("TODO", f"IMM {number}", "Edited", f"{rows[key]['question'][:70]}: form says '{str(f['value'])[:40]}', worksheet '{planned[:40]}'"))
    return out


def check_forms(found, folder, person, docs):
    items = []
    for number, (path, values, got) in sorted(found.items()):
        items += blanks(number, got) + details_boxes(number, got, values) + family_rows(number, values) + logic(number, got, values) + edited(number, got, folder, person)
    items += across(found, docs) + documents(found, docs)
    if found:
        items.append(item("TODO", ", ".join(f"IMM {n}" for n in sorted(found)), "Sign", "Signatures and dates are not checked here: validate each form in Adobe, then sign and date it"))
    return items


def case_docs(folder):
    report = fp.latest_report(folder / "03-documents" / "_extraction")
    return json.loads(report.read_text(encoding="utf-8")).get("documents", []) if report else []


def own_docs(docs, person):
    """The case's documents that belong to this person (or name nobody)."""
    return [d for d in docs if not de.doc_name(d) or de.same_person(person, de.doc_name(d))]


def check(folder, person):
    """(items, forms checked) for one person's forms in a case."""
    groups = group_people(all_finals(folder), person)
    key = next((k for k in groups if person and de.same_person(k, person)), None)
    found = groups.get(key, {}) if key else (next(iter(groups.values())) if len(groups) == 1 and not person else {})
    return check_forms(found, folder, person, own_docs(case_docs(folder), person) if person else case_docs(folder)), {n: p.name for n, (p, _, _) in found.items()}


def first_value(found, key):
    return next((g[key]["value"] for _, _, g in found.values() if g.get(key, {}).get("value")), "")


def spouse_of(found):
    return first_value(found, "spouse_name") or first_value(found, "spouse_details").split(" | ")[0]


def between_people(groups, principal):
    """Across people: the spouse named on each form against the spouse's own forms, and children on the family forms."""
    out = []
    listed = []
    for who, found in groups.items():
        spouse = spouse_of(found)
        other = next((k for k in groups if k != who and spouse and de.same_person(k, spouse)), None)
        if other:
            back = spouse_of(groups[other])
            if back and not de.same_person(back, who):
                out.append(item("MUST", f"{who} / {other}", "People", f"{who}'s forms name {spouse} as spouse, but {other}'s forms name '{back}'"))
            else:
                out.append(item("OK", f"{who} / {other}", "People", f"Spouse {spouse} matches their own forms"))
        for number, (path, values, got) in found.items():
            for child in children_on(number, values):
                listed.append(child["name"])
                kid = next((k for k in groups if k != who and de.same_person(k, child["name"])), None)
                dob = first_value(groups[kid], "date_of_birth") if kid else ""
                if kid and dob and child["dob"] and dob != child["dob"]:
                    out.append(item("MUST", f"IMM {number} / {kid}", "People", f"{who}'s IMM {number} gives {child['name']}'s date of birth as {child['dob']}, {kid}'s own forms say {dob}"))
                elif kid:
                    out.append(item("OK", f"IMM {number} / {kid}", "People", f"Child {child['name']} matches their own forms"))
    named = listed + [spouse_of(f) for f in groups.values()]
    for who in groups:
        if principal and de.same_person(who, principal):
            continue
        if not any(n and de.same_person(who, n) for n in named):
            out.append(item("URGENT", who, "People", f"{who} has forms in this file but isn't named as a spouse or child on any family form"))
    unique = {}
    for it in out:  # both parents' family forms list the same children
        unique.setdefault((it["level"], it["text"]), it)
    return list(unique.values())


ORDER = {"MUST": 0, "URGENT": 1, "TODO": 2, "OK": 3}
LABEL = {"MUST": "Must fix", "URGENT": "Check", "TODO": "Confirm", "OK": "OK"}


def show(items):
    for it in sorted(items, key=lambda x: (ORDER[x["level"]], x["form"], x["check"])):
        print(f"  [{LABEL[it['level']]}] {it['form']} | {it['check']}: {it['text']}")


def cmd_check(a):
    folder = de.active_case(a.case)
    client = cs.read_case(folder).get("client", "")
    if a.person:
        items, forms = check(folder, a.person)
        if not forms:
            sys.exit(f"No finished IRCC forms for {a.person} found in 05-forms-submissions")
        print(f"Final forms checked for {a.person}: " + "; ".join(f"IMM {n}: {name}" for n, name in sorted(forms.items())))
        show(items)
        must = sum(1 for i in items if i["level"] == "MUST")
    else:
        groups = group_people(all_finals(folder), client)
        if not groups:
            sys.exit("No finished IRCC forms found in 05-forms-submissions")
        docs, must = case_docs(folder), 0
        for who, found in sorted(groups.items(), key=lambda kv: (not (client and de.same_person(kv[0], client)), kv[0])):
            items = check_forms(found, folder, who, own_docs(docs, who))
            print(f"{who}: forms checked " + "; ".join(f"IMM {n}: {p.name}" for n, (p, _, _) in sorted(found.items())))
            show(items)
            must += sum(1 for i in items if i["level"] == "MUST")
        if len(groups) > 1:
            items = between_people(groups, client)
            print("Across people:")
            show(items)
            must += sum(1 for i in items if i["level"] == "MUST")
    print(f"{must} must-fix item(s)." + (" Not ready to submit." if must else " No blocking items found; your own final review is still needed."))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Check the finished IRCC forms before submitting")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("check"); x.add_argument("case"); x.add_argument("--person"); x.set_defaults(fn=cmd_check)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
