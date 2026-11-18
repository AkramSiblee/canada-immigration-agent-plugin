#!/usr/bin/env python3
"""Comprehensive Ranking System (CRS) calculator, grid in force from 2026-11-03 (MI 2026-1).

  python3 scripts/crs.py --age 29 --education bachelor --eca --first 9,9,8,8 --cwe 2 --foreign 3
  python3 scripts/crs.py --dob 1996-12-20 --expected-ita 2027-01-15 --education master --eca \\
      --first 8,8,7,7 --french 7,7,7,7 --cwe 1 --hw 1.5x:14 --offer-noc 21231 \\
      --spouse --spouse-education bachelor --spouse-eca --spouse-first 7,7,7,7 --spouse-cwe 0
  python3 scripts/crs.py --noc 21231          # high-wage level lookup only
  add --what-if for ranked improvement levers, --json for machine output.

Language scores are CLB/NCLC per ability, four values (use scripts/clb.py to convert test scores). Points are per
ability and the thresholds use the lowest ability, so the order doesn't change the score; write them in clb.py's
order (speaking,listening,reading,writing) to avoid mix-ups. --first is the language the client uses as first official language; --second the other one
(or --french to give French scores; the French bonus is worked out automatically).

Education values: none, secondary, one-year, two-year, bachelor, two-or-more, master, doctorate.
A foreign credential counts only with an ECA (--eca / --spouse-eca); a Canadian credential needs --canadian-edu.

Labour market integration (MI 2026-1 s.15): the greater of (i) Canadian work experience points plus the high-wage
experience bonus, or (ii) a qualifying high-wage job offer; never both; capped at 150 single / 140 with spouse.
The high-wage level comes from the OCCUPATION (templates/ee/high-wage.csv), never from the client's own pay.

Every number below mirrors knowledge/01-federal-economic/crs-scoring.md; test_crs.py checks the KB still states
them. Decision support only: the consultant confirms every input against the documents.
"""
import argparse
import csv
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HIGH_WAGE = ROOT / "templates" / "ee" / "high-wage.csv"
KB = "knowledge/01-federal-economic/crs-scoring.md"

# Age: (with spouse, single)
AGE = {17: (0, 0), 18: (90, 99), 19: (95, 105), 30: (95, 105), 31: (90, 99), 32: (85, 94), 33: (80, 88),
       34: (75, 83), 35: (70, 77), 36: (65, 72), 37: (60, 66), 38: (55, 61), 39: (50, 55), 40: (45, 50),
       41: (35, 39), 42: (25, 28), 43: (15, 17), 44: (5, 6)}
EDU_LEVELS = ["none", "secondary", "one-year", "two-year", "bachelor", "two-or-more", "master", "doctorate"]
EDU = {"none": (0, 0), "secondary": (28, 30), "one-year": (84, 90), "two-year": (91, 98), "bachelor": (112, 120),
       "two-or-more": (119, 128), "master": (126, 135), "doctorate": (140, 150)}
SPOUSE_EDU = {"none": 0, "secondary": 2, "one-year": 6, "two-year": 7, "bachelor": 8, "two-or-more": 9,
              "master": 10, "doctorate": 10}
CWE = {0: (0, 0), 1: (35, 40), 2: (46, 53), 3: (56, 64), 4: (63, 72), 5: (70, 80)}
SPOUSE_CWE = {0: 0, 1: 5, 2: 7, 3: 8, 4: 9, 5: 10}
OFFER = {"2x": 100, "1.5x": 70, "1.3x": 50}
HW_BONUS = {"2x": 70, "1.5x": 40, "1.3x": 20}
LMI_CAP = (140, 150)
SECOND_CAP = (22, 24)


def first_lang_pts(clb, spouse):
    i = 0 if spouse else 1
    if clb >= 10: return (32, 34)[i]
    if clb == 9: return (29, 31)[i]
    if clb == 8: return (22, 23)[i]
    if clb == 7: return (16, 17)[i]
    if clb == 6: return (8, 9)[i]
    if clb >= 4: return 6
    return 0


def second_lang_pts(clb):
    return 6 if clb >= 9 else 3 if clb >= 7 else 1 if clb >= 5 else 0


def spouse_lang_pts(clb):
    return 5 if clb >= 9 else 3 if clb >= 7 else 1 if clb >= 5 else 0


