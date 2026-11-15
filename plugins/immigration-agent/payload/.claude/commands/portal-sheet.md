---
description: Copy sheet of the client's answers for forms filed online (PR portal, IRCC account, representative portal), in each form's order
argument-hint: [case id, forms, people]
---
Request: $ARGUMENTS

1. Run /extract on the case first if its documents haven't been read, so the answers are as complete as they can be.
2. `python3 scripts/portal_sheet.py CASE [--forms imm0008,imm5669,imm5406] [--person "Name" ...] [--all]`. Without --forms it uses the
   program's usual forms. Add --person for a spouse or children who need their own forms (imm5669, imm5406).
3. It saves a Word copy sheet in 05-forms-submissions: question, answer, status and a box to tick, form by form, and lists at the end what
   must be settled first (questions for the client, the consultant's decisions, conflicts between documents). Show that list inline and
   offer /follow-up for the client's answers.
4. Remind the consultant: the portal may split or reorder a form's questions, so match each by its wording; copy hidden numbers (****123)
   from the original; the client signs or submits per the portal's rules. The agent never logs in to IRCC.
