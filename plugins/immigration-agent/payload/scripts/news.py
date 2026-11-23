#!/usr/bin/env python3
"""Immigration news from official sources only, matched to open files. Shown on the dashboard (Today and IRCC data).

Usage:
  python3 scripts/news.py check            read the official pages now (public pages; nothing about you or your clients is sent)
  python3 scripts/news.py list [--n 20] [--tag federal|provincial|quebec|work|rules|fees] [--days 60]
  python3 scripts/news.py show ID [--files]  one item, its source link and (with --files) the open files it may concern
  python3 scripts/news.py sources          each source, when it was last read and whether it worked

Guarantees:
  - Official sources only: IRCC's news feed and notices, IRCC's Express Entry rounds, ESDC and Job Bank, and each province's
    own draw page. No news site or draw tracker is read. Items say what the source says and link to it.
  - The daily alerts read the sources once a day; the dashboard's "Check now" button reads them on request. Pages that block
    automated reads (PEI, Yukon) or don't publish draw results (Saskatchewan) are listed as "check by hand".
  - A source that fails or changes its layout is reported as failed. It never produces a guessed item.
  - "Your files" matches use the file's program and province (keywords) and, for Express Entry rounds, the recorded CRS score.
    Each match is a prompt to review, not a finding that the client qualifies or was invited.
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402

STATE = cs.ROOT / ".news-state.json"
EVERY_HOURS = 20
KEEP_DAYS = 180        # items older than this are dropped from the saved list
SHOW_DAYS = 60         # default window on the dashboard
RULE_BACK, RULE_AHEAD = 60, 90
TAGS = {"federal": "Federal", "provincial": "Provincial", "quebec": "Quebec", "work": "Work and wages", "rules": "Rules", "fees": "Forms and fees"}
PROVINCE_NAME = {"AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick", "NL": "Newfoundland and Labrador",
                 "NS": "Nova Scotia", "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec", "SK": "Saskatchewan", "YT": "Yukon",
                 "NT": "Northwest Territories", "NU": "Nunavut"}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
IRCC_NEWS = ("https://api.io.canada.ca/io-server/gc/news/en/v2?dept=departmentofcitizenshipandimmigration"
             "&sort=publishedDate&orderBy=desc&pick=40&format=json")
NOTICES = "https://www.canada.ca/en/immigration-refugees-citizenship/news/notices.html"
FEES_PAGE = "https://ircc.canada.ca/english/information/fees/fees.asp"
EE_PAGE = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/policies-operational-instructions-agreements/ministerial-instructions/express-entry-rounds.html"


def year_url(template, year):
    return template.format(year=year)


# key: (label, tag, province, url or url template with {year}, parser name)
SOURCES = {
    "ircc-news": ("IRCC news releases", "federal", None, IRCC_NEWS, "ircc_news"),
    "ircc-notices": ("IRCC notices", "federal", None, NOTICES, "ircc_notices"),
    "esdc-median-wage": ("ESDC median wage thresholds (LMIA)", "work", None,
                         "https://www.canada.ca/en/employment-social-development/services/foreign-workers/median-wage.html", "page_date"),
    "jobbank-wages": ("Job Bank prevailing wages", "work", None, "https://www.jobbank.gc.ca/wagereport/location/on", "jobbank"),
    "ab-draws": ("Alberta AAIP draws", "provincial", "AB", "https://www.alberta.ca/aaip-processing-information", "alberta"),
    "bc-draws": ("BC PNP invitations", "provincial", "BC",
                 "https://www.welcomebc.ca/immigrate-to-b-c/about-the-bc-provincial-nominee-program/invitations-to-apply", "bc"),
    "mb-draws": ("Manitoba MPNP draws", "provincial", "MB", "https://immigratemanitoba.com/draws/", "manitoba"),
    "nb-draws": ("New Brunswick selection rounds", "provincial", "NB",
                 "https://www.gnb.ca/en/topic/family-home-community/immigration/invitation-selection-rounds.html", "new_brunswick"),
    "nl-draws": ("Newfoundland and Labrador ITAs", "provincial", "NL", "https://www.gov.nl.ca/immigration/invitations-to-apply-updates/", "newfoundland"),
    "ns-draws": ("Nova Scotia EOI selections", "provincial", "NS", "https://liveinnovascotia.com/eoi-selection", "nova_scotia"),
    "on-updates": ("Ontario OINP updates", "provincial", "ON", "https://www.ontario.ca/page/{year}-ontario-immigrant-nominee-program-updates", "ontario"),
    "qc-arrima": ("Quebec PSTQ invitations (Arrima)", "quebec", "QC",
                  "https://www.quebec.ca/en/immigration/permanent/skilled-workers/skilled-worker-selection-program/invitation/{year}", "quebec"),
}
BY_HAND = [  # official pages the agent can't read automatically
    ("Saskatchewan SINP draws", "SK", "https://www.saskatchewan.ca/residents/moving-to-saskatchewan/live-in-saskatchewan/by-immigrating/saskatchewan-immigrant-nominee-program",
     "The SINP page doesn't publish draw results in a form the agent can read"),
    ("Prince Edward Island EOI draws", "PE", "https://www.princeedwardisland.ca/en/information/office-of-immigration/expression-of-interest-draws",
     "The PEI site blocks automated reads (bot check)"),
    ("Yukon Nominee Program", "YT", "https://yukon.ca/en/immigrate-yukon", "The Yukon site blocks automated reads"),
    ("Northwest Territories Nominee Program", "NT", "https://www.immigratenwt.ca/", "No draw list published"),
]
NOT_IMMIGRATION = re.compile(r"highlights.*budget|budget.*investments|investments from budget|culture, creativity", re.I)
IMMIGRATION_WORDS = re.compile(r"immigra|worker|resident|refugee|asylum|citizen|visa|permit|newcomer|francophone|student|express entry", re.I)
SKIP_TITLE = re.compile(r"\bto (make an announcement|highlight|announce|deliver|participate|hold|attend|speak|mark|celebrate)\b|media advisory", re.I)


# ---------- helpers ----------
def clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or "")).replace("\\r\\n", " ").replace("\xa0", " ")
    text = text.replace("‑", "-").replace("–", "-").replace("—", "-").replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def unmangle(text):
    """IRCC's news feed sends some text encoded twice (Canadaâ€™s); undo it when that is what happened."""
    if text and re.search("[âÃ]", text):
        try:
            return text.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return text


