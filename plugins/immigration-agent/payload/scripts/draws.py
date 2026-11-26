#!/usr/bin/env python3
"""Draw matcher: after each Express Entry round (or a provincial draw you record), list the clients at or near the cut-off.

Usage:
  python3 scripts/draws.py profile CASE --crs 485 [--eligible cec,french] [--profile-date YYYY-MM-DD] [--pnp BC:115,SK:82]
  python3 scripts/draws.py check                 read IRCC's rounds feed (public; nothing about you or your clients is sent) and match
  python3 scripts/draws.py latest [--n 10]       rounds saved at the last check
  python3 scripts/draws.py match [--round N]     match one saved round (default: the latest) against every open file
  python3 scripts/draws.py pnp-add --province BC --stream "Skills Immigration" --date YYYY-MM-DD --min-score 110 [--note TEXT]
  python3 scripts/draws.py categories

--eligible lists the rounds the client can be invited in besides general rounds:
  cec, fsw, fst, pnp, french, healthcare, trades, stem, education, transport, physicians, senior-managers, researchers, military
(category eligibility is your assessment: the agent can't verify it).

Guarantees:
  - The CRS score is the one you record for the client. A match means the recorded score is at or above the round's
    cut-off, not that an invitation was issued: ties are broken by the profile's submission time, and the profile must
    have been in the pool before the round's cut-off time. Check the client's IRCC account.
  - Express Entry rounds come from IRCC's own feed only (third-party draw trackers disagree with IRCC).
  - The daily alerts read the feed once a day and flag clients matched by a round of the last 14 days.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402

FEED = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
ROUNDS_PAGE = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations.html"
ROUND_PAGE = ("https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/policies-operational-instructions-agreements/"
              "ministerial-instructions/express-entry-rounds/invitations.html?q={n}")
STATE = cs.ROOT / ".draws-state.json"
KEEP = 200          # rounds saved: about two years, so the IRCC data tab can total a whole year
NEAR = 10            # points below the cut-off still worth a look
RECENT_DAYS = 14     # a round this recent is flagged in the daily alerts
EVERY_HOURS = 20
CATEGORIES = [  # (key, pattern in IRCC's round name, plain name)
    ("cec", r"canadian experience", "Canadian Experience Class"),
    ("fsw", r"federal skilled worker", "Federal Skilled Worker"),
    ("fst", r"federal skilled trades", "Federal Skilled Trades"),
    ("pnp", r"provincial nominee", "Provincial Nominee Program"),
    ("french", r"french", "French-language proficiency"),
    ("healthcare", r"health", "Healthcare and social services"),
    ("trades", r"\btrade", "Trades"),
    ("stem", r"\bstem\b|science, technology", "STEM"),
    ("education", r"education", "Education"),
    ("transport", r"transport", "Transport"),
    ("physicians", r"physician", "Physicians with Canadian work experience"),
    ("senior-managers", r"senior manager", "Senior managers with Canadian work experience"),
    ("researchers", r"research", "Researchers with Canadian work experience"),
    ("military", r"military", "Skilled military recruits"),
    ("agriculture", r"agri", "Agriculture and agri-food"),
]
KEYS = {k for k, _, _ in CATEGORIES}


def die(msg):
    sys.exit("ERROR: " + msg)


def category(name):
    for key, rx, _ in CATEGORIES:
        if re.search(rx, name, re.I):
            return key
    return "general"  # "No Program Specified" and anything not named: every candidate can be invited


def num(text):
    try:
        return int(str(text).replace(",", "").strip())
    except ValueError:
        return None


def round_url(n, html=""):
    """IRCC's page for one round (its Ministerial Instructions). The feed gives an internal path; the public page is the same path on canada.ca."""
    m = re.search(r"href='([^']*invitations\.html\?q=\d+)'", html or "")
    if m:
        return "https://www.canada.ca" + m.group(1).replace("/content/canadasite", "", 1)
    return ROUND_PAGE.format(n=n)


