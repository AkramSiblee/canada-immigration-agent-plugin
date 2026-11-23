---
description: Immigration news from official sources (IRCC, ESDC, Job Bank, provincial draws), matched to open files, and short client messages about an item
argument-hint: [check | list | post ID]
---
Request: $ARGUMENTS

1. `check`: `python3 scripts/news.py check` reads the official pages now (public; nothing about the firm or clients is sent) and lists
   new items. `python3 scripts/news.py sources` shows any source that failed and the ones to check by hand (PEI, Saskatchewan, Yukon, NWT).
   For a failed or by-hand source, offer to read the official page yourself. If the knowledge base lacks a rule change the news shows,
   offer /update-kb for the matching file.
2. `list`: `python3 scripts/news.py list [--tag federal|provincial|quebec|work|rules|fees]`. Show it as a short table: date, tag, headline.
3. `post ID` (the dashboard's Share button copies this):
   a. `python3 scripts/news.py show ID --files`.
   b. Open the item's official link and confirm the facts before drafting (CLAUDE.md rule 2). If the page now says something different,
      say so and use the page. Items from the knowledge base changelog have no link: cite the matching knowledge file and its source.
   c. Draft, inline in chat:
      - A client message (email or WhatsApp, under 120 words): what happened, who it may affect, the source link, and one line inviting
        the client to book a review if they think it applies to them. Personalise it only for the files listed by `--files`, and only from
        their case facts.
      - A social post (under 60 words) for the firm's page, if the consultant wants one.
   d. CICC Code s.44 applies to both (social posts are advertising, `knowledge/10-consultant-practice/advertising-and-conflicts.md`):
      the consultant's name as registered with the College; for written ads, the address of the College's online public register;
      no guarantees or likely-outcome claims; no "apply before it's too late" pressure; nothing implying a link to the Government of Canada
      or a province (no flags or government-style logos). A draw's cut-off doesn't mean the client will be invited. Never describe a
      closed or paused program as open (check `knowledge/14-policy-tracker/` first).
   e. Send only to clients whose file shows contact consent "yes" (Canada's anti-spam law, CASL, and privacy rules). List the others as
      "consent not recorded" and suggest `python3 scripts/opportunities.py consent CASE yes` once the client agrees. Each message must
      say how to stop receiving updates.
   f. With Gmail connected and the consultant's OK, save one draft per client (create_draft). Never send. Never put one client's details
      in another client's message, and never send a group email with clients visible to each other.
   g. Once sent, log it on each file: `python3 scripts/case.py log CASE "News sent: <headline>"`.
