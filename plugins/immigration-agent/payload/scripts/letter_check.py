#!/usr/bin/env python3
"""Check a drafted letter's facts against the case's extracted documents.

  check LETTER (--case CASE | --report REPORT)

Compares dates (by what the sentence says they are), UCI, application and passport numbers, dollar amounts,
the spelling of names, and the IRCC forms the letter mentions. A finding is a question for the consultant,
not a verdict: a letter may rightly mention something no document shows yet.
"""
import argparse
import difflib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402

# what a date is, from the words just before it (first match wins)
DATE_ROLES = [
    (r"\bborn\b|birth|\bDOB\b", ["date_of_birth"]),
    (r"married|marriage|wedding", ["marriage_date"]),
    (r"common.?law|cohabit|living together|moved in", ["cohabitation_from", "marriage_date"]),
    (r"permanent resident|landed|landing|\bPR\b", ["pr_date"]),
    (r"expir|valid until|valid to", ["expiry_date"]),
    (r"issued", ["issue_date"]),
    (r"refus|decision", ["decision_date"]),
    (r"start(?:ed)?|hired|employed since|began", ["start_date"]),
]
MONEY_WORDS = r"income|salary|earn|wage|balance|funds|savings|deposit|premium|coverage|tuition|paid|support"
MONEY_FIELDS = {"total_income", "net_income", "closing_balance", "opening_balance", "salary", "premium", "coverage_amount", "tuition",
                "stated_mni", "available_income", "large_deposit"}
NAME_FIELDS = {"full_name", "family_name", "given_name", "applicant_name"}
NUMBER_KINDS = [
    ("UCI", r"(?:UCI|client identifier|client ID)\D{0,20}(\d{4}-?\d{4}(?:-?\d{2})?)", {"uci"}),
    ("passport number", r"passport(?: no\.?| number| #)?\D{0,12}([A-Z]{1,2}\d{6,9}|\d{8,9})\b", {"passport_number", "document_number", "previous_document_number"}),
    ("application number", r"(?:application|file)(?: no\.?| number| #)\D{0,12}([A-Z]{1,2}\d{6,12})", {"application_number"}),
]


def letter_text(path):
    p = pathlib.Path(path)
    if any(part.lower() == "client-ids" for part in p.resolve().parts):
        sys.exit("ERROR: client-ids folders are not opened")
    ext = p.suffix.lower()
    try:
        if ext == ".docx":
            pages = de.read_docx(p)
        elif ext == ".pdf":
            pages = de.read_pdf(p, 50)[0]
        elif ext in (".txt", ".md"):
            pages = de.read_text(p)
        else:
            sys.exit(f"ERROR: {p.name}: use a .docx, .pdf or .txt letter")
    except de.Skip as e:
        sys.exit(f"ERROR: {p.name} can't be read ({e})")
    return re.sub(r"[ \t]+", " ", "\n".join(t for _, t in pages))


def collect(docs):
    """Facts from the extraction: dates by field, number fingerprints, amounts, name words, form numbers."""
    dates, hashes, plain, amounts, names, forms = {}, {}, {}, [], {}, set()
    for d in docs:
        for f in d.get("fields", []):
            key, value = f["field"], str(f.get("value", ""))
            if f.get("value_hash"):
                hashes.setdefault(key, {})[f["value_hash"]] = value
            elif key == "application_number":
                plain.setdefault(key, {})[re.sub(r"[\s-]", "", value).upper()] = value
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                dates.setdefault(key, {}).setdefault(value, set()).add(d["file"])
            if key in MONEY_FIELDS or key.startswith("available_"):
                a = de.amount(value)
                if a is not None:
                    amounts.append((a, key, d["file"]))
            if key in NAME_FIELDS:
                for w in re.findall(r"[A-Za-zÀ-ÿ'-]{3,}", value):
                    names[w.upper()] = value
            if key == "form_number":
                forms.add(value.upper().replace(" ", ""))
    return dates, hashes, plain, amounts, names, forms


