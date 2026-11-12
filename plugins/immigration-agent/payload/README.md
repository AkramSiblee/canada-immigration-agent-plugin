# Canada Immigration Agent (RCIC support)

Claude Code project: instructions, skills, subagents, slash commands, and a staged knowledge base.

## Open in VS Code
1. Install the Claude Code extension (or CLI: `npm i -g @anthropic-ai/claude-code`).
2. `File > Open Folder` > this folder. Start Claude Code in the folder; `CLAUDE.md` and `.claude/` load automatically.
3. Session start prints KB freshness (SessionStart hook).

## Install (new computer or buyer)
- `install.ps1` (Windows) or `sh install.sh` (Mac): Python libraries, working folders and the installation check. Full guide: `INSTALL.md`
- `python3 scripts/setup_check.py` : installation check (what is missing and how to fix it)
- `python3 scripts/make_release.py` : the clean zip for buyers in `dist/`: committed files only, checked for client names, numbers and firm details

## Plugin release (how firms install and get updates)
Firms install the agent as a Claude plugin; at every Claude start it copies the latest agent into their folder (never cases/, Input/, Output/; files they changed are backed up to `.immigration-agent/backup/`). Source: `plugin/`.
1. Make the change and commit it.
2. Bump `VERSION` and add an entry at the top of `WHATS-NEW.md` (firms see it after updating). Commit.
3. `python3 scripts/build_plugin.py` : builds `dist/marketplace/` from the last commit, with the same privacy checks as the zip, and validates it.
4. `python3 scripts/build_plugin.py --publish` : builds, then commits, tags vX.Y.Z and pushes to https://github.com/AkramSiblee/canada-immigration-agent-plugin (the git repo in `dist/marketplace/`). Refuses an already-published version. Firms receive it at their next update.
- Tests: `python3 scripts/test_plugin.py`

## First steps
- `python3 scripts/kb_status.py` : see NEEDS-SEED / STALE files
- Drop the baseline research report into `knowledge/_inbox/`, then `/update-kb inbox`
- `/update-kb 01-federal-economic/express-entry` : seed one file at a time
- Use `research-prompts/gap-pass-01.md` for the uncovered areas

## Slash commands
`/case` `/readiness` `/status-update` `/agreement` `/billing` `/extract` `/prefill` `/intake` `/select-program` `/crs` `/pnp` `/checklist` `/fees` `/refusal` `/pf-response` `/compliance` `/update-kb` `/audit-kb` `/changelog`

## Layout
- `CLAUDE.md` : agent rules
- `.claude/skills/` : 29 skills (practice + KB maintenance)
- `.claude/agents/` : kb-researcher, kb-auditor, case-reviewer
- `.claude/commands/` : slash commands
- `knowledge/` : domains 00-14, `_inbox/`, `kb-manifest.yaml`
- `research-prompts/` : gap pass and monthly refresh
- `cases/`, `templates/` : client work (cases ignored by git)
- `scripts/kb_status.py` : freshness report
- `scripts/case.py` : client files and deadline tracker (see `cases/README.md`)
- `scripts/doc_extract.py` : document extraction and cross-checks (tests: `scripts/test_doc_extract.py`)
- `scripts/form_prefill.py` : worksheets of answers for IRCC forms (specs in `templates/form-specs/`)
- `scripts/intake_form.py` : guided client questionnaire for five programs (visitor, study, work, Express Entry, family / PR), and import of the answers into a case (`scripts/intake_questionnaire.py` holds the questions and document lists)
- `scripts/alerts.py` : daily local alerts matched to open case files
- `scripts/billing.py` : invoices, receipts, client (trust) account ledger and monthly reconciliation
- `scripts/readiness.py` : case readiness report before filing: extraction flags, open form answers, intake steps, deadlines, updates and client account issues in one workbook
- `scripts/updates.py` : client status updates: record what was submitted or received, draft the letter, track copies (Code s.22(3))
- `scripts/firm.py` : agreements and letters on your letterhead, as Word files (templates in `templates/firm/`)
- `scripts/presence.py` : residence day counter: citizenship physical presence (1,095 days, half-day pre-PR credit, s.21 exclusions) and the PR 730-day residency obligation, with the earliest signing date or latest return date (`/presence`)
- `scripts/followup.py` : client follow-up requests: open questions and missing documents as one fillable PDF, the reply imported, open items tracked (`/follow-up`)
- `scripts/final_check.py` : final form check before submitting: blanks, logic, consistency across forms and the passport number on the finished PDFs (`/final-check`; also in the readiness report)
- `scripts/package.py` : sorting run: a case's documents in IRCC checklist order, one upload-ready PDF per item, with an index (`/package`; tests: `scripts/test_package.py`)
- `scripts/letter_check.py` : checks a drafted letter's dates, numbers, amounts, names and forms against the extracted documents
- `scripts/autofill.py` : writes a worksheet's ready answers into IRCC's official blank form and reads it back to confirm (`/autofill`)
- `scripts/lmia.py` : LMIA stream, refusal-to-process, cap and recruitment checks (`/lmia`; data in `templates/lmia/`; tests: `scripts/test_autofill_lmia.py`)
- `scripts/pdf_studio.py` : private PDF tools on this computer: combine, organize, split, compress (to IRCC's upload limit) and convert, with IRCC forms protected (`/pdf`; tests: `scripts/test_pdf_studio.py`)

## Maintenance cadence
- Fast-changing domains (01, 02, 03, 11, 14): every 30 days
- Others: every 90 days
- After any IRCC/Gazette announcement: `/changelog`
