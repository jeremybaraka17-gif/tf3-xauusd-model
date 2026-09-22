# Model Spec — TF2: Multi-scale EWMAC drawdown-management overlay, XAUUSD / XAGUSD / NAS100, v1

Status: research-validated as a drawdown-management tool by this project's own standing breach-count metric, on all three instruments. **NOT validated as a return-enhancing or Sharpe-improving signal** — do not deploy or present it as one. Two single-window exceptions exist (noted in Section 5) and are explicitly not part of this spec's deployment claim.

## 1. What this is

A multi-scale trend-forecast position-sizing system, replacing a plain buy-and-hold (or an existing always-long) exposure with a variable, sign-aware, volatility-responsive position on the SAME instrument. It is not an overlay layered on top of another signal (unlike FD4/FD7/FD10) — it IS the position, standalone. Long AND short (two-sided), unlike this project's existing long-only trend constructions.

## 2. Construction (frozen, as tested — no parameter here was tuned after seeing results)

For each instrument independently:

1. **Six EWMAC pairs**, fast/slow spans in trading days: (2,8), (4,16), (8,32), (16,64), (32,128), (64,256).
2. **Per pair**: `raw = EWMA(close, fast) - EWMA(close, slow)`; `norm = raw / rolling_60d_std(close)`.
3. **Per-pair scalar** (computed once, on the dev window 2018-08-21 to 2025-04-02 only, frozen before any OOS data is touched): `scalar = 10 / mean(abs(norm on dev))`. This is a units-normalization constant matching Robert Carver's published calibration target (average absolute forecast of 10), not a performance-fit parameter.
4. `scaled_pair_forecast = clip(norm * scalar, -20, 20)`.
5. **Combined forecast** = simple average of the 6 scaled pair forecasts.
6. **Base position** = `clip(combined_forecast / 20, -1, 1)`.
7. **Acceleration multiplier**: `accel = combined_forecast.diff(10)`; `agree = sign(accel) * sign(combined_forecast)`; `size_mult = clip(1 + 0.5*agree, 0.5, 1.5)`.
8. **Volatility-spike cut**: if 21-day realized vol (annualized) exceeds 1.5x its own 252-day trailing average, that day's position is cut to 50%.
9. **Final position** = `base_position * size_mult * vol_cut_mult`, applied with a 1-day lag (signal computed on close, position taken the next day).

## 3. Per-instrument recommendation

- **XAUUSD**: deploy Stage 1 (steps 1-6 only, WITHOUT steps 7-8) or Stage 1+2 (full construction) — both clear the breach-count bar in both windows (Stage 1: dev 16 vs. BH 27, OOS 4 vs. 10; Stage 1+2: dev 14 vs. 27, OOS 6 vs. 10). Stage 1 alone is simpler and has the stronger single-window result (OOS Sharpe 0.945 vs. BH 0.862, the one case here that also improves risk-adjusted return, not just reduces drawdown) — recommended as the default unless the acceleration/vol-cut layer's dev improvement (16→14 breaches) is specifically wanted.
- **XAGUSD**: deploy Stage 1+2 (full construction) specifically, not Stage 1 alone — the vol-spike cut materially improves silver's already-strong breach reduction (dev 5→3, OOS holds at similar level) and, more importantly, is the version behind the standout OOS Sharpe (1.912) noted as an anomaly in Section 5, not a validated edge.
- **NAS100**: deploy Stage 1+2 ONLY. Stage 1 alone FAILS its own governing metric on this instrument (dev breach count 47 vs. BH's 31 — worse, not better, from fragmenting one long drawdown into many short ones). The vol-spike cut is not optional for NAS100; without it, this construction should not be deployed there at all.

## 4. What this achieves, stated honestly

Materially shallower, less frequent breaches of a -6% floor-breach-episode definition, on all three instruments, in both the dev and OOS windows, using the recommended per-instrument stage above. This is risk management, not alpha generation — the same category, and the same honest framing, as this project's other validated overlays (FD4 gold, FD7 silver/WTI, most of FD10). Expect this construction to underperform buy-and-hold on raw return and mostly on Sharpe too, especially during strong directional bull runs (as seen directly in dev for XAUUSD/NAS100 and OOS for NAS100) — that underperformance is the cost of the drawdown protection, not a flaw to be tuned away.

## 5. Disclosed anomalies — not part of the deployment claim

Two single-window results (XAUUSD Stage 1 OOS: Sharpe 0.945 vs. BH 0.862; XAGUSD Stage 1+2 OOS: Sharpe 1.912 vs. BH 0.813) show genuine risk-ADJUSTED outperformance, not just risk reduction. Both are single-window (neither replicates in the other window; XAGUSD's dev window for the identical construction is actually negative). These are noted for future walk-forward tracking, explicitly not cited as evidence this construction beats buy-and-hold in general.

## 6. Not yet done — required before any live deployment

- **Net-of-cost check**: gross-of-cost only so far. This construction trades far more often than a monthly-rebalanced signal (daily-updating continuous forecast) — transaction costs need checking before any of the breach-count PASSes above can be trusted net-of-cost, following this project's own FD4/FD7 precedent (FD7 initially looked uneconomic under a wrong point-size assumption and was only cleared after correcting it — the same diligence applies here).
- **Regime-conditioning diagnostic**: not yet run against this project's standard 5-axis gate (vol tercile, ADX, real-yield, dollar regime, risk-on/off) — mandatory on any result carried further, per this project's own locked methodology.
- **Live deployment target**: none of the three instruments currently has a confirmed live deployment slot in either of this project's two live systems (prop-firm FX/WTI trend system; GOAT-8 always-long ensemble) — this would be a THIRD, separate live construction if deployed, not a modification to either existing system, and that decision has not been made.
