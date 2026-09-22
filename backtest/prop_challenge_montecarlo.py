"""
TF3 XAUUSD -- Monte Carlo pass-rate simulation for the GFT $5k 2-Step and
$10k 1-Step challenges, following the exact methodology this project
already uses for this class of question (P31's block-bootstrap
Monte Carlo, block length 21 days) and the survival guide's own explicit
Rule 3 ("run the Monte Carlo, don't guess an allocation").

WHAT IS CONFIRMED (from the user directly, this session) vs ASSUMED:

  $5k 2-Step (GFT):  Step 1 target 8%, Step 2 target 6% (disclosed by the
    user as "6% (or 5% depending on Standard/Goat variant)" -- 6% used
    as primary, 5% not separately simulated here, flagged as an open
    variant question). Max total loss 10% static (floor at 90% of
    INITIAL balance -- this script does NOT reset the total-loss floor
    between Step 1 and Step 2, since the user's own description says
    "static... floor at 90% of initial balance," not "per phase").
    Max daily loss: user gave a range (4-5%, "based on balance/equity")
    -- this script uses the TIGHTER 4%, following this project's own
    established convention (risk_governor.py did the same thing when
    GFT's 1-Step daily limit was ambiguous between two account-purchase
    dates: default to the tighter figure, since it only costs a little
    EV if the true limit is looser and never costs safety margin).
    Min trading days: 3 per phase (confirmed).

  $10k 1-Step (GFT): profit target 10%, max total loss 6% static,
    max daily loss 3%, min trading days 3 -- ALL of these match
    risk_governor.py's already-confirmed, in-project figures exactly,
    so this is the most solidly-grounded of the two challenges simulated
    here.

WHAT IS NOT CONFIRMED AND IS SWEPT, NOT ASSUMED: GFT's actual leverage
for XAUUSD. `instrument_specs.py` (imported by the existing live prop
system) almost certainly has this as `LEVERAGE_GFT['xauusd']`, but that
file was not retrievable from the project's docs in this session -- so
rather than invent a number, this script sweeps EFFECTIVE_EXPOSURE_MULT
(defined below) across a range and reports the FULL sensitivity, not a
single cherry-picked "recommended" number pretending precision it
doesn't have.

EFFECTIVE_EXPOSURE_MULT collapses two separate real-world numbers
(risk_allocation_fraction x actual broker leverage) into one, because
what actually matters for the P&L path is their PRODUCT -- the total
multiple of account equity deployed as notional exposure at
target_position=+-1. If GFT's real gold leverage is confirmed later,
divide the EFFECTIVE_EXPOSURE_MULT that looks best below by that real
leverage number to back out the risk_allocation_fraction it implies.

Return source: block bootstrap (block=21 trading days, matching P31's
own locked choice, not re-tuned here) of TF3's ACTUAL net-of-cost daily
return series, pooled across dev+OOS (the best available estimate of
the return-generating process's distribution; note this is a distinct,
disclosed choice from the dev-only calibration used for the SIGNAL's own
scalars, which remains untouched -- only the bootstrap's INPUT DATA
pools both windows, not the forecast construction).
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

BLOCK_LEN = 21          # P31's own locked choice, reused unchanged
N_SIMS = 3000
MAX_HORIZON_DAYS = 180  # ~8.5 months, a generous cap; most challenges have no formal time limit on GFT but this bounds the simulation
MIN_TRADING_DAYS = 3
EXPOSURE_MULTS = [1, 2, 3, 5, 8, 12, 16, 20]

HERE = os.path.dirname(os.path.abspath(__file__))

CHALLENGES = {
    '5k_2step': {
        'account_equity': 5000.0,
        'phases': [
            {'name': 'Step 1', 'target': 0.08},
            {'name': 'Step 2', 'target': 0.06},
        ],
        'daily_loss_limit': 0.04,   # tighter of the disclosed 4-5% range
        'total_loss_limit': 0.10,   # static, from INITIAL balance, not reset between phases
    },
    '10k_1step': {
        'account_equity': 10000.0,
        'phases': [
            {'name': 'Step 1 (single phase)', 'target': 0.10},
        ],
        'daily_loss_limit': 0.03,
        'total_loss_limit': 0.06,
    },
}


def build_tf3_net_returns():
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
    # REVISED: long-only -- see research/tf3_addendum_05...md and tf4_addendum_01...md.
    # This changes the return-generating series the Monte Carlo bootstraps from, so the
    # pass-rate numbers below supersede the original two-sided run.
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
    position = pd.Series(held, index=target.index)

    pos_change = position.diff().abs().fillna(position.abs())
    med_spread = spread_col[spread_col > 0].median()
    cost = pos_change * (spread_col.replace(0, med_spread) * POINT_SIZE) / px
    net_ret = (position * logret - cost).dropna()
    return net_ret  # simple (arithmetic-ish, log-return) daily series, both windows pooled by caller


def block_bootstrap_paths(return_series, n_sims, horizon, block_len, rng):
    """Returns an (n_sims, horizon) array of resampled daily log-returns."""
    r = return_series.values
    n = len(r)
    n_blocks_needed = int(np.ceil(horizon / block_len))
    paths = np.empty((n_sims, n_blocks_needed * block_len))
    for i in range(n_sims):
        starts = rng.integers(0, n - block_len, size=n_blocks_needed)
        blocks = [r[s:s + block_len] for s in starts]
        paths[i] = np.concatenate(blocks)
    return paths[:, :horizon]


def simulate_challenge(paths_logret, challenge_cfg, exposure_mult):
    """paths_logret: (n_sims, horizon) array of UNLEVERED daily log-returns
    (TF3's own, already net of cost). Scales by exposure_mult to get
    account-level daily log-returns, then walks each path day by day
    against the challenge's phase targets and loss limits.

    Returns dict of summary stats across all sims."""
    n_sims, horizon = paths_logret.shape
    account_ret = paths_logret * exposure_mult   # approx: linear scaling of the leveraged notional's log-return

    results = []  # per-sim: dict(outcome, days_to_pass or days_to_breach)
    for i in range(n_sims):
        equity = 1.0            # normalized to 1.0 = initial balance
        day_start_equity = 1.0
        phase_start_equity = 1.0
        initial_equity = 1.0    # for the STATIC total-loss floor (never resets between phases)
        phase_idx = 0
        outcome = 'no_pass_within_horizon'
        pass_day = None
        breach_day = None
        for day in range(horizon):
            r = account_ret[i, day]
            equity = equity * np.exp(r)

            daily_loss = (day_start_equity - equity) / day_start_equity
            total_loss = (initial_equity - equity) / initial_equity

            if daily_loss > challenge_cfg['daily_loss_limit']:
                outcome = 'breach_daily'
                breach_day = day + 1
                break
            if total_loss > challenge_cfg['total_loss_limit']:
                outcome = 'breach_total'
                breach_day = day + 1
                break

            phase_gain = (equity - phase_start_equity) / phase_start_equity
            phase = challenge_cfg['phases'][phase_idx]
            if phase_gain >= phase['target'] and (day + 1) >= MIN_TRADING_DAYS:
                if phase_idx == len(challenge_cfg['phases']) - 1:
                    outcome = 'pass'
                    pass_day = day + 1
                    break
                else:
                    phase_idx += 1
                    phase_start_equity = equity
                    # NOTE: day_start_equity resets normally below regardless;
                    # total_loss floor intentionally NOT reset (static, per spec)

            # simulate calendar-day reset of day_start_equity (each sim step = 1 trading day)
            day_start_equity = equity

        results.append({'outcome': outcome, 'pass_day': pass_day, 'breach_day': breach_day})

    rdf = pd.DataFrame(results)
    pass_rate = (rdf['outcome'] == 'pass').mean()
    breach_rate = rdf['outcome'].isin(['breach_daily', 'breach_total']).mean()
    no_pass_rate = (rdf['outcome'] == 'no_pass_within_horizon').mean()
    passed = rdf[rdf['outcome'] == 'pass']
    median_days = passed['pass_day'].median() if len(passed) else np.nan
    p25_days = passed['pass_day'].quantile(0.25) if len(passed) else np.nan
    p75_days = passed['pass_day'].quantile(0.75) if len(passed) else np.nan

    return {
        'exposure_mult': exposure_mult, 'pass_rate': pass_rate, 'breach_rate': breach_rate,
        'no_pass_within_horizon_rate': no_pass_rate,
        'median_days_to_pass': median_days, 'p25_days_to_pass': p25_days, 'p75_days_to_pass': p75_days,
    }


def main():
    rng = np.random.default_rng(20260922)  # fixed seed, disclosed, not tuned for a favorable result
    net_ret = build_tf3_net_returns()
    print(f"Pooled dev+OOS TF3 net daily return series: n={len(net_ret)} days, "
          f"mean={net_ret.mean()*100:.4f}%/day, std={net_ret.std()*100:.4f}%/day")

    all_rows = []
    for chal_name, cfg in CHALLENGES.items():
        print(f"\n{'='*78}\n{chal_name}  (equity ${cfg['account_equity']:,.0f}, "
              f"daily_limit={cfg['daily_loss_limit']*100:.0f}%, total_limit={cfg['total_loss_limit']*100:.0f}%, "
              f"phases={[p['name']+':'+str(p['target']*100)+'%' for p in cfg['phases']]})\n{'='*78}")
        for mult in EXPOSURE_MULTS:
            paths = block_bootstrap_paths(net_ret, N_SIMS, MAX_HORIZON_DAYS, BLOCK_LEN, rng)
            res = simulate_challenge(paths, cfg, mult)
            res['challenge'] = chal_name
            all_rows.append(res)
            print(f"  exposure_mult={mult:>3d}  pass_rate={res['pass_rate']*100:5.1f}%  "
                  f"breach_rate={res['breach_rate']*100:5.1f}%  "
                  f"no_pass_in_{MAX_HORIZON_DAYS}d={res['no_pass_within_horizon_rate']*100:5.1f}%  "
                  f"median_days_to_pass={res['median_days_to_pass']}")

    out = pd.DataFrame(all_rows)
    out.to_csv(os.path.join(HERE, 'prop_challenge_montecarlo_results.csv'), index=False)
    print(f"\nSaved to prop_challenge_montecarlo_results.csv")


if __name__ == '__main__':
    main()
