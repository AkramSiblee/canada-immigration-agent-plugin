# Canada Immigration Agent (1.1.1)

Decision support for licensed Canadian immigration consultants. It prepares and checks; the licensed professional makes every judgment and signs every submission.

## Install (about 15 minutes, once)
You need: the Claude desktop app with a Claude plan that includes Claude Code, Python 3.10 or newer, and on Windows Git for Windows.

1. Make an empty folder for the agent and your client files, for example `Documents\Immigration Agent`.
2. In the Claude app, open the **Code** tab and choose that folder.
3. Add this marketplace: type `/plugin marketplace add AkramSiblee/canada-immigration-agent-plugin`.
4. Install the agent: `/plugin install immigration-agent@immigration-agent-marketplace`.
5. Turn on automatic updates: `/plugin` > **Marketplaces** > **immigration-agent-marketplace** > **Enable auto-update**.
6. Start a new conversation and type `/immigration-agent:setup`. Claude walks you through the rest.

## Updates
New knowledge (fees, draws, policy changes) and new features arrive by themselves when auto-update is on.
Type `/immigration-agent:update` to see your version and what's new. Your client folders are never changed by an update.

## Licence
Copyright (c) 2026 AkramSiblee. All rights reserved. Use requires a current subscription; see LICENSE.
