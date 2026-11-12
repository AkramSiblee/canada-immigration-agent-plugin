#!/usr/bin/env python3
"""Final form check: the finished IRCC forms in a case's 05-forms-submissions, as they stand after editing in Adobe.

  check CASE [--person NAME]

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


def finals(folder):
    """{form number: (path, raw values)} for the newest PDF of each IRCC form in 05-forms-submissions (subfolders skipped)."""
    import pypdf
    out = {}
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
        out[number] = (path, values)  # newest wins
    return out


def answers_of(number, values):
    return {f["field"]: f for f in de.form_answers(values, number)}


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
        out.append(item("MUST", f"IMM {number}", "Blank", r["question"][:110]))
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


def across(found):
    """The same core answers on every form, and the extractor's own cross-checks."""
    out, seen = [], {}
    for number, (path, values, got) in found.items():
        for key in ("family_name", "given_name", "date_of_birth", "marital_status"):
            if key in got:
                seen.setdefault(key, {})[f"IMM {number}"] = got[key]["value"]
    for key, by_form in seen.items():
        if len({de.squash(v) for v in by_form.values()}) > 1:
            out.append(item("MUST", ", ".join(by_form), "Across", f"{key.replace('_', ' ')} differs: " + "; ".join(f"{f} '{v}'" for f, v in by_form.items())))
    docs = []
    for number, (path, values, got) in found.items():
        docs.append({"file": path.name, "doc_type": "imm_form", "status": "ok", "detail": "", "sha256": "", "needs_vision": [],
                     "fields": [de.field("form_number", f"IMM {number}" if number.isdigit() else number, 0, "form")] + list(got.values())})
    for f in de.cross_check(docs):
        if f["rule"] in ("form_version_unknown", "duplicate"):
            continue
        out.append(item("MUST" if f["severity"] == "HIGH" else "URGENT" if f["severity"] == "MEDIUM" else "TODO", ", ".join(f["files"]) or "forms", "Across", f["message"][:240]))
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
        if not planned:
            out.append(item("TODO", f"IMM {number}", "Edited", f"{rows[key]['question'][:70]}: typed on the form ('{str(f['value'])[:50]}'), not in the worksheet"))
        elif de.squash(planned) != de.squash(f["value"]) and not same_content(planned, f["value"]) and not af.matches(str(f["value"]), str(planned)):
            out.append(item("TODO", f"IMM {number}", "Edited", f"{rows[key]['question'][:70]}: form says '{str(f['value'])[:40]}', worksheet '{planned[:40]}'"))
    return out


def check(folder, person):
    """(items, forms checked) for a case."""
    found = {}
    for number, (path, values) in finals(folder).items():
        found[number] = (path, values, answers_of(number, values))
    report = fp.latest_report(folder / "03-documents" / "_extraction")
    docs = json.loads(report.read_text(encoding="utf-8")).get("documents", []) if report else []
    items = []
    for number, (path, values, got) in sorted(found.items()):
        items += blanks(number, got) + details_boxes(number, got, values) + family_rows(number, values) + logic(number, got, values) + edited(number, got, folder, person)
    items += across(found) + documents(found, docs)
    if found:
        items.append(item("TODO", ", ".join(f"IMM {n}" for n in sorted(found)), "Sign", "Signatures and dates are not checked here: validate each form in Adobe, then sign and date it"))
    return items, {n: p.name for n, (p, _, _) in found.items()}


ORDER = {"MUST": 0, "URGENT": 1, "TODO": 2, "OK": 3}
LABEL = {"MUST": "Must fix", "URGENT": "Check", "TODO": "Confirm", "OK": "OK"}


def cmd_check(a):
    folder = de.active_case(a.case)
    person = a.person or cs.read_case(folder).get("client", "")
    items, forms = check(folder, person)
    if not forms:
        sys.exit("No finished IRCC forms found in 05-forms-submissions")
    print("Final forms checked: " + "; ".join(f"IMM {n}: {name}" for n, name in sorted(forms.items())))
    for it in sorted(items, key=lambda x: (ORDER[x["level"]], x["form"], x["check"])):
        print(f"  [{LABEL[it['level']]}] {it['form']} | {it['check']}: {it['text']}")
    must = sum(1 for i in items if i["level"] == "MUST")
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
