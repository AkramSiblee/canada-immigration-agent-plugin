---
name: form-prefill
description: Build a plain-English Excel worksheet of answers for an IRCC form from extracted documents and client facts. Use when the user asks to pre-fill, prepare or draft answers for an IMM form.
---
# Form Pre-fill

## Read first
- knowledge/11-forms-fees-processing/forms-directory.md
- knowledge/10-consultant-practice/ai-and-privacy.md

## Workflow
1. Run the document-extractor skill first if there is no recent report. For scans, add `family_name` and `given_name` separately, as printed on the passport.
2. Run `python3 scripts/form_prefill.py build --form FORM --person "Full Name" --case ID`. For several family members, build one sheet per person. `list` shows the forms available.
3. Report the counts, conflicts first. Name where each sheet was saved.
4. Collect the client's answers with the fillable form (`scripts/intake_form.py`, see the case-intake skill), or add them to `client-facts.csv` in the case folder (person, key, value, source). Then rebuild.

## Forms
- IMM 0008, IMM 5669, IMM 5406, IMM 5257 (visitor visa), IMM 1294 (study permit, outside Canada), IMM 5710 (work permit, inside Canada), IMM 5708 (visitor extension), IMM 5709 (study permit, inside Canada), IMM 1295 (work permit, outside Canada), IMM 1344 (sponsor), IMM 5532 (relationship, filled by sponsor and applicant together), IMM 5476 (representative), IMM 5645 and IMM 5707 (family information, visitors, students and workers), IMM 5409 (common-law declaration), IMM 5562 (travel history), IMM 5444 (PR card or PR travel document; IMM 5524 is no longer used), IMM 5768 and IMM 1283 (financial evaluation), IMM 5748 (parents and grandparents income sources), CIT 0003 (citizenship for minors, s.5(2)), CIT 0001 (proof of citizenship), CIT 0002 (citizenship). `list` shows versions.
- Most visitor, study, work and sponsorship applications are now filed in the IRCC online portal. The questions are the same, but the order and wording on screen can differ: check the portal before relying on question numbers.
- IMM 5476: your details as representative come from your firm profile (`firm.py setup`). If an earlier IMM 5476 names someone else, confirm that agreement ended (Code s.24(2)(c)).
- IMM 5532 Part C is the couple's own account. Never draft their relationship story (CLAUDE.md rule 7 applies to IRB matters; the same care applies here).
- IMM 5409 is a solemn declaration: both partners sign before a commissioner or notary. Never pre-fill its facts.
- IMM 5257 Schedule 1: no current official version was found on IRCC's site (2026-11-10). If a visa office asks for it, use the version that office provides.
- IMM 1344 is for the sponsor; build the applicant's forms under the applicant's name.

## Guardrails
- Never fill, edit or submit an IRCC form. A person enters every answer and checks it against the original.
- Never answer a background, refusal, family, medical or consent question from a document or inference. Those come from the client.
- Answers from an earlier IRCC form appear only in the note, for comparison. If the client's answer differs, the row becomes a conflict: ask why before filing.
- Never choose between conflicting answers. Flag IRPA s.40 and IRPR 117(9)(d) where relevant.
- Show masked numbers only.
- Before relying on a form version, check it on IRCC's page. If `templates/form-specs/index.csv` is more than 90 days old for that form, re-check the wording and update the spec.
- For IRB forms and narratives, follow rule 7 in CLAUDE.md.

## Autofill
- Once answers are Ready, `python3 scripts/autofill.py fill --form FORM --person NAME --case CASE` writes them into IRCC's official blank PDF and reads it back to confirm each one. Everything else stays blank. The consultant opens it in Adobe, completes it, validates and has it signed.
