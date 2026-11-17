# Build log — gta6-twitch-ccu-forecast-01 entry

Session: 17 Nov 2026, ~15:13–15:30 WIB. Builder: Muse (Meta AI agent,
working for Andi / @Bradestudio). No submission was made in this session;
the entry was built and graded locally only. A GitHub repository (public,
created by Andi after the competition opened at 13:00 WIB) and Andi's
explicit confirmation are still needed before any submit.

## Bounty (from make.fun API detail snapshot, 17 Nov 2026 15:12 WIB)

- Slug: gta6-twitch-ccu-forecast-01 — "Forecast GTA VI's launch-day
  Twitch viewers hour by hour"
- Free (entry fee $0, pot $250), escrow state open. Prizes: 1st $50,
  2nd $35, 3rd $25, 4th–10th $10, 11th–20th $7. 21 submissions already
  in when found by the periodic watcher.
- Opens 2026-11-17T06:00:00Z (13:00 WIB), deadline 2026-11-19T01:00:00Z
  (19 Nov 2026 08:00 WIB). Status open, acceptingSubmissions true.
- This session started after the competition opened, so it meets the
  transcript rule (session must start at/after opening).

## Kit

- Downloaded from https://make.fun/c/gta6-twitch-ccu-forecast-01/kit
  (6.0 MB tarball) to
  ~/workspace/makefun/gta6-twitch-ccu-forecast-01-kit/ — kit format
  agent-fun/kit/v1, harness program/v1, 4 practice cases (p00–p03),
  starter in Python + TypeScript (house persistence baseline).
- Read RULES.txt (the full rules text), competition.yaml, the starter,
  input/NOTICE.txt (data provenance + SullyGnome fetch URLs) and the
  detail JSON (rules, rewards, escrow).
- Official `grade-local` refuses this kit: "its scorer and reference
  data are not published in the kit, so it is graded on the server
  only". So a local replica scorer was built instead (below).

## Practice answers (replica scorer)

- The practice answers are not in the kit. They were rebuilt from the
  same source the house used: SullyGnome's "Average viewers" hourly
  series, one API request per practice game for its release month
  (4 requests total, no bulk download):
  Wolverine 117671 (2026-09), RDR2 28264 (2018-10), God of War
  Ragnarök 65645 (2022-11), Spider-Man 2 97296 (2023-10).
- Validation: all four rebuilt hour-1 prints match the cases' `known`
  values exactly (23,357 / 116,550 / 269,517 / 119,087); no hour
  missing. (First attempt used the "Peak viewers" dataset by mistake;
  the "Average viewers" dataset matched the cases' history_hourly
  167/167 exactly.)
- Scorer replica: mean pinball loss on the log scale over every hour
  2–24 and level 0.05/0.25/0.5/0.75/0.95, exactly as the rules define
  it. Sanity check: the kit starter scores 0.3871 on it with typical
  miss 82.7% and 90% coverage 0.783 — the rules say "about 0.387",
  "about 82.8%", "about 0.783". The replica is faithful.

## Strategy search (all scored on the 4 practice cases)

1. House baseline (persistence): 0.3871.
2. Median launch-shape ratio per hour (lognormal spread from
   cross-comparable std): 0.3997 — spread far too wide.
3. Median ratio, empirical quantiles: 0.3240.
4. Median ratio, IQR spread: 0.3102.
5. Per-hour OLS log(viewers_h) ~ log(hour-1 print), all comparables,
   IQR spread: 0.2273; spread ×0.8: 0.2096.
6. Same regression, dropping "early-access-contaminated" launches:
   0.2090; spread ×0.7: 0.1818.
7. Same regression, dropping early-access AND launches whose hour 1 is
   under 5% of their own release-day peak (simultaneous-global
   unlocks, hour 1 still pre-launch noise): 0.1736, spread ×1.1:
   **0.1739** with 90% coverage 0.902 (chosen).
   - Why the filter matters: simultaneous unlocks give OLS extreme
     leverage (tiny hour 1, huge peak) and flatten the late-hour slope
     to ~0.1; after filtering, slopes run ~1.0 at hour 2 down to
     ~0.5–0.6 in the evening and residual spread drops to 0.15–0.39
     in log units.
   - Extra features tested and rejected (no gain): log channels in
     hour 1, log pre-release 24 h mean, console-only weighting.

## Chosen model (shipped in main.py)

Per hour h = 2..24: OLS of log(viewers_h) on log(hour-1 print) over
the filtered comparables; forecast log(viewers_h) ~
Normal(mu_h, sigma_h) with sigma_h = max(IQR(residuals)/1.349, 0.12)
× 1.1; quantiles mu_h + z_tau × sigma_h. Filter: not
early-access-contaminated and hour-1 ≥ 5% of own release-day peak;
fallbacks relax the filters, then a median-ratio forecast, then the
house baseline (never triggered on practice or on the final case as
specified). Single file, standard library only, deterministic.

## Verification of the shipped entry

- Ran `python3 -P -s main.py` on the kit's input/ (4 practice cases):
  practice loss **0.1739** (p00 0.233, p01 0.161, p02 0.120,
  p03 0.181), typical miss 31.0%, 90% coverage 0.902 — 55% lower
  loss than the house baseline (0.3871). Output schema validated:
  23 rows, hours 2–24, five non-decreasing quantiles each in
  (0, 1e9], files ~1.5 KB (limit 65,536).
- Determinism: two full runs byte-for-byte identical.
- Runtime: ~0.05 s per case (limit 8 s).
- Synthetic final-case test: case h00 built from p00's structure with
  42 comparables (the 4 practice launches added, all passing the
  filter) and hour-1 print 300,000 — runs in 0.09 s, median curve
  dips mid-day (~203k at hours 10–12) and peaks ~407k at hour 21,
  bands widening with horizon. Sane.

## What is still needed from Andi

- Create a NEW public GitHub repository (name suggestion:
  Bradestudio-gta6-twitch-ccu-forecast-01) and put these files in it:
  `main.py`, `LICENSE`, `README.md`, `TRANSCRIPT.md`. The repo must be
  created after the competition opened (it was — opening was 13:00 WIB
  17 Nov 2026).
- Confirm explicitly before any submit. No submit, push, or repo
  creation was done in this session.
