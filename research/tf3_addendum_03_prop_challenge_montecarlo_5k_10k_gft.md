# TF3 Addendum 03 — Prop-challenge Monte Carlo: pass-rate sweep for GFT $5k 2-Step and $10k 1-Step, following the survival guide's own Rule 3 methodology

## Confirmed inputs (from the user, this session) vs. assumed

| | $5k 2-Step | $10k 1-Step |
|---|---|---|
| Profit target | Step 1: 8%, Step 2: 6% (user flagged 6% vs. 5% as a variant question — 6% used here) | 10% |
| Max total loss | 10% static, floor at 90% of initial balance | 6% static (matches `risk_governor.py`'s already-confirmed figure) |
| Max daily loss | 4-5% range given, tighter 4% used (same "default to the tighter limit" convention `risk_governor.py` already used for this account's own ambiguous daily-limit date-range) | 3% (matches `risk_governor.py`) |
| Min trading days | 3 per phase | 3 |

The $10k figures match this project's own already-confirmed `risk_governor.py` constants exactly — the strongest-grounded of the two challenges simulated here. The $5k figures are as given by the user, with the Step 2 target (6% vs. 5%) and the exact daily-loss basis left as open variant questions, not resolved by assumption.

**NOT confirmed, and swept rather than assumed: GFT's real leverage on XAUUSD.** `instrument_specs.py` (imported by the existing live prop-firm system) almost certainly has this as a `LEVERAGE_GFT` entry, but that file wasn't retrievable from this project's docs this session. Rather than invent a number, this simulation sweeps `EFFECTIVE_EXPOSURE_MULT` — the product of `risk_allocation_fraction × actual leverage`, i.e. the total multiple of account equity deployed as notional exposure at `target_position = ±1` — across a range, and reports the full sensitivity. Once GFT's real leverage for gold is confirmed, divide whichever `EFFECTIVE_EXPOSURE_MULT` looks best below by that number to back out the `risk_allocation_fraction` it implies.

## Method (reuses this project's own locked Monte Carlo convention, not invented fresh)

Block bootstrap (block length 21 trading days, the same value P31 already locked for this exact class of question — reused, not re-tuned) of TF3's actual net-of-cost daily return series, pooled across dev+OOS (2,008 days, mean +0.0218%/day, std 0.571%/day) — the best available estimate of the return-GENERATING process, a disclosed choice distinct from the dev-only calibration still used for the signal's own EWMAC scalars. 3,000 simulated paths per `EXPOSURE_MULT`, 180-trading-day horizon cap, walked day by day against each challenge's daily-loss, total-loss, and phase-target rules exactly as specified above (daily loss resets each simulated day; total loss is static against the initial balance and does NOT reset between Step 1 and Step 2, per the user's own "static... floor at 90% of initial balance" description).

## Results

### $5k 2-Step

| Exposure mult | Pass rate | Breach rate | No pass in 180d | Median days to pass |
|---|---|---|---|---|
| 1 | 12.7% | 26.3% | 61.0% | 115.5 |
| 1.5 | 30.6% | 24.0% | — | 95.0 |
| 2 | 36.5% | 44.8% | 18.7% | 75.0 |
| 2.5 | 36.9% | 55.3% | — | 66.0 |
| 3 | 34.5-34.9% | 62.3-63.0% | 2.7% | 46-46.5 |
| 5 | 27.2% | 72.8% | 0.0% | 22.0 |
| 8 | 23.3% | 76.7% | 0.0% | 11.0 |
| 12 | 18.1% | 81.9% | 0.0% | 8.0 |
| 16-20 | ~17-18% | ~82% | 0.0% | 6.0 |

### $10k 1-Step

| Exposure mult | Pass rate | Breach rate | No pass in 180d | Median days to pass |
|---|---|---|---|---|
| 1 | 30.9% | 27.6% | 41.5% | 100.0 |
| 1.5 | 41.6% | 44.4% | — | 70.0 |
| 2 | 43.0-43.1% | 52.6-53.1% | 4.4% | 49-53.0 |
| 2.5 | 38.1% | 60.8% | — | 34.0 |
| 3 | 38.7-39.7% | 60.1-61.1% | 0.2% | 27.0 |
| 5 | 30.5% | 69.5% | 0.0% | 12.0 |
| 8-20 | 26-28% | 72-74% | 0.0% | 3-6 |

## Read plainly

Both challenges show exactly the shape the survival guide's own Rule 3 predicts: pass rate rises with exposure up to a peak, then falls as breach risk overtakes the speed benefit. **The peak sits around exposure_mult ≈ 2-2.5 for the $5k challenge (36.5-36.9% pass rate) and ≈ 2 for the $10k challenge (43.0-43.1% pass rate).** Pushing exposure much higher (8x, 12x, 20x) buys a faster median time-to-pass (down to 6-11 days) at a steep cost — breach rate climbs past 75-82%, and pass rate actually falls well below the peak, not just plateaus. Going too low (1x) is also costly: months-long median time-to-pass and a large "never passed within 180 days" tail (41-61%), which on a real account likely means a re-purchase before the challenge would have organically resolved either way.

**No exposure level tested clears even a 50% pass rate.** The best this construction manages is 36.9% ($5k) and 43.1% ($10k) — meaning a real attempt at either challenge, sized at this simulation's best exposure level, would still be expected to fail more often than it passes. This is a statement about the challenge's structural difficulty relative to this signal's actual historical return distribution, not a modeling artifact — read it as a genuine finding, not a reason to keep raising exposure until pass rate looks better (which the sweep itself shows does not work past the ~2-2.5x peak).

## What this does NOT do

Does not pick a final `risk_allocation_fraction` for deployment — that still requires GFT's confirmed real leverage figure to convert the recommended `EFFECTIVE_EXPOSURE_MULT` (≈2-2.5) into an actual allocation percentage. Does not account for the $5k Step 2 target ambiguity (6% vs. 5%) — a lower Step 2 target would modestly raise the $5k pass rate, not simulated separately here. Does not model the "Initial Payout Cap" (4% withdrawal limit on the $5k account's first two reward requests) — that's a funded-phase economics question, not a pass/fail mechanic, out of scope for this simulation. Does not re-tune the block length, horizon, or number of simulations after seeing results — all three were fixed before this was run, reusing P31's own already-locked choices where available.
