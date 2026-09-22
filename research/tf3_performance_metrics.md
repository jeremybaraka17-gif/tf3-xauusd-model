# TF3 XAUUSD — performance metrics (win rate, Sharpe, Sortino, expected value), net of cost

Two views, because they answer different questions: daily-return metrics (how the equity curve behaves day to day) and trade-level metrics (how the system does each time it actually holds a position). Both computed from the buffered TF3 construction, net of the same spread-cost assumption used throughout (point_size=0.01).

## Daily-return metrics

| Window | Sharpe | Sortino | Daily win rate | Ann. return | Max DD | EV/day (bps) |
|---|---|---|---|---|---|---|
| dev | 0.500 | 0.564 | 50.9% | 3.41% | -17.26% | 1.35 |
| oos | 1.000 | 1.060 | 52.9% | 16.37% | -13.55% | 6.50 |

Sortino (downside-deviation-based) is higher than Sharpe in both windows, meaning the return distribution's downside is somewhat less punishing relative to its upside than a symmetric-vol measure like Sharpe implies — consistent with this being a drawdown-management construction rather than one with fat negative tails. Daily win rate sits close to a coin flip in both windows (50.9%/52.9%) — this is expected and not a weakness by itself: a trend system's edge comes from asymmetric payoff (bigger wins than losses), not from being right more than half the time, and the trade-level table below is the more informative one for that question.

## Trade-level metrics (a "trade" = one continuous holding period at a fixed buffered position)

| Window | Trades | Win rate | Avg win | Avg loss | EV/trade | Payoff ratio | Avg days held |
|---|---|---|---|---|---|---|---|
| dev | 615 | 47.2% | +0.458% | -0.339% | +0.037% | 1.35 | 2.6 |
| oos | 112 | 51.8% | +1.219% | -0.921% | +0.187% | 1.32 | 2.9 |

Read plainly: this is a sub-50%-win-rate system in dev (47.2%) that is still net-positive in expected value per trade (+0.037%), because the payoff ratio (average win roughly 1.3-1.35x the average loss) more than compensates. This is the textbook trend-following shape — lose slightly more often than you win, but win bigger when you do — not an anomaly to explain away. OOS win rate crosses 50% (51.8%) with a similar payoff ratio, giving a meaningfully higher EV/trade (+0.187% vs. +0.037%), consistent with OOS's stronger overall Sharpe already reported elsewhere in this package. Average holding period is short (2.6-2.9 days) — a consequence of the fastest EWMAC pair (2/8-day spans) still updating daily even with the position-inertia buffer in place; the buffer roughly halves turnover (see `research/tf3_addendum_01...md`) but does not turn this into a long-holding-period system.

## What this does NOT do

Does not annualize the trade-level EV into an implied return figure — trade count and holding period vary too much between dev (615 trades, ~4.4/week) and OOS (112 trades, ~1.8/week) for that conversion to be meaningful without accounting for compounding and overlap, and the daily-return table above already gives the honest annualized figure directly from the actual return series. Does not treat the OOS trade-level numbers (112 trades) as equally reliable as dev's (615 trades) — a smaller sample is a wider-uncertainty estimate, stated plainly rather than presented with false precision.