def parse_day(text):
    """A date from 'November 13, 2026', 'November 06 and 16, 2026' (the last day), 'Nov. 5, 2026' or '2026-11-13'. None if none."""
    text = clean(text)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:\s*(?:and|&|to|-)\s*(\d{1,2}))?,?\s+(\d{4})", text)
    if not m:
        return None
    month = next((n for name, n in MONTHS.items() if name.startswith(m.group(1).lower()[:3])), None)
    try:
        return datetime.date(int(m.group(4)), month, int(m.group(3) or m.group(2))) if month else None
    except ValueError:
        return None


def num(text):
    m = re.search(r"\d[\d,\s]*", text or "")
    return int(re.sub(r"[,\s]", "", m.group(0))) if m and "<" not in text else None


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def total(counts):
    """'374' or '374+' when some counts are published as '<5'."""
    known = [num(c) for c in counts if num(c) is not None]
    return f"{sum(known):,}{'+' if len(known) < len(counts) else ''}" if known else "?"


def item(source, day, title, link, detail=None, key=None, **extra):
    label, tag, prov, *_ = SOURCES[source]
    ident = hashlib.sha256(f"{source}|{key or title}".encode("utf-8")).hexdigest()[:10]
    return {"id": ident, "source": source, "source_label": label, "tag": tag, "province": prov, "date": day.isoformat() if day else "",
            "title": title, "detail": [d for d in (detail or []) if d], "link": link, **extra}


def tables(page):
    """[(heading before the table, [[cell text]])]: rows with th or td cells."""
    out = []
    for m in re.finditer(r"<table.*?</table>", page, re.S | re.I):
        heads = re.findall(r"<h[1-5][^>]*>(.*?)</h[1-5]>", page[max(0, m.start() - 4000):m.start()], re.S | re.I)
        rows = [[clean(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S | re.I)] for r in re.findall(r"<tr.*?</tr>", m.group(0), re.S | re.I)]
        out.append((clean(heads[-1]) if heads else "", [r for r in rows if any(r)]))
    return out


