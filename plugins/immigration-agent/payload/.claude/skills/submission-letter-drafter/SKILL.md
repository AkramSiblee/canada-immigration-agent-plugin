---
name: submission-letter-drafter
description: Draft letters of explanation, cover letters and written submissions to IRCC or the IRB, on the firm's letterhead. Use for submission letters, LOEs and representations.
---
# Submission Letter Drafter

## Read first
- knowledge/11-forms-fees-processing/portals-and-submission.md
- knowledge/10-consultant-practice/ai-and-privacy.md (IRB Practice Notice on AI)
- The knowledge file for the program, and any refusal or procedural fairness letter in the case

## Workflow
1. Gather the facts and the issue to address. Use the case documents and the extraction report; ask the RCIC for anything missing. Never invent dates, numbers or events.
2. Draft the letter inline in chat first: concise, one point per paragraph, each point tied to an enclosed document.
3. Cross-check every date, name and number against the forms and documents. Verify every legal citation on Justice Laws or CanLII.
4. Once the RCIC approves the text, write a terms file in the scratchpad: recipient, subject, body (list of paragraphs), enclosures (list), and uci / application_number if known. Then run `python3 scripts/firm.py make submission-letter --case ID --terms FILE`. It is saved in the case's `05-forms-submissions`, on letterhead.
5. Relay the checklist the script prints. Delete the scratchpad terms file.

## Guardrails
- IRB (any division): the script adds the required AI declaration automatically, naming the RCIC as reviewer. Never use this for a narrative, basis of claim, affidavit, witness statement or other evidence: those are the person's own words (IRB Practice Notice; CLAUDE.md rule 7). Submissions about the law and the evidence are allowed.
- IRCC: no AI declaration rule was found (low confidence). Add `"ai_declaration": "yes"` only if the RCIC chooses to disclose.
- Federal Court: refused by the script. Refer to a lawyer (CLAUDE.md rule 4).
- A client's own explanation (e.g. why they overstayed) must reflect what the client actually said. Quote or paraphrase them; don't improve their facts.
- Flag IRPA s.40 if any fact differs from earlier forms.
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases. Never guarantee outcomes.

## Fact check
- After drafting, run `python3 scripts/letter_check.py check LETTER --case CASE`. It compares the letter's dates, UCI, passport and application numbers, amounts, name spellings and the forms it mentions with the case's extracted documents. Fix every HIGH finding or confirm the documents are what's out of date. The readiness report runs the same check on letters in 05-forms-submissions and 06-correspondence.
