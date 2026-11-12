#!/usr/bin/env python3
"""LMIA toolkit for employer files (Temporary Foreign Worker Program, ESDC).

  check --province ON --wage 28.50 [--cma Toronto] [--naics 722] [--noc 62200] [--tfw 3 --workforce 20]
        [--days 365] [--date 2026-12-01] [--agricultural] [--caregiver] [--pr-only] [--seasonal]
      stream (wage against the provincial median + 20%), refusal to process, the low-wage cap,
      recruitment, transition plan and fee
  recruit ADS.csv --apply 2026-12-01 --stream high|low [--job-match 2026-10-05]
      checks advertising against the stream's rules. ADS.csv columns:
      method,start,end,national,group   (method: job bank, indeed, ...; national: yes/no;
      group: youth, indigenous, newcomers, disability, vulnerable youth, or blank)

Rules come from knowledge/05-temporary-residence/work-permits-lmia.md; the thresholds and the quarterly
unemployment table are in templates/lmia/ (update them when ESDC does: thresholds each July, the table
each quarter). LMIA applications are filed in LMIA Online; this tool prepares, it doesn't file.
"""
import argparse
import csv
import datetime
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DATA = REPO / "templates" / "lmia"
KB = "knowledge/05-temporary-residence/work-permits-lmia.md"
PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
PROV_NAMES = {"alberta": "AB", "british columbia": "BC", "manitoba": "MB", "new brunswick": "NB", "newfoundland and labrador": "NL", "nova scotia": "NS",
              "northwest territories": "NT", "nunavut": "NU", "ontario": "ON", "prince edward island": "PE", "quebec": "QC", "saskatchewan": "SK", "yukon": "YT"}
CAP_20_NAICS = ("23", "311", "622", "623")  # construction, food manufacturing, hospitals, nursing and residential care
PRIMARY_AG_NOCS = {"80020", "80021", "82030", "82031", "84120", "85100", "85101", "85103"}
RECRUIT = {
    "high": {"weeks": 4, "stars": 4, "rule": "Job Bank + 2 more methods, at least 1 national; 4 consecutive weeks within the 3 months before applying; "
             "invite Job Match candidates rated 4+ stars within 30 days"},
    "low": {"weeks": 8, "stars": 2, "rule": "Job Bank + an effort aimed at youth + 2 more methods, each aimed at a different underrepresented group; "
            "8 consecutive weeks within the 3 months before applying; invite Job Match candidates rated 2+ stars within the first 30 days"},
}
GROUPS = {"youth", "indigenous", "newcomers", "disability", "vulnerable youth", "asylum claimants"}


