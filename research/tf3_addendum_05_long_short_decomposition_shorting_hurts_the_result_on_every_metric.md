# TF3 Addendum 05 — Long/short decomposition: the short side is a net drag, on every metric, in both windows. Not a minor caveat.

## What was tested

Two things, both requested directly: (1) how much of TF3's return comes from its long days vs. its short days, and (2) a genuine same-signal comparison — the identical EWMAC construction with shorts zeroed out (`clip(0,1)` instead of `clip(-1,1)`, same buffer, same cost model, nothing else changed) — against the two-sided version actually shipped in this package.

## Long/short return decomposition (net of cost)

| Window | Long days | Short days | Flat days | Long contribution | Short contribution |
|---|---|---|---|---|---|
| dev | 1,227 (72.8%) | 399 (23.7%) | 60 (3.6%) | +30.54% | **-7.73%** |
| oos | 283 (87.6%) | 40 (12.4%) | 0 (0%) | +21.95% | **-0.96%** |

The short side loses money outright in both windows (Sharpe on the short-only subset: -0.507 dev, -0.221 OOS). It is not a smaller positive contributor — it is negative.

## TF3 two-sided vs. the identical signal, long-only

| Window | Construction | Net Sharpe | Net ann. return | Net max DD | Breach episodes |
|---|---|---|---|---|---|
| dev | TF3 two-sided (shipped) | 0.500 | 3.41% | -17.26% | 9 |
| dev | **Same signal, long-only** | **0.709** | **4.56%** | **-12.74%** | **5** |
| oos | TF3 two-sided (shipped) | 1.000 | 16.37% | -13.55% | 5 |
| oos | **Same signal, long-only** | **1.061** | **16.99%** | **-12.67%** | **5 (tied)** |

## Read plainly, without softening it

The long-only variant of the EXACT SAME signal beats the shipped two-sided TF3 construction on every single metric checked, in both windows: higher Sharpe, higher annualized return, shallower max drawdown, and fewer-or-equal floor breaches. This is not a marginal or single-window result — it holds in dev and OOS simultaneously, on every axis. Shorting XAUUSD, as this construction currently does it, actively destroys value rather than adding diversification or extra return. This directly echoes what the project's own `prop_firm_survival_guide_final.md.pdf` argues qualitatively ("Trend follow. Stop shorting. Stay long" — bear markets don't last as long as bull markets, so a long-only trend filter has structurally more to work with) — here it's confirmed quantitatively, on this exact instrument and this exact signal, not assumed from the guide's own prior.

## What this means for the package as shipped

TF3, as specified in `model_spec_tf3_xauusd_deployment_architecture_v1.md`, is a two-sided construction — that was never revisited after this finding, since the finding is new as of this addendum, not something the original spec should have caught. Read together, this addendum is a clear, disclosed argument for reconsidering that choice: a long-only version of the same signal is a straightforwardly better construction on every metric measured, not a trade-off between different desirable properties. This is stated as a finding for you to act on, not implemented as a silent change to the shipped construction — changing TF3's own spec to long-only would be a real, disclosed revision worth its own addendum, not something folded in here without being named as a change.

## What this does NOT do

Does not change `model_spec_tf3_xauusd_deployment_architecture_v1.md` or any packaged live script — those still ship the two-sided construction, as originally specified, pending an explicit decision on whether to revise it. Does not re-run the Monte Carlo prop-challenge simulation (`tf3_addendum_03...md`) with the long-only variant — that used the two-sided net-return series as its bootstrap source; a long-only re-run would very plausibly show a materially different (likely better, based on the return-level improvement above) pass-rate curve, but that is a fresh run, not assumed here from the daily-return comparison alone.
