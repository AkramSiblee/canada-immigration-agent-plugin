#!/usr/bin/env python3
"""Federal Skilled Worker 67-point grid: score, minimum requirements, proof of funds and what would add points.

  python3 scripts/fsw.py --age 33 --education bachelor --clb 8 9 7 8 --experience 3
  python3 scripts/fsw.py --age 38 --education masters --test ielts --scores 7 8 7 6.5 --experience 6 \
      --second-clb 5 5 5 5 --spouse-language --relative-canada --family-size 3 --funds 30000

  Language levels are in the order speaking, listening, reading, writing (CLB or NCLC), or give --test and --scores.
  Education: phd, masters, professional, two-or-more, bachelor, two-year, one-year, secondary.

Grid: templates/fsw/selection-grid.json (IRCC six selection factors page 2026-11-03 and ECA page, read 2026-11-13).
Decision support only: it never says a client qualifies. The RCIC confirms each fact (ECA, NOC duties, test dates).
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clb  # noqa: E402

GRID = HERE.parent / "templates" / "fsw" / "selection-grid.json"
ABILITIES = clb.ABILITIES


def load():
    return json.loads(GRID.read_text(encoding="utf-8"))


def age_points(g, age):
    if age is None or age < 18:
        return 0
    if age <= 35:
        return g["age"]["18-35"]
    return g["age"].get(str(age), 0)


def experience_points(g, years):
    return next((p for y, p in g["experience"] if years >= y), 0)


def language_points(g, first, second):
    low = min(first.values()) if len(first) == 4 else 0
    pts = sum(g["language"]["first_per_ability"][str(min(v, 9))] for v in first.values()) if low >= g["language"]["first_minimum_clb"] else 0
    sec = g["language"]["second_points"] if second and len(second) == 4 and min(second.values()) >= g["language"]["second_minimum_clb_all"] else 0
    return min(pts + sec, g["language"]["max"]), pts, sec


def score(p, g=None):
    """p: dict with age, education, first {ability: clb}, second, experience, job_offer and adaptability flags."""
    g = g or load()
    lang, first_pts, sec_pts = language_points(g, p["first"], p.get("second"))
    edu = g["education"].get(p.get("education") or "", [0, "Not given"])
    adapt_items = [(k, v[0], v[1]) for k, v in g["adaptability"].items()
                   if (p.get("job_offer") if k == "arranged_employment" else p.get(k))]
    adapt = min(sum(x[1] for x in adapt_items), g["adaptability_max"])
    parts = {
        "Language": lang,
        "Education": edu[0],
        "Experience": experience_points(g, p.get("experience") or 0),
        "Age": age_points(g, p.get("age")),
        "Arranged employment": g["arranged_employment"] if p.get("job_offer") else 0,
        "Adaptability": adapt,
    }
    total = sum(parts.values())
    low = min(p["first"].values()) if len(p["first"]) == 4 else 0
    minimums = {
        "First official language at CLB/NCLC 7 in all four abilities": low >= g["language"]["first_minimum_clb"],
        "1 year continuous full-time skilled experience (TEER 0-3) in the last 10 years": (p.get("experience") or 0) >= 1,
        "Education: Canadian credential, or foreign credential with an ECA under 5 years old": bool(p.get("education")),
    }
    return {"parts": parts, "total": total, "pass_mark": g["pass_mark"], "passes_grid": total >= g["pass_mark"],
            "minimums": minimums, "meets_minimums": all(minimums.values()), "language_detail": {"first": first_pts, "second": sec_pts},
            "education_label": edu[1], "adaptability_items": [x[2] + f" ({x[1]})" for x in adapt_items]}


def funds_needed(g, size):
    size = max(1, int(size or 1))
    f = g["funds"]
    return f[str(size)] if str(size) in f else f["7"] + (size - 7) * f["each_more"]


def levers(p, g, base):
    """What-if changes and the points each adds (only ones that change the total)."""
    out = []

    def tryit(desc, **change):
        q = json.loads(json.dumps(p))
        for k, v in change.items():
            q[k] = v
        gain = score(q, g)["total"] - base["total"]
        if gain > 0:
            out.append((gain, desc))
    f = p["first"]
    if len(f) == 4:
        for target in (8, 9):
            if min(f.values()) < target:
                tryit(f"First language at CLB/NCLC {target} in every ability (retake)", first={a: max(v, target) for a, v in f.items()})
    if not (p.get("second") and len(p["second"]) == 4 and min(p["second"].values()) >= 5):
        tryit("Second official language at CLB/NCLC 5 in all four (e.g. TEF/TCF Canada)", second={a: 5 for a in ABILITIES})
    order = ["secondary", "one-year", "two-year", "bachelor", "two-or-more", "masters", "phd"]
    cur = p.get("education")
    if cur in order and cur != "phd":
        nxt = order[order.index(cur) + 1]
        tryit(f"Education: {g['education'][nxt][1]} (with ECA)", education=nxt)
    yrs = p.get("experience") or 0
    for y, _ in sorted(g["experience"]):
        if y > yrs:
            tryit(f"Experience reaches {y} year(s)", experience=y)
            break
    if not p.get("job_offer"):
        tryit("Valid job offer from a Canadian employer (no LMIA needed since 2026-11-03)", job_offer=True)
    for k, (pts, desc) in g["adaptability"].items():
        if k != "arranged_employment" and not p.get(k):
            tryit(f"Adaptability: {desc}", **{k: True})
    return sorted(out, reverse=True)


def parse_levels(vals, test=None):
    if vals is None:
        return {}
    if test:
        return clb.convert(test, dict(zip(ABILITIES, vals)))
    return {a: int(v) for a, v in zip(ABILITIES, vals)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    g = load()
    ap = argparse.ArgumentParser(description="FSW 67-point grid (IRCC)")
    ap.add_argument("--age", type=int, required=True)
    ap.add_argument("--education", choices=list(g["education"]), required=True)
    lang = ap.add_mutually_exclusive_group(required=True)
    lang.add_argument("--clb", nargs=4, type=float, metavar=("S", "L", "R", "W"), help="first official language levels")
    lang.add_argument("--scores", nargs=4, type=float, metavar=("S", "L", "R", "W"), help="first official language test scores (needs --test)")
    ap.add_argument("--test", help="ielts, celpip, pte, tef or tcf (with --scores)")
    ap.add_argument("--second-clb", nargs=4, type=float, metavar=("S", "L", "R", "W"))
    ap.add_argument("--experience", type=float, default=0, help="years of skilled (TEER 0-3) work in the last 10 years")
    ap.add_argument("--job-offer", action="store_true", help="valid arranged employment")
    for k, (_, desc) in g["adaptability"].items():
        if k != "arranged_employment":
            ap.add_argument("--" + k.replace("_", "-"), action="store_true", help=desc)
    ap.add_argument("--family-size", type=int, default=1)
    ap.add_argument("--funds", type=float, help="settlement funds available (CAD)")
    ap.add_argument("--work-authorized", action="store_true", help="authorized to work in Canada (with --job-offer: no proof of funds)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.scores and not a.test:
        ap.error("--scores needs --test")
    try:
        first = parse_levels(a.scores or a.clb, a.test if a.scores else None)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")
    p = {"age": a.age, "education": a.education, "first": first, "second": parse_levels(a.second_clb),
         "experience": a.experience, "job_offer": a.job_offer, **{k: getattr(a, k) for k in g["adaptability"] if k != "arranged_employment"}}
    r = score(p, g)
    exempt = a.job_offer and a.work_authorized
    need = funds_needed(g, a.family_size)
    r["funds"] = {"required": 0 if exempt else need, "family_size": a.family_size, "available": a.funds,
                  "short": None if exempt or a.funds is None else max(0, need - a.funds)}
    r["levers"] = [{"points": pts, "change": d} for pts, d in levers(p, g, r)]
    r["source"] = g["sources"]
    if a.json:
        print(json.dumps(r, indent=1))
        return
    print(f"FSW selection grid: {r['total']} / 100 (pass mark {r['pass_mark']}): {'meets the pass mark' if r['passes_grid'] else 'below the pass mark'}")
    for k, v in r["parts"].items():
        print(f"  {k:<20} {v:>3}")
    print(f"  (language: first {r['language_detail']['first']}, second {r['language_detail']['second']}; education: {r['education_label']})")
    if r["adaptability_items"]:
        print("  Adaptability counted (max 10): " + "; ".join(r["adaptability_items"]))
    print("Minimum requirements:")
    for k, ok in r["minimums"].items():
        print(f"  [{'met' if ok else 'NOT MET'}] {k}")
    if exempt:
        print("Proof of funds: not required (authorized to work in Canada with a valid job offer); upload a letter explaining this.")
    else:
        line = f"Proof of funds for a family of {a.family_size}: ${need:,.0f}"
        if a.funds is not None:
            line += f"; available ${a.funds:,.0f}" + (f"; short ${r['funds']['short']:,.0f}" if r["funds"]["short"] else "; enough")
        print(line)
    if r["levers"]:
        print("What would add points (one change at a time):")
        for x in r["levers"]:
            print(f"  +{x['points']:<3} {x['change']}")
    print("FSW points decide eligibility only; CRS decides invitations (use /crs).")
    print("Sources: " + "; ".join(g["sources"].values()))


if __name__ == "__main__":
    main()