def check(text, docs):
    """[(severity, message)]; severity HIGH, MEDIUM or LOW."""
    dates, hashes, plain, amounts, names, forms = collect(docs)
    out = []
    flat = re.sub(r"\s+", " ", text)
    for m in re.finditer(de.DATE_RX, flat, re.I):
        iso, _ = de.parse_date(m.group(0))
        if not iso:
            continue
        before = flat[max(0, m.start() - 70):m.start()]
        for rx, keys in DATE_ROLES:
            if re.search(rx, before, re.I):
                known = {v: files for k in keys for v, files in dates.get(k, {}).items()}
                if known and iso not in known:
                    shown = "; ".join(f"{v} ({', '.join(sorted(files))[:60]})" for v, files in sorted(known.items())[:3])
                    out.append(("HIGH", f"Date {m.group(0)} after '...{before[-40:].strip()}': the documents show {shown}"))
                break
    for label, rx, keys in NUMBER_KINDS:
        for m in re.finditer(rx, flat, re.I):
            raw = m.group(1)
            if label == "application number":
                known = {k: v for key in keys for k, v in plain.get(key, {}).items()}
                if known and re.sub(r"[\s-]", "", raw).upper() not in known:
                    out.append(("HIGH", f"Application number {raw} isn't in the documents (they show {', '.join(sorted(known.values()))})"))
                continue
            known = {h: v for key in keys for h, v in hashes.get(key, {}).items()}
            if known and de.number_hash(raw) not in known:
                out.append(("HIGH", f"{label} {de.mask(raw)} doesn't match the documents ({', '.join(sorted(set(known.values())))})"))
    for m in re.finditer(rf"(?:\$|CAD\s?|C\$)\s?({de.AMOUNT_RX}|\d{{3,}})", flat):
        context = flat[max(0, m.start() - 80):m.end() + 40]
        if not re.search(MONEY_WORDS, context, re.I):
            continue
        value = de.amount(m.group(1))
        if value is None or not amounts:
            continue
        if not any(abs(value - a) < 1 for a, _, _ in amounts):
            near = min(amounts, key=lambda x: abs(x[0] - value))
            out.append(("MEDIUM", f"Amount {de.dollars(value)} isn't shown in any document (closest: {de.dollars(near[0])} {near[1].replace('_', ' ')} in {near[2]}). Check the source"))
    seen = set()
    for w in re.findall(r"\b[A-ZÀ-Ý][A-Za-zÀ-ÿ'-]{2,}\b", text):
        up = w.upper()
        if up in names or up in seen:
            continue
        close = difflib.get_close_matches(up, list(names), n=1, cutoff=0.8)
        if close and close[0][0] == up[0]:
            seen.add(up)
            out.append(("MEDIUM", f"Name '{w}' may be misspelled: the documents have {close[0].title()} ({names[close[0]]})"))
    for m in sorted(set(re.findall(r"\b(IMM|CIT)\s?(\d{4})\b", flat))):
        number = f"{m[0]}{m[1]}"
        if forms and number not in forms:
            out.append(("LOW", f"The letter mentions {m[0]} {m[1]}, which isn't among the case's documents. Attach it or check the reference"))
    return out


def report_docs(case=None, report=None):
    if report:
        path = pathlib.Path(report)
    else:
        path = fp.latest_report(de.active_case(case) / "03-documents" / "_extraction")
        if not path:
            sys.exit(f"ERROR: no extraction for {case} yet. Run doc_extract.py extract --case {case}")
    return json.loads(path.read_text(encoding="utf-8")).get("documents", [])


def cmd_check(a):
    found = check(letter_text(a.letter), report_docs(a.case, a.report))
    name = pathlib.Path(a.letter).name
    if not found:
        print(f"{name}: no conflicts found with the extracted documents. This doesn't check legal content, tone or facts no document covers.")
        return
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    print(f"{name}: {len(found)} point(s) to check")
    for sev, msg in sorted(found, key=lambda x: order[x[0]]):
        print(f"  {sev}: {msg}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Check a letter's facts against the extracted documents")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("check"); x.add_argument("letter"); g = x.add_mutually_exclusive_group(required=True)
    g.add_argument("--case"); g.add_argument("--report"); x.set_defaults(fn=cmd_check)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
