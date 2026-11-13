---
name: firm-profile
description: Show, set up or change the firm's own details (consultant name, RCIC licence, contact details, incapacity plan, business name, logo) used for the letterhead and on agreements and letters. Optional. Use when the user asks about their firm profile, letterhead, logo or their own details on documents.
---
# Firm profile (optional)

Speak plainly: the user is a consultant, not a programmer.

## What it is
- The consultant's own details, saved once on this computer (`cases/.firm-profile.json`). Updates never change it.
- **Optional.** Without it, documents are on plain paper and Claude asks for the details a document needs each time.
- Agreements must contain the consultant's name, licence number and contact details (CICC Code s.23(2)(a), s.24(3)(a)); a service agreement also needs the incapacity plan (s.24(3)(y)). Letters need the name and licence number for the signature.

## Workflow
1. Run `python3 scripts/firm.py show`. If a profile exists, show it and ask what to change. If none, say it is optional and what it adds (letterhead, logo, no retyping details).
2. If the user wants one, ask one question at a time:
   - Required for agreements: full name; RCIC licence number (R + 6 digits); business address; phone; email; incapacity plan (who takes over the files if they cannot continue: successor's name, licence number, contact).
   - Optional: business name, website, logo (path to an image file), own complaints procedure, own confidentiality wording, language of service.
   - The user may skip anything. Never invent or guess any detail.
3. Save with `python3 scripts/firm.py setup --name "..." --rcic R123456 ...` (only the flags given), then show the result of `firm.py show`.
4. To change one detail later, run `firm.py setup` with just that flag.
5. Mention that standard wording is used for the complaints procedure and confidentiality unless they give their own, and that the dashboard sidebar now shows their business name.

## Guardrails
- Never put the profile details into anything sent outside this computer.
- If the licence number is not R + 6 digits, ask again; do not "fix" it.
- Decision support for a licensed RCIC. Be concise.
