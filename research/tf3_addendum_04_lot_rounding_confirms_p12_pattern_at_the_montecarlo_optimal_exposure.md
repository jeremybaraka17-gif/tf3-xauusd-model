# TF3 Addendum 04 — Testing the live script surfaces the same lot-rounding problem P12 already found, now for TF3 specifically, even at the Monte Carlo's own recommended exposure

## What happened

Running `live/tf3_challenge_live.py` end-to-end (governor init + a live check against real recent XAUUSD prices) to verify the package actually works before shipping it — this is not a hypothetical concern raised in the abstract, it showed up on the FIRST real test run: at `effective_exposure_mult=2.0` (the $10k challenge's Monte Carlo peak, `tf3_addendum_03...md`), a -0.2148 raw forecast on real recent data produced a target of **0.0048 lots** — below GFT's min lot (0.01, per this project's own `h5b_addendum_02` confirmation, though that was a different broker; treated here as the best available estimate, not GFT-confirmed).

This is not a one-off. Checked systematically across the dev+OOS history at the assumed price level:

| Config | Median lots (when position ≠ 0) | % of position-days below 0.01 min lot |
|---|---|---|
| $5k @ exposure_mult=2.0 | 0.0124 | 38.3% |
| $5k @ exposure_mult=2.5 | 0.0155 | 24.1% |
| $10k @ exposure_mult=2.0 | 0.0248 | 17.6% |

## Why this matters, stated plainly

This is the SAME structural problem `p4_signal_workflow.py`'s own comments already documented for the other live system's XAUUSD leg (confirmed on two real GFT accounts: "structurally round to zero lots" at $5k-$10k) — this project already knew this pattern exists for gold at this capital level, and it shows up here too, via a different sizing mechanism (TF3's leveraged-exposure-fraction sizing vs. the other system's ATR-stop-distance risk sizing), for the same underlying reason: gold's ~$3,800+ price and 100-oz contract size make one full lot represent roughly $380,000 of notional, which is large relative to $5k-$10k of account equity even before conviction-scaling the position down from ±1 toward TF3's typical, smaller working range.

**The Monte Carlo simulation in `tf3_addendum_03...md` does NOT account for this.** It assumes exposure scales continuously and exactly with the forecast; in reality, on a large fraction of trading days (17.6-38.3% at the exposure levels that simulation recommended), the true executable position is either zero (rounds down entirely) or a coarser, lot-quantized step rather than the smooth fractional exposure the backtest and the Monte Carlo both assumed. This means the Monte Carlo's reported pass rates (36.9% best case for $5k, 43.1% for $10k) are **optimistic** relative to what a real, lot-quantized account would actually achieve — a real account effectively trades a noisier, more sparsely-updated version of the same signal, which this project's own prior findings (H3/H4's low-trade-count results, repeatedly) suggest tends to underperform a smoother version of the same construction, not match it.

## What this does NOT do

Does not re-run the Monte Carlo with lot quantization built in — that is real, additional work (each simulated day would need `floor(raw_lots / MIN_LOT) * MIN_LOT` applied before computing the return, which changes the return-generating assumption materially and should be its own disclosed re-run, not folded in silently here). Does not change the `effective_exposure_mult` recommendation in `tf3_addendum_03...md` — raising exposure further to fix lot-rounding would directly fight the same Monte Carlo's own finding that pass rate falls past ~2-2.5x, so this is a genuine tension, not a free fix. Does not confirm GFT's actual min lot for XAUUSD (used here at 0.01, the value confirmed for a DIFFERENT broker in `h5b_addendum_02` — flagged, not assumed reliable for GFT specifically).

## Bottom line for deployment

Both packaged challenge configs should be read as **optimistic upper bounds** on pass probability, not as the actual expected pass rate — the $5k config more so than the $10k one, since its lot-rounding problem is roughly double the $10k account's at a comparable exposure multiple. This is disclosed here rather than smoothed over, consistent with this project's standing practice of reporting a limitation the moment it's found rather than after the fact.