def parse_feed(text):
    data = json.loads(text)
    out = []
    for r in data.get("rounds", []):
        n, crs = num(r.get("drawNumber")), num(r.get("drawCRS"))
        try:
            day = datetime.date.fromisoformat(r.get("drawDate", ""))
        except ValueError:
            continue
        if n is None or crs is None:
            continue
        out.append({"number": n, "date": day.isoformat(), "name": r.get("drawName", ""), "category": category(r.get("drawName", "")),
                    "size": num(r.get("drawSize")), "crs": crs, "tiebreak": r.get("drawCutOff", ""), "programs": r.get("drawText2", ""),
                    "url": round_url(n, r.get("drawNumberURL", ""))})
    if not out:
        raise ValueError("no rounds in IRCC's feed (its layout may have changed)")
    return sorted(out, key=lambda r: -r["number"])


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


def refresh():
    """Read the feed and save it. Returns (state, new rounds since the last check)."""
    import watch as wt
    text = wt.fetch(FEED)
    if not text:
        raise ConnectionError("IRCC's rounds feed couldn't be read (no internet, or the page moved)")
    rounds = parse_feed(text)
    state = load_state()
    last = state.get("latest", 0)
    new = [r for r in rounds if r["number"] > last] if last else []
    state.update(rounds=rounds[:KEEP], latest=rounds[0]["number"], checked=datetime.datetime.now().isoformat(timespec="seconds"))
    save_state(state)
    return state, new


def stale(now=None):
    checked = load_state().get("checked")
    if not checked:
        return True
    now = now or datetime.datetime.now()
    return (now - datetime.datetime.fromisoformat(checked)).total_seconds() >= EVERY_HOURS * 3600


def profile_of(folder):
    info = cs.read_case(folder)
    crs = num(info.get("crs_score", ""))
    eligible = {x.strip().lower() for x in re.split(r"[,; ]+", info.get("ee_eligible", "")) if x.strip()}
    pnp = {}
    for part in re.split(r"[,;]+", info.get("pnp_scores", "")):
        if ":" in part:
            prov, score = part.split(":", 1)
            if num(score) is not None:
                pnp[prov.strip().upper()] = num(score)
    return info, crs, eligible, pnp


def match_round(rnd, pool=None):
    """Open files at or near an Express Entry round's cut-off: [(folder, info, crs, gap)]. gap >= 0 means at or above."""
    out = []
    for folder in pool if pool is not None else cs.folders(cs.ACTIVE):
        try:
            info, crs, eligible, _ = profile_of(folder)
        except (OSError, ValueError):
            continue
        if crs is None:
            continue
        if rnd["category"] != "general" and rnd["category"] not in eligible:
            continue
        gap = crs - rnd["crs"]
        if gap >= -NEAR:
            out.append((folder, info, crs, gap))
    return sorted(out, key=lambda x: -x[3])


def match_pnp(draw, pool=None):
    out = []
    for folder in pool if pool is not None else cs.folders(cs.ACTIVE):
        try:
            info, _, _, pnp = profile_of(folder)
        except (OSError, ValueError):
            continue
        score = pnp.get(draw["province"])
        if score is not None and score - draw["min_score"] >= -NEAR:
            out.append((folder, info, score, score - draw["min_score"]))
    return sorted(out, key=lambda x: -x[3])


def describe(rnd):
    return f"Round #{rnd['number']} on {rnd['date']}: {rnd['name']}, {rnd['size'] or '?'} invitations, lowest CRS {rnd['crs']}"


def print_matches(rnd, hits):
    print(describe(rnd))
    if not hits:
        print("  No open file with a recorded CRS score is at or within 10 points of the cut-off.")
    for folder, info, crs, gap in hits:
        state = f"{gap:+d} over the cut-off" if gap >= 0 else f"{-gap} below"
        print(f"  {info.get('case_id', folder.name[:8])} {info.get('client', '')}: recorded CRS {crs} ({state})")
    if any(g >= 0 for *_, g in hits):
        print(f"  Check each client's IRCC account for an invitation. Ties: profiles submitted before {rnd['tiebreak'] or 'the cut-off time'}. The ITA period is 60 days.")


