#!/usr/bin/env python3
"""Convert language test scores to CLB / NCLC levels with IRCC's official equivalency tables.

  python3 scripts/clb.py ielts --speaking 6.5 --listening 8 --reading 7 --writing 6.5
  python3 scripts/clb.py tef --speaking 360 --listening 300 --reading 250 --writing 350 --json
  python3 scripts/clb.py tests                      (accepted tests and score ranges)

Tables: templates/language/test-equivalency.csv, from IRCC's Express Entry language test page
(page 2026-10-16, read 2026-11-13). Rule: the level is the highest one whose minimum the score meets.
Below CLB/NCLC 4 is reported as 3 ("below 4"); 10 means "10 and above".
It reports the level per ability, program minimums met, and FSW language points. It never says a client
is eligible: the RCIC checks the test report (test type, date under 2 years, TEF 'ancien score' column).
"""
import argparse
import csv
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent / "templates" / "language"
ABILITIES = ("speaking", "listening", "reading", "writing")
SOURCE = "IRCC Express Entry language test results page (2026-10-16), read 2026-11-13"
SOURCE_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/documents/language-requirements/language-testing.html"
ALIASES = {"ielts": "ielts", "ielts-gt": "ielts", "celpip": "celpip", "celpip-g": "celpip", "pte": "pte", "pte-core": "pte", "tef": "tef", "tef-canada": "tef", "tcf": "tcf", "tcf-canada": "tcf"}


def load():
    with open(DATA / "tests.csv", encoding="utf-8") as fh:
        tests = {r["test"]: r for r in csv.DictReader(fh)}
    table = {}
    with open(DATA / "test-equivalency.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            table.setdefault(r["test"], []).append((int(r["level"]), {a: float(r[a]) for a in ABILITIES}))
    for rows in table.values():
        rows.sort(reverse=True)
    return tests, table


def convert(test, scores):
    """scores: {ability: number}. Returns {ability: level} (3 = below 4). Raises ValueError on a bad test or score."""
    tests, table = load()
    test = ALIASES.get(str(test).lower())
    if not test:
        raise ValueError("test must be one of: ielts, celpip, pte, tef, tcf")
    out = {}
    for a in ABILITIES:
        if scores.get(a) is None:
            continue
        s = float(scores[a])
        top = float(tests[test][f"{a}_max"])
        if s < 0 or s > top:
            raise ValueError(f"{a} score {s:g} is outside the {tests[test]['name']} range (0-{top:g})")
        out[a] = next((lvl for lvl, mins in table[test] if s >= mins[a]), 3)
    return out


def summary(levels, language="English"):
    """Program minimums and FSW language points for one test's levels (all four abilities needed)."""
    unit = "NCLC" if language == "French" else "CLB"
    full = len(levels) == 4
    low = min(levels.values()) if levels else 0
    fsw_first = sum({7: 4, 8: 5}.get(min(v, 9), 6 if v >= 9 else 0) for v in levels.values()) if full and low >= 7 else 0
    checks = {
        "FSW first official language (all four at 7)": full and low >= 7,
        "FSW second official language (all four at 5: 4 points)": full and low >= 5,
        "CEC, TEER 0 or 1 job (all four at 7)": full and low >= 7,
        "CEC, TEER 2 or 3 job (all four at 5)": full and low >= 5,
        "Federal Skilled Trades (speaking, listening 5; reading, writing 4)": full and levels["speaking"] >= 5 and levels["listening"] >= 5 and levels["reading"] >= 4 and levels["writing"] >= 4,
    }
    return {"unit": unit, "lowest": low, "fsw_first_language_points": fsw_first, "minimums": checks}


def label(level, unit):
    return f"below {unit} 4" if level < 4 else f"{unit} 10+" if level >= 10 else f"{unit} {level}"


def cmd_convert(a):
    tests, _ = load()
    test = ALIASES.get(a.test.lower())
    try:
        levels = convert(a.test, {x: getattr(a, x) for x in ABILITIES})
    except ValueError as e:
        sys.exit(f"ERROR: {e}")
    if not levels:
        sys.exit("ERROR: give at least one score, e.g. --speaking 6.5")
    info = tests[test]
    s = summary(levels, info["language"])
    if a.json:
        print(json.dumps({"test": info["name"], "levels": levels, **s, "source": SOURCE, "source_url": SOURCE_URL}, indent=1))
        return
    print(f"{info['name']} ({info['language']}). {info['note']}.")
    for x in ABILITIES:
        if x in levels:
            print(f"  {x.capitalize():<10} {getattr(a, x):>6g}  ->  {label(levels[x], s['unit'])}")
    if len(levels) == 4:
        print(f"Lowest ability: {label(s['lowest'], s['unit'])}")
        for k, ok in s["minimums"].items():
            print(f"  [{'met' if ok else 'not met'}] {k}")
        print(f"FSW points as first official language: {s['fsw_first_language_points']} of 24")
    else:
        print("Give all four abilities to check program minimums.")
    print("Results must be under 2 years old at profile creation and at the PR application.")
    print(f"Source: {SOURCE}\n  {SOURCE_URL}")


def cmd_tests(_):
    tests, _ = load()
    for t in tests.values():
        print(f"{t['test']:<7} {t['name']} ({t['language']}): speaking 0-{t['speaking_max']}, listening 0-{t['listening_max']}, "
              f"reading 0-{t['reading_max']}, writing 0-{t['writing_max']}. {t['note']}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 1 and sys.argv[1] == "tests":
        return cmd_tests(None)
    p = argparse.ArgumentParser(description="Language test scores to CLB/NCLC (IRCC tables)")
    p.add_argument("test", help="ielts, celpip, pte, tef or tcf")
    for x in ABILITIES:
        p.add_argument(f"--{x}", type=float)
    p.add_argument("--json", action="store_true")
    cmd_convert(p.parse_args())


if __name__ == "__main__":
    main()
