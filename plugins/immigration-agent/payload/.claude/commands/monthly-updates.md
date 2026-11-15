---
description: Draft a "still in process" update for every client whose application is at IRCC and who hasn't heard from you in a month
argument-hint: [days, default 30]
---
Request: $ARGUMENTS

1. `python3 scripts/updates.py monthly --dry-run [--days N]` lists the files that would get a letter. Show the list.
   Files with news not yet reported are skipped: offer `updates.py notify CASE` for those (the client must hear the news itself).
2. Run `python3 scripts/ptimes.py check` first if processing times are tracked, so each letter quotes IRCC's current estimate.
3. After the consultant confirms: `python3 scripts/updates.py monthly [--days N]`. Each letter is a Word file on letterhead in the case's
   06-correspondence, and is recorded in updates.csv. It needs the firm's name and licence number (/firm-profile).
4. Remind the consultant to read and send each one by a secure method. For clients with `client_language` set, offer /translate.
A file can opt out with `monthly_updates: no` in case.md.
