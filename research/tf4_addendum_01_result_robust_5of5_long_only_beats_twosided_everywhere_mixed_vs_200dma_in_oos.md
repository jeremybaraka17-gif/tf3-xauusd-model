# TF4 Addendum 01 — Result: long-only beats two-sided at 5/5 locked vol-normalization windows. PASS (robust). One honest nuance vs. the 200d-MA benchmark, not glossed over.

## Headline result

Long-only beats two-sided TF3 on net Sharpe, in BOTH dev and OOS, at **all 5** of the locked candidate vol-normalization windows (30, 45, 60, 90, 120 days) — not just the one window (60) already used throughout this project. Per Section 4's locked thresholds, this is a **PASS (robust)** verdict: the long-only advantage found in Addendum 05 is a genuine property of removing shorts, not a coincidence of one specific window choice.

| VOL_WINDOW | Dev: long-only Sharpe | Dev: two-sided Sharpe | OOS: long-only Sharpe | OOS: two-sided Sharpe | Beats two-sided, both windows |
|---|---|---|---|---|---|
| 30 | 0.686 | 0.480 | 0.841 | 0.784 | Yes |
| 45 | 0.684 | 0.447 | 0.942 | 0.905 | Yes |
| 60 (original) | 0.709 | 0.500 | 1.061 | 1.000 | Yes |
| 90 | 0.682 | 0.441 | 1.012 | 0.963 | Yes |
| 120 | 0.663 | 0.458 | 0.959 | 0.877 | Yes |

## The honest nuance: robust vs. two-sided, mixed vs. the 200-day MA

This hypothesis only tested long-only against two-sided (Section 4's locked bar). Checking the same sweep against the 200d-MA benchmark (already computed in the same run, reported here for completeness, NOT a retroactive change to what PASS/FAIL means for this hypothesis):

- **Dev**: long-only beats the 200d-MA (Sharpe 0.658) at **all 5** windows (0.663-0.709).
- **OOS**: long-only beats the 200d-MA (Sharpe 1.002) at only **2 of 5** windows — 60 (1.061) and 90 (1.012). The other three (30: 0.841, 45: 0.942, 120: 0.959) fall short of the 200d-MA in OOS.

Read plainly: dropping shorts is a robust, well-evidenced improvement over the two-sided construction — that conclusion should be trusted. Whether the resulting long-only construction is ALSO better than a plain 200-day MA is a separate, weaker claim, true at the specific window this project has used throughout (60) but not guaranteed at nearby windows. This is exactly the kind of distinction a robustness check is supposed to surface, not paper over — reporting only the 60-day OOS number (1.061 > 1.002) without this table would overstate how settled the "beats the 200d-MA" question actually is.

## What this changes going forward

Given the user's explicit direction to drop shorting, TF3's construction is revised to long-only (`clip(combined_forecast/20, 0, 1)` instead of `clip(..., -1, 1)`), keeping `VOL_WINDOW=60` — the original, already-used value, not re-picked from this sweep to chase the best-looking number (that would be exactly the curve-fitting this hypothesis was designed to rule out; 60 was already locked before this sweep ran). All downstream files (backtest, live scripts, figures) are updated to match. See `tf3_addendum_06_revision_to_long_only.md` for the concrete before/after numbers on the actual shipped construction.

## What this does NOT do

Does not sweep or re-tune VOL_WINDOW itself as a live choice — 60 remains the deployed value; the sweep's job was to confirm robustness, not to select a new "best" window (which would reintroduce the same curve-fitting risk this hypothesis exists to check for). Does not re-test the EWMAC pair spans, buffer width, or cost assumptions — per Section 5's locked exclusions, unchanged.
