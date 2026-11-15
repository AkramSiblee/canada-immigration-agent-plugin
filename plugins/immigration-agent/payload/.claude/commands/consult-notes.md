---
description: Turn a consultation recording's transcript (or typed notes) into a filed record of the consultation, with risk flags and follow-ups
argument-hint: [transcript file, case id or prospect id]
---
Request: $ARGUMENTS

1. Transcript: a text, .vtt, .srt, Word or PDF transcript (Zoom, Teams, Otter or Word "Transcribe" export). The agent can't hear audio:
   if only a recording is given, ask for its transcript. If the consultation was recorded, confirm the client agreed to the recording.
2. `python3 scripts/consult_notes.py scan TRANSCRIPT` lists risk words with their context (previous refusal, status problems, family not
   declared, possible misrepresentation, an agent or unlicensed consultant, criminality, medical, Federal Court or IRB), money and dates.
3. Read the whole transcript. Draft the notes from what was actually said, never adding facts: goals, facts the client gave, advice given,
   options discussed, risks, documents requested, next steps, fees discussed, and dated follow-ups. Flag IRPA s.40, IRPR 117(9)(d) and
   ghost-consultant risk (CLAUDE.md rule 5), and anything for a lawyer (rule 4). Show the draft inline and let the consultant correct it.
4. Write the approved notes as JSON in the scratchpad (fields in `scripts/consult_notes.py`), with "source" and, for a recording,
   "recording_consent": "yes". Then `python3 scripts/consult_notes.py save --notes FILE --case CASE --transcript TRANSCRIPT`
   (or `--prospect ID` before a file is opened). It saves a Word record in 04-advice, adds the advice to case.md's "Advice given" table,
   adds the follow-ups as deadlines and files the transcript. Delete the scratchpad file.
Never use this for an IRB narrative, statement or evidence: those are the person's own words (rule 7).
