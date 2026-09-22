# TF3 Addendum 02 — Completeness review: parameters and decisions not yet specified, requested explicitly by the user before packaging.

This is a plain audit of what is fixed vs. what is still open in the TF3 XAUUSD construction, done at the user's request ("make sure you structure it like a proper quant model i may have missed other parameters"). Nothing below is a new hypothesis or a new test — it is a checklist of gaps, some already disclosed in prior docs and repeated here for completeness, some genuinely new to this review.

## Parameters that ARE fixed, and where they come from

| Parameter | Value | Source |
|---|---|---|
| EWMAC pairs | (2,8),(4,16),(8,32),(16,64),(32,128),(64,256) | Carver, *Systematic Trading* (2015) |
| Vol-normalization window | 60d rolling std of close | TF2 model spec, Section 2 |
| Per-pair forecast scalar target | avg abs forecast = 10, dev-calibrated | TF2 model spec, Section 2 |
| Forecast cap | ±20 | TF2 model spec, Section 2 |
| Combination method | simple average across pairs | TF2 model spec, Section 2 |
| Stage for XAUUSD | Stage 1 only (no accel multiplier, no vol-spike cut) | TF2 model spec, Section 3 |
| Position-inertia buffer width | 0.10 | TF3 model spec, Section 2 |
| Execution lag | 1 trading day | TF3 model spec, Section 4 |
| Point size (cost inference) | 0.01 | TF2 model spec, Section 6 |
| Dev/OOS split | dev ≤ 2025-04-02, OOS 2025-04-03..2026-07-03 | project-wide, locked |
| Floor-breach threshold | -6% | project-wide, locked |

## Parameters/decisions genuinely still OPEN (repeated from existing docs, consolidated here)

1. **`risk_allocation_fraction`** — how much of total account capital this system gets. Not a research output; a capital-allocation/business decision, explicitly left unset (model_spec_tf3, Section 3). The live script defaults it to 0.0 rather than guessing a number.
2. **Live deployment slot** — XAUUSD/TF3 is not currently assigned to either existing live system (prop-firm FX/WTI trend system, GOAT-8). Deploying it would be a third live construction, not a modification of either existing one (model_spec_tf2, Section 9; model_spec_tf3, Section 7). Not decided.
3. **Interaction with CAP1** — CAP1's capital-allocation analysis was scoped to the two EXISTING live systems only; it has not been extended to include a third XAUUSD/TF3 system, and CAP1's own allocation-optimization numbers were separately flagged as unreliable pending better prop-firm proxy data (cap1_addendum_01). A third system's capital share cannot currently be derived from anything already computed.
4. **Data-integrity kill switch** — specified qualitatively (model_spec_tf3, Section 5) but not implemented with a concrete threshold. The `live/` script stubs this with a `NotImplementedError`, not a placeholder that looks functional but isn't.
5. **NAS100's regime oddity** — not relevant to XAUUSD directly, but was left open in the TF2 family and is worth noting here for completeness since it means the broader TF2/TF3 construction is not uniformly understood across instruments, only XAUUSD's mechanism is cleanly interpretable.

## Parameters/decisions this review surfaces as NEWLY notable (not previously written down explicitly)

1. **`CONTRACT_SIZE = 100` (oz per lot) in `live/tf3_xauusd_live.py`** — this is a standard XAUUSD CFD/futures convention assumption, not verified against any specific broker's contract specification in this project. It was never stated anywhere in the TF2/TF3 research docs because the research never got to lot-sizing arithmetic until this packaging step. Flagged now: confirm against the actual broker before this number is used to size a real order — a wrong contract size silently produces a wrong exposure at any `risk_allocation_fraction`.
2. **Slippage is not modeled separately from spread.** The cost model throughout (TF2's net-of-cost check, this package's backtest) uses only the spread column times point size. Real fills, especially during the kind of vol-spike conditions the floor-breach metric is designed around, may include slippage beyond quoted spread. This was true of every net-of-cost check in this project (FD4, FD7, FD10, TF2) — not a new gap specific to TF3, but worth restating here since this is the first document meant to sit next to a literal live-execution script.
3. **No maximum daily-loss or portfolio-level circuit breaker is specified**, distinct from the -6% floor-breach diagnostic (which is a backtest reporting metric, not a live risk control) and the qualitative kill switches in Section 5 of the TF3 spec. If XAUUSD/TF3 is deployed as a third live system, whatever overall risk framework governs the two existing live systems (position limits, max daily loss, margin usage) has not been explicitly extended to include it — this is a deployment/operations gap, not a signal-construction one.
4. **Walk-forward monitoring is specified qualitatively** (model_spec_tf3, Section 6: "repeat Walk-Forward 01's approach once enough live calendar time accumulates") but no concrete re-validation cadence (e.g., quarterly, after N trading days, after a fixed drawdown trigger) is set. Left as a genuinely open scheduling decision, not filled in here since doing so now would be inventing a number rather than reporting one.
5. **The buffer reproduction discrepancy** (Addendum 01, this folder) means `buffer_width=0.10`'s exact effect size is not pinned down as precisely as the original spec implied — the qualitative conclusion holds, the exact turnover/Sharpe numbers should be read from `backtest/tf3_xauusd_backtest.py`'s output going forward, not from the original spec's Section 2 sanity check.

## What this review does NOT do

Does not propose values for any of the open items above — that would be exactly the kind of after-the-fact parameter selection this project's discipline is built to avoid. Does not re-run or re-validate the underlying signal. Does not change any per-instrument recommendation. It is a checklist, not a new result.