# ---------- parsers: (page text, source url) -> [item] ----------
def p_ircc_news(text, url):
    entries = json.loads(text).get("feed", {}).get("entry", [])
    out = []
    for e in entries:
        title = clean(unmangle(e.get("title", "")))
        day = parse_day(e.get("publishedDate", ""))
        if not title or not day or SKIP_TITLE.search(title) or (NOT_IMMIGRATION.search(title) and not IMMIGRATION_WORDS.search(title)):
            continue
        if any(o["title"] == title for o in out):  # IRCC posts some releases twice (two links, same text)
            continue
        teaser = clean(unmangle(e.get("teaser", "")))
        out.append(item("ircc-news", day, title, e.get("link", ""), [teaser[:300] if teaser != title else ""], key=e.get("link") or title))
    if not entries:
        raise ValueError("no entries in IRCC's news feed")
    return out


def p_ircc_notices(text, url):
    out, seen = [], set()
    main = text[text.find("<main"):] if "<main" in text else text
    for m in re.finditer(r'<a href="([^"]*/news/notices/[^"#]+\.html)"[^>]*>(.*?)</a>', main, re.S):
        link, title = m.group(1), re.sub(r"^Notice\s*[-–]\s*", "", clean(m.group(2)))
        day = parse_day(main[m.end():m.end() + 400].split("<a ", 1)[0])
        if not day or link in seen or not title:
            continue
        seen.add(link)
        out.append(item("ircc-notices", day, title, link if link.startswith("http") else "https://www.canada.ca" + link, key=link))
    if not out:
        raise ValueError("no notices found (IRCC may have changed the page)")
    return out


def p_page_date(text, url):
    m = (re.search(r'name="dcterms.modified"[^>]*content="(\d{4}-\d{2}-\d{2})"', text) or re.search(r"<gcds-date-modified>\s*(\d{4}-\d{2}-\d{2})", text)
         or re.search(r'<time[^>]*property="dateModified"[^>]*>([^<]+)</time>', text))
    day = parse_day(m.group(1)) if m else None
    if not day:
        raise ValueError("no 'Date modified' on the page")
    return [item("esdc-median-wage", day, "ESDC updated its median wage page (high-wage and low-wage LMIA thresholds)", url,
                 ["Check the threshold for the work location before choosing the high-wage or low-wage LMIA stream."], key=day.isoformat())]


def p_jobbank(text, url):
    m = re.search(r"wages were updated on\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})", clean(text), re.I)
    day = parse_day(m.group(1)) if m else None
    if not day:
        raise ValueError("no wage update date on the Job Bank page")
    return [item("jobbank-wages", day, "Job Bank updated prevailing wages by occupation and region", "https://www.jobbank.gc.ca/trend-analysis/search-wages",
                 ["The LMIA wage must meet the new Job Bank wage for the occupation and region. Re-check open employer files."], key=day.isoformat())]


def group_draws(source, rows, link, name, unit="invitations"):
    """rows: [(date, stream, min score or '', count text)] -> one item per draw date."""
    by_day = {}
    for day, stream, low, count in rows:
        by_day.setdefault(day, []).append((stream, low, count))
    out = []
    for day, draws in by_day.items():
        detail = [f"{s}: {c} {unit}" + (f", minimum score {lo}" if lo and lo.lower() not in ("n/a", "-", "") else "") for s, lo, c in draws]
        n = total([c for _, _, c in draws])
        title = f"{name} issues {n} {unit} in {plural(len(draws), 'draw')}" if len(draws) > 1 else f"{name}: {n} {unit} ({draws[0][0]})"
        out.append(item(source, day, title, link, detail, key=day.isoformat(), count=n))
    return out


def p_alberta(text, url):
    rows = []
    for _, tb in tables(text):
        if tb and tb[0] and tb[0][0].lower().startswith("draw date"):
            for r in tb[1:]:
                day = parse_day(r[0]) if r else None
                if day and len(r) >= 4:
                    rows.append((day, r[1], r[2], r[3]))
    if not rows:
        raise ValueError("no draw table found")
    return group_draws("ab-draws", rows, url, "Alberta")


