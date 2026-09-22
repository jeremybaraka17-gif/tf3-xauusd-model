# TF2 Addendum 01 — Result: the multi-scale EWMAC framework is a real, decisive drawdown-reduction tool on all three instruments (XAUUSD, XAGUSD, NAS100) by this project's own standing breach-count metric — it is NOT a Sharpe-improving return signal on any of them, and on XAGUSD's dev window it costs real absolute return. Two honest standout exceptions are flagged, not oversold.

## Two different, both-legitimate lenses give different verdicts — reporting both, not picking the one that looks better

This project has always scored results two ways: the primary Sharpe-vs-benchmark condition (used throughout EV1-EV3, TF1), and the floor-breach-episode-count condition (this project's actual standing de-risk metric, the one FB1/FD4/FD7/FD10 were validated on, chosen specifically because it survives construction changes that flip Sharpe/MaxDD signs). TF2's results split cleanly along exactly that line, and reporting only one lens would misrepresent what was found.

## Sharpe-primary verdict (strict, matching EV1/TF1's own rule)

| Instrument | Stage 1 vs BH | Stage 1+2 vs BH |
|---|---|---|
| XAUUSD | PARTIAL (dev fails 0.443 vs 1.000; OOS wins 0.945 vs 0.862) | PARTIAL (dev fails; OOS fails 0.583 vs 0.862) |
| XAGUSD | FAIL (dev negative: -0.145, ann. -2.14%) | FAIL (dev negative: -0.125, ann. -2.16%) |
| NAS100 | PARTIAL (both positive, both lose to BH) | FAIL (OOS negative: -0.050) |

None of these are a clean PASS. XAUUSD's dev and NAS100's dev/OOS numbers are being compared against buy-and-hold benchmarks having exceptional runs (gold dev Sharpe 1.000/14.38% ann., NAS100 OOS Sharpe 1.521/34.84% ann.) — a risk-controlled, often-flat-or-short construction was never going to out-Sharpe a benchmark riding one of its best multi-year stretches, and it mostly didn't.

## Breach-count verdict (this project's standing de-risk metric)

| Instrument | Stage 1 | Stage 1+2 |
|---|---|---|
| XAUUSD | PASS (dev 16<27, OOS 4<10) | PASS (dev 14<27, OOS 6<10) |
| XAGUSD | PASS (dev 5<18, OOS 5<9) | PASS (dev 3<18, OOS 6<9) |
| NAS100 | **FAIL dev (47>31 — fragmentation)** | PASS (dev 25<31, OOS 4<11) |

By this metric, the framework passes on **every instrument** with the acceleration+vol-spike layer included (Stage 1+2), and on two of three (XAUUSD, XAGUSD) even without it. NAS100's Stage-1-alone failure is itself informative and consistent with a pattern already documented elsewhere in this project (FD1, FD9, EV2-Stage2): a raw continuous trend signal without the vol-spike cut can fragment one long drawdown into several shorter ones that each independently breach the floor, inflating episode count even while shrinking MaxDD (NAS100 Stage 1's MaxDD is -10.51% vs. BH's -39.02% — much shallower, but split into 47 separate breach episodes instead of BH's 31). Adding the vol-spike cut (Stage 1+2) fixes exactly this on NAS100 (47→25 episodes) — the mechanism doing precisely what it was designed to do, on this instrument specifically.

## Two standout results, flagged honestly as anomalies rather than overclaimed

- **XAUUSD, Stage 1, OOS**: beats buy-and-hold on BOTH Sharpe (0.945 vs 0.862) AND MaxDD (-15.03% vs -27.90%) AND breach count (4 vs 10) simultaneously — the rare case (matching FD10-NAS100's earlier precedent as "the only overlay that improves Sharpe net of cost") of genuine risk-adjusted-return improvement, not just risk reduction. Not replicated in dev (dev Stage 1 loses on Sharpe), so this is one strong window, not a confirmed edge across both.
- **XAGUSD, Stage 1+2, OOS**: Sharpe 1.912 vs. BH's 0.813, more than double, with MaxDD -23.49% vs. -58.39% — the single best number anywhere in the TF family. Reported with the necessary caveat attached directly: XAGUSD's DEV window for the same construction is negative (-0.125 Sharpe, -2.16% annualized) — an OOS result this strong sitting on top of a negative dev result is exactly the shape a small-sample, favorable-window artifact produces, not confirmed evidence of a real edge. This is disclosed as an anomaly to note and watch, explicitly not as grounds for deployment confidence.

## What "developed" means honestly, given this evidence

The framework, as built (unchanged from TF1 — no per-instrument re-tuning was done to produce these numbers), is a genuine, consistent, deployable **drawdown-management tool** on gold, silver, and NAS100 — the same category of result as this project's actual majority of validated PASSes (FB1, FD4, FD7, most of FD10) — not a new return-generating signal. Framed and specced as that, honestly, a model spec is warranted for XAUUSD and XAGUSD Stage 1(+2) and NAS100 Stage 1+2 specifically (not NAS100 Stage 1 alone, which fails its own governing metric). Framed as anything more than risk reduction — as a way to beat buy-and-hold returns — the evidence does not support that claim except in the two flagged single-window anomalies, which are noted, not built into the spec's headline claim.
