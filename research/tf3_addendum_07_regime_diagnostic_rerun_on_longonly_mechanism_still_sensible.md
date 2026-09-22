# TF3 Addendum 07 — Regime-conditioning diagnostic re-run on the actual shipped (long-only) construction. Result: the same mechanism still holds; walk-forward on fresh data is BLOCKED on data.

## Two items requested, one executed, one honestly blocked

**Walk-forward re-validation on fresh data: BLOCKED, not run.** Checked before doing anything else: `xauusd_D1.csv`, `macro_raw.csv`, and `us500_D1.csv` all end at 2026-07-03 — the exact date this project's own `OOS_END` already uses. There is no unseen data sitting in this session to walk forward onto. Re-slicing the same OOS window and calling it a walk-forward would not be a real out-of-sample check; it would just be relabeling data the construction has already been evaluated against. This item stays open until fresher data is available — not faked here.

**Regime-conditioning diagnostic, re-run on the long-only construction: DONE.** TF2's original diagnostic (`tf2_addendum_02...md`) was computed on the two-sided signal, before Addendum 05/06's revision. This project's own locked methodology (`methodology_regime_conditioning_gate.md`) treats this as mandatory on any PASS — it had never actually been run on what's shipping now. Same 5 locked axes, same thresholds, reused verbatim, dev window, net-of-cost Sharpe per bucket.

## Result

| Axis | Bucket | Net Sharpe (dev) | n days |
|---|---|---|---|
| Vol regime | Low | **2.540** | 351 |
| | Normal | 0.884 | 654 |
| | High | **-0.583** | 422 |
| Trend regime (ADX) | Range-bound | 0.297 | 585 |
| | Transitional | 1.146 | 287 |
| | Trending | 0.841 | 788 |
| Real-yield regime | Falling | **1.230** | 709 |
| | Flat | 1.075 | 288 |
| | Rising | **-0.300** | 681 |
| Dollar regime | Weakening | 1.013 | 561 |
| | Flat | 1.611 | 300 |
| | Strengthening | 0.121 | 817 |
| Risk-on/off | Risk-On | 0.772 | 1165 |
| | Risk-Off | 0.553 | 521 |

## Read plainly

The mechanism is still sensible, and in the same direction as the original two-sided version's diagnostic (`tf2_addendum_02...md`): Low-vol beats High-vol decisively (2.540 vs. -0.583), Falling real-yield beats Rising real-yield decisively (1.230 vs. -0.300) — this is the same Erb & Harvey "Golden Dilemma" concentration the original construction showed, and removing shorts did not break it or reveal it as an artifact of the two-sided version. Dollar regime also behaves in the expected direction (Strengthening dollar is the weakest bucket, 0.121, though now positive rather than the original's -0.22 — an improvement in magnitude, not a reversal in direction). Trend regime (ADX) shows a mild, not fully monotonic wrinkle — Transitional (1.146) slightly outperforms Trending (0.841), rather than Trending being cleanest — a minor, disclosed oddity, nowhere near the severity of NAS100's outright inversion in the TF2 family, and not treated as a red flag on its own.

**This diagnostic remains what this project's methodology says it always is: informative context, never a pass/fail gate and never a live trading filter on its own.** It does not change TF3's verdict, and does not authorize adding a regime-based entry/exit condition without that being its own separately pre-registered hypothesis.

## What this does NOT do

Does not run the OOS window's regime split (per this project's own locked convention, the diagnostic is dev-window only, to avoid any risk of the regime characterization itself being shaped by looking at OOS). Does not resolve the walk-forward gap — that stays open, honestly, until this session (or a future one) has access to data past 2026-07-03.
