---
description: Fee quote for a prospect or client: your professional fees plus IRCC's fees for the program and family, as a Word letter
argument-hint: [program, family size, prospect id or case id]
---
Request: $ARGUMENTS

1. Fee table (once per program): `python3 scripts/quote.py fee PROGRAM --base 3000 [--extra 500] [--schedule "50% at signing; 50% before filing"] [--services "a; b"]`
   and tax once: `python3 scripts/quote.py tax --rate 13 --name HST`. `quote.py table` shows both. Never invent the consultant's fees: ask.
2. IRCC fees come from templates/quote-fees.csv (dated). Read `knowledge/11-forms-fees-processing/fee-schedule.md`; if it is stale, or
   `python3 scripts/watch.py status` shows a fee change, verify on IRCC's fee list first and tell the consultant (CLAUDE.md rule 2).
3. `python3 scripts/quote.py calc --program P [--spouse] [--children N] [--people N] [--minors N] [--open-work-permit N]` and show the numbers.
   Visas and permits: each person is priced by their own application. State each one with `--member role:application[:age]`
   (visitor, super-visa, study, work, owp), e.g. `--member spouse:owp:34 --member child:study:12`; ages apply the biometrics exemptions.
   Without --member the quote assumes a worker's spouse needs an open work permit and children a visitor visa, and says so: confirm
   with the consultant. --people/--minors for citizenship.
4. On approval: `python3 scripts/quote.py make ... --prospect ID` (moves the prospect to "quoted"), or `--case CASE`, or `--name "Client"`.
   Relay: a quote isn't a service agreement (Code s.24); offer /agreement service-agreement once the client accepts.