def p_bc(text, url):
    rows = []
    for head, tb in tables(text):
        if not tb or not tb[0] or tb[0][0].lower() != "date":
            continue
        width, day = len(tb[0]), None
        for r in tb[1:]:
            if parse_day(r[0]) and len(r) == width:
                day, r = parse_day(r[0]), r[1:]
            elif len(r) != width - 1 or not day:
                continue  # a continuation line of the selection factors
            stream = r[0] if width == 4 else f"{r[0]} ({r[1]})" if r[1] and len(r[1]) < 60 else r[0]
            rows.append((day, ("Entrepreneur " if "entrepreneur" in head.lower() else "") + stream, r[-2], r[-1]))
    if not rows:
        raise ValueError("no invitation table found")
    return group_draws("bc-draws", rows, url, "BC PNP")


def p_manitoba(text, url):
    out = []
    for m in re.finditer(r"<article.*?</article>", text, re.S):
        art = m.group(0)
        h = re.search(r'<h2[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', art, re.S)
        day = parse_day((re.search(r'class="published"[^>]*>(.*?)<', art, re.S) or re.search(r"(x)", "x")).group(1))
        if not h or not day or "draw" not in clean(h.group(2)).lower():
            continue
        name = clean(h.group(2))
        detail, parts = [], re.split(r"<h4[^>]*>", art)[1:]
        for part in parts:
            stream = clean(part.split("</h4>", 1)[0])
            sub = re.search(r"<p[^>]*>\s*(?:<strong>\s*</strong>)?\s*<strong>([^<]{3,80})</strong>\s*</p>", part)
            n = re.search(r"Letters of Advice to Apply issued:\s*(?:<[^>]+>\s*)*([\d,]+)", part)
            if n:
                detail.append(f"{stream}{' - ' + clean(sub.group(1)) if sub else ''}: {n.group(1)}")
        whole = re.search(r"Of the\s*(?:<[^>]+>\s*)*([\d,]+)\s*(?:<[^>]+>\s*)*Letters of Advice", art)
        n = whole.group(1) if whole else total([d.rsplit(": ", 1)[1] for d in detail]) if detail else "?"
        number = re.search(r"#\s*(\d+)", name)
        out.append(item("mb-draws", day, f"Manitoba {name.replace('Expression of Interest', 'EOI')}: {n} Letters of Advice to Apply", h.group(1), detail,
                        key=number.group(1) if number else name, count=n))
    if not out:
        raise ValueError("no draws found (the page may have changed or blocked the read)")
    return out


def p_new_brunswick(text, url):
    out, seen = [], set()
    for head, tb in tables(text):
        kv = {r[0].lower(): r[1] for r in tb if len(r) >= 2}
        day = parse_day(kv.get("date of draw", ""))
        count = next((v for k, v in kv.items() if k.startswith(("applications selected", "invitations issued", "number of invitations"))), None)
        if not day or not count or (head, day) in seen:
            continue
        seen.add((head, day))
        stream = re.sub(r"^New Brunswick\s+", "", head) or "selection round"
        paths = kv.get("pathways", "")
        out.append(item("nb-draws", day, f"New Brunswick {stream}: {count} {'selected' if 'applications selected' in kv else 'invitations'}", url,
                        [f"Pathways: {paths}" if paths else "", f"Cut-off: {kv['cut-off date and time']}" if kv.get("cut-off date and time") else ""],
                        key=f"{stream}|{day}", count=count))
    if not out:
        raise ValueError("no selection rounds found")
    return out


def p_newfoundland(text, url):
    out = []
    for _, tb in tables(text):
        if not tb or "date" not in tb[0][0].lower():
            continue
        for r in tb[1:]:
            day = parse_day(r[0]) if r else None
            if day and len(r) >= 2:
                out.append(item("nl-draws", day, f"Newfoundland and Labrador issues {r[1]} invitations to apply", url, [r[2] if len(r) > 2 else ""], key=day.isoformat(), count=r[1]))
    if not out:
        raise ValueError("no ITA table found")
    return out


