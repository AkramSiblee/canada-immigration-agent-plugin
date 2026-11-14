---
description: Conflict check of a new client, spouse, sponsor or employer against every open and closed file
argument-hint: [names, and the case id if the file is open]
---
Request: $ARGUMENTS

1. Ask for every party if not given: client, spouse or partner, sponsor or co-signer, employer, and anyone else in the matter. Never guess names.
2. Run `python3 scripts/conflicts.py check "Name 1" "Name 2" ... [--case CASE]`. It searches every open and closed file (clients, family
   members in case.md, names in client-facts.csv), the closed-files list and other-parties.csv, and logs the check in cases/conflict-checks.csv.
3. Show each match with its strength, where it was found and the file. A match is a prompt to review, not a finding; no match only means no
   recorded name matched. Read knowledge/10-consultant-practice/advertising-and-conflicts.md, then say what the Code requires (ss.15-18):
   written disclosure and the client's written, informed consent; joint files (sponsor and applicant, employer and worker) are treated as a
   conflict; s.16 conflicts can't be consented to.
4. The consultant decides. Record only the decision they give: `python3 scripts/conflicts.py record CASE --result clear|consented|conflict --note "..."`.
   `consented` needs a note saying where the written disclosure and consent are filed. This sets conflict_check in case.md.
5. People declined, opposing parties, and employers or recruiters the firm has a link with: `python3 scripts/conflicts.py add-party "Name" --role ROLE [--case CASE] [--note TEXT]`.
   `parties` lists them; `history [CASE]` shows past checks.
