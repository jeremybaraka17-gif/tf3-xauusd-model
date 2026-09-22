# Hypothesis TF4 — Long-only EWMAC (shorts removed) with a vol-normalization-window robustness sweep

Status: PRE-REGISTERED, LOCKED BEFORE RUNNING.

## Why this, and why it is not curve-fitting

Addendum 05 found that TF3's short side destroys value on every metric, both windows — this motivates dropping shorts, a disclosed, evidence-driven construction change, not an arbitrary tweak. The user separately asked for a robustness check before trusting that change: rather than accept the long-only result at its single already-used vol-normalization window (60 days) and call it done, this hypothesis sweeps that window across several LOCKED candidate values, chosen now, before seeing any of their results, specifically to check whether the long-only advantage is a genuine property of the construction or an artifact of one specific window choice.

This is the correct way to answer "is this robust," not by re-running with different windows until one looks best (that would be curve-fitting) and not by tuning any OTHER parameter alongside it in the same run (that would confound which change did what). Only `VOL_WINDOW` moves in this hypothesis. Everything else — the six EWMAC pairs (2/8...64/256), the buffer width (0.10), the forecast cap (±20), the point size (0.01), the dev/OOS split — is Carver's own literature-standard value or this project's already-locked convention, reused unchanged. A note on why those are NOT being swept is in Section 5.

## Section 1 — Claim

The long-only EWMAC construction (identical to TF3 except `raw_position = clip(combined_forecast/20, 0, 1)` instead of `clip(..., -1, 1)`) beats the two-sided TF3 construction on net Sharpe, in both dev and OOS, not only at `VOL_WINDOW=60` (already shown in Addendum 05) but across a MAJORITY of the locked candidate windows below — i.e., the advantage is a property of removing shorts, not a coincidence of one specific normalization window.

## Section 2 — Locked candidate windows (chosen now, not after seeing results)

`VOL_WINDOW ∈ {30, 45, 60, 90, 120}` trading days. Five values, spread roughly geometrically around the original 60-day choice (not clustered near it, so the sweep can actually detect fragility), all round numbers a practitioner would plausibly pick without reference to this data — not searched from a finer grid to find where the result happens to look best.

## Section 3 — Construction (frozen except VOL_WINDOW)

Per candidate window `W`: `native_vol = rolling_std(close, W)`; per-pair `norm = (EWMA_fast - EWMA_slow) / native_vol`; per-pair scalar re-calibrated on DEV DATA ONLY for each `W` (since the scalar's job is unit normalization against whatever `norm`'s own dev-window scale turns out to be at that window — holding the ORIGINAL W=60 scalars fixed while changing W would silently break the units-normalization the scalar exists to provide, not a fair test of the window itself). Everything downstream (combination, clip to [0,1] for long-only, buffer, cost model) is identical to TF3/Addendum 05's already-used code, unchanged.

## Section 4 — Falsification condition (locked)

For each of the 5 windows, compute net Sharpe (dev and OOS) for long-only vs. two-sided. Count how many of the 5 windows show long-only beating two-sided on Sharpe in BOTH dev and OOS simultaneously (matching Addendum 05's own two-window standard). **PASS (robust)**: ≥4 of 5 windows show this. **PARTIAL (window-dependent)**: 2-3 of 5. **FAIL (fragile / W=60 was a coincidence)**: 0-1 of 5. Also reports each window's absolute Sharpe/breach numbers against the 200d-MA benchmark, since "beats two-sided" and "beats the 200d-MA" are different bars (Addendum 05 only established the former).

## Section 5 — What is deliberately NOT swept, and why

- **EWMAC pair spans (2/8...64/256)**: Carver's own published set, not derived from this data. Sweeping these would be tuning the actual shape of the trend filter to this specific price history — the textbook definition of curve-fitting this project's standing "No curve fitting" instruction exists to prevent.
- **Buffer width (0.10)**: already disclosed as a literature-standard starting point in `model_spec_tf3...md`, explicitly flagged there as "to monitor and revisit with real fill data, not backtested and picked for this specific result." Sweeping it now, on this same backtest, would be exactly the after-the-fact tuning that document said not to do.
- **Forecast cap (±20) and scalar target (10)**: Carver's own calibration convention, a units choice, not a performance lever.
- **Point size / cost assumption (0.01)**: already independently inferred from the data's own spread-quoting convention (TF2 model spec, Section 6) — re-deriving it here would not be a robustness check on the SIGNAL, it would be revisiting a different, already-settled question.

If, after this hypothesis, there is a specific, motivated reason to test one of the above (not "it might make the curve look better"), that should be its own pre-registered hypothesis, stating the reason up front — not folded into this one.

## Two-attempt-then-stop

First run of this construction.
