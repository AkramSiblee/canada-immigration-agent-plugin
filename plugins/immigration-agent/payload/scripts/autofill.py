#!/usr/bin/env python3
"""Autofill an IRCC form's official PDF with the worksheet answers that are ready.

  fetch --form imm5257                        download the current blank form from IRCC into forms-cache/
  fill --form imm5257 --person "Name" (--case CASE | --report REPORT [--facts FACTS.csv])
       [--blank BLANK.pdf] [--include-confirm] [--out FILE]

Only answers the worksheet marks "Ready" (and firm-profile details) are written; with --include-confirm,
answers read from images ("please confirm") too. Conflicts, open questions, masked numbers, joined fields
(addresses) and signatures are left blank for you. Each answer goes to the one field the extractor reads it
from, and the filled form is read back to prove every answer landed on the right question.

The result is a draft. Open it in Adobe Acrobat or Reader, check every page, complete the blanks, click
Validate to make the barcodes, and sign. Nothing is sent anywhere.
"""
import argparse
import datetime
import io
import json
import pathlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402
import doc_extract as de  # noqa: E402
import form_prefill as fp  # noqa: E402
import pdf_studio as ps  # noqa: E402

CACHE = de.REPO / "forms-cache"
SYNONYMS = {"F": ("female",), "M": ("male",), "X": ("another gender", "unknown", "other")}
FILL = {fp.READY, fp.FROM_FIRM}
XFA_DATA = "http://www.xfa.org/schema/xfa-data/1.0/"
tag = lambda e: e.tag.split("}")[-1]  # noqa: E731


def number_of(form):
    f = form.lower()
    return f[3:] if f.startswith("imm") else f.upper()


# ---- the blank form ----
def fetch(form):
    """The current blank from IRCC's form page, cached in forms-cache/<form>-<version>.pdf."""
    info = next((r for r in fp.load_csv(fp.SPECS / "index.csv") if r["form"] == form), None)
    if not info:
        sys.exit(f"ERROR: no worksheet for {form}. Known: " + ", ".join(r["form"] for r in fp.load_csv(fp.SPECS / "index.csv")))
    CACHE.mkdir(exist_ok=True)
    target = CACHE / f"{form}-{info['version_code']}.pdf"
    if target.exists():
        problem = blank_problem(target)
        if not problem:
            return target
        print(f"Note: the saved blank {target.name} {problem}; downloading it again.")
        target.unlink()
    m = None
    standard = f"https://www.canada.ca/en/immigration-refugees-citizenship/services/application/application-forms-guides/{form}.html"
    for source in dict.fromkeys((info["source_url"], standard)):  # IRCC moves pages: its standard form page is the fallback
        page = download(source).decode("utf-8", "replace")
        m = re.search(rf'href="([^"]*{re.escape(form)}e?\.pdf)"', page, re.I)
        if m:
            break
    if not m:
        sys.exit(f"ERROR: no PDF link found on {info['source_url']}. Download the form yourself and pass --blank")
    url = m.group(1) if m.group(1).startswith("http") else "https://www.canada.ca" + m.group(1)
    data = download(url)
    part = target.with_name(target.name + ".part")
    part.write_bytes(data)  # checked before it becomes the cached blank, so a cut-off download is never reused
    problem = blank_problem(part)
    if problem:
        part.unlink()
        sys.exit(f"ERROR: the form downloaded from {url} {problem}. Download it yourself in Adobe and pass --blank")
    part.replace(target)
    return target


def download(url):
    """IRCC's pages, with curl when available (canada.ca can stall other clients), else urllib."""
    import shutil
    import subprocess
    curl = shutil.which("curl")
    try:
        if curl:
            r = subprocess.run([curl, "-sSL", "--max-time", "180", "-A", "Mozilla/5.0", url], capture_output=True, timeout=200)
            if r.returncode == 0 and r.stdout:
                return r.stdout
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
        return urllib.request.urlopen(req, timeout=120).read()
    except Exception as e:
        sys.exit(f"ERROR: couldn't download {url} ({type(e).__name__}). Download the form yourself and pass --blank")


def xfa_parts(reader):
    acro = reader.trailer["/Root"].get("/AcroForm")
    xfa = acro.get_object().get("/XFA") if acro else None
    if xfa is None:
        sys.exit("ERROR: this PDF has no XFA form data: it isn't one of IRCC's fillable forms")
    items = list(xfa.get_object())
    return {str(items[i]): items[i + 1].get_object() for i in range(0, len(items) - 1, 2)}


