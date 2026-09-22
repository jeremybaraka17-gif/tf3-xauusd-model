"""
TF3 XAUUSD -- long/short decomposition and three-way benchmark comparison
(buy-and-hold, 200d-MA long-only, TF3 two-sided).

Two things this adds beyond what's already in the package:
1. Splits TF3's net return into days held long vs. days held short, and
   separately builds a LONG-ONLY variant of the identical signal
   (position clipped to [0,1] instead of [-1,1], same buffer, same
   everything else) to isolate what shorting actually contributes versus
   a same-construction long-only version -- not just "TF3 vs a totally
   different long-only MA signal" (that comparison already exists in
   tf3_vs_200dma_result.md).
2. Produces the three-way series (buy-and-hold, 200d-MA long-only, TF3)
   for a single combined chart.
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


def sharpe(r):
    r = r.dropna()
    if r.std() == 0 or len(r) < 2:
        return np.nan
    return (r.mean() / r.std()) * np.sqrt(252)


def max_dd(r):
    r = r.dropna()
    if len(r) == 0:
        return np.nan
    cum = (1 + r).cumprod()
    return (cum / cum.cummax() - 1).min()


def breach_episodes(r, floor=FLOOR):
    r = r.dropna()
    if len(r) == 0:
        return 0
    cum = (1 + r).cumprod()
    dd = cum / cum.cummax() - 1
    below = dd < floor
    prev = below.shift(1).fillna(False).astype(bool)
    return int((below & (~prev)).sum())


def buffer_apply(raw_position, buffer_width=BUFFER_WIDTH):
    target = raw_position.shift(1).fillna(0)
    held = np.zeros(len(target))
    t = target.values
    for i in range(1, len(t)):
        prev = held[i - 1]
        gap = t[i] - prev
        if abs(gap) > buffer_width:
            held[i] = prev + buffer_width if gap > 0 else prev - buffer_width
        else:
            held[i] = prev
    return pd.Series(held, index=target.index)


def cost_series(position, spread_col, px):
    pos_change = position.diff().abs().fillna(position.abs())
    med_spread = spread_col[spread_col > 0].median()
    return pos_change * (spread_col.replace(0, med_spread) * POINT_SIZE) / px


def main():
    d = pd.read_csv(DATA, parse_dates=['time']).set_index('time')
    px = d['close']
    spread_col = d['spread']
    logret = np.log(px / px.shift(1))

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

    raw_position_twosided = (combined / 20.0).clip(-1, 1)
    raw_position_longonly = (combined / 20.0).clip(0, 1)  # same signal, shorts zeroed instead of taken

    pos_twosided = buffer_apply(raw_position_twosided)
    pos_longonly = buffer_apply(raw_position_longonly)

    tf3_net = pos_twosided * logret - cost_series(pos_twosided, spread_col, px)
    longonly_net = pos_longonly * logret - cost_series(pos_longonly, spread_col, px)

    bh_pos = pd.Series(1.0, index=px.index)
    bh_net = logret - cost_series(bh_pos, spread_col, px)

    ma200_pos = (px > px.rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()).astype(float).shift(1).fillna(0)
    ma200_net = ma200_pos * logret - cost_series(ma200_pos, spread_col, px)

    # --- long/short decomposition of TF3 itself ---
    print(f"{'='*78}\nTF3 long/short decomposition (net of cost)\n{'='*78}")
    for label, s, e in [('dev', None, DEV_END), ('oos', OOS_START, OOS_END)]:
        pos_w = pos_twosided.loc[s:e]
        ret_w = tf3_net.loc[s:e]
        long_days = pos_w > 0
        short_days = pos_w < 0
        flat_days = pos_w == 0
        long_contrib = ret_w[long_days].sum()
        short_contrib = ret_w[short_days].sum()
        total = ret_w.sum()
        print(f"\n[{label}] total_net_log_return={total*100:.2f}%  "
              f"long_days={long_days.sum()} ({long_days.mean()*100:.1f}%)  "
              f"short_days={short_days.sum()} ({short_days.mean()*100:.1f}%)  "
              f"flat_days={flat_days.sum()} ({flat_days.mean()*100:.1f}%)")
        print(f"  Contribution from LONG days:  {long_contrib*100:+.2f}%  "
              f"(Sharpe on long-only subset, ret on long days vs 0 on others: "
              f"{sharpe(ret_w.where(long_days, 0)):.3f})")
        print(f"  Contribution from SHORT days: {short_contrib*100:+.2f}%  "
              f"(Sharpe on short-only subset: {sharpe(ret_w.where(short_days, 0)):.3f})")

    # --- two-sided TF3 vs. same-signal long-only variant ---
    print(f"\n{'='*78}\nTF3 (two-sided) vs. SAME signal, long-only variant (shorts zeroed)\n{'='*78}")
    rows = []
    for label, s, e in [('dev', None, DEV_END), ('oos', OOS_START, OOS_END)]:
        for name, series in [('TF3 two-sided', tf3_net), ('TF3 long-only variant', longonly_net),
                              ('Buy & hold', bh_net), ('200d-MA long-only', ma200_net)]:
            r = series.loc[s:e]
            rows.append({
                'window': label, 'construction': name,
                'net_sharpe': sharpe(r), 'net_ann_return_pct': r.mean() * 252 * 100,
                'net_max_dd_pct': max_dd(r) * 100, 'net_breach_episodes': breach_episodes(r),
            })
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    out.to_csv(os.path.join(HERE, 'tf3_long_short_and_threeway_metrics.csv'), index=False)

    # --- save series for the three-way + long-only chart ---
    series_df = pd.DataFrame({
        'close': px, 'bh_net_ret': bh_net, 'ma200_net_ret': ma200_net,
        'tf3_net_ret': tf3_net, 'tf3_longonly_net_ret': longonly_net,
    })
    series_df.to_csv(os.path.join(HERE, 'tf3_threeway_series.csv'))
    print(f"\nSaved metrics + series.")


if __name__ == '__main__':
    main()