def age_pts(age, spouse):
    if age is None:
        return 0
    if 20 <= age <= 29:
        return 100 if spouse else 110
    if age >= 45 or age < 17:
        return 0
    return AGE[age][0 if spouse else 1]


def age_on(dob, day):
    return day.year - dob.year - ((day.month, day.day) < (dob.month, dob.day))


def load_high_wage(path=HIGH_WAGE):
    if not path.exists():
        return {}, "missing"
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    date = max((r.get("page_modified", "") for r in rows), default="")
    return {r["noc"].strip().zfill(5): (r["level"].strip(), r.get("title", "").strip()) for r in rows}, date or "unknown"


def langs(s):
    if not s:
        return None
    v = [int(x) for x in str(s).replace(" ", "").split(",")]
    if len(v) != 4:
        raise ValueError("language needs four CLB values (speaking,listening,reading,writing)")
    return v


def hw_bonus(hw):
    """hw: {'2x': months, '1.5x': months, '1.3x': months} of Canadian high-wage experience (s.15.1(8))."""
    m2, m15, m13 = hw.get("2x", 0), hw.get("1.5x", 0), hw.get("1.3x", 0)
    if m2 >= 12:
        return 70, "12+ months at the 2x level"
    if m15 >= 12 or m15 + m2 >= 12:
        return 40, "12+ months at 1.5x (or 1.5x combined with 2x)"
    if m13 >= 12 or m2 + m15 + m13 >= 12:
        return 20, "12+ months at 1.3x or any combination of levels"
    return 0, "under 12 months of high-wage experience"