def template_fields(template):
    """Every place the form stores an answer: data path (as the extractor sees it) -> 'field' or 'group'."""
    root = ET.fromstring(template)
    top = next((k for k in root.iter() if tag(k) == "subform" and k.get("name")), None)
    out = {}

    def items(node):
        for k in node:
            t = tag(k)
            if t in ("subform", "subformSet", "area") and not k.get("name"):
                yield from items(k)
            elif t in ("subform", "field", "exclGroup") and k.get("name"):
                yield k

    def walk(node, path):
        kids = list(items(node))
        names = [k.get("name") for k in kids]
        seen = {}
        for k in kids:
            n = k.get("name")
            i = seen.get(n, 0)
            seen[n] = i + 1
            here = f"{path}/{n}" + (f"[{i}]" if names.count(n) > 1 else "")
            bind = next((b for b in k if tag(b) == "bind"), None)
            if bind is not None and bind.get("match") in ("none", "global", "dataRef"):
                continue  # not stored under its own name
            if tag(k) == "subform":
                walk(k, here)
            else:
                ui = next((u for u in k if tag(u) == "ui"), None)
                kind = tag(list(ui)[0]) if ui is not None and len(ui) else ""
                if kind not in ("button", "barcode", "signature"):
                    out[here] = "group" if tag(k) == "exclGroup" else "field"
    if top is not None:
        walk(top, f"/data/{top.get('name')}")
    return out


def find_path(paths, rx, exclude=None):
    by_position = "\\[" in rx
    for p in paths:
        q = p if by_position else de.clean_path(p)
        if re.search(rx, q) and not (exclude and re.search(exclude, q, re.I)):
            return p
    return None


# ---- answers to stored values ----
def encode(value, how, path, lists):
    """(stored value, None) or (None, why not)."""
    v = str(value).strip()
    codes = {}
    for m in lists:
        for code, label in m.items():
            codes.setdefault(label.strip().lower(), code)
    if how == "yn":
        v = {"yes": "Yes", "no": "No", "y": "Yes", "n": "No"}.get(v.strip(" .").lower(), v)  # YES, no. -> Yes, No; anything longer is left for you
        if v not in ("Yes", "No"):
            return None, f"'{v}' isn't Yes or No"
        if codes:
            code = codes.get(v.lower())
            return (code, None) if code else (None, "the form's Yes/No codes weren't found")
        return None, "the form's Yes/No codes weren't found"
    if isinstance(how, dict):
        options = [c for c, label in how.items() if label == v]
        if not options:
            return None, f"'{v}' isn't one of this question's options"
        known = {c for m in lists for c in m}
        return next((c for c in options if c in known), options[0]), None
    if how == "cm":
        v = re.sub(r"\s*cm$", "", v)
    if how == "date":
        iso, _ = de.parse_date(v)
        if not iso:
            return None, f"'{v}' isn't a full date"
        v = iso
    if codes:  # a list on the form: store its code
        code = codes.get(v.lower()) or codes.get(de.country_name(v).lower())  # a passport code like PRT
        for alt in SYNONYMS.get(v.upper(), ()):  # passports print F, M or X
            code = code or codes.get(alt)
        if not code:  # labels like "F Female": the leading code or the rest of the label, if only one label fits
            fits = {c for label, c in codes.items() if v.lower() in (label.split(" ", 1)[0], label.split(" ", 1)[-1].strip("()"))}
            code = fits.pop() if len(fits) == 1 else None
        if not code:  # labels like "BGD (Bangladesh)": the name in brackets, or a passport code
            name = de.country_name(v).lower()
            fits = {c for label, c in codes.items() if label.split(" ", 1)[-1].strip("()") in (v.lower(), name)}
            code = fits.pop() if len(fits) == 1 else None
        if not code:  # "Bangladeshi" for "Bangladesh": the answer starts with exactly one label and adds at most 3 letters
            fits = {c for label, c in codes.items() if len(label) >= 4 and v.lower().startswith(label) and len(v) - len(label) <= 3}
            code = fits.pop() if len(fits) == 1 else None
        return (code, None) if code else (None, f"'{v}' isn't in the form's list: choose it in Adobe")
    return v, None


