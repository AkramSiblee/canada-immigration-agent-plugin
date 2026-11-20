# What's new

Newest first. Each heading is a version number; firms see the entries newer than their own after an update.

## 1.16.1
- **All provincial nominee files now checked on official sources** (high confidence):
  - **Newfoundland and Labrador**: entrepreneur points grid (120 points, pass mark 72), no deposit, deadlines after approval (work permit within 2 months, arrival within 6 months), up to 10 partners for International Entrepreneur and 3 for International Graduate Entrepreneur, 5-year bar for misrepresentation.
  - **New Brunswick**: the Post-Graduate Entrepreneurial Stream is not available; the Business Immigration stream has no special rules for graduates.
  - **PNP processing**: IRCC's own estimates (through Express Entry about 7 months; outside Express Entry about 12).
  - **Atlantic 2026 allocations**: confirmed not published by any province; the agent will not quote unofficial figures.

## 1.16.0
- **Knowledge base: 7 new topics** the agent now reads before answering:
  - **Victims of family violence, human trafficking and abused workers**: the family violence permit, the trafficking permit and the open work permit for vulnerable workers (all fee-exempt).
  - **Quebec family sponsorship**: Quebec's cap of 15,700 undertakings from 2026-07-02 to 2028-06-30 (13,300 spouses; 2,400 parents and other relatives), the filing schedule, undertaking lengths, 2026 income tables, $335 fee.
  - **Quebec temporary workers**: joint LMIA, $233 Quebec fee, wage threshold $36.00/h, the Montréal/Laval low-wage freeze to 2026-12-31, French at renewal.
  - **Refugees and protected persons in Quebec**: free CSQ, federal health cover ends 90 days after a positive decision, Quebec collective sponsorship closed to 2029-12-31.
  - **Immigration Division and detention**: who decides inadmissibility, detention reviews (48 hours, 7 days, 30 days), bonds and release conditions.
  - **Cessation, vacation and danger opinions**: when a refugee or a PR who was a refugee can lose status (for example by travelling on the home-country passport).
  - **Caregivers**: the caregiver pilots stay paused; caregiver work permits from outside Canada only for Quebec jobs; LMIA fee waivers for families; PR alternatives.
- **H&C expanded**: bars and exceptions, forms, naming each exemption you ask for, stay of removal and open work permit after approval in principle.
- **Manitoba, PEI and Yukon checked on their official sites** (now high confidence): Manitoba fees, deadlines and the business points grid; PEI's official business points grid and refund rules; Yukon worker requirements. Yukon's Business Nominee apply page now redirects, so treat it as not accepting applications until Yukon confirms.

## 1.15.0
- **New dashboard page: IRCC data** (left menu). Together these tell a client how long a file may take and whether it may also wait for space:
  - the IRCC application inventory card;
  - **processing times for permanent residence and citizenship**: IRCC's estimate for a new application and the number of people waiting, for all 28 programs (Express Entry, PNP, AIP, caregivers, spousal, PGP, protected persons, refugees, H&C, citizenship grant and proof);
  - **visas and permits from outside Canada**: choose the client's country of residence to see visitor visa, super visa, study permit and work permit times (171 countries; the page remembers your choice);
  - **in Canada and other services**: extensions, PR cards, eTA, IEC, citizenship services and status documents.
  Each card names its source (IRCC), the date IRCC updated it and the date it was read, and turns "Out of date" after 45 days. The home page inventory card links to the new page.
- Processing times updated to IRCC's data of 2026-11-17 and 2026-11-18, for example: FSW about 9 months (was 7), spouse outside Canada about 19 months and in Canada about 27, PGP about 26, protected persons in Canada about 11, proof of citizenship about 35, PR card renewal 50 days, work permit extension 119 days. Visitor and super visa times refreshed for 147 countries.