def p_nova_scotia(text, url):
    page = clean(text)
    updated = parse_day((re.search(r"Last Updated:\s*([A-Za-z]+ \d{1,2}, \d{4})", page) or re.search(r"(x)", "x")).group(1))
    out = []
    for _, tb in tables(text):
        for r in tb:
            m = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", r[0]) if len(r) >= 2 else None
            month = MONTHS.get(m.group(1).lower()) if m else None
            if not month or num(r[1]) is None:
                continue
            year = int(m.group(2))
            end = (datetime.date(year + (month == 12), month % 12 + 1, 1) - datetime.timedelta(days=1))
            day = min(end, updated) if updated else end
            out.append(item("ns-draws", day, f"Nova Scotia selects {r[1]} candidates from its EOI pool ({r[0]})", url,
                            ["Monthly total of EOI selections (Nova Scotia Nominee Program and Atlantic Immigration Program)"], key=r[0], count=r[1]))
    if not out:
        raise ValueError("no monthly selection table found")
    return out


def p_ontario(text, url):
    year = re.search(r"/page/(\d{4})-", url)
    out = []
    for h in re.findall(r"<h3[^>]*>(.*?)</h3>", text, re.S):
        m = re.match(r"([A-Za-z]+ \d{1,2}):\s*(.+)", clean(h))
        day = parse_day(f"{m.group(1)}, {year.group(1)}") if m and year else None
        if day:
            out.append(item("on-updates", day, f"Ontario (OINP): {m.group(2)}", url, key=f"{day}|{m.group(2)}"))
    if not out:
        raise ValueError("no dated updates found")
    return out


def p_quebec(text, url):
    by_day, stream = {}, ""
    pieces = re.split(r"(<h[2-4][^>]*>.*?</h[2-4]>)", text, flags=re.S)
    for i, piece in enumerate(pieces):
        if not re.match(r"<h[2-4]", piece):
            continue
        head = clean(piece)
        if re.match(r"Stream \d", head):
            stream = head.split(":")[0]
        elif head.lower().startswith("invitations for"):
            day = parse_day(head)
            n = re.search(r"invited\s+([\d,\s]+?)\s+people", clean(pieces[i + 1] if i + 1 < len(pieces) else ""))
            if day and n:
                by_day.setdefault(day, []).append((stream or "PSTQ", n.group(1).strip()))
    out = []
    for day, rows in by_day.items():
        out.append(item("qc-arrima", day, f"Quebec invites {total([c for _, c in rows])} people to apply under the PSTQ (Arrima)", url,
                        [f"{s}: {c}" for s, c in rows], key=day.isoformat(), count=total([c for _, c in rows])))
    if not out:
        raise ValueError("no invitation rounds found")
    return out


PARSERS = {"ircc_news": p_ircc_news, "ircc_notices": p_ircc_notices, "page_date": p_page_date, "jobbank": p_jobbank, "alberta": p_alberta,
           "bc": p_bc, "manitoba": p_manitoba, "new_brunswick": p_new_brunswick, "newfoundland": p_newfoundland, "nova_scotia": p_nova_scotia,
           "ontario": p_ontario, "quebec": p_quebec}


