# TF3 XAUUSD vs. 200-day-MA long-only — head-to-head, net of cost

## What this compares

Not a naive "buy and hold" line — a 200-day-MA long-only signal (long when close > SMA200, flat otherwise, no shorting), the exact signal CLASS your live GFT prop-firm trend system runs (`p4_signal_workflow.py`: `MA_WINDOW = 200`, long-only). This construction does not replicate that system's ATR-stop exit or cushion sizing — it is the same plain MA-flip simplification CAP1 already used and disclosed, chosen to isolate what the EWMAC forecast does differently from a plain trend-MA flip on the SAME instrument (XAUUSD), not a comparison against your fully-engineered live system.

Both constructions use the same spread-cost assumption (point_size=0.01, TF2/TF3's own inferred value, reused unchanged).

## Results

| Window | Construction | Net Sharpe | Net Sortino | Net win rate | Net ann. return | Net max DD | Breach episodes (-6%) |
|---|---|---|---|---|---|---|---|
| dev | TF3 (buffered EWMAC) | 0.500 | 0.564 | 50.9% | 3.41% | -17.26% | 9 |
| dev | 200d-MA long-only | 0.658 | 0.705 | 53.2% | 8.16% | -29.68% | 23 |
| oos | TF3 (buffered EWMAC) | 1.000 | 1.060 | 52.9% | 16.37% | -13.55% | 5 |
| oos | 200d-MA long-only | 1.002 | 1.208 | 54.9% | 25.14% | -21.75% | 10 |

## Read plainly

The 200-day MA beats TF3 on Sharpe in the dev window (0.658 vs. 0.500) and is essentially tied in OOS (1.002 vs. 1.000) — TF3 does NOT beat this benchmark on risk-adjusted return, in either window. On raw annualized return the gap is larger: the 200d-MA more than doubles TF3's dev return (8.16% vs. 3.41%) and meaningfully beats it in OOS (25.14% vs. 16.37%). Win rate is close in both windows (roughly a 2-3 point edge to the 200d-MA), not a meaningful differentiator either way.

Where TF3 wins, and wins clearly, is drawdown control: fewer than half the floor-breach episodes in both windows (9 vs. 23 dev, 5 vs. 10 OOS) and a shallower max drawdown in both windows (-17.3% vs. -29.7% dev, -13.5% vs. -21.7% OOS). This is the exact same story TF2's original validation told (a drawdown-management tool, not a return- or Sharpe-improving one) — this head-to-head against a real, project-relevant benchmark (rather than generic buy-and-hold) confirms it again, does not contradict it, and should not be read as a new, better result just because the benchmark changed. If the choice is between raw return/Sharpe and drawdown control on the same instrument, the 200d-MA construction is the higher-return, higher-drawdown option and TF3 is the lower-return, lower-drawdown option — a genuine trade-off, not a case where one dominates the other on every axis.

## What this does NOT do

Does not compare TF3 against your ACTUAL live prop-firm system (which adds an ATR-based Chandelier stop and cushion-proportional sizing on top of the plain MA signal) — that would require rebuilding this comparison with the real stop/sizing logic, not done here. Does not re-derive or change TF3's own construction, buffer, or point-size assumptions. Does not imply the 200d-MA construction is itself deployable as shown here — it is a simplified proxy, same caveat CAP1 already disclosed for this exact construction.