def cmd_profile(a):
    folder = cs.find(a.case)
    text = (folder / "case.md").read_text(encoding="utf-8")
    head = text.split("\n---", 1)[0]
    for key in ("crs_score", "ee_eligible", "pnp_scores"):
        if not re.search(rf"(?m)^{key}:", head):
            text = re.sub(r"\A---\n", f"---\n{key}:\n", text, count=1)
            head = text.split("\n---", 1)[0]
    (folder / "case.md").write_text(text, encoding="utf-8")
    if a.crs is not None:
        cs.write_key(folder, "crs_score", str(a.crs))
    if a.eligible is not None:
        bad = {x.strip().lower() for x in a.eligible.split(",") if x.strip()} - KEYS
        if bad:
            die("unknown round type(s): " + ", ".join(sorted(bad)) + ". Run: draws.py categories")
        cs.write_key(folder, "ee_eligible", a.eligible.lower())
    if a.pnp is not None:
        cs.write_key(folder, "pnp_scores", a.pnp.upper())
    if a.profile_date:
        import validity as vd
        day = cs.parse_date(a.profile_date, "--profile-date")
        vd.append(folder, cs.read_case(folder).get("client", ""), "ee_profile", day, "from draws.py profile")
        print(f"Express Entry profile date {day} tracked: it is removed after 12 months (validity.py).")
    cs.add_log(folder, "Draw profile updated: " + ", ".join(f"{k} {v}" for k, v in (("CRS", a.crs), ("eligible", a.eligible), ("PNP", a.pnp)) if v is not None))
    info, crs, eligible, pnp = profile_of(folder)
    print(f"{folder.name}: CRS {crs if crs is not None else 'not set'} | eligible for: general{', ' + ', '.join(sorted(eligible)) if eligible else ''} rounds"
          + (f" | PNP scores: {', '.join(f'{k} {v}' for k, v in pnp.items())}" if pnp else ""))
    print("Update the score whenever the profile changes (new test, birthday, more experience, job offer).")


def cmd_check(_):
    print("Reading IRCC's Express Entry rounds (public page; nothing about you or your clients is sent)...")
    try:
        state, new = refresh()
    except (ConnectionError, ValueError) as e:
        die(str(e))
    print(f"Latest round: #{state['latest']} ({state['rounds'][0]['date']}).")
    if not new:
        print("No new round since the last check." if load_state().get("latest") else "")
        print_matches(state["rounds"][0], match_round(state["rounds"][0]))
        return
    print(f"{len(new)} new round(s):")
    for rnd in new:
        print_matches(rnd, match_round(rnd))


def cmd_latest(a):
    state = load_state()
    if not state.get("rounds"):
        die("no rounds saved yet. Run: draws.py check")
    print(f"Checked {state.get('checked', '?')}")
    for r in state["rounds"][:a.n]:
        print("  " + describe(r))
    for d in state.get("pnp", [])[-a.n:]:
        print(f"  PNP {d['province']} {d['stream']} on {d['date']}: minimum score {d['min_score']}" + (f" ({d['note']})" if d.get("note") else ""))


def cmd_match(a):
    state = load_state()
    rounds = state.get("rounds") or []
    if not rounds:
        die("no rounds saved yet. Run: draws.py check")
    rnd = next((r for r in rounds if r["number"] == a.round), None) if a.round else rounds[0]
    if not rnd:
        die(f"round #{a.round} isn't among the {len(rounds)} saved rounds")
    if not getattr(a, "case", None):
        print_matches(rnd, match_round(rnd))
        return
    folder = cs.find(a.case)  # one file: its score against the round, however far from the cut-off
    info, crs, eligible, _ = profile_of(folder)
    print(describe(rnd))
    who = f"{info.get('case_id', folder.name[:8])} {info.get('client', '')}"
    if crs is None:
        print(f"  {who}: no CRS score recorded. Record it: draws.py profile {a.case} --crs SCORE")
    elif rnd["category"] != "general" and rnd["category"] not in eligible:
        print(f"  {who}: recorded CRS {crs}, but the file isn't marked eligible for this round's category ({rnd['category']}). draws.py profile {a.case} --eligible ...")
    else:
        gap = crs - rnd["crs"]
        print(f"  {who}: recorded CRS {crs} ({f'{gap:+d} over the cut-off' if gap >= 0 else f'{-gap} below'})")
        if gap >= 0:
            print("  Check the client's IRCC account for an invitation. The ITA period is 60 days.")


