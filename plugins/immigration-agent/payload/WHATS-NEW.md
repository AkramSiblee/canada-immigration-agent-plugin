# What's new

Newest first. Each heading is a version number; firms see the entries newer than their own after an update.

## 1.3.6
- Updates no longer depend on you remembering to check. Automatic updates are now turned on by the agent folder itself.
- Once a day, when Claude starts in your agent folder, the agent checks whether a newer version exists (it sends nothing about you or your clients). If one does, Claude tells you, with the steps to install it.
- The dashboard shows a banner when a newer version is available or downloaded and waiting, with the steps.

## 1.3.5
- Document progress for every case in the dashboard. Open a case to see the percentage of required documents received, what is still missing, what you still need to confirm, and the full IRCC checklist. Mark each item Received, Missing or Not needed, and add documents the visa office asks for (for example IMM 5890 items). The Cases list shows each case's progress.
- New official checklists: visitor visa (IMM 5484), study permit and work permit applied outside Canada (IMM 5483, IMM 5488), and Express Entry permanent residence.
- Your marks also apply to the readiness report and client follow-ups, so a document marked Not needed is no longer asked for.

## 1.3.4
- Autofilled IRCC forms no longer open as altered or damaged in Adobe. Answers are now saved the way Adobe saves them, so IRCC's certification stays valid: Adobe shows "Certified by Immigration, Refugees and Citizenship Canada". Fill again any form autofilled before this version.
- IMM 5476 answers now show in Adobe (before, the form could open empty).
- IMM 5669 can now be autofilled, and CIT 0002 downloads again (IRCC moved its page).
- Every filled form is checked before it is saved; if a check fails, nothing is saved and you are told why. A damaged, cut-off or browser-saved blank form is refused with the reason.
- Open IRCC forms only in Adobe Acrobat or the free Adobe Acrobat Reader. A web browser, Edge or Preview shows them blank or as "Please wait...", which is not damage.

## 1.3.3
- Fees re-checked on 2026-11-12: visitor visa $100 (family maximum $500) and biometrics $85 (family maximum $170) are unchanged, and IRCC lists no upcoming change to them.

## 1.3.2
- Updates on Windows no longer treat every agent file as "changed by you", so they stop making large backup copies in .immigration-agent/backup/ each time. Backup folders made by this problem only hold copies of the agent's own files; unless you edited agent files yourself, you can delete them.

## 1.3.1
- Policy changes checked on 2026-11-12.
- Rural Community Immigration: the pilot closes and the new permanent program opens on January 1, 2027. Recommendations dated December 31, 2026 or earlier must be used before they expire. (Before, the agent showed the permanent program as already open.)
- Express Entry: draws are still paused while scores are recalculated; IRCC has not announced a restart date.

## 1.3.0
- The office dashboard has a new, clearer design: a sidebar with a count of urgent items, summary cards, and alerts marked by colour with days left or overdue.
- The case list shows each client, their next deadline and whether anything needs attention at a glance.
- Case pages show the case number and program as tags, files labelled PDF, Word or Excel, and unpaid amounts in red.
- Works in light and dark mode, and still runs only on your computer.

## 1.2.3
- Client intake always uses the new guided questionnaire (cover page, plain-language sections with examples, family cards, document checklist), including for clients who also need IMM 5707 (residents of Bangladesh). Before, those clients received the older one-list form.
- The questionnaire now asks the client's present occupation.
- Forms already sent to clients still import as before.

## 1.2.2
- Install instructions now include a one-step install command for the Claude app's Code tab.

## 1.2.1
- The dashboard opens in its own window, with no black console window behind it.
- It stops by itself a few minutes after you close its window, so nothing is left running.
- If it has stopped, it tells you to reopen it from the desktop shortcut.

## 1.2.0
- New office dashboard: today's deadlines and alerts, every case with its next deadline, case files, money and activity, and all finished documents, in your web browser. Open it with the "Immigration Agent Dashboard" shortcut (or Dashboard.bat in your agent folder).
- One-click "Copy for Claude" buttons for common tasks on each case.
- Runs on your computer only and uses no AI, so it costs nothing to use.

## 1.1.1
- Setup runs smoothly inside the Claude app: no extra permission questions when installing or updating.

## 1.1.0
- The agent now installs and updates through the Claude app: no zip files, updates arrive automatically.
- Your client folders (cases, Input, Output) are never touched by an update.
- If you changed one of the agent's files, your copy is saved in `.immigration-agent/backup/` before it is replaced.

## 1.0.0
- First release: case files, intake, checklists, document extraction, form prefill and final check, letters, refusals, CRS, fees, PNP matching, residence day counter, billing and daily alerts.
