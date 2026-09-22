"""
TF3 (long-only, revised) -- regime-conditioning diagnostic, re-run on the
ACTUAL shipped construction. TF2's original diagnostic (tf2_addendum_02...md)
was computed on the two-sided signal; this project's own locked methodology
treats this diagnostic as mandatory on any PASS, so it needs re-running on
whatever construction is actually shipping now, not left standing on the
superseded version. Uses the SAME 5 locked regime axes, SAME thresholds,
reused verbatim from methodology_regime_conditioning_gate.md -- nothing
re-thresholded here.
"""
import pandas as pd
import numpy as np
import os

DATA = '/home/claude/h4_uploads/xauusd_D1.csv'
MACRO = '/home/claude/macro_uploads/macro_raw.csv'
US500 = '/home/claude/equity_uploads2/us500_D1.csv'
DEV_END = '2025-04-02'
OOS_START = '2025-04-03'
OOS_END = '2026-07-03'
PAIRS = [(2, 8), (4, 16), (8, 32), (16, 64), (32, 128), (64, 256)]
VOL_WINDOW = 60
POINT_SIZE = 0.01
BUFFER_WIDTH = 0.10

HERE = os.path.dirname(os.path.abspath(__file__))


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


def main():
    d = pd.read_csv(DATA, parse_dates=['time']).set_index('time')
    px, hi, lo = d['close'], d['high'], d['low']
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
    raw_position = (combined / 20.0).clip(0, 1)  # REVISED: long-only

    target = raw_position.shift(1).fillna(0)
    held = np.zeros(len(target))
    t = target.values
    for i in range(1, len(t)):
        prev = held[i - 1]
        gap = t[i] - prev
        if abs(gap) > BUFFER_WIDTH:
            held[i] = prev + BUFFER_WIDTH if gap > 0 else prev - BUFFER_WIDTH
        else:
            held[i] = prev
    position = pd.Series(held, index=target.index)

    pos_change = position.diff().abs().fillna(position.abs())
    med_spread = spread_col[spread_col > 0].median()
    cost = pos_change * (spread_col.replace(0, med_spread) * POINT_SIZE) / px
    net_ret = position * logret - cost

    # --- regime axes, locked thresholds reused verbatim ---
    macro = pd.read_csv(MACRO, index_col=0, parse_dates=True)
    us500 = pd.read_csv(US500, parse_dates=['time']).set_index('time')['close']

    vol60 = logret.rolling(60, min_periods=60).std() * np.sqrt(252)
    vol_pctile = vol60.rolling(756, min_periods=200).apply(lambda x: (x < x.iloc[-1]).mean(), raw=False)
    vol_regime = pd.cut(vol_pctile, bins=[-1, 0.33, 0.67, 2], labels=['Low', 'Normal', 'High'])

    trend_regime = pd.cut(adx14(hi, lo, px), bins=[-1, 20, 25, 999], labels=['Range-bound', 'Transitional', 'Trending'])

    real_yield_regime = pd.cut(macro['real_yield'].diff(63), bins=[-999, -0.10, 0.10, 999], labels=['Falling', 'Flat', 'Rising']).reindex(px.index).ffill()
    dollar_regime = pd.cut(macro['dollar_index'].pct_change(63) * 100, bins=[-999, -0.5, 0.5, 999], labels=['Weakening', 'Flat', 'Strengthening']).reindex(px.index).ffill()

    us500_sma200 = us500.rolling(200, min_periods=200).mean()
    risk_regime = pd.Series(np.where(us500 > us500_sma200, 'Risk-On', 'Risk-Off'), index=us500.index).reindex(px.index).ffill()

    dev_net = net_ret.loc[:DEV_END]

    print(f"{'='*78}\nTF3 (long-only, revised) -- regime-conditioning diagnostic, dev window, net Sharpe per bucket\n{'='*78}")
    results = {}
    for axis_name, regime_series, buckets in [
        ('Vol regime', vol_regime, ['Low', 'Normal', 'High']),
        ('Trend regime (ADX)', trend_regime, ['Range-bound', 'Transitional', 'Trending']),
        ('Real-yield regime', real_yield_regime, ['Falling', 'Flat', 'Rising']),
        ('Dollar regime', dollar_regime, ['Weakening', 'Flat', 'Strengthening']),
        ('Risk-on/off (US500 vs SMA200)', risk_regime, ['Risk-On', 'Risk-Off']),
    ]:
        print(f"\n{axis_name}:")
        row = {}
        for b in buckets:
            mask = regime_series.loc[:DEV_END] == b
            sh = sharpe(dev_net[mask])
            n = mask.sum()
            row[b] = sh
            print(f"  {b:>14}: Sharpe={sh:.3f}  (n={n} days)")
        results[axis_name] = row

    pd.DataFrame(results).to_csv(os.path.join(HERE, 'tf3_longonly_regime_diagnostic.csv'))
    print(f"\nSaved to tf3_longonly_regime_diagnostic.csv")


if __name__ == '__main__':
    main()