def cmd_pnp_add(a):
    day = cs.parse_date(a.date, "--date")
    state = load_state()
    draw = {"province": a.province.upper(), "stream": a.stream, "date": day.isoformat(), "min_score": a.min_score, "note": a.note or "",
            "recorded": datetime.datetime.now().isoformat(timespec="seconds")}
    state.setdefault("pnp", []).append(draw)
    save_state(state)
    print(f"Recorded: {draw['province']} {draw['stream']} on {draw['date']}, minimum score {draw['min_score']}. Check the province's own page for the stream rules.")
    hits = match_pnp(draw)
    if not hits:
        print(f"  No open file has a recorded {draw['province']} score within {NEAR} points.")
    for folder, info, score, gap in hits:
        print(f"  {info.get('case_id', folder.name[:8])} {info.get('client', '')}: recorded {draw['province']} score {score} ({f'{gap:+d} over' if gap >= 0 else f'{-gap} below'})")


def cmd_categories(_):
    for key, _, name in CATEGORIES:
        print(f"{key:16} {name}")
    print("Rounds of other types (No Program Specified) are general: every candidate in the pool can be invited.")
    print("2026 categories: knowledge/01-federal-economic/category-draws-history.md")


def issues(folder, today, state=None):
    """Alerts for one case from the saved rounds: (rank, kind, tier, text, step, day)."""
    state = load_state() if state is None else state
    out = []
    for rnd in state.get("rounds", []):
        day = datetime.date.fromisoformat(rnd["date"])
        if (today - day).days > RECENT_DAYS:
            break
        for f, info, crs, gap in match_round(rnd, [folder]):
            if gap >= 0:
                out.append((2, "Draw", "at cut-off", f"{describe(rnd)}. Recorded CRS {crs} is at or above it",
                            "Check the client's IRCC account for an invitation (60 days to apply)", day))
    for d in state.get("pnp", []):
        day = datetime.date.fromisoformat(d["date"])
        if (today - day).days <= RECENT_DAYS:
            for f, info, score, gap in match_pnp(d, [folder]):
                if gap >= 0:
                    out.append((2, "Draw", "PNP", f"{d['province']} {d['stream']} draw on {d['date']}, minimum {d['min_score']}: recorded score {score}",
                                "Check the client's provincial account for an invitation", day))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Express Entry and PNP draw matcher")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("profile"); x.add_argument("case"); x.add_argument("--crs", type=int); x.add_argument("--eligible"); x.add_argument("--profile-date"); x.add_argument("--pnp"); x.set_defaults(fn=cmd_profile)
    x = s.add_parser("check"); x.set_defaults(fn=cmd_check)
    x = s.add_parser("latest"); x.add_argument("--n", type=int, default=10); x.set_defaults(fn=cmd_latest)
    x = s.add_parser("match"); x.add_argument("case", nargs="?", help="one file only (default: every open file)"); x.add_argument("--round", type=int); x.set_defaults(fn=cmd_match)
    x = s.add_parser("pnp-add"); x.add_argument("--province", required=True); x.add_argument("--stream", required=True); x.add_argument("--date", required=True)
    x.add_argument("--min-score", type=int, required=True); x.add_argument("--note"); x.set_defaults(fn=cmd_pnp_add)
    x = s.add_parser("categories"); x.set_defaults(fn=cmd_categories)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
