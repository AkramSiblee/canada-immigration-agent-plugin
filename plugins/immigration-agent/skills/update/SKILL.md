---
name: update
description: Check which version of the Immigration Agent is installed, get the latest updates, and show what's new. Use when the user asks about updates, versions, or what changed in the agent.
allowed-tools: Bash(immigration-agent-sync:*)
---
# Agent updates

Speak plainly: the user is a consultant, not a programmer.

Updates install themselves: when a conversation starts, the agent checks GitHub once a day and, if there is a newer release, downloads it, checks every file, and installs it into this folder. Client files (cases, Input, Output) are never changed.

1. Run `immigration-agent-sync --status` and explain the result in one or two sentences: the version in this folder and the latest release.
   - If the folder is not an agent folder yet, offer the setup command instead.
2. If the latest release is newer than this folder, or the user asks to update now, run `immigration-agent-sync --update`. It downloads and installs the newest release straight away. Tell the user the new commands work from their next new conversation.
3. If `--update` says it couldn't install automatically (no internet, or the download didn't check out), nothing was changed. Suggest trying again later; if it keeps failing, give the manual steps it printed.
4. To show what's new, read `WHATS-NEW.md` in this folder and summarise the latest entries.
5. On Windows, run `python3 scripts/alerts.py status`. If it says the scheduled task is not installed, explain that the daily
   updates (news, IRCC processing times and inventory, deadline alerts) are off, and offer to turn them on with `/daily-updates on`.

Files the firm edited are backed up in `.immigration-agent/backup/` before they are replaced; their own permanent instructions belong in `CLAUDE.local.md`. To turn off automatic installs (and only be told about updates), the firm can set the environment variable `IMMIGRATION_AGENT_NO_AUTO_UPDATE=1`.
