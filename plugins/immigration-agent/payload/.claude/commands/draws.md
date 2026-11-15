---
description: Match the latest Express Entry round (or a provincial draw) against every open file's recorded score
argument-hint: [check | latest | profile CASE --crs N | pnp-add ...]
---
Request: $ARGUMENTS

1. Scores: each Express Entry client needs a recorded score and the round types they are eligible for:
   `python3 scripts/draws.py profile CASE --crs 485 --eligible cec,french [--profile-date YYYY-MM-DD] [--pnp BC:115]`.
   Get the score from /crs or the client's profile. Category eligibility is the consultant's assessment
   (read `knowledge/01-federal-economic/category-draws-history.md`). Update it whenever the profile changes.
2. `python3 scripts/draws.py check` reads IRCC's rounds feed (public; nothing about clients is sent) and lists clients at, above or within
   10 points of each new round's cut-off. `latest` shows the saved rounds; `match --round N` re-checks one.
3. Provincial draws aren't in one feed: when the consultant gives one (from the province's official page), record it with
   `python3 scripts/draws.py pnp-add --province XX --stream "..." --date D --min-score N`.
4. A match isn't an invitation: ties go by profile submission time, and the profile must have been in the pool before the round's cut-off
   time. Tell the consultant to check each client's IRCC account. If invited: 60 days to apply; record the ITA date with `/validity`.
If the knowledge file's draw log is older than the newest round, offer /update-kb 01-federal-economic/category-draws-history.
