#!/usr/bin/env python3
"""Keep the dashboard's IRCC data current: processing times, the application inventory and the Express Entry rounds, read from
IRCC's own public pages.

Usage:
  python3 scripts/ircc_data.py check      read IRCC's processing time feeds and inventory page now (public; nothing about you or
                                          your clients is sent) and save the local copy
  python3 scripts/ircc_data.py status     when each part was last read, IRCC's own update dates, and any failure

Guarantees:
  - Official sources only: the three feeds behind IRCC's "Check processing times" tool, IRCC's "Inside IRCC's application
    processing system" page, and the feed behind IRCC's "Rounds of invitations" page (saved by scripts/draws.py). IRCC's words and figures are kept as published; nothing is estimated.
  - The daily alerts run this once a day; the dashboard's Check now button runs it on request.
  - The refreshed copy is saved in cases/.ircc-data/ and used only when it is at least as new as the data shipped with the agent.
    A failed read keeps the last good data and is reported; it never produces guessed figures.
  - IRCC updates processing times about weekly and the inventory about monthly (with a lag of 6-7 weeks), so most daily checks
    find no change.
"""
import argparse
import datetime
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import case as cs  # noqa: E402

STATE = cs.ROOT / ".ircc-data" / "state.json"
EVERY_HOURS = 20


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(STATE.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    os.replace(tmp, STATE)


def stale(now=None):
    checked = load_state().get("checked")
    if not checked:
        return True
    now = now or datetime.datetime.now()
    return (now - datetime.datetime.fromisoformat(checked)).total_seconds() >= EVERY_HOURS * 3600


def refresh(today=None):
    """Read every source; one failure doesn't stop the others. Returns the saved state."""
    import draws as dr
    import inventory as iv
    import ircc_times as it

    def rounds():
        st, new = dr.refresh()
        return f"{len(new)} new round(s), latest #{st['latest']}" if new else f"no new round, latest #{st['latest']}"
    today = today or datetime.date.today()
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    state = load_state()
    parts = state.get("parts", {})
    for key, run in (("times", lambda: it.refresh_local(today)), ("inventory", lambda: iv.refresh_local(today)), ("rounds", rounds)):
        try:
            result = run()
            note = result if isinstance(result, str) else (f"{len(result)} note(s): " + "; ".join(result[:3]) if result else "ok")
            parts[key] = {"ok": True, "checked": stamp, "last_ok": stamp, "note": note}
        except Exception as e:  # a failed read must show, not pass as "no change"
            parts[key] = {"ok": False, "checked": stamp, "error": (str(e) or type(e).__name__)[:200], "last_ok": (parts.get(key) or {}).get("last_ok", "")}
    state.update(parts=parts, checked=stamp)
    save_state(state)
    return state


def status():
    """For the dashboard: when each part was read and whether it worked."""
    state = load_state()
    return {"checked": state.get("checked", ""), "parts": state.get("parts", {}), "stale": stale()}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Refresh the dashboard's IRCC data from IRCC's public pages")
    p.add_argument("cmd", choices=["check", "status"])
    a = p.parse_args()
    if a.cmd == "check":
        print("Reading IRCC's processing times, inventory and Express Entry rounds (public pages; nothing about you or your clients is sent)...")
        refresh()
    import inventory as iv
    import ircc_times as it
    s = load_state()
    print("Last check:", s.get("checked", "never"))
    for key, label in (("times", "Processing times"), ("inventory", "Application inventory"), ("rounds", "Express Entry rounds")):
        part = (s.get("parts") or {}).get(key) or {}
        print(f"  {label}: " + ("not read yet" if not part else "OK (" + part.get("note", "") + ")" if part.get("ok") else "FAILED: " + part.get("error", "")))
    c, inv = it.card(), iv.card()
    if c:
        print(f"  Showing processing times updated by IRCC {c['pr_updated']} (PR), {c['other_updated']} (other), {c['country_updated']} (countries)")
    if inv:
        print(f"  Showing inventory data to {inv['data_as_of']} (IRCC page dated {inv['page_date']})")


if __name__ == "__main__":
    main()
