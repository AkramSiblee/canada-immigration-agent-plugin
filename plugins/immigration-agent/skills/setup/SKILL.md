---
name: setup
description: Install the Canada Immigration Agent in this folder (first-time setup for a firm). Use when the user asks to set up, install or start using the immigration agent, or when this folder has no CLAUDE.md for the agent yet.
allowed-tools: Bash(immigration-agent-sync:*)
---
# Set up the Immigration Agent in this folder

Speak plainly: the user is a consultant, not a programmer. One step at a time; say what each step does.

1. **Check the folder.** Show the full path of the current folder. Ask the user to confirm it is the folder they want for the agent and their client files (for example `Documents\Immigration Agent`).
   - If it holds unrelated files, suggest making a new empty folder and opening that one instead.
   - If the path contains OneDrive, Dropbox or Google Drive: client files will be stored with that service too. They should confirm that meets their privacy obligations (PIPEDA, CICC Code) before continuing.
2. **Check Python.** Run `python3 --version`. It must be 3.10 or newer. If it is missing: Windows, install "Python 3.12" from the Microsoft Store; Mac, install from python.org. Then start again.
3. **Install the agent files.** Run:
   `immigration-agent-sync --init`
   This copies the agent into the folder. Client folders (cases, Input, Output) are created empty and are never touched by updates.
4. **Install the libraries.** Run `python3 -m pip install --user -r requirements.txt`, then the check: `python3 scripts/setup_check.py --install`. Explain anything marked [FIX] in plain words.
5. **Dashboard shortcut.** On Windows run `python3 app/dashboard.py --shortcut`. It puts an "Immigration Agent Dashboard" shortcut on the desktop: deadlines, alerts, cases and documents in the web browser, no AI used. On a Mac, tell them to double-click `Dashboard.command` in this folder.
6. **Finish.** Tell the user:
   - Start a **new conversation** in this folder so Claude loads the agent.
   - Optional: save their firm details and letterhead once with `/firm-profile` (otherwise Claude asks for the details each document needs).
   - Automatic updates are turned on by the agent folder's settings. To be sure: `/plugin` > Marketplaces > select the agent's marketplace > it should offer Disable auto-update (if it offers Enable, choose it).
   - The agent also checks once a day for a newer version and says so here and on the dashboard.
   - Try a practice run with a made-up client before real files.

Never run the install in a folder the user did not confirm.