def calc(p):
    """p: dict of inputs (see main). Returns {'lines': [...], 'total': int, 'warnings': [...], 'sections': {...}}."""
    lines, warn = [], []
    sp = bool(p.get("spouse"))
    i = 1 if not sp else 0

    def add(section, factor, value, pts, rule=""):
        lines.append({"section": section, "factor": factor, "input": value, "points": pts, "rule": rule})
        return pts

    # Age
    age = p.get("age")
    if p.get("dob"):
        today = p.get("as_of") or datetime.date.today()
        age = age_on(p["dob"], today)
        ita = p.get("expected_ita")
        if ita:
            a2 = age_on(p["dob"], ita)
            if age_pts(a2, sp) < age_pts(age, sp):
                warn.append(f"Birthday before the expected ITA ({ita}): age {age} -> {a2}, age points "
                            f"{age_pts(age, sp)} -> {age_pts(a2, sp)}. CRS is recalculated on the birthday.")
    core = add("A core", "Age", age, age_pts(age, sp), "20-29 = max; drops each year from 30; 0 at 45+")

    # Education
    entered = p.get("education", "none")
    edu = entered
    if edu not in ("none", "secondary") and not (p.get("eca") or p.get("canadian_edu")):
        warn.append("Principal's post-secondary credential scored 0: a foreign credential counts only with an ECA "
                    "(add --eca, or --canadian-edu for a Canadian credential).")
        edu = "none"
    core += add("A core", "Education", entered if edu == entered else f"{entered} (no ECA: scored as none)", EDU[edu][i])

    # Languages
    first = p.get("first") or [0, 0, 0, 0]
    second = p.get("second")
    if p.get("first_is_english", True):
        if p.get("french") and not second:
            second = p["french"]
        elif second and not p.get("french"):
            p = dict(p, french=second)  # English first: the second official language is French
    fl = sum(first_lang_pts(c, sp) for c in first)
    core += add("A core", "First official language", first, fl, "per ability: CLB 4-5 6, 6 8/9, 7 16/17, 8 22/23, 9 29/31, 10+ 32/34")
    if second:
        sl = min(sum(second_lang_pts(c) for c in second), SECOND_CAP[i])
        core += add("A core", "Second official language", second, sl, f"per ability 1/3/6; cap {SECOND_CAP[i]}")

    # Labour market integration
    cwe = min(int(p.get("cwe", 0)), 5)
    cwe_pts = CWE[cwe][i]
    hw = p.get("hw", {})
    bad = [k for k in hw if k not in HW_BONUS]
    if bad:
        raise ValueError(f"high-wage level must be 2x, 1.5x or 1.3x (got {', '.join(bad)})")
    bonus, why = hw_bonus(hw)
    if cwe < 1 and bonus:
        bonus, why = 0, "no bonus without at least 1 year of Canadian work experience"
    if sum(hw.values()) > max(int(p.get("cwe", 0)), 0) * 12 + 11:
        warn.append("High-wage months entered exceed the Canadian work experience entered: check both.")
    route_i = cwe_pts + bonus
    offer_level = p.get("offer_level")
    route_ii = OFFER.get(offer_level, 0)
    lmi = min(max(route_i, route_ii), LMI_CAP[i])
    chosen = "Canadian experience" if route_i >= route_ii else "job offer"
    core += add("A core", "Labour market integration", f"CWE {cwe} yr (+{bonus}: {why}) vs offer {offer_level or 'none'}",
                lmi, f"greater of {route_i} (CWE {cwe_pts} + high-wage {bonus}) or {route_ii} (offer); never both; cap {LMI_CAP[i]}; uses {chosen}")
    if p.get("offer_noc") and not offer_level:
        warn.append(f"Job offer NOC {p['offer_noc']} is not on the high-wage list: the offer earns 0 CRS points.")
    if offer_level:
        warn.append("Job offer points need a genuine full-time offer of 1+ year from PR visa issuance (TEER 0-3, one employer; "
                    "trades up to two). No LMIA needed. An offer from the client's own company is a high genuineness risk.")

    # Spouse factors
    spouse_total = 0
    if sp:
        se = p.get("spouse_education", "none")
        if se not in ("none", "secondary") and not (p.get("spouse_eca") or p.get("spouse_canadian_edu")):
            spouse_total += add("B spouse", "Spouse education", se, 0, "foreign credential without ECA scores 0 (add --spouse-eca)")
            warn.append("Spouse education scored 0: no ECA flagged. An ECA for the spouse may add points (see --what-if).")
        else:
            spouse_total += add("B spouse", "Spouse education", se, SPOUSE_EDU[se])
        sfl = p.get("spouse_first")
        spouse_total += add("B spouse", "Spouse first official language", sfl or "no test",
                            sum(spouse_lang_pts(c) for c in sfl) if sfl else 0, "per ability 1/3/5; max 20")
        scwe = min(int(p.get("spouse_cwe", 0)), 5)
        spouse_total += add("B spouse", "Spouse Canadian work experience", scwe, SPOUSE_CWE[scwe])

    # Skill transferability
    minfirst = min(first)
    post_secondary = edu in EDU_LEVELS[2:]
    high_edu = edu in ("two-or-more", "master", "doctorate")
    if not (p.get("eca") or p.get("canadian_edu")) and post_secondary:
        pass  # warned above
    e_lang = 0
    if post_secondary:
        if minfirst >= 9:
            e_lang = 50 if high_edu else 25
        elif minfirst >= 7:
            e_lang = 25 if high_edu else 13
    e_cwe = 0
    if post_secondary and cwe >= 1:
        e_cwe = (50 if high_edu else 25) if cwe >= 2 else (25 if high_edu else 13)
    edu_combo = min(e_lang + e_cwe, 50)
    foreign = int(p.get("foreign", 0))
    f_lang = f_cwe = 0
    if foreign >= 1:
        big = foreign >= 3
        if minfirst >= 9:
            f_lang = 50 if big else 25
        elif minfirst >= 7:
            f_lang = 25 if big else 13
        if cwe >= 2:
            f_cwe = 50 if big else 25
        elif cwe == 1:
            f_cwe = 25 if big else 13
    for_combo = min(f_lang + f_cwe, 50)
    coq = 0
    if p.get("coq"):
        coq = 50 if minfirst >= 7 else 25 if minfirst >= 5 else 0
    trans = min(edu_combo + for_combo + coq, 100)
    add("C transferability", "Education + language / CWE", f"{edu}; min CLB {minfirst}; CWE {cwe}", edu_combo, f"{e_lang} + {e_cwe}, cap 50")
    add("C transferability", "Foreign experience + language / CWE", f"foreign {foreign} yr", for_combo, f"{f_lang} + {f_cwe}, cap 50")
    if p.get("coq"):
        add("C transferability", "Certificate of qualification + language", f"min CLB {minfirst}", coq, "CLB 5+ 25; CLB 7+ 50")
    add("C transferability", "Transferability total", "", trans, "cap 100")

    # Additional
    extra = 0
    if p.get("pnp"):
        extra += add("D additional", "Provincial nomination", "yes", 600)
    fr = p.get("french")
    if fr and min(fr) >= 7:
        eng = p.get("first") if p.get("first_is_english", True) else p.get("second")
        eng_ok = eng and min(eng) >= 5
        extra += add("D additional", "French bonus", f"NCLC {min(fr)}+ all four; English {'CLB 5+ all four' if eng_ok else 'CLB 4 or lower / none'}",
                     50 if eng_ok else 25, "25 or 50")
    cs = p.get("canadian_study")
    if cs in ("1-2", "3+"):
        extra += add("D additional", "Canadian post-secondary study", cs, 15 if cs == "1-2" else 30)
    if p.get("sibling"):
        extra += add("D additional", "Sibling in Canada (18+, citizen/PR)", "yes", 15)
    extra = min(extra, 600)

    total = core + spouse_total + trans + extra
    return {"lines": lines, "total": total, "warnings": warn,
            "sections": {"core": core, "spouse": spouse_total, "transferability": trans, "additional": extra}}