# Answers made of several boxes, given part by part (client-facts keys like "contacts_in_canada.Name").
# Patterns name the box on the temporary residence forms; a part with no matching box is reported, never guessed.
BOXES = {
    "current_residence": {"Country": r"CurrentCOR/(?:.*/)?Row\d*/Country$", "Status": r"CurrentCOR/(?:.*/)?Row\d*/Status$",
                          "FromDate": r"CurrentCOR/(?:.*/)?Row\d*/FromDate$", "ToDate": r"CurrentCOR/(?:.*/)?Row\d*/ToDate$"},
    "mailing_address": {"POBox": r"contact/AddressRow1/POBox/POBox$", "AptUnit": r"contact/AddressRow1/Apt/AptUnit$",
                        "StreetNum": r"contact/AddressRow1/StreetNum/StreetNum$", "StreetName": r"contact/AddressRow1/Streetname/Streetname$",
                        "CityTown": r"contact/AddressRow2/(?:CityTow|CityTown)/CityTown$", "Country": r"contact/AddressRow2/Country/Country$",
                        "ProvinceState": r"contact/AddressRow2/ProvinceState/ProvinceState$", "PostalCode": r"contact/AddressRow2/PostalCode/PostalCode$",
                        "District": r"contact/AddressRow2/District$"},
    "contacts_in_canada": {"Name": r"Contacts_Row1/Name/Name$", "Relationship": r"Contacts_Row1/(?:RelationshipToMe|Relationship)/RelationshipToMe$",
                           "Address": r"Contacts_Row1/AddressInCanada/AddressInCanada$"},
}
# Family tables (IMM 5645, IMM 5707), given person by person: client-facts keys like "family.child1.GivenNames".
# People: applicant, spouse, mother, father, child1-child9, sibling1-sibling9. Boxes: FamilyName, GivenNames, NativeName, DOB, COB,
# Address, Occupation, MaritalStatus, Relationship, Accompanying (Yes/No), MarriageInPerson (Yes/No). A box the form doesn't have is skipped.
COVERED_BY_FAMILY = {"family_name", "given_name", "date_of_birth", "birth_country", "present_address", "occupation", "marital_status",
                     "spouse_details", "spouse_accompanying", "mother_details", "mother_accompanying", "father_details", "father_accompanying",
                     "parent1_details", "parent2_details", "children_details", "siblings_details", "name_native_script",
                     "present_at_marriage", "spouse_present_at_marriage"}


def family_people(client):
    people = {}
    for key, entries in client.items():
        parts = key.split(".")
        if len(parts) == 3 and parts[0] == "family":
            values = {e["value"] for e in entries if e.get("value")}
            if len(values) == 1:
                people.setdefault(parts[1], {})[parts[2]] = values.pop()
    return people


def family_paths(number, role, box, value):
    """[(data path, value to store as a label)] for one person's box on IMM 5645 or IMM 5707, or [] if the form has no such box."""
    kind = re.sub(r"\d+$", "", role)
    n = int(re.sub(r"\D", "", role) or 1) - 1
    if number == "5645":
        base = {"applicant": "SectionA/Applicant", "spouse": "SectionA/Spouse", "mother": "SectionA/Mother", "father": "SectionA/Father",
                "child": f"SectionB/Child[{n}]", "sibling": f"SectionC/Child[{n}]"}.get(kind)
        stem = {"applicant": "App", "spouse": "Spouse", "mother": "Mother", "father": "Father"}.get(kind, "Child")
        if not base:
            return []
        root = f"/data/IMM_5645/page1/{base}/"
        if box == "Name":
            return [(root + stem + "Name", value)]
        if box in ("DOB", "COB", "Address", "Occupation"):
            return [(root + stem + box, value)]
        if box == "Relationship" and kind in ("child", "sibling"):
            return [(root + "ChildRelationship", value)]
        if box == "MaritalStatus":
            return [(root + "ChildMStatus", value)]
        if box == "Accompanying" and kind != "applicant" and value in ("Yes", "No"):
            return [(root + stem + value, "1")]
        return []
    if number == "5707":
        if kind == "sibling":
            return []
        section = {"applicant": "SectionA/Applicant", "spouse": "SectionA/Spouse", "mother": "SectionA/Parent1", "father": "SectionA/Parent2",
                   "child": f"SectionB/Child[{n}]"}.get(kind)
        if not section:
            return []
        root = f"/data/IMM_5707/page1/{section}/PaddedEntry/"
        first, second = root + "PersonalData[0]/", root + "PersonalData[1]/"
        early_dob = kind in ("mother", "father", "child")
        where = {"FamilyName": first, "GivenNames": first, "NativeName": first if kind in ("applicant", "spouse") else None,
                 "DOB": first if early_dob else second, "COB": second, "Address": second if kind != "applicant" else None,
                 "MaritalStatus": second, "Occupation": second, "Relationship": first if kind == "child" else None}.get(box)
        if where:
            return [(where + box, value)]
        if box == "Accompanying" and kind != "applicant":
            return [(root + "Accompanying/yesno", value)]
        if box == "MarriageInPerson" and kind in ("applicant", "spouse"):
            return [(root + "MarriageInPerson/MarriageInPerson/yesno", value)]
    return []


SPLIT_DATES = {"date_of_birth": r"(?:DOB|DateOfBirth|dob)"}
OTHER_PEOPLE = r"spouse|partner|child|dependant|parent|mother|father|sibling|previous|prev"


