---
description: Courtesy translation of a client letter (status update, follow-up, general letter) into the client's language, as a Word file
argument-hint: [case id, letter, language]
---
Request: $ARGUMENTS

1. Language: from the request, or `client_language` in case.md (record it with `python3 scripts/case.py set CASE client_language Punjabi`
   if the field exists, otherwise ask). English and French letters need no translation.
2. Read the English letter (the newest in 06-correspondence unless named). Translate it faithfully: no new facts, no softening, keep every
   date, amount, deadline and reference number exactly as written. Translate the notice too: "Courtesy translation of our letter dated
   [date]. It was prepared with the help of AI translation. If anything differs from the English letter, the English letter is the one that counts."
3. Write a terms file in the scratchpad: {"language", "original_date", "original_file", "title" (translated), "notice_translated",
   "body": [translated paragraphs]}, then `python3 scripts/firm.py make translation --case CASE --terms FILE`.
4. Show the translation inline, with the English beside each deadline and amount. Tell the consultant:
   send it with the English letter, never instead; have a speaker of the language check deadlines, money or refusals.
Only for letters to the client. Translations filed with IRCC or the IRB need a translator's declaration, and the IRB requires AI use to be
disclosed (`knowledge/10-consultant-practice/ai-and-privacy.md`).
