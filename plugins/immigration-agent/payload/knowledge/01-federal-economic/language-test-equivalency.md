---
domain: 01-federal-economic
topic: language-test-equivalency
status: verified
last_verified: 2026-11-13
confidence: H
review_every_days: 90
sources:
  - https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/documents/language-requirements/language-testing.html
---
# Language tests: scores to CLB / NCLC (economic immigration)

Source: IRCC Express Entry "Language test results" page (page 2026-10-16), all tables read in full 2026-11-13 (H).
Calculator: `python3 scripts/clb.py <test> --speaking --listening --reading --writing` (data: `templates/language/`).

## Accepted tests
- English: **CELPIP-General**, **IELTS General Training** (IELTS One Skill Retake not accepted), **PTE Core** (not PTE Academic).
- French: **TEF Canada** (use the "équivalence ancien score" column; never the score out of 699), **TCF Canada**.
- Results must be **under 2 years old** at profile creation **and** at the PR application. Expired results lead to refusal.

## Program minimums
- FSW first official language: CLB/NCLC 7 in all four. Second official language: CLB/NCLC 5 in all four = 4 FSW points.
- CEC: CLB/NCLC 7 (TEER 0 or 1 job), 5 (TEER 2 or 3).
- FST: speaking and listening 5, reading and writing 4.

## Minimum score for each level (speaking / listening / reading / writing)
The level is the highest one whose minimum the score meets.

| Level | IELTS GT | CELPIP-G | PTE Core | TEF Canada (ancien score) | TCF Canada |
|---|---|---|---|---|---|
| 10+ | 7.5 / 8.5 / 8.0 / 7.5 | 10 each | 89 / 89 / 88 / 90 | 393 / 316 / 263 / 393 | 16 / 549 / 549 / 16 |
| 9 | 7.0 / 8.0 / 7.0 / 7.0 | 9 each | 84 / 82 / 78 / 88 | 371 / 298 / 248 / 371 | 14 / 523 / 524 / 14 |
| 8 | 6.5 / 7.5 / 6.5 / 6.5 | 8 each | 76 / 71 / 69 / 79 | 349 / 280 / 233 / 349 | 12 / 503 / 499 / 12 |
| 7 | 6.0 / 6.0 / 6.0 / 6.0 | 7 each | 68 / 60 / 60 / 69 | 310 / 249 / 207 / 310 | 10 / 458 / 453 / 10 |
| 6 | 5.5 / 5.5 / 5.0 / 5.5 | 6 each | 59 / 50 / 51 / 60 | 271 / 217 / 181 / 271 | 7 / 398 / 406 / 7 |
| 5 | 5.0 / 5.0 / 4.0 / 5.0 | 5 each | 51 / 39 / 42 / 51 | 226 / 181 / 151 / 226 | 6 / 369 / 375 / 6 |
| 4 | 4.0 / 4.5 / 3.5 / 4.0 | 4 each | 42 / 28 / 33 / 41 | 181 / 145 / 121 / 181 | 4 / 331 / 342 / 4 |

Score ranges: IELTS 0-9; CELPIP 0-12; PTE 10-90; TEF speaking/writing 0-450, listening 0-360, reading 0-300; TCF speaking/writing 0-20, listening/reading 0-699.

## Watch
- IELTS listening and PTE thresholds differ by ability: never assume one band = one CLB.
- A TEF score out of 699 entered in a profile is a common error: use the ancien-score column.
- CRS language points by CLB: see `crs-scoring.md`. FSW points: see `fsw-selection-grid.md`.