def split_date(value, stem, paths, exclude, placed, uses, plain):
    """{path: value} for a date the form keeps in separate year, month and day boxes, or None."""
    iso, _ = de.parse_date(str(value))
    if not iso:
        return None
    year = next((p for p in paths if re.search(rf"{stem}(?:Year|YYYY)$", p) and not re.search(OTHER_PEOPLE, de.clean_path(p), re.I)
                 and not (exclude and re.search(exclude, de.clean_path(p), re.I))), None)
    if not year:
        return None
    base = re.sub(r"(?:Year|YYYY)$", "", year)
    month = next((base + x for x in ("Month", "MM") if base + x in paths), None)
    day = next((base + x for x in ("Day", "DD") if base + x in paths), None)
    if not (month and day):
        return None
    out = {}
    for path, part in ((year, iso[:4]), (month, iso[5:7]), (day, iso[8:10])):
        lists = de.lists_for(path, placed, uses, plain)
        codes = {c for m in lists for c in m}
        if codes:  # a month or day list: store the matching code (01 or 1)
            code = next((c for c in (part, part.lstrip("0")) if c in codes), None)
            if code is None:
                return None
            part = code
        out[path] = part
    return out


# ---- writing ----
NOT_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿\ud800-\udfff]")  # characters XML can't hold: they would corrupt the form


EMPTY_DATASETS = f'<xfa:datasets xmlns:xfa="{XFA_DATA}"><xfa:data/></xfa:datasets>'.encode()


class FillError(Exception):
    """The form couldn't be written safely; nothing was saved."""


def _elements(node, name=None):
    return [k for k in node.childNodes if k.nodeType == k.ELEMENT_NODE and (name is None or k.localName == name)]


def _default_ns(node):
    """The default XML namespace in force at this node ('' if none)."""
    while node is not None and node.nodeType == node.ELEMENT_NODE:
        if node.hasAttribute("xmlns"):
            return node.getAttribute("xmlns")
        node = node.parentNode
    return ""


def set_values(datasets_xml, values):
    """Write {data path: value} into the datasets XML; the form's other data is kept.

    The XML is edited in place (minidom keeps every namespace declaration where the form put it). A rewrite that
    moved a declaration, as ElementTree does, put IMM 5476's answers in the XHTML namespace, where Adobe never sees them.
    """
    from xml.dom import minidom
    if b"<!DOCTYPE" in datasets_xml or b"<!ENTITY" in datasets_xml:
        raise FillError("the form's data section contains a DOCTYPE; it isn't an IRCC form as published")
    doc = minidom.parseString(datasets_xml)
    root = doc.documentElement
    data = next((k for k in _elements(root, "data") if k.namespaceURI == XFA_DATA), None)
    if data is None:
        data = doc.createElementNS(XFA_DATA, (root.prefix + ":" if root.prefix else "") + "data")
        root.appendChild(data)
    for path, value in values.items():
        node = data
        for part in path.split("/")[2:]:  # skip '' and 'data'
            m = re.fullmatch(r"(.+?)(?:\[(\d+)\])?", part)
            name, idx = m.group(1), int(m.group(2) or 0)
            same = _elements(node, name)
            while len(same) <= idx:
                new = doc.createElement(name)
                if _default_ns(node):  # answers are never in a namespace, whatever the form declared above them
                    new.setAttribute("xmlns", "")
                node.appendChild(new)
                same.append(new)
            node = same[idx]
        for k in list(node.childNodes):  # a field holds text, not leftover children (rich text, old answers)
            node.removeChild(k)
        for a in [a for a in node.attributes.values() if a.localName in ("contentType", "dataNode")]:
            node.removeAttributeNode(a)  # plain text now: a leftover text/html marker would hide it
        node.appendChild(doc.createTextNode(NOT_XML.sub("", str(value))))
    return root.toxml().encode("utf-8")


def _trailer_value(obj):
    buf = io.BytesIO()
    obj.write_to_stream(buf)
    return buf.getvalue()


