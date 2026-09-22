"""
TF3 XAUUSD (buffered EWMAC) vs. a 200-day-MA long-only benchmark.

The 200d-MA construction here reuses the SAME convention this project
already established in CAP1 (prop-firm proxy) and TC1 (live prop-firm
signal): long when close > SMA(close, 200), flat otherwise, no shorting.
This is NOT a naive buy-and-hold benchmark -- it is the actual signal
CLASS your live GFT prop-firm trend system runs (p4_signal_workflow.py:
MA_WINDOW = 200, long-only, ATR-stop exit). This script does not
replicate the ATR-stop exit or the cushion sizing -- it is a plain MA
flip, the same simplification CAP1 used and disclosed, chosen so the
comparison isolates "what does the EWMAC forecast do differently from a
plain trend-MA flip on the SAME instrument," not a comparison against
your fully-engineered live system.

Reads xauusd_D1.csv directly (same source as the TF3 package). Computes
both constructions gross AND net of the same spread-cost assumption
(point_size=0.01, TF2/TF3's own inferred value for XAUUSD -- reused
unchanged, not re-derived).
"""
import pandas as pd
import numpy as np
import os

DATA = '/home/claude/h4_uploads/xauusd_D1.csv'
DEV_END = '2025-04-02'
OOS_START = '2025-04-03'
OOS_END = '2026-07-03'
FLOOR = -0.06
PAIRS = [(2, 8), (4, 16), (8, 32), (16, 64), (32, 128), (64, 256)]
VOL_WINDOW = 60
POINT_SIZE = 0.01
BUFFER_WIDTH = 0.10
MA_WINDOW = 200

HERE = os.path.dirname(os.path.abspath(__file__))


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
    return (cum / cum.cummax() - 1).min()


def sharpe(r):
    r = r.dropna()
    if r.std() == 0 or len(r) < 2:
        return np.nan
    return (r.mean() / r.std()) * np.sqrt(252)


def sortino(r, target=0.0):
    r = r.dropna()
    downside = r[r < target]
    if len(downside) < 2 or downside.std() == 0:
        return np.nan
    return (r.mean() - target) / downside.std() * np.sqrt(252)


def win_rate(r):
    r = r.dropna()
    r = r[r != 0]  # exclude flat/no-position days from the win-rate denominator
    if len(r) == 0:
        return np.nan
    return (r > 0).mean()


def build_tf3_position(px):
    native_vol = px.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std()
    pair_forecasts = []
    for fast, slow in PAIRS:
        ewma_fast = px.ewm(span=fast, min_periods=fast).mean()
        ewma_slow = px.ewm(span=slow, min_periods=slow).mean()
        norm = (ewma_fast - ewma_slow) / native_vol.replace(0, np.nan)
        dev_norm = norm.loc[:DEV_END]
        m = dev_norm.abs().mean()
        scalar = 10.0 / m if m and not np.isnan(m) else np.nan
        pair_forecasts.append((norm * scalar).clip(-20, 20))
    combined = pd.concat(pair_forecasts, axis=1).mean(axis=1)
    # REVISED: long-only -- see research/tf3_addendum_05...md and tf4_addendum_01...md
    raw_position = (combined / 20.0).clip(0, 1)

    target = raw_position.shift(1).fillna(0)
    held = np.zeros(len(target))
    t = target.values
    for i in range(1, len(t)):
        prev_held = held[i - 1]
        gap = t[i] - prev_held
        if abs(gap) > BUFFER_WIDTH:
            held[i] = prev_held + BUFFER_WIDTH if gap > 0 else prev_held - BUFFER_WIDTH
        else:
            held[i] = prev_held
    return pd.Series(held, index=target.index)


def build_ma200_position(px):
    sma = px.rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()
    signal = (px > sma).astype(float)
    return signal.shift(1).fillna(0)


def cost_series(position, spread_col, px):
    pos_change = position.diff().abs().fillna(position.abs())
    med_spread = spread_col[spread_col > 0].median()
    return pos_change * (spread_col.replace(0, med_spread) * POINT_SIZE) / px


def main():
    d = pd.read_csv(DATA, parse_dates=['time']).set_index('time')
    px = d['close']
    spread_col = d['spread']
    logret = np.log(px / px.shift(1))

    tf3_pos = build_tf3_position(px)
    ma200_pos = build_ma200_position(px)

    tf3_gross = tf3_pos * logret
    tf3_net = tf3_gross - cost_series(tf3_pos, spread_col, px)

    ma_gross = ma200_pos * logret
    ma_net = ma_gross - cost_series(ma200_pos, spread_col, px)

    rows = []
    for label, s, e in [('dev', None, DEV_END), ('oos', OOS_START, OOS_END)]:
        for name, gross, net in [('TF3 (buffered EWMAC)', tf3_gross, tf3_net),
                                  ('200d-MA long-only', ma_gross, ma_net)]:
            g = gross.loc[s:e]
            n = net.loc[s:e]
            rows.append({
                'window': label, 'construction': name,
                'gross_sharpe': sharpe(g), 'net_sharpe': sharpe(n),
                'net_sortino': sortino(n), 'net_win_rate': win_rate(n),
                'net_ann_return_pct': n.mean() * 252 * 100,
                'net_max_dd_pct': max_dd(n) * 100,
                'net_breach_episodes': breach_episodes(n),
                'net_ev_per_day_bps': n.mean() * 10000,
            })

    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    out.to_csv(os.path.join(HERE, 'tf3_vs_200dma_metrics.csv'), index=False)

    # save series for figure
    series = pd.DataFrame({
        'close': px, 'tf3_net_ret': tf3_net, 'ma200_net_ret': ma_net,
    })
    series.to_csv(os.path.join(HERE, 'tf3_vs_200dma_series.csv'))
    print(f"\nSaved metrics to tf3_vs_200dma_metrics.csv, series to tf3_vs_200dma_series.csv")


if __name__ == '__main__':
    main()
