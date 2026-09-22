# Hypothesis TF1 — Pre-Registration: multi-scale EWMAC forecast combination + acceleration-based sizing + volatility-spike cut, on the 16-symbol equity/index universe

Status: PRE-REGISTERED, not yet run.

## Source, and an honest note on sourcing

The user supplied a practitioner explainer (promotional in tone — it solicits membership signups) describing a multi-timescale EWMA-crossover trend system with forecast normalization, forecast combination across speeds, and acceleration-based position sizing. That post is not a citable source on its own. The underlying construction it describes, however, is real, well-documented, and independently verifiable: this is the EWMAC (exponentially-weighted moving-average crossover) forecast framework formalized by Robert Carver in *Systematic Trading* (2015) — the published methodology behind AHL/Man Group-style CTA trend systems — and academically discussed in Baltas & Kosowski's work on trend-following replication and the "life cycle" of a trend (the birth/cruise/decay framing the post uses has a direct academic analogue in documented findings on trend "aging" and momentum decay). This hypothesis is built on the verifiable framework, using the post only as the trigger for testing it now, per the user's explicit "take this as inspo" direction.

One correction made before building anything: the post's own listed EWMAC pair sequence (2/8, 4/16, 8/32, 16/64, 64/256) skips a step — a clean geometric doubling requires 2/8, 4/16, 8/32, 16/64, **32/128**, 64/256. This is also Carver's actual published pair set (6 pairs, not 5). Using the corrected, complete geometric sequence, not the post's as-typed one, since "perfect geometry" is the post's own claimed property and the typo breaks it.

## Construction (locked)

**Per-instrument, per-pair EWMAC forecast**: for each of 6 pairs (fast, slow) = (2,8), (4,16), (8,32), (16,64), (32,128), (64,256) trading days:
1. `raw = EWMA(close, span=fast) - EWMA(close, span=slow)`
2. Vol-normalize: `norm = raw / (close.rolling(60).std())` — reusing this project's own established 60-day vol convention, computed on each instrument's native calendar per the fix in Bug Correction 02 (this signal uses `.ewm()` and `.rolling()`, both subject to the same cross-calendar-gap issue as EV1/EV3, so the native-calendar fix is applied from the start here, not discovered as a bug mid-run).
3. Scale to a target average absolute forecast of 10 (Carver's own calibration target): a single scalar per pair, computed once on the DEV window only (`10 / mean(abs(norm on dev))`), frozen before touching OOS — this is a units-normalization constant, not a re-tuned trading parameter, and is computed identically to how Carver's own published scalars are derived (from historical average forecast magnitude, not from optimizing performance).
4. Cap each pair's scaled forecast at ±20.

**Combined forecast**: simple average of the 6 pairs' capped forecasts, per instrument, per day. This is where "layers agreeing vs. fighting" lives mechanically — agreement pushes the average toward ±20, disagreement pulls it toward 0. No additional cap beyond the natural bound from averaging 6 already-capped series.

**Stage 1 position**: `position = combined_forecast / 20` (range -1 to +1), inverse-60-day-vol-scaled across instruments and monthly-rebalanced into a blended portfolio, matching this project's standing IV-blend convention (FB1/EV1). Long AND short (this is explicitly two-sided, like TSMOM, not long-only — the post describes a symmetric trend-reading machine, not a long-only filter).

**Stage 2 (only run if Stage 1 is not a clean fail)**: layer the two mechanisms the post frames as the actual point of this construction —
- **Acceleration sizing**: `accel = combined_forecast.diff(10)` (10-day rate of change of the combined forecast — a disclosed, reasonable choice for "the gas pedal," not tuned after seeing results). Position multiplier scales up when `sign(accel) == sign(combined_forecast)` (trend still speeding up in its own direction) and scales down when they diverge (decelerating) — implemented as `size_mult = clip(1 + 0.5*sign(accel*combined_forecast), 0.5, 1.5)`, a disclosed, symmetric, non-aggressive multiplier chosen for simplicity, not fit to this data.
- **Volatility-spike cut**: when an instrument's realized vol (21-day, annualized) exceeds 1.5x its own 252-day trailing average vol (both computed on native calendar), cut that instrument's position to 50%. This is the direct, literal implementation of "exit based on volatility spikes" — the user's original request from the start of this loop.

## Universe, split, data

Same 16-symbol, split-corrected universe and dev/OOS boundary as EV1-EV3 (`ev1_prices_corrected.csv`, 2025-04-02/2025-04-03-2026-07-03) — no new choices.

## Feasibility floor

The slowest pair (64/256) needs 256 trading days of warm-up before producing a real signal; combined with the fastest pair's noise, expect this construction to generate meaningfully more frequent position changes than EV1's TSMOM (daily-updating continuous forecast, not a monthly re-rank) — feasibility is about magnitude of exposure change, not discrete transition count here. Floor: OOS window (326 obs) must have at least 60 days where the blended combined-forecast portfolio's absolute weight exceeds 0.1 (i.e., the book is meaningfully non-flat, not sitting near-zero from cancellation the whole window) for OOS to be evaluable. Below that, OOS is INCONCLUSIVE.

## Verdict rule

Same structure as EV1: PRIMARY condition is blended Sharpe > buy-and-hold-EW Sharpe, both windows. SECONDARY is strictly fewer -6% floor-breach episodes, both windows. PASS requires primary in both windows; PARTIAL if primary holds in one window or both windows are individually positive; FAIL otherwise. Stage 2 compared against Stage 1 (not against buy-and-hold) on the same primary/secondary structure, and only run if Stage 1 is not a clean fail — same discipline as every prior EV-family hypothesis.

## What would make a second attempt (beyond Stage 1→Stage 2) legitimate

If Stage 1+2 together fail, the only disclosed follow-up would be testing on the original 7/8-instrument FX/commodity universe (GOAT-7/8) instead of the 16-symbol equity universe — since Carver's own framework was built for and is most published on futures/FX/commodity universes, not single-name equities, so that would be testing the construction on the asset class it was actually designed for, not an invented tweak to the signal itself. Not run without a checkpoint after Stage 1+2's result is reported.
