#!/usr/bin/env python3
"""PR plan: one client-ready Word document on the firm's letterhead from a plan prepared by Claude (/pr-plan).

  python3 scripts/pr_plan.py build plan.json [--folder general|<Input subfolder>] [--case 2026-001]

plan.json (every field optional except client and pathways):
  {"client": "Full name", "goal": "...", "summary": ["..."], "profile": ["Age 33", ...],
   "scores": [{"name": "CRS", "value": "478", "note": "..."}],
   "pathways": [{"route": "...", "fit": "Strong|Possible|Not now", "why": "...", "gap": "...", "timeline": "...", "next": "..."}],
   "plan": [{"when": "Months 1-2", "steps": ["..."]}],
   "risks": ["..."], "documents": ["..."], "assumptions": ["..."], "sources": ["..."]}

Output: Output/<folder>/YYYY-MM-DD-pr-plan.docx (never overwrites: -v2, -v3), and a copy in the case's 04-advice
folder with --case. Every plan is a draft for the RCIC to review; the document says outcomes are not guaranteed.
"""
import argparse
import datetime
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import firm  # noqa: E402

DISCLAIMER = ("This plan is professional advice based on the information you gave us and the rules published by Immigration, "
              "Refugees and Citizenship Canada and the provinces on the dates shown. Rules, draw scores and program openings change "
              "often. No outcome is guaranteed. We will review the plan with you before any application is filed.")


def blocks(plan, profile):
    b = [("title", f"Permanent residence plan: {plan['client']}"),
         ("para", f"Prepared {plan.get('prepared') or datetime.date.today().isoformat()} by {profile.get('name') or 'your consultant'}"
                  + (f", RCIC {profile['rcic']}" if profile.get("rcic") else "")),
         ("space", "")]
    if plan.get("goal"):
        b += [("heading", "Your goal"), ("para", plan["goal"])]
    if plan.get("summary"):
        b += [("heading", "Summary")] + [("bullet", x) for x in plan["summary"]]
    if plan.get("profile"):
        b += [("heading", "Your profile (as you told us)")] + [("bullet", x) for x in plan["profile"]]
    if plan.get("scores"):
        b += [("heading", "Scores"), ("table", [["Measure", "Result", "What it means"]] + [[s.get("name", ""), s.get("value", ""), s.get("note", "")] for s in plan["scores"]])]
    b += [("heading", "Pathways compared"),
          ("table", [["Pathway", "Fit", "Why", "Gap to close", "Timeline"]] +
           [[p.get("route", ""), p.get("fit", ""), p.get("why", ""), p.get("gap", ""), p.get("timeline", "")] for p in plan["pathways"]])]
    nxt = [p for p in plan["pathways"] if p.get("next")]
    if nxt:
        b += [("heading", "Next step for each pathway")] + [("bullet", f"**{p['route']}:** {p['next']}") for p in nxt]
    if plan.get("plan"):
        b += [("heading", "Step-by-step plan")]
        for stage in plan["plan"]:
            b += [("para", f"**{stage.get('when', '')}**")] + [("bullet", s) for s in stage.get("steps", [])]
    for key, title in (("documents", "Documents to start gathering"), ("risks", "Risks and how we manage them"),
                       ("assumptions", "What this plan assumes")):
        if plan.get(key):
            b += [("heading", title)] + [("bullet", x) for x in plan[key]]
    b += [("heading", "Important"), ("para", DISCLAIMER)]
    if plan.get("sources"):
        b += [("heading", "Sources")] + [("bullet", x) for x in plan["sources"]]
    return b


def build(plan_path, folder="general", case=None):
    plan = json.loads(pathlib.Path(plan_path).read_text(encoding="utf-8"))
    if not plan.get("client") or not plan.get("pathways"):
        firm.die("the plan needs at least 'client' and 'pathways'")
    out_dir = firm.REPO / "Output" / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    path = firm.next_path(out_dir, f"{datetime.date.today().isoformat()}-pr-plan")
    profile = firm.load_profile()
    firm.write_docx(path, blocks(plan, profile), profile, plan["client"])
    copies = [path]
    if case:
        import doc_extract as de
        cdir = de.active_case(case) / "04-advice"
        cdir.mkdir(parents=True, exist_ok=True)
        dest = firm.next_path(cdir, f"{datetime.date.today().isoformat()}-pr-plan")
        shutil.copy2(path, dest)
        copies.append(dest)
        import case as cs
        cs.add_log(de.active_case(case), f"PR plan prepared ({len(plan['pathways'])} pathways compared): {dest.name}")
    return copies, profile


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Client PR plan (Word, firm letterhead)")
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("build")
    x.add_argument("plan")
    x.add_argument("--folder", default="general")
    x.add_argument("--case")
    a = p.parse_args()
    copies, profile = build(a.plan, a.folder, a.case)
    for c in copies:
        print(f"Saved: {c}")
    if not profile.get("rcic"):
        print("Note: the firm profile is not set up, so the letterhead is blank. Ask: 'Set up my firm profile'.")
    print("Draft for your review before it goes to the client.")


if __name__ == "__main__":
    main()
