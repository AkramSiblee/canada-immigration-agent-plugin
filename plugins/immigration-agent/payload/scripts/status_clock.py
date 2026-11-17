#!/usr/bin/env python3
"""Status clock for temporary residents: the dates that decide what a client can still do.

  python3 scripts/status_clock.py --expiry 2026-12-31 --applied 2026-12-20
  (--expiry = permit expiry; add --stay-end if a "must leave Canada by" date is later: the later date is used)
  python3 scripts/status_clock.py --expiry 2026-08-31 --applied 2026-08-20 --second-applied 2026-08-30 --refused 2026-11-02
  python3 scripts/status_clock.py --principal-end 2027-06-30 --spouse-route c49     # spouse of a BOWP holder
  python3 scripts/status_clock.py --expiry 2026-01-31 --mb-bridge                   # Manitoba support-letter holder
  python3 scripts/status_clock.py --expiry 2026-08-31                      # no extension filed
  python3 scripts/status_clock.py --expiry 2026-08-31 --applied 2026-08-20 --refused 2026-11-02
  python3 scripts/status_clock.py --completion 2026-05-15 --study-expiry 2026-09-30
  python3 scripts/status_clock.py --principal-end 2028-03-31 --spouse-applies 2026-11-17
  python3 scripts/status_clock.py --unauthorized-ended 2026-10-01
  add --today YYYY-MM-DD to test another day; --json for machine output.

What it prints (each line names the rule and the knowledge file it comes from):
  - maintained status: whether it applies (extension filed on or before expiry) and from when
  - status lost on: expiry (nothing filed) or the refusal date (if on maintained status)
  - restoration deadline: 90 days after status was lost (R182); days left
  - 6-month bar end: 6 months after unauthorized work or study stopped (R200(3)(e) work, R221 study)
  - spouse 16-month test: principal's permit valid at least 16 months after the spouse's application is received
  - PGWP window: 180 days after confirmation of completion; whether the study permit was valid at some point in it

The numbers (90 days, 6 months, 16 months, 180 days) are checked against the knowledge files by test_status_clock.py,
so a rule change in the KB makes the test fail instead of leaving this script silently wrong. Decision support only:
the consultant confirms every date against the documents.
"""
import argparse
import calendar
import datetime
import json
import sys

RESTORE_DAYS = 90        # knowledge/05-temporary-residence/trp-restoration-maintained-status.md (R182)
BAR_MONTHS = 6           # knowledge/05-temporary-residence/study-permit-status-and-compliance.md (R200(3)(e), R221)
SPOUSE_MONTHS = 16       # knowledge/05-temporary-residence/open-work-permits.md (spouse of worker, since 2025-01-21)
C49_MONTHS = 6           # knowledge/05-temporary-residence/open-work-permits.md (C49: principal authorized 6+ months)
PGWP_DAYS = 180          # knowledge/05-temporary-residence/pgwp.md
SRC = {
    "maintained": "knowledge/05-temporary-residence/trp-restoration-maintained-status.md (maintained status, R183(5)/R186(u))",
    "restore": "knowledge/05-temporary-residence/trp-restoration-maintained-status.md (R182: 90 days)",
    "bar": "knowledge/05-temporary-residence/study-permit-status-and-compliance.md (R200(3)(e), R221: 6 months)",
    "spouse": "knowledge/05-temporary-residence/open-work-permits.md (16 months after the spouse applies)",
    "pgwp": "knowledge/05-temporary-residence/pgwp.md (180 days; study permit valid at some point in the window)",
}


def d(s):
    return datetime.date.fromisoformat(s) if s else None


def add_months(day, months):
    y, m = divmod(day.month - 1 + months, 12)
    y, m = day.year + y, m + 1
    return datetime.date(y, m, min(day.day, calendar.monthrange(y, m)[1]))


