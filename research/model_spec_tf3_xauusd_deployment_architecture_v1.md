# Model Spec — TF3: XAUUSD deployment architecture (built on TF2's validated Stage 1 construction), v1

Status: architecture for a deployable instance. Built directly on TF2's already-validated XAUUSD result (gross PASS, net PASS, mechanistically-sensible regime concentration) — no signal change from what was tested. What's new here is everything between "a Sharpe number in a backtest" and "an order sent to a broker."

## 1. Signal (unchanged from TF2, Stage 1 — reused exactly, not re-tuned for this document)

Six EWMAC pairs (2/8, 4/16, 8/32, 16/64, 32/128, 64/256) on XAUUSD daily close, vol-normalized (60-day), dev-calibrated scalars (target average absolute forecast of 10 per pair, frozen at TF2's already-computed values — not re-fit here), combined by simple average, capped ±20. `target_position = clip(combined_forecast / 20, -1, 1)`. No acceleration multiplier, no vol-spike cut — TF2 found Stage 1 alone already clears both the gross and net breach-count bar on XAUUSD with lower turnover than Stage 1+2, and the added complexity isn't earning its cost on this instrument specifically (it does on XAGUSD/NAS100, it doesn't materially help here).

## 2. Position-inertia buffer (new — added for deployment, not backtested as a performance parameter)

TF2's backtest re-traded on every daily change in `target_position`, generating the turnover behind its (small but nonzero) cost drag. Robert Carver's own published framework — the same source this whole construction is built on — includes a buffer zone specifically to address this: only trade when the target position has moved far enough from the current held position to be worth the cost of trading, rather than chasing every daily wiggle.

**Buffer rule**: maintain a currently-held position `held_position`. Only submit an order when `abs(target_position - held_position) > buffer_width`, and when triggered, trade only PART of the way to the target (to the nearer edge of the buffer band, not all the way to the target) — this is Carver's own published "trade to the edge of the buffer" rule, not a new invention. `buffer_width = 0.10` (in the same -1 to +1 units as `target_position`) is a reasonable, literature-standard starting point (Carver's own book uses a similar order-of-magnitude buffer relative to a forecast's typical day-to-day noise) — this number is disclosed as a starting point to monitor and revisit with real fill data, not backtested and picked for this specific result, since doing so now would be exactly the after-the-fact tuning this project's discipline exists to avoid. If revisited, it should be re-derived from XAUUSD's own realized cost-per-trade vs. tracking-error-cost tradeoff, using data collected after deployment, not by re-running this backtest with different buffer values until one looks best.

**Sanity check run before shipping this document** (not a re-tune — the 0.10 buffer width was chosen first, from Carver's own literature convention, then checked against the already-collected data to confirm it doesn't quietly break TF2's validated result): with the buffer applied, dev turnover drops from 0.0615 to 0.0303 average daily |position change| (roughly halved), OOS turnover drops from 0.0572 to 0.0267. Sharpe is essentially unchanged (dev 0.421→0.424, OOS 0.939→0.999) and breach-episode count is exactly unchanged (11 dev, 6 OOS) in both windows. The buffer does what it's supposed to — cut trading frequency without giving up the validated result — and did not require adjusting the 0.10 width to achieve this.

## 3. Position sizing in account terms

`target_position` (range -1 to +1) is a fraction of a notional risk allocation, not a lot size directly. Convert as:

```
notional_risk_capital = account_equity * risk_allocation_fraction
target_exposure_usd = target_position * notional_risk_capital
target_lots = target_exposure_usd / (contract_size * xauusd_price)
```

`risk_allocation_fraction` is a business decision (how much of total capital this system gets), not something this research determines — flagged explicitly as an open input, not defaulted to a number here. Every other live construction in this project (prop-firm system, GOAT-8) already has its own capital allocation; this would be a third, and CAP1's own finding (correlation ~0.31 between the two existing systems, real but moderate diversification) is the closest available evidence for how a third system might slot in, though CAP1 was scoped to the other two systems specifically and hasn't been extended to include this one.

## 4. Execution logic

- Signal computed once per day on the daily close (matching the backtest exactly — no intraday recomputation, since the underlying EWMACs are daily-span).
- Order submitted the next trading session at market open (matching the 1-day lag already built into and validated in the backtest — executing same-day-on-close would NOT match what was tested).
- Buffer check (Section 2) run before any order is placed; a target inside the buffer band around the current held position means no trade that day, not a partial one.

## 5. Risk limits (deployment-layer, not present in the backtest, needed regardless of signal quality)

- **Hard position cap**: `target_position` is already bounded [-1, 1] by construction; this bounds notional exposure to `risk_allocation_fraction` of capital by design, no additional cap needed at the signal layer.
- **Kill switch on data integrity**: if the daily price feed shows a single-day move inconsistent with realistic gold price action (the kind of discontinuity this project has repeatedly found in raw feeds — see Bug Correction 02's equity-universe findings for the general pattern), suspend new position changes and hold the last valid position until the data anomaly is confirmed or corrected, rather than trading on a bad print.
- **Kill switch on regime**: given the regime-conditioning finding that this construction's edge concentrates in falling-real-yield/low-vol conditions and is negative in rising-real-yield/high-vol conditions, a sustained period in the unfavorable regime bucket is expected to produce real drawdown, not a signal of implementation failure — this should be monitored and understood, not used to override the signal, per this project's own locked rule that regime labels are a diagnostic, never a new tunable trading gate, unless a SEPARATE, freshly pre-registered regime-conditional hypothesis is built and validated on its own (not authorized by this document).

## 6. Monitoring

- Track realized turnover and cost-per-trade against the backtest's assumed 0.01 point-size/spread economics — if realized costs run materially higher (wider live spreads than the historical spread column implies), the buffer width (Section 2) is the first thing to revisit, using realized data, not the backtest.
- Track realized Sharpe/breach-count against TF2's dev and OOS numbers on a rolling basis — this is the walk-forward check this project has already established as standard practice (see Walk-Forward 01 on FB1) and should be repeated here once enough live calendar time accumulates.

## 7. What this document does not do

Does not change or re-validate the underlying signal — that work is TF2's, already done, already disclosed as risk-reduction-only. Does not pick `risk_allocation_fraction` or `buffer_width`'s exact value beyond a disclosed starting point — both are deployment/business decisions or need real fill data this research phase doesn't have. Does not decide whether this becomes a third live system alongside the prop-firm trend system and GOAT-8 — that decision, and how it interacts with CAP1's still-open capital-allocation question, is yours to make.
