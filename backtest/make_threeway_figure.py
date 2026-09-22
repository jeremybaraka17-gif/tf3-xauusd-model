import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, '..', 'figures')
DEV_END = '2025-04-02'

s = pd.read_csv(os.path.join(HERE, 'tf3_threeway_series.csv'), index_col=0, parse_dates=True)

bh_cum = (1 + s['bh_net_ret'].fillna(0)).cumprod()
ma_cum = (1 + s['ma200_net_ret'].fillna(0)).cumprod()
tf3_cum = (1 + s['tf3_net_ret'].fillna(0)).cumprod()
tf3_lo_cum = (1 + s['tf3_longonly_net_ret'].fillna(0)).cumprod()

fig, ax = plt.subplots(figsize=(11.5, 6))
ax.plot(bh_cum.index, bh_cum.values, label='Buy & hold', color='#888888', lw=1.2)
ax.plot(ma_cum.index, ma_cum.values, label='200d-MA long-only', color='#e5a50a', lw=1.3)
ax.plot(tf3_cum.index, tf3_cum.values, label='TF3 two-sided (long+short)', color='#1a5fb4', lw=1.5)
ax.plot(tf3_lo_cum.index, tf3_lo_cum.values, label='TF3 signal, long-only variant', color='#2ec27e', lw=1.3, ls='--')
ax.axvline(pd.Timestamp(DEV_END), color='black', ls='--', lw=0.8, alpha=0.6)
ax.set_yscale('log')
ax.set_title('XAUUSD -- Buy & hold vs. 200d-MA vs. TF3 (two-sided) vs. TF3 signal long-only, net of cost')
ax.set_ylabel('Cumulative growth (log)')
ax.legend(loc='upper left', fontsize=9)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'threeway_comparison_equity.png'), dpi=140)
plt.close(fig)
print("wrote threeway_comparison_equity.png")
