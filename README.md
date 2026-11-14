# TF3 — XAUUSD EWMAC drawdown-management deployment architecture

**REVISED TO LONG-ONLY.** The construction described below was originally two-sided (long and short). `research/tf3_addendum_05...md` found the short side destroys value on every metric, in both windows; `research/tf4_addendum_01...md` confirmed that finding is robust across 5 different vol-normalization windows, not a coincidence of one parameter choice. The shipped code now clips position to [0,1], not [-1,1] — see `research/tf3_addendum_06_revision_to_long_only_shipped_construction_updated_numbers.md` for the updated numbers, which supersede everything below and in the original model spec that assumes two-sided.

Status: research-validated drawdown-management construction (gross and net of cost, with a completed regime-conditioning diagnostic), packaged as a deployment-ready architecture. With the long-only revision, it also now beats a 200-day-MA long-only benchmark on Sharpe in both dev and OOS (`research/tf3_vs_200dma_result.md`, updated) — a genuine improvement over the original two-sided version, though not an unconditional one (see Addendum 06's OOS-robustness caveat). Still not primarily a return-enhancer — read it as a drawdown-management tool that, after this revision, no longer costs Sharpe to get that protection. Not yet actually deployed: `risk_allocation_fraction` is undecided and no live system slot has been assigned. See `research/tf3_addendum_02_missing_parameters_completeness_review.md` for the full list of what remains open, and `research/tf3_addendum_06...md` for what changed.

## Folder structure

```
xauusd_tf3_model/
├── data/          Source price/macro series this construction is built and tested on
├── research/      Pre-registrations, results, model specs, addenda — the paper trail
├── backtest/      Consolidated, rerunnable backtest + figure generation
├── figures/       Generated charts (equity curve, drawdown, position, regime concentration)
├── live/          Reference deployment logic (signal + buffer + sizing) — NOT wired to a broker
└── README.md      This file
```

## What TF3 is, in one paragraph

A standalone, two-sided (long/short) position-sizing system on XAUUSD, built from a 6-pair EWMAC forecast (Carver's *Systematic Trading* framework), replacing a plain buy-and-hold exposure. It materially reduces the frequency and depth of -6%-floor-breach drawdown episodes in both the dev window (through 2025-04-02) and the out-of-sample window (2025-04-03 through 2026-07-03), gross and net of realistic spread costs, and its edge concentrates exactly where gold's known real-yield mechanism (Erb & Harvey, "The Golden Dilemma") predicts it should — the most mechanistically interpretable result in this project's broader TF family. TF3 adds a position-inertia buffer (Carver's own published "trade to the edge of the buffer" rule) on top of TF2's already-validated signal, cutting turnover without degrading the validated result.

## Where each claim comes from

| Claim | Source doc |
|---|---|
| EWMAC signal construction, per-instrument staging | `research/model_spec_tf2_ewmac_drawdown_management_xauusd_xagusd_nas100_v1.md` |
| Net-of-cost breach-count PASS, XAUUSD cost drag is small | `research/tf2_addendum_02_full_construction_net_of_cost_survives_regime_check_reveals_gold_mechanism_sensible_silver_nas100_weaker.md` |
| Position-inertia buffer, account-terms sizing, execution lag, risk limits | `research/model_spec_tf3_xauusd_deployment_architecture_v1.md` |
| Buffer reproduction discrepancy (disclosed, not resolved) | `research/tf3_addendum_01_backtest_consolidation_buffer_numbers_do_not_exactly_reproduce_the_original_inline_check_conclusion_unchanged.md` |
| Completeness review / open parameters | `research/tf3_addendum_02_missing_parameters_completeness_review.md` |
| Where TF3 came from (prior EWMAC attempt that failed on the equity universe, closed) | `research/hypothesis_tf1_ewmac_multiscale_forecast_acceleration_volspike.md`, `research/tf1_addendum_01...md` |

## Reproducing this package

```bash
cd backtest
python3 tf3_xauusd_backtest.py   # prints dev/OOS Sharpe, breach counts, turnover; saves tf3_xauusd_series.csv
python3 make_figures.py          # writes ../figures/*.png from the saved series
```

Both scripts are self-contained given the files in `data/` and require only `pandas`, `numpy`, `matplotlib`.

## Live logic (reference only, not connected to a broker)

```bash
cd live
python3 tf3_xauusd_live.py --price-csv ../data/xauusd_D1.csv --held-position 0.0 \
    --account-equity 100000 --risk-allocation-fraction 0.0
```

`--risk-allocation-fraction` defaults callers to `0.0` deliberately — it is an undecided business input, not a research output, and this script will not guess a number for it. The data-integrity kill switch specified in the deployment spec is a stub (`NotImplementedError`) here, not a working control — see `research/tf3_addendum_02...md` item 4 for why, and do not treat this script as ready to run against a real account.

## Unattended daemon (signal + Telegram + account fail-safe) — `research/tf3_addendum_08...md`

`live/tf3_daemon.py` runs the challenge-config version of the signal (`tf3_challenge_live.py`) unattended, once a day: it connects to a local MT5 terminal, refuses to compute or send anything unless the terminal is logged into the account named in `live/.env`, and pushes the resulting target to Telegram — never placing an order. Credentials (Telegram token/chat ID, expected MT5 account login/server) live in `live/.env` (copy `live/.env.example`), never in JSON, and `.env` is git-ignored. It has been tested against a mock MT5 interface (`live/tf3_daemon.py --dry-run`), not against a real terminal or real Telegram delivery — both require your own machine and credentials, and `research/tf3_addendum_08...md` is explicit about exactly what has and hasn't been verified. Read it, and its "before running this for real" checklist, before scheduling anything.

## What is genuinely NOT done yet

- No `risk_allocation_fraction` chosen.
- No confirmed live deployment slot (this would be a third live system alongside the existing prop-firm trend system and GOAT-8).
- No extension of CAP1's capital-allocation analysis to include this as a third system.
- Data-integrity and regime kill switches are specified qualitatively, not implemented.
- No walk-forward re-validation cadence set.
- Contract size (100 oz/lot) used in the live script's lot-sizing arithmetic is a standard-convention assumption, not confirmed against any specific broker.
- Hit a wall on momentum; still...

Full detail on every item above is in `research/tf3_addendum_02_missing_parameters_completeness_review.md`.