def save_incremental(blank_bytes, reader, ref, new_data, out, values=None):
    """The blank's bytes unchanged, plus one appended update that replaces the form's data section.

    This is how Adobe itself saves a filled form. IRCC certifies some forms (IMM 5257, IMM 1294) with a digital
    signature and adds usage rights: both cover the original bytes, so a full rewrite (the old way) broke them and
    Adobe reported the form as altered or damaged. An appended update leaves them valid.
    """
    import zlib
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject, TextStringObject
    start = blank_bytes.rfind(b"startxref")
    m = re.match(rb"startxref\s+(\d+)", blank_bytes[start:]) if start >= 0 else None
    if not m:
        raise FillError("the blank form is incomplete (no cross-reference table): download it again")
    prev = int(m.group(1))
    classic = blank_bytes[prev:prev + 4] == b"xref"
    t = reader.trailer
    size = int(t["/Size"])
    objects = {}  # object number -> (generation, what goes between "obj" and "endobj")

    def data_stream(num, gen):
        body = zlib.compress(new_data, 9)
        if reader.is_encrypted:  # IRCC's forms are encrypted (no password to open): the update must use the same key
            body = reader._encryption._make_crypt_filter(num, gen).stm_crypt.encrypt(body)
        return f"<</Filter/FlateDecode/Length {len(body)}>>\nstream\n".encode() + body + b"\nendstream"

    def plain(obj, num, gen):
        if reader.is_encrypted:
            obj = reader._encryption.encrypt_object(obj, num, gen)
        return _trailer_value(obj)

    if ref is not None:
        if not isinstance(ref, IndirectObject):
            raise FillError("the form's data section isn't stored as its own object")
        objects[ref.idnum] = (ref.generation, data_stream(ref.idnum, ref.generation))
    else:  # a form nobody has typed into yet (IMM 5669) has no data section: add one, as Adobe does on first save
        num, size = size, size + 1
        objects[num] = (0, data_stream(num, 0))
        root_ref = t.raw_get("/Root")
        root = root_ref.get_object()
        acro_raw = root.raw_get("/AcroForm")
        acro = acro_raw.get_object()
        xfa_raw = acro.raw_get("/XFA")
        xfa = xfa_raw.get_object()
        if not isinstance(xfa, ArrayObject):
            raise FillError("this form keeps its layout in one piece, which isn't supported")
        items = ArrayObject(list(xfa))
        names = [str(items[i]) for i in range(0, len(items) - 1, 2)]
        after = next((names.index(n) for n in ("localeSet", "template") if n in names), len(names) - 2)
        items[2 * after + 2:2 * after + 2] = [TextStringObject("datasets"), IndirectObject(num, 0, reader)]
        if isinstance(xfa_raw, IndirectObject):
            objects[xfa_raw.idnum] = (xfa_raw.generation, plain(items, xfa_raw.idnum, xfa_raw.generation))
        elif isinstance(acro_raw, IndirectObject):
            new_acro = DictionaryObject(acro)
            new_acro[NameObject("/XFA")] = items
            objects[acro_raw.idnum] = (acro_raw.generation, plain(new_acro, acro_raw.idnum, acro_raw.generation))
        else:
            new_acro = DictionaryObject(acro)
            new_acro[NameObject("/XFA")] = items
            new_root = DictionaryObject(root)
            new_root[NameObject("/AcroForm")] = new_acro
            objects[root_ref.idnum] = (root_ref.generation, plain(new_root, root_ref.idnum, root_ref.generation))
    entries = b""
    for key in ("/Root", "/Encrypt", "/Info"):
        if key in t:
            entries += key.encode() + b" " + _trailer_value(t.raw_get(key))
    if "/ID" in t:
        ids = [bytes(x.original_bytes if hasattr(x, "original_bytes") else x.get_original_bytes()) for x in t["/ID"]]
        entries += b"/ID[" + b"".join(b"<" + i.hex().encode() + b">" for i in ids) + b"]"
    buf = bytearray(blank_bytes)
    if not buf.endswith(b"\n"):
        buf += b"\n"
    where = {}
    for num in sorted(objects):
        gen, body = objects[num]
        where[num] = (len(buf), gen)
        buf += f"{num} {gen} obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(buf)
    if classic:
        buf += b"xref\n" + b"".join(f"{n} 1\n{at:010d} {g:05d} n \n".encode() for n, (at, g) in where.items())
        buf += b"trailer\n<<" + entries + f"/Size {size}/Prev {prev}>>\n".encode()
    else:  # the blank uses a cross-reference stream: the update must too
        where[size] = (xref_at, 0)
        rows = b"".join(b"\x01" + at.to_bytes(4, "big") + g.to_bytes(2, "big") for at, g in where.values())
        index = " ".join(f"{n} 1" for n in where)
        buf += (f"{size} 0 obj\n<</Type/XRef/W[1 4 2]/Index[{index}]/Size {size + 1}/Prev {prev}".encode() + entries
                + f"/Length {len(rows)}>>\nstream\n".encode() + rows + b"\nendstream\nendobj\n")
    buf += f"startxref\n{xref_at}\n%%EOF\n".encode()
    part = out.with_name(out.name + ".part")
    try:
        part.write_bytes(bytes(buf))
        check_saved(part, blank_bytes, new_data, values)
        part.replace(out)
    finally:
        if part.exists():
            part.unlink()


def check_saved(path, blank_bytes, new_data, values=None):
    """Open the saved file as a PDF reader would: the original untouched, the new data readable and whole."""
    import pypdf
    saved = path.read_bytes()
    if not saved.startswith(blank_bytes):
        raise FillError("the original form bytes changed")
    r = pypdf.PdfReader(str(path), strict=False)
    if r.is_encrypted and not r.decrypt(""):
        raise FillError("the saved form can't be opened")
    parts = xfa_parts(r)
    if parts.get("datasets") is None or parts["datasets"].get_data() != new_data:
        raise FillError("the saved form data doesn't read back exactly")
    items = list(r.trailer["/Root"]["/AcroForm"]["/XFA"].get_object())
    chunks = [items[i + 1].get_object().get_data() for i in range(0, len(items) - 1, 2)]
    wrapped = str(items[0]) in ("xdp:xdp", "preamble")  # IRCC's forms: the parts join into one XML document
    try:
        for chunk in ([b"".join(chunks)] if wrapped else chunks):
            ET.fromstring(chunk)
    except ET.ParseError as e:
        raise FillError(f"the saved form's XML is damaged ({e})")
    lost = misplaced(new_data, values or {})
    if lost:
        raise FillError("answers not where the form looks for them: " + ", ".join(lost[:5]))