def load(name):
    with (DATA / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def day(text):
    return datetime.date.fromisoformat(text) if text else None


def threshold(province, when):
    for r in load("wage-thresholds.csv"):
        if r["province"] == province and day(r["from"]) <= when and (not r["to"] or when <= day(r["to"])):
            return float(r["hourly"]), r["from"]
    return None, None


def cma_rate(name, when):
    """(rate, CMA, period) for the CMA whose name contains `name`, in the period covering `when`."""
    rows = [r for r in load("cma-unemployment.csv") if name and name.lower() in r["cma"].lower()]
    if not rows:
        return None, None, None
    for r in rows:
        if day(r["from"]) <= when <= day(r["to"]):
            return float(r["rate"]), r["cma"], (r["from"], r["to"])
    last = max(rows, key=lambda r: r["to"])
    return None, last["cma"], (last["from"], last["to"])


def province_code(text):
    t = (text or "").strip()
    return t.upper() if t.upper() in PROVINCES else PROV_NAMES.get(t.lower())


def check(a):
    """Lines of findings: (level, text). Levels: RESULT, STOP, CHECK, NOTE."""
    out = []
    when = day(a.date) if a.date else datetime.date.today()
    prov = province_code(a.province)
    if not prov:
        sys.exit(f"ERROR: province '{a.province}' not recognized (use AB, BC, ON ...)")
    limit, since = threshold(prov, when)
    if limit is None:
        sys.exit(f"ERROR: no wage threshold for {prov} on {when} in templates/lmia/wage-thresholds.csv. Check ESDC's median wage page and update it")
    ag = a.agricultural or (a.noc in PRIMARY_AG_NOCS)
    if ag:
        out.append(("RESULT", f"Primary agriculture (NOC {a.noc or 'given'}): agricultural stream or SAWP if the commodity is on the national list; otherwise the high- or low-wage stream by wage"))
    high = a.wage >= limit
    stream = "high" if high else "low"
    out.append(("RESULT", f"{'High' if high else 'Low'}-wage stream: ${a.wage:.2f}/h {'is at or above' if high else 'is below'} the {prov} threshold of ${limit:.2f}/h (median + 20%, in force from {since})"))
    if abs(a.wage - limit) / limit < 0.03:
        out.append(("CHECK", "The wage is within 3% of the threshold: confirm the threshold in force on the date ESDC receives the application"))
    out.append(("CHECK", f"The wage must also meet the prevailing wage for the NOC{' ' + a.noc if a.noc else ''} and region on Job Bank"))
    exempt_cap = ag or a.pr_only or (a.days and a.days <= 120) or a.seasonal
    if not high:
        rtp_exempt = ag or a.caregiver or a.pr_only or (a.days and a.days <= 120) or (a.naics and a.naics.startswith(CAP_20_NAICS)) or (a.noc == "42202" and when >= datetime.date(2026, 11, 6))
        if a.cma:
            rate, cma, period = cma_rate(a.cma, when)
            if cma is None:
                out.append(("CHECK", f"'{a.cma}' isn't a census metropolitan area on ESDC's list: the refusal to process rule doesn't apply outside CMAs. Confirm the work location"))
            elif rate is None:
                out.append(("STOP", f"No unemployment rate stored for {cma} on {when} (stored up to {period[1]}). Update templates/lmia/cma-unemployment.csv from ESDC's refusal page"))
            elif rate >= 6.0 and not rtp_exempt:
                out.append(("STOP", f"Refused to process: {cma} unemployment {rate}% (6% or more) for applications {period[0]} to {period[1]}. Low-wage LMIAs there aren't processed unless an exemption applies"))
            elif rate >= 6.0:
                out.append(("NOTE", f"{cma} is at {rate}% (6% or more), but this position is exempt from the refusal to process"))
            else:
                out.append(("RESULT", f"{cma}: {rate}% for applications {period[0]} to {period[1]}, under 6%: not refused to process"))
            if rate is not None and period and (day(period[1]) - when).days <= 30:
                out.append(("CHECK", f"The list changes after {period[1]}: file before then, or re-check the new rate"))
        else:
            out.append(("CHECK", "Give the work location's CMA (--cma) to check the refusal to process list"))
        if prov == "QC":
            out.append(("CHECK", "Quebec: Montréal and Laval low-wage restrictions differ (knowledge/03-quebec)"))
        if exempt_cap:
            out.append(("RESULT", "Low-wage cap doesn't apply (primary agriculture, PR-only, 120 days or less, or seasonal up to 270 days)"))
        else:
            cap = 0.20 if (a.naics and a.naics.startswith(CAP_20_NAICS)) or a.caregiver else 0.10
            if a.tfw is not None and a.workforce:
                allowed = (1 if cap == 0.10 else 2) if a.workforce < 10 else a.workforce * cap
                after = a.tfw + a.positions
                verdict = "within" if after <= allowed + 1e-9 else "OVER"
                out.append(("RESULT" if verdict == "within" else "STOP",
                            f"Cap {int(cap * 100)}%: {a.tfw} low-wage TFWs now + {a.positions} requested = {after}; allowed {allowed:g} for a workforce of {a.workforce}: {verdict} the cap"))
            else:
                out.append(("CHECK", f"Cap {int(cap * 100)}% of the workforce at the work location: give --tfw and --workforce to check"))
        if a.days and a.days > 365 and when >= datetime.date(2026, 11, 6):
            out.append(("NOTE", "Low-wage LMIAs can be for up to 2 years for applications on or after 2026-11-06"))
    else:
        if not (a.caregiver or ag or a.pr_only):
            out.append(("CHECK", "Transition plan required (unless an exemption applies: caregiver, agriculture, PR-only, limited duration or unique skills)"))
    if not ag:
        out.append(("CHECK", "Recruitment: " + RECRUIT[stream]["rule"]))
    fee = "no LMIA fee for in-home caregiver or on-farm primary agriculture positions" if (a.caregiver or ag) else f"${1000 * a.positions:,} (${1000:,} per position, can't be recovered from the worker)"
    out.append(("NOTE", f"LMIA fee: {fee}. Employment agreement: EMP5711 (high-wage) or EMP5712 (low-wage), signed by the first day of work. Representative: EMP5575"))
    return out


def weeks_in_window(start, end, window_start, apply):
    s, e = max(start, window_start), min(end, apply)
    return max((e - s).days + 1, 0) / 7


def recruit(rows, apply, stream, job_match=None):
    """Findings for advertising rows against the stream's rules."""
    out, need = [], RECRUIT[stream]
    window = apply - datetime.timedelta(days=91)  # the 3 months before applying
    ads = []
    for r in rows:
        try:
            start, end = day(r["start"].strip()), day((r.get("end") or "").strip() or apply.isoformat())
        except ValueError:
            out.append(("STOP", f"Dates not understood for '{r.get('method')}': use YYYY-MM-DD"))
            continue
        ads.append({"method": r["method"].strip(), "start": start, "end": end, "national": (r.get("national") or "").strip().lower() in ("yes", "y", "true", "1"),
                    "group": (r.get("group") or "").strip().lower(), "weeks": weeks_in_window(start, end, window, apply)})
    ok = [x for x in ads if x["weeks"] >= need["weeks"]]
    short = [x for x in ads if x not in ok]
    for x in short:
        out.append(("STOP", f"{x['method']}: {x['weeks']:.1f} weeks within the 3 months before {apply} ({window} to {apply}); {need['weeks']} consecutive weeks needed"))
    jb = [x for x in ok if re.search(r"job ?bank", x["method"], re.I)]
    others = [x for x in ok if x not in jb]
    out.append(("RESULT" if jb else "STOP", "Job Bank ad: " + (f"yes, from {jb[0]['start']}" if jb else "missing or too short (required)")))
    if stream == "high":
        out.append(("RESULT" if len(others) >= 2 else "STOP", f"Other methods long enough: {len(others)} of 2 needed" + (f" ({', '.join(x['method'] for x in others)})" if others else "")))
        national = [x for x in ok if x["national"]]
        out.append(("RESULT" if national else "STOP", "National method: " + (", ".join(x["method"] for x in national) if national else "none (at least 1 needed)")))
    else:
        youth = [x for x in others if "youth" in x["group"]]
        groups = {x["group"] for x in others if x["group"] and x not in youth[:1]}
        out.append(("RESULT" if youth else "STOP", "Effort aimed at youth: " + (youth[0]["method"] if youth else "none (required)")))
        out.append(("RESULT" if len(groups) >= 2 else "STOP", f"Methods aimed at different underrepresented groups (besides youth): {len(groups)} of 2" + (f" ({', '.join(sorted(groups))})" if groups else "")))
        unknown = sorted({x["group"] for x in others if x["group"] and x["group"] not in GROUPS})
        if unknown:
            out.append(("CHECK", f"Group(s) not recognized: {', '.join(unknown)}. ESDC's groups include youth, Indigenous people, newcomers, persons with disabilities and vulnerable youth"))
    if jb:
        due = jb[0]["start"] + datetime.timedelta(days=30)
        if job_match is None:
            out.append(("CHECK", f"Job Match: invite candidates rated {need['stars']}+ stars by {due} (30 days from the Job Bank ad) and keep the record"))
        else:
            out.append(("RESULT" if job_match <= due else "STOP", f"Job Match invitations sent {job_match}: {'within' if job_match <= due else 'AFTER'} the 30 days (by {due})"))
    out.append(("NOTE", "Keep proof of every ad (copies, dates, where it ran) and a record of candidates and why each was not hired"))
    return out


def show(lines):
    for level, text in lines:
        print(f"{level:7} {text}")


def cmd_check(a):
    show(check(a))
    print(f"\nRules: {KB}. Check ESDC's pages before filing; the thresholds change each July and the unemployment table each quarter.")


def cmd_recruit(a):
    path = pathlib.Path(a.ads)
    if not path.is_file():
        sys.exit(f"ERROR: {path} not found")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or "method" not in rows[0] or "start" not in rows[0]:
        sys.exit("ERROR: the file needs the columns method,start,end,national,group")
    show(recruit(rows, day(a.apply), a.stream, day(a.job_match) if a.job_match else None))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="LMIA stream, eligibility and recruitment checks")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("check"); x.add_argument("--province", required=True); x.add_argument("--wage", type=float, required=True)
    x.add_argument("--cma"); x.add_argument("--naics"); x.add_argument("--noc"); x.add_argument("--tfw", type=int); x.add_argument("--workforce", type=int)
    x.add_argument("--positions", type=int, default=1); x.add_argument("--days", type=int); x.add_argument("--date")
    for flag in ("--agricultural", "--caregiver", "--pr-only", "--seasonal"):
        x.add_argument(flag, action="store_true")
    x.set_defaults(fn=cmd_check)
    x = s.add_parser("recruit"); x.add_argument("ads"); x.add_argument("--apply", required=True); x.add_argument("--stream", choices=["high", "low"], required=True)
    x.add_argument("--job-match"); x.set_defaults(fn=cmd_recruit)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