def what_if(p):
    """Ranked levers: each re-runs calc on a changed profile."""
    base = calc(p)["total"]
    tries = []

    def t(label, **chg):
        q = dict(p)
        q.update(chg)
        gain = calc(q)["total"] - base
        if gain > 0:
            tries.append((gain, label))

    first = p.get("first") or [0, 0, 0, 0]
    if min(first) < 9:
        t("First language CLB 9 in all four (retest)", first=[max(c, 9) for c in first])
    if min(first) < 10:
        t("First language CLB 10 in all four (retest)", first=[max(c, 10) for c in first])
    if not p.get("french"):
        t("French NCLC 7 in all four (TEF/TCF Canada)", french=[7, 7, 7, 7])
    t("Provincial nomination (+600)", pnp=True)
    t("One more year of Canadian work experience", cwe=min(int(p.get("cwe", 0)) + 1, 5))
    if p.get("spouse"):
        if not p.get("spouse_eca"):
            t("Spouse ECA for their credential", spouse_eca=True)
        if not p.get("spouse_first"):
            t("Spouse language test at CLB 7", spouse_first=[7, 7, 7, 7])
        t("Apply without the spouse as accompanying (only if genuinely non-accompanying; disclose them either way)", spouse=False)
    lvl = p.get("offer_level")
    if lvl != "2x":
        t("Qualifying job offer in a 2x high-wage NOC", offer_level="2x")
    if p.get("education") in ("one-year", "two-year", "bachelor"):
        t("Second credential (two or more, one 3+ yr) with ECA", education="two-or-more", eca=True)
    return sorted(tries, reverse=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--noc", help="look up a NOC on the high-wage list and stop")
    p.add_argument("--age", type=int)
    p.add_argument("--dob")
    p.add_argument("--as-of", help="score as of this date (default today)")
    p.add_argument("--expected-ita", help="warn if a birthday before this date lowers age points")
    p.add_argument("--education", choices=EDU_LEVELS, default="none")
    p.add_argument("--eca", action="store_true")
    p.add_argument("--canadian-edu", action="store_true")
    p.add_argument("--first", help="CLB L,R,W,S of the first official language")
    p.add_argument("--first-is-french", action="store_true", help="the first official language is French")
    p.add_argument("--second", help="CLB L,R,W,S of the second official language")
    p.add_argument("--french", help="NCLC L,R,W,S (French); used as second language unless --second is given")
    p.add_argument("--cwe", type=int, default=0, help="years of Canadian skilled work experience")
    p.add_argument("--hw", action="append", default=[], help="high-wage Canadian experience LEVEL:MONTHS, e.g. 2x:14 (repeatable)")
    p.add_argument("--offer-noc", help="NOC of a qualifying job offer (level looked up)")
    p.add_argument("--offer-level", choices=("2x", "1.5x", "1.3x"))
    p.add_argument("--foreign", type=int, default=0, help="years of foreign skilled work experience")
    p.add_argument("--coq", action="store_true", help="certificate of qualification in a trade")
    p.add_argument("--spouse", action="store_true", help="spouse/partner accompanying and not a citizen/PR")
    p.add_argument("--spouse-education", choices=EDU_LEVELS, default="none")
    p.add_argument("--spouse-eca", action="store_true")
    p.add_argument("--spouse-canadian-edu", action="store_true")
    p.add_argument("--spouse-first", help="spouse CLB L,R,W,S")
    p.add_argument("--spouse-cwe", type=int, default=0)
    p.add_argument("--pnp", action="store_true")
    p.add_argument("--canadian-study", choices=("1-2", "3+"))
    p.add_argument("--sibling", action="store_true")
    p.add_argument("--what-if", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    hw_list, hw_date = load_high_wage()
    if a.noc:
        n = a.noc.strip().zfill(5)
        if hw_date == "missing":
            print("High-wage list not stored (templates/ee/high-wage.csv). Check IRCC's high-wage page.")
            return 2
        lvl = hw_list.get(n)
        print(f"{n}: " + (f"high-wage {lvl[0]} ({lvl[1]})" if lvl else "not on the high-wage list") + f"; IRCC page date {hw_date}.")
        print("The level is the occupation's national median wage, not the client's pay; the level on the ITA date applies.")
        return 0

    try:
        prof = {
            "age": a.age, "dob": datetime.date.fromisoformat(a.dob) if a.dob else None,
            "as_of": datetime.date.fromisoformat(a.as_of) if a.as_of else None,
            "expected_ita": datetime.date.fromisoformat(a.expected_ita) if a.expected_ita else None,
            "education": a.education, "eca": a.eca, "canadian_edu": a.canadian_edu,
            "first": langs(a.first), "second": langs(a.second), "french": langs(a.french),
            "first_is_english": not a.first_is_french,
            "cwe": a.cwe, "foreign": a.foreign, "coq": a.coq,
            "spouse": a.spouse, "spouse_education": a.spouse_education, "spouse_eca": a.spouse_eca,
            "spouse_canadian_edu": a.spouse_canadian_edu, "spouse_first": langs(a.spouse_first), "spouse_cwe": a.spouse_cwe,
            "pnp": a.pnp, "canadian_study": a.canadian_study, "sibling": a.sibling,
        }
    except ValueError as e:
        print(f"Input not understood: {e}")
        return 1
    if a.first_is_french and prof["french"] is None:
        prof["french"] = prof["first"]
    hw = {}
    for item in a.hw:
        lvl, _, months = item.partition(":")
        hw[lvl] = hw.get(lvl, 0) + int(months or 0)
    prof["hw"] = hw
    prof["offer_level"] = a.offer_level
    if a.offer_noc:
        prof["offer_noc"] = a.offer_noc
        found = hw_list.get(a.offer_noc.strip().zfill(5))
        prof["offer_level"] = found[0] if found else None
    if prof["age"] is None and prof["dob"] is None:
        print("Give --age or --dob.")
        return 1

    try:
        r = calc(prof)
    except ValueError as e:
        print(f"Input not understood: {e}")
        return 1
    levers = what_if(prof) if a.what_if else []
    if a.json:
        r["what_if"] = [{"gain": g, "lever": l} for g, l in levers]
        r["high_wage_list_date"] = hw_date
        print(json.dumps(r, indent=2, default=str))
        return 0
    print(f"CRS total: {r['total']}  (core {r['sections']['core']} + spouse {r['sections']['spouse']} + "
          f"transferability {r['sections']['transferability']} + additional {r['sections']['additional']})")
    print("Grid: MI 2026-1 (in force 2026-11-03); " + KB + f"; high-wage list page {hw_date}.")
    sec = None
    for ln in r["lines"]:
        if ln["section"] != sec:
            sec = ln["section"]
            print(f"\n{sec}")
        print(f"  {ln['factor']}: {ln['points']}   [{ln['input']}]" + (f"  - {ln['rule']}" if ln["rule"] else ""))
    if r["warnings"]:
        print("\nWarnings:")
        for w in r["warnings"]:
            print(f"- {w}")
    if levers:
        print("\nWhat would add points (ranked):")
        for g, l in levers:
            print(f"  +{g}: {l}")
    print("\nCompare with the latest round cut-off (category-draws-history.md); confirm every input against documents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