def misplaced(datasets_xml, values):
    """Paths whose answer isn't stored exactly there: plain names (no namespace) under xfa:data, as Adobe binds them."""
    data = next((k for k in ET.fromstring(datasets_xml) if k.tag == f"{{{XFA_DATA}}}data"), None)
    if data is None:
        return list(values)[:1] or ["(no answer section)"]
    bad = []
    for path, value in values.items():
        node = data
        for part in path.split("/")[2:]:
            m = re.fullmatch(r"(.+?)(?:\[(\d+)\])?", part)
            same = [k for k in node if k.tag == m.group(1)]  # an exact, namespace-free name
            node = same[int(m.group(2) or 0)] if len(same) > int(m.group(2) or 0) else None
            if node is None:
                break
        if node is None or (node.text or "") != NOT_XML.sub("", str(value)) or len(node):
            bad.append(path.split("/")[-1])
    return bad


def blank_problem(path):
    """None if the file is a usable IRCC form, else what is wrong with it in plain words."""
    import pypdf
    try:
        raw = pathlib.Path(path).read_bytes()
    except OSError as e:
        return f"can't be read ({e.strerror})"
    if not raw.startswith(b"%PDF"):
        return "isn't a PDF (a web page or an incomplete download?)"
    if b"%%EOF" not in raw[-2048:]:
        return "is incomplete (the download was cut off)"
    try:
        r = pypdf.PdfReader(io.BytesIO(raw), strict=False)
        if r.is_encrypted and not r.decrypt(""):
            return "is locked with a password"
        acro = r.trailer["/Root"].get("/AcroForm")
        xfa = acro.get_object().get("/XFA") if acro else None
        if xfa is None:
            return ("has no IRCC form inside: it was probably saved from a web browser or printed to PDF, which removes "
                    "the form. Download it again from IRCC")
        items = list(xfa.get_object())
        names = {str(items[i]) for i in range(0, len(items) - 1, 2)}
        if "template" not in names:
            return "is missing its form template"
        for i in range(0, len(items) - 1, 2):
            if str(items[i]) in ("template", "datasets"):
                ET.fromstring(items[i + 1].get_object().get_data())
    except Exception as e:  # any damage the reader trips on
        return f"is damaged ({type(e).__name__})"
    return None


def answers(form, person, case=None, report=None, facts=None, include_confirm=False):
    """{key: answer} that may be written, and {key: why not} for the rest."""
    _, spec = fp.load_spec(form)
    folder = de.active_case(case) if case else None
    report_path = pathlib.Path(report) if report else (fp.latest_report(folder / "03-documents" / "_extraction") if folder else None)
    pool = fp.facts_from_report(json.loads(report_path.read_text(encoding="utf-8")), person)[0] if report_path else {}
    facts_path = pathlib.Path(facts) if facts else (folder / "client-facts.csv" if folder else None)
    client = fp.facts_from_file(facts_path, person) if facts_path else {}
    ok, skipped = {}, {}
    fill.family = family_people(client)
    allowed = FILL | ({fp.CONFIRM} if include_confirm else set())
    asked = {q["key"] for q in spec}
    for key, entries in client.items():  # parts of a several-box answer, confirmed by the consultant
        group, _, box = key.partition(".")
        if group in BOXES and box in BOXES[group] and group in asked:
            values = {e["value"] for e in entries if e.get("value")}
            if len(values) == 1:
                ok[key] = values.pop()
            elif values:
                skipped[key] = "conflict: more than one value given"
    for q, r in zip(spec, fp.build_rows(spec, pool, client)):
        if q["rule"] == "sign":
            skipped[q["key"]] = "signature"
        elif r["status"] in allowed and r["answer"] and "*" not in r["answer"]:
            ok[q["key"]] = r["answer"]
        else:
            skipped[q["key"]] = r["status"] if r["answer"] or r["status"] != fp.READY else "no answer"
    return ok, skipped, spec, folder


