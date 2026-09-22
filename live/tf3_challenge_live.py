"""
tf3_challenge_live.py -- daily signal generation for TF3/XAUUSD on a GFT
prop-challenge account, wired to tf3_risk_governor.py exactly the way the
existing live prop-firm system wires p4_signal_workflow.py to its own
risk_governor.py: the governor is consulted BEFORE any new-entry sizing
is suggested, and HALT means "no new entries," never a forced close of
whatever is already open.

Sizing formula corrected from the original `tf3_xauusd_live.py` draft
(see research/tf3_addendum_02...md, item under "genuinely notable"): that
draft used `target_position * risk_allocation_fraction * account_equity`
as a literal dollar notional with NO leverage term, which does not match
how a real leveraged CFD/margin account actually works. This version
follows the survival guide's own formula exactly:

    notional_exposure_usd = target_position * EFFECTIVE_EXPOSURE_MULT * account_equity
    target_lots = notional_exposure_usd / (contract_size * price)

where EFFECTIVE_EXPOSURE_MULT = risk_allocation_fraction x actual_leverage,
collapsed into one number because GFT's real leverage for XAUUSD is NOT
confirmed in this project (see research/tf3_addendum_03...md) -- rather
than guess a leverage number and a risk_allocation_fraction separately
and multiply two unconfirmed numbers together, this script takes their
already-swept PRODUCT directly from challenge_config.json
("effective_exposure_mult"), which the Monte Carlo addendum grounds in
an actual pass-rate simulation, not a guess.

STILL NOT DONE: confirming GFT's real leverage for XAUUSD would let you
decompose effective_exposure_mult back into an actual risk_allocation_fraction
of capital, which may matter for other reasons (e.g. margin call distance
independent of the challenge's own loss limits, which this script does
NOT separately model -- the governor's own loss-limit tracking is the
binding constraint simulated here, and margin-call risk is a DIFFERENT,
unmodeled failure mode if effective_exposure_mult is pushed high enough
relative to the account's real available margin).
"""
import argparse
import json
import os
import pandas as pd
import numpy as np

import tf3_risk_governor as gov

HERE = os.path.dirname(os.path.abspath(__file__))
PAIRS = [(2, 8), (4, 16), (8, 32), (16, 64), (32, 128), (64, 256)]
VOL_WINDOW = 60
BUFFER_WIDTH = 0.10
CONTRACT_SIZE = 100  # oz/lot, per the project's own survival guide multiplier table -- confirm against the actual GFT XAUUSD spec before use
DEV_END = '2025-04-02'


def _load_config():
    with open(os.path.join(HERE, 'challenge_config.json')) as f:
        return json.load(f)


def compute_dev_scalars(price_csv):
    d = pd.read_csv(price_csv, parse_dates=['time']).set_index('time')
    return compute_dev_scalars_from_df(d)


def compute_dev_scalars_from_df(d):
    """Same as compute_dev_scalars, but takes an already-loaded DataFrame
    (indexed by time, with a 'close' column) instead of a CSV path.
    Added so tf3_daemon.py can pass MT5-sourced bars straight through
    without round-tripping them to a temp file first -- compute_dev_scalars
    itself is left untouched so the existing CLI usage of this module
    (tf3_challenge_live.py run manually with --price-csv) is unaffected."""
    px = d['close']
    native_vol = px.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std()
    scalars = {}
    for fast, slow in PAIRS:
        ewma_fast = px.ewm(span=fast, min_periods=fast).mean()
        ewma_slow = px.ewm(span=slow, min_periods=slow).mean()
        norm = (ewma_fast - ewma_slow) / native_vol.replace(0, np.nan)
        dev_norm = norm.loc[:DEV_END]
        m = dev_norm.abs().mean()
        scalars[(fast, slow)] = 10.0 / m if m and not np.isnan(m) else np.nan
    return scalars


def combined_forecast_today(price_series, dev_scalars):
    native_vol = price_series.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std()
    pair_forecasts = []
    for fast, slow in PAIRS:
        ewma_fast = price_series.ewm(span=fast, min_periods=fast).mean()
        ewma_slow = price_series.ewm(span=slow, min_periods=slow).mean()
        norm = (ewma_fast - ewma_slow) / native_vol.replace(0, np.nan)
        scalar = dev_scalars[(fast, slow)]
        pair_forecasts.append((norm * scalar).clip(-20, 20))
    combined = pd.concat(pair_forecasts, axis=1).mean(axis=1)
    return combined.iloc[-1]


def apply_buffer_single_step(target, held_position, buffer_width=BUFFER_WIDTH):
    gap = target - held_position
    if abs(gap) > buffer_width:
        return (held_position + buffer_width if gap > 0 else held_position - buffer_width), True
    return held_position, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--price-csv', required=True)
    ap.add_argument('--held-position', type=float, required=True)
    ap.add_argument('--current-equity', type=float, required=True,
                     help='Current account equity (for the risk governor check)')
    ap.add_argument('--xauusd-price', type=float, default=None)
    args = ap.parse_args()

    cfg = _load_config()

    gstate, diag, challenge_passed = gov.evaluate(args.current_equity)
    print(f"Governor state: {gstate.value}")
    print(f"  Daily loss: {diag['daily_loss_pct']*100:.2f}% (limit {diag['daily_limit']*100:.0f}%)")
    print(f"  Total loss: {diag['total_loss_pct']*100:.2f}% (limit {diag['total_limit']*100:.0f}%)")
    print(f"  Phase: {diag['phase_name']}  gain={diag['phase_gain_pct']*100:.2f}% "
          f"(target {diag['phase_target']*100:.0f}%)  trading_days_this_phase={diag['trading_days_this_phase']}")
    if challenge_passed:
        print("  *** CHALLENGE PASSED ***")

    d = pd.read_csv(args.price_csv, parse_dates=['time']).set_index('time')
    px = d['close']
    dev_scalars = compute_dev_scalars(args.price_csv)
    cf_today = combined_forecast_today(px, dev_scalars)
    # REVISED: long-only -- see research/tf3_addendum_05...md and tf4_addendum_01...md
    target = float(np.clip(cf_today / 20.0, 0, 1))

    if gstate == gov.GovernorState.HALT:
        print("\nHALT -- no new entries suggested. Existing position (if any) may remain per your own judgment.")
        new_position = args.held_position
        traded = False
    else:
        new_position, traded = apply_buffer_single_step(target, args.held_position)

    xau_px = args.xauusd_price if args.xauusd_price is not None else float(px.iloc[-1])
    exposure_mult = cfg['effective_exposure_mult']
    notional_exposure_usd = new_position * exposure_mult * args.current_equity
    target_lots = notional_exposure_usd / (CONTRACT_SIZE * xau_px) if xau_px else 0.0

    print(f"\nRaw target position (-1..+1): {target:.4f}")
    print(f"Held position (input):         {args.held_position:.4f}")
    print(f"New position to hold:          {new_position:.4f}  (trade fires: {traded})")
    print(f"effective_exposure_mult (from challenge_config.json, Monte Carlo peak): {exposure_mult}")
    print(f"  ^ product of risk_allocation_fraction x real GFT leverage -- leverage itself UNCONFIRMED, see research/tf3_addendum_03...md")
    print(f"Target notional exposure (USD): {notional_exposure_usd:,.2f}")
    print(f"Target lots ({CONTRACT_SIZE} oz/lot): {target_lots:.4f}")
    print("\nThis computes a TARGET only. Does not place orders. Margin-call risk "
          "at this exposure level is NOT separately modeled -- see this file's own docstring.")


if __name__ == '__main__':
    main()
