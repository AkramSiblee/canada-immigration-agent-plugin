---
name: update
description: Check which version of the Immigration Agent is installed, get the latest updates, and show what's new. Use when the user asks about updates, versions, or what changed in the agent.
---
# Agent updates

Speak plainly: the user is a consultant, not a programmer.

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/agent_sync.py" --status` and explain the result in one or two sentences.
   - If the folder is not an agent folder yet, offer the setup command instead.
2. If the user wants the newest version, tell them how to fetch it, because Claude cannot run `/plugin` for them:
   - Type `/plugin`, open **Marketplaces**, select the agent's marketplace, choose **Update marketplace**.
   - Recommend **Enable auto-update** there too, so future updates arrive by themselves.
   - Then start a new conversation. The new version installs into this folder automatically when it starts.
3. If the status shows pending changes on the current version, run `python3 "${CLAUDE_PLUGIN_ROOT}/agent_sync.py" --init` to apply them now.
4. To show what's new, read `WHATS-NEW.md` in this folder and summarise the latest entries.

Client files (cases, Input, Output) are never changed by updates. Files the firm edited are backed up in `.immigration-agent/backup/` before they are replaced; their own permanent instructions belong in `CLAUDE.local.md`.
