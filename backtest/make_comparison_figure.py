import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEV_END = '2025-04-02'

s = pd.read_csv(os.path.join(HERE, 'tf3_vs_200dma_series.csv'), index_col=0, parse_dates=True)
tf3_cum = (1 + s['tf3_net_ret'].fillna(0)).cumprod()
ma_cum = (1 + s['ma200_net_ret'].fillna(0)).cumprod()

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(ma_cum.index, ma_cum.values, label='200d-MA long-only (net)', color='#e5a50a', lw=1.3)
ax.plot(tf3_cum.index, tf3_cum.values, label='TF3 buffered EWMAC (net)', color='#1a5fb4', lw=1.4)
ax.axvline(pd.Timestamp(DEV_END), color='black', ls='--', lw=0.8, alpha=0.6)
ax.set_yscale('log')
ax.set_title('TF3 vs. 200d-MA long-only, XAUUSD, net of cost (log scale)')
ax.set_ylabel('Cumulative growth (log)')
ax.legend(loc='upper left')
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(HERE, 'tf3_vs_200dma_equity.png'), dpi=140)
plt.close(fig)
print("wrote tf3_vs_200dma_equity.png")
