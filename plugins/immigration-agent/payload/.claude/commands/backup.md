---
description: Back up the case files and client records, check a backup, or restore one
argument-hint: [create | setup | status | list | verify | restore]
---
Request: $ARGUMENTS

- Status first: `python3 scripts/backup.py status`.
- Set up once: ask where backups should go (an external, network or encrypted drive, not the same disk), then
  `python3 scripts/backup.py setup --to "<folder>" [--every 7]`. The daily alerts then make a backup when one is due (alerts.py install).
- Now: `python3 scripts/backup.py create [--to "<folder>"]`. Report the file, the number of files and the size, and any file it couldn't read.
- Check a backup: `python3 scripts/backup.py verify "<zip>"`. Restore: `python3 scripts/backup.py restore "<zip>" --into "<new empty folder>"`.
  Restore never overwrites: it unpacks into an empty folder, and the consultant moves files back themselves.
- A backup holds cases/ (including client-ids), Input/, Output/, the firm profile and logo. It isn't encrypted: tell the consultant to keep
  it on encrypted storage that meets their privacy obligations. Never open, list or read the contents of client-ids.