# ---------- state ----------
def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    cs.ROOT.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(STATE.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    os.replace(tmp, STATE)


def stale(now=None):
    checked = load_state().get("checked")
    if not checked:
        return True
    now = now or datetime.datetime.now()
    return (now - datetime.datetime.fromisoformat(checked)).total_seconds() >= EVERY_HOURS * 3600


def read_source(key, today, fetch=None):
    """[items] from one source. Raises on a failed read or an unreadable page."""
    import watch as wt
    fetch = fetch or wt.fetch
    _, _, _, url, parser = SOURCES[key]
    years = [today.year, today.year - 1] if "{year}" in url else [None]
    last = None
    for y in years:
        page_url = year_url(url, y) if y else url
        text = fetch(page_url)
        if not text:
            last = ConnectionError("couldn't read the page")
            continue
        if "Radware" in text[:3000] or "captcha" in text[:3000].lower():
            raise ConnectionError("the site blocked the automated read")
        try:
            return PARSERS[parser](text, page_url)
        except ValueError as e:
            last = e
    raise last


def refresh(today=None, fetch=None, only=None):
    """Read every source and save. Returns the saved state. One failed source doesn't stop the others."""
    today = today or datetime.date.today()
    state = load_state()
    items, sources = state.get("items", {}), state.get("sources", {})
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    for key in only or SOURCES:
        try:
            got = read_source(key, today, fetch)
            for it in got:
                old = items.get(it["id"])
                it["first_seen"] = old["first_seen"] if old else today.isoformat()
                items[it["id"]] = it
            sources[key] = {"ok": True, "checked": stamp, "last_ok": stamp, "count": len(got)}
        except Exception as e:  # a failed read must show, not pass as "no news"
            sources[key] = {"ok": False, "checked": stamp, "error": (str(e) or type(e).__name__)[:160], "last_ok": (sources.get(key) or {}).get("last_ok", "")}
    cutoff = (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    state.update(items={k: v for k, v in items.items() if v.get("date", "") >= cutoff}, sources=sources, checked=stamp)
    save_state(state)
    return state


# ---------- items the agent already holds (no web read) ----------
def ee_items(today):
    import draws as dr
    out = []
    for r in (dr.load_state().get("rounds") or [])[:12]:
        day = datetime.date.fromisoformat(r["date"])
        kind = "general" if r["category"] == "general" else next((n for k, _, n in dr.CATEGORIES if k == r["category"]), r["name"])
        out.append({"id": f"ee{r['number']}", "source": "ee-rounds", "source_label": "IRCC Express Entry rounds", "tag": "federal", "province": None,
                    "date": r["date"], "title": f"Express Entry round #{r['number']}: {plural(r['size'], 'invitation') if r['size'] else 'invitations'}, lowest CRS {r['crs']}",
                    "detail": [f"Round type: {r['name']}" + ("" if kind == "general" else f" (category: {kind})"), f"Tie-breaking rule: {r['tiebreak']}" if r.get("tiebreak") else ""],
                    "link": EE_PAGE, "round": r["number"], "first_seen": r["date"]})
    for d in (dr.load_state().get("pnp") or [])[-10:]:
        out.append({"id": "pnp" + hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:8], "source": "pnp-recorded",
                    "source_label": "Provincial draw you recorded", "tag": "provincial", "province": d["province"], "date": d["date"],
                    "title": f"{PROVINCE_NAME.get(d['province'], d['province'])} {d['stream']} draw: minimum score {d['min_score']}",
                    "detail": [d.get("note", "")], "link": province_page(d["province"]), "pnp": d, "first_seen": d["date"]})
    return [i for i in out if i["date"] >= (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()]


def rule_items(today):
    import alerts as al
    if not al.CHANGELOG.exists():
        return []
    out = []
    for c in al.parse_changes(al.CHANGELOG.read_text(encoding="utf-8")):
        day = al.date_of(c["effective"])
        if not day or not -RULE_BACK <= (day - today).days <= RULE_AHEAD:
            continue
        coming = day > today
        out.append({"id": "kb" + c["id"][:8], "source": "kb-changelog", "source_label": "Knowledge base rule changes (verified)", "tag": "rules",
                    "province": al.province_code(c["change"]), "date": day.isoformat(), "title": ("Coming: " if coming else "") + re.sub(r"\*\*", "", c["change"]),
                    "detail": [f"Confidence {c['conf']} (H = official source)"], "link": c.get("source", ""), "coming": coming, "first_seen": day.isoformat()})
    return out


def fee_items(today):
    import watch as wt
    state = wt.load_state()
    checked = (state.get("fees") or {}).get("checked") or state.get("checked") or today.isoformat()
    out = []
    for kind, text, step in wt.findings(state):
        if kind == "Fee change" or (kind == "Form version" and text.startswith("IRCC has a newer")):
            out.append({"id": "fw" + hashlib.sha256(text.encode()).hexdigest()[:8], "source": "watch", "source_label": "IRCC fee list and form pages",
                        "tag": "fees", "province": None, "date": str(checked)[:10], "title": text, "detail": [step],
                        "link": FEES_PAGE if kind == "Fee change" else form_page(text), "first_seen": str(checked)[:10]})
    return out


def province_page(code):
    """The province's own draw page (or its main immigration page when the agent can't read it)."""
    page = next((url for _, _, prov, url, _ in SOURCES.values() if prov == code), None) or next((url for _, p, url, _ in BY_HAND if p == code), "")
    return year_url(page, datetime.date.today().year) if "{year}" in page else page


def form_page(text):
    import watch as wt
    m = re.search(r"\bIMM\s?(\d{4}[A-Z]?)", text)
    return wt.FORM_PAGE.format("imm" + m.group(1).lower()) if m else ""


def all_items(today=None, state=None):
    """Every item, newest first: saved web items plus Express Entry rounds, recorded PNP draws, rule changes and fee/form changes."""
    today = today or datetime.date.today()
    state = load_state() if state is None else state
    out = list((state.get("items") or {}).values())
    for extra in (ee_items, rule_items, fee_items):
        try:
            out += extra(today)
        except Exception:  # a damaged local file must not hide the web items
            pass
    return dedupe(sorted(out, key=lambda i: (i.get("date", ""), i.get("first_seen", "")), reverse=True))


def same_key(it):
    """Items with the same date and headline (ignoring notes in brackets, case and punctuation) are the same news."""
    title = re.sub(r"\([^)]*\)", " ", it.get("title", "")).lower()
    return it.get("date", ""), re.sub(r"[^a-z0-9]+", " ", title).strip()


def dedupe(items):
    """One item per piece of news: keep the one with a source link, then the one that says more."""
    best = {}
    for it in items:
        k = same_key(it)
        old = best.get(k)
        if old is None or (bool(it.get("link")), len(it.get("title", "")) + len(" ".join(it.get("detail", [])))) >                 (bool(old.get("link")), len(old.get("title", "")) + len(" ".join(old.get("detail", [])))):
            best[k] = it
    keep = {id(v) for v in best.values()}
    return [it for it in items if id(it) in keep]


def window(items, today, days=SHOW_DAYS):
    start = (today - datetime.timedelta(days=days)).isoformat()
    return [i for i in items if i.get("date", "") >= start]


# ---------- matching to open files ----------
def consent_of(info):
    return {"yes": "yes", "no": "no"}.get(str(info.get("contact_ok", "")).strip().lower(), "not recorded")


def case_pool():
    out = []
    for folder in cs.folders(cs.ACTIVE):
        try:
            info = cs.read_case(folder)
        except (OSError, ValueError):
            continue
        out.append({"folder": folder, "name": folder.name, "id": info.get("case_id", folder.name[:8]), "client": info.get("client", ""),
                    "program": info.get("program", ""), "province": info.get("province", ""), "consent": consent_of(info)})
    return out


def files_for(it, pool):
    """[{folder, id, client, why}] open files this item may concern."""
    import alerts as al
    import draws as dr
    out = []
    if it["source"] == "ee-rounds":
        rnd = next((r for r in dr.load_state().get("rounds", []) if r["number"] == it.get("round")), None)
        if rnd:
            for f, info, crs, gap in dr.match_round(rnd, [c["folder"] for c in pool]):
                out.append({"folder": f.name, "id": info.get("case_id", f.name[:8]), "client": info.get("client", ""),
                            "why": f"recorded CRS {crs} ({f'{gap:+d} over' if gap >= 0 else f'{-gap} below'} the cut-off)", "strong": gap >= 0, "consent": consent_of(info)})
        return out
    if it["source"] == "pnp-recorded":
        for f, info, score, gap in dr.match_pnp(it["pnp"], [c["folder"] for c in pool]):
            out.append({"folder": f.name, "id": info.get("case_id", f.name[:8]), "client": info.get("client", ""),
                        "why": f"recorded {it['province']} score {score} ({f'{gap:+d} over' if gap >= 0 else f'{-gap} below'})", "strong": gap >= 0, "consent": consent_of(info)})
        return out
    text = " ".join([it["title"], *it.get("detail", [])])
    if it.get("province"):
        text += f" {PROVINCE_NAME.get(it['province'], '')} " + ("PSTQ quebec" if it["province"] == "QC" else "PNP nominee")
    if it["tag"] == "work":
        text += " LMIA work permit"
    home_only = bool(it.get("province"))  # news about one province only concerns files in that province (or with none recorded)
    for c in pool:
        if home_only and al.province_code(c["province"]) not in (None, it["province"]):
            continue
        if al.matches(text, c):
            out.append({"folder": c["name"], "id": c["id"], "client": c["client"], "why": f"{c['program'] or 'program not set'}"
                        + (f", {c['province']}" if c["province"] else ""), "strong": False, "consent": c["consent"]})
    return out


def with_files(items, pool=None):
    pool = case_pool() if pool is None else pool
    out = []
    for it in items:
        try:
            files = files_for(it, pool) if pool else []
        except Exception:
            files = []
        out.append({**it, "files": files})
    return out


def source_rows(state=None):
    state = load_state() if state is None else state
    rows = []
    for key, (label, tag, prov, url, _) in SOURCES.items():
        s = (state.get("sources") or {}).get(key) or {}
        rows.append({"key": key, "label": label, "tag": tag, "url": year_url(url, datetime.date.today().year) if "{year}" in url else url,
                     "ok": s.get("ok"), "checked": s.get("checked", ""), "error": s.get("error", ""), "count": s.get("count")})
    rows += [{"key": "hand-" + p.lower(), "label": label, "tag": "provincial", "url": url, "ok": None, "checked": "", "error": why, "by_hand": True}
             for label, p, url, why in BY_HAND]
    return rows


def find_item(ident, today=None):
    return next((i for i in all_items(today) if i["id"] == ident), None)


# ---------- command line ----------
def line(it):
    return f"{it['id']:12} {it['date']:10}  [{TAGS.get(it['tag'], it['tag'])}] {it['title']}"


def cmd_check(_):
    print("Reading official sources (public pages; nothing about you or your clients is sent)...")
    state = refresh()
    for r in source_rows(state):
        if r.get("by_hand"):
            continue
        print(f"  {'OK    ' if r['ok'] else 'FAILED'} {r['label']}" + (f": {r['count']} items" if r["ok"] else f": {r['error']}"))
    today = datetime.date.today()
    new = [i for i in window(all_items(today, state), today, 14) if i.get("first_seen") == today.isoformat()]
    print(f"{len(new)} new item(s) today." if new else "No new items today.")
    for it in new[:20]:
        print("  " + line(it))


def cmd_list(a):
    today = datetime.date.today()
    items = window(all_items(today), today, a.days)
    if a.tag:
        items = [i for i in items if i["tag"] == a.tag]
    if not items:
        print("No news saved yet. Run: python3 scripts/news.py check")
    for it in items[:a.n]:
        print(line(it))


def cmd_show(a):
    it = find_item(a.id)
    if not it:
        sys.exit(f"ERROR: no news item {a.id}. Run: news.py list")
    print(line(it))
    for d in it.get("detail", []):
        print("  - " + d)
    print("Source:", it["source_label"], "|", it["link"] or "knowledge/00-meta/changelog.md (see the matching knowledge file for the official source)")
    if a.files:
        files = files_for(it, case_pool())
        print(f"Open files it may concern: {len(files)}")
        for f in files:
            print(f"  {f['id']} {f['client']}: {f['why']} | contact consent: {f['consent']}")
        if any(f["consent"] != "yes" for f in files):
            print("Send news only to clients who agreed to hear from you (anti-spam law, CASL). Record it: opportunities.py consent CASE yes")


def cmd_sources(_):
    for r in source_rows():
        state = "check by hand" if r.get("by_hand") else "never read" if r["ok"] is None else "OK" if r["ok"] else "FAILED"
        print(f"{state:14} {r['label']}  {r['checked'][:16]}  {r['error'] if r['error'] and not r['ok'] else ''}\n               {r['url']}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Immigration news from official sources")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("check"); x.set_defaults(fn=cmd_check)
    x = s.add_parser("list"); x.add_argument("--n", type=int, default=20); x.add_argument("--tag", choices=sorted(TAGS)); x.add_argument("--days", type=int, default=SHOW_DAYS); x.set_defaults(fn=cmd_list)
    x = s.add_parser("show"); x.add_argument("id"); x.add_argument("--files", action="store_true"); x.set_defaults(fn=cmd_show)
    x = s.add_parser("sources"); x.set_defaults(fn=cmd_sources)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
