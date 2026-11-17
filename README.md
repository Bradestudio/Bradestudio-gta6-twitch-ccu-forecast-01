# Bradestudio-gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Bradestudio/Bradestudio-gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Bradestudio/Bradestudio-gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A Python 3.13 program (standard library only) for the make.fun bounty
"Forecast GTA VI's launch-day Twitch viewers hour by hour". It reads one
case (everything recorded up to the end of the release day's first hour)
and forecasts the Twitch concurrent viewers of the Grand Theft Auto VI
category for hours 2–24 of 2026-11-19 (UTC), as five quantiles per hour.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

(`main.py` reads every `<id>.in` in the input directory and writes
`<id>.out` to the output directory. The grader runs it as
`python3 -P -s /bot/main.py` with `/input` and `/output`.)

## Strategy

Per hour h = 2..24, fit an ordinary least squares regression over past
big game launches (the case's `comparables`):

```
log(viewers_h) = a_h + b_h * log(hour-1 print)
```

and forecast `log(viewers_h) ~ Normal(mu_h, sigma_h)`, where `mu_h` is
the regression prediction at this case's hour-1 print and `sigma_h` is
the IQR-based residual spread (× 1.1). Quantiles are `mu_h + z_tau *
sigma_h` at the 5%, 25%, 50%, 75% and 95% levels.

The regression uses only launches shaped like GTA VI — a console
rolling-midnight launch with no early access:

- the launch's hour-1 print is at least 5% of its own release-day peak
  (this drops simultaneous-global unlocks, whose hour 1 is still
  pre-launch noise — in the kit's data the values cluster at ≤ 0.011
  and ≥ 0.082, so 0.05 sits in an empty gap);
- launches the house annotated `early-access-contaminated` are dropped
  (their hour 1 is inflated by early access).

If fewer than 3 launches survive, the filters relax in stages, then
the program falls back to a median launch-shape ratio, and finally to
the house persistence baseline. The fallbacks never trigger on the
kit's practice cases or on the final case as specified.

Why regress the level on log(hour 1) instead of forecasting a ratio to
hour 1: across launches the release-day peak in absolute viewers varies
far less (~2x across the practice launches) than the hour-1 print does
(~12x), because hour 1 only catches the regions that already unlocked
at midnight UTC while the peak catches the whole world. The fitted
slope falls from ~1.0 at hour 2 to ~0.5–0.6 by the evening hours.

## Local verification (practice cases, replica scorer)

The kit's official `grade-local` cannot grade this competition (its
scorer and reference data are not published), so the practice answers
were rebuilt from the same source the house used — SullyGnome's hourly
averages, fetched once per practice game for its release month — and
scored with a replica of the rules' pinball loss on the log scale.
All four rebuilt hour-1 prints match the cases' `known` values exactly.

| Entry | Practice loss | Typical miss | 90% coverage |
| --- | --- | --- | --- |
| House baseline (kit starter) | 0.3871 | 82.7% | 0.783 |
| This entry | **0.1739** | 31.0% | 0.902 |

Per-case loss: p00 (Wolverine) 0.233, p01 (RDR2) 0.161,
p02 (God of War Ragnarök) 0.120, p03 (Spider-Man 2) 0.181.
55% lower loss than the house baseline. Practice pays nothing and
is no guide to the final — but the entry beats the house baseline by
a wide margin on every practice case.

The entry is deterministic (two runs on the practice set are byte for
byte identical) and runs in ~0.05 s per case, far inside the 8 s cap.

## Files

- `main.py` — the whole entry (single file, standard library only).
- `LICENSE` — MIT.
- `TRANSCRIPT.md` — build log of the agent session that built this entry.

---

<sub>Entered on [make.fun](https://make.fun/?ref=qjs4e9sj&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
