---
description: Turn on, check or turn off the daily updates (news, IRCC processing times and inventory, Express Entry rounds, deadline alerts)
argument-hint: [on | status | off] [--time HH:MM]
---
Request: $ARGUMENTS

Speak plainly: the user is a consultant, not a programmer.

What the daily updates do, once a day on this computer: read official public pages only (IRCC news and notices, Express Entry
rounds, ESDC and Job Bank, provincial draw pages, IRCC processing times and inventory), check every open file's deadlines and
expiry dates, and save an alerts file in Output/general. Nothing about the firm or its clients is sent anywhere. If the computer
is off at the set time, it runs at the next start-up.

1. `status` (or no argument): run `python3 scripts/alerts.py status` and `python3 scripts/ircc_data.py status`, then say in one or
   two sentences whether the daily task is on, when it runs next, and when IRCC's pages and the news were last read.
2. `on`: Windows only. Ask the time they want (default 08:00), then run `python3 scripts/alerts.py install --time HH:MM`. Confirm
   with `python3 scripts/alerts.py status`. Then run `python3 scripts/news.py check` and `python3 scripts/ircc_data.py check` once
   so the dashboard is current today.
   - On a Mac the daily task isn't available yet: tell them to click **Check now** on the dashboard's IRCC data & news page when
     they want fresh figures.
3. `off`: confirm first (the dashboard's news and IRCC figures then only change when someone clicks Check now), then run
   `python3 scripts/alerts.py uninstall`.
