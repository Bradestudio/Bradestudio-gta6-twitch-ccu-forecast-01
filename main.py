"""gta6-twitch-ccu-forecast-01 entry in Python 3.13 (standard library only).

Forecasts the Twitch concurrent viewers of the Grand Theft Auto VI category
for hours 2..24 of its release day (2026-11-19 UTC), as five quantiles per
hour, from everything recorded up to the end of hour 1.

Method (calibrated on the kit's four practice launches; see README.md):
  Per hour h, fit an ordinary least squares regression over past big game
  launches (the case's `comparables`):

      log(viewers_h) = a_h + b_h * log(hour-1 print)

  and forecast log(viewers_h) ~ Normal(mu_h, sigma_h), where mu_h is the
  regression prediction at this case's hour-1 print and sigma_h is the
  IQR-based residual spread (x 1.1).  Quantiles are mu_h + z_tau * sigma_h.

  The regression is fit only on launches shaped like a console rolling-
  midnight launch with no early access (GTA VI's shape): the launch's
  hour-1 print must be at least 5% of its own release-day peak (this
  drops simultaneous-global unlocks, whose hour 1 is still pre-launch
  noise), and launches the house annotated "early-access-contaminated"
  are dropped (their hour 1 is inflated by early access).  If fewer
  than 3 launches survive, the filters relax in stages (drop the peak
  test, then the early-access test); with still nothing usable the
  program falls back to a median launch-shape ratio, and finally to
  the house persistence baseline.  The fallbacks never trigger on the
  kit's practice cases or on the final case as specified.

Why a regression on log(hour 1), not a ratio to hour 1: across launches
the release-day peak in absolute viewers varies far less (about 2x
across the practice launches) than the hour-1 print does (about 12x),
because hour 1 only catches the regions that already unlocked at
midnight UTC while the peak catches the whole world.  The fitted slope
falls from ~1.0 at hour 2 (the level is still hour 1's) to ~0.5-0.6 by
the evening hours (the level is mostly the launch's own scale).

Deterministic: pure arithmetic over the case file, fixed iteration
order, no randomness, no clock, no network.  Runs in well under a
second per case on one CPU.

How the grader runs it: `python3 -P -s /bot/main.py`
(PYTHONHASHSEED=0) in python:3.13-slim, standard library only.
Reads every <id>.in in $MAKEFUN_INPUT_DIR (else /input) and writes
<id>.out to $MAKEFUN_OUTPUT_DIR (else /output).
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a
# module shipped beside this file would import.  (This entry is a
# single file; the line is kept for parity with the kit's starter.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# Standard normal quantiles at LEVELS (exact to 15 digits).
Z = [-1.6448536269514722, -0.6744897501960817, 0.0,
     0.6744897501960817, 1.6448536269514722]

# A launch counts as "shaped like GTA VI" when its hour-1 print is at
# least this share of its own release-day peak.  In the kit's data the
# values cluster at <=0.011 (simultaneous-global unlocks, hour 1 still
# pre-launch) and >=0.082 (rolling-midnight launches); 0.05 sits in
# the empty gap between the clusters.
MIN_H1_OVER_PEAK = 0.05
# Minimum launches for a usable regression; fewer relaxes the filters.
MIN_ROWS = 3
# Residual spread: IQR/1.349, floored, then widened 10% (calibrated so
# the 90% band covers about 90% of practice hours).
SPREAD_FLOOR = 0.12
SPREAD_MULT = 1.1
MAX_VIEWERS = 1_000_000_000


def _parse_time(text):
    """ISO 8601 timestamp -> aware datetime (UTC)."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _norm_ppf(p):
    """Inverse standard normal CDF (Acklam's rational approximation).

    Only used when a case asks for levels other than LEVELS; for the
    standard levels the exact Z table above is used instead.
    """
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285984469534e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _z_values(levels):
    if list(levels) == LEVELS:
        return list(Z)
    return [_norm_ppf(p) for p in levels]


def _round2(x):
    """Round to 2 decimals, half up (as JavaScript Math.round does)."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value == int(value) else value


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def _quantile(xs, p):
    s = sorted(xs)
    n = len(s)
    if n == 1:
        return s[0]
    idx = p * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    f = idx - lo
    return s[lo] * (1 - f) + s[hi] * f


def _ols(xs, ys):
    """Least squares y = a + b*x; returns (a, b)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx if sxx > 0 else 0.0
    return my - b * mx, b


def _hour1_print(case):
    """Hour 1's print, with defensive fallbacks (never crash the run)."""
    for row in case.get("known", []):
        if row.get("hour") == 1:
            return max(1.0, float(row.get("viewers") or 1))
    hourly = case.get("history_hourly") or []
    if hourly:
        return max(1.0, float(hourly[-1].get("viewers") or 1))
    return 1000.0