def fill(form, blank, ready, out):
    """Write the ready answers into the blank. Returns (filled {key: value}, not filled {key: reason})."""
    import pypdf
    number = number_of(form)
    maps, joins = de.form_maps(number)
    if not maps:
        sys.exit(f"ERROR: {form.upper()} isn't autofilled (its answers are a table of figures or free text): fill it in Adobe")
    problem = blank_problem(blank)
    if problem:
        sys.exit(f"ERROR: the blank form {blank} {problem}.")
    blank_bytes = pathlib.Path(blank).read_bytes()
    reader = pypdf.PdfReader(io.BytesIO(blank_bytes), strict=False)
    if reader.is_encrypted:
        reader.decrypt("")
    parts = xfa_parts(reader)
    if "template" not in parts:
        sys.exit("ERROR: the form's template or data section is missing")
    template = parts["template"].get_data()
    datasets = parts["datasets"].get_data() if "datasets" in parts else EMPTY_DATASETS  # IMM 5669 ships without one
    paths = template_fields(template)
    placed, uses, plain = de.choice_maps(ET.fromstring(datasets), template)
    exclude = de.NOT_PA if number == "0008" else None
    values, filled, missed = {}, {}, {}
    for key, rx, *how in maps:
        if key not in ready or key in filled:
            continue
        path = find_path(paths, rx, exclude)
        if not path:
            missed[key] = "no matching field on this version of the form"
            continue
        code, why = encode(ready[key], how[0] if how else None, path, de.lists_for(path, placed, uses, plain))
        if why:
            missed[key] = why
            continue
        values[path], filled[key] = code, ready[key]
    parts_written, split = {}, set()
    for role, boxes in (getattr(fill, "family", None) or {}).items():
        for box, value in boxes.items():
            if box == "Name" or (box in ("FamilyName", "GivenNames") and number == "5645"):
                continue
            for path, label in family_paths(number, role, box, value):
                code, why = encode(label, "date" if box == "DOB" else None, path, de.lists_for(path, placed, uses, plain))
                key = f"family.{role}.{box}"
                if why:
                    missed[key] = why
                    continue
                values[path], filled[key] = code, label
                parts_written[path] = label
        if number == "5645" and ("FamilyName" in boxes or "GivenNames" in boxes):  # IMM 5645 has one name box
            full = " ".join(x for x in (boxes.get("GivenNames"), boxes.get("FamilyName")) if x)
            for path, label in family_paths(number, role, "Name", full):
                values[path], filled[f"family.{role}.Name"] = label, label
                parts_written[path] = label
    for key, value in ready.items():
        group, _, box = key.partition(".")
        if group not in BOXES or box not in BOXES[group]:
            continue
        path = find_path(paths, BOXES[group][box])
        if not path:
            missed[key] = "no matching box on this form"
            continue
        code, why = encode(value, "date" if box.endswith("Date") else None, path, de.lists_for(path, placed, uses, plain))
        if why:
            missed[key] = why
            continue
        values[path], filled[key] = code, value
        parts_written[path] = value
    for key, stem in SPLIT_DATES.items():  # dates kept as year, month and day boxes (IMM 5257, IMM 0008 ...)
        if key in ready and key not in filled:
            got = split_date(ready[key], stem, paths, exclude, placed, uses, plain)
            if got:
                values.update(got)
                parts_written.update(got)  # read back box by box: the extractor has no single answer for them
                split.add(key)
                filled[key] = ready[key]
                missed.pop(key, None)
    for key, _, _ in joins:
        if key in ready and key not in filled and not any(k.startswith(key + ".") for k in filled):
            missed[key] = "made of several boxes (e.g. an address): give it in parts, or type it in Adobe"
    family_written = any(k.startswith("family.") for k in filled)
    for key in ready:
        if key in BOXES and any(k.startswith(key + ".") for k in filled):
            continue  # written from its parts
        if family_written and key in COVERED_BY_FAMILY:
            missed.pop(key, None)
            continue  # written row by row in the family table
        if key not in filled and key not in missed:
            missed[key] = "not a single form field (calculated or a table): type it in Adobe"
    items = list(reader.trailer["/Root"]["/AcroForm"].get_object()["/XFA"].get_object())
    ref = next((items[i + 1] for i in range(0, len(items) - 1, 2) if str(items[i]) == "datasets"), None)
    out = pathlib.Path(out)
    ps.check_output(out)
    fill.family = None
    try:
        new_data = set_values(datasets, values)
        out.parent.mkdir(parents=True, exist_ok=True)
        save_incremental(blank_bytes, reader, ref, new_data, out, values)
    except FillError as e:
        sys.exit(f"ERROR: the form could not be filled safely, so nothing was saved: {e}. "
                 "Fill this form by hand in Adobe, and tell your agent provider.")
    fill.parts_written, fill.split = parts_written, split
    return filled, missed


