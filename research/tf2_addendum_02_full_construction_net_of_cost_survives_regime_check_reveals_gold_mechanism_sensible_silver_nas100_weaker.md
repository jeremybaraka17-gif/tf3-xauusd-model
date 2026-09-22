# TF2 Addendum 02 — Full construction complete: net-of-cost check and regime-conditioning diagnostic, per the model spec's own stated requirements before deployment consideration.

## Net-of-cost breach-count verdict: PASS survives on all three, but real turnover costs matter and are disclosed, not absorbed silently

Point sizes: XAUUSD 0.01 (inferred fresh here the same way FD7/FD10 inferred theirs — median nonzero spread-column value of 15 at point_size 0.01 implies a $0.15 spread on a ~$1880 gold price, 0.008% of price, matching realistic retail CFD gold spreads; 0.1 would imply an implausible $1.50/0.08%). XAGUSD 0.001, NAS100 0.1 — both already established in this project (FD7 Addendum 03, FD10 Addendum 03), reused unchanged.

| Instrument | Stage | Dev breach (net) | OOS breach (net) | Net verdict |
|---|---|---|---|---|
| XAUUSD | Stage 1 | 11 vs BH 27 | 6 vs BH 10 | PASS |
| XAGUSD | Stage 1+2 | 7 vs BH 18 | 7 vs BH 9 | PASS |
| NAS100 | Stage 1+2 | 25 vs BH 31 | 2 vs BH 11 | PASS |

The core drawdown-management claim holds net-of-cost on all three, both windows.

**But the cost drag is real and uneven, and changes the economic picture for two of the three:**
- **XAUUSD**: small drag (dev 0.15%/yr, OOS 0.11%/yr) — Stage 1's lower turnover (avg daily |position change| ~0.06) keeps costs trivial, and the Sharpe numbers barely move (dev 0.443→0.421, OOS 0.945→0.939).
- **XAGUSD**: real drag (dev 2.80%/yr, OOS 2.06%/yr) from much higher turnover (~0.10-0.11 avg daily change, since Stage 1+2's acceleration multiplier and vol-cut both add position churn on top of the base signal). Dev, already negative gross (-2.16% ann.), becomes MORE negative net (-4.96% ann.) — the already-weak dev result gets materially worse once realistic costs are included, not just marginally worse.
- **NAS100**: real drag (dev 2.21%/yr, OOS 1.92%/yr), same turnover-from-Stage-2 mechanism. Dev Sharpe nearly halves net-of-cost (0.366→0.168). OOS, already weak gross (-0.050), goes more negative net (-0.232).

Read plainly: the drawdown-reduction claim is genuine and survives costs. The idea that XAGUSD or NAS100 might ALSO be attractive on raw return terms — never a strong claim to begin with — is weaker net-of-cost than it looked gross-of-cost. XAUUSD remains the strongest instrument in this family on every axis checked so far.

## Regime-conditioning diagnostic (mandatory per this project's locked methodology, dev window, net-of-cost Sharpe per bucket)

**XAUUSD** — the edge concentrates exactly where gold's known macro mechanism predicts it should: Low-vol regime (Sharpe 1.96) vs. High-vol (-1.08); Falling real-yield (1.05) vs. Rising real-yield (-0.35). This is the textbook Erb & Harvey "Golden Dilemma" real-yield relationship showing up directly in a regime split that was locked BEFORE this hypothesis existed (the methodology's five axes were fixed in a prior, unrelated session) — a mechanistically sensible concentration, not an unexplained one. Dollar regime also behaves sensibly (Strengthening -0.22, the expected drag on a dollar-denominated asset). This is the strongest, most interpretable result in the whole TF family.

**XAGUSD** — broadly weak across almost every bucket (Low vol -0.22, Normal -0.11, High -0.58; Rising real-yield -0.84; Strengthening dollar -0.55), consistent with dev's poor overall net result. The only positive buckets are Trending regime (0.25) and Falling real-yield (0.28) — real but modest, not enough to offset the broader weakness. No regime bucket rescues XAGUSD's dev performance.

**NAS100** — a genuine oddity, disclosed rather than explained away: the construction performs WORST during the Trending ADX regime (-0.39) and best during Transitional (1.68) and Low-vol (0.98). A trend-following construction underperforming specifically when ADX says the market IS trending is counterintuitive and not mechanistically obvious. Two honest possibilities, neither confirmed: the acceleration/vol-cut layer (Stage 2, required for NAS100 per the model spec) may be cutting exposure precisely as NAS100's genuine trending moves develop (the vol-spike cut firing on strong trending rallies, not just crash-type spikes); or ADX-defined "Trending" doesn't align well with this multi-scale forecast's own definition of trend strength. Not resolved here — flagged as a real, unexplained wrinkle in this instrument's result.

## Updated recommendation

XAUUSD is the one instrument in this family with a clean, low-cost, mechanistically-explained result at every check performed so far (breach-count PASS gross AND net, small cost drag, sensible regime concentration). XAGUSD and NAS100 both still clear the core drawdown-management bar net-of-cost, but with real, non-trivial cost drag and (for NAS100) an unexplained regime pattern — both are usable as risk-management tools on the evidence gathered, with less confidence than XAUUSD, and neither should be described as return-generating on any version of this evidence, gross or net.