## 1.14.4
- Dashboard, IRCC application inventory card:
  - shows the time period: inventory on 2026-09-30, change since 2026-08-31, and files finalized from 2026-01-01 to 2026-09-30;
  - names its source (IRCC, Inside IRCC's application processing system, with a link), the page date and the date it was read;
  - the "Your files" column is removed.
- Dashboard left open during an update: the home page now says "reopen the dashboard", and opening it again from its shortcut starts it with the new version. Before, it kept running the old version, and new parts (such as the inventory tables) could be missing.

## 1.14.3
- Dashboard: the IRCC card is now "IRCC application inventory", with two tables (data to 2026-09-30):
  - **Permanent residence** (707,405, down 7,935): for economic, family and protection, the files in inventory, the change since the month before, the share actively processed and the share waiting for space, files finalized since January, and your open files in each category.
  - **Temporary residence** (347,935, down 17,490): visitor visas, work permits and study permits, with inventory, change and files finalized since January.
- "Waiting for space" means the file is held because the yearly admission targets are full. It is not a processing delay.

## 1.14.2
- Dashboard: the "IRCC: files held for space" card moved to the left column of the home page, under Needs attention, so it shows without scrolling. In 1.14.0 it sat below the long Ask Claude list.

## 1.14.1
- PGWP: new section on the work permit bar after unauthorized work or study, or breaking a permit condition (IRPR 200(3)(e)): no PGWP or other work permit until 6 months after it stopped, with the regulation's exceptions (some condition breaches, section 206, a later TRP). Working more than the allowed off-campus hours in term is generally treated as unauthorized work (our reading; check the facts).

## 1.14.0
- **New on the dashboard home page: "IRCC: files held for space".** For economic, family and protection permanent residence files, the share IRCC holds complete but waiting until a yearly target space opens (now 22%, 42% and 44%, data to 2026-09-30), whether it rose or fell since the month before, and how many of your open files are in each category. It is not a processing time; use it to set client expectations, for example that a spousal file can wait beyond the posted time. The card turns grey with "Out of date" when IRCC's page is more than 60 days old.
- Each case page shows the same figure for that case's category (permanent residence files only).
- The figures come with each update after IRCC publishes new data (about monthly). `python3 scripts/inventory.py` prints the card as text.

## 1.13.3
- **Express Entry researchers category changed (IRCC notice 2026-11-18):** post-secondary teaching and research assistants (NOC 41201) no longer qualify; only university professors and lecturers (NOC 41200) remain. Canadian professor or lecturer experience and job offers paid through stipends, grants, bursaries or scholarships now count for the Canadian Experience Class and Federal Skilled Worker and earn CRS points. Clients with that experience should update their profile. IRCC gave no transition rules and nothing on invitations already issued.
- Checked today, nothing new: no Express Entry round since 2026-10-28; no immigration regulations in the 2026-11-18 Canada Gazette; 2027 study cap not published; LMIA wage thresholds unchanged since 2026-07-17; Quebec 2027 plan not tabled; no province has announced how it will use the 2027 workers measure.

## 1.13.2
- IRCC's application inventory updated to 2026-09-30: about 348,000 temporary residence and 707,000 permanent residence applications not yet finalized; 22% of economic, 42% of family and 44% of protection files are waiting for space under the yearly targets. IRCC no longer publishes an overall backlog percentage.
- 2027 figures now sourced on IRCC pages: up to 115,000 protected persons and 33,000 work permit holders moved to PR in 2026-2027 (the 33,000 is the In-Canada Workers Initiative for smaller communities; no action needed by applicants), the goal of PR admissions under 1% of the population after 2027, and temporary residents under 5%.
- Checked today, nothing new: no Express Entry round since 2026-10-28; 2027 study cap not published; federal start-up pilot not launched; Quebec 2027 plan not tabled; no province has announced how it will use the 2027 workers measure; Ebola measures still end 2026-11-27.

## 1.13.1
- **Your knowledge base edits are no longer undone by updates.** Until now, a knowledge file you edited in your agent folder was replaced at the next start (after a backup). Now:
  - if the new release didn't change that file, your version stays;
  - if the release changed it too, your version stays and the release's version is saved next to it as `<file>.shipped.md`, and the start-up message lists it as a conflict to merge (then delete the .shipped.md file);
  - when a release includes your edit, the file is reported as merged and follows updates again.
  The start-up message after an update lists kept, merged and conflicting files. Other files (scripts, commands) still update as before, with a backup of anything you changed.
- Fees: the right of permanent residence fee is refunded if you withdraw or IRCC refuses the application; it is the only fee refunded once processing has started.
- Express Entry: children under 14 and people over 79 don't give biometrics.
- 2027 one-time measure: humanitarian figures added (Hong Kong up to 32,000, Ukraine family reunification 18,800, H&C already found eligible 12,600, spouses, partners and children in Canada 45,000; together more than the stated 100,000, which IRCC doesn't explain). The workers measure also covers people waiting in the Atlantic Immigration Program. Clients don't need to apply.
- Restoring status as a worker: what IRCC's page requires, the provincial support-letter exception, and the visitor-record fallback ($100, no work while waiting).
- The 2027 study permit cap is still unpublished.
- Restored edits the old updater had undone in your folder on 2026-11-16: the online inland refugee claim steps (Guide 0174), the latest Canada Gazette check and the 2027 one-time measure details in the levels plan file.

## 1.13.0
- **New CRS calculator (`scripts/crs.py`, used by /crs):** the full grid in force since 2026-11-03, with the new labour market integration factor (the higher of Canadian experience plus the high-wage bonus, or a high-wage job offer), spouse points (education counts only with an ECA), transferability caps, the French bonus and the nomination. It shows a line-by-line breakdown, ranks what would add points, and warns when a birthday before the expected invitation would cost age points.
- **High-wage list stored:** all 186 occupations with their level (2x, 1.5x, 1.3x). `python3 scripts/crs.py --noc 21231` gives the level. It depends on the occupation, never the client's own pay.
- **Category lists stored:** every 2026 category occupation. `python3 scripts/category_check.py 31102` shows which categories a NOC is in, plus its high-wage level. The 12 months of category experience don't need to be continuous.
- **Express Entry rounds:** none since #453 (2026-10-28) as of 2026-11-17; the first rounds under the new CRS will be added as they appear.
- **Police certificates for 25 countries:** what to get, how to apply from Canada or abroad, which countries need an IRCC request letter or send results to IRCC directly (Saudi Arabia, Colombia, Mexico, Qatar), and official fees and times where published.
- **Express Entry:** proof of funds rules from the regulations and officer instructions (what is official vs. practice for gifts, parents' accounts and fixed deposits), a reference letter template, what to do when a former employer has closed, processing times, and what to report between the invitation and landing.
- **Correction:** IRCC's new penalties (in force 2026-10-23) apply to paid representatives and advisers, not to applicants. Applicants still face the 5-year misrepresentation bar. No IRCC guidelines published yet.
- Biometrics sources checked (all links live) and updated.

## 1.12.0
- **New `scripts/status_clock.py`:** give it the dates you have (permit expiry, date an extension was filed, refusal date, program completion, principal's permit end, end of any unauthorized work) and it shows maintained status, the date status was lost, the 90-day restoration deadline, when the 6-month bar ends, whether the spouse passes the 16-month test, and when the 180-day PGWP window closes. The temporary residence advisor and the work permit pathfinder now use it instead of counting by hand.
- **New decision tree for an expiring permit:** time left, then BOWP, LMIA, PGWP, spouse permits, a visitor fallback and restoration.
- **Bridging open work permit:** IRCC's new BOWP page is in. Help Centre answer 676 ("expires in 4 months or less") is out of date: the program page and officer instructions have no such window. Express Entry applicants need the acknowledgement of receipt showing the completeness check was passed.
- **Spouse open work permits:** what happens when the principal is on maintained status, moves to a PGWP, changes job, or holds a BOWP (spouse gets C49), and the renewal rules.
- **Express Entry completeness:** what makes an application complete, what is rejected and refunded (the invitation is used up), letters of explanation, and late documents.
- **Work permit process:** restoration and a new permit in one application, the Manitoba bridge policy (the only current exception to the 90-day limit), two applications pending at once, LMIA validity vs permit length (low-wage LMIAs up to 2 years from 2026-11-06), and the PR-only LMIA.
- **Express Entry points (MI 2026-1):** the high-wage tier is based on the occupation's national median wage, not the client's pay. No LMIA is needed for job-offer points or for FSW/FST arranged employment for invitations from 2026-11-03; a work permit still needs one (or an exemption).
- **Employers:** IRPA s.124 offence for employing someone without authorization (up to $50,000 and 2 years per count), recent CBSA cases, and what due diligence looks like.
- New case law on restoration, BOWP, spouse permits, maintained status and PGWP transitions.

## 1.11.0
- **PGWP field of study, checked from IRCC's full list:** all 1,107 rows of IRCC's field-of-study list are now stored with the page date (2026-03-09). New command `python3 scripts/cip_check.py 52.0201` answers eligible, not listed, or date-conditioned; add `--applied` (study permit date) and `--pgwp` (PGWP date) to settle the date conditions. The study permit and PGWP assessor runs it for every CIP question instead of answering from memory.
- **PGWP:** how IRCC measures program length (the program's length per the school, breaks not subtracted, accelerated programs get the full length, Quebec hours), combining programs, and what happens when a student changes program or school after the study permit (the completed program's CIP is what counts; a new school means a new permit and a fresh field-of-study test).
- **Staying compliant:** permits now name the school (since 2024-11-08), so leaving that school without finishing ends the permit; when a PAL is or isn't needed on an extension; scheduled breaks (in the school calendar, max 150 days each and 180 days a year; no IRCC guidance for thesis students); the student's spouse's work permit when the student's permit ends early (no IRCC answer on working to expiry); restoration (90 days, not available to a student who stopped studying) and the 6-month bars after unauthorized work or study.
- **Study permits:** how each province and territory issues the PAL (always requested by the school; no provincial fee), country instructions for the Philippines, India, Vietnam, Iran, Ghana and Kenya (Ghana's form still shows an old funds figure: use IRCC's $23,448), the medical exam rules (Iran is not on the list), and Quebec CAQ steps with the 2026 Quebec funds amounts.
- New student decision tree: school and program choice, PAL and cap, funds, applying, compliance, PGWP, then PR.
- New student case law: 34 Federal Court decisions from 2024-2026 on study plans, ties, funds, boilerplate refusals, PGWP full-time study and restoration, and spouses of students. Read each decision before citing it.
- Policy tracker: the 2027 study cap and PAL allocations aren't published yet (150,000 student arrivals a year is the levels target, not the cap); nothing announced on the 2027 field-of-study list.

## 1.10.0
- New **/entrepreneur**: give it a business client's profile (net worth, liquid funds, ownership history, language, education, age, target province, business idea) and it checks every open provincial and Quebec entrepreneur stream: eligible or not and why, points estimate, investment and jobs against the minimums, excluded businesses, compliance risks (spending before the performance agreement, related employees, family living elsewhere, source of funds), the work permit code and next steps. /select-program and /pnp send business clients to it; the dashboard has a "Business client" button.
- New business decision tree: provincial entrepreneur (C60 work permit, nomination, PR), Quebec business programs, temporary-only routes (C11, ICT start-up C12/C61, CUSMA traders and investors T34/T35), an LMIA for the owner's own job, and clients with a Start-up Visa or Self-Employed file still in process.
- **Correction:** provincial entrepreneur candidates who want PR use a **C60** work permit with the province's support letter (then T13 after nomination), not C11. C11 is for temporary stays only (51%+ owner, up to 18 months); PR plans on a C11 file risk refusal.
- Entrepreneur rules filled in from official guides and pages for BC (Base, Regional, Strategic Projects), Alberta (Rural, Graduate, Foreign Graduate, Farm), Manitoba, New Brunswick, Nova Scotia (full process from the September 2026 guide), PEI, Newfoundland and Labrador, Northwest Territories and Yukon. A new "Entrepreneur streams" table in the PNP comparison shows status, net worth, investment, ownership, jobs, language, deposit, operating period, fee and work permit for each.
- Corrections: Manitoba's business fee is $2,500 (the $500 fee is for worker streams); Yukon does have a Business Nominee Program (intake status not stated, confirm with Yukon); Manitoba is not running business draws; PEI has issued no business invitations in 2026.
- Federal status unchanged: Start-up Visa closed, Self-Employed paused, the new start-up pilot announced but not launched. Provinces may nominate people still waiting on a Start-up Visa or Self-Employed application through the extra 2027 spaces (by 2027-03-31; applicants don't need to do anything).
- Quebec business programs are still open; the new Quebec government has proposed a pause on economic immigration from abroad (not adopted).
- New: source-of-funds and net worth checklist, business refusal case law, and business checklists in /checklist (business plan, net worth verification, performance agreement, work permit, arrival, nomination request, PR).

## 1.9.12
- US-based clients: the facts that were only medium confidence were checked on the full official pages. Confirmed: study permits at the border for US citizens and green-card holders (they still need a PAL/TAL), SWAP Working Holidays for Americans aged 18-35, and how IRCC treats a US pardon or expungement (not automatic; the Saini test).
- Remote work as a visitor now follows IRCC's new digital nomad instructions (2026-05-26): up to 6 months at a time, income earned outside Canada, and the documents officers may ask for.
- Biometrics in the US corrected: an application support centre or the Los Angeles / New York visa application centre, booked free on the USCIS website.
- Cannabis offences stay medium confidence: conduct now legal in Canada should not count, but no IRCC page says so directly.

## 1.9.11
- /us-pathway now covers every kind of US-based client, not only workers: business visitors and after-sales service under CUSMA, remote work for a US employer as a visitor, CUSMA traders and investors, SWAP Working Holidays for young Americans, study permits at the border, Canadian citizens in the US sponsoring a spouse (must show a plan to live in Canada), US-born children and Bill C-3, PRs living in the US, the asylum 14-day rule, and US expungements, cannabis and removals.
- Correction: US citizens and green-card holders can still apply for a work or study permit at the border (they are an exception to the end of flagpoling). H-1B, L-1 and F-1 holders without a green card cannot.
- The H-1B pathway from Budget 2025 is now in the policy tracker: announced, not open as of 2026-11-17.

## 1.9.10
- case.py review: any IRCC letter in the file (procedural fairness, biometrics, medical, passport request, refusal, approval) or an IRCC application number now counts as proof that an application exists. A submitted date earlier than the date you opened the file is asked as a question (filed before you took the file?), not reported as an error.

## 1.9.9
- case.py review: clearing or changing a header field no longer counts as proof that an application was filed, so fields such as the IRCC processing line are still flagged when nothing shows a submission.

## 1.9.8
- Fee quotes and the questionnaire now check a worker's spouse against IRCC's rules for a spouse open work permit: the principal's NOC must be TEER 0-1, or on IRCC's list of eligible TEER 2-3 occupations (now in the knowledge base), with 16+ months left on the permit. A spouse who doesn't qualify is priced as a visitor, with the reason; with no NOC on file, the quote says "Confirm spouse open work permit eligibility: NOC not on file". New command: owp_rules.py check NOC.
- /autofill: an other name written "Yes: Nahar Begum (name before marriage)" now fills the name boxes; when a name can't be split for certain, the Yes is left blank too and the client is asked.
- /evidence: wedding, family, visit and trip pictures go to the captioned photo PDF (the keyword becomes a suggested theme); screenshots and scanned documents keep their category.
- /final-check no longer lists answers autofill wrote from the client's own facts as "typed on the form".
- /pdf compress: no more pypdf warning.
- New: case.py review lists header fields (submitted date, CRS score, expiry dates, program) that the file's facts, documents, log or notes don't support. It never changes the header.
- Knowledge base: Nova Scotia's four streams with their eligibility rules, the food and accommodation pause and the NOC 62020 pause; the rural pilot closes 2027-01-01 (permanent program from that date) and community intakes re-checked; official sources for every decision tree; the Quebec business programs in the policy tracker; one fee-page date.

## 1.9.7
- Readiness report: your own letters to the client (closing letters, agreements, quotes, status updates) are no longer fact-checked against the client's documents, so your fees aren't flagged as "amount not shown in any document". Letters of explanation and submission letters are still checked.

## 1.9.6
- /final-check and the readiness report now check the form saved most recently. Before, a version from an earlier day with a higher number (for example yesterday's -v3) was checked instead of today's.

## 1.9.5
- /autofill reads more of the work and education history written on one line: dates written "2011-07 to present", homemaker, unemployed or retired lines with no employer, and "field, school" written before the place when the school is clearly named (college, university, school ...). An answer of "None" means no rows. Anything that still can't be read for certain is reported, as before.
- School and work addresses written "Province, City, street address" (in any order) are split when the street is the part with a number.

## 1.9.4
- Automatic updates keep working after the first one. Before, an agent folder that had updated itself once stopped at that version.

## 1.9.3
- Family members are no longer mixed up. Before, two people whose names shared two words (for example two brothers whose names both start with Md and end with the same family name, or a mother and daughter with the same two-word family name) could be treated as one person, so one person's answers could reach the other's forms. Now names must match fully (middle names and word order don't matter), and prefixes such as Md, Mohammad or Syed don't count. Close spellings are still flagged for you to check.
- "Check for updates" (/immigration-agent:update) reports correctly after the agent has updated itself.

## 1.9.2
- The client questionnaire now reaches the forms: work history, education and countries lived in are saved row by row, so /autofill fills those tables; "Calgary, Alberta" style answers fill the province and city boxes; job duties fill the duties box. A Yes to education or previous countries is only written when at least one row is filled, and answers too long for a box are reported, never cut short.
- /autofill: "No expiry" leaves the expiry date blank; "Not required" is never written in the PAL/TAL or CAQ number box; better suggestions when an answer isn't on a form's list; IMM 5476 tells you to set your family name once when your name has more than two words.
- Worksheets: "If yes" questions show "Not needed" when the question before them is answered No. /follow-up now asks every open question (other names, previous marriage) and doesn't repeat what's already on an open request.
- Readiness checklist: filled forms are "Prepared, not yet signed", not missing. Final check: a Yes to a refusal is "Confirm" when the refusal letter is already on file.
- /extract flags payslips and labour cards dated outside the employment letter's dates (possible misrepresentation).
- /quote gives open work permits to the spouse, never to a principal on an employer-specific permit.
- The "Ignoring padding error" messages are gone.

## 1.9.1
- The agent now updates itself. When you start a conversation, it checks for a newer version once a day and, if there is one, downloads it, checks every file, and installs it into your agent folder. You see "Immigration Agent updated" with what's new. No /plugin steps, no other software. Your client files are never changed, and any file you edited is backed up first.
- /immigration-agent:update installs the newest version straight away.

## 1.9.0
- /autofill fills much more: Yes/No answers given with details ("Yes: maiden name"), answers in parts (employer, place of work, job title and duties, work dates, school address, PAL/TAL and CAQ, spouse's names), the education and 10-year employment tables, national ID details, and your name and address on IMM 5476 from the firm profile. When an answer isn't on a form's list, the closest choices are shown. Running it again with the same answers no longer makes a new copy.
- /final-check checks each person's forms separately (no more false "date of birth differs" between spouse and children), uses the newest version of each form, and checks the spouse and children across everyone's forms.
- Client questionnaire: Yes/No plus details for other names and countries lived in, a passport and ID section (numbers stored hidden), a short supplement for each child's own application, and a warning when a spouse asks for an open work permit the principal's job or studies may not support.
- /extract compares documents with the client's answers and flags differences as possible misrepresentation (refusals, job title, dates, hours, NOC, names); old refusals say the time limits have passed and suggest the GCMS notes; payslips, labour cards, foreign tax returns and school records are recognised; a different name on the marriage certificate is flagged as an other name to declare.
- /ircc-letter reads "30 days from the date of this letter" and similar wording.
- Letter check: possessive names ("Smith's") aren't flagged, and application numbers from IRCC letters are known. Readiness picks IMM 5645 or IMM 5707 by the visa office for the client's country.
- /follow-up: questions for you (representative details, your decisions) are listed for you, not put on the client's request.
- /quote prices each family member by their own application (spouse open work permit, children's study permits or visas), applies biometrics age exemptions, and states its assumptions.
- /presence: "days to spare" for the PR residency obligation is now the days over 730.
- /consult-notes accepts plain typed notes (.txt or Word). /draws match takes a case id. /opportunities uses dates already in the file (documents, family table, children's birthdays) and says where each came from. A filled IMM 5476 shows as "prepared, not yet signed".

## 1.8.1
- /autofill now writes the passport number in full. The agent finds it again in the client's facts or the passport itself (for a scanned passport, the agent reads the code lines at the bottom of the page), and writes it only if it matches the number checked when the documents were read. It stays hidden everywhere else (worksheets, reports, screen output). Always check it against the original passport.
- Word documents (agreements, letters, quotes, PR plans, translations, portal copy sheets) now share one house style with the PDFs: navy headings, a letterhead with a rule under it, page numbers and banded tables.

## 1.8.0
- /dropbox: clients upload documents to their own folder in your OneDrive, Google Drive or Dropbox (through an upload-only link you share). One command files each document into the right case with its type in the name, says what the checklist still lacks, and keeps anything it can't match aside for you. The daily alerts tell you when uploads are waiting.
- /reply: drafts the answer to "what's happening with my file?" from the case's own facts (last events, what the client still owes, missing documents, IRCC's current processing time), as a Gmail draft when Gmail is connected. You read and send it.
- /quote: set your fees once per program, then get a quote letter in seconds: your fees and tax, IRCC's fees for the program and family size (with the family caps), totals and payment schedule. A prospect moves to "quoted" automatically.
- /evidence: spousal and partner evidence sorted into a dated timeline (camera dates, file names, document dates), with gaps flagged. Mark the photos and add captions, and it builds the upload PDFs: captioned photos (20 at most), proof of contact (10 pages at most) and the other categories, with an index.
- /tasks: give staff tasks on each file, and sign off what they prepare. Only a licensee can approve, and only the exact version sent for review. Work waiting for your review shows in the readiness report, the alerts and the case page (Code s.38).
- /portal-sheet: for forms filed online, a Word copy sheet of the client's answers in each form's order, with a box to tick, and a list of what to settle before you start.
- /accounting: invoices, payments and client account movements in one Excel for your bookkeeper, plus import files for QuickBooks Online and Xero. Client account money is kept apart from income.

## 1.7.0
- /consult-notes: give the agent the transcript of a recorded consultation (from Zoom, Teams, Otter or Word), or your typed notes. It flags risks (previous refusals, family not declared, possible misrepresentation, an unlicensed agent, criminality, medical, matters for a lawyer), drafts the notes for you to correct, and files them as a Word record in the client's file, with the advice added to the file's advice log and follow-ups as deadlines. A recording needs the client's consent.
- /prospects: track every enquiry from first contact to paid consultation, quote and signed client. Each new name is conflict-checked, you are reminded of the consultation agreement and that an advance fee goes to the client account, prospects waiting for a follow-up show in the alerts, and a report shows conversion by source and why people didn't sign.
- /processing: each submitted file is compared with IRCC's own published processing times (read weekly). A file past the time is flagged and the agent drafts the IRCC web form enquiry for you to send. No repeat reminder within 30 days.
- /monthly-updates: one command drafts a "still in process" letter for every client whose application is at IRCC and who hasn't heard from you in a month, quoting IRCC's current estimate.
- /licence: your CPD hours for the July to June term (16 hours, 1 on professionalism or the Code), annual fee and insurance dates, with reminders before June 30 and each due date.
- Dashboard: prospects and your licence on the Opportunities page; processing time on each case page.

## 1.6.0
- /ircc-letter: give the agent an IRCC letter (or let it look in Gmail for IRCC emails). It recognises the letter (acknowledgement of receipt, biometrics, medical, procedural fairness, document request, interview, passport request, PR confirmation, approval, refusal, ITA), finds the client's file, files a copy, adds the time limit the letter states, and records it so the client update is tracked. It never guesses a deadline: if the letter's limit isn't clear, it asks you.
- /validity: tracks how long language tests (2 years), ECAs (5 years), medicals (12 months), police certificates (6 months before filing), Express Entry profiles (12 months) and ITAs (60 days) stay valid. Set a planned filing or landing date and you are warned when a document will run out before it. The daily alerts and the dashboard warn 90 and 30 days ahead.
- /draws: record each Express Entry client's CRS score and categories once. After every round (read from IRCC's own feed, once a day), the agent lists clients at or within 10 points of the cut-off. You can also record provincial draws.
- /opportunities: finds clients in open and closed files who may need you again: citizenship eligibility, PR card renewal, permits ending, study or work clients ready for a PR route, CRS points dropping at a birthday, expiring tests, and family members left behind. Contact only clients who agreed to hear from you (`contact_ok` in the file).
- /time: record hours on each file and see what each file, and each kind of file, earns per hour against your target rate.
- /precedents: keep your best past letters as anonymised precedents by issue (study gap, previous refusal, dual intent...), and start new drafts from them. Letters of explanation now check the library first.
- /translate: a courtesy translation of a client letter in the client's language, as a Word file, stating that the English letter governs.
- Dashboard: a new Opportunities page (clients to review, latest Express Entry rounds and who matches them), plus document validity and hours on each case page.

## 1.5.1
- New knowledge for corporate files: employer compliance inspections (who inspects, the employer conditions, the 30-day response, and the official penalty and ban tables), work permits under trade agreements other than CUSMA (CETA, UK, CPTPP, GATS, Chile, Peru, Colombia, Korea, Panama, Ukraine), and the Global Skills Strategy (2-week processing, the 15/30/120-day work permit exemptions, Global Talent Stream wages).
- Quebec business immigration: Investor, Entrepreneur (3 streams) and Self-Employed programs, with net worth, investment, French level 7 and 2026 fees. Correction: these programs are open and take applications at any time; the agent previously said their status was unconfirmed.
- Investment programs of other countries (such as Antigua and Barbuda, Portugal, Spain) are outside an RCIC's licence; the agent now says so and refers them out.

## 1.5.0
- /conflicts: checks a new client, spouse, sponsor, co-signer or employer against every open and closed file (clients, family members and every name in the client facts) and a list of other parties you keep, such as people you declined. Spelling variants and reversed names are found. Every check is kept on record, and you record your decision (clear, consented in writing, or conflict). Opening a new case now compares the client's name automatically.
- /calendar: puts every open deadline and status and passport expiry date into Outlook, Google or Apple Calendar, with reminders 7 days and 1 day before. Titles show the case number only, so no client names go to your calendar provider. The dashboard's Cases page has an "Add deadlines to calendar" button.
- /backup: backs up your case files, client account records, Input and Output folders, firm profile and logo into one file, checks every file in it, and can restore it into an empty folder (nothing is ever overwritten). Choose a backup folder once (an external or encrypted drive) and the daily alerts make a backup every week. Today and the dashboard warn you when a backup is due or failed.
- /watch: compares each form the agent fills with the version on IRCC's page, and every amount on IRCC's fee list with the agent's fee table. The daily alerts check once a week and the dashboard shows what changed. Autofill now refuses a form IRCC has replaced, so answers can't land on moved questions.

## 1.4.1
- Your firm profile is now optional. Without it, documents are on plain paper and Claude asks for the details each one needs (agreements still need your name, licence number and contact details, as the CICC Code requires).
- New /firm-profile command to add, show or change your details, letterhead and logo in a few questions.
- The dashboard shows an optional reminder to add your firm details; click "Not now" to hide it.

## 1.4.0
- /clb: converts IELTS General Training, CELPIP-General, PTE Core, TEF Canada and TCF Canada scores to CLB/NCLC levels with IRCC's official tables, and shows which program minimums are met.
- /fsw: scores the Federal Skilled Worker 67-point grid, checks the minimum requirements and proof of funds, and lists what would add the most points.
- /us-pathway: routes for clients in the United States (US citizens, green-card holders, H-1B, L-1, TN, F-1): CUSMA and intra-company work permits, Express Entry, PNP, and DUI and police-certificate checks. The H-1B pathway announced in Budget 2025 is not open yet; the agent says so.
- /pr-plan: a full eligibility assessment and PR plan for the client (scores, pathways compared, step-by-step timeline, documents, risks) as a Word document on your letterhead.

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