def matches(got, value):
    """Does the value read back from the form say what was written? Allows 'F' for 'F Female' and '160' for '160 cm'."""
    g, v = got.strip().lower(), value.strip().lower()
    if "*" in g and g.strip("*") and v.endswith(g.strip("*")) and len(g) == len(v):  # numbers are read back masked: ******567
        return True
    g, v = re.sub(r"\s*cm$", "", g), re.sub(r"\s*cm$", "", v)
    if de.squash(g) in (de.squash(v), de.squash(de.country_name(value))):
        return True
    if len(g) >= 4 and v.startswith(g) and len(v) - len(g) <= 3:  # Bangladeshi -> Bangladesh
        return True
    head, _, rest = g.partition(" ")
    rest = rest.strip("()")
    return v in (head, rest) or any(alt in (g, rest) for alt in SYNONYMS.get(v.upper(), ()))


def verify(form, out, filled):
    """Read the filled form back with the extractor: every written answer must come back under its own question."""
    import pypdf
    r = pypdf.PdfReader(str(out), strict=False)
    form_values = de.read_form(r)
    back = {f["field"]: f["value"] for f in de.form_answers(form_values, number_of(form))}
    wrong = {}
    raw = form_values
    for key, value in filled.items():
        if key.startswith("family.") or key in (getattr(fill, "split", None) or ()):
            continue  # checked below, box by box
        group, _, box = key.partition(".")
        if group in BOXES and box in BOXES[group]:  # a part: read its own box back
            got = next((v for p, v in raw.items() if re.search(BOXES[group][box], de.clean_path(p))), None)
            if got is None or not matches(str(got), str(value)):
                wrong[key] = f"wrote '{value}', reads back as '{got}'"
            continue
        got = back.get(key)
        same = got is not None and matches(str(got), str(value))
        if not same:
            wrong[key] = f"wrote '{value}', reads back as '{got}'"
    flat = {}
    for p, v in raw.items():
        flat.setdefault(re.sub(r"\[0\](?=/)", "", p), v)  # a single repeated section is read back without [0]
    for path, label in (getattr(fill, "parts_written", None) or {}).items():
        got = raw.get(path, flat.get(re.sub(r"\[0\](?=/)", "", path)))
        if got is None or not (matches(str(got), str(label)) or str(got).lstrip("0") == str(label).lstrip("0")
                               or (label == "1" and str(got) in ("1", "on"))):
            box = path.split("/page1/")[-1] if "/page1/" in path else "/".join(path.split("/")[-2:])
            wrong[box] = f"wrote '{label}', reads back as '{got}'"
    return wrong


def cmd_fetch(a):
    print(f"Blank form: {fetch(a.form)}")


def cmd_fill(a):
    form = a.form.lower()
    ready, skipped, spec, folder = answers(form, a.person, a.case, a.report, a.facts, a.include_confirm)
    blank = pathlib.Path(a.blank) if a.blank else fetch(form)
    stem = f"{datetime.date.today().isoformat()}-{form}-{re.sub(r'[^a-z0-9]+', '-', a.person.lower()).strip('-')}-autofill"
    if a.out:
        out = pathlib.Path(a.out)
    elif folder:
        out = folder / "05-forms-submissions" / f"{stem}.pdf"
    else:
        out = ps.OUTPUT / f"{stem}.pdf"
    out = ps.free_name(out)
    filled, missed = fill(form, blank, ready, out)
    wrong = verify(form, out, filled)
    questions = {r["key"]: r["question"] for r in spec}
    print(f"Saved: {out}")
    print(f"Filled {len(filled) - len(wrong)} answer(s); checked by reading the form back.")
    if wrong:
        print("NOT confirmed (fix these in Adobe):")
        for k, why in wrong.items():
            print(f"  - {questions.get(k, k)[:80]}: {why}")
    if missed:
        print(f"Ready but not filled ({len(missed)}):")
        for k, why in missed.items():
            print(f"  - {questions.get(k, k)[:80]}: {why}")
    left = {k: v for k, v in skipped.items() if v != "signature"}
    print(f"Left blank for you: {len(left)} question(s) not ready (see the worksheet), and every signature.")
    print("Next: open it in Adobe Acrobat or the free Adobe Acrobat Reader (right-click > Open with > Adobe Acrobat), check every page,")
    print("fill the blanks, click Validate, then sign. A web browser, Edge or Preview shows IRCC forms blank or as 'Please wait...':")
    print("that is the viewer, not damage. Adobe shows the form as certified by IRCC.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Autofill an IRCC form with the worksheet's ready answers")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("fetch"); x.add_argument("--form", required=True); x.set_defaults(fn=cmd_fetch)
    x = s.add_parser("fill"); x.add_argument("--form", required=True); x.add_argument("--person", required=True)
    g = x.add_mutually_exclusive_group(required=True); g.add_argument("--case"); g.add_argument("--report")
    x.add_argument("--facts"); x.add_argument("--blank"); x.add_argument("--out"); x.add_argument("--include-confirm", action="store_true")
    x.set_defaults(fn=cmd_fill)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
