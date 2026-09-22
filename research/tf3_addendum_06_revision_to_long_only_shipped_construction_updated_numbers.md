# TF3 Addendum 06 — Revision applied: TF3 is now long-only. Updated numbers for the actual shipped construction.

## What changed

Per the user's direction and Addendum 05's finding (shorting destroys value on every metric, both windows) confirmed robust across 5 vol-normalization windows (TF4/Addendum 01), TF3's construction is revised: `raw_position = clip(combined_forecast/20, 0, 1)` instead of `clip(..., -1, 1)`. `VOL_WINDOW` stays at 60 — the original, already-locked value, not re-picked from the robustness sweep to chase a better number. All files in this package (`backtest/tf3_xauusd_backtest.py`, `backtest/tf3_vs_200dma_comparison.py`, `backtest/tf3_trade_metrics.py`, `backtest/prop_challenge_montecarlo.py`, `live/tf3_xauusd_live.py`, `live/tf3_challenge_live.py`) now reflect this, each with an inline comment pointing back to this addendum — not a silent edit.

## Updated headline numbers (long-only, buffered, net of cost)

| Window | Sharpe | Breach episodes | Ann. return | Max DD |
|---|---|---|---|---|
| dev | 0.709 (was 0.500) | 5 (was 9) | 4.56% (was 3.41%) | -12.74% (was -17.26%) |
| oos | 1.061 (was 1.000) | 5 (was 5, tied) | 16.99% (was 16.37%) | -12.67% (was -13.55%) |

Every figure improves or ties versus the original two-sided construction, in both windows — consistent with Addendum 05's finding, now the actual shipped number rather than a side comparison.

## Updated vs. 200-day MA (the comparison from `tf3_vs_200dma_result.md`, now with the revised construction)

| Window | TF3 (long-only) Sharpe | 200d-MA Sharpe |
|---|---|---|
| dev | **0.709** | 0.658 |
| oos | **1.061** | 1.002 |

TF3 now beats the 200d-MA on Sharpe in BOTH windows (it previously lost in dev and tied in OOS as the two-sided version). This is a real improvement, not just a smaller loss — but TF4's own robustness sweep (Addendum 01) already disclosed that this specific win over the 200d-MA in OOS only holds at 2 of the 5 tested vol-normalization windows (60 and 90) — read that qualifier as still standing, not superseded by this table.

## Updated trade-level metrics (long-only)

| Window | Trades | Win rate | Avg win | Avg loss | EV/trade | Payoff ratio |
|---|---|---|---|---|---|---|
| dev | 453 (was 615) | 50.6% (was 47.2%) | +0.512% | -0.387% | +0.067% (was +0.037%) | 1.32 |
| oos | 98 (was 112) | 54.1% (was 51.8%) | +1.229% | -0.963% | +0.222% (was +0.187%) | 1.28 |

Fewer trades (removing the short side removes short trades entirely), higher win rate in both windows, higher EV/trade in both windows.

## Updated prop-challenge Monte Carlo (supersedes `tf3_addendum_03...md`'s two-sided numbers)

Same method (block bootstrap, 21-day blocks, 3,000 sims, 180-day horizon), same challenge rules, now bootstrapping the long-only net-return series (pooled dev+OOS: mean +0.0260%/day, std 0.549%/day, both slightly better than the two-sided series's +0.0218%/+0.571%).

| Challenge | Best pass rate (old, two-sided) | Best pass rate (new, long-only) | At exposure_mult |
|---|---|---|---|
| $5k 2-Step | 36.9% | **38.1%** | ~2-3 |
| $10k 1-Step | 43.1% | **46.2%** | ~2 |

A real but modest improvement — still below 50% at every exposure level tested, same qualitative conclusion as before: a real attempt at either challenge, even at the best exposure level found, is still expected to fail more often than pass. The lot-rounding problem from `tf3_addendum_04...md` is UNCHANGED by this revision (it's driven by position magnitude and contract size, not by direction) and still applies at essentially the same severity.

## What this does NOT do

Does not re-run the regime-conditioning diagnostic (`tf2_addendum_02...md`) for the long-only construction — that was computed on the original two-sided TF2 Stage 1 signal; whether the same real-yield mechanism concentration holds for the long-only version is untested, a real gap disclosed here rather than assumed to carry over. Does not update `model_spec_tf3_xauusd_deployment_architecture_v1.md`'s prose sections in place — that document is left as the historical record of the original two-sided spec; this addendum is the disclosed revision on top of it, the same pattern this project has used for every other addendum.
