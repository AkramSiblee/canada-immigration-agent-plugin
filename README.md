# Canada Immigration Agent (1.4.1)

Decision support for licensed Canadian immigration consultants. It prepares and checks; the licensed professional makes every judgment and signs every submission.

## Install (about 15 minutes, once)
You need: the Claude desktop app with a Claude plan that includes Claude Code, Python 3.10 or newer, and on Windows Git for Windows.

1. Make an empty folder for the agent and your client files, for example `C:\Users\<you>\Immigration Agent`.
   Keep it outside OneDrive, Dropbox or Google Drive unless that meets your privacy obligations.
2. In the Claude app, open **Customize > Plugins > Add marketplace** and paste: `AkramSiblee/canada-immigration-agent-plugin`
3. In the same screen, click **Install** on **Canada Immigration Agent** (choose "for you" if asked).
   Or do steps 2 and 3 in one step: open the **Code** tab and type `/plugin install immigration-agent --marketplace AkramSiblee/canada-immigration-agent-plugin`
   (needs Claude Code 2.1.275 or later).
4. Turn on automatic updates for this marketplace in the same screen (or type `/plugin` > Marketplaces > Enable auto-update).
5. Open the **Code** tab, choose your agent folder, start a **new conversation** and type `/immigration-agent:setup`.
   Claude walks you through the rest. Click **Allow** when it asks to install the agent files.
6. Open the **Immigration Agent Dashboard** shortcut on your desktop to see deadlines, alerts and cases.

## Updates
New knowledge (fees, draws, policy changes) and new features arrive by themselves when auto-update is on (the agent folder turns it on for you).
Once a day, when Claude starts in your agent folder, the agent checks GitHub for a newer version (it sends nothing about you or your clients). If one exists, Claude and the dashboard tell you, with the steps to install it.
Type `/immigration-agent:update` to see your version and what's new. Your client folders are never changed by an update.

## Licence
Copyright (c) 2026 AkramSiblee. All rights reserved. Use requires a current subscription; see LICENSE.
