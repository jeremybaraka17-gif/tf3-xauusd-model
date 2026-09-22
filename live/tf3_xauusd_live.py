"""
TF3 -- XAUUSD live deployment logic (signal + position-inertia buffer +
account-terms position sizing). This is a reference implementation of the
decision logic specified in ../research/model_spec_tf3_xauusd_deployment_architecture_v1.md.

THIS IS NOT WIRED TO A BROKER. There is no order-execution, authentication,
or connectivity code here -- deliberately. What this file provides is the
part that IS validated by research: given a price history ending at "today,"
what position should be held tomorrow, and how many lots does that imply.
Wiring it to a live feed and a broker API is an infrastructure task outside
this project's research scope, and doing so without review is exactly the
kind of unreviewed step Section 5 of the deployment spec exists to prevent.

Required before this is actually turned on, per the model spec's own
Section 7 ("what this document does not do"):
  - `risk_allocation_fraction` is NOT set here (see CONFIG below) -- it is
    an explicit open business decision, not a research output.
  - No live deployment slot has been confirmed for XAUUSD in either of this
    project's two existing live systems -- this would be a third, separate
    live construction, and that decision has not been made (see model_spec_tf3,
    Section 3, and model_spec_tf2, Section 9).
  - The data-integrity and regime kill switches (Section 5 of the spec) are
    stubbed below with a clear TODO, not implemented -- they need real
    exchange/feed-specific logic this research phase doesn't have.

Usage:
    python3 tf3_xauusd_live.py --price-csv /path/to/latest_xauusd_D1.csv \
        --held-position 0.0 --account-equity 100000 --risk-allocation-fraction 0.0
"""
import argparse
import pandas as pd
import numpy as np

PAIRS = [(2, 8), (4, 16), (8, 32), (16, 64), (32, 128), (64, 256)]
VOL_WINDOW = 60
BUFFER_WIDTH = 0.10
CONTRACT_SIZE = 100  # oz per standard lot -- confirm against your broker's contract spec before use

# Frozen per-pair scalars, calibrated on the dev window 2018-08-21..2025-04-02
# and NOT recalibrated here (recalibrating on more recent data would be
# silent re-tuning outside this project's pre-registration discipline).
# Reproduced by running backtest/tf3_xauusd_backtest.py and reading off
# each pair's `scalar` value -- pasted here as constants so this script has
# no dependency on the historical dev window being present in the live feed.
DEV_END = '2025-04-02'


def compute_dev_scalars(dev_price_csv):
    """One-time utility: recompute the frozen scalars from the dev window,
    if you need to re-derive DEV_SCALARS below from scratch. Not called by
    the live path -- kept here for auditability, not for routine use."""
    d = pd.read_csv(dev_price_csv, parse_dates=['time']).set_index('time')
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
    """price_series: pd.Series of close prices, indexed by date, ending at
    the most recent available close. Returns the combined forecast for the
    LAST date in the series (not yet lagged -- caller applies the 1-day
    execution lag by holding this position starting next session)."""
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


def target_position_from_forecast(combined_forecast_value):
    # REVISED: long-only (clip 0..1, not -1..1) -- see research/tf3_addendum_05...md
    # and research/tf4_addendum_01...md. The short side was found to destroy value on
    # every metric in both windows, and the fix was confirmed robust across 5 vol-window
    # choices, not tuned to look good on this one.
    return float(np.clip(combined_forecast_value / 20.0, 0, 1))


def apply_buffer_single_step(target, held_position, buffer_width=BUFFER_WIDTH):
    """One-step version of the buffer rule for live use: given today's target
    (already reflecting the 1-day execution lag -- i.e. this is the position
    to move toward, to be held starting the next session) and the currently
    held position, return the new position to hold and whether a trade fires."""
    gap = target - held_position
    if abs(gap) > buffer_width:
        new_position = held_position + buffer_width if gap > 0 else held_position - buffer_width
        return new_position, True
    return held_position, False


def data_integrity_kill_switch(price_series):
    """STUB -- not implemented. Per model_spec_tf3 Section 5: suspend new
    position changes on an implausible single-day move. Needs a concrete
    threshold (e.g. daily |logret| beyond N standard deviations of trailing
    realized vol) calibrated and reviewed before use, not invented here."""
    raise NotImplementedError(
        "Data-integrity kill switch is specified but not implemented -- "
        "see model_spec_tf3_xauusd_deployment_architecture_v1.md, Section 5."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--price-csv', required=True, help='Daily OHLC csv with a "time" and "close" column, most recent close last')
    ap.add_argument('--held-position', type=float, required=True, help='Currently held position, -1..+1')
    ap.add_argument('--account-equity', type=float, required=True)
    ap.add_argument('--risk-allocation-fraction', type=float, required=True,
                     help='OPEN BUSINESS DECISION -- not set by research. Pass 0.0 until this is actually decided.')
    ap.add_argument('--xauusd-price', type=float, default=None,
                     help='Optional override for the current XAUUSD price used in the lot-size conversion; defaults to the last close in --price-csv')
    args = ap.parse_args()

    d = pd.read_csv(args.price_csv, parse_dates=['time']).set_index('time')
    px = d['close']

    dev_scalars = compute_dev_scalars(args.price_csv)
    cf_today = combined_forecast_today(px, dev_scalars)
    target = target_position_from_forecast(cf_today)

    new_position, traded = apply_buffer_single_step(target, args.held_position)

    xau_px = args.xauusd_price if args.xauusd_price is not None else float(px.iloc[-1])
    notional_risk_capital = args.account_equity * args.risk_allocation_fraction
    target_exposure_usd = new_position * notional_risk_capital
    target_lots = target_exposure_usd / (CONTRACT_SIZE * xau_px) if xau_px else 0.0

    print(f"Combined forecast (today, pre-lag):  {cf_today:.3f}")
    print(f"Raw target position (-1..+1):        {target:.4f}")
    print(f"Held position (input):                {args.held_position:.4f}")
    print(f"Buffer width:                          {BUFFER_WIDTH}")
    print(f"Trade fires:                           {traded}")
    print(f"New position to hold (starting next session): {new_position:.4f}")
    print(f"risk_allocation_fraction:              {args.risk_allocation_fraction}  "
          f"{'<-- STILL UNDECIDED, see model_spec_tf3 Section 3' if args.risk_allocation_fraction == 0 else ''}")
    print(f"Target notional exposure (USD):        {target_exposure_usd:,.2f}")
    print(f"Target lots ({CONTRACT_SIZE} oz/lot):        {target_lots:.4f}")
    print()
    print("Reminder: this script computes a TARGET. It does not place orders, "
          "check the data-integrity kill switch (unimplemented, see Section 5), "
          "or check the regime-based monitoring flag (diagnostic only, not a "
          "trading gate per this project's locked methodology).")


if __name__ == '__main__':
    main()
