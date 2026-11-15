---
description: Staff tasks on each file, and the licensee's review sign-off before anything prepared by staff is filed
argument-hint: [add CASE "task" --to NAME | list | review CASE FILE | approve CASE ID]
---
Request: $ARGUMENTS

- Staff list (once): `python3 scripts/tasks.py staff add "Name" --role rcic|assistant [--licence R123456]`. Only role rcic can approve.
- Tasks: `python3 scripts/tasks.py add CASE "what" --to NAME [--due D]`, `done CASE ID --by NAME`, `list [--who NAME] [--case CASE]`.
- Review: whoever prepared a form, letter or package sends it with `python3 scripts/tasks.py review CASE FILE --by NAME`. The licensee
  approves with `approve CASE ID --by NAME`, or sends it back with `return CASE ID --by NAME --note "what to fix"`. If the file changed
  after it was sent, approval is refused: send the new version for review. `reviews` lists what is waiting.
- The CICC Code (s.38) makes the licensee responsible for supervising anyone who assists. Pending reviews show in the readiness report as
  something to fix before filing, and in the daily alerts and dashboard with overdue tasks. The approval is a record, not a substitute
  for reading the work.
