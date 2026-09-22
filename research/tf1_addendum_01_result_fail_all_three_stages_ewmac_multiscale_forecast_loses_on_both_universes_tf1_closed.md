# TF1 Addendum 01 — Result: FAIL at every stage. The multi-scale EWMAC forecast construction (Carver-style trend framework) underperforms both benchmarks it was tested against, on both universes tried. TF1 is closed.

## Stage 1 — raw multi-scale EWMAC forecast, 16-symbol equity/index universe, vs. buy-and-hold-EW

**Result**: FAIL on the pre-registered primary condition. Dev Sharpe 0.452 vs. BH-EW 0.701; OOS Sharpe **-0.587** vs. BH-EW 0.905 — TF1 lost money on a risk-adjusted basis in OOS while the benchmark had its strongest window of the whole project (18.63% annualized). Not a marginal loss on either side.

This was NOT scored a clean fail, and Stage 2 was run anyway, for a specific, disclosed reason: TF1's secondary risk metrics were decisively better than the benchmark in both windows — MaxDD -8.53%/-7.73% (dev/OOS) vs. BH-EW's -41.52%/-18.92%, and breach episodes 14/5 vs. 35/9. A construction that controls risk dramatically better but simply doesn't capture enough of an unusually strong directional bull market is a different failure mode from one with no discernible edge on any metric (which is how EV1's TSMOM failed). That distinction is why Stage 2 was judged worth running rather than stopping here — stated plainly as a judgment call made in the moment, not a pre-committed rule.

## Stage 2 — + acceleration sizing + volatility-spike cut, same universe, vs. Stage 1

**Result**: FAIL. Dev Sharpe improved (0.452→0.596) but OOS got WORSE, not better (-0.587→-0.853, more negative). Breach count improved in OOS (5→2) but worsened in dev (14→17). The two mechanisms this hypothesis was actually built to test — acceleration-based sizing and the volatility-spike cut, i.e., the "exit based on volatility spikes" the user asked for at the start of this loop — did not produce a consistent improvement over the raw forecast. They helped in exactly the windows/metrics where the raw signal was already doing acceptably and hurt where it wasn't, which is the opposite of what a life-cycle-aware sizing overlay is supposed to do.

## Attempt 2 — same full construction (Stage 1 + Stage 2 combined), tested on GOAT-8's own universe (FX/commodity/index — the asset class Carver's framework was actually built for and published on), vs. the real live GOAT-8 system

This was the one permitted follow-up named in the pre-registration: not a re-tune of the signal, but a test of the construction on the universe it was designed for, since single-name equities are not what CTA trend systems like this were built to trade.

**Result**: FAIL, and more decisively than on the equity universe. TF1 posted **negative Sharpe in both windows** (-0.306 dev, -0.732 oos) against the real live GOAT-8 system's positive Sharpe in both (0.262 dev, 1.788 oos). TF1's own MaxDD was still shallower than live GOAT-8's in dev (-7.66% vs -8.01%) but that's the only metric where it wins — on OOS even the drawdown comparison narrows (-3.78% vs -2.12%, TF1 now worse), and the return/Sharpe comparison is not close in either window.

## TF1 is closed — all three stages tested, all three FAIL

Per the same two-attempt-then-stop discipline applied throughout this project: Stage 1 and Stage 2 together counted as the first full attempt (base construction, then its own built-in refinement), and the universe change was the one disclosed second attempt. Both failed. No further variation on this construction — different pair sets, different vol-normalization windows, different acceleration lookbacks — will be tested without a new, separately-justified reason, for the same reason EV2's grid search was capped at one follow-up point.

## Honest overall reading

The source material (a practitioner post, correctly flagged at pre-registration as promotional rather than citable, but grounded in Carver's real, published EWMAC-forecast framework) describes a construction with real academic and institutional pedigree — this is genuinely how AHL/Man-Group-style CTA trend systems are built. That pedigree did not translate into a result on this project's specific data. Two honest, separate possibilities, neither confirmed over the other: (1) the framework needs its full, real calibration (Carver's actual published pair-weighting and buffer-zone position-inertia logic, both simplified or omitted here for tractability) to work as intended, and this test built a simplified, undercalibrated version of it; or (2) the framework's edge, like TSMOM's, depends on breadth this project's universe (8-16 instruments) doesn't provide — the same structural explanation that closed TSMOM. This addendum does not pick between them; picking one without further evidence would be exactly the kind of after-the-fact story-fitting this project's discipline exists to prevent. What's certain is that the specific, disclosed construction tested here — as built, on both universes tried — does not beat its benchmark.
