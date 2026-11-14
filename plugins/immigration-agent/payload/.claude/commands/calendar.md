---
description: Put open deadlines and expiry dates into Outlook, Google or Apple Calendar (.ics file)
argument-hint: [case id, or blank for all active cases]
---
Request: $ARGUMENTS

Run `python3 scripts/case.py calendar [CASE]`. It saves Output/general/YYYY-MM-DD-deadlines-calendar.ics with every open deadline and the
status and passport expiry dates, each with reminders 7 days and 1 day before. Titles show the case number only. Add `--details` only if the
consultant asks for descriptions and file names in the calendar, and say that these then go to their calendar provider.
Tell them to import the file (Outlook: File > Open & Export > Import/Export; Google Calendar: Settings > Import & export), that importing
again adds new dates but doesn't remove ones marked done, and that a computed date is a planning aid to confirm against the decision.
The dashboard's Cases page has the same download ("Add deadlines to calendar").
