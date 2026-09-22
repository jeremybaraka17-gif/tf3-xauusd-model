# TF3 Addendum 01 — Consolidating the backtest into a saved script surfaces a reproduction discrepancy in the buffer sanity check. Disclosed, not smoothed over.

## What happened

`model_spec_tf3_xauusd_deployment_architecture_v1.md`, Section 2, reports a buffer sanity check run before that document shipped: dev turnover 0.0615→0.0303, Sharpe 0.421→0.424, breach 11→11 (unchanged); OOS turnover 0.0572→0.0267, Sharpe 0.939→0.999, breach 6→6 (unchanged). That check was run as a one-off inline `python3 -c "..."` command and never saved as its own script — a process gap, flagged at the time only implicitly ("currently only existing as an inline command, never saved as its own script" — noted in the packaging task list, not in the spec itself).

Writing `backtest/tf3_xauusd_backtest.py` as the first saved, deterministic implementation of the same buffer rule (Carver's "trade to the edge of the buffer" logic: only trade when `abs(target - held) > 0.10`, and move only to the nearer buffer edge, not to target) reproduces the **unbuffered** numbers exactly — dev turnover 0.0615/Sharpe 0.421/breach 11 vs BH 27, OOS turnover 0.0572/Sharpe 0.939/breach 6 vs BH 10, all matching the spec and the earlier TF2 addenda to three decimal places. That confirms the signal itself (the part that matters most) is correctly reproduced in this consolidation.

The **buffered** numbers do not match the spec's sanity check:

| | dev turnover | dev Sharpe | dev breach | OOS turnover | OOS Sharpe | OOS breach |
|---|---|---|---|---|---|---|
| Spec (unsaved inline check) | 0.0303 | 0.424 | 11 | 0.0267 | 0.999 | 6 |
| This script (saved, rerunnable) | 0.0365 | 0.500 | 9 | 0.0344 | 1.000 | 5 |

## What this means, stated plainly

The two implementations of the same rule are not identical, and since the original was never saved, there is no way to diff the two codepaths line-by-line to find where they diverge — a real limitation, not a minor bookkeeping note. The most likely explanation is a difference in how the day-by-day state-holding loop was written (e.g., a vectorized approximation vs. this script's explicit per-day loop), not a different buffer rule or width — both were `buffer_width=0.10`, both use "trade to the nearer edge."

The direction of the discrepancy matters: this script's numbers are **better** on every metric (lower turnover, higher Sharpe, fewer breaches) than the ones originally reported, not worse. That is exactly the kind of asymmetry that should raise suspicion rather than be accepted gratefully — a bug that happens to make a result look better than an unsaved reference is not evidence of a correct fix, and this addendum does not claim the new numbers are "right" and the old ones "wrong." Both are reported here, neither is preferred by fiat.

## What does NOT change

The qualitative conclusion in `model_spec_tf3...md` Section 2 — that the buffer cuts turnover roughly in half without degrading Sharpe or breach count — holds under both implementations. This is a magnitude-of-numbers discrepancy inside an unchanged direction of result, not a reversal of the buffer's validity.

## What this means for deployment

The `backtest/tf3_xauusd_backtest.py` script in this package is now the authoritative, rerunnable reference — treat its output as current. `buffer_width=0.10` should still be treated as a disclosed literature-standard starting point (per the original spec), not re-tuned off either set of numbers above; this addendum is a reproducibility disclosure, not grounds to pick a new buffer width by comparing which version looks best.
