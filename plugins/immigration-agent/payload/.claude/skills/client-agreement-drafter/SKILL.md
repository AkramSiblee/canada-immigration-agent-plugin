---
name: client-agreement-drafter
description: Draft CICC-compliant agreements and letters on the firm's letterhead (consultation agreement, service agreement, amendment, risk acknowledgement, closing letter, non-engagement letter, general letter). Use when onboarding a client, changing terms, closing a file, or writing a letter.
---
# Client Agreement Drafter

## Read first
- knowledge/10-consultant-practice/client-agreements-trust-fees.md
- knowledge/10-consultant-practice/scope-and-representation.md
- knowledge/10-consultant-practice/ai-and-privacy.md (the technology notice)

## Workflow
1. Check the firm profile: `python3 scripts/firm.py show`. It is optional. If missing, ask the RCIC for the details this document needs (agreements: name, licence number, address, phone, email; service agreement also the incapacity plan; letters: name and licence number) and put them in the terms file under "firm". Offer once to save them with /firm-profile. Never invent these.
2. Pick the type with `firm.py types`. Collect the terms from the RCIC. Never invent fees, refund terms, advice or instructions. Ask.
3. Write the terms to a JSON file in the scratchpad (keys as listed in the refusal message if any are missing; lists for services, disbursements, changes, reasons, risks, documents_returned, body). Client contact details come from the case's intake answers; override with a "client" object if needed.
4. Run `firm.py make TYPE --case ID --terms FILE`. Without a case, add a "client" object with name and address; the file goes to `Output/general`.
5. Show the key terms inline in chat, give the file path, and relay the checklist the script prints (identity check, draft to client, other representative, copy of the Code, IMM 5476, signed copies).
6. Delete the scratchpad terms file.

## Related
- Submission letters and letters of explanation: use the submission-letter-drafter skill (`firm.py make submission-letter`).

## Guardrails
- Never weaken a required clause or remove an `@covers` line to get past a refusal. If a template no longer covers the Code, restore it.
- The standard confidentiality and complaints wording is a starting point. Tell the RCIC when it was used.
- The technology notice must match the tools actually used. If the RCIC hasn't confirmed it, say so.
- Fee overruns need a signed amendment before the work (s.31(3)). A matter with little chance needs a risk acknowledgement (s.27).
- Escalate to a licensed lawyer: Federal Court, criminal equivalency, retroactive asylum bars, multigenerational C-3 cases. Never guarantee outcomes.
