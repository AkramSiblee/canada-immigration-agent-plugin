#!/usr/bin/env python3
"""Spouse open work permit eligibility for a worker's spouse, read from the knowledge base.

  python3 scripts/owp_rules.py check NOC [--permit-end YYYY-MM-DD]

The rules (eligible TEER levels, IRCC's list of eligible TEER 2 and 3 occupations, the remaining-validity months and
whether dependent children qualify) are read from knowledge/05-temporary-residence/open-work-permits.md every time:
nothing here is a rule of its own. Used by quote.py, intake_form.py and /pr-plan.

The answer is "yes", "no" or "confirm" with the reason. "confirm" means the agent can't tell (no NOC on file, or the
rule couldn't be read): it is never turned into a yes.
"""
import argparse
import datetime
import pathlib
import re
import sys

KB = pathlib.Path(__file__).resolve().parent.parent / "knowledge" / "05-temporary-residence" / "open-work-permits.md"
WHERE = "knowledge/05-temporary-residence/open-work-permits.md"
NO_NOC = "Confirm spouse open work permit eligibility: NOC not on file"


def rules(path=KB):
    """{eligible, select, months, listed {noc: title}, children} or None when the worker-spouse rule can't be read."""
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    worker = next((line for line in text.splitlines() if line.startswith("| **Spouse of worker**")), "")
    ok = re.search(r"TEER (\d)-(\d)\*\*", worker)
    sel = re.search(r"select TEER (\d)-(\d)", worker)
    months = re.search(r"at least (\d+) months", worker)
    if not (ok and months):
        return None
    listed = {}
    m = re.search(r"^### Eligible TEER 2 and 3 occupations.*?(?=^### |\Z)", text, re.M | re.S)
    if m:
        listed = {code: title.strip() for code, title in re.findall(r"^- (\d{5}) (.+)$", m.group(0), re.M)}
    return {"eligible": set(range(int(ok.group(1)), int(ok.group(2)) + 1)),
            "select": set(range(int(sel.group(1)), int(sel.group(2)) + 1)) if sel else set(),
            "months": int(months.group(1)), "listed": listed,
            "children": not re.search(r"dependent children (?:are )?(?:no longer|not) eligible", text, re.I)}


def teer_of(noc):
    """The TEER of a 5-digit NOC 2021 code (its second digit), or None."""
    code = re.sub(r"\D", "", str(noc or ""))
    return (code, int(code[1])) if len(code) == 5 else (code, None)


def spouse_check(noc, permit_end=None, today=None, path=KB):
    """("yes" | "no" | "confirm", reason) for a worker's spouse, from the principal's NOC and permit end date."""
    code, teer = teer_of(noc)
    if teer is None:
        return "confirm", NO_NOC
    r = rules(path)
    if not r:
        return "confirm", f"Confirm spouse open work permit eligibility: the rule couldn't be read from {WHERE}"
    if teer in r["eligible"]:
        verdict, why = "yes", f"NOC {code} is TEER {teer}: any TEER {min(r['eligible'])}-{max(r['eligible'])} occupation qualifies"
    elif teer in r["select"]:
        if not r["listed"]:
            return "confirm", f"NOC {code} is TEER {teer}: confirm it is on IRCC's list of eligible occupations (the list couldn't be read from {WHERE})"
        if code in r["listed"]:
            verdict, why = "yes", f"NOC {code} ({r['listed'][code]}) is on IRCC's list of eligible TEER {teer} occupations"
        else:
            return "no", f"NOC {code} is TEER {teer} but isn't on IRCC's list of eligible TEER 2-3 occupations ({WHERE})"
    else:
        return "no", f"NOC {code} is TEER {teer}: a TEER {teer} worker's spouse doesn't get an open work permit under this measure ({WHERE})"
    if permit_end:
        try:
            end = datetime.date.fromisoformat(str(permit_end)[:10])
        except ValueError:
            end = None
        if end:
            left = (end - (today or datetime.date.today())).days / 30.44
            if left < r["months"]:
                return "no", f"{why}, but the principal's permit has about {left:.0f} months left; it must be valid {r['months']}+ months when the spouse applies ({WHERE})"
            return verdict, why
    return verdict, f"{why}. The principal's permit must also be valid {r['months']}+ months when the spouse applies"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Spouse open work permit check (rules from the knowledge base)")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("check")
    x.add_argument("noc")
    x.add_argument("--permit-end")
    a = p.parse_args()
    verdict, why = spouse_check(a.noc, a.permit_end)
    print(f"{verdict.upper()}: {why}")


if __name__ == "__main__":
    main()
