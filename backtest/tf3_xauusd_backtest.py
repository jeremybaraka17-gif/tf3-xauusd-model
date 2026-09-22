"""
TF3 -- XAUUSD deployment backtest (consolidated, standalone)

Reproduces, in one place, the exact construction validated across TF2 (signal,
net-of-cost, regime diagnostic) and TF3 (position-inertia buffer). Nothing here
is re-tuned -- every parameter is copied unchanged from the research docs in
../research/. If a number produced by this script does not match the research
docs, that is a bug in this consolidation, not a new result.

Source scripts this was extracted/adapted from (not included verbatim, kept
for provenance): tf2_run.py, tf2_full_construction.py, plus the inline
buffer sanity-check originally run as a one-off `python3 -c "..."` command
and never previously saved as its own script.

Run from this directory:  python3 tf3_xauusd_backtest.py
Expects ../data/xauusd_D1.csv, ../data/macro_raw.csv, ../data/us500_D1.csv
"""
import pandas as pd
import numpy as np
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')

DEV_END = '2025-04-02'
OOS_START = '2025-04-03'
OOS_END = '2026-07-03'
FLOOR = -0.06
PAIRS = [(2, 8), (4, 16), (8, 32), (16, 64), (32, 128), (64, 256)]
VOL_WINDOW = 60
POINT_SIZE = 0.01          # inferred and justified in model_spec_tf2..., Section 6
BUFFER_WIDTH = 0.10        # Carver literature-standard starting point, model_spec_tf3, Section 2
STAGE = 'stage1'           # recommended stage for XAUUSD per model_spec_tf2, Section 3


# ---------------------------------------------------------------- metrics ---
def breach_episodes(r, floor=FLOOR):
    r = r.dropna()
    if len(r) == 0:
        return 0
    cum = (1 + r).cumprod()
    dd = cum / cum.cummax() - 1
    below = dd < floor
    prev = below.shift(1).fillna(False).astype(bool)
    return int((below & (~prev)).sum())


def max_dd(r):
    r = r.dropna()
    if len(r) == 0:
        return np.nan
    cum = (1 + r).cumprod()
    dd = cum / cum.cummax() - 1
    return dd.min()


def sharpe(r):
    r = r.dropna()
    if r.std() == 0 or len(r) < 2:
        return np.nan
    return (r.mean() / r.std()) * np.sqrt(252)


def adx14(high, low, close):
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat([(high - low), (high - close.shift()).abs(),
                     (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, min_periods=14).mean()
    plus_di = 100 * pd.Series(plus_dm, index=high.index).ewm(alpha=1 / 14, min_periods=14).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=high.index).ewm(alpha=1 / 14, min_periods=14).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1 / 14, min_periods=14).mean()


# ------------------------------------------------------------- signal ------
def build_signal(px):
    """Six-pair EWMAC combined forecast and Stage-1 raw position. Dev-only
    calibration, frozen scalars, no look-ahead into OOS."""
    native_vol = px.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std()
    pair_forecasts = []
    for fast, slow in PAIRS:
        ewma_fast = px.ewm(span=fast, min_periods=fast).mean()
        ewma_slow = px.ewm(span=slow, min_periods=slow).mean()
        raw = ewma_fast - ewma_slow
        norm = raw / native_vol.replace(0, np.nan)
        dev_norm = norm.loc[:DEV_END]
        m = dev_norm.abs().mean()
        scalar = 10.0 / m if m and not np.isnan(m) else np.nan
        pair_forecasts.append((norm * scalar).clip(-20, 20))
    combined_forecast = pd.concat(pair_forecasts, axis=1).mean(axis=1)
    # REVISED per tf3_addendum_05/tf4_addendum_01: shorts removed. The short side was
    # found to destroy value on every metric in both windows (Addendum 05), and dropping
    # it was confirmed robust across 5 locked vol-normalization windows (TF4), not just
    # this one -- clip(0, 1) instead of clip(-1, 1) is a disclosed construction change,
    # not a silent edit.
    raw_position = (combined_forecast / 20.0).clip(0, 1)
    return combined_forecast, raw_position


def apply_buffer(raw_position, buffer_width=BUFFER_WIDTH):
    """Position-inertia buffer, Carver's own published 'trade to the edge of
    the buffer' rule. Only trade when the (lagged) target has moved far
    enough from the currently-held position; when triggered, move only to
    the nearer edge of the buffer band, not all the way to target."""
    target = raw_position.shift(1).fillna(0)
    held = np.zeros(len(target))
    t = target.values
    for i in range(1, len(t)):
        prev_held = held[i - 1]
        gap = t[i] - prev_held
        if abs(gap) > buffer_width:
            edge = prev_held + buffer_width if gap > 0 else prev_held - buffer_width
            held[i] = edge
        else:
            held[i] = prev_held
    return pd.Series(held, index=target.index)


def main():
    d = pd.read_csv(os.path.join(DATA, 'xauusd_D1.csv'), parse_dates=['time']).set_index('time')
    px, hi, lo = d['close'], d['high'], d['low']
    spread_col = d['spread']
    logret = np.log(px / px.shift(1))

    combined_forecast, raw_position = build_signal(px)

    # unbuffered (matches TF2 Stage 1 exactly)
    pos_unbuffered = raw_position.shift(1).fillna(0)
    # buffered (TF3 deployment version)
    pos_buffered = apply_buffer(raw_position, BUFFER_WIDTH)

    for label, position in [('unbuffered (TF2 Stage1)', pos_unbuffered),
                             ('buffered (TF3, width=0.10)', pos_buffered)]:
        gross_ret = position * logret
        pos_change = position.diff().abs().fillna(position.abs())
        cost = pos_change * (spread_col.replace(0, spread_col[spread_col > 0].median()) * POINT_SIZE) / px
        net_ret = gross_ret - cost

        bh_pos = pd.Series(1.0, index=px.index)
        bh_change = bh_pos.diff().abs().fillna(1.0)
        bh_cost = bh_change * (spread_col.replace(0, spread_col[spread_col > 0].median()) * POINT_SIZE) / px
        bh_net = logret - bh_cost

        print(f"\n{'=' * 70}\n=== XAUUSD -- {label} ===\n{'=' * 70}")
        for win, s, e in [('dev', None, DEV_END), ('oos', OOS_START, OOS_END)]:
            n = net_ret.loc[s:e]
            bn = bh_net.loc[s:e]
            turnover = pos_change.loc[s:e].mean()
            print(f"  [{win}] turnover={turnover:.4f}  Sharpe(net)={sharpe(n):.3f}  "
                  f"breach(net)={breach_episodes(n)}  vs BH breach(net)={breach_episodes(bn)}  "
                  f"PASS={breach_episodes(n) < breach_episodes(bn)}")

    # save series for figure generation
    out = pd.DataFrame({
        'close': px,
        'logret': logret,
        'combined_forecast': combined_forecast,
        'pos_unbuffered': pos_unbuffered,
        'pos_buffered': pos_buffered,
    })
    out.to_csv(os.path.join(HERE, 'tf3_xauusd_series.csv'))
    print(f"\nSaved series to {os.path.join(HERE, 'tf3_xauusd_series.csv')}")


if __name__ == '__main__':
    main()
