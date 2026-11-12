# Canada Immigration Agent: installation and setup

Decision support for licensed Canadian immigration consultants (RCICs) and immigration lawyers.
It prepares and checks; the licensed professional makes every judgment and signs every submission.

## 1. What you need
| Item | Why | Notes |
|---|---|---|
| Windows 10/11 or macOS | Runs on your own computer | Client files stay in your folders |
| Your own Claude account with Claude Code | The AI that reads, reasons and drafts | Each user needs their own account; plans with Claude Code access are listed at claude.com |
| Python 3.10 or newer | Runs the agent's tools | Windows: install "Python 3.12" from the Microsoft Store |
| Git for Windows (Windows only) | Needed by Claude Code on Windows | git-scm.com |
| Adobe Acrobat Reader (free) or Acrobat | Finish, validate and sign IRCC forms | Recommended |
| LibreOffice (free) | Convert Word, Excel and PowerPoint to PDF | Optional |

## 2. Install (about 15 minutes)
1. Unzip the release into a folder of its own, for example `Documents\Immigration Agent`.
   If that folder is synced to OneDrive, Dropbox or Google Drive, client files will be stored with that service too:
   check that this meets your privacy obligations first.
2. Windows: right-click `install.ps1` > **Run with PowerShell**.
   Mac: open Terminal in the folder and run `sh install.sh`.
3. The installer adds the Python libraries, creates the working folders and runs the installation check.
   Fix anything marked **[FIX]**, then run the check again: `python3 scripts/setup_check.py`.
4. Install Claude Code and sign in with your account (claude.com/claude-code).

## 3. First-time setup
Open Claude Code in the agent's folder (in VS Code: File > Open Folder, then start Claude Code). Then:
1. **Your firm profile** (letterhead, agreements, letters):
   `python3 scripts/firm.py setup --name "Your Name" --rcic R123456 --business "Your Firm" --address "..." --phone "..." --email "..."`
2. **Billing and client account** (optional): `python3 scripts/billing.py setup --model 1` (see `/billing`).
3. **Daily alerts** (optional, Windows): `python3 scripts/alerts.py install --time 08:30`.
4. **Practice run with a made-up client** before using real files: ask
   "Open a practice visitor visa case for a fictional client and walk me through it."

## 4. Everyday use
Ask in plain English, or use a command:
| You want to | Type |
|---|---|
| Open a client file | `/case` |
| Send the intake questionnaire | `/intake` |
| Read the client's documents | `/extract 2026-001` |
| Prepare answers for a form | `/prefill imm5257` |
| Fill the official IRCC form | `/autofill imm5257` |
| Ask the client for what's missing | `/follow-up 2026-001` |
| Check the forms before submitting | `/final-check 2026-001` |
| Is the file ready? | `/readiness 2026-001` |
| Build the upload package | `/package 2026-001` |
| Count days for citizenship or PR | `/presence 2026-001 citizenship` |
| Which program fits? CRS? PNP? | `/select-program`, `/crs`, `/pnp` |

Folders:
- `Input/`: files you give the agent (it never changes them)
- `cases/`: one folder per client file
- `Output/`: finished documents (PDF, Word, Excel)

## 5. Keeping it current
- Each time Claude Code starts, it shows how fresh the knowledge base is (OK / STALE / NEEDS-SEED).
- `/changelog` scans official sources for new rule changes; `/update-kb <topic>` re-researches one topic; `/audit-kb` finds stale or conflicting entries.
- **Updates from us:** unzip the new release over your folder. Your `cases/`, `Input/`, `Output/`, firm profile and billing settings are not in the zip, so they stay as they are.
  If you edited knowledge files yourself, keep a copy first: the update replaces them.

## 6. Privacy and professional duties
- The tools run on your computer. The AI (Claude) reads what you ask it to read, under your Claude account.
- Get your client's authorization for AI-assisted handling and describe it in your service agreement (CICC Code ss.24, 28).
  See `knowledge/10-consultant-practice/ai-and-privacy.md`.
- Never put client files in the agent's code folders (`scripts/`, `knowledge/`, `templates/`).
- The agent never logs in to IRCC as your client, never submits, never signs, and never writes a person's narrative or evidence for the IRB.
- Its outputs are drafts for your professional review. It does not guarantee any outcome.

## 7. Help
Run `python3 scripts/setup_check.py` and send the result (it contains no client data) to your support contact.
