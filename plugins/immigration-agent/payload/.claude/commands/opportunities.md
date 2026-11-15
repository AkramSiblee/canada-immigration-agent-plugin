---
description: Find past and current clients who may need the firm again soon (citizenship, PR card, permit ending, next step to PR, family sponsorship)
argument-hint: [days ahead, default 120]
---
Request: $ARGUMENTS

1. `python3 scripts/opportunities.py list [--days N]`. Present the items as a short table: date, case, client, opportunity, why, service.
2. Each item is a prompt to review the file, not advice that the client qualifies. Before any contact, open the file and check the facts
   (for citizenship: run /presence; for family sponsorship: check IRPR 117(9)(d), CLAUDE.md rule 5).
3. Consent: marketing to a former client uses their information for a new purpose. Privacy law and anti-spam rules apply.
   Read `knowledge/10-consultant-practice/ai-and-privacy.md` and `advertising-and-conflicts.md`. Suggest contact only where
   contact_ok is yes. Record a client's answer: `python3 scripts/opportunities.py consent CASE yes|no`.
   Suggest adding a consent line to the service agreement for future clients.
4. To keep a list: `python3 scripts/opportunities.py report` (Excel in Output/general). Draft a short, factual outreach letter only if asked
   (/agreement, general letter), with no promise of any outcome.