def clock(expiry=None, applied=None, refused=None, completion=None, study_expiry=None,
          principal_end=None, spouse_applies=None, unauthorized_ended=None, today=None,
          stay_end=None, second_applied=None, spouse_route="c41", mb_bridge=False):
    today = today or datetime.date.today()
    out = []
    # Status ends on the later of the permit expiry and any "must leave Canada by" date
    # (work-permit-process-and-status.md).
    if expiry and stay_end and stay_end > expiry:
        expiry = stay_end

    def line(key, label, value, note=""):
        out.append({"key": key, "label": label, "value": value, "note": note, "source": SRC.get(key.split("_")[0], "")})

    lost = None
    if expiry:
        if applied and applied <= expiry:
            line("maintained", "Maintained status", f"from {expiry} (extension filed {applied}, on or before expiry)",
                 "Same conditions continue while the person stays in Canada until a decision; leaving can end the right to keep working or studying: advise before travel.")
            if refused and second_applied and second_applied <= expiry:
                line("maintained_end", "Status lost on", "not yet: a second application filed on or before expiry is still pending",
                     f"First application refused {refused}; maintained status continues while the second (filed {second_applied}) "
                     "is processed. If it is also refused, status is lost on that refusal date.")
            elif refused:
                lost = refused
                note = "Refusal while on maintained status."
                if second_applied:
                    note += f" The second application (filed {second_applied}, after expiry) gives no maintained status."
                line("maintained_end", "Status lost on", str(refused), note)
            else:
                line("maintained_end", "Status lost on", "not yet (decision pending)")
        else:
            if applied and applied > expiry:
                line("maintained", "Maintained status", "NO: application filed after expiry",
                     "Filed late: treat as out of status; restoration may be needed.")
            if expiry < today:
                lost = expiry
                line("maintained_end", "Status lost on", str(expiry), "Permit expired with nothing filed before expiry.")
            else:
                days = (expiry - today).days
                line("maintained_end", "Status lost on", f"not yet: permit valid to {expiry} ({days} days left)",
                     "File an extension or new permit on or before this date to keep maintained status.")
    if lost:
        deadline = lost + datetime.timedelta(days=RESTORE_DAYS)
        left = (deadline - today).days
        note = (f"{left} days left." if left >= 0 else f"Passed {-left} days ago: only a TRP or leaving Canada.")
        note += " Counted as 90 calendar days after the date status was lost. No work or study while restoration is pending."
        if mb_bridge:
            note += (" Manitoba Workforce Transition Bridge: holders of a Manitoba support letter (issued on or before"
                     " 2025-12-31) with a current Manitoba employer letter are exempt from the 90 days if the application"
                     " is received before 2027-12-31 (work-permit-process-and-status.md).")
        line("restore", "Restoration deadline", str(deadline), note)
    if unauthorized_ended:
        end = add_months(unauthorized_ended, BAR_MONTHS)
        line("bar", "6-month bar ends", str(end),
             ("Still barred." if end > today else "Bar over.") + " Applies unless the breach was only of a restorable condition or a TRP was issued later.")
    if principal_end:
        received = spouse_applies or today
        common = (" The principal must still qualify when IRCC decides; a principal on maintained status puts the spouse's"
                  " file on hold; a principal working under R186(w) while a PGWP is pending can't support a spouse permit"
                  " (open-work-permits.md).")
        if spouse_route == "exempt":
            line("spouse", "Spouse remaining-validity test", "NOT APPLICABLE",
                 "SIP BC (from 2026-03-23) or listed Quebec health recruitment (from 2026-05-25): no 16-month test;"
                 " confirm the route in open-work-permits.md." + common)
        else:
            months = SPOUSE_MONTHS if spouse_route == "c41" else C49_MONTHS
            needed = add_months(received, months)
            ok = principal_end >= needed
            label = ("Spouse 16-month test (C41 worker spouse)" if spouse_route == "c41"
                     else "Spouse 6-month test (C49, principal on a BOWP / economic PR route)")
            note = f"Principal's permit ends {principal_end}; needs to run to at least {needed} for an application received {received}."
            if spouse_route == "c41":
                note += " Occupation (TEER 0-1 or eligible TEER 2-3) is checked separately: scripts/owp_rules.py."
            line("spouse", label, "PASS" if ok else "FAIL", note + common)
    if completion:
        end = completion + datetime.timedelta(days=PGWP_DAYS)
        left = (end - today).days
        note = f"{left} days left." if left >= 0 else f"Closed {-left} days ago."
        if study_expiry:
            if study_expiry >= completion:
                note += f" Study permit valid to {study_expiry}: valid during the window."
                if study_expiry < min(end, today) and today <= end:
                    note += f" It has expired: status lost {study_expiry}; restoration + PGWP by {study_expiry + datetime.timedelta(days=RESTORE_DAYS)} (and within the 180 days)."
            else:
                note += (f" Study permit expired {study_expiry}, before completion: not valid at any point in the window,"
                         f" which pgwp.md requires. Check restoration as a student (within 90 days of {study_expiry})"
                         " and confirm eligibility on IRCC's PGWP pages before advising.")
        line("pgwp", "PGWP window closes", str(end), note)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("expiry", "stay-end", "applied", "second-applied", "refused", "completion", "study-expiry",
              "principal-end", "spouse-applies", "unauthorized-ended", "today"):
        p.add_argument("--" + a, help="YYYY-MM-DD")
    p.add_argument("--spouse-route", choices=("c41", "c49", "exempt"), default="c41",
                   help="c41 worker spouse (16 months), c49 spouse of a BOWP/economic-PR principal (6 months), "
                        "exempt (SIP BC / Quebec health)")
    p.add_argument("--mb-bridge", action="store_true", help="client holds a Manitoba support letter (Workforce Transition Bridge)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        kw = {k: (v if k in ("spouse_route", "mb_bridge") else d(v)) for k, v in vars(a).items() if k != "json"}
    except ValueError as e:
        print(f"Date not understood ({e}); use YYYY-MM-DD.")
        return 1
    rows = clock(**kw)
    if not rows:
        p.print_help()
        return 1
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        print(f"{r['label']}: {r['value']}" + (f"  ({r['note']})" if r["note"] else ""))
    print("Sources: " + "; ".join(sorted({r['source'] for r in rows if r['source']})))
    print("Confirm every date against the client's documents before advising.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