def _comparable_rows(case):
    """One row per past launch: log hour-1 print and per-hour log viewers.

    A row keeps only the release day's 24 hourly points (00:00-23:00
    UTC of the launch's day_start).  Launches missing hour 1 or with
    fewer than 18 of the 24 hours are unusable and dropped.
    """
    rows = []
    for comp in case.get("comparables") or []:
        try:
            day0 = _parse_time(comp["day_start"])
        except (KeyError, TypeError, ValueError):
            continue
        by_hour = {}
        for point in comp.get("hourly") or []:
            try:
                at = _parse_time(point["from"])
            except (KeyError, TypeError, ValueError):
                continue
            viewers = point.get("viewers")
            if viewers is None:
                continue
            by_hour[at] = max(1.0, float(viewers))
        curve = [by_hour.get(day0 + timedelta(hours=h)) for h in range(24)]
        if curve[0] is None or sum(v is not None for v in curve) < 18:
            continue
        present = [v for v in curve if v is not None]
        unlock = comp.get("unlock") or ""
        rows.append({
            "log_h1": math.log(curve[0]),
            "hours": [None if v is None else math.log(v) for v in curve],
            "h1_over_peak": curve[0] / max(present),
            "early_access": "early-access-contaminated" in unlock,
        })
    return rows


def _regression_forecast(p1, rows, z_values):
    """Per-hour OLS on log viewers vs log hour-1 print.

    Returns {hour: [q05, q25, q50, q75, q95]} for hours 2..24, or None
    when fewer than MIN_ROWS launches have that hour.
    """
    log_p1 = math.log(max(1.0, p1))
    out = {}
    for h in range(2, 25):
        pairs = [(r["log_h1"], r["hours"][h - 1]) for r in rows
                 if r["hours"][h - 1] is not None]
        if len(pairs) < MIN_ROWS:
            return None
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        a, b = _ols(xs, ys)
        mu = a + b * log_p1
        resid = [y - (a + b * x) for x, y in pairs]
        sigma = max((_quantile(resid, 0.75) - _quantile(resid, 0.25)) / 1.349,
                    SPREAD_FLOOR) * SPREAD_MULT
        qs = []
        prev = 0.0
        for z in z_values:
            q = math.exp(mu + z * sigma)
            q = min(max(q, 1.0), float(MAX_VIEWERS))
            q = _round2(q)
            if q < prev:  # keep quantiles non-decreasing after rounding
                q = prev
            qs.append(q)
            prev = q
        out[h] = qs
    return out


def _ratio_forecast(p1, rows, z_values):
    """Fallback: median launch-shape ratio per hour, IQR spread."""
    out = {}
    for h in range(2, 25):
        ratios = [r["hours"][h - 1] - r["log_h1"] for r in rows
                  if r["hours"][h - 1] is not None]
        if len(ratios) < MIN_ROWS:
            return None
        mu = math.log(max(1.0, p1)) + _median(ratios)
        sigma = max((_quantile(ratios, 0.75) - _quantile(ratios, 0.25)) / 1.349,
                    0.15)
        qs = []
        prev = 0.0
        for z in z_values:
            q = min(max(math.exp(mu + z * sigma), 1.0), float(MAX_VIEWERS))
            q = _round2(q)
            if q < prev:
                q = prev
            qs.append(q)
            prev = q
        out[h] = qs
    return out


def _persistence_forecast(p1, z_values):
    """Last fallback: the house baseline (every hour stays at hour 1)."""
    out = {}
    for h in range(2, 25):
        qs = []
        prev = 0.0
        for z in z_values:
            q = min(max(p1 * math.exp(z * 0.15 * math.sqrt(h - 1)), 1.0),
                    float(MAX_VIEWERS))
            q = _round2(q)
            if q < prev:
                q = prev
            qs.append(q)
            prev = q
        out[h] = qs
    return out


def forecast_case(case):
    levels = case.get("levels") or LEVELS
    z_values = _z_values(levels)
    p1 = _hour1_print(case)
    rows = _comparable_rows(case)

    # Launches shaped like GTA VI: rolling-midnight console launch,
    # no early access (see module docstring).
    shaped = [r for r in rows
              if not r["early_access"]
              and r["h1_over_peak"] >= MIN_H1_OVER_PEAK]
    forecast = _regression_forecast(p1, shaped, z_values)
    if forecast is None:
        no_ea = [r for r in rows if not r["early_access"]]
        forecast = _regression_forecast(p1, no_ea, z_values)
    if forecast is None:
        forecast = _regression_forecast(p1, rows, z_values)
    if forecast is None:
        forecast = _ratio_forecast(p1, rows, z_values)
    if forecast is None:
        forecast = _persistence_forecast(p1, z_values)
    return {"hours": [{"hour": h, "q": forecast[h]} for h in range(2, 25)]}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n",
            encoding="utf-8")


if __name__ == "__main__":
    main()
