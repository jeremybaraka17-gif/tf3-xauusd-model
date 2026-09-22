"""
TF4 -- long-only EWMAC (shorts removed) robustness sweep across the
vol-normalization window. See research/hypothesis_tf4_long_only_vol_window_robustness.md
for the locked design -- this script implements it exactly, nothing
tuned after seeing output.
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
POINT_SIZE = 0.01
BUFFER_WIDTH = 0.10
MA_WINDOW = 200
CANDIDATE_VOL_WINDOWS = [30, 45, 60, 90, 120]  # locked in the pre-registration, not searched

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


def build_positions(px, vol_window, clip_range):
    native_vol = px.rolling(vol_window, min_periods=vol_window).std()
    pair_forecasts = []
    for fast, slow in PAIRS:
        ewma_fast = px.ewm(span=fast, min_periods=fast).mean()
        ewma_slow = px.ewm(span=slow, min_periods=slow).mean()
        norm = (ewma_fast - ewma_slow) / native_vol.replace(0, np.nan)
        dev_norm = norm.loc[:DEV_END]
        m = dev_norm.abs().mean()
        # scalar re-calibrated PER WINDOW on dev data only -- see Section 3's rationale
        scalar = 10.0 / m if m and not np.isnan(m) else np.nan
        pair_forecasts.append((norm * scalar).clip(-20, 20))
    combined = pd.concat(pair_forecasts, axis=1).mean(axis=1)
    raw_position = (combined / 20.0).clip(*clip_range)
    return buffer_apply(raw_position)


def main():
    d = pd.read_csv(DATA, parse_dates=['time']).set_index('time')
    px = d['close']
    spread_col = d['spread']
    logret = np.log(px / px.shift(1))

    ma200_pos = (px > px.rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()).astype(float).shift(1).fillna(0)
    ma200_net = ma200_pos * logret - cost_series(ma200_pos, spread_col, px)

    rows = []
    both_windows_beat_twosided = 0
    print(f"{'='*90}\nTF4 -- long-only vs two-sided, swept across VOL_WINDOW (locked candidates)\n{'='*90}")
    for W in CANDIDATE_VOL_WINDOWS:
        pos_long = build_positions(px, W, (0, 1))
        pos_two = build_positions(px, W, (-1, 1))
        net_long = pos_long * logret - cost_series(pos_long, spread_col, px)
        net_two = pos_two * logret - cost_series(pos_two, spread_col, px)

        beats_both = True
        print(f"\n--- VOL_WINDOW={W} ---")
        for label, s, e in [('dev', None, DEV_END), ('oos', OOS_START, OOS_END)]:
            sh_long = sharpe(net_long.loc[s:e])
            sh_two = sharpe(net_two.loc[s:e])
            sh_ma = sharpe(ma200_net.loc[s:e])
            beats_two = sh_long > sh_two
            beats_both &= beats_two
            rows.append({
                'vol_window': W, 'construction': f'long-only', 'window': label,
                'net_sharpe': sh_long, 'net_max_dd_pct': max_dd(net_long.loc[s:e]) * 100,
                'net_breach': breach_episodes(net_long.loc[s:e]),
                'vs_twosided_sharpe': sh_two, 'vs_ma200_sharpe': sh_ma,
                'beats_twosided': beats_two,
            })
            print(f"  [{label}] long-only Sharpe={sh_long:.3f}  vs two-sided={sh_two:.3f}  "
                  f"vs 200d-MA={sh_ma:.3f}  long-only>two-sided: {beats_two}")
        if beats_both:
            both_windows_beat_twosided += 1
            print(f"  => beats two-sided in BOTH windows at this vol_window")

    print(f"\n{'='*90}\nSUMMARY: long-only beat two-sided in BOTH windows at "
          f"{both_windows_beat_twosided}/{len(CANDIDATE_VOL_WINDOWS)} candidate vol_windows\n{'='*90}")
    if both_windows_beat_twosided >= 4:
        verdict = "PASS (robust)"
    elif both_windows_beat_twosided >= 2:
        verdict = "PARTIAL (window-dependent)"
    else:
        verdict = "FAIL (fragile)"
    print(f"Verdict per Section 4's locked thresholds: {verdict}")

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(HERE, 'tf4_vol_window_sweep_results.csv'), index=False)
    print(f"\nSaved to tf4_vol_window_sweep_results.csv")


if __name__ == '__main__':
    main()
