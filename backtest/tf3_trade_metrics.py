"""
TF3 XAUUSD -- trade-level metrics (distinct from the daily-return metrics
already reported elsewhere). A "trade" here = one continuous holding
period at a single buffered position value (position changes only when
the buffer rule -- Section 2 of model_spec_tf3 -- fires). Reports win
rate and expected value PER TRADE, not per day, since a per-day win rate
is dominated by small-magnitude noise on days where the position barely
moved, and a per-trade view is what actually matters for "does this
system make money when it acts."
"""
import pandas as pd
import numpy as np
import os

DATA = '/home/claude/h4_uploads/xauusd_D1.csv'
DEV_END = '2025-04-02'
OOS_START = '2025-04-03'
OOS_END = '2026-07-03'
PAIRS = [(2, 8), (4, 16), (8, 32), (16, 64), (32, 128), (64, 256)]
VOL_WINDOW = 60
POINT_SIZE = 0.01
BUFFER_WIDTH = 0.10

HERE = os.path.dirname(os.path.abspath(__file__))


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


def segment_trades(position, net_ret_series, window_name, s, e):
    pos = position.loc[s:e]
    ret = net_ret_series.loc[s:e]
    trades = []
    current_pos = None
    trade_ret = 0.0
    trade_days = 0
    for dt in pos.index:
        p = pos.loc[dt]
        r = ret.loc[dt] if not pd.isna(ret.loc[dt]) else 0.0
        if current_pos is None:
            current_pos = p
            trade_ret = r
            trade_days = 1
        elif p == current_pos:
            trade_ret += r
            trade_days += 1
        else:
            if current_pos != 0:
                trades.append({'window': window_name, 'position': current_pos,
                                'days_held': trade_days, 'trade_ret_pct': trade_ret * 100})
            current_pos = p
            trade_ret = r
            trade_days = 1
    if current_pos is not None and current_pos != 0:
        trades.append({'window': window_name, 'position': current_pos,
                        'days_held': trade_days, 'trade_ret_pct': trade_ret * 100})
    return trades


def main():
    d = pd.read_csv(DATA, parse_dates=['time']).set_index('time')
    px = d['close']
    spread_col = d['spread']
    logret = np.log(px / px.shift(1))

    position = build_tf3_position(px)
    pos_change = position.diff().abs().fillna(position.abs())
    med_spread = spread_col[spread_col > 0].median()
    cost = pos_change * (spread_col.replace(0, med_spread) * POINT_SIZE) / px
    net_ret = position * logret - cost

    all_trades = []
    for label, s, e in [('dev', None, DEV_END), ('oos', OOS_START, OOS_END)]:
        all_trades += segment_trades(position, net_ret, label, s, e)

    tdf = pd.DataFrame(all_trades)
    tdf.to_csv(os.path.join(HERE, 'tf3_trades.csv'), index=False)

    print(f"{'='*70}\nTF3 XAUUSD -- trade-level metrics (net of cost)\n{'='*70}")
    for label in ['dev', 'oos']:
        sub = tdf[tdf['window'] == label]
        n = len(sub)
        wins = (sub['trade_ret_pct'] > 0).sum()
        win_rate = wins / n if n else np.nan
        avg_win = sub.loc[sub['trade_ret_pct'] > 0, 'trade_ret_pct'].mean()
        avg_loss = sub.loc[sub['trade_ret_pct'] <= 0, 'trade_ret_pct'].mean()
        ev_per_trade = sub['trade_ret_pct'].mean()
        avg_days_held = sub['days_held'].mean()
        print(f"\n[{label}] n_trades={n}  win_rate={win_rate*100:.1f}%  "
              f"avg_win={avg_win:.3f}%  avg_loss={avg_loss:.3f}%  "
              f"EV/trade={ev_per_trade:.3f}%  avg_days_held={avg_days_held:.1f}")
        if n > 0 and avg_loss < 0:
            payoff_ratio = abs(avg_win / avg_loss)
            print(f"  payoff ratio (avg_win/|avg_loss|) = {payoff_ratio:.2f}")

    print(f"\nSaved {len(tdf)} trades to tf3_trades.csv")


if __name__ == '__main__':
    main()
