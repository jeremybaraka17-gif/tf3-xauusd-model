"""
Generate figures for the TF3 XAUUSD package. Run AFTER tf3_xauusd_backtest.py
(reads its saved series). Writes PNGs into ../figures/.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, '..', 'figures')
os.makedirs(FIG, exist_ok=True)

DEV_END = '2025-04-02'
OOS_START = '2025-04-03'

s = pd.read_csv(os.path.join(HERE, 'tf3_xauusd_series.csv'), index_col=0, parse_dates=True)

bh_ret = s['logret']
tf3_ret = (s['pos_buffered'] * s['logret'])

bh_cum = (1 + bh_ret.fillna(0)).cumprod()
tf3_cum = (1 + tf3_ret.fillna(0)).cumprod()

# ---------------------------------------------------------------- Fig 1 ---
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(bh_cum.index, bh_cum.values, label='Buy & Hold XAUUSD', color='#888888', lw=1.2)
ax.plot(tf3_cum.index, tf3_cum.values, label='TF3 (buffered EWMAC, gross)', color='#1a5fb4', lw=1.4)
ax.axvline(pd.Timestamp(DEV_END), color='black', ls='--', lw=0.8, alpha=0.6)
ax.text(pd.Timestamp(DEV_END), ax.get_ylim()[1]*0.02 + ax.get_ylim()[0], '  dev | OOS', fontsize=8, alpha=0.7)
ax.set_yscale('log')
ax.set_title('TF3 XAUUSD -- Growth of $1, gross of cost (log scale)')
ax.set_ylabel('Cumulative growth (log)')
ax.legend(loc='upper left')
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'equity_curve.png'), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- Fig 2 ---
bh_dd = bh_cum / bh_cum.cummax() - 1
tf3_dd = tf3_cum / tf3_cum.cummax() - 1

fig, ax = plt.subplots(figsize=(11, 4.5))
ax.fill_between(bh_dd.index, bh_dd.values * 100, 0, color='#888888', alpha=0.35, label='Buy & Hold drawdown')
ax.fill_between(tf3_dd.index, tf3_dd.values * 100, 0, color='#1a5fb4', alpha=0.45, label='TF3 drawdown')
ax.axhline(-6, color='#c01c28', ls='--', lw=1, label='-6% floor')
ax.axvline(pd.Timestamp(DEV_END), color='black', ls='--', lw=0.8, alpha=0.6)
ax.set_title('TF3 XAUUSD -- Drawdown vs. -6% floor-breach-episode definition')
ax.set_ylabel('Drawdown (%)')
ax.legend(loc='lower left')
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'drawdown.png'), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- Fig 3 ---
fig, ax = plt.subplots(figsize=(11, 3.2))
ax.plot(s.index, s['pos_buffered'], color='#1a5fb4', lw=0.8)
ax.axhline(0, color='black', lw=0.6)
ax.axvline(pd.Timestamp(DEV_END), color='black', ls='--', lw=0.8, alpha=0.6)
ax.set_title('TF3 XAUUSD -- Buffered position over time (-1 to +1)')
ax.set_ylabel('Position')
ax.set_ylim(-1.05, 1.05)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'position_over_time.png'), dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- Fig 4 ---
# Regime-concentration bar chart, XAUUSD dev-window net-of-cost Sharpe per bucket
# (numbers reproduced from tf2_full_construction.py's XAUUSD dev output, disclosed
# in tf2_addendum_02...md -- not recomputed here from raw regime series, since the
# regime-conditioning diagnostic is a TF2-level artifact this package inherits,
# not a TF3-level recomputation).
vol_regime = {'Low': 1.96, 'Normal': 0.71, 'High': -1.08}
real_yield_regime = {'Falling': 1.05, 'Flat': 0.30, 'Rising': -0.35}
dollar_regime = {'Weakening': None, 'Flat': None, 'Strengthening': -0.22}
dollar_regime = {k: v for k, v in dollar_regime.items() if v is not None}

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
colors = ['#26a269' if v >= 0 else '#c01c28' for v in vol_regime.values()]
axes[0].bar(list(vol_regime.keys()), list(vol_regime.values()), color=colors)
axes[0].axhline(0, color='black', lw=0.6)
axes[0].set_title('Vol-regime concentration (dev, net Sharpe)')
axes[0].grid(alpha=0.25, axis='y')

colors2 = ['#26a269' if v >= 0 else '#c01c28' for v in real_yield_regime.values()]
axes[1].bar(list(real_yield_regime.keys()), list(real_yield_regime.values()), color=colors2)
axes[1].axhline(0, color='black', lw=0.6)
axes[1].set_title('Real-yield-regime concentration (dev, net Sharpe)')
axes[1].grid(alpha=0.25, axis='y')

fig.suptitle('XAUUSD TF2/TF3 -- edge concentrates where the Erb & Harvey real-yield\nmechanism predicts (source: tf2_addendum_02, not recomputed here)', fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'regime_concentration.png'), dpi=140)
plt.close(fig)

print("Figures written to", FIG)
for f in sorted(os.listdir(FIG)):
    print(" -", f)
